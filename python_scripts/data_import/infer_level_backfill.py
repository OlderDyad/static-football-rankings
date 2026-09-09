#!/usr/bin/env python3
"""
infer_level_backfill.py

Catches the class of gap the OK 6/8-man LevelMismatch review just surfaced:
name-matching a state association's official roster string (e.g. OSSAA's
"Balko/Forgan") to *a* DB TeamName (e.g. "Balko-Forgan (OK)") does not
guarantee that's the TeamName string actually used in HS_Scores for that
program's games -- MaxPreps/import naming can quietly use the OTHER half
of a co-op name ("Balko (OK)") for some or all seasons, leaving the real
game-log name with no verified HS_Team_Level_History row at all, which
then shows up as a false-positive LevelMismatch against the co-op's
correctly-tagged opponents.

Rather than trust name-matching alone a second time, this infers level
from WHO A TEAM ACTUALLY PLAYS: for any (TeamName, Season) that has no
existing VERIFIED HS_Team_Level_History row, look at its opponents that
season. If a strong majority of them are already verified at a level
(typically 8, since that's the actively-being-corrected gap, but 11 works
the same way), propose the team is that level for that season too.
Evidence-based, not name-based -- reusable for any state's 6/8-man
mapping, not just OK.

This is READ-ONLY by default (produces a review CSV of season-level
proposals, auto-merged into contiguous ranges per team). --apply only
writes rows from a CSV you've reviewed (Confirmed=1 column), using the
same transition-split pattern as ossaa_8man_import.py: close the
overlapping existing row's Season_End right before the proposed range,
insert the new verified row.

Usage:
  python infer_level_backfill.py --state OK --season-min 2015 --output ok_level_backfill_review.csv
  # ... review the CSV, set Confirmed=1 for rows to apply ...
  python infer_level_backfill.py --input ok_level_backfill_review.csv --apply
"""

import argparse
import logging

import pandas as pd
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
db_connection_str = f'mssql+pyodbc://{SERVER_NAME}/{DATABASE_NAME}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes'
engine = create_engine(db_connection_str)

MIN_VERIFIED_OPPONENTS = 2      # need at least this many verified-level opponents that season to say anything
AGREEMENT_THRESHOLD = 0.80      # this fraction of verified opponents must agree on one level
DEFAULT_LEVEL = 11              # what an unverified/absent row is treated as elsewhere in the pipeline


def fetch_level_history(state):
    df = pd.read_sql(text("""
        SELECT TeamName, PlayerLevel, Season_Begin, Season_End, Is_Verified
        FROM HS_Team_Level_History
        WHERE TeamName LIKE :pattern
    """), engine, params={'pattern': f'%({state})'})
    return df


def build_lookup(level_df):
    lookup = {}
    for r in level_df.itertuples(index=False):
        lookup.setdefault(r.TeamName, []).append((r.Season_Begin, r.Season_End, r.PlayerLevel, bool(r.Is_Verified)))
    return lookup


def verified_level(lookup, team, season):
    """Level if this team has a VERIFIED row covering this season, else None."""
    for begin, end, level, is_verified in lookup.get(team, []):
        if is_verified and begin <= season <= end:
            return level
    return None


def has_any_row(lookup, team, season):
    for begin, end, level, is_verified in lookup.get(team, []):
        if begin <= season <= end:
            return True
    return False


def fetch_games(state, season_min):
    df = pd.read_sql(text("""
        SELECT Season, Home, Visitor
        FROM HS_Scores
        WHERE (Home LIKE :pattern OR Visitor LIKE :pattern) AND Season >= :season_min
    """), engine, params={'pattern': f'%({state})', 'season_min': season_min})
    return df


def find_backfill_candidates(games_df, lookup):
    """For every (team, season) with no verified row, tally verified-opponent
    levels and propose one if there's a strong majority."""
    # team -> season -> list of opponent verified levels seen
    evidence = {}
    for r in games_df.itertuples(index=False):
        for team, opponent in ((r.Home, r.Visitor), (r.Visitor, r.Home)):
            opp_level = verified_level(lookup, opponent, r.Season)
            evidence.setdefault(team, {}).setdefault(r.Season, {'total': 0, 'verified_levels': []})
            evidence[team][r.Season]['total'] += 1
            if opp_level is not None:
                evidence[team][r.Season]['verified_levels'].append(opp_level)

    proposals = []
    for team, season_map in evidence.items():
        for season, data in season_map.items():
            if verified_level(lookup, team, season) is not None:
                continue  # already ground truth, nothing to propose
            levels = data['verified_levels']
            if len(levels) < MIN_VERIFIED_OPPONENTS:
                continue
            counts = pd.Series(levels).value_counts()
            top_level, top_count = counts.index[0], counts.iloc[0]
            agreement = top_count / len(levels)
            if agreement < AGREEMENT_THRESHOLD:
                continue
            current = DEFAULT_LEVEL if not has_any_row(lookup, team, season) else None
            if current == top_level:
                continue  # already matches the unverified default, nothing new to say
            proposals.append({
                'TeamName': team, 'Season': season, 'ProposedLevel': int(top_level),
                'VerifiedOpponentGames': len(levels), 'TotalGamesThatSeason': data['total'],
                'Agreement': round(agreement, 2),
            })
    return pd.DataFrame(proposals)


def merge_into_ranges(proposals_df):
    """Collapse consecutive same-team same-level seasons into one row per
    range, so the apply step doesn't insert a separate History row per year."""
    if proposals_df.empty:
        return proposals_df
    rows = []
    for team, group in proposals_df.groupby('TeamName'):
        group = group.sort_values('Season')
        for level, lvl_group in group.groupby('ProposedLevel'):
            seasons = sorted(lvl_group['Season'].tolist())
            start = prev = seasons[0]
            for s in seasons[1:] + [None]:
                if s is not None and s == prev + 1:
                    prev = s
                    continue
                sub = lvl_group[(lvl_group['Season'] >= start) & (lvl_group['Season'] <= prev)]
                rows.append({
                    'TeamName': team, 'ProposedLevel': int(level),
                    'Season_Begin': int(start), 'Season_End': int(prev),
                    'VerifiedOpponentGames': int(sub['VerifiedOpponentGames'].sum()),
                    'TotalGamesThatSeason': int(sub['TotalGamesThatSeason'].sum()),
                    'MinAgreement': float(sub['Agreement'].min()),
                    'Confirmed': 0,
                })
                if s is not None:
                    start = prev = s
    return pd.DataFrame(rows)


def apply_backfill(confirmed_df, dry_run=True):
    confirmed = confirmed_df[confirmed_df['Confirmed'] == 1]
    if confirmed.empty:
        logger.info("No confirmed rows to apply.")
        return

    if dry_run:
        logger.info(f"[DRY RUN] Would apply {len(confirmed)} range(s).")
        for _, row in confirmed.iterrows():
            logger.info(f"  {row['TeamName']}: PlayerLevel {row['ProposedLevel']} for "
                        f"{row['Season_Begin']}-{row['Season_End']}")
        return

    with engine.begin() as conn:
        for _, row in confirmed.iterrows():
            team, level = row['TeamName'], int(row['ProposedLevel'])
            begin, end = int(row['Season_Begin']), int(row['Season_End'])

            # Close out any existing open-ended row that this range would overlap
            # the start of (mirrors ossaa_8man_import.py's transition-split logic).
            conn.execute(text("""
                UPDATE HS_Team_Level_History
                SET Season_End = :prior_end
                WHERE TeamName = :team AND Season_End >= :begin AND Season_Begin < :begin
            """), {'prior_end': begin - 1, 'team': team, 'begin': begin})

            conn.execute(text("""
                INSERT INTO HS_Team_Level_History (TeamName, PlayerLevel, Season_Begin, Season_End, Is_Verified)
                VALUES (:team, :level, :begin, :end, 1)
            """), {'team': team, 'level': level, 'begin': begin, 'end': end})

    logger.info(f"{len(confirmed)} range(s) applied and logged as verified "
                f"(evidence: opponent-network inference, see infer_level_backfill.py).")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--state', default=None, help="State code, e.g. OK (required for detection mode)")
    parser.add_argument('--season-min', type=int, default=2015, help="Only consider seasons >= this year")
    parser.add_argument('--output', default=None, help="Write the review CSV here")
    parser.add_argument('--input', default=None, help="Read a reviewed CSV back in (Confirmed column edited by hand)")
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()

    if args.apply:
        if not args.input:
            parser.error("--apply requires --input <reviewed CSV>")
        df = pd.read_csv(args.input)
        apply_backfill(df, dry_run=False)
        return

    if not args.state:
        parser.error("--state is required in detection mode")

    level_df = fetch_level_history(args.state)
    lookup = build_lookup(level_df)
    logger.info(f"{len(level_df)} level-history row(s) loaded for {args.state}.")

    games_df = fetch_games(args.state, args.season_min)
    logger.info(f"{len(games_df)} game(s) loaded for {args.state}, season >= {args.season_min}.")

    proposals = find_backfill_candidates(games_df, lookup)
    logger.info(f"{len(proposals)} season-level proposal(s) before range-merging.")

    ranges = merge_into_ranges(proposals)
    print(f"\n{len(ranges)} range proposal(s):")
    if not ranges.empty:
        print(ranges.sort_values(['TeamName', 'Season_Begin']).to_string(index=False))

    if args.output:
        ranges.to_csv(args.output, index=False, encoding='utf-8-sig')
        logger.info(f"Written to {args.output}. Review, set Confirmed=1 for ranges to apply, "
                    f"then re-run with --input {args.output} --apply.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
diagnose_game_count_anomaly.py

Read-only prototype for the GameCountAnomaly ConflictType -- which exists
as an enum value in mapping_conflict_audit.py's CLI choices but has NEVER
had a detector written for it (confirmed by grep, 2026-09-10). This script
is step one: see what the real data's distribution actually looks like
before committing to any threshold, rather than guessing a fixed
"14 games regular season, 16 for deep-playoff states" cap from general
knowledge of playoff formats. That knowledge would be unreliable (playoff
formats have changed repeatedly across decades within the same state --
see the Reserve/Leon Godchaux 1972-77 split and Tallulah/Plain Dealing
consolidation-era gaps found earlier this session) and is exactly the
kind of unverified assumption this project has learned to distrust
tonight (the classify_team_tiers.py Deaf-seed bug, the Lake Arthur
mistagging -- both were "docstring/assumption vs. actual code/data" gaps).

APPROACH: empirical and self-calibrating, same philosophy as
diagnose_date_truncation.py -- derive "anomalous" from the database's OWN
distribution for that specific (State, Season), not a hardcoded universal
constant. For each (State, Season) with enough teams to be statistically
meaningful, compute the median and MAD (median absolute deviation --
robust to the very outliers we're trying to detect, unlike mean/stddev)
of games-played-that-season across all teams in that state. Flag a team
whose count is both:
  1. A robust z-score outlier relative to its own (State, Season) peers
     (Iglewicz-Hoaglin modified z-score: 0.6745*(x-median)/MAD >= threshold), AND
  2. Above an absolute floor (so a season with almost no MAD spread, e.g.
     a small/rural season where everyone plays near-identically, doesn't
     trivially flag a team playing just 1-2 games more than everyone else).

This intentionally does NOT hardcode a per-state max-games table. If a
genuine, documented exception season needs excluding later (a real
format change worth noting explicitly), that should live in a database
table (era/region-scoped, matching the HS_Team_Level_History /
HS_Team_Name_Alias pattern already used elsewhere in this project) --
not in this script -- and only after this empirical version shows it's
actually needed.

Entirely READ-ONLY. A ranked report, nothing more. No HS_Mapping_Investigations
rows get written by this script -- that's a separate step (a
register_game_count_anomalies()-style function in mapping_conflict_audit.py,
analogous to the other detect-* commands) to build only once this
prototype's threshold has been sanity-checked against real output.

Usage:
  python diagnose_game_count_anomaly.py --state LA
  python diagnose_game_count_anomaly.py --state OK --z-threshold 4 --min-teams 10
"""

import argparse
import logging

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
db_connection_str = f'mssql+pyodbc://{SERVER_NAME}/{DATABASE_NAME}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes'
engine = create_engine(db_connection_str)

MIN_TEAMS_PER_SEASON = 8       # skip (State, Season) groups too small to say anything statistically
Z_THRESHOLD = 4.5              # modified/robust z-score cutoff (Iglewicz-Hoaglin suggest 3.5 for general
                                # outlier work; set higher here deliberately -- a real deep playoff run IS
                                # a legitimate outlier, we only want the implausible-beyond-that tail)
MIN_ABSOLUTE_GAMES = 16        # a flagged team's count must also clear this floor, regardless of z-score,
                                # so a low-spread small-town season doesn't trivially flag a minor difference


def fetch_team_season_counts(state):
    """One row per (TeamName, Season) with that team's total game count for
    the season, counting both Home and Visitor appearances. Scoped to one
    state via the same '%(ST)' suffix-match convention used elsewhere in
    this project (RemoveDuplicateGamesParameterized, diagnose_date_truncation.py)."""
    df = pd.read_sql(text("""
        SELECT Team, Season, COUNT(*) AS GameCount
        FROM (
            SELECT Home AS Team, Season FROM HS_Scores WHERE Home LIKE :pattern
            UNION ALL
            SELECT Visitor AS Team, Season FROM HS_Scores WHERE Visitor LIKE :pattern
        ) t
        GROUP BY Team, Season
    """), engine, params={'pattern': f'%({state})'})
    return df


def scan_seasons(df, min_teams, z_threshold, min_absolute_games):
    """For each Season, compute the median/MAD of GameCount across all
    teams that state fielded that year, then flag teams whose count is
    BOTH a robust z-score outlier AND above the absolute floor. Requiring
    both mirrors diagnose_date_truncation.py's two-signal design -- a
    single signal alone (either "far from the state's own median" or
    just "a lot of games") isn't enough on its own to distinguish a real
    deep-playoff champion from a genuine data error."""
    results = []
    for season, group in df.groupby('Season'):
        if len(group) < min_teams:
            continue

        counts = group['GameCount'].values
        median = np.median(counts)
        mad = np.median(np.abs(counts - median))
        if mad == 0:
            continue  # zero spread -- can't compute a meaningful z-score, skip rather than divide by zero

        for _, row in group.iterrows():
            z = 0.6745 * (row['GameCount'] - median) / mad
            if z >= z_threshold and row['GameCount'] >= min_absolute_games:
                results.append({
                    'Team': row['Team'], 'Season': int(season), 'GameCount': int(row['GameCount']),
                    'SeasonMedian': round(median, 1), 'SeasonMAD': round(mad, 1),
                    'RobustZ': round(z, 2), 'TeamsThatSeason': len(group),
                })
    return pd.DataFrame(results)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--state', required=True, help="2-letter code, e.g. LA")
    parser.add_argument('--min-teams', type=int, default=MIN_TEAMS_PER_SEASON)
    parser.add_argument('--z-threshold', type=float, default=Z_THRESHOLD)
    parser.add_argument('--min-absolute-games', type=int, default=MIN_ABSOLUTE_GAMES)
    parser.add_argument('--output', default=None)
    args = parser.parse_args()

    df = fetch_team_season_counts(args.state)
    logger.info(f"{len(df)} (team, season) row(s) for {args.state}.")

    if df.empty:
        logger.info(f"{args.state}: no rows found -- check the state code.")
        return

    report = scan_seasons(df, args.min_teams, args.z_threshold, args.min_absolute_games)

    if report.empty:
        logger.info(f"{args.state}: no team-season showed a game-count outlier at "
                    f"z>={args.z_threshold} / floor>={args.min_absolute_games}. Clean on this check "
                    f"(or thresholds may need loosening -- this is a prototype, sanity-check against "
                    f"a few known-real deep-playoff seasons before trusting a 'clean' result).")
    else:
        print(f"\n{len(report)} candidate game-count anomaly row(s) for {args.state}:")
        print(report.sort_values('RobustZ', ascending=False).to_string(index=False))
        logger.info(f"{args.state}: {len(report)} candidate(s) flagged. These are UNVERIFIED -- "
                    f"manually spot-check a few (live schedule, or the team's own game list) before "
                    f"assuming any are real errors. A genuine deep playoff run for a state championship "
                    f"team is expected to be the top of this list some seasons; the question is whether "
                    f"any of these are implausible even accounting for that.")

    if args.output:
        report.to_csv(args.output, index=False, encoding='utf-8-sig')
        logger.info(f"Written to {args.output}")


if __name__ == "__main__":
    main()

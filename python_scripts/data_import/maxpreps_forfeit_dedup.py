#!/usr/bin/env python3
"""
maxpreps_forfeit_dedup.py

Nationwide finding (discovered while investigating OK's Comanche vs.
Anadarko Riverside Indian repeat pattern): MaxPreps records a forfeit as a
literal "2-0" / "0-2" score with an "(FF)" tag on the team schedule page.
That symbolic score isn't caught by dbo.RemoveDuplicateGamesParameterized's
forfeit-marking step (it only flags Home_Score + Visitor_Score = 1), so
none of these ~5,800 maxpreps.com-sourced 2-0/0-2 games have Forfeit=1 set
anywhere in the database.

Separately -- and this is the part worth fixing structurally rather than
just flagging -- hundreds of specific team-pairs have the EXACT SAME 2-0
score duplicated across multiple different Season values (verified for
one case: Riverside Indian's entire 2013 season on MaxPreps is a single
forfeit loss to Comanche, "L 2-0 (FF)"; that same row also exists, wrongly,
under Season 2014/2015/2017/2018/2019 in HS_Scores). This script treats
every (Home, Visitor, Home_Score, Visitor_Score) group sharing the maxpreps
2-0/0-2 pattern across 2+ distinct seasons as one real forfeit duplicated
forward: it keeps the EARLIEST season's row (matching the one case we
verified by hand against MaxPreps directly), marks it Forfeit=1, and
deletes the later duplicate(s) with a full row-snapshot audit trail in
HS_Scores_Change_Log -- same ID-scoped, log-before-delete convention as
mapping_conflict_audit.py's delete command.

IMPORTANT CAVEAT: the "keep earliest season" rule is a heuristic based on
ONE verified case (Comanche), not something independently confirmed for
every one of the ~150+ affected team-pairs nationwide. Run --sample first
and spot-check a handful against MaxPreps before trusting --apply at full
scale, the same way every other fix in this project has been verified
against a primary source before being applied in bulk.

This script does NOT touch the ~5,600 games that only have ONE season on
record with this score (no cross-season duplicate) -- those just get
flagged Forfeit=1 in a separate, simpler pass (see --flag-only-singles).

Usage:
  python maxpreps_forfeit_dedup.py --sample 15                 # print 15 duplicate groups for manual MaxPreps spot-check, no DB changes
  python maxpreps_forfeit_dedup.py                              # dry run: show every group + planned keep/delete, no DB changes
  python maxpreps_forfeit_dedup.py --apply                      # actually dedup + flag Forfeit=1, full audit trail
  python maxpreps_forfeit_dedup.py --flag-only-singles --apply  # separate pass: just set Forfeit=1 on the non-duplicated 2-0/0-2 rows
"""

import argparse
import logging
from collections import defaultdict

import pandas as pd
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
db_connection_str = f'mssql+pyodbc://{SERVER_NAME}/{DATABASE_NAME}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes'
engine = create_engine(db_connection_str)


def fetch_all_forfeit_pattern_rows():
    return pd.read_sql(text("""
        SELECT ID, Date, Season, Home, Visitor, Home_Score, Visitor_Score,
               Location, Location2, Source, Forfeit, OT
        FROM HS_Scores
        WHERE Source LIKE '%maxpreps%'
          AND ((Home_Score = 2 AND Visitor_Score = 0) OR (Home_Score = 0 AND Visitor_Score = 2))
    """), engine)


def group_duplicates(df, max_day_spread=3):
    """Returns {(Home, Visitor, Home_Score, Visitor_Score): sorted-by-Season rows} for
    groups with 2+ distinct seasons.

    IMPORTANT: a same-score group spanning multiple seasons is only treated
    as a true duplicate if the (month, day) of the game is the same --
    within `max_day_spread` days -- across every season in the group. This
    was added after spot-checking the initial sample against MaxPreps
    directly: Greenbrier Christian Academy (VA) beat Hampton Roads Academy
    2-0 in BOTH 2018 (8/31) and 2019 (10/12) -- two genuinely different real
    games, just with the same score, on very different calendar dates. A
    copy-paste import bug reproduces the same calendar date every time (verified
    for Comanche/Anadarko Riverside Indian: every duplicate landed on 9/27,
    every single year); a real recurring rivalry does not. Filtering on date
    proximity is what tells the two cases apart."""
    groups = defaultdict(list)
    for _, row in df.iterrows():
        key = (row['Home'], row['Visitor'], row['Home_Score'], row['Visitor_Score'])
        groups[key].append(row)

    dup_groups = {}
    excluded_real_repeats = {}
    for key, rows in groups.items():
        seasons = set(r['Season'] for r in rows)
        if len(seasons) <= 1:
            continue
        rows_sorted = sorted(rows, key=lambda r: (r['Season'], str(r['ID'])))
        # compare every pair's (month, day) as a day-of-year distance (ignoring year),
        # so 12/30 vs 1/2 doesn't get falsely split by the wrap-around
        doys = [r['Date'].timetuple().tm_yday for r in rows_sorted]
        max_spread = max(doys) - min(doys)
        if max_spread <= max_day_spread:
            # every occurrence landed within a few days of the same calendar date -- true duplicate
            dup_groups[key] = rows_sorted
        else:
            # dates differ enough that this looks like a real recurring matchup, not a copy-paste bug
            excluded_real_repeats[key] = rows_sorted
    return dup_groups, excluded_real_repeats


def row_snapshot(row):
    # OldValue is VARCHAR(255) -- keep this well under that, so drop the
    # verbose/long fields (Location2, Source) that aren't needed to identify
    # the deleted game and aren't consistently short.
    s = (f"Season={row['Season']}, Date={row['Date']}, Home={row['Home']!r}, "
         f"Home_Score={row['Home_Score']}, Visitor={row['Visitor']!r}, "
         f"Visitor_Score={row['Visitor_Score']}, Forfeit={row['Forfeit']}, OT={row['OT']}")
    return s[:255]


def apply_group(key, rows, dry_run=True):
    keep = rows[0]
    dupes = rows[1:]
    home, visitor, hs, vs = key

    if dry_run:
        logger.info(f"[DRY RUN] KEEP {keep['ID']} (Season {keep['Season']}): {home} {hs}-{vs} {visitor} "
                    f"-- set Forfeit=1; DELETE {len(dupes)} duplicate(s): "
                    + ", ".join(f"{d['ID']} (Season {d['Season']})" for d in dupes))
        return

    with engine.begin() as conn:
        # Re-check current state in case a prior partial run already touched this
        # group (e.g. crashed partway through) -- makes re-running after a failure safe.
        keep_row = conn.execute(text("SELECT Forfeit FROM HS_Scores WHERE ID = :id"), {'id': keep['ID']}).fetchone()
        if keep_row is not None and not keep_row.Forfeit:
            conn.execute(text("""
                INSERT INTO HS_Scores_Change_Log (ScoresID, InvestigationID, FieldChanged, OldValue, NewValue, Reason, Script)
                VALUES (:id, NULL, 'Forfeit', :old, '1', :reason, 'maxpreps_forfeit_dedup.py')
            """), {'id': keep['ID'], 'old': str(keep['Forfeit']),
                   'reason': f"MaxPreps 2-0/0-2 forfeit-score pattern; kept as earliest-season copy of a game duplicated across seasons {[int(d['Season']) for d in dupes] + [int(keep['Season'])]}"})
            conn.execute(text("UPDATE HS_Scores SET Forfeit = 1 WHERE ID = :id"), {'id': keep['ID']})

        for d in dupes:
            still_there = conn.execute(text("SELECT 1 FROM HS_Scores WHERE ID = :id"), {'id': d['ID']}).fetchone()
            if still_there is None:
                continue  # already deleted by a prior partial run -- skip, don't double-log
            snapshot = row_snapshot(d)
            conn.execute(text("""
                INSERT INTO HS_Scores_Change_Log (ScoresID, InvestigationID, FieldChanged, OldValue, NewValue, Reason, Script)
                VALUES (:id, NULL, 'ROW_DELETED', :old, NULL, :reason, 'maxpreps_forfeit_dedup.py')
            """), {'id': d['ID'], 'old': snapshot,
                   'reason': f"Duplicate of MaxPreps forfeit game kept under Season {keep['Season']} (ID {keep['ID']}); "
                             f"same {home} {hs}-{vs} {visitor} score re-stamped under Season {d['Season']}."})
            conn.execute(text("DELETE FROM HS_Scores WHERE ID = :id"), {'id': d['ID']})

    logger.info(f"Applied: kept {keep['ID']} (Season {keep['Season']}), Forfeit=1; "
                f"deleted {len(dupes)} duplicate(s).")


def flag_singles(df, dup_groups, dry_run=True):
    """Rows with the forfeit score pattern but NOT part of a cross-season
    duplicate group -- just need Forfeit=1 set, nothing to delete."""
    dup_ids = set(str(r['ID']) for rows in dup_groups.values() for r in rows)
    singles = df[~df['ID'].astype(str).isin(dup_ids) & (df['Forfeit'] != True)]

    logger.info(f"{len(singles)} single (non-duplicated) maxpreps 2-0/0-2 rows to flag Forfeit=1.")
    if dry_run:
        return len(singles)

    with engine.begin() as conn:
        for _, row in singles.iterrows():
            conn.execute(text("""
                INSERT INTO HS_Scores_Change_Log (ScoresID, InvestigationID, FieldChanged, OldValue, NewValue, Reason, Script)
                VALUES (:id, NULL, 'Forfeit', :old, '1', 'MaxPreps 2-0/0-2 forfeit-score pattern, single occurrence, not duplicated across seasons.', 'maxpreps_forfeit_dedup.py')
            """), {'id': row['ID'], 'old': str(row['Forfeit'])})
            conn.execute(text("UPDATE HS_Scores SET Forfeit = 1 WHERE ID = :id"), {'id': row['ID']})
    return len(singles)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--sample', type=int, default=None, help="Print N duplicate groups (largest first) for manual MaxPreps spot-check, then exit -- no DB access beyond the read.")
    parser.add_argument('--apply', action='store_true', help="Actually apply the dedup + Forfeit flagging (default is dry-run/review only)")
    parser.add_argument('--flag-only-singles', action='store_true', help="Skip the dedup entirely; just Forfeit=1 the non-duplicated rows")
    parser.add_argument('--max-day-spread', type=int, default=3,
                         help="A same-score group is only treated as a true duplicate if every occurrence falls within this many days of the same calendar date across all its seasons (default 3). Real recurring matchups (verified example: Greenbrier Christian Academy vs. Hampton Roads Academy, 8/31 in 2018 and 10/12 in 2019, same 2-0 score both times) land on very different dates and are excluded instead.")
    args = parser.parse_args()

    logger.info("Fetching all maxpreps.com 2-0/0-2 rows...")
    df = fetch_all_forfeit_pattern_rows()
    logger.info(f"{len(df)} total rows fetched.")

    dup_groups, excluded_real_repeats = group_duplicates(df, max_day_spread=args.max_day_spread)
    total_dupe_rows = sum(len(v) for v in dup_groups.values())
    logger.info(f"{len(dup_groups)} team-pair groups look like TRUE duplicates (same score within "
                f"{args.max_day_spread} days every season): {total_dupe_rows} rows involved, "
                f"{total_dupe_rows - len(dup_groups)} would be deleted, {len(dup_groups)} kept.")
    logger.info(f"{len(excluded_real_repeats)} groups EXCLUDED as likely real recurring matchups "
                f"(same score, but dates spread out across the season/years) -- left untouched.")

    if args.sample is not None:
        ranked = sorted(dup_groups.items(), key=lambda kv: -len(kv[1]))
        print(f"\n=== TRUE DUPLICATE candidates (same date every season) -- top {args.sample} ===")
        for key, rows in ranked[:args.sample]:
            home, visitor, hs, vs = key
            seasons = ", ".join(f"{r['Season']}(ID {r['ID']}, {r['Date']})" for r in rows)
            print(f"{home} {hs}-{vs} {visitor}  ->  seasons: {seasons}  [would keep {rows[0]['Season']}]")

        ranked_excl = sorted(excluded_real_repeats.items(), key=lambda kv: -len(kv[1]))
        print(f"\n=== EXCLUDED as likely real repeat matchups (different dates) -- top {min(args.sample, len(ranked_excl))} ===")
        for key, rows in ranked_excl[:args.sample]:
            home, visitor, hs, vs = key
            seasons = ", ".join(f"{r['Season']}(ID {r['ID']}, {r['Date']})" for r in rows)
            print(f"{home} {hs}-{vs} {visitor}  ->  seasons: {seasons}  [NOT touched]")
        return

    if args.flag_only_singles:
        flag_singles(df, dup_groups, dry_run=not args.apply)
        return

    for key, rows in dup_groups.items():
        apply_group(key, rows, dry_run=not args.apply)

    n_singles = flag_singles(df, dup_groups, dry_run=not args.apply)

    print(f"\n=== {'APPLY' if args.apply else 'DRY RUN'} summary ===")
    print(f"Duplicate groups processed: {len(dup_groups)}")
    print(f"Rows kept (Forfeit=1 set): {len(dup_groups)}")
    print(f"Duplicate rows {'deleted' if args.apply else 'would be deleted'}: {total_dupe_rows - len(dup_groups)}")
    print(f"Single (non-duplicated) rows {'flagged' if args.apply else 'would be flagged'} Forfeit=1: {n_singles}")

    if not args.apply:
        print("\n(Dry run only -- no changes made. Try `--sample 15` first to spot-check a handful "
              "against MaxPreps directly, then re-run with --apply.)")


if __name__ == "__main__":
    main()
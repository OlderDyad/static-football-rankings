"""
run_full_rankings_recalc.py
============================
Orchestrates a multi-season ratings recalculation.

Why this exists: dbo.CalculateRankings_v4_Optimized loops through seasons
internally (it accepts @BeginSeason/@EndSeason and processes them one at a
time, with its own per-season TRY/CATCH so one bad season doesn't kill the
whole run) -- but it does NOT populate dbo.ScoresWinLossResults itself.
That table is populated by dbo.ScoresWinLoss, which only ever takes a
SINGLE @Season at a time and only INSERTs (never DELETEs first). So a
full historical recalc needs a driver that, for every season in range:
    1. DELETEs that season's existing rows from ScoresWinLossResults
    2. Calls dbo.ScoresWinLoss to repopulate them for the target @Week
before finally handing the whole season range to
CalculateRankings_v4_Optimized in one call, then refreshing Combined_Rating.

This mirrors the exact 4-step manual sequence worked out interactively on
2026-09-19/20 while diagnosing why 2026 rankings weren't calculating:
    1. DELETE FROM ScoresWinLossResults WHERE Season = <season>
    2. EXEC dbo.ScoresWinLoss @Season=<season>, @Week=<week>, @LeagueType=1
    3. EXEC CalculateRankings_v4_Optimized @BeginSeason=<begin>, @EndSeason=<end>, @Week=<week>
    4. EXEC UpdateCombinedRating @Season=NULL, @Week=NULL  -- refreshes everything, ~6 sec for 1.2M rows

Usage:
    python run_full_rankings_recalc.py
    (prompts for BeginSeason, EndSeason, Week; everything else is hardcoded
    below to match this project's standard configuration)

    python run_full_rankings_recalc.py --begin 2026 --end 2026 --week 38 --yes
    (non-interactive -- used by weekly_pipeline.py; exits non-zero on failure)

For a normal in-season weekly update (a single season, e.g. just 2026),
just enter the same season for both Begin and End -- this script works
fine for a single-season run too, it isn't only for full historical
recalcs.
"""

import pyodbc
import sys
import time
from datetime import datetime, timedelta

# --- CONFIGURATION (hardcoded -- matches consolidation_workflow_latin.py) ---
SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
LEAGUE_TYPE = 1          # 1 = High School
MAX_LOOPS = 2048
LOG_FREQUENCY = 100
CONN_STR = (
    f'DRIVER={{ODBC Driver 17 for SQL Server}};'
    f'SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;'
)
# --- END CONFIGURATION ---


def get_int_input(prompt, min_val=None, max_val=None):
    """Prompts for an integer, re-asking until a valid one (in range, if given) is entered."""
    while True:
        raw = input(prompt).strip()
        try:
            value = int(raw)
        except ValueError:
            print("  Please enter a whole number.")
            continue
        if min_val is not None and value < min_val:
            print(f"  Must be >= {min_val}.")
            continue
        if max_val is not None and value > max_val:
            print(f"  Must be <= {max_val}.")
            continue
        return value


def get_season_range_and_week():
    """Prompts for BeginSeason, EndSeason, and Week. Everything else is hardcoded."""
    print("=" * 70)
    print("FULL RANKINGS RECALC")
    print("=" * 70)
    print("Enter the season range to recalculate. For a normal weekly update")
    print("during the season, just use the same season for Begin and End")
    print("(e.g. Begin=2026, End=2026).")
    print()

    begin_season = get_int_input("Begin Season (e.g. 1877): ", min_val=1800, max_val=2100)
    end_season = get_int_input("End Season (e.g. 2026): ", min_val=1800, max_val=2100)
    week = get_int_input(
        "Week (35-52; use the ACTUAL current week during an in-progress season, "
        "52 only once a season -- including playoffs -- is fully complete): ",
        min_val=1, max_val=52,
    )

    n_seasons = abs(end_season - begin_season) + 1
    print()
    print(f"About to recalculate {n_seasons} season(s), from {begin_season} to "
          f"{end_season}, using Week={week} as the cumulative cutoff for every "
          f"one of those seasons.")
    if n_seasons > 5:
        print("This is a large batch -- for many decades of history this can take")
        print("a long time (each season runs its own convergence loop).")
    confirm = input("Type YES to proceed: ").strip()
    if confirm != "YES":
        print("Aborted -- nothing was changed.")
        sys.exit(0)

    return begin_season, end_season, week


def format_elapsed(seconds):
    return str(timedelta(seconds=int(seconds)))


def repopulate_scores_win_loss(conn, begin_season, end_season, week):
    """
    For every season in [begin_season, end_season] (inclusive, either
    direction), delete then repopulate that season's rows in
    dbo.ScoresWinLossResults via dbo.ScoresWinLoss. Continues past a season
    with zero games or an error rather than aborting the whole batch.
    """
    step = 1 if end_season >= begin_season else -1
    seasons = list(range(begin_season, end_season + step, step))
    total = len(seasons)

    print()
    print(f"STEP 1/3: Repopulating ScoresWinLossResults for {total} season(s)...")
    start_time = time.time()
    ok_count = 0
    error_count = 0

    for i, season in enumerate(seasons, start=1):
        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM dbo.ScoresWinLossResults WHERE Season = ?", season)
                cursor.execute(
                    "EXEC dbo.ScoresWinLoss @Season = ?, @Week = ?, @LeagueType = ?",
                    season, week, LEAGUE_TYPE,
                )
                cursor.execute(
                    "SELECT COUNT(*) FROM dbo.ScoresWinLossResults WHERE Season = ?", season
                )
                row_count = cursor.fetchone()[0]
            conn.commit()
            ok_count += 1
            if i % 10 == 0 or i == total or row_count == 0:
                elapsed = format_elapsed(time.time() - start_time)
                print(f"  [{i}/{total}] Season {season}: {row_count} games staged "
                      f"(elapsed {elapsed})")
        except Exception as exc:
            error_count += 1
            print(f"  [{i}/{total}] Season {season}: ERROR -- {exc}")
            try:
                conn.rollback()
            except Exception:
                pass

    elapsed = format_elapsed(time.time() - start_time)
    print(f"STEP 1/3 complete in {elapsed}. OK: {ok_count}, Errors: {error_count}")
    return error_count


def run_calculate_rankings(conn, begin_season, end_season, week):
    """Single call -- CalculateRankings_v4_Optimized loops through the season
    range internally, with its own per-season error handling."""
    print()
    print(f"STEP 2/3: Running CalculateRankings_v4_Optimized for "
          f"{begin_season}-{end_season}, Week={week}...")
    print("(This can take a long time for a large season range -- SSMS-style")
    print(" PRINT messages from the procedure are not visible through pyodbc;")
    print(" watch dbo.RankingsProcessLog in another window if you want live progress.)")
    start_time = time.time()
    with conn.cursor() as cursor:
        cursor.execute(
            "EXEC [dbo].[CalculateRankings_v4_Optimized] "
            "@LeagueType = ?, @BeginSeason = ?, @EndSeason = ?, @Week = ?, @MaxLoops = ?",
            str(LEAGUE_TYPE), begin_season, end_season, week, MAX_LOOPS,
        )
        # Drain any result sets the procedure's internal PRINTs/SELECTs might produce
        while cursor.nextset():
            pass
    conn.commit()
    elapsed = format_elapsed(time.time() - start_time)
    print(f"STEP 2/3 complete in {elapsed}.")


def run_update_combined_rating(conn):
    """Refreshes Combined_Rating for ALL data -- fast (~6 sec for 1.2M rows
    per project docs), simplest to just always refresh everything rather
    than track exactly which seasons changed."""
    print()
    print("STEP 3/3: Refreshing Combined_Rating for all data...")
    start_time = time.time()
    with conn.cursor() as cursor:
        cursor.execute("EXEC UpdateCombinedRating @Season = NULL, @Week = NULL")
        while cursor.nextset():
            pass
    conn.commit()
    elapsed = format_elapsed(time.time() - start_time)
    print(f"STEP 3/3 complete in {elapsed}.")


def parse_args():
    import argparse
    parser = argparse.ArgumentParser(description="Multi-season ratings recalculation.")
    parser.add_argument("--begin", type=int, help="Begin season")
    parser.add_argument("--end", type=int, help="End season")
    parser.add_argument("--week", type=int, help="Week cutoff (1-52)")
    parser.add_argument("--yes", action="store_true",
                        help="Skip the YES confirmation (for unattended runs)")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.begin is not None and args.end is not None and args.week is not None:
        if not (1 <= args.week <= 52):
            print(f"--week must be 1-52 (got {args.week}).")
            return 1
        begin_season, end_season, week = args.begin, args.end, args.week
        print(f"Non-interactive run: seasons {begin_season}-{end_season}, Week={week}")
        if not args.yes:
            if input("Type YES to proceed: ").strip() != "YES":
                print("Aborted -- nothing was changed.")
                return 0
    else:
        begin_season, end_season, week = get_season_range_and_week()

    overall_start = time.time()
    print()
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    conn = pyodbc.connect(CONN_STR, autocommit=False)
    exit_code = 0
    try:
        error_count = repopulate_scores_win_loss(conn, begin_season, end_season, week)
        if error_count > 0:
            exit_code = 2
            print()
            print(f"WARNING: {error_count} season(s) failed to repopulate "
                  f"ScoresWinLossResults -- their ranking calc may produce zero "
                  f"rows or stale data. Review the errors above before trusting "
                  f"those seasons' results.")
        run_calculate_rankings(conn, begin_season, end_season, week)
        run_update_combined_rating(conn)
    except Exception as exc:
        print(f"FATAL: {exc}")
        return 1
    finally:
        conn.close()

    total_elapsed = format_elapsed(time.time() - overall_start)
    print()
    print("=" * 70)
    print(f"ALL STEPS COMPLETE. Total elapsed: {total_elapsed}")
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()
    print("Next: spot-check HS_Rankings for a few seasons/weeks in this range,")
    print("then run .\\run_update_cycle.ps1 to publish.")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())

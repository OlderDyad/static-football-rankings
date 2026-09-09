#!/usr/bin/env python3
"""
game_count_anomaly_scanner.py

Wraps the existing dbo.FindSuspiciousGameCounts stored proc and turns its
output into tracked investigations instead of a one-off query result you
have to eyeball and remember.

Why era buckets: FindSuspiciousGameCounts computes ONE average/stdev of
games-per-season across whatever season range you give it. A flat range
like 1877-2025 dilutes that statistic badly -- a 1920s 8-man team playing
a lean 8-game season and a 2020s 11-man team on a deep playoff run get
judged against the same bar, which risks both false positives (a real
long playoff run flagged) and false negatives (an era-typical anomaly
washed out by the wide variance). This script instead calls the proc once
per (state, era bucket) and treats each bucket's statistics as its own
distribution. Default buckets follow real structural shifts in the data:
pre-1960 (minimal/no deep playoff systems), 1960-1999 (playoff systems
established but pre-internet), 2000-2025 (MaxPreps era, deep playoff
brackets common) -- override with --eras if you want finer/coarser cuts.

Every HIGHLY_SUSPICIOUS / SUSPICIOUS row that comes back gets registered
into HS_Mapping_Investigations under ConflictType='GameCountAnomaly' (new
investigation type, added to the queue/dashboard/defer/dismiss commands
in mapping_conflict_audit.py alongside GhostTeam / DuplicateImport /
AliasReclassification). Registration is idempotent -- rerunning the scan
won't create duplicate investigations for a (team, state, season) already
on file. This script never modifies HS_Scores itself; it only flags
candidates for the same manual review workflow every other investigation
type already goes through (mapping_conflict_audit.py queue / dashboard).

Usage:
  python game_count_anomaly_scanner.py --state OK                                  # scan OK across default era buckets, dry-run
  python game_count_anomaly_scanner.py --state OK --apply                          # actually register the investigations
  python game_count_anomaly_scanner.py --state OK --min-suspicion INVESTIGATE      # also register the lower-confidence tier
  python game_count_anomaly_scanner.py --state TX --eras 1877-1959,1960-1999,2000-2025 --apply
"""

import argparse
import logging

import pyodbc
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
CONN_STR = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;'
db_connection_str = f'mssql+pyodbc://{SERVER_NAME}/{DATABASE_NAME}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes'
engine = create_engine(db_connection_str)

DEFAULT_ERA_BUCKETS = [(1877, 1959), (1960, 1999), (2000, 2025)]
SUSPICION_ORDER = ['NORMAL', 'INVESTIGATE', 'SUSPICIOUS', 'HIGHLY_SUSPICIOUS']


def parse_eras(eras_str):
    buckets = []
    for part in eras_str.split(','):
        start, end = part.split('-')
        buckets.append((int(start), int(end)))
    return buckets


def run_proc(state, start_season, end_season, min_game_count=14):
    """Calls FindSuspiciousGameCounts with @IncludeStatistics=1 and returns
    the detail rows (first result set) as a list of dicts. Uses raw pyodbc
    because the proc returns two result sets and pandas.read_sql only
    captures the first cleanly via a direct SELECT, not a multi-result-set
    EXEC."""
    with pyodbc.connect(CONN_STR) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "EXEC dbo.FindSuspiciousGameCounts @StartSeason=?, @EndSeason=?, @StateFilter=?, @MinGameCount=?, @IncludeStatistics=1",
            start_season, end_season, state, min_game_count
        )
        columns = [c[0] for c in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return rows


def get_existing_anchors(state):
    """(AnchorTeam, Season) pairs already registered under GameCountAnomaly
    for this state, so reruns don't create duplicate investigations."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT AnchorTeam, Season FROM HS_Mapping_Investigations
            WHERE State = :state AND ConflictType = 'GameCountAnomaly'
        """), {'state': state})
        return set((r.AnchorTeam, r.Season) for r in result)


def register(state, candidates, dry_run=True):
    existing = get_existing_anchors(state)
    to_insert = [c for c in candidates if (c['TeamName'], c['Season']) not in existing]
    skipped = len(candidates) - len(to_insert)

    if dry_run:
        for c in to_insert:
            logger.info(f"[DRY RUN] Would register: {c['TeamName']} / {c['Season']} "
                        f"[{c['SuspicionLevel']}] GameCount={c['GameCount']} "
                        f"(era avg={c['LeagueAvgGamesPerSeason']:.1f}, "
                        f"{c['StandardDeviationsAboveAvg']} stdevs above)")
        return len(to_insert), skipped

    with engine.begin() as conn:
        for c in to_insert:
            notes = (f"GameCountAnomaly scan: {c['GameCount']} games in season {c['Season']} vs. "
                     f"era-bucket average {c['LeagueAvgGamesPerSeason']:.1f} "
                     f"(stdev {c['StandardDeviationsAboveAvg']}), analysis period "
                     f"{c['AnalysisPeriodStart']}-{c['AnalysisPeriodEnd']}, threshold {c['ThresholdUsed']}.")
            conn.execute(text("""
                INSERT INTO HS_Mapping_Investigations
                    (AnchorTeam, State, Season, ConflictType, Status, Priority, Notes)
                VALUES (:team, :state, :season, 'GameCountAnomaly', 'New', :priority, :notes)
            """), {'team': c['TeamName'], 'state': state, 'season': c['Season'],
                   'priority': c['SuspicionLevel'], 'notes': notes})
    return len(to_insert), skipped


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--state', required=True, help="2-letter state code, e.g. OK")
    parser.add_argument('--eras', default=None,
                         help="Comma-separated START-END season buckets, e.g. '1877-1959,1960-1999,2000-2025'. "
                              "Defaults to those three buckets if omitted.")
    parser.add_argument('--min-game-count', type=int, default=14, help="Passed through to FindSuspiciousGameCounts (default 14)")
    parser.add_argument('--min-suspicion', default='SUSPICIOUS', choices=SUSPICION_ORDER,
                         help="Lowest SuspicionLevel to register (default SUSPICIOUS -- excludes plain INVESTIGATE)")
    parser.add_argument('--apply', action='store_true', help="Actually register investigations (default is dry-run/review only)")
    args = parser.parse_args()

    state_code = args.state.strip().strip('()').upper()  # e.g. 'OK' -- what FindSuspiciousGameCounts' @StateFilter expects
    state_db = f"({state_code})"  # e.g. '(OK)' -- the format HS_Mapping_Investigations.State is stored in everywhere else
    eras = parse_eras(args.eras) if args.eras else DEFAULT_ERA_BUCKETS
    min_rank = SUSPICION_ORDER.index(args.min_suspicion)

    total_found = 0
    total_registered = 0
    total_skipped = 0

    for start, end in eras:
        logger.info(f"Scanning {state_code} {start}-{end}...")
        rows = run_proc(state_code, start, end, args.min_game_count)
        candidates = [r for r in rows if SUSPICION_ORDER.index(r['SuspicionLevel']) >= min_rank]
        total_found += len(candidates)

        if not candidates:
            logger.info(f"  {state_code} {start}-{end}: no candidates at or above {args.min_suspicion}.")
            continue

        registered, skipped = register(state_db, candidates, dry_run=not args.apply)
        total_registered += registered
        total_skipped += skipped
        logger.info(f"  {state_code} {start}-{end}: {len(candidates)} candidate(s) "
                    f"({'would register' if not args.apply else 'registered'} {registered}, "
                    f"{skipped} already on file).")

    print(f"\n=== {'DRY RUN' if not args.apply else 'APPLY'} summary for {state_code} ===")
    print(f"Candidates found (>= {args.min_suspicion}): {total_found}")
    print(f"{'Would register' if not args.apply else 'Registered'}: {total_registered}")
    print(f"Already on file (skipped): {total_skipped}")

    if not args.apply:
        print("\n(Review only -- no investigations created. Re-run with --apply once reviewed, "
              "then use `python mapping_conflict_audit.py queue --state {} --type GameCountAnomaly` to triage.)".format(state_code))
    else:
        print(f"\nTriage with: python mapping_conflict_audit.py queue --state {state_code} --type GameCountAnomaly")


if __name__ == "__main__":
    main()
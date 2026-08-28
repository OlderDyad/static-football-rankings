#!/usr/bin/env python3
"""
mapping_conflict_audit.py

Finds teams that appear to play two different opponents on the same date
(or within 2 days) -- the signature of a bad HS_Team_Name_Alias mapping
("ghost team") -- registers them into a persistent investigation queue,
tracks investigation status per case, and applies confirmed fixes to
HS_Scores with a full before/after audit trail in HS_Scores_Change_Log.

Only "reliable-date" sources are considered: newspapers.com clippings,
source filenames with an embedded YYYY_MM_DD date (e.g.
The_Daily_Oklahoman_1970_12_05_25.csv), or Season >= 2003 (maxpreps era).
Same-opponent duplicate/typo pairs (two papers covering the same real
game with a slightly different score) are deliberately NOT flagged here
-- that's a separate dedup problem, not a mapping problem.

Detection logic distinguishes three priorities per (AnchorTeam, Season):
  High - same game, wrong opponent name   : a pair with an IDENTICAL score
                                             for the anchor team -- one real
                                             game, opponent name garbled/
                                             mismatched between sources.
  High - true same-day conflict           : a pair on the exact same date
                                             with DIFFERENT scores -- two
                                             genuinely different games
                                             claimed for one team in one day.
  Low  - possible multi-level scheduling  : pairs 1-2 days apart with
                                             different scores -- usually a
                                             big program's freshman/JV/
                                             varsity games in the same week,
                                             not a real mapping error. Worth
                                             a batch spot-check, not
                                             one-by-one review.

Schema (auto-created on first run, see ensure_schema()):
  HS_Mapping_Investigations       -- one row per (AnchorTeam, State, Season)
  HS_Mapping_Investigation_Games  -- links investigations to HS_Scores.ID
  HS_Scores_Change_Log            -- audit trail: every field change made
                                      to any HS_Scores row via apply_fix(),
                                      keyed to the game ID, with old/new
                                      value, reason, and which investigation
                                      justified it.

Usage
-----
python mapping_conflict_audit.py detect --state OK
python mapping_conflict_audit.py detect --state OK --dry-run

python mapping_conflict_audit.py dashboard
python mapping_conflict_audit.py dashboard --state OK

python mapping_conflict_audit.py queue --state OK --priority high
python mapping_conflict_audit.py queue --state OK --investigation 73

python mapping_conflict_audit.py fix --id 13AA058C-853E-4722-9232-5FF428FD4B79 \\
    --field Visitor --value "Amarillo San Jacinto Christian Academy (TX)" \\
    --investigation 73 --reason "Confirmed via 1961 Tulsa World clipping"

python mapping_conflict_audit.py dismiss --investigation 658 \\
    --status "Verified-FalsePositive" --reason "Mustang HS multi-squad program, freshman/JV/varsity vs different opponents same week"

python mapping_conflict_audit.py close --investigation 73 --status Fixed \\
    --reason "Renamed Visitor to Amarillo San Jacinto Christian Academy (TX) on the 2003-09-13 row"
"""

import os
import argparse
import logging
import pandas as pd
import pyodbc
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

db_connection_str = f'mssql+pyodbc://{SERVER_NAME}/{DATABASE_NAME}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes'
engine = create_engine(db_connection_str)

VALID_FIELDS = {'Home', 'Visitor', 'Home_Score', 'Visitor_Score', 'Date',
                 'Season', 'Location', 'Location2', 'Source', 'Forfeit', 'OT'}

DDL_STATEMENTS = [
    """
    IF OBJECT_ID('dbo.HS_Mapping_Investigations', 'U') IS NULL
    CREATE TABLE HS_Mapping_Investigations (
        InvestigationID INT IDENTITY(1,1) PRIMARY KEY,
        AnchorTeam VARCHAR(100) NOT NULL,
        State VARCHAR(10) NOT NULL,
        Season INT NOT NULL,
        DateIdentified DATETIME DEFAULT GETDATE(),
        Status VARCHAR(30) NOT NULL DEFAULT 'New',
        MinDaysApart INT NULL,
        ScoreMatchFlag BIT NULL,
        Priority VARCHAR(60) NULL,
        GhostTeamCandidate VARCHAR(100) NULL,
        ProbableCorrectOpponent VARCHAR(100) NULL,
        VerificationSource VARCHAR(255) NULL,
        Notes VARCHAR(MAX) NULL,
        FixedDate DATETIME NULL
    )
    """,
    """
    IF OBJECT_ID('dbo.HS_Mapping_Investigation_Games', 'U') IS NULL
    CREATE TABLE HS_Mapping_Investigation_Games (
        InvestigationID INT NOT NULL FOREIGN KEY REFERENCES HS_Mapping_Investigations(InvestigationID),
        ScoresID UNIQUEIDENTIFIER NOT NULL,
        PRIMARY KEY (InvestigationID, ScoresID)
    )
    """,
    """
    IF OBJECT_ID('dbo.HS_Scores_Change_Log', 'U') IS NULL
    CREATE TABLE HS_Scores_Change_Log (
        LogID INT IDENTITY(1,1) PRIMARY KEY,
        ScoresID UNIQUEIDENTIFIER NOT NULL,
        InvestigationID INT NULL,
        FieldChanged VARCHAR(50) NOT NULL,
        OldValue VARCHAR(255) NULL,
        NewValue VARCHAR(255) NULL,
        ChangedAt DATETIME DEFAULT GETDATE(),
        ChangedBy VARCHAR(100) NULL DEFAULT SUSER_SNAME(),
        Reason VARCHAR(MAX) NULL,
        Script VARCHAR(100) NULL
    )
    """,
    # column guards, in case the tables were created by hand in SSMS before
    # this script existed and are missing a column added later
    "IF COL_LENGTH('HS_Mapping_Investigations', 'MinDaysApart') IS NULL ALTER TABLE HS_Mapping_Investigations ADD MinDaysApart INT NULL",
    "IF COL_LENGTH('HS_Mapping_Investigations', 'ScoreMatchFlag') IS NULL ALTER TABLE HS_Mapping_Investigations ADD ScoreMatchFlag BIT NULL",
    "IF COL_LENGTH('HS_Mapping_Investigations', 'Priority') IS NULL ALTER TABLE HS_Mapping_Investigations ADD Priority VARCHAR(60) NULL",
]


def ensure_schema():
    """Idempotently creates the three tracking tables if they don't exist yet."""
    conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;'
    with pyodbc.connect(conn_str, autocommit=True) as conn:
        with conn.cursor() as cursor:
            for stmt in DDL_STATEMENTS:
                cursor.execute(stmt)
    logger.info("Schema check complete (tables created if they didn't already exist).")


def normalize_state(state):
    """Accepts 'OK' or '(OK)' -- always returns '(OK)'."""
    return f"({state.strip().strip('()').upper()})"


# --- Detection ---------------------------------------------------------

def fetch_reliable_games(state):
    """Every (Team, Opponent, Date, Score, Source) row for the given state,
    restricted to reliable-date sources: newspapers.com, a source filename
    with an embedded YYYY_MM_DD date, or Season >= 2003 (maxpreps era)."""
    query = text("""
        SELECT ID, Season, Date, Home AS Team, Visitor AS Opponent,
               Home_Score AS TeamScore, Visitor_Score AS OppScore, Source
        FROM HS_Scores WHERE Home LIKE :pattern
        UNION ALL
        SELECT ID, Season, Date, Visitor AS Team, Home AS Opponent,
               Visitor_Score AS TeamScore, Home_Score AS OppScore, Source
        FROM HS_Scores WHERE Visitor LIKE :pattern
    """)
    df = pd.read_sql(query, engine, params={'pattern': f'%{state}'})
    df['ID'] = df['ID'].astype(str)

    reliable_mask = (
        df['Source'].str.contains('newspapers.com', case=False, na=False)
        | df['Source'].str.contains(r'\d{4}_\d{2}_\d{2}', regex=True, na=False)
        | (df['Season'] >= 2003)
    )
    return df[reliable_mask].copy()


def find_conflicts(reliable_df):
    """Self-joins on (Team, Season) to find pairs of games <=2 days apart
    with a DIFFERENT opponent -- the ghost-team signal. Same-opponent
    pairs (duplicate coverage / score typos) are excluded on purpose."""
    if reliable_df.empty:
        return reliable_df

    pairs = reliable_df.merge(reliable_df, on=['Team', 'Season'], suffixes=('_1', '_2'))
    pairs = pairs[pairs['ID_1'] < pairs['ID_2']]
    pairs['Date_1'] = pd.to_datetime(pairs['Date_1'])
    pairs['Date_2'] = pd.to_datetime(pairs['Date_2'])
    pairs['DaysApart'] = (pairs['Date_1'] - pairs['Date_2']).abs().dt.days
    pairs = pairs[pairs['DaysApart'] <= 2]
    pairs = pairs[pairs['Opponent_1'] != pairs['Opponent_2']]
    return pairs.copy()


def classify_groups(pairs_df):
    """One row per (Team, Season) with MinDaysApart / ScoreMatchFlag / Priority."""
    if pairs_df.empty:
        return pd.DataFrame(columns=['Team', 'Season', 'MinDaysApart', 'ScoreMatch', 'Priority'])

    pairs_df = pairs_df.assign(ScoreMatch=pairs_df['TeamScore_1'] == pairs_df['TeamScore_2'])
    grouped = pairs_df.groupby(['Team', 'Season']).agg(
        MinDaysApart=('DaysApart', 'min'),
        ScoreMatch=('ScoreMatch', 'any'),
    ).reset_index()

    def priority(row):
        if row['ScoreMatch']:
            return 'High - same game, wrong opponent name'
        if row['MinDaysApart'] == 0:
            return 'High - true same-day conflict'
        return 'Low - possible multi-level scheduling, spot-check only'

    grouped['Priority'] = grouped.apply(priority, axis=1)
    return grouped


def register_investigations(pairs_df, groups_df, state, dry_run=False):
    """Idempotently inserts new (AnchorTeam, State, Season) investigations,
    refreshes classification for ALL matching investigations (so a case's
    priority stays accurate as new import batches add more games), and
    links every conflicting HS_Scores row to its investigation."""
    if groups_df.empty:
        logger.info(f"{state}: no conflicts found. Nothing to register.")
        return

    existing = pd.read_sql(
        text("SELECT InvestigationID, AnchorTeam, Season FROM HS_Mapping_Investigations WHERE State = :state"),
        engine, params={'state': state}
    )
    existing_keys = set(zip(existing['AnchorTeam'], existing['Season']))
    new_anchors = groups_df[~groups_df.apply(lambda r: (r['Team'], r['Season']) in existing_keys, axis=1)]

    if dry_run:
        logger.info(f"[DRY RUN] {state}: would register {len(new_anchors)} new investigation(s), "
                    f"refresh classification on {len(groups_df)} total case(s), "
                    f"and link up to {len(pairs_df) * 2} game row(s).")
        return

    with engine.begin() as conn:
        for _, row in new_anchors.iterrows():
            conn.execute(text("""
                INSERT INTO HS_Mapping_Investigations (AnchorTeam, State, Season)
                VALUES (:team, :state, :season)
            """), {'team': row['Team'], 'state': state, 'season': int(row['Season'])})

        for _, row in groups_df.iterrows():
            conn.execute(text("""
                UPDATE HS_Mapping_Investigations
                SET MinDaysApart = :mind, ScoreMatchFlag = :smatch, Priority = :priority
                WHERE AnchorTeam = :team AND Season = :season AND State = :state
            """), {'mind': int(row['MinDaysApart']), 'smatch': bool(row['ScoreMatch']),
                   'priority': row['Priority'], 'team': row['Team'],
                   'season': int(row['Season']), 'state': state})

    logger.info(f"{state}: {len(new_anchors)} new investigation(s) registered, "
                f"{len(groups_df)} case(s) reclassified.")

    # link games
    inv_map = pd.read_sql(
        text("SELECT InvestigationID, AnchorTeam, Season FROM HS_Mapping_Investigations WHERE State = :state"),
        engine, params={'state': state}
    )
    inv_lookup = {(r.AnchorTeam, r.Season): r.InvestigationID for r in inv_map.itertuples()}

    games_long = pd.concat([
        pairs_df[['Team', 'Season', 'ID_1']].rename(columns={'ID_1': 'ScoresID'}),
        pairs_df[['Team', 'Season', 'ID_2']].rename(columns={'ID_2': 'ScoresID'}),
    ]).drop_duplicates()
    games_long['InvestigationID'] = games_long.apply(lambda r: inv_lookup.get((r['Team'], r['Season'])), axis=1)
    games_long = games_long.dropna(subset=['InvestigationID'])

    existing_links = pd.read_sql(text("""
        SELECT g.InvestigationID, g.ScoresID
        FROM HS_Mapping_Investigation_Games g
        JOIN HS_Mapping_Investigations i ON i.InvestigationID = g.InvestigationID
        WHERE i.State = :state
    """), engine, params={'state': state})
    existing_set = set(zip(existing_links['InvestigationID'], existing_links['ScoresID'].astype(str)))

    new_links = games_long[~games_long.apply(
        lambda r: (r['InvestigationID'], r['ScoresID']) in existing_set, axis=1
    )].drop_duplicates(subset=['InvestigationID', 'ScoresID'])

    if new_links.empty:
        logger.info(f"{state}: no new game links to add.")
        return

    with engine.begin() as conn:
        for _, row in new_links.iterrows():
            conn.execute(text("""
                INSERT INTO HS_Mapping_Investigation_Games (InvestigationID, ScoresID)
                VALUES (:inv, :sid)
            """), {'inv': int(row['InvestigationID']), 'sid': row['ScoresID']})

    logger.info(f"{state}: {len(new_links)} new game link(s) added.")


# --- Fix / change history ----------------------------------------------

def apply_fix(scores_id, field, new_value, investigation_id=None, reason='', dry_run=False):
    """Updates ONE field on ONE HS_Scores row, identified by its ID -- never
    a blanket rename by team name. Logs the old/new value to
    HS_Scores_Change_Log before writing, so every change is traceable back
    to the exact game and the investigation that justified it."""
    if field not in VALID_FIELDS:
        raise ValueError(f"Unrecognized field '{field}'. Must be one of: {sorted(VALID_FIELDS)}")

    with engine.begin() as conn:
        current = conn.execute(text(f"SELECT {field} AS val FROM HS_Scores WHERE ID = :id"),
                                {'id': scores_id}).fetchone()
        if current is None:
            logger.warning(f"No HS_Scores row found for ID {scores_id} -- skipped.")
            return False
        old_value = current.val
        preview = f"{scores_id}: SET {field} = '{new_value}' (was '{old_value}')"

        if str(old_value) == str(new_value):
            logger.info(f"{scores_id}: {field} already '{new_value}' -- no change needed.")
            return False

        if dry_run:
            logger.info(f"[DRY RUN] {preview}")
            return True

        conn.execute(text("""
            INSERT INTO HS_Scores_Change_Log
                (ScoresID, InvestigationID, FieldChanged, OldValue, NewValue, Reason, Script)
            VALUES (:id, :inv, :field, :old, :new, :reason, :script)
        """), {'id': scores_id, 'inv': investigation_id, 'field': field,
               'old': str(old_value), 'new': str(new_value),
               'reason': reason, 'script': 'mapping_conflict_audit.py'})

        conn.execute(text(f"UPDATE HS_Scores SET {field} = :new WHERE ID = :id"),
                     {'new': new_value, 'id': scores_id})

    logger.info(preview + "  [logged to HS_Scores_Change_Log]")
    return True


def close_investigation(investigation_id, status, reason=None):
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE HS_Mapping_Investigations
            SET Status = :status,
                Notes = CASE WHEN :reason IS NOT NULL THEN
                            COALESCE(Notes + CHAR(10), '') + :reason
                        ELSE Notes END,
                FixedDate = CASE WHEN :status = 'Fixed' THEN GETDATE() ELSE FixedDate END
            WHERE InvestigationID = :id
        """), {'status': status, 'reason': reason, 'id': investigation_id})
    logger.info(f"Investigation {investigation_id} -> {status}")


# --- Reporting -----------------------------------------------------------

def show_dashboard(state=None, output=None):
    where = "WHERE State = :state" if state else ""
    params = {'state': state} if state else {}
    df = pd.read_sql(text(f"""
        SELECT State,
               CASE WHEN Season >= 2003 THEN 'Maxpreps era' ELSE 'Newspaper era' END AS Era,
               Priority, Status, COUNT(*) AS Cnt
        FROM HS_Mapping_Investigations
        {where}
        GROUP BY State, CASE WHEN Season >= 2003 THEN 'Maxpreps era' ELSE 'Newspaper era' END, Priority, Status
        ORDER BY State, Era, Priority, Status
    """), engine, params=params)

    if df.empty:
        logger.info("No investigations found.")
        return

    print(df.to_string(index=False))
    if output:
        df.to_csv(output, index=False, encoding='utf-8-sig')
        logger.info(f"Written to {output}")


def get_queue(state, priority=None, status='New', investigation_id=None, limit=20, output=None):
    filters = ["i.State = :state"]
    params = {'state': normalize_state(state)} if state else {}
    if investigation_id:
        filters = ["i.InvestigationID = :inv"]
        params = {'inv': investigation_id}
    else:
        if priority:
            filters.append("i.Priority LIKE :priority")
            params['priority'] = f'%{priority}%'
        if status:
            filters.append("i.Status = :status")
            params['status'] = status

    where = " AND ".join(filters)
    df = pd.read_sql(text(f"""
        SELECT i.InvestigationID, i.AnchorTeam, i.Season, i.Priority, i.Status,
               s.ID AS ScoresID, s.Date, s.Home, s.Home_Score, s.Visitor, s.Visitor_Score, s.Source
        FROM HS_Mapping_Investigations i
        JOIN HS_Mapping_Investigation_Games g ON g.InvestigationID = i.InvestigationID
        JOIN HS_Scores s ON s.ID = g.ScoresID
        WHERE {where}
        ORDER BY i.InvestigationID, s.Date
    """), engine, params=params)

    if df.empty:
        logger.info("No matching investigations.")
        return

    if not investigation_id:
        capped_ids = df['InvestigationID'].drop_duplicates().head(limit)
        df = df[df['InvestigationID'].isin(capped_ids)]

    for inv_id, grp in df.groupby('InvestigationID', sort=False):
        first = grp.iloc[0]
        print(f"\n=== Investigation {inv_id}: {first['AnchorTeam']} ({first['Season']}) "
              f"[{first['Priority']}] Status={first['Status']} ===")
        for _, r in grp.iterrows():
            print(f"  [{r['ScoresID']}] {r['Date']}: {r['Home']} {r['Home_Score']} - "
                  f"{r['Visitor_Score']} {r['Visitor']}  ({r['Source']})")

    if output:
        df.to_csv(output, index=False, encoding='utf-8-sig')
        logger.info(f"Written to {output}")


# --- CLI -----------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)

    p_detect = sub.add_parser('detect', help='Scan a state for new mapping conflicts and register them.')
    p_detect.add_argument('--state', required=True, help="2-letter code, e.g. OK")
    p_detect.add_argument('--dry-run', action='store_true')

    p_dash = sub.add_parser('dashboard', help='Show investigation counts by era/priority/status.')
    p_dash.add_argument('--state', default=None)
    p_dash.add_argument('--output', default=None)

    p_queue = sub.add_parser('queue', help='List open investigations and their games.')
    p_queue.add_argument('--state', default=None)
    p_queue.add_argument('--priority', default=None, help="Substring match, e.g. 'High'")
    p_queue.add_argument('--status', default='New')
    p_queue.add_argument('--investigation', type=int, default=None)
    p_queue.add_argument('--limit', type=int, default=20)
    p_queue.add_argument('--output', default=None)

    p_fix = sub.add_parser('fix', help='Apply a confirmed fix to one HS_Scores row, with audit logging.')
    p_fix.add_argument('--id', required=True, help="HS_Scores.ID (GUID) of the row to correct")
    p_fix.add_argument('--field', required=True, choices=sorted(VALID_FIELDS))
    p_fix.add_argument('--value', required=True)
    p_fix.add_argument('--investigation', type=int, default=None)
    p_fix.add_argument('--reason', default='')
    p_fix.add_argument('--dry-run', action='store_true')

    p_dismiss = sub.add_parser('dismiss', help='Close an investigation as a false positive (no HS_Scores change).')
    p_dismiss.add_argument('--investigation', type=int, required=True)
    p_dismiss.add_argument('--status', default='Verified-FalsePositive')
    p_dismiss.add_argument('--reason', default=None)

    p_close = sub.add_parser('close', help='Manually set an investigation status/note.')
    p_close.add_argument('--investigation', type=int, required=True)
    p_close.add_argument('--status', required=True)
    p_close.add_argument('--reason', default=None)

    args = parser.parse_args()
    ensure_schema()

    if args.command == 'detect':
        state = normalize_state(args.state)
        logger.info(f"Fetching reliable-date games for {state}...")
        reliable = fetch_reliable_games(state)
        logger.info(f"  {len(reliable)} reliable-source team-game row(s).")
        pairs = find_conflicts(reliable)
        logger.info(f"  {len(pairs)} conflicting pair(s) found.")
        groups = classify_groups(pairs)
        register_investigations(pairs, groups, state, dry_run=args.dry_run)

    elif args.command == 'dashboard':
        state = normalize_state(args.state) if args.state else None
        show_dashboard(state, args.output)

    elif args.command == 'queue':
        get_queue(args.state, args.priority, args.status, args.investigation, args.limit, args.output)

    elif args.command == 'fix':
        apply_fix(args.id, args.field, args.value, args.investigation, args.reason, args.dry_run)

    elif args.command == 'dismiss':
        close_investigation(args.investigation, args.status, args.reason)

    elif args.command == 'close':
        close_investigation(args.investigation, args.status, args.reason)


if __name__ == "__main__":
    main()

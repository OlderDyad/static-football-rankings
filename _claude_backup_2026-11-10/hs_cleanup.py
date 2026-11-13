r"""
hs_cleanup.py - state-by-state HS data cleanup in one place (preview first, --commit second).

Run from python_scripts\data_import (same venv as consolidation_workflow_latin.py):

    python hs_cleanup.py status CO
    python hs_cleanup.py round  CO --reason "CO round 4: town-name aliases"   # consolidate + dedup preview + review-pair preview
    python hs_cleanup.py commit CO                                            # commit the dedup + review pairs just previewed

Let Claude queue commands (leave this running in its own window):
    python hs_cleanup.py watch        (runs *.job files Claude writes to hs_school\_jobs\; logs in _jobs\done\)

Single steps (each previews unless --commit is given):
    python hs_cleanup.py consolidate  CO --reason "..."      (runs the CO_Alias_Rules.csv merges; no preview step)
    python hs_cleanup.py dedup        CO [--commit]
    python hs_cleanup.py review-pairs CO [--commit] [--no-long]
    python hs_cleanup.py report       CO names|drift|same-town|double-booked   (read-only reports)
    python hs_cleanup.py move-team    CO --from "La Jara Centauri (CO)" --to "La Jara (CO)" --seasons 1900-1959 [--commit]
    python hs_cleanup.py same-score-fix CO [--commit]  (double-booked pairs with the same score: archive the wrong-opponent copy)
    python hs_cleanup.py block-dups   CO [--commit]  (results pages imported with one date: archive block rows copied elsewhere)
    python hs_cleanup.py query        CO ault_highland.sql   (read-only .sql file from hs_school/<ST>/queries/; every result set -> CSV)
    python hs_cleanup.py archive-ids  CO --ids file.csv --reason "..." [--commit]   (archive listed games; no kept copy)
    python hs_cleanup.py remap        WY --url "<maxpreps url>" --to "Name (WY)" [--commit]   (point a MaxPreps URL at another name)
    python hs_cleanup.py mapcheck     WY [--commit]   (mapping rows whose Team_ID does not match the ProperName)
    python hs_cleanup.py fix-dates    CO [--commit]   (kept copy has an estimated date, archived copy had a real one)
    python hs_cleanup.py step         CO 1.3 done "note text"         (update the tracker by hand; 'complete' = 'done')

Every result is written to CSV in python_scripts\hs_school\<STATE>\ and summarised on screen,
so nothing has to be copied out of SSMS. Commits update dbo.HS_Cleanup_Status automatically.
"""
import argparse, csv, datetime as dt, os, re, sys
import pyodbc

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_ROOT = os.path.normpath(os.path.join(HERE, '..', 'hs_school'))
SERVER, DB = r"McKnights-PC\SQLEXPRESS01", "hs_football_database"
CONN = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER};DATABASE={DB};Trusted_Connection=yes;"


def connect(autocommit=False):
    return pyodbc.connect(CONN, autocommit=autocommit)


def state_arg(s):
    s = s.upper()
    if not re.fullmatch(r'[A-Z]{2}', s):
        raise argparse.ArgumentTypeError('state must be a 2-letter code, e.g. CO')
    return s


def out_path(state, label):
    d = os.path.join(OUT_ROOT, state)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{state}_{label}_{dt.datetime.now():%Y%m%d_%H%M}.csv")


def run_batch(sql, params=()):
    """Run a multi-statement batch; return every result set as (columns, rows)."""
    sets = []
    with connect(autocommit=True) as cn:
        cur = cn.cursor()
        cur.execute(sql, params)
        while True:
            if cur.description:
                cols = [c[0] for c in cur.description]
                sets.append((cols, [list(r) for r in cur.fetchall()]))
            if not cur.nextset():
                break
    return sets


def save(state, label, cols, rows):
    p = out_path(state, label)
    with open(p, 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        w.writerows(rows)
    return p


def show(cols, rows, limit=15):
    if not rows:
        print('   (no rows)')
        return
    widths = [min(max(len(str(c)), *(len(str(r[i])) for r in rows[:limit])), 40) for i, c in enumerate(cols)]
    fmt = '   ' + '  '.join('{:<%d}' % w for w in widths)
    print(fmt.format(*[str(c)[:40] for c in cols]))
    for r in rows[:limit]:
        print(fmt.format(*[str(v)[:40] for v in r]))
    if len(rows) > limit:
        print(f'   ... {len(rows) - limit} more rows (see CSV)')


# ---------------------------------------------------------------- tracker
def step_update(state, stepno, status=None, runid=None, note=None):
    sql = """
    UPDATE dbo.HS_Cleanup_Status
       SET Status  = COALESCE(?, Status),
           Updated = CAST(GETDATE() AS date),
           RunIDs  = LEFT(CASE WHEN ? IS NULL THEN RunIDs
                               WHEN RunIDs IS NULL THEN ? ELSE RunIDs + '; ' + ? END, 400),
           Notes   = LEFT(CASE WHEN ? IS NULL THEN Notes
                               WHEN Notes IS NULL THEN ? ELSE Notes + ' | ' + ? END, 1000)
     WHERE State = ? AND StepNo = ?"""
    with connect(autocommit=True) as cn:
        n = cn.cursor().execute(sql, status, runid, runid, runid, note, note, note, state, stepno).rowcount
    if n == 0:
        print(f'   (tracker: no row for {state} step {stepno}; run: EXEC dbo.HS_Cleanup_AddState \'{state}\')')


def cmd_status(a):
    cols, rows = run_batch("SELECT StepNo, Step, Status, Updated, RunIDs, Notes FROM dbo.HS_Cleanup_Status WHERE State = ? ORDER BY StepNo", (a.state,))[0]
    show(cols, rows, limit=50)


def cmd_addstate(a):
    run_batch("SET NOCOUNT ON; IF NOT EXISTS (SELECT 1 FROM dbo.HS_Cleanup_Status WHERE State = ?) EXEC dbo.HS_Cleanup_AddState ?; SELECT 1 AS ok", (a.state, a.state))
    print(f'Tracker rows ready for {a.state}')
    cmd_status(a)


def cmd_step(a):
    step_update(a.state, a.stepno, a.status, None, a.note)
    print(f'Tracker updated: {a.state} {a.stepno} -> {a.status}')


# ---------------------------------------------------------------- consolidation
def cmd_consolidate(a):
    sys.path.insert(0, HERE)
    import consolidation_workflow_latin as cw
    path = os.path.join(cw.RULES_FOLDER, f'{a.state}_Alias_Rules.csv')
    print(f'Consolidating {a.state} from {path}')
    cw.run_consolidation_from_staging(f'({a.state})', path, a.reason)
    step_update(a.state, 1.1, None, None, f'consolidation {dt.date.today()}: {a.reason}')


# ---------------------------------------------------------------- dedup v4
def cmd_dedup(a):
    preview = 0 if a.commit else 1
    sets = run_batch("SET NOCOUNT ON; EXEC dbo.RemoveDuplicateGamesParameterized @State = ?, @Preview = ?", (a.state, preview))
    labels = ['dedup_archive', 'dedup_review', 'dedup_summary']
    print(f"\nDEDUP v4 {a.state} - {'COMMIT' if a.commit else 'PREVIEW (nothing changed)'}")
    summary = None
    for i, (cols, rows) in enumerate(sets):
        lab = labels[i] if i < len(labels) else f'dedup_set{i + 1}'
        p = save(a.state, lab + ('_COMMITTED' if a.commit else ''), cols, rows)
        print(f' {lab}: {len(rows)} rows -> {p}')
        if lab == 'dedup_summary':
            summary = (cols, rows)
    if summary:
        show(*summary)
    if a.commit and summary and summary[1]:
        r = dict(zip(summary[0], summary[1][0]))
        step_update(a.state, 2.1, 'done', str(r.get('RunID')), f"{dt.date.today()}: {r.get('DuplicatesToArchive')} archived")
    return summary


# ---------------------------------------------------------------- review-only pairs
REVIEW_SQL = r"""
SET NOCOUNT ON;
DECLARE @Commit bit = ?, @IncludeLongGap bit = ?, @Pat varchar(10) = ?;
DECLARE @RunID uniqueidentifier = NEWID(), @RunAt datetime = GETDATE();
DECLARE @RunParams varchar(400) = ?;

IF OBJECT_ID('tempdb..#rp_g') IS NOT NULL DROP TABLE #rp_g;
SELECT s.ID, s.Season, s.[Date], s.Home, s.Visitor, s.Home_Score, s.Visitor_Score, s.Source, s.Access_ID, s.Location, s.Date_Added,
       T1 = CASE WHEN s.Home <= s.Visitor THEN s.Home ELSE s.Visitor END,
       T2 = CASE WHEN s.Home <= s.Visitor THEN s.Visitor ELSE s.Home END,
       S1 = CASE WHEN s.Home <= s.Visitor THEN s.Home_Score ELSE s.Visitor_Score END,
       S2 = CASE WHEN s.Home <= s.Visitor THEN s.Visitor_Score ELSE s.Home_Score END,
       SrcRank = CASE WHEN s.Access_ID IS NOT NULL THEN 0
                      WHEN s.Source IS NULL OR s.Source IN ('', 'REF!', '0') THEN 3
                      WHEN s.Source IN ('www.maxpreps.com','[www.maxpreps.com]','[www.maxpreps.com](https://www.maxpreps.com)','MaxPreps')
                        OR s.Source LIKE '%classmates%' OR s.Source LIKE '%e-yearbook%' OR s.Source LIKE '%cebyrd%'
                        OR s.Source = 'Mr. Dan R Ford Sr' OR s.Source LIKE '%azfootballarchives%' OR s.Source LIKE '%footballhistory%' OR s.Source LIKE '%lonestarfootball%' OR s.Source LIKE '%digital.libraries.psu.edu%' THEN 2
                      ELSE 1 END
INTO #rp_g
FROM dbo.HS_Scores s
WHERE (RTRIM(s.Home) LIKE @Pat OR RTRIM(s.Visitor) LIKE @Pat)
  AND s.Home_Score IS NOT NULL AND s.Visitor_Score IS NOT NULL AND s.[Date] IS NOT NULL;

IF OBJECT_ID('tempdb..#rp_p') IS NOT NULL DROP TABLE #rp_p;
;WITH grp AS (SELECT Season, T1, T2, S1, S2, n = COUNT(*) FROM #rp_g GROUP BY Season, T1, T2, S1, S2)
SELECT a.ID AS AID, b.ID AS BID, a.Season, Gap = ABS(DATEDIFF(day, a.[Date], b.[Date])),
       Grp = CASE WHEN a.Season = 2020 AND ABS(DATEDIFF(day, a.[Date], b.[Date])) = 365 THEN 'COVID'
                  WHEN ABS(DATEDIFF(day, a.[Date], b.[Date])) <= 35 THEN 'SHORT' ELSE 'LONG' END
INTO #rp_p
FROM #rp_g a
JOIN #rp_g b ON b.Season = a.Season AND b.T1 = a.T1 AND b.T2 = a.T2 AND b.S1 = a.S1 AND b.S2 = a.S2 AND a.ID < b.ID
JOIN grp g ON g.Season = a.Season AND g.T1 = a.T1 AND g.T2 = a.T2 AND g.S1 = a.S1 AND g.S2 = a.S2 AND g.n = 2
WHERE ABS(DATEDIFF(day, a.[Date], b.[Date])) > CASE WHEN a.Season >= 2004 THEN 1 ELSE 10 END
  AND NOT EXISTS (SELECT 1 FROM dbo.HS_Scores_Not_Duplicate nd WHERE nd.ID IN (a.ID, b.ID));

IF OBJECT_ID('tempdb..#rp_d') IS NOT NULL DROP TABLE #rp_d;
SELECT p.Grp, p.Season, p.Gap,
       KeepID = CASE WHEN p.Grp = 'COVID' THEN CASE WHEN YEAR(a.[Date]) = 2021 THEN a.ID ELSE b.ID END
                     WHEN a.SrcRank < b.SrcRank THEN a.ID WHEN b.SrcRank < a.SrcRank THEN b.ID
                     WHEN a.Location IS NOT NULL AND b.Location IS NULL THEN a.ID WHEN b.Location IS NOT NULL AND a.Location IS NULL THEN b.ID
                     WHEN ISNULL(a.Date_Added,'9999-12-31') <= ISNULL(b.Date_Added,'9999-12-31') THEN a.ID ELSE b.ID END,
       DropID = CAST(NULL AS uniqueidentifier)
INTO #rp_d
FROM #rp_p p JOIN #rp_g a ON a.ID = p.AID JOIN #rp_g b ON b.ID = p.BID
WHERE p.Grp <> 'LONG' OR @IncludeLongGap = 1;
UPDATE d SET DropID = CASE WHEN d.KeepID = p.AID THEN p.BID ELSE p.AID END
FROM #rp_d d JOIN #rp_p p ON d.KeepID IN (p.AID, p.BID);

SELECT d.Grp, d.Season, d.Gap,
       k.[Date] AS Keep_Date, k.Home AS Keep_Home, k.Home_Score AS K_HS, k.Visitor AS Keep_Visitor, k.Visitor_Score AS K_VS, k.Source AS Keep_Source,
       x.[Date] AS Drop_Date, x.Home AS Drop_Home, x.Source AS Drop_Source, d.DropID, d.KeepID
FROM #rp_d d JOIN #rp_g k ON k.ID = d.KeepID JOIN #rp_g x ON x.ID = d.DropID
ORDER BY d.Grp, d.Season, k.Home;

IF @Commit = 1
BEGIN
    DECLARE @n int = (SELECT COUNT(*) FROM #rp_d);
    BEGIN TRY
        BEGIN TRAN;
        INSERT INTO dbo.HS_Scores_Duplicate_Archive
            (RunID, RunAt, RunParams, KeptID, DayGap,
             ID, [Date], Season, Home, Visitor, Neutral, Location, Location2, Line, Future_Game,
             Source, Date_Added, OT, Forfeit, Visitor_Score, Home_Score, Margin, BatchID, Access_ID)
        SELECT @RunID, @RunAt, @RunParams, d.KeepID, d.Gap,
             s.ID, s.[Date], s.Season, s.Home, s.Visitor, s.Neutral, s.Location, s.Location2, s.Line, s.Future_Game,
             s.Source, s.Date_Added, s.OT, s.Forfeit, s.Visitor_Score, s.Home_Score, s.Margin, s.BatchID, s.Access_ID
        FROM #rp_d d JOIN dbo.HS_Scores s ON s.ID = d.DropID;
        IF @@ROWCOUNT <> @n BEGIN ROLLBACK; SELECT Status = 'ROLLED BACK', Archived = 0, RunID = NULL, Err = 'archive count mismatch'; RETURN; END

        INSERT INTO dbo.HS_Scores_Change_Log (ScoresID, InvestigationID, FieldChanged, OldValue, NewValue, Reason, Script)
        SELECT s.ID, NULL, 'ROW_DELETED',
               LEFT(CONCAT('Season=', s.Season, ', Date=', CONVERT(varchar(10), s.[Date], 120), ', Home=''', s.Home, ''', Home_Score=', s.Home_Score,
                           ', Visitor=''', s.Visitor, ''', Visitor_Score=', s.Visitor_Score, ', Source=''', ISNULL(s.Source, ''), ''''), 255),
               NULL, LEFT(CONCAT(@RunParams, ' Grp=', d.Grp, ' RunID=', @RunID, ' -- kept ', d.KeepID), 255), 'hs_cleanup.py review-pairs'
        FROM #rp_d d JOIN dbo.HS_Scores s ON s.ID = d.DropID;

        DELETE s FROM dbo.HS_Scores s JOIN #rp_d d ON d.DropID = s.ID;
        IF @@ROWCOUNT <> @n BEGIN ROLLBACK; SELECT Status = 'ROLLED BACK', Archived = 0, RunID = NULL, Err = 'delete count mismatch'; RETURN; END
        COMMIT;
        SELECT Status = 'COMMITTED', Archived = @n, RunID = @RunID, Err = NULL;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK;
        SELECT Status = 'ROLLED BACK', Archived = 0, RunID = NULL, Err = ERROR_MESSAGE();
    END CATCH
END
"""


def cmd_review(a):
    params = (1 if a.commit else 0, 0 if a.no_long else 1, f'%({a.state})',
              f'{a.state} review-only pairs {dt.date.today()}: same season/teams/score, dates beyond the dedup window')
    sets = run_batch(REVIEW_SQL, params)
    cols, rows = sets[0]
    p = save(a.state, 'review_pairs' + ('_COMMITTED' if a.commit else ''), cols, rows)
    groups = {}
    for r in rows:
        groups[r[0]] = groups.get(r[0], 0) + 1
    print(f"\nREVIEW-ONLY PAIRS {a.state} - {'COMMIT' if a.commit else 'PREVIEW (nothing changed)'}")
    print(f' {len(rows)} pairs {groups} -> {p}')
    if a.commit and len(sets) > 1:
        show(*sets[1])
        st = dict(zip(sets[1][0], sets[1][1][0]))
        if st.get('Status') == 'COMMITTED':
            step_update(a.state, 2.2, 'done', str(st['RunID']), f"{dt.date.today()}: {st['Archived']} archived {groups}")
    return rows


# ---------------------------------------------------------------- reports (read-only)
REPORTS = {
'names': r"""
SET NOCOUNT ON;
;WITH N AS (
    SELECT Name, COUNT(*) AS Games, MIN(Season) AS FirstSeason, MAX(Season) AS LastSeason
    FROM (SELECT Home AS Name, Season FROM dbo.HS_Scores WHERE Home LIKE ?
          UNION ALL SELECT Visitor, Season FROM dbo.HS_Scores WHERE Visitor LIKE ?) x
    GROUP BY Name)
SELECT N.*, InTeamNames = CASE WHEN t.ID IS NULL THEN 0 ELSE 1 END,
       Mapped = CASE WHEN EXISTS (SELECT 1 FROM dbo.URL_ProperName_Mapping u WHERE u.Team_ID = t.ID) THEN 1 ELSE 0 END
FROM N LEFT JOIN dbo.HS_Team_Names t ON t.Team_Name = N.Name
ORDER BY N.Name;""",
'drift': r"""
SET NOCOUNT ON;
;WITH N AS (
    SELECT Name, Games = COUNT(*), F = MIN(Season), L = MAX(Season), Town = LEFT(Name, CHARINDEX(' ', Name + ' ') - 1)
    FROM (SELECT Home AS Name, Season FROM dbo.HS_Scores WHERE RTRIM(Home) LIKE ?
          UNION ALL SELECT Visitor, Season FROM dbo.HS_Scores WHERE RTRIM(Visitor) LIKE ?) x
    WHERE Name NOT LIKE '% JV (%' AND Name NOT LIKE '% B (%' AND Name NOT LIKE '%Frosh%' AND Name NOT LIKE '%Lightweights%'
    GROUP BY Name),
M AS (SELECT DISTINCT t.Team_Name FROM dbo.URL_ProperName_Mapping u JOIN dbo.HS_Team_Names t ON t.ID = u.Team_ID)
SELECT a.Name AS Stopped, a.Games AS S_Games, a.F AS S_First, a.L AS S_Last,
       S_Mapped = CASE WHEN EXISTS (SELECT 1 FROM M WHERE M.Team_Name = a.Name) THEN 1 ELSE 0 END,
       b.Name AS Started, b.Games AS N_Games, b.F AS N_First, b.L AS N_Last,
       N_Mapped = CASE WHEN EXISTS (SELECT 1 FROM M WHERE M.Team_Name = b.Name) THEN 1 ELSE 0 END
FROM N a
LEFT JOIN N b ON b.Town = a.Town AND b.Name <> a.Name AND b.F BETWEEN a.L - 4 AND a.L + 2 AND b.L >= YEAR(GETDATE()) - 2
WHERE a.L BETWEEN YEAR(GETDATE()) - 11 AND YEAR(GETDATE()) - 1 AND a.Games >= 10
ORDER BY a.Town, a.Name;""",
'same-town': r"""
SET NOCOUNT ON;
IF OBJECT_ID('tempdb..#st_g') IS NOT NULL DROP TABLE #st_g;
SELECT Team, Opp, Season, [Date], Town = LEFT(Team, CHARINDEX(' ', Team + ' ') - 1)
INTO #st_g
FROM (SELECT Home AS Team, Visitor AS Opp, Season, [Date] FROM dbo.HS_Scores WHERE RTRIM(Home) LIKE ?
      UNION ALL SELECT Visitor, Home, Season, [Date] FROM dbo.HS_Scores WHERE RTRIM(Visitor) LIKE ?) x
WHERE [Date] IS NOT NULL AND Team NOT LIKE '% JV (%' AND Team NOT LIKE '% B (%' AND Team NOT LIKE '%Frosh%'
  AND Team NOT LIKE '%Lightweights%' AND Team NOT LIKE '%Reserves%' AND Team NOT LIKE '%Alumni%' AND Team NOT LIKE '%Sophs%';
CREATE INDEX ix_st ON #st_g (Season, Opp, Town);
;WITH H AS (SELECT a.Team AS A, b.Team AS B, a.Season FROM #st_g a
            JOIN #st_g b ON b.Season = a.Season AND b.Opp = a.Opp AND b.Town = a.Town AND b.Team > a.Team
                        AND ABS(DATEDIFF(day, a.[Date], b.[Date])) <= 10)
SELECT H.A, H.B, Hits = COUNT(*), Seasons = COUNT(DISTINCT H.Season), FirstSeason = MIN(H.Season), LastSeason = MAX(H.Season),
       A_Games = (SELECT COUNT(*) FROM #st_g g WHERE g.Team = H.A), B_Games = (SELECT COUNT(*) FROM #st_g g WHERE g.Team = H.B)
FROM H GROUP BY H.A, H.B HAVING COUNT(*) >= 2 ORDER BY COUNT(*) DESC;""",
'double-booked': r"""
SET NOCOUNT ON;
IF OBJECT_ID('tempdb..#db_g') IS NOT NULL DROP TABLE #db_g;
SELECT ID, Season, [Date], Team, Opp, TS, OS, Source, BatchID
INTO #db_g
FROM (SELECT ID, Season, [Date], Home AS Team, Visitor AS Opp, Home_Score AS TS, Visitor_Score AS OS, Source, BatchID FROM dbo.HS_Scores WHERE RTRIM(Home) LIKE ?
      UNION ALL
      SELECT ID, Season, [Date], Visitor, Home, Visitor_Score, Home_Score, Source, BatchID FROM dbo.HS_Scores WHERE RTRIM(Visitor) LIKE ?) x
WHERE [Date] IS NOT NULL AND MONTH([Date]) <> 6                                   -- June = placeholder dates
  AND ISNULL(Source, '') NOT IN ('', 'REF!', 'Mr. Dan R Ford Sr')                 -- estimated-date / unknown sources
  AND ISNULL(Source, '') NOT LIKE '%classmates%' AND ISNULL(Source, '') NOT LIKE '%e-yearbook%' AND ISNULL(Source, '') NOT LIKE '%cebyrd%'
  AND Team NOT LIKE '% JV (%' AND Team NOT LIKE '% B (%' AND Team NOT LIKE '%Frosh%' AND Team NOT LIKE '%Lightweights%'
  AND Team NOT LIKE '%Reserves%' AND Team NOT LIKE '%Alumni%' AND Team NOT LIKE '%Sophs%'
  AND Opp NOT LIKE '% JV (%' AND Opp NOT LIKE '% B (%' AND Opp NOT LIKE '%Frosh%' AND Opp NOT LIKE '%Alumni%';
CREATE INDEX ix_db ON #db_g (Team, Season, [Date]);
SELECT Kind = CASE WHEN a.TS = b.TS AND a.OS = b.OS THEN 'SAME SCORE (opponent alias?)'
                   WHEN MONTH(a.[Date]) = 11 AND DAY(a.[Date]) BETWEEN 22 AND 30 THEN 'THANKSGIVING?'
                   ELSE 'DIFFERENT GAMES' END,
       a.Team, a.Season, Gap = ABS(DATEDIFF(day, a.[Date], b.[Date])),
       A_Date = a.[Date], A_Opp = a.Opp, A_Score = CONCAT(a.TS, '-', a.OS), A_Source = a.Source, A_Batch = a.BatchID,
       B_Date = b.[Date], B_Opp = b.Opp, B_Score = CONCAT(b.TS, '-', b.OS), B_Source = b.Source, B_Batch = b.BatchID,
       A_ID = a.ID, B_ID = b.ID
FROM #db_g a
JOIN #db_g b ON b.Team = a.Team AND b.Season = a.Season AND a.ID < b.ID AND b.Opp <> a.Opp
            AND ABS(DATEDIFF(day, a.[Date], b.[Date])) <= 2
WHERE NOT EXISTS (SELECT 1 FROM dbo.HS_Scores_Not_Duplicate nd WHERE nd.ID IN (a.ID, b.ID))
ORDER BY 1, a.Team, a.Season, a.[Date];""",
}


def cmd_report(a):
    pat = f'%({a.state})'
    sets = run_batch(REPORTS[a.which], (pat, pat))
    cols, rows = sets[-1]
    p = save(a.state, a.which.replace('-', '_'), cols, rows)
    print(f'\nREPORT {a.which} {a.state}: {len(rows)} rows -> {p}')
    show(cols, rows)


# ---------------------------------------------------------------- move a name's games (split one name holding two schools)
MOVE_SQL = r"""
SET NOCOUNT ON;
DECLARE @Commit bit = ?, @From varchar(150) = ?, @To varchar(150) = ?, @S1 int = ?, @S2 int = ?, @Reason varchar(200) = ?;
IF OBJECT_ID('tempdb..#mv') IS NOT NULL DROP TABLE #mv;
SELECT s.ID, s.Season, s.[Date], s.Home, s.Home_Score, s.Visitor, s.Visitor_Score, s.Source,
       Side = CASE WHEN s.Home = @From THEN 'Home' ELSE 'Visitor' END,
       Opp  = CASE WHEN s.Home = @From THEN s.Visitor ELSE s.Home END
INTO #mv
FROM dbo.HS_Scores s
WHERE (s.Home = @From OR s.Visitor = @From) AND s.Season BETWEEN @S1 AND @S2
  AND (NOT EXISTS (SELECT 1 FROM #mv_ids) OR s.ID IN (SELECT ID FROM #mv_ids));

-- 1: the games that would move (TargetHasGame = the new name already has this opponent within 10 days: a duplicate for dedup)
SELECT m.Season, m.[Date], m.Home, m.Home_Score, m.Visitor, m.Visitor_Score, m.Source, m.Side,
       TargetHasGame = CASE WHEN EXISTS (SELECT 1 FROM dbo.HS_Scores t
                                         WHERE t.Season = m.Season AND ABS(DATEDIFF(day, t.[Date], m.[Date])) <= 10
                                           AND ((t.Home = @To AND t.Visitor = m.Opp) OR (t.Visitor = @To AND t.Home = m.Opp))) THEN 1 ELSE 0 END,
       m.ID
FROM #mv m ORDER BY m.Season, m.[Date];

-- 2: both names by season, so the split point can be checked
SELECT Season,
       FromGames = SUM(CASE WHEN Name = @From THEN 1 ELSE 0 END),
       ToGames   = SUM(CASE WHEN Name = @To THEN 1 ELSE 0 END),
       InRange   = CASE WHEN Season BETWEEN @S1 AND @S2 THEN 'move' ELSE '' END
FROM (SELECT Home AS Name, Season FROM dbo.HS_Scores WHERE Home IN (@From, @To)
      UNION ALL SELECT Visitor, Season FROM dbo.HS_Scores WHERE Visitor IN (@From, @To)) x
GROUP BY Season ORDER BY Season;

-- 3: status
DECLARE @n int = (SELECT COUNT(*) FROM #mv);
DECLARE @ToKnown bit = CASE WHEN EXISTS (SELECT 1 FROM dbo.HS_Team_Names WHERE Team_Name = @To) THEN 1 ELSE 0 END;
IF @Commit = 0
    SELECT Status = 'PREVIEW (nothing changed)', Games = @n, ToNameInTeamNames = @ToKnown, Err = NULL;
ELSE IF @ToKnown = 0
    SELECT Status = 'NOT RUN', Games = 0, ToNameInTeamNames = 0, Err = 'target name is not in HS_Team_Names - check the spelling';
ELSE
BEGIN
    BEGIN TRY
        BEGIN TRAN;
        INSERT INTO dbo.HS_Scores_Change_Log (ScoresID, InvestigationID, FieldChanged, OldValue, NewValue, Reason, Script)
        SELECT m.ID, NULL, m.Side, @From, @To, LEFT(@Reason, 255), 'hs_cleanup.py move-team' FROM #mv m;
        UPDATE s SET Home = @To FROM dbo.HS_Scores s JOIN #mv m ON m.ID = s.ID WHERE m.Side = 'Home';
        UPDATE s SET Visitor = @To FROM dbo.HS_Scores s JOIN #mv m ON m.ID = s.ID WHERE m.Side = 'Visitor';
        COMMIT;
        SELECT Status = 'COMMITTED', Games = @n, ToNameInTeamNames = 1, Err = NULL;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK;
        SELECT Status = 'ROLLED BACK', Games = 0, ToNameInTeamNames = @ToKnown, Err = ERROR_MESSAGE();
    END CATCH
END
"""


def cmd_move(a):
    m = re.fullmatch(r'(\d{4})-(\d{4})', a.seasons)
    if not m:
        sys.exit('--seasons must look like 1900-1959')
    s1, s2 = int(m.group(1)), int(m.group(2))
    reason = a.reason or f'{a.state} split: {getattr(a, "from")} -> {a.to} for seasons {s1}-{s2} ({dt.date.today()})'
    pre = "SET NOCOUNT ON;\nIF OBJECT_ID('tempdb..#mv_ids') IS NOT NULL DROP TABLE #mv_ids;\nCREATE TABLE #mv_ids (ID uniqueidentifier);\n"
    if a.ids:
        path = a.ids if os.path.isabs(a.ids) else os.path.join(OUT_ROOT, a.state, a.ids)
        g = re.compile(r'^[0-9A-Fa-f-]{36}$')
        with open(path, encoding='utf-8-sig') as fh:
            ids = [r['ID'].strip() for r in csv.DictReader(fh)]
        bad = [i for i in ids if not g.match(i)]
        if bad or not ids:
            sys.exit(f'bad or empty ID list in {path}: {bad[:3]}')
        pre += ''.join(f"INSERT INTO #mv_ids VALUES ('{i}');\n" for i in ids)
        print(f' only the {len(ids)} games listed in {path}')
        reason += f' (games listed in {os.path.basename(path)})'
    sets = run_batch(pre + MOVE_SQL, (1 if a.commit else 0, getattr(a, 'from'), a.to, s1, s2, reason))
    tag = '_COMMITTED' if a.commit else ''
    print(f"\nMOVE {getattr(a, 'from')} -> {a.to}, seasons {s1}-{s2} - {'COMMIT' if a.commit else 'PREVIEW (nothing changed)'}")
    for lab, (cols, rows) in zip(['move_games', 'move_by_season'], sets[:2]):
        print(f' {lab}: {len(rows)} rows -> {save(a.state, lab + tag, cols, rows)}')
    show(*sets[2])
    st = dict(zip(sets[2][0], sets[2][1][0]))
    if st.get('Status') == 'COMMITTED':
        step_update(a.state, 1.4, 'in progress', None, f"{dt.date.today()}: moved {st['Games']} games {getattr(a, 'from')} -> {a.to} ({s1}-{s2})")


# ---------------------------------------------------------------- fix dates (estimated kept copy, dated archived copy)
FIXDATES_SQL = r"""
SET NOCOUNT ON;
DECLARE @Commit bit = ?, @Pat varchar(10) = ?, @Reason varchar(200) = ?, @MinShift int = ?;
IF OBJECT_ID('tempdb..#fd') IS NOT NULL DROP TABLE #fd;
;WITH c AS (
    SELECT KeepID = k.ID, k.Season, OldDate = k.[Date], NewDate = a.[Date], k.Home, k.Home_Score, k.Visitor, k.Visitor_Score,
           KeepSource = k.Source, ArchivedSource = a.Source, ArchiveRunID = a.RunID,
           rn = ROW_NUMBER() OVER (PARTITION BY k.ID ORDER BY a.RunAt DESC, a.[Date])
    FROM dbo.HS_Scores_Duplicate_Archive a
    JOIN dbo.HS_Scores k ON k.ID = a.KeptID
    WHERE (RTRIM(k.Home) LIKE @Pat OR RTRIM(k.Visitor) LIKE @Pat)
      AND a.[Date] IS NOT NULL AND k.[Date] IS NOT NULL AND a.[Date] <> k.[Date]
      AND ABS(DATEDIFF(day, a.[Date], k.[Date])) BETWEEN @MinShift AND 75   -- 1-2 days = newspaper publication date vs the Friday game: keep the Friday
      AND NOT (k.Season = 2020 AND YEAR(k.[Date]) = 2021)
      -- kept copy: estimated-date or unknown source
      AND (ISNULL(k.Source, '') IN ('', 'REF!', 'Mr. Dan R Ford Sr') OR k.Source LIKE '%classmates%' OR k.Source LIKE '%e-yearbook%' OR k.Source LIKE '%cebyrd%' OR k.Source LIKE '%azfootballarchives%' OR k.Source LIKE '%footballhistory%' OR k.Source LIKE '%lonestarfootball%' OR k.Source LIKE '%digital.libraries.psu.edu%')
      -- archived copy: a dated source
      AND ISNULL(a.Source, '') NOT IN ('', 'REF!', 'Mr. Dan R Ford Sr') AND a.Source NOT LIKE '%classmates%' AND a.Source NOT LIKE '%e-yearbook%' AND a.Source NOT LIKE '%cebyrd%' AND a.Source NOT LIKE '%azfootballarchives%' AND a.Source NOT LIKE '%footballhistory%' AND a.Source NOT LIKE '%lonestarfootball%' AND a.Source NOT LIKE '%digital.libraries.psu.edu%'
)
SELECT * INTO #fd FROM c WHERE rn = 1;

SELECT Season, OldDate, NewDate, DayShift = DATEDIFF(day, OldDate, NewDate), Home, Home_Score, Visitor, Visitor_Score,
       KeepSource, ArchivedSource, KeepID, ArchiveRunID
FROM #fd ORDER BY Season, OldDate;

DECLARE @n int = (SELECT COUNT(*) FROM #fd);
IF @Commit = 0
    SELECT Status = 'PREVIEW (nothing changed)', Updated = @n, Err = NULL;
ELSE
BEGIN
    BEGIN TRY
        BEGIN TRAN;
        INSERT INTO dbo.HS_Scores_Change_Log (ScoresID, InvestigationID, FieldChanged, OldValue, NewValue, Reason, Script)
        SELECT f.KeepID, NULL, 'Date', CONVERT(varchar(10), f.OldDate, 120), CONVERT(varchar(10), f.NewDate, 120),
               LEFT(CONCAT(@Reason, ' -- date from archived copy (', f.ArchivedSource, ')'), 255), 'hs_cleanup.py fix-dates'
        FROM #fd f;
        UPDATE s SET [Date] = f.NewDate FROM dbo.HS_Scores s JOIN #fd f ON f.KeepID = s.ID;
        COMMIT;
        SELECT Status = 'COMMITTED', Updated = @n, Err = NULL;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK;
        SELECT Status = 'ROLLED BACK', Updated = 0, Err = ERROR_MESSAGE();
    END CATCH
END
"""


def cmd_fixdates(a):
    reason = f'{a.state} fix-dates {dt.date.today()}: kept copy had an estimated date'
    sets = run_batch(FIXDATES_SQL, (1 if a.commit else 0, f'%({a.state})', reason, a.min_shift))
    cols, rows = sets[0]
    p = save(a.state, 'fix_dates' + ('_COMMITTED' if a.commit else ''), cols, rows)
    print(f"\nFIX DATES {a.state} - {'COMMIT' if a.commit else 'PREVIEW (nothing changed)'}")
    print(f' {len(rows)} games -> {p}')
    show(cols, rows, limit=10)
    show(*sets[1])
    st = dict(zip(sets[1][0], sets[1][1][0]))
    if st.get('Status') == 'COMMITTED':
        step_update(a.state, 2.2, None, None, f"{dt.date.today()}: fix-dates {st['Updated']} kept rows given the archived copy's date")


# ---------------------------------------------------------------- same-score double-bookings (one game, two opponent names)
SAMESCORE_SQL = r"""
SET NOCOUNT ON;
DECLARE @Commit bit = ?, @Pat varchar(10) = ?, @RunParams varchar(400) = ?, @Near varchar(200) = ?;
DECLARE @RunID uniqueidentifier = NEWID(), @RunAt datetime = GETDATE();
IF OBJECT_ID('tempdb..#ss_g') IS NOT NULL DROP TABLE #ss_g;
SELECT ID, Season, [Date], Team, Opp, TS, OS, Source
INTO #ss_g
FROM (SELECT ID, Season, [Date], Home AS Team, Visitor AS Opp, Home_Score AS TS, Visitor_Score AS OS, Source FROM dbo.HS_Scores WHERE RTRIM(Home) LIKE @Pat
      UNION ALL
      SELECT ID, Season, [Date], Visitor, Home, Visitor_Score, Home_Score, Source FROM dbo.HS_Scores WHERE RTRIM(Visitor) LIKE @Pat) x
WHERE [Date] IS NOT NULL AND MONTH([Date]) <> 6 AND TS IS NOT NULL AND OS IS NOT NULL
  AND ISNULL(Source, '') NOT IN ('', 'REF!', 'Mr. Dan R Ford Sr')
  AND ISNULL(Source, '') NOT LIKE '%classmates%' AND ISNULL(Source, '') NOT LIKE '%e-yearbook%' AND ISNULL(Source, '') NOT LIKE '%cebyrd%';
CREATE INDEX ix_ss ON #ss_g (Team, Season, [Date]);

IF OBJECT_ID('tempdb..#ss_p') IS NOT NULL DROP TABLE #ss_p;
SELECT a.Team, a.Season, Gap = ABS(DATEDIFF(day, a.[Date], b.[Date])), Score = CONCAT(a.TS, '-', a.OS),
       AID = a.ID, A_Date = a.[Date], A_Opp = a.Opp, A_Source = a.Source,
       BID = b.ID, B_Date = b.[Date], B_Opp = b.Opp, B_Source = b.Source,
       -- Source '0' (an import with no source text; NE 2015-17) misnames opponents: it loses to any real source
       A_Weak = CASE WHEN ISNULL(a.Source, '') = '0' THEN 1 ELSE 0 END, B_Weak = CASE WHEN ISNULL(b.Source, '') = '0' THEN 1 ELSE 0 END,
       -- busy = the opponent has ANOTHER game within 2 days against someone other than this team
       A_OppBusy = CASE WHEN EXISTS (SELECT 1 FROM dbo.HS_Scores s WHERE s.ID NOT IN (a.ID, b.ID) AND s.Season = a.Season
                                     AND ((s.Home = a.Opp AND s.Visitor <> a.Team) OR (s.Visitor = a.Opp AND s.Home <> a.Team))
                                     AND ABS(DATEDIFF(day, s.[Date], a.[Date])) <= 2) THEN 1 ELSE 0 END,
       B_OppBusy = CASE WHEN EXISTS (SELECT 1 FROM dbo.HS_Scores s WHERE s.ID NOT IN (a.ID, b.ID) AND s.Season = b.Season
                                     AND ((s.Home = b.Opp AND s.Visitor <> b.Team) OR (s.Visitor = b.Opp AND s.Home <> b.Team))
                                     AND ABS(DATEDIFF(day, s.[Date], b.[Date])) <= 2) THEN 1 ELSE 0 END,
       -- history: games between this team and each candidate opponent in OTHER seasons (who does the team usually play?)
       A_Hist = (SELECT COUNT(*) FROM dbo.HS_Scores s WHERE s.Season <> a.Season AND ((s.Home = a.Team AND s.Visitor = a.Opp) OR (s.Visitor = a.Team AND s.Home = a.Opp))),
       B_Hist = (SELECT COUNT(*) FROM dbo.HS_Scores s WHERE s.Season <> b.Season AND ((s.Home = b.Team AND s.Visitor = b.Opp) OR (s.Visitor = b.Team AND s.Home = b.Opp))),
       A_OppGames = (SELECT COUNT(*) FROM dbo.HS_Scores s WHERE s.Home = a.Opp OR s.Visitor = a.Opp),
       B_OppGames = (SELECT COUNT(*) FROM dbo.HS_Scores s WHERE s.Home = b.Opp OR s.Visitor = b.Opp),
       -- same-named schools in two states (Sheridan MT/WY, Cody NE/WY, Deer Lodge Powell County MT / Powell WY): prefer the team's own state
       TwinPref = CASE WHEN RIGHT(RTRIM(a.Opp), 4) <> RIGHT(RTRIM(b.Opp), 4)
                        AND (CHARINDEX(LEFT(RTRIM(a.Opp), CASE WHEN LEN(RTRIM(a.Opp)) > 6 THEN LEN(RTRIM(a.Opp)) - 5 ELSE LEN(RTRIM(a.Opp)) END), RTRIM(b.Opp)) > 0
                          OR CHARINDEX(LEFT(RTRIM(b.Opp), CASE WHEN LEN(RTRIM(b.Opp)) > 6 THEN LEN(RTRIM(b.Opp)) - 5 ELSE LEN(RTRIM(b.Opp)) END), RTRIM(a.Opp)) > 0)
                        THEN CASE WHEN RIGHT(RTRIM(a.Opp), 4) = RIGHT(RTRIM(a.Team), 4) THEN 'B'
                                  WHEN RIGHT(RTRIM(b.Opp), 4) = RIGHT(RTRIM(a.Team), 4) THEN 'A' END END,
       A_OppFar = CASE WHEN CHARINDEX(RIGHT(RTRIM(a.Opp), 4), @Near) > 0 THEN 0 ELSE 1 END,
       B_OppFar = CASE WHEN CHARINDEX(RIGHT(RTRIM(b.Opp), 4), @Near) > 0 THEN 0 ELSE 1 END
INTO #ss_p
FROM #ss_g a
JOIN #ss_g b ON b.Team = a.Team AND b.Season = a.Season AND a.ID < b.ID AND b.Opp <> a.Opp
            AND b.TS = a.TS AND b.OS = a.OS AND ABS(DATEDIFF(day, a.[Date], b.[Date])) <= 2
WHERE NOT EXISTS (SELECT 1 FROM dbo.HS_Scores_Not_Duplicate nd WHERE nd.ID IN (a.ID, b.ID));

IF OBJECT_ID('tempdb..#ss_d') IS NOT NULL DROP TABLE #ss_d;
IF OBJECT_ID('tempdb..#ss_q') IS NOT NULL DROP TABLE #ss_q;
SELECT p.*,
       Swapped = CASE WHEN EXISTS (SELECT 1 FROM #ss_p q WHERE q.Team = p.Team AND q.Season = p.Season AND q.AID <> p.AID
                                   AND ((q.A_Opp = p.A_Opp AND q.B_Opp = p.B_Opp) OR (q.A_Opp = p.B_Opp AND q.B_Opp = p.A_Opp))) THEN 1 ELSE 0 END
INTO #ss_q FROM #ss_p p;
SELECT q.*,
       DropSide = CASE WHEN q.Swapped = 1 THEN NULL
                       WHEN q.A_Weak = 1 AND q.B_Weak = 0 THEN 'A'
                       WHEN q.B_Weak = 1 AND q.A_Weak = 0 THEN 'B'
                       -- border twins: a twin with few games is a mislabel (Fort Scott (MO), Lansing (MO)); a twin the team plays every year beats one it never played
                       WHEN q.TwinPref IS NOT NULL AND q.A_OppGames <= 20 AND q.B_OppGames >= 50 THEN 'A'
                       WHEN q.TwinPref IS NOT NULL AND q.B_OppGames <= 20 AND q.A_OppGames >= 50 THEN 'B'
                       WHEN q.TwinPref = 'A' AND q.A_Hist >= 3 AND q.B_Hist = 0 THEN 'B'
                       WHEN q.TwinPref = 'B' AND q.B_Hist >= 3 AND q.A_Hist = 0 THEN 'A'
                       WHEN q.TwinPref IS NOT NULL THEN q.TwinPref
                       WHEN q.A_OppFar = 1 AND q.B_OppFar = 0 THEN 'A'
                       WHEN q.B_OppFar = 1 AND q.A_OppFar = 0 THEN 'B'
                       WHEN q.A_OppGames <= 5 AND q.B_OppGames >= 25 THEN 'A'
                       WHEN q.B_OppGames <= 5 AND q.A_OppGames >= 25 THEN 'B'
                       WHEN q.A_OppBusy = 1 AND q.B_OppBusy = 0 THEN 'A'
                       WHEN q.B_OppBusy = 1 AND q.A_OppBusy = 0 THEN 'B'
                       WHEN q.A_Hist = 0 AND q.B_Hist >= 2 THEN 'A'
                       WHEN q.B_Hist = 0 AND q.A_Hist >= 2 THEN 'B' END,
       Why = CAST(CASE WHEN q.Swapped = 1 THEN 'UNDECIDED - two games with the opponents swapped'
                       WHEN q.A_Weak <> q.B_Weak THEN 'dropped copy has Source 0 (no source; misnames opponents)'
                       WHEN q.TwinPref IS NOT NULL AND ((q.A_OppGames <= 20 AND q.B_OppGames >= 50) OR (q.B_OppGames <= 20 AND q.A_OppGames >= 50)) THEN 'same-named twin: dropped the rare (mislabelled) name'
                       WHEN (q.TwinPref = 'A' AND q.A_Hist >= 3 AND q.B_Hist = 0) OR (q.TwinPref = 'B' AND q.B_Hist >= 3 AND q.A_Hist = 0) THEN 'same-named twin: kept the one the team plays in other seasons'
                       WHEN q.TwinPref IS NOT NULL THEN 'same-named school in another state: kept the one in the team''s state'
                       WHEN q.A_OppFar <> q.B_OppFar THEN 'dropped opponent is from a distant state'
                       WHEN (q.A_OppGames <= 5 AND q.B_OppGames >= 25) OR (q.B_OppGames <= 5 AND q.A_OppGames >= 25) THEN 'dropped opponent name is rare (misspelling?)'
                       WHEN q.A_OppBusy <> q.B_OppBusy THEN 'dropped opponent has its own game that day'
                       WHEN (q.A_Hist = 0 AND q.B_Hist >= 2) OR (q.B_Hist = 0 AND q.A_Hist >= 2) THEN 'team never played the dropped opponent in other seasons'
                       ELSE 'UNDECIDED - Claude/David to choose' END AS varchar(80))
INTO #ss_d FROM #ss_q q;
-- manual decisions (--decisions file): Keep = A / B, or X = leave undecided
UPDATE d SET DropSide = CASE m.Keep WHEN 'A' THEN 'B' WHEN 'B' THEN 'A' END,
             Why = CASE m.Keep WHEN 'X' THEN 'UNDECIDED - manual' ELSE 'manual decision (keep ' + m.Keep + ')' END
FROM #ss_d d JOIN #ss_m m ON m.AID = d.AID AND m.BID = d.BID;
-- a row may not be both kept and dropped: such pairs become undecided
UPDATE d SET DropSide = NULL, Why = 'UNDECIDED - row is kept in another pair'
FROM #ss_d d
WHERE d.DropSide IS NOT NULL
  AND EXISTS (SELECT 1 FROM #ss_d o WHERE o.DropSide IS NOT NULL
              AND (CASE WHEN o.DropSide = 'A' THEN o.BID ELSE o.AID END) = (CASE WHEN d.DropSide = 'A' THEN d.AID ELSE d.BID END));

SELECT Decision = CASE WHEN DropSide IS NULL THEN 'UNDECIDED' ELSE 'DROP ' + DropSide END, Why, Team, Season, Gap, Score,
       A_Date, A_Opp, A_OppBusy, A_OppGames, A_Hist, A_Source, B_Date, B_Opp, B_OppBusy, B_OppGames, B_Hist, B_Source, AID, BID
FROM #ss_d ORDER BY CASE WHEN DropSide IS NULL THEN 1 ELSE 0 END, Team, Season, A_Date;

IF OBJECT_ID('tempdb..#ss_x') IS NOT NULL DROP TABLE #ss_x;
SELECT DropID = CASE WHEN DropSide = 'A' THEN AID ELSE BID END, KeepID = MIN(CASE WHEN DropSide = 'A' THEN BID ELSE AID END), Gap = MIN(Gap)
INTO #ss_x FROM #ss_d WHERE DropSide IS NOT NULL
GROUP BY CASE WHEN DropSide = 'A' THEN AID ELSE BID END;

DECLARE @n int = (SELECT COUNT(*) FROM #ss_x);
IF @Commit = 0
    SELECT Status = 'PREVIEW (nothing changed)', Archived = @n, RunID = NULL, Err = NULL;
ELSE
BEGIN
    BEGIN TRY
        BEGIN TRAN;
        INSERT INTO dbo.HS_Scores_Duplicate_Archive
            (RunID, RunAt, RunParams, KeptID, DayGap,
             ID, [Date], Season, Home, Visitor, Neutral, Location, Location2, Line, Future_Game,
             Source, Date_Added, OT, Forfeit, Visitor_Score, Home_Score, Margin, BatchID, Access_ID)
        SELECT @RunID, @RunAt, @RunParams, x.KeepID, x.Gap,
             s.ID, s.[Date], s.Season, s.Home, s.Visitor, s.Neutral, s.Location, s.Location2, s.Line, s.Future_Game,
             s.Source, s.Date_Added, s.OT, s.Forfeit, s.Visitor_Score, s.Home_Score, s.Margin, s.BatchID, s.Access_ID
        FROM #ss_x x JOIN dbo.HS_Scores s ON s.ID = x.DropID;
        IF @@ROWCOUNT <> @n BEGIN ROLLBACK; SELECT Status = 'ROLLED BACK', Archived = 0, RunID = NULL, Err = 'archive count mismatch'; RETURN; END
        INSERT INTO dbo.HS_Scores_Change_Log (ScoresID, InvestigationID, FieldChanged, OldValue, NewValue, Reason, Script)
        SELECT s.ID, NULL, 'ROW_DELETED',
               LEFT(CONCAT('Season=', s.Season, ', Date=', CONVERT(varchar(10), s.[Date], 120), ', Home=''', s.Home, ''', Home_Score=', s.Home_Score,
                           ', Visitor=''', s.Visitor, ''', Visitor_Score=', s.Visitor_Score, ', Source=''', ISNULL(s.Source, ''), ''''), 255),
               NULL, LEFT(CONCAT(@RunParams, ' RunID=', @RunID, ' -- kept ', x.KeepID), 255), 'hs_cleanup.py same-score-fix'
        FROM #ss_x x JOIN dbo.HS_Scores s ON s.ID = x.DropID;
        DELETE s FROM dbo.HS_Scores s JOIN #ss_x x ON x.DropID = s.ID;
        IF @@ROWCOUNT <> @n BEGIN ROLLBACK; SELECT Status = 'ROLLED BACK', Archived = 0, RunID = NULL, Err = 'delete count mismatch'; RETURN; END
        COMMIT;
        SELECT Status = 'COMMITTED', Archived = @n, RunID = @RunID, Err = NULL;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK;
        SELECT Status = 'ROLLED BACK', Archived = 0, RunID = NULL, Err = ERROR_MESSAGE();
    END CATCH
END
"""


def decisions_sql(path):
    sql = "SET NOCOUNT ON;\nIF OBJECT_ID('tempdb..#ss_m') IS NOT NULL DROP TABLE #ss_m;\nCREATE TABLE #ss_m (AID uniqueidentifier, BID uniqueidentifier, Keep char(1));\n"
    if not path:
        return sql
    g = re.compile(r'^[0-9A-Fa-f-]{36}$')
    n = 0
    with open(path, encoding='utf-8-sig') as fh:
        for r in csv.DictReader(fh):
            aid, bid, keep = r['AID'].strip(), r['BID'].strip(), r['Keep'].strip().upper()
            if not (g.match(aid) and g.match(bid) and keep in ('A', 'B', 'X')):
                sys.exit(f'bad decisions row: {r}')
            sql += f"INSERT INTO #ss_m VALUES ('{aid}', '{bid}', '{keep}');\n"
            n += 1
    print(f' {n} manual decisions from {path}')
    return sql


NEIGHBORS = {  # the state itself plus bordering states: an opponent outside these counts as 'distant'
    'CO': 'CO NM WY UT NE KS OK AZ', 'WY': 'WY MT SD NE CO UT ID', 'NE': 'NE SD IA MO KS CO WY',
    'NM': 'NM CO AZ TX OK UT', 'UT': 'UT ID WY CO NM AZ NV', 'KS': 'KS NE MO OK CO',
    'SD': 'SD ND MN IA NE WY MT', 'MT': 'MT ND SD WY ID', 'ID': 'ID MT WY UT NV OR WA', 'AZ': 'AZ CA NV UT CO NM',
    'MO': 'MO KS NE IA IL KY TN AR OK', 'FL': 'FL GA AL', 'MA': 'MA RI CT NY VT NH', 'IA': 'IA MN SD NE MO IL WI', 'IL': 'IL WI IA MO KY IN',
    'AR': 'AR MO TN MS LA TX OK', 'OK': 'OK KS MO AR TX NM CO', 'TX': 'TX NM OK AR LA', 'NV': 'NV CA OR ID UT AZ',
}


def near_list(state):
    sts = NEIGHBORS.get(state, state).split()
    return ','.join(f'({s})' for s in sts)


def cmd_samescore(a):
    params = (1 if a.commit else 0, f'%({a.state})',
              f'{a.state} same-score double-booking {dt.date.today()}: one game under two opponent names, wrong-opponent copy archived',
              near_list(a.state))
    dec_path = a.decisions or os.path.join(OUT_ROOT, a.state, f'{a.state}_same_score_decisions.csv')
    sets = run_batch(decisions_sql(dec_path if os.path.exists(dec_path) else None) + SAMESCORE_SQL, params)
    cols, rows = sets[0]
    p = save(a.state, 'same_score' + ('_COMMITTED' if a.commit else ''), cols, rows)
    dec = {}
    for r in rows:
        dec[r[0]] = dec.get(r[0], 0) + 1
    print(f"\nSAME-SCORE DOUBLE-BOOKINGS {a.state} - {'COMMIT' if a.commit else 'PREVIEW (nothing changed)'}")
    print(f' {len(rows)} pairs {dec} -> {p}')
    show(*sets[1])
    st = dict(zip(sets[1][0], sets[1][1][0]))
    if st.get('Status') == 'COMMITTED':
        step_update(a.state, 2.3, 'in progress', str(st['RunID']), f"{dt.date.today()}: same-score fix archived {st['Archived']}")


# ---------------------------------------------------------------- one-date source blocks (a results page imported with the paper's date on every game)
BLOCKS_SQL = r"""
SET NOCOUNT ON;
DECLARE @Commit bit = ?, @Pat varchar(10) = ?, @RunParams varchar(400) = ?, @MinRepeat int = ?;
DECLARE @RunID uniqueidentifier = NEWID(), @RunAt datetime = GETDATE();
IF OBJECT_ID('tempdb..#bk_g') IS NOT NULL DROP TABLE #bk_g;
SELECT s.ID, s.Season, s.[Date], s.Home, s.Visitor, s.Home_Score, s.Visitor_Score, Src = ISNULL(s.Source, ''),
       T1 = CASE WHEN s.Home <= s.Visitor THEN s.Home ELSE s.Visitor END,
       T2 = CASE WHEN s.Home <= s.Visitor THEN s.Visitor ELSE s.Home END,
       S1 = CASE WHEN s.Home <= s.Visitor THEN s.Home_Score ELSE s.Visitor_Score END,
       S2 = CASE WHEN s.Home <= s.Visitor THEN s.Visitor_Score ELSE s.Home_Score END
INTO #bk_g
FROM dbo.HS_Scores s
WHERE (RTRIM(s.Home) LIKE @Pat OR RTRIM(s.Visitor) LIKE @Pat) AND s.[Date] IS NOT NULL;
CREATE INDEX ix_bk ON #bk_g (Season, T1, T2);

-- blocks: one Source + Season + Date in which several teams have 2+ games (a multi-week results page given one date).
-- MaxPreps, Ford and yearbooks are never blocks.
IF OBJECT_ID('tempdb..#bk_b') IS NOT NULL DROP TABLE #bk_b;
;WITH tg AS (
    SELECT Src, Season, [Date], Team, n = COUNT(*)
    FROM (SELECT Src, Season, [Date], Team = Home FROM #bk_g UNION ALL SELECT Src, Season, [Date], Visitor FROM #bk_g) t
    WHERE Src NOT IN ('', 'REF!', 'Mr. Dan R Ford Sr') AND Src NOT LIKE '%maxpreps%' AND Src NOT LIKE '%classmates%' AND Src NOT LIKE '%e-yearbook%'
    GROUP BY Src, Season, [Date], Team)
SELECT Src, Season, BDate = [Date], RepeatTeams = SUM(CASE WHEN n >= 2 THEN 1 ELSE 0 END)
INTO #bk_b
FROM tg GROUP BY Src, Season, [Date]
HAVING SUM(CASE WHEN n >= 2 THEN 1 ELSE 0 END) >= @MinRepeat;

-- block rows that have another copy (same season, teams, score) from a different source: the other copy is kept
IF OBJECT_ID('tempdb..#bk_x') IS NOT NULL DROP TABLE #bk_x;
;WITH c AS (
    SELECT DropID = g.ID, KeepID = o.ID, Gap = ABS(DATEDIFF(day, g.[Date], o.[Date])),
           rn = ROW_NUMBER() OVER (PARTITION BY g.ID ORDER BY ABS(DATEDIFF(day, g.[Date], o.[Date])), o.ID)
    FROM #bk_g g
    JOIN #bk_b b ON b.Src = g.Src AND b.Season = g.Season AND b.BDate = g.[Date]
    JOIN #bk_g o ON o.Season = g.Season AND o.T1 = g.T1 AND o.T2 = g.T2 AND o.S1 = g.S1 AND o.S2 = g.S2
                AND o.ID <> g.ID AND o.Src <> g.Src
                AND NOT EXISTS (SELECT 1 FROM #bk_b b2 WHERE b2.Src = o.Src AND b2.Season = o.Season AND b2.BDate = o.[Date])   -- keep a copy from outside any block
    WHERE NOT EXISTS (SELECT 1 FROM dbo.HS_Scores_Not_Duplicate nd WHERE nd.ID IN (g.ID, o.ID))
)
SELECT DropID, KeepID, Gap INTO #bk_x FROM c WHERE rn = 1;

-- 1: the blocks
SELECT b.Src AS Source, b.Season, b.BDate AS BlockDate, b.RepeatTeams,
       Games = (SELECT COUNT(*) FROM #bk_g g WHERE g.Src = b.Src AND g.Season = b.Season AND g.[Date] = b.BDate),
       CopiedElsewhere = (SELECT COUNT(*) FROM #bk_x x JOIN #bk_g g ON g.ID = x.DropID WHERE g.Src = b.Src AND g.Season = b.Season AND g.[Date] = b.BDate)
FROM #bk_b b ORDER BY b.Season, b.Src;

-- 2: the block rows that would be archived, with the copy that is kept
SELECT g.Season, Block_Date = g.[Date], g.Home, g.Home_Score, g.Visitor, g.Visitor_Score, Block_Source = g.Src,
       Keep_Date = k.[Date], Keep_Source = k.Src, x.Gap, x.DropID, x.KeepID
FROM #bk_x x JOIN #bk_g g ON g.ID = x.DropID JOIN #bk_g k ON k.ID = x.KeepID
ORDER BY g.Season, g.Src, g.Home;

DECLARE @n int = (SELECT COUNT(*) FROM #bk_x);
IF @Commit = 0
    SELECT Status = 'PREVIEW (nothing changed)', Archived = @n, RunID = NULL, Err = NULL;
ELSE
BEGIN
    BEGIN TRY
        BEGIN TRAN;
        INSERT INTO dbo.HS_Scores_Duplicate_Archive
            (RunID, RunAt, RunParams, KeptID, DayGap,
             ID, [Date], Season, Home, Visitor, Neutral, Location, Location2, Line, Future_Game,
             Source, Date_Added, OT, Forfeit, Visitor_Score, Home_Score, Margin, BatchID, Access_ID)
        SELECT @RunID, @RunAt, @RunParams, x.KeepID, x.Gap,
             s.ID, s.[Date], s.Season, s.Home, s.Visitor, s.Neutral, s.Location, s.Location2, s.Line, s.Future_Game,
             s.Source, s.Date_Added, s.OT, s.Forfeit, s.Visitor_Score, s.Home_Score, s.Margin, s.BatchID, s.Access_ID
        FROM #bk_x x JOIN dbo.HS_Scores s ON s.ID = x.DropID;
        IF @@ROWCOUNT <> @n BEGIN ROLLBACK; SELECT Status = 'ROLLED BACK', Archived = 0, RunID = NULL, Err = 'archive count mismatch'; RETURN; END
        INSERT INTO dbo.HS_Scores_Change_Log (ScoresID, InvestigationID, FieldChanged, OldValue, NewValue, Reason, Script)
        SELECT s.ID, NULL, 'ROW_DELETED',
               LEFT(CONCAT('Season=', s.Season, ', Date=', CONVERT(varchar(10), s.[Date], 120), ', Home=''', s.Home, ''', Home_Score=', s.Home_Score,
                           ', Visitor=''', s.Visitor, ''', Visitor_Score=', s.Visitor_Score, ', Source=''', ISNULL(s.Source, ''), ''''), 255),
               NULL, LEFT(CONCAT(@RunParams, ' RunID=', @RunID, ' -- kept ', x.KeepID), 255), 'hs_cleanup.py block-dups'
        FROM #bk_x x JOIN dbo.HS_Scores s ON s.ID = x.DropID;
        DELETE s FROM dbo.HS_Scores s JOIN #bk_x x ON x.DropID = s.ID;
        IF @@ROWCOUNT <> @n BEGIN ROLLBACK; SELECT Status = 'ROLLED BACK', Archived = 0, RunID = NULL, Err = 'delete count mismatch'; RETURN; END
        COMMIT;
        SELECT Status = 'COMMITTED', Archived = @n, RunID = @RunID, Err = NULL;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK;
        SELECT Status = 'ROLLED BACK', Archived = 0, RunID = NULL, Err = ERROR_MESSAGE();
    END CATCH
END
"""


def cmd_blocks(a):
    params = (1 if a.commit else 0, f'%({a.state})',
              f'{a.state} one-date source blocks {dt.date.today()}: block copy (paper date on every game) archived, other copy kept',
              a.min_repeat)
    sets = run_batch(BLOCKS_SQL, params)
    tag = '_COMMITTED' if a.commit else ''
    print(f"\nONE-DATE SOURCE BLOCKS {a.state} - {'COMMIT' if a.commit else 'PREVIEW (nothing changed)'}")
    for lab, (cols, rows) in zip(['blocks', 'block_dups'], sets[:2]):
        print(f' {lab}: {len(rows)} rows -> {save(a.state, lab + tag, cols, rows)}')
    show(*sets[0], limit=25)
    show(*sets[2])
    st = dict(zip(sets[2][0], sets[2][1][0]))
    if st.get('Status') == 'COMMITTED':
        step_update(a.state, 2.3, 'in progress', str(st['RunID']), f"{dt.date.today()}: block-dups archived {st['Archived']}")


# ---------------------------------------------------------------- read-only query files (Claude writes them, you run them)
WRITE_WORDS = re.compile(r'\b(INSERT\s+INTO\s+(?!#)|UPDATE\s+(?!#)|DELETE\s|MERGE\s|DROP\s+(?!TABLE\s+#)|ALTER\s|TRUNCATE\s|EXEC|CREATE\s+(?!(TABLE|INDEX)\s+(#|\w+\s+ON\s+#)))', re.I)


def cmd_query(a):
    path = a.file if os.path.isabs(a.file) else os.path.join(OUT_ROOT, a.state, 'queries', a.file)
    sql = open(path, encoding='utf-8-sig').read()
    body = re.sub(r"--[^\n]*|'[^']*'", ' ', sql)          # ignore comments and string literals
    body = re.sub(r"OBJECT_ID\s*\(\s*\)", ' ', body)
    m = WRITE_WORDS.search(body.replace("IF OBJECT_ID(  ) IS NOT NULL DROP TABLE #", ""))
    if m:
        sys.exit(f'refused: {path} contains "{m.group(0).strip()}" - query files must be read-only')
    sets = run_batch('SET NOCOUNT ON;\n' + sql)
    base = os.path.splitext(os.path.basename(path))[0]
    print(f'\nQUERY {base} ({len(sets)} result sets)')
    for i, (cols, rows) in enumerate(sets, 1):
        print(f' set {i}: {len(rows)} rows -> {save(a.state, f"q_{base}_{i}", cols, rows)}')


# ---------------------------------------------------------------- archive listed games (no kept copy: e.g. MaxPreps "TBA Opponent" rows)
ARCHIVE_SQL = r"""
SET NOCOUNT ON;
DECLARE @Commit bit = ?, @RunParams varchar(400) = ?;
DECLARE @RunID uniqueidentifier = NEWID(), @RunAt datetime = GETDATE();
DECLARE @n int = (SELECT COUNT(*) FROM dbo.HS_Scores s JOIN #ar_ids i ON i.ID = s.ID);
DECLARE @listed int = (SELECT COUNT(*) FROM #ar_ids);

SELECT s.Season, s.[Date], s.Home, s.Home_Score, s.Visitor, s.Visitor_Score, s.Source, s.Access_ID, s.ID
FROM dbo.HS_Scores s JOIN #ar_ids i ON i.ID = s.ID ORDER BY s.Season, s.[Date];

IF @Commit = 0
    SELECT Status = 'PREVIEW (nothing changed)', Listed = @listed, Found = @n, RunID = NULL, Err = NULL;
ELSE
BEGIN
    BEGIN TRY
        BEGIN TRAN;
        INSERT INTO dbo.HS_Scores_Duplicate_Archive
            (RunID, RunAt, RunParams, KeptID, DayGap,
             ID, [Date], Season, Home, Visitor, Neutral, Location, Location2, Line, Future_Game,
             Source, Date_Added, OT, Forfeit, Visitor_Score, Home_Score, Margin, BatchID, Access_ID)
        SELECT @RunID, @RunAt, @RunParams, '00000000-0000-0000-0000-000000000000', 0,   -- no kept copy (KeptID is NOT NULL)
             s.ID, s.[Date], s.Season, s.Home, s.Visitor, s.Neutral, s.Location, s.Location2, s.Line, s.Future_Game,
             s.Source, s.Date_Added, s.OT, s.Forfeit, s.Visitor_Score, s.Home_Score, s.Margin, s.BatchID, s.Access_ID
        FROM dbo.HS_Scores s JOIN #ar_ids i ON i.ID = s.ID;
        IF @@ROWCOUNT <> @n BEGIN ROLLBACK; SELECT Status = 'ROLLED BACK', Listed = @listed, Found = @n, RunID = NULL, Err = 'archive count mismatch'; RETURN; END
        INSERT INTO dbo.HS_Scores_Change_Log (ScoresID, InvestigationID, FieldChanged, OldValue, NewValue, Reason, Script)
        SELECT s.ID, NULL, 'ROW_DELETED',
               LEFT(CONCAT('Season=', s.Season, ', Date=', CONVERT(varchar(10), s.[Date], 120), ', Home=''', s.Home, ''', Home_Score=', s.Home_Score,
                           ', Visitor=''', s.Visitor, ''', Visitor_Score=', s.Visitor_Score, ', Source=''', ISNULL(s.Source, ''), ''''), 255),
               NULL, LEFT(CONCAT(@RunParams, ' RunID=', @RunID), 255), 'hs_cleanup.py archive-ids'
        FROM dbo.HS_Scores s JOIN #ar_ids i ON i.ID = s.ID;
        DELETE s FROM dbo.HS_Scores s JOIN #ar_ids i ON i.ID = s.ID;
        IF @@ROWCOUNT <> @n BEGIN ROLLBACK; SELECT Status = 'ROLLED BACK', Listed = @listed, Found = @n, RunID = NULL, Err = 'delete count mismatch'; RETURN; END
        COMMIT;
        SELECT Status = 'COMMITTED', Listed = @listed, Found = @n, RunID = @RunID, Err = NULL;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK;
        SELECT Status = 'ROLLED BACK', Listed = @listed, Found = @n, RunID = NULL, Err = ERROR_MESSAGE();
    END CATCH
END
"""


def read_ids(state, f):
    path = f if os.path.isabs(f) else os.path.join(OUT_ROOT, state, f)
    g = re.compile(r'^[0-9A-Fa-f-]{36}$')
    with open(path, encoding='utf-8-sig') as fh:
        ids = [r['ID'].strip() for r in csv.DictReader(fh)]
    bad = [i for i in ids if not g.match(i)]
    if bad or not ids:
        sys.exit(f'bad or empty ID list in {path}: {bad[:3]}')
    return path, ids


def cmd_archive(a):
    path, ids = read_ids(a.state, a.ids)
    pre = ("SET NOCOUNT ON;\nIF OBJECT_ID('tempdb..#ar_ids') IS NOT NULL DROP TABLE #ar_ids;\nCREATE TABLE #ar_ids (ID uniqueidentifier);\n"
           + ''.join(f"INSERT INTO #ar_ids VALUES ('{i}');\n" for i in ids))
    runparams = f'{a.state} archive-ids {dt.date.today()}: {a.reason} ({os.path.basename(path)})'
    sets = run_batch(pre + ARCHIVE_SQL, (1 if a.commit else 0, runparams[:400]))
    cols, rows = sets[0]
    st0 = dict(zip(sets[1][0], sets[1][1][0])) if len(sets) > 1 and sets[1][1] else {}
    p = save(a.state, 'archive_ids' + ('_COMMITTED' if st0.get('Status') == 'COMMITTED' else ('_FAILED' if a.commit else '')), cols, rows)
    print(f"\nARCHIVE LISTED GAMES {a.state} - {'COMMIT' if a.commit else 'PREVIEW (nothing changed)'}")
    print(f' {len(rows)} games -> {p}')
    show(cols, rows, limit=20)
    show(*sets[1])


# ---------------------------------------------------------------- MaxPreps URL mapping (URL_ProperName_Mapping)
REMAP_SQL = r"""
SET NOCOUNT ON;
DECLARE @Commit bit = ?, @URL varchar(400) = ?, @To varchar(150) = ?;
DECLARE @NewID int = (SELECT TOP 1 ID FROM dbo.HS_Team_Names WHERE Team_Name = @To);
DECLARE @n int = (SELECT COUNT(*) FROM dbo.URL_ProperName_Mapping WHERE URL = @URL);
SELECT u.URL, u.ProperName, u.Team_ID, NewProperName = @To, NewTeam_ID = @NewID FROM dbo.URL_ProperName_Mapping u WHERE u.URL = @URL;
IF @Commit = 0
    SELECT Status = 'PREVIEW (nothing changed)', Rows = @n, Err = CASE WHEN @NewID IS NULL THEN 'target name not in HS_Team_Names' WHEN @n <> 1 THEN 'URL matches ' + CAST(@n AS varchar(5)) + ' rows' END;
ELSE IF @NewID IS NULL OR @n <> 1
    SELECT Status = 'NOT RUN', Rows = 0, Err = CASE WHEN @NewID IS NULL THEN 'target name not in HS_Team_Names' ELSE 'URL matches ' + CAST(@n AS varchar(5)) + ' rows' END;
ELSE
BEGIN
    UPDATE dbo.URL_ProperName_Mapping SET ProperName = @To, Team_ID = @NewID WHERE URL = @URL;
    SELECT Status = 'COMMITTED', Rows = @@ROWCOUNT, Err = NULL;
END
"""

MAPCHECK_SQL = r"""
SET NOCOUNT ON;
DECLARE @Commit bit = ?, @UrlPat varchar(40) = ?, @Pat varchar(10) = ?;
IF OBJECT_ID('tempdb..#mc') IS NOT NULL DROP TABLE #mc;
SELECT u.URL, u.ProperName, u.Team_ID, NameID = t.ID,
       Problem = CASE WHEN t.ID IS NULL THEN 'ProperName not in HS_Team_Names'
                      WHEN u.Team_ID IS NULL THEN 'Team_ID empty'
                      WHEN u.Team_ID <> t.ID THEN 'Team_ID points to another name' END,
       Team_ID_Name = (SELECT TOP 1 x.Team_Name FROM dbo.HS_Team_Names x WHERE x.ID = u.Team_ID)
INTO #mc
FROM dbo.URL_ProperName_Mapping u
LEFT JOIN dbo.HS_Team_Names t ON t.Team_Name = u.ProperName
WHERE (u.URL LIKE @UrlPat OR u.ProperName LIKE @Pat)
  AND (t.ID IS NULL OR u.Team_ID IS NULL OR u.Team_ID <> t.ID);
SELECT * FROM #mc ORDER BY Problem, ProperName;
DECLARE @n int = (SELECT COUNT(*) FROM #mc WHERE NameID IS NOT NULL);
IF @Commit = 0
    SELECT Status = 'PREVIEW (nothing changed)', Fixable = @n, Err = NULL;
ELSE
BEGIN
    UPDATE u SET Team_ID = m.NameID FROM dbo.URL_ProperName_Mapping u JOIN #mc m ON m.URL = u.URL WHERE m.NameID IS NOT NULL;
    SELECT Status = 'COMMITTED', Fixable = @@ROWCOUNT, Err = NULL;
END
"""


def cmd_remap(a):
    sets = run_batch(REMAP_SQL, (1 if a.commit else 0, a.url, a.to))
    print(f"\nREMAP {a.url} -> {a.to} - {'COMMIT' if a.commit else 'PREVIEW (nothing changed)'}")
    show(*sets[0])
    show(*sets[1])


def cmd_mapcheck(a):
    sets = run_batch(MAPCHECK_SQL, (1 if a.commit else 0, f'%maxpreps.com/{a.state.lower()}/%', f'%({a.state})'))
    cols, rows = sets[0]
    p = save(a.state, 'mapcheck' + ('_COMMITTED' if a.commit else ''), cols, rows)
    print(f"\nMAPPING CHECK {a.state} - {'COMMIT (Team_ID set to the ProperName ID)' if a.commit else 'PREVIEW (nothing changed)'}")
    print(f' {len(rows)} rows -> {p}')
    show(cols, rows, limit=20)
    show(*sets[1])


# ---------------------------------------------------------------- job watcher (lets Claude queue hs_cleanup commands)
JOB_DIR = os.path.join(OUT_ROOT, '_jobs')
WATCH_TIMEOUT = 15 * 60   # seconds per command
WATCH_ALLOWED = {'status', 'addstate', 'step', 'consolidate', 'dedup', 'review-pairs', 'report', 'round', 'commit', 'move-team',
                 'archive-ids', 'same-score-fix', 'block-dups', 'fix-dates', 'query', 'remap', 'mapcheck'}


def cmd_watch(a):
    """Poll hs_school/_jobs/ for *.job files. Each line of a job file is one hs_cleanup command (without 'python hs_cleanup.py').
    Lines run in order; output goes to _jobs/done/<job>.log; a failing line stops that job. Only hs_cleanup subcommands
    in WATCH_ALLOWED can run - nothing else."""
    import shlex, subprocess, time, glob as _glob
    done = os.path.join(JOB_DIR, 'done')
    os.makedirs(done, exist_ok=True)
    print(f'Watching {JOB_DIR} for *.job files (Ctrl+C to stop).')
    while True:
        with open(os.path.join(JOB_DIR, 'heartbeat.txt'), 'w') as fh:
            fh.write(dt.datetime.now().isoformat(timespec='seconds'))
        for job in sorted(_glob.glob(os.path.join(JOB_DIR, '*.job'))):
            name = os.path.splitext(os.path.basename(job))[0]
            log_path = os.path.join(done, name + '.log')
            with open(job, encoding='utf-8-sig') as fh:
                lines = [l.strip() for l in fh if l.strip() and not l.strip().startswith('#')]
            os.replace(job, os.path.join(done, name + '.job'))
            print(f'{dt.datetime.now():%H:%M:%S} running {name} ({len(lines)} commands)')
            with open(log_path, 'w', encoding='utf-8') as log:
                status = 'OK'
                for line in lines:
                    args = shlex.split(line, posix=True)
                    # only hs_cleanup subcommands can run (the child's argparse rejects anything else); never a nested watcher
                    if not args or args[0] == 'watch' or args[0].startswith('-'):
                        log.write(f'\n>>> {line}\nREFUSED: not an allowed hs_cleanup command\n')
                        status = 'REFUSED'
                        break
                    log.write(f'\n>>> {line}\n')
                    log.flush()
                    try:
                        r = subprocess.run([sys.executable, os.path.abspath(__file__)] + args, capture_output=True, text=True,
                                           encoding='utf-8', errors='replace', cwd=HERE, timeout=WATCH_TIMEOUT)
                    except subprocess.TimeoutExpired:
                        log.write(f'\nTIMED OUT after {WATCH_TIMEOUT // 60} minutes (a transaction in progress is rolled back)\n')
                        status = 'TIMED OUT'
                        break
                    log.write(r.stdout)
                    if r.stderr:
                        log.write('\n[stderr]\n' + r.stderr)
                    if r.returncode != 0:
                        status = f'FAILED (exit {r.returncode})'
                        break
                log.write(f'\n=== {status} {dt.datetime.now():%Y-%m-%d %H:%M:%S}\n')
            print(f'{dt.datetime.now():%H:%M:%S} {name}: {status}')
        time.sleep(5)


# ---------------------------------------------------------------- one round / commit
def cmd_round(a):
    cmd_consolidate(a)
    a.commit = False
    cmd_dedup(a)
    a.no_long = False
    cmd_review(a)
    print('\nNothing deleted yet. Check the CSVs (or ask Claude to), then run:  python hs_cleanup.py commit', a.state)


def cmd_commit(a):
    a.commit = True
    cmd_dedup(a)
    a.no_long = False
    cmd_review(a)   # after the dedup, so pairs it just removed are not counted twice


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    s = sp.add_parser('status');       s.add_argument('state', type=state_arg); s.set_defaults(f=cmd_status)
    s = sp.add_parser('addstate');     s.add_argument('state', type=state_arg); s.set_defaults(f=cmd_addstate)
    s = sp.add_parser('step');         s.add_argument('state', type=state_arg); s.add_argument('stepno', type=float)
    s.add_argument('status', type=lambda v: {'complete': 'done', 'completed': 'done'}.get(v.lower(), v.lower()),
                   choices=['not started', 'in progress', 'done', 'skipped']); s.add_argument('note', nargs='?'); s.set_defaults(f=cmd_step)
    s = sp.add_parser('consolidate');  s.add_argument('state', type=state_arg); s.add_argument('--reason', required=True); s.set_defaults(f=cmd_consolidate)
    s = sp.add_parser('dedup');        s.add_argument('state', type=state_arg); s.add_argument('--commit', action='store_true'); s.set_defaults(f=cmd_dedup)
    s = sp.add_parser('review-pairs'); s.add_argument('state', type=state_arg); s.add_argument('--commit', action='store_true')
    s.add_argument('--no-long', action='store_true', help='leave pairs 36+ days apart alone'); s.set_defaults(f=cmd_review)
    s = sp.add_parser('report');       s.add_argument('state', type=state_arg); s.add_argument('which', choices=sorted(REPORTS)); s.set_defaults(f=cmd_report)
    s = sp.add_parser('move-team');    s.add_argument('state', type=state_arg); s.add_argument('--from', required=True); s.add_argument('--to', required=True)
    s.add_argument('--seasons', required=True, help='e.g. 1900-1959'); s.add_argument('--reason')
    s.add_argument('--ids', help='CSV with an ID column (in hs_school/<ST>/): move only those games'); s.add_argument('--commit', action='store_true'); s.set_defaults(f=cmd_move)
    s = sp.add_parser('same-score-fix'); s.add_argument('state', type=state_arg); s.add_argument('--commit', action='store_true')
    s.add_argument('--decisions', help='CSV AID,BID,Keep(A/B/X); default hs_school/<ST>/<ST>_same_score_decisions.csv'); s.set_defaults(f=cmd_samescore)
    s = sp.add_parser('block-dups');   s.add_argument('state', type=state_arg); s.add_argument('--commit', action='store_true')
    s.add_argument('--min-repeat', type=int, default=3, help='teams with 2+ games on the block date (default 3)'); s.set_defaults(f=cmd_blocks)
    s = sp.add_parser('query');        s.add_argument('state', type=state_arg); s.add_argument('file', help='a .sql file in hs_school/<ST>/queries/'); s.set_defaults(f=cmd_query)
    s = sp.add_parser('archive-ids');  s.add_argument('state', type=state_arg); s.add_argument('--ids', required=True); s.add_argument('--reason', required=True)
    s.add_argument('--commit', action='store_true'); s.set_defaults(f=cmd_archive)
    s = sp.add_parser('remap');        s.add_argument('state', type=state_arg); s.add_argument('--url', required=True); s.add_argument('--to', required=True)
    s.add_argument('--commit', action='store_true'); s.set_defaults(f=cmd_remap)
    s = sp.add_parser('mapcheck');     s.add_argument('state', type=state_arg); s.add_argument('--commit', action='store_true'); s.set_defaults(f=cmd_mapcheck)
    s = sp.add_parser('watch');        s.set_defaults(f=cmd_watch)
    s = sp.add_parser('fix-dates');    s.add_argument('state', type=state_arg); s.add_argument('--commit', action='store_true')
    s.add_argument('--min-shift', type=int, default=3, help='skip date differences smaller than this (default 3 days)'); s.set_defaults(f=cmd_fixdates)
    s = sp.add_parser('round');        s.add_argument('state', type=state_arg); s.add_argument('--reason', required=True); s.set_defaults(f=cmd_round)
    s = sp.add_parser('commit');       s.add_argument('state', type=state_arg); s.set_defaults(f=cmd_commit)
    a = ap.parse_args()
    a.f(a)


if __name__ == '__main__':
    main()

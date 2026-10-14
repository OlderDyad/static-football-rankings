-- ============================================================================
-- Audit_Past_Dedup_Runs.sql  (read-only)  -- v2, 2026-10-12
--
-- The deployed v3 procedure logged only a 90-character note per deleted game:
--     Season=1925, Date=1925-10-11, Home='X (CO)', Visitor='Y (CO)'
-- (no scores, and long visitor names get cut off). So on its own the log can
-- check dates and states, but NOT who won. If a backup table taken BEFORE the
-- runs still has the deleted rows (same ID), set @BackupTable below and the
-- audit pulls the full rows from it, including scores.
--
-- Flags (each = a deletion v4 rules would NOT have made):
--   OutOfState  neither team is "(XX)" for the state the run was for
--   DateGap     more than 10 days apart (pre-2004) / 1 day (2004+)
--   NoDate      a date is missing on one side
--   KeptGone    the surviving row it was matched to no longer exists
--   WinnerFlip  opposite winner from the kept row (needs the backup)
--   ScoresUnknown  "swapped" deletion with no backup row - winner can't be checked
-- ============================================================================
USE hs_football_database;
SET NOCOUNT ON;

DECLARE @BackupTable SYSNAME = NULL;    -- e.g. N'HS_Scores_Backup_20260905'  (see Result 0)

-- Result 0: backup tables that exist
SELECT t.name AS BackupTable, t.create_date, SUM(p.rows) AS [Rows]
FROM sys.tables t JOIN sys.partitions p ON p.object_id = t.object_id AND p.index_id IN (0, 1)
WHERE t.name LIKE 'HS_Scores%Backup%' OR t.name LIKE 'HS_Scores_Bak%'
GROUP BY t.name, t.create_date ORDER BY t.create_date;

IF OBJECT_ID('tempdb..#Del') IS NOT NULL DROP TABLE #Del;

SELECT
    c.ScoresID,
    CASE WHEN c.Script LIKE '%(swapped)' THEN 'swapped' ELSE 'regular' END AS Pass,
    UPPER(SUBSTRING(c.Reason, CHARINDEX('State=', c.Reason) + 6, 2)) AS RunState,
    LEFT(c.Reason, CHARINDEX(' -- ', c.Reason + ' -- ') - 1) AS RunReason,
    TRY_CONVERT(UNIQUEIDENTIFIER, RIGHT(RTRIM(c.Reason), 36)) AS KeptID,
    TRY_CONVERT(INT, SUBSTRING(c.OldValue, 8, CHARINDEX(',', c.OldValue + ',') - 8)) AS D_Season,
    TRY_CONVERT(DATE, SUBSTRING(c.OldValue, CHARINDEX(', Date=', c.OldValue) + 7, 10)) AS D_Date,
    CASE WHEN CHARINDEX(''', Visitor=''', c.OldValue) > 0
         THEN SUBSTRING(c.OldValue, CHARINDEX(', Home=''', c.OldValue) + 8,
                        CHARINDEX(''', Visitor=''', c.OldValue) - CHARINDEX(', Home=''', c.OldValue) - 8) END AS D_Home,
    CASE WHEN CHARINDEX(''', Visitor=''', c.OldValue) > 0
         THEN REPLACE(SUBSTRING(c.OldValue, CHARINDEX(''', Visitor=''', c.OldValue) + 12, 200), '''', '') END AS D_Visitor,
    CAST(NULL AS INT) AS D_HS, CAST(NULL AS INT) AS D_VS, 0 AS FromBackup
INTO #Del
FROM dbo.HS_Scores_Change_Log c
WHERE c.FieldChanged = 'ROW_DELETED'
  AND c.Script LIKE 'RemoveDuplicateGamesParameterized (%';

-- Fill full rows (incl. scores) from the backup, if one was named
IF @BackupTable IS NOT NULL
BEGIN
    DECLARE @sql NVARCHAR(MAX) = N'
        UPDATE d SET d.D_Date = b.[Date], d.D_Home = b.Home, d.D_Visitor = b.Visitor,
                     d.D_HS = b.Home_Score, d.D_VS = b.Visitor_Score, d.FromBackup = 1
        FROM #Del d JOIN dbo.' + QUOTENAME(@BackupTable) + N' b ON b.ID = d.ScoresID;';
    EXEC sp_executesql @sql;
END

IF OBJECT_ID('tempdb..#Audit') IS NOT NULL DROP TABLE #Audit;

SELECT d.*,
    k.[Date] AS K_Date, k.Home AS K_Home, k.Home_Score AS K_HS, k.Visitor AS K_Visitor, k.Visitor_Score AS K_VS,
    CASE WHEN d.RunState = 'NO' THEN 0
         WHEN d.D_Home LIKE '%(' + d.RunState + ')' OR d.D_Visitor LIKE '%(' + d.RunState + ')%' THEN 0
         WHEN d.D_Home IS NULL THEN 0
         ELSE 1 END AS OutOfState,
    CASE WHEN d.D_Date IS NOT NULL AND k.[Date] IS NOT NULL
          AND ABS(DATEDIFF(DAY, d.D_Date, k.[Date])) > CASE WHEN d.D_Season >= 2004 THEN 1 ELSE 10 END
         THEN 1 ELSE 0 END AS DateGap,
    CASE WHEN k.ID IS NOT NULL AND (d.D_Date IS NULL OR k.[Date] IS NULL) THEN 1 ELSE 0 END AS NoDate,
    CASE WHEN k.ID IS NULL THEN 1 ELSE 0 END AS KeptGone,
    CASE WHEN d.D_HS IS NOT NULL AND k.ID IS NOT NULL
          AND (CASE WHEN d.D_Home = k.Home THEN d.D_HS ELSE d.D_VS END) <> k.Home_Score
         THEN 1 ELSE 0 END AS WinnerFlip,
    CASE WHEN d.Pass = 'swapped' AND d.D_HS IS NULL THEN 1 ELSE 0 END AS ScoresUnknown
INTO #Audit
FROM #Del d LEFT JOIN dbo.HS_Scores k ON k.ID = d.KeptID;

-- Result 1: summary per run
SELECT RunReason, Pass, COUNT(*) AS Deleted, SUM(FromBackup) AS FoundInBackup,
       SUM(OutOfState) AS OutOfState, SUM(DateGap) AS DateGap, SUM(NoDate) AS NoDate,
       SUM(KeptGone) AS KeptGone, SUM(WinnerFlip) AS WinnerFlip, SUM(ScoresUnknown) AS ScoresUnknown,
       SUM(CASE WHEN DateGap + KeptGone + WinnerFlip > 0 THEN 1 ELSE 0 END) AS LikelyWrong
FROM #Audit GROUP BY RunReason, Pass ORDER BY RunReason, Pass;

-- Result 2: deletions most likely wrong (different dates, opposite winner, or partner gone)
SELECT RunState, Pass, DateGap, WinnerFlip, KeptGone, OutOfState, FromBackup,
       D_Season, D_Date, D_Home, D_HS, D_Visitor, D_VS,
       K_Date, K_Home, K_HS, K_Visitor, K_VS, ScoresID, KeptID
FROM #Audit WHERE DateGap + KeptGone + WinnerFlip > 0
ORDER BY RunState, D_Season, D_Home;

DROP TABLE #Audit; DROP TABLE #Del;

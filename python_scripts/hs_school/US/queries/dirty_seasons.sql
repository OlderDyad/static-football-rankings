SET NOCOUNT ON;
-- 0: column names of the logs
SELECT TOP 3 * FROM dbo.HS_Scores_Change_Log ORDER BY 1 DESC;
-- 1: archived rows by season and state since the cleanup started
IF OBJECT_ID('tempdb..#t') IS NOT NULL DROP TABLE #t;
SELECT a.Season, ST = SUBSTRING(RIGHT(RTRIM(a.Home), 4), 2, 2), ST2 = SUBSTRING(RIGHT(RTRIM(a.Visitor), 4), 2, 2), Kind = 'archived'
INTO #t FROM dbo.HS_Scores_Duplicate_Archive a WHERE a.RunAt >= '2026-11-04';
-- moved games (still in HS_Scores)
INSERT INTO #t
SELECT s.Season, SUBSTRING(RIGHT(RTRIM(s.Home), 4), 2, 2), SUBSTRING(RIGHT(RTRIM(s.Visitor), 4), 2, 2), 'moved'
FROM (SELECT DISTINCT ScoresID FROM dbo.HS_Scores_Change_Log WHERE Script = 'hs_cleanup.py move-team') c
JOIN dbo.HS_Scores s ON s.ID = c.ScoresID;
SELECT Season, Kind, Games = COUNT(*),
       CO = SUM(CASE WHEN 'CO' IN (ST, ST2) THEN 1 ELSE 0 END), WY = SUM(CASE WHEN 'WY' IN (ST, ST2) THEN 1 ELSE 0 END),
       NE = SUM(CASE WHEN 'NE' IN (ST, ST2) THEN 1 ELSE 0 END), NM = SUM(CASE WHEN 'NM' IN (ST, ST2) THEN 1 ELSE 0 END),
       UT = SUM(CASE WHEN 'UT' IN (ST, ST2) THEN 1 ELSE 0 END), KS = SUM(CASE WHEN 'KS' IN (ST, ST2) THEN 1 ELSE 0 END)
FROM #t GROUP BY Season, Kind ORDER BY Season, Kind;
-- 2: games per season now (whole table) and in the six states
SELECT Season, AllGames = COUNT(*),
       SixStates = SUM(CASE WHEN SUBSTRING(RIGHT(RTRIM(Home), 4), 2, 2) IN ('CO','WY','NE','NM','UT','KS') OR SUBSTRING(RIGHT(RTRIM(Visitor), 4), 2, 2) IN ('CO','WY','NE','NM','UT','KS') THEN 1 ELSE 0 END)
FROM dbo.HS_Scores GROUP BY Season ORDER BY Season;
-- 3: consolidation log rows since the cleanup started
SELECT TOP 50 * FROM dbo.HS_Consolidation_Log ORDER BY 1 DESC;

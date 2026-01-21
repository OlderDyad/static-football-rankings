USE [hs_football_database]
GO

SET NOCOUNT ON;

PRINT '==============================================================================';
PRINT 'MONITORING SCRIPT FOR CalculateRankings_v5';
PRINT '==============================================================================';
PRINT 'Note: V5 uses the same "RankingsProcessLog" table as V4.';
PRINT 'These queries look for activity in the last 24 hours to track the current run.';
PRINT '==============================================================================';
PRINT '';

-- =============================================================================
-- 1. LIVE STATUS: What is happening RIGHT NOW?
-- =============================================================================
PRINT '1. CURRENT STATUS (Last 5 minutes activity)';
SELECT 
    CASE 
        WHEN COUNT(*) > 0 THEN 'RUNNING'
        ELSE 'IDLE / STUCK'
    END AS [System State],
    MAX(LogTime) AS [Last Log Entry],
    MAX(Season) AS [Current Season],
    (SELECT TOP 1 StepDescription FROM RankingsProcessLog ORDER BY LogTime DESC) AS [Current Step],
    (SELECT TOP 1 Comments FROM RankingsProcessLog ORDER BY LogTime DESC) AS [Latest Info]
FROM RankingsProcessLog
WHERE LogTime >= DATEADD(MINUTE, -5, GETDATE());

-- =============================================================================
-- 2. RECENT ACTIVITY DETAIL
-- Top 20 most recent log entries to see loop progress or errors
-- =============================================================================
PRINT '';
PRINT '2. RECENT LOG ENTRIES (Top 20)';
SELECT TOP 20
    LogTime,
    Season,
    StepDescription,
    RowsProcessed,
    Comments
FROM RankingsProcessLog
ORDER BY LogTime DESC;

-- =============================================================================
-- 3. SEASON PROGRESS REPORT
-- Which seasons have been completed in this run (last 24 hours)?
-- =============================================================================
PRINT '';
PRINT '3. SEASONS PROCESSED (Last 24 Hours)';
WITH SeasonStats AS (
    SELECT 
        Season,
        MIN(LogTime) AS startTime,
        MAX(LogTime) AS endTime,
        MAX(CASE WHEN StepDescription = 'Season Complete' THEN 1 ELSE 0 END) AS isComplete
    FROM RankingsProcessLog
    WHERE LogTime >= DATEADD(HOUR, -24, GETDATE())
    GROUP BY Season
)
SELECT 
    Season,
    startTime AS [Started At],
    endTime AS [Last Activity],
    DATEDIFF(SECOND, startTime, endTime) AS [Duration (Sec)],
    CASE WHEN isComplete = 1 THEN 'COMPLETE' ELSE 'IN PROGRESS' END AS [Status]
FROM SeasonStats
ORDER BY startTime DESC;

-- =============================================================================
-- 4. REMAINING WORK (Gap Analysis)
-- Shows seasons between Begin and End that haven't been touched yet.
-- Edit the BETWEEN clause to match your current execution range.
-- =============================================================================
/*
PRINT '';
PRINT '4. UNTOUCHED SEASONS (Gap Analysis - Edit Range in Script)';
WITH Processed AS (
    SELECT DISTINCT Season 
    FROM RankingsProcessLog 
    WHERE LogTime >= DATEADD(HOUR, -24, GETDATE())
)
SELECT s.Season AS [Pending Season]
FROM dbo.HS_Scores s
LEFT JOIN Processed p ON s.Season = p.Season
WHERE s.Season BETWEEN 1950 AND 2024 -- <--- UPDATE THIS RANGE TO MATCH YOUR RUN
  AND p.Season IS NULL
GROUP BY s.Season
ORDER BY s.Season DESC;
*/

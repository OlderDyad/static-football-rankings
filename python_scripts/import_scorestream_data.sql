-- ScoreStream Data Import Script
-- Generated: 2025-12-09 05:58:20
-- Teams: 221 | Games: 359

-- Step 1: Create temporary staging tables
IF OBJECT_ID('tempdb..#ScoreStream_Teams') IS NOT NULL DROP TABLE #ScoreStream_Teams;
IF OBJECT_ID('tempdb..#ScoreStream_Games') IS NOT NULL DROP TABLE #ScoreStream_Games;

CREATE TABLE #ScoreStream_Teams (
    TeamName NVARCHAR(200),
    State NVARCHAR(50),
    Level NVARCHAR(50),
    FullName NVARCHAR(250),
    Source NVARCHAR(50),
    ScrapedDate DATE
);

CREATE TABLE #ScoreStream_Games (
    GameID NVARCHAR(200),
    GameDate DATE,
    Season INT,
    Week INT,
    Level NVARCHAR(50),
    HomeTeam NVARCHAR(250),
    AwayTeam NVARCHAR(250),
    HomeScore INT,
    AwayScore INT,
    ScoreStreamLink NVARCHAR(500),
    OpponentTeamID NVARCHAR(50),
    Source NVARCHAR(50),
    ScrapedDate DATETIME
);

-- Step 2: Use BULK INSERT to load CSV files
-- Note: Update the file paths to match your system

BULK INSERT #ScoreStream_Teams
FROM 'C:\path\to\sql_import_teams.csv'
WITH (
    FIRSTROW = 2,
    FIELDTERMINATOR = ',',
    ROWTERMINATOR = '\n',
    TABLOCK
);

BULK INSERT #ScoreStream_Games
FROM 'C:\path\to\sql_import_games.csv'
WITH (
    FIRSTROW = 2,
    FIELDTERMINATOR = ',',
    ROWTERMINATOR = '\n',
    TABLOCK
);

-- Step 3: Verify data loaded
SELECT 'Teams loaded' AS Stage, COUNT(*) AS RecordCount FROM #ScoreStream_Teams;
SELECT 'Games loaded' AS Stage, COUNT(*) AS RecordCount FROM #ScoreStream_Games;

-- Step 4: Insert into your actual tables
-- Example - adjust table/column names to match your schema:

-- Insert teams (avoid duplicates)
INSERT INTO dbo.HS_Team_Names (TeamName, State, Level, Source, DateAdded)
SELECT DISTINCT 
    TeamName, 
    State, 
    Level, 
    Source, 
    GETDATE()
FROM #ScoreStream_Teams t
WHERE NOT EXISTS (
    SELECT 1 FROM dbo.HS_Team_Names h 
    WHERE h.TeamName = t.TeamName AND h.State = t.State AND h.Level = t.Level
);

-- Insert games (avoid duplicates)
INSERT INTO dbo.HS_Scores (
    GameID, GameDate, Season, Week, Level,
    HomeTeam, AwayTeam, HomeScore, AwayScore,
    Source, DateAdded
)
SELECT 
    GameID, GameDate, Season, Week, Level,
    HomeTeam, AwayTeam, HomeScore, AwayScore,
    Source, GETDATE()
FROM #ScoreStream_Games g
WHERE NOT EXISTS (
    SELECT 1 FROM dbo.HS_Scores h 
    WHERE h.GameID = g.GameID
);

-- Step 5: Summary
SELECT 'Import Complete' AS Status;
SELECT COUNT(*) AS NewTeams FROM dbo.HS_Team_Names WHERE DateAdded >= CAST(GETDATE() AS DATE);
SELECT COUNT(*) AS NewGames FROM dbo.HS_Scores WHERE DateAdded >= CAST(GETDATE() AS DATE);

-- Clean up
DROP TABLE #ScoreStream_Teams;
DROP TABLE #ScoreStream_Games;

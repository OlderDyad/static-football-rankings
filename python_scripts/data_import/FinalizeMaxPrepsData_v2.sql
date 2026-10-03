-- ============================================================================
-- Consolidated patch, 2026-09-11. Run this whole script once, top to bottom.
-- Two new tables + one ALTER PROCEDURE. Both changes inside the procedure
-- are marked "-- CHANGED" / "-- NEW" so you can diff against what you
-- already have. Everything else in the procedure is byte-for-byte what you
-- pasted from OBJECT_DEFINITION earlier today.
-- ============================================================================

-- 1. Visibility: every opponent FinalizeMaxPrepsData couldn't resolve gets
--    logged here instead of silently vanishing.
CREATE TABLE dbo.Unmatched_Opponents (
    UnmatchedID INT IDENTITY(1,1) PRIMARY KEY,
    BatchID INT NOT NULL,
    PrimaryTeamName VARCHAR(255) NULL,
    OpponentNameRaw VARCHAR(255) NULL,
    OpponentMaxPrepsURL VARCHAR(500) NULL,
    GameDateRaw VARCHAR(50) NULL,
    ResultText VARCHAR(255) NULL,
    LoggedAt DATETIME NOT NULL DEFAULT GETDATE(),
    Resolved BIT NOT NULL DEFAULT 0,
    ResolvedNote VARCHAR(500) NULL
);
GO

-- 2. The actual fix: lets a Team_ID have more than one known URL (current +
--    any historical variants), instead of URL_ProperName_Mapping's implicit
--    one-URL-per-team limit. Populate this by researching Unmatched_Opponents
--    rows, or automatically via the new maxpreps_scraper_db.py alias fallback.
CREATE TABLE dbo.URL_ProperName_Mapping_Aliases (
    AliasID INT IDENTITY(1,1) PRIMARY KEY,
    Team_ID INT NOT NULL,
    URL VARCHAR(500) NOT NULL,
    Notes VARCHAR(500) NULL,
    AddedBy VARCHAR(100) NULL,
    AddedAt DATETIME NOT NULL DEFAULT GETDATE(),
    CONSTRAINT UQ_URLAlias UNIQUE (Team_ID, URL)
);
GO

/* ============================================================================
   ALTER PROCEDURE dbo.FinalizeMaxPrepsData  -  season-aware (CALIBRATED)
   ----------------------------------------------------------------------------
   All transforms below were verified against batch 14 (MO 2022) real data.
   Changes vs the original, all backward-compatible (current-season batches,
   where season_year IS NULL and season_slug IS NULL, behave as before):

     1. YEAR from games_raw.season_year, fallback YEAR(GETDATE()). Past-season
        rows no longer stamped with the current year.
     2. DATE cleaned before parsing. MaxPreps cells store date + time on
        SEPARATE LINES, e.g. '8/26' + CHAR(10) + '7:00pm', and TBA games as
        '10/7' + CHAR(10) + 'TBA'. We take only the text before the first
        newline OR space, so '8/26\n7:00pm' -> '8/26'. Without this every row
        failed TRY_CONVERT and dropped silently. Computed ONCE via CROSS APPLY.
     3. OPPONENT URL join: the scraped opponent_maxpreps_url already ends in
        '/schedule/' and carries the season segment, e.g.
            .../liberal-bulldogs/football/22-23/schedule/
        The mapping stores the current-season form
            .../liberal-bulldogs/football/schedule/
        So we strip the season segment and match directly (NO appended
        'schedule/'). Verified: transformed == mapping URL on all sampled rows.
        season_slug NULL -> REPLACE is a no-op -> original behavior.

        2026-09-11 CHANGE: this join now also checks URL_ProperName_Mapping_
        Aliases, since a team's URL can drift over the years (slug rename,
        page moved, school renamed) and the plain mapping table only ever
        holds the CURRENT url. See Unmatched_Opponents for what still fails
        to resolve even with aliases -- that's the queue for adding more.

   Season and the Access_ID yyyyMMdd both derive from the corrected date.

   SOURCE (Option A): each row's Source is the primary scraped team's schedule
   page, e.g. https://www.maxpreps.com/mo/drexel/drexel-miami/football/22-23/schedule/
   The /22-23/ segment makes season rows inherently distinct from the old
   '[www.maxpreps.com]' macro rows, and points at the exact page for troubleshooting.

   IDENTIFYING THIS IMPORT: HS_Scores.BatchID is NOT unique (reused across many
   years of loads). Identify these rows by the season segment in Source:
       WHERE Source LIKE '%/22-23/%'
   (and Season = 2022). Never key off BatchID for this table.

   2026-09-11 CHANGE: rows FinalizeMaxPrepsData still can't resolve an
   opponent for (even after checking aliases) are now logged to
   dbo.Unmatched_Opponents instead of silently dropped. See that table.
   ============================================================================ */
CREATE OR ALTER PROCEDURE dbo.FinalizeMaxPrepsData
    @BatchID INT
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @SeasonSlug VARCHAR(10);
    SELECT @SeasonSlug = season_slug FROM dbo.scraping_batches WHERE batch_id = @BatchID;

    CREATE TABLE #ProcessedGames (
        GameID VARCHAR(255) PRIMARY KEY,
        HomeTeamID INT NULL,
        AwayTeamID INT NULL,
        RawHomeTeam VARCHAR(255),
        RawAwayTeam VARCHAR(255),
        HomeScore INT NULL,
        AwayScore INT NULL,
        GameDate DATE NULL,
        Season INT NULL,
        SourceURL VARCHAR(500) NULL
    );

    ;WITH RankedGames AS (
        SELECT
            g.game_date,
            g.result_text,
            g.opponent_name_raw,
            primary_url.ProperName AS PrimaryTeamName,
            primary_url.Team_ID AS PrimaryTeamID,
            opponent_url.ProperName AS OpponentTeamName,
            opponent_url.Team_ID AS OpponentTeamID,
            d.GameDate,
            -- Option A: per-game source = the primary scraped team's schedule
            -- page (season segment reinserted). Current-season runs (slug NULL)
            -- keep the plain mapping URL.
            CASE WHEN @SeasonSlug IS NULL THEN primary_url.URL
                 ELSE REPLACE(primary_url.URL, '/football/schedule/',
                              '/football/' + @SeasonSlug + '/schedule/')
            END AS SourceURL,
            CASE
                WHEN g.opponent_name_raw LIKE '@%' THEN opponent_url.ProperName
                WHEN g.opponent_name_raw LIKE 'vs%' THEN primary_url.ProperName
                WHEN primary_url.ProperName < opponent_url.ProperName THEN primary_url.ProperName
                ELSE opponent_url.ProperName
            END AS HomeTeam,
            CASE
                WHEN g.opponent_name_raw LIKE '@%' THEN primary_url.ProperName
                WHEN g.opponent_name_raw LIKE 'vs%' THEN opponent_url.ProperName
                WHEN primary_url.ProperName < opponent_url.ProperName THEN opponent_url.ProperName
                ELSE primary_url.ProperName
            END AS AwayTeam,
            CASE
                WHEN g.opponent_name_raw LIKE '@%' THEN opponent_url.Team_ID
                WHEN g.opponent_name_raw LIKE 'vs%' THEN primary_url.Team_ID
                WHEN primary_url.ProperName < opponent_url.ProperName THEN primary_url.Team_ID
                ELSE opponent_url.Team_ID
            END AS HomeTeamID,
            CASE
                WHEN g.opponent_name_raw LIKE '@%' THEN primary_url.Team_ID
                WHEN g.opponent_name_raw LIKE 'vs%' THEN opponent_url.Team_ID
                WHEN primary_url.ProperName < opponent_url.ProperName THEN opponent_url.Team_ID
                ELSE primary_url.Team_ID
            END AS AwayTeamID,
            ROW_NUMBER() OVER (
                PARTITION BY
                    d.GameDate,
                    IIF(primary_url.ProperName < opponent_url.ProperName, primary_url.ProperName, opponent_url.ProperName),
                    IIF(primary_url.ProperName > opponent_url.ProperName, primary_url.ProperName, opponent_url.ProperName)
                ORDER BY g.raw_id
            ) AS rn
        FROM dbo.games_raw g
        LEFT JOIN dbo.URL_ProperName_Mapping primary_url
            ON g.primary_team_name = primary_url.ProperName
        -- CHANGED 2026-09-11: opponent resolution now checks the current
        -- mapping table UNIONed with URL_ProperName_Mapping_Aliases, so a
        -- team with a since-changed URL can still resolve via a known
        -- historical alias, not just today's URL.
        LEFT JOIN (
            SELECT URL, ProperName, Team_ID FROM dbo.URL_ProperName_Mapping
            UNION
            SELECT a.URL, m.ProperName, a.Team_ID
            FROM dbo.URL_ProperName_Mapping_Aliases a
            JOIN dbo.URL_ProperName_Mapping m ON a.Team_ID = m.Team_ID
        ) opponent_url
            ON REPLACE(g.opponent_maxpreps_url, '/' + ISNULL(@SeasonSlug, '~~none~~') + '/', '/')
               = opponent_url.URL
        -- CONFIRMED: cut date at first newline OR space, then apply correct year
        CROSS APPLY (
            SELECT TRY_CONVERT(
                DATE,
                LEFT(
                    g.game_date,
                    -- position of the earliest of: first CHAR(10), first space, or end
                    (SELECT MIN(p) FROM (VALUES
                        (NULLIF(CHARINDEX(CHAR(10), g.game_date), 0)),
                        (NULLIF(CHARINDEX(' ',       g.game_date), 0)),
                        (LEN(g.game_date) + 1)
                    ) AS positions(p)) - 1
                )
                + '/' + CAST(COALESCE(g.season_year, YEAR(GETDATE())) AS VARCHAR(4)),
                101
            ) AS GameDate
        ) d
        WHERE g.batch_id = @BatchID
          AND g.primary_team_name IS NOT NULL
          AND d.GameDate IS NOT NULL
          AND primary_url.ProperName IS NOT NULL
          AND opponent_url.ProperName IS NOT NULL
    )
    INSERT INTO #ProcessedGames (GameID, RawHomeTeam, RawAwayTeam, HomeTeamID, AwayTeamID, HomeScore, AwayScore, GameDate, Season, SourceURL)
    SELECT
        CONCAT(FORMAT(GameDate, 'yyyyMMdd'), '-', IIF(HomeTeam < AwayTeam, HomeTeam, AwayTeam), '-', IIF(HomeTeam > AwayTeam, HomeTeam, AwayTeam)) AS GameID,
        HomeTeam,
        AwayTeam,
        HomeTeamID,
        AwayTeamID,
        CASE
            WHEN HomeTeam = PrimaryTeamName AND result_text LIKE 'W%' THEN scores.s_max
            WHEN HomeTeam = PrimaryTeamName AND result_text LIKE 'L%' THEN scores.s_min
            WHEN AwayTeam = PrimaryTeamName AND result_text LIKE 'W%' THEN scores.s_min
            WHEN AwayTeam = PrimaryTeamName AND result_text LIKE 'L%' THEN scores.s_max
            ELSE scores.s_max
        END AS HomeScore,
        CASE
            WHEN AwayTeam = PrimaryTeamName AND result_text LIKE 'W%' THEN scores.s_max
            WHEN AwayTeam = PrimaryTeamName AND result_text LIKE 'L%' THEN scores.s_min
            WHEN HomeTeam = PrimaryTeamName AND result_text LIKE 'W%' THEN scores.s_min
            WHEN HomeTeam = PrimaryTeamName AND result_text LIKE 'L%' THEN scores.s_max
            ELSE scores.s_min
        END AS AwayScore,
        GameDate,
        YEAR(GameDate) AS Season,
        SourceURL
    FROM RankedGames
    CROSS APPLY (
        SELECT
            MIN(TRY_CAST(value AS INT)) AS s_min,
            MAX(TRY_CAST(value AS INT)) AS s_max
        FROM STRING_SPLIT(REPLACE(result_text, '-', ' '), ' ')
        WHERE ISNUMERIC(value) = 1
    ) AS scores
    WHERE rn = 1;

    INSERT INTO dbo.HS_Scores (ID, Date, Season, Home, Visitor, Home_Score, Visitor_Score, Margin, Access_ID, Source, Date_Added, BatchID)
    SELECT
        NEWID(),
        pg.GameDate,
        pg.Season,
        pg.RawHomeTeam,
        pg.RawAwayTeam,
        pg.HomeScore,
        pg.AwayScore,
        pg.HomeScore - pg.AwayScore,
        pg.GameID,
        -- Option A: per-game MaxPreps source page (carries /22-23/ for season runs,
        -- so it is inherently distinct from old '[www.maxpreps.com]' rows).
        pg.SourceURL,
        GETDATE(),
        @BatchID
    FROM #ProcessedGames pg
    WHERE pg.HomeScore IS NOT NULL AND pg.AwayScore IS NOT NULL
      AND NOT EXISTS (SELECT 1 FROM dbo.HS_Scores s WHERE s.Access_ID = pg.GameID);

    IF OBJECT_ID('dbo.Future_Games', 'U') IS NOT NULL
    BEGIN
        INSERT INTO dbo.Future_Games (GameID, BatchID, RawHomeTeam, RawAwayTeam, GameDate)
        SELECT pg.GameID, @BatchID, pg.RawHomeTeam, pg.RawAwayTeam, pg.GameDate
        FROM #ProcessedGames pg
        WHERE (pg.HomeScore IS NULL OR pg.AwayScore IS NULL)
          AND NOT EXISTS (SELECT 1 FROM dbo.Future_Games fg WHERE fg.GameID = pg.GameID);
    END

    -- NEW 2026-09-11: surface opponents that couldn't be resolved (even with
    -- aliases) instead of silently excluding them. This is purely additive --
    -- it reads the same games_raw/primary_url/opponent_url logic above but
    -- writes to a separate table, so it cannot change which rows land in
    -- HS_Scores.
    INSERT INTO dbo.Unmatched_Opponents (BatchID, PrimaryTeamName, OpponentNameRaw, OpponentMaxPrepsURL, GameDateRaw, ResultText)
    SELECT @BatchID, g.primary_team_name, g.opponent_name_raw, g.opponent_maxpreps_url, g.game_date, g.result_text
    FROM dbo.games_raw g
    LEFT JOIN dbo.URL_ProperName_Mapping primary_url ON g.primary_team_name = primary_url.ProperName
    LEFT JOIN (
        SELECT URL, ProperName, Team_ID FROM dbo.URL_ProperName_Mapping
        UNION
        SELECT a.URL, m.ProperName, a.Team_ID
        FROM dbo.URL_ProperName_Mapping_Aliases a
        JOIN dbo.URL_ProperName_Mapping m ON a.Team_ID = m.Team_ID
    ) opponent_url
        ON REPLACE(g.opponent_maxpreps_url, '/' + ISNULL(@SeasonSlug, '~~none~~') + '/', '/') = opponent_url.URL
    WHERE g.batch_id = @BatchID
      AND primary_url.ProperName IS NOT NULL
      AND opponent_url.ProperName IS NULL;

    DROP TABLE #ProcessedGames;
    PRINT 'Batch ' + CAST(@BatchID AS VARCHAR(10)) + ' processed successfully';
END
GO

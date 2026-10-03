import argparse
import pyodbc

parser = argparse.ArgumentParser()
parser.add_argument('--commit', action='store_true')
args = parser.parse_args()

# Same procedure as before, with ONE further change: the opponent URL is now
# normalized (append '/schedule/' if it's missing) via a CROSS APPLY, computed
# once and used in both the RankedGames join and the Unmatched_Opponents
# insert's join -- mirroring what _clean_schedule_url() does in Python.
# Root cause: raw scraped opponent hrefs are the opponent's TEAM HOME page
# (".../mustangs/football/"), never their schedule sub-page, so a bare
# equality join against URL_ProperName_Mapping.URL (always ".../football/
# schedule/") matched ~0% of games. Confirmed on batch 33: 96,198 rows to
# Unmatched_Opponents, 0 to HS_Scores.
CREATE_OR_ALTER_SQL = r"""
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
        -- 2026-09-19 NEW: normalize the raw opponent URL (strip season slug,
        -- then ensure it ends in '/football/schedule/' -- raw scraped hrefs
        -- are the opponent's team home page, e.g. '.../football/', not their
        -- schedule sub-page) before joining against the mapping table.
        CROSS APPLY (
            SELECT
                CASE
                    WHEN REPLACE(g.opponent_maxpreps_url, '/' + ISNULL(@SeasonSlug, '~~none~~') + '/', '/') LIKE '%/football/schedule/'
                        THEN REPLACE(g.opponent_maxpreps_url, '/' + ISNULL(@SeasonSlug, '~~none~~') + '/', '/')
                    WHEN REPLACE(g.opponent_maxpreps_url, '/' + ISNULL(@SeasonSlug, '~~none~~') + '/', '/') LIKE '%/football/'
                        THEN REPLACE(g.opponent_maxpreps_url, '/' + ISNULL(@SeasonSlug, '~~none~~') + '/', '/') + 'schedule/'
                    WHEN REPLACE(g.opponent_maxpreps_url, '/' + ISNULL(@SeasonSlug, '~~none~~') + '/', '/') LIKE '%/football'
                        THEN REPLACE(g.opponent_maxpreps_url, '/' + ISNULL(@SeasonSlug, '~~none~~') + '/', '/') + '/schedule/'
                    ELSE REPLACE(g.opponent_maxpreps_url, '/' + ISNULL(@SeasonSlug, '~~none~~') + '/', '/')
                END AS NormalizedOpponentURL
        ) nou
        LEFT JOIN (
            SELECT URL, ProperName, Team_ID FROM dbo.URL_ProperName_Mapping
            UNION
            SELECT a.URL, m.ProperName, a.Team_ID
            FROM dbo.URL_ProperName_Mapping_Aliases a
            JOIN dbo.URL_ProperName_Mapping m ON a.Team_ID = m.Team_ID
        ) opponent_url
            ON nou.NormalizedOpponentURL = opponent_url.URL
        CROSS APPLY (
            SELECT TRY_CONVERT(
                DATE,
                LEFT(
                    g.game_date,
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

    INSERT INTO dbo.Unmatched_Opponents (BatchID, PrimaryTeamName, OpponentNameRaw, OpponentMaxPrepsURL, GameDateRaw, ResultText, RawGameID)
    SELECT @BatchID, g.primary_team_name, g.opponent_name_raw, g.opponent_maxpreps_url, g.game_date, g.result_text, g.raw_id
    FROM dbo.games_raw g
    LEFT JOIN dbo.URL_ProperName_Mapping primary_url ON g.primary_team_name = primary_url.ProperName
    CROSS APPLY (
        SELECT
            CASE
                WHEN REPLACE(g.opponent_maxpreps_url, '/' + ISNULL(@SeasonSlug, '~~none~~') + '/', '/') LIKE '%/football/schedule/'
                    THEN REPLACE(g.opponent_maxpreps_url, '/' + ISNULL(@SeasonSlug, '~~none~~') + '/', '/')
                WHEN REPLACE(g.opponent_maxpreps_url, '/' + ISNULL(@SeasonSlug, '~~none~~') + '/', '/') LIKE '%/football/'
                    THEN REPLACE(g.opponent_maxpreps_url, '/' + ISNULL(@SeasonSlug, '~~none~~') + '/', '/') + 'schedule/'
                WHEN REPLACE(g.opponent_maxpreps_url, '/' + ISNULL(@SeasonSlug, '~~none~~') + '/', '/') LIKE '%/football'
                    THEN REPLACE(g.opponent_maxpreps_url, '/' + ISNULL(@SeasonSlug, '~~none~~') + '/', '/') + '/schedule/'
                ELSE REPLACE(g.opponent_maxpreps_url, '/' + ISNULL(@SeasonSlug, '~~none~~') + '/', '/')
            END AS NormalizedOpponentURL
    ) nou
    LEFT JOIN (
        SELECT URL, ProperName, Team_ID FROM dbo.URL_ProperName_Mapping
        UNION
        SELECT a.URL, m.ProperName, a.Team_ID
        FROM dbo.URL_ProperName_Mapping_Aliases a
        JOIN dbo.URL_ProperName_Mapping m ON a.Team_ID = m.Team_ID
    ) opponent_url
        ON nou.NormalizedOpponentURL = opponent_url.URL
    WHERE g.batch_id = @BatchID
      AND primary_url.ProperName IS NOT NULL
      AND opponent_url.ProperName IS NULL
      AND NOT EXISTS (SELECT 1 FROM dbo.Unmatched_Opponents uo WHERE uo.RawGameID = g.raw_id);

    DROP TABLE #ProcessedGames;
    PRINT 'Batch ' + CAST(@BatchID AS VARCHAR(10)) + ' processed successfully';
END
"""

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

if args.commit:
    print('--commit passed: applying CREATE OR ALTER PROCEDURE now...')
    cur.execute(CREATE_OR_ALTER_SQL)
    conn.commit()
    print('Done.')

    cur.execute("SELECT OBJECT_DEFINITION(OBJECT_ID('dbo.FinalizeMaxPrepsData'))")
    definition = cur.fetchone()[0]
    print(f'  Contains NormalizedOpponentURL: {"NormalizedOpponentURL" in definition}')
else:
    print('DRY RUN -- nothing applied. Re-run with --commit to apply.')
    print('(See script source for the full SQL that will run.)')

conn.close()

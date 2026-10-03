import argparse
import pyodbc

parser = argparse.ArgumentParser()
parser.add_argument('--commit', action='store_true', help='Actually apply. Without this flag, prints the SQL and exits.')
args = parser.parse_args()

ALTER_TABLE_SQL = """
ALTER TABLE dbo.Unmatched_Opponents ADD RawGameID INT NULL;
"""

# Full procedure body, unchanged except: (1) RawGameID added to the
# Unmatched_Opponents INSERT's column list/SELECT, sourced from g.raw_id,
# and (2) a NOT EXISTS guard added to the WHERE clause so calling this
# procedure again for a batch that's still accumulating games (nightly,
# not just once at full completion) no longer re-logs the same unresolved
# row every time. HS_Scores and Future_Games inserts were already safe via
# their own NOT EXISTS guards -- this was the only remaining blocker to
# calling FinalizeMaxPrepsData nightly instead of once at batch completion.
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
        LEFT JOIN (
            SELECT URL, ProperName, Team_ID FROM dbo.URL_ProperName_Mapping
            UNION
            SELECT a.URL, m.ProperName, a.Team_ID
            FROM dbo.URL_ProperName_Mapping_Aliases a
            JOIN dbo.URL_ProperName_Mapping m ON a.Team_ID = m.Team_ID
        ) opponent_url
            ON REPLACE(g.opponent_maxpreps_url, '/' + ISNULL(@SeasonSlug, '~~none~~') + '/', '/')
               = opponent_url.URL
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

    -- 2026-09-19 CHANGE: added RawGameID (= games_raw.raw_id) + a NOT EXISTS
    -- guard on it, so calling this procedure repeatedly for the same
    -- still-accumulating @BatchID (nightly, not just once at full batch
    -- completion) no longer re-inserts the same unresolved row every time.
    -- HS_Scores/Future_Games above were already idempotent this way; this
    -- was the only blocker to safe nightly finalize.
    INSERT INTO dbo.Unmatched_Opponents (BatchID, PrimaryTeamName, OpponentNameRaw, OpponentMaxPrepsURL, GameDateRaw, ResultText, RawGameID)
    SELECT @BatchID, g.primary_team_name, g.opponent_name_raw, g.opponent_maxpreps_url, g.game_date, g.result_text, g.raw_id
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
      AND opponent_url.ProperName IS NULL
      AND NOT EXISTS (SELECT 1 FROM dbo.Unmatched_Opponents uo WHERE uo.RawGameID = g.raw_id);

    DROP TABLE #ProcessedGames;
    PRINT 'Batch ' + CAST(@BatchID AS VARCHAR(10)) + ' processed successfully';
END
"""

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=McKnights-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;')
cur = conn.cursor()

print('=== SQL to be applied ===')
print(ALTER_TABLE_SQL)
print('-- (then) --')
print('CREATE OR ALTER PROCEDURE dbo.FinalizeMaxPrepsData ... [full body, see script source]')

if args.commit:
    print()
    print('--commit passed: applying now...')
    cur.execute(ALTER_TABLE_SQL)
    conn.commit()
    print('ALTER TABLE done (Unmatched_Opponents.RawGameID added).')

    cur.execute(CREATE_OR_ALTER_SQL)
    conn.commit()
    print('CREATE OR ALTER PROCEDURE done (FinalizeMaxPrepsData updated).')

    print()
    print('Verifying...')
    cur.execute("""
        SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'Unmatched_Opponents' AND COLUMN_NAME = 'RawGameID'
    """)
    print(f'  RawGameID column present: {cur.fetchone() is not None}')
    cur.execute("SELECT OBJECT_DEFINITION(OBJECT_ID('dbo.FinalizeMaxPrepsData'))")
    definition = cur.fetchone()[0]
    print(f'  Procedure contains new NOT EXISTS guard: {"NOT EXISTS (SELECT 1 FROM dbo.Unmatched_Opponents uo WHERE uo.RawGameID" in definition}')
else:
    print()
    print('DRY RUN ONLY -- nothing applied. Re-run with --commit to actually apply.')

conn.close()

-- ============================================================================
-- RemoveDuplicateGamesParameterized -- v4 (2026-10-12)
--
-- Problems found in v3 (the version currently deployed):
--
--  1. STATE FILTER WAS A SUBSTRING MATCH.  Home LIKE '%' + @State + '%'
--     with @State = 'CO' matches ANY team name containing "co" (Lincoln,
--     Scott, Cody, Academy, Jacobs, Cocoa, Colorado...), in every state.
--     Same for 'IN', 'OR', 'ME', 'LA', 'MA', 'AL' ... So one "state" run
--     actually swept a large slice of the whole database, and the next
--     state's run kept finding games from the state just done.
--     v4: matches the state suffix only:  RTRIM(Home) LIKE '%(CO)'.
--
--  2. THE "SWAPPED" PASS IGNORED WHO WON.  It sorted the two team names
--     and, separately, sorted the two scores. So
--         A 14  B 7    and    B 14  A 7     (two different games, A lost one)
--     looked identical and one was deleted. v4 compares each team's own
--     score (score of the alphabetically-first team, score of the second).
--
--  3. NO DATE CHECK.  Any two games in the same season with the same teams
--     and score were treated as one game (two 0-0 ties, home-and-home
--     series with the same result, etc.). v4 requires:
--         Season <= 2003 (newspaper era): dates within @NewspaperDayWindow (10)
--         Season >= 2004 (MaxPreps era):  dates within @MaxPrepsDayWindow (1)
--     Pairs with a missing date or a bigger gap are only LISTED for review.
--
--  4. THE ROW KEPT WAS RANDOM.  MIN(ID) on a GUID is arbitrary. v4 keeps the
--     best-documented row (see KeepRank below) and archives the others.
--
--  5. ARCHIVE WAS A 255-CHAR TEXT SNAPSHOT.  Not restorable in full. v4
--     copies the complete row to dbo.HS_Scores_Duplicate_Archive (and still
--     writes the usual ROW_DELETED line to HS_Scores_Change_Log).
--
--  6. FORFEIT STEP REMOVED.  v3 un-flagged every Forfeit=1 row whose score
--     did not total 1 (undoing real 2-0 / "(FF)" forfeits) and does not match
--     the forfeit rule now used by dbo.ScoresWinLoss. @MarkForfeits is still
--     accepted so old calls don't break, but it does nothing.
--
--  7. PREVIEW BY DEFAULT.  @Preview = 1 (default) changes nothing. Run with
--     @Preview = 0 to archive and delete.
--
-- Result sets (in this order, every run):
--   1. WILL ARCHIVE  - one row per game to be removed, shown next to the row
--                      it duplicates (Drop_* vs Keep_*), with the day gap.
--   2. REVIEW ONLY   - same season, same teams, same score but the dates are
--                      missing or further apart than the window. Never deleted.
--   3. Summary counts.
--
-- Usage:
--   EXEC dbo.RemoveDuplicateGamesParameterized @State = 'CO';                 -- preview
--   EXEC dbo.RemoveDuplicateGamesParameterized @State = 'CO', @Preview = 0;   -- do it
--   EXEC dbo.RemoveDuplicateGamesParameterized @State = 'CO', @SeasonStart = 1920, @SeasonEnd = 1959;
-- ============================================================================

-- ---------------------------------------------------------------------------
-- PART 1 (run once): full-row archive table
-- ---------------------------------------------------------------------------
IF OBJECT_ID('dbo.HS_Scores_Duplicate_Archive') IS NULL
BEGIN
    CREATE TABLE dbo.HS_Scores_Duplicate_Archive (
        ArchiveID     INT IDENTITY(1,1) PRIMARY KEY,
        RunID         UNIQUEIDENTIFIER NOT NULL,
        RunAt         DATETIME         NOT NULL,
        RunParams     VARCHAR(400)     NULL,
        KeptID        UNIQUEIDENTIFIER NOT NULL,   -- surviving HS_Scores.ID
        DayGap        INT              NULL,
        -- full copy of the HS_Scores row
        ID            UNIQUEIDENTIFIER NOT NULL,
        [Date]        DATE             NULL,
        Season        INT              NULL,
        Home          VARCHAR(111)     NULL,
        Visitor       VARCHAR(111)     NULL,
        Neutral       BIT              NULL,
        Location      VARCHAR(111)     NULL,
        Location2     VARCHAR(255)     NULL,
        Line          INT              NULL,
        Future_Game   BIT              NULL,
        Source        VARCHAR(255)     NULL,
        Date_Added    DATETIME         NULL,
        OT            INT              NULL,
        Forfeit       BIT              NULL,
        Visitor_Score INT              NULL,
        Home_Score    INT              NULL,
        Margin        INT              NULL,
        BatchID       INT              NULL,
        Access_ID     VARCHAR(255)     NULL
    );
    CREATE INDEX IX_HS_Scores_Duplicate_Archive_RunID ON dbo.HS_Scores_Duplicate_Archive (RunID);
    CREATE INDEX IX_HS_Scores_Duplicate_Archive_ID    ON dbo.HS_Scores_Duplicate_Archive (ID);
END
GO

-- ---------------------------------------------------------------------------
-- PART 2: the procedure
-- ---------------------------------------------------------------------------
ALTER PROCEDURE [dbo].[RemoveDuplicateGamesParameterized]
    @State              VARCHAR(2) = NULL,     -- 2-letter code, matched as the "(XX)" suffix
    @SeasonStart        INT = NULL,
    @SeasonEnd          INT = NULL,
    @Preview            BIT = 1,               -- 1 = list only (default), 0 = archive + delete
    @NewspaperDayWindow INT = 10,              -- seasons <= 2003
    @MaxPrepsDayWindow  INT = 1,               -- seasons >= 2004
    @MarkForfeits       BIT = 0                -- ignored (kept for old callers)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    IF @State IS NOT NULL AND @State NOT LIKE '[A-Z][A-Z]'
    BEGIN
        RAISERROR('@State must be a 2-letter code such as CO.', 16, 1);
        RETURN;
    END

    DECLARE @StatePat VARCHAR(10) = '%(' + @State + ')';
    DECLARE @RunID UNIQUEIDENTIFIER = NEWID(), @RunAt DATETIME = GETDATE();
    DECLARE @RunParams VARCHAR(400) = CONCAT(
        'RemoveDuplicateGamesParameterized v4 run: State=', ISNULL(@State, 'ALL'),
        ', SeasonStart=', ISNULL(CAST(@SeasonStart AS VARCHAR(10)), 'First'),
        ', SeasonEnd=', ISNULL(CAST(@SeasonEnd AS VARCHAR(10)), 'Last'),
        ', Windows=', @NewspaperDayWindow, '/', @MaxPrepsDayWindow, ' days');

    IF @MarkForfeits = 1 PRINT 'Note: @MarkForfeits is ignored in v4 (forfeit handling lives in dbo.ScoresWinLoss).';

    -- -----------------------------------------------------------------------
    -- 1. Games in scope, with a team-order-independent key and a keep rank
    -- -----------------------------------------------------------------------
    SELECT
        s.ID, s.Season, s.[Date], s.Home, s.Visitor, s.Home_Score, s.Visitor_Score,
        s.Source, s.Access_ID, s.Date_Added,
        CASE WHEN s.Home <= s.Visitor THEN s.Home ELSE s.Visitor END AS T1,
        CASE WHEN s.Home <= s.Visitor THEN s.Visitor ELSE s.Home END AS T2,
        CASE WHEN s.Home <= s.Visitor THEN s.Home_Score ELSE s.Visitor_Score END AS T1_Score,
        CASE WHEN s.Home <= s.Visitor THEN s.Visitor_Score ELSE s.Home_Score END AS T2_Score,
        ROW_NUMBER() OVER (ORDER BY
            CASE WHEN s.Access_ID IS NOT NULL THEN 0 ELSE 1 END,             -- current MaxPreps pipeline row
            CASE WHEN s.[Date] IS NOT NULL THEN 0 ELSE 1 END,                -- has a date
            CASE WHEN s.Source IS NULL OR s.Source = '' THEN 2               -- has a source ...
                 WHEN s.Source IN ('www.maxpreps.com', '[www.maxpreps.com]') THEN 1   -- generic MaxPreps (2019 date bug)
                 WHEN s.Source LIKE '%classmates%' OR s.Source LIKE '%cebyrd%' THEN 1 -- yearbook-derived, approx. date
                 ELSE 0 END,
            CASE WHEN s.Location IS NULL OR s.Location = '' THEN 1 ELSE 0 END,
            ISNULL(s.Date_Added, '9999-12-31'),                               -- then the original (earliest) entry
            s.ID
        ) AS KeepRank
    INTO #G
    FROM dbo.HS_Scores s
    WHERE s.Home IS NOT NULL AND s.Visitor IS NOT NULL
      AND s.Home_Score IS NOT NULL AND s.Visitor_Score IS NOT NULL
      AND (@State IS NULL OR RTRIM(s.Home) LIKE @StatePat OR RTRIM(s.Visitor) LIKE @StatePat)
      AND (@SeasonStart IS NULL OR s.Season >= @SeasonStart)
      AND (@SeasonEnd   IS NULL OR s.Season <= @SeasonEnd);

    CREATE INDEX IX_G ON #G (Season, T1, T2, T1_Score, T2_Score) INCLUDE ([Date], KeepRank);

    -- -----------------------------------------------------------------------
    -- 2. Matching pairs: same season, same two teams, same score for each team
    --    a = candidate to drop, b = better-ranked row it duplicates
    -- -----------------------------------------------------------------------
    SELECT
        a.ID AS DropID, b.ID AS KeepID, b.KeepRank AS KeepRank,
        CASE WHEN a.[Date] IS NULL OR b.[Date] IS NULL THEN NULL
             ELSE ABS(DATEDIFF(DAY, a.[Date], b.[Date])) END AS DayGap,
        CASE WHEN a.[Date] IS NOT NULL AND b.[Date] IS NOT NULL
              AND ABS(DATEDIFF(DAY, a.[Date], b.[Date]))
                  <= CASE WHEN a.Season >= 2004 THEN @MaxPrepsDayWindow ELSE @NewspaperDayWindow END
             THEN 1 ELSE 0 END AS InWindow
    INTO #Pairs
    FROM #G a
    JOIN #G b
      ON  b.Season = a.Season AND b.T1 = a.T1 AND b.T2 = a.T2
      AND b.T1_Score = a.T1_Score AND b.T2_Score = a.T2_Score
      AND b.KeepRank < a.KeepRank;

    -- -----------------------------------------------------------------------
    -- 3. Decide what to drop (in-window pairs only). Iterative so chains
    --    (A~B, B~C but A not ~ C) never drop a row whose keeper is also dropped.
    -- -----------------------------------------------------------------------
    CREATE TABLE #Drop (ID UNIQUEIDENTIFIER PRIMARY KEY, KeptID UNIQUEIDENTIFIER, DayGap INT);

    WHILE 1 = 1
    BEGIN
        ;WITH Winners AS (           -- rows still standing with no better-ranked, still-standing in-window twin
            SELECT g.ID FROM #G g
            WHERE NOT EXISTS (SELECT 1 FROM #Drop d WHERE d.ID = g.ID)
              AND NOT EXISTS (SELECT 1 FROM #Pairs p
                              WHERE p.DropID = g.ID AND p.InWindow = 1
                                AND NOT EXISTS (SELECT 1 FROM #Drop d2 WHERE d2.ID = p.KeepID))
        ), Cand AS (
            SELECT p.DropID, p.KeepID, p.DayGap,
                   ROW_NUMBER() OVER (PARTITION BY p.DropID ORDER BY p.KeepRank) AS rn
            FROM #Pairs p
            JOIN Winners w ON w.ID = p.KeepID
            WHERE p.InWindow = 1
              AND NOT EXISTS (SELECT 1 FROM #Drop d WHERE d.ID = p.DropID)
        )
        INSERT INTO #Drop (ID, KeptID, DayGap)
        SELECT DropID, KeepID, DayGap FROM Cand WHERE rn = 1;

        IF @@ROWCOUNT = 0 BREAK;
    END

    -- -----------------------------------------------------------------------
    -- 4. Result set 1: WILL ARCHIVE (side by side)
    -- -----------------------------------------------------------------------
    SELECT
        CASE WHEN @Preview = 1 THEN 'PREVIEW - would archive' ELSE 'ARCHIVED' END AS Action,
        x.Season, d.DayGap,
        CASE WHEN x.Season >= 2004 THEN 'MaxPreps era' ELSE 'Newspaper era' END AS Era,
        x.[Date] AS Drop_Date, x.Home AS Drop_Home, x.Home_Score AS Drop_HS,
        x.Visitor AS Drop_Visitor, x.Visitor_Score AS Drop_VS, x.Source AS Drop_Source,
        k.[Date] AS Keep_Date, k.Home AS Keep_Home, k.Home_Score AS Keep_HS,
        k.Visitor AS Keep_Visitor, k.Visitor_Score AS Keep_VS, k.Source AS Keep_Source,
        x.ID AS Drop_ID, k.ID AS Keep_ID
    FROM #Drop d
    JOIN dbo.HS_Scores x ON x.ID = d.ID
    JOIN dbo.HS_Scores k ON k.ID = d.KeptID
    ORDER BY x.Season, k.Home, k.[Date];

    -- -----------------------------------------------------------------------
    -- 5. Result set 2: REVIEW ONLY (never deleted)
    -- -----------------------------------------------------------------------
    SELECT
        'REVIEW ONLY - not deleted' AS Action,
        a.Season, p.DayGap,
        CASE WHEN p.DayGap IS NULL THEN 'missing date' ELSE 'dates too far apart' END AS Why,
        a.[Date] AS A_Date, a.Home AS A_Home, a.Home_Score AS A_HS, a.Visitor AS A_Visitor, a.Visitor_Score AS A_VS, a.Source AS A_Source,
        b.[Date] AS B_Date, b.Home AS B_Home, b.Home_Score AS B_HS, b.Visitor AS B_Visitor, b.Visitor_Score AS B_VS, b.Source AS B_Source,
        a.ID AS A_ID, b.ID AS B_ID
    FROM #Pairs p
    JOIN #G a ON a.ID = p.DropID
    JOIN #G b ON b.ID = p.KeepID
    WHERE p.InWindow = 0
      AND NOT EXISTS (SELECT 1 FROM #Drop d WHERE d.ID = p.DropID)
    ORDER BY a.Season, a.T1, a.[Date];

    DECLARE @n INT = (SELECT COUNT(*) FROM #Drop);
    DECLARE @r INT = (SELECT COUNT(*) FROM #Pairs p WHERE p.InWindow = 0
                      AND NOT EXISTS (SELECT 1 FROM #Drop d WHERE d.ID = p.DropID));

    -- -----------------------------------------------------------------------
    -- 6. Archive + delete (only when @Preview = 0)
    -- -----------------------------------------------------------------------
    IF @Preview = 0 AND @n > 0
    BEGIN
        BEGIN TRANSACTION;

        INSERT INTO dbo.HS_Scores_Duplicate_Archive
            (RunID, RunAt, RunParams, KeptID, DayGap,
             ID, [Date], Season, Home, Visitor, Neutral, Location, Location2, Line, Future_Game,
             Source, Date_Added, OT, Forfeit, Visitor_Score, Home_Score, Margin, BatchID, Access_ID)
        SELECT @RunID, @RunAt, @RunParams, d.KeptID, d.DayGap,
             s.ID, s.[Date], s.Season, s.Home, s.Visitor, s.Neutral, s.Location, s.Location2, s.Line, s.Future_Game,
             s.Source, s.Date_Added, s.OT, s.Forfeit, s.Visitor_Score, s.Home_Score, s.Margin, s.BatchID, s.Access_ID
        FROM #Drop d JOIN dbo.HS_Scores s ON s.ID = d.ID;

        IF @@ROWCOUNT <> @n
        BEGIN
            ROLLBACK TRANSACTION;
            RAISERROR('Archive row count did not match - nothing deleted.', 16, 1);
            RETURN;
        END

        INSERT INTO dbo.HS_Scores_Change_Log (ScoresID, InvestigationID, FieldChanged, OldValue, NewValue, Reason, Script)
        SELECT s.ID, NULL, 'ROW_DELETED',
               LEFT(CONCAT('Season=', s.Season, ', Date=', CONVERT(VARCHAR(10), s.[Date], 120),
                           ', Home=''', s.Home, ''', Home_Score=', s.Home_Score,
                           ', Visitor=''', s.Visitor, ''', Visitor_Score=', s.Visitor_Score,
                           ', Source=''', ISNULL(s.Source, ''), ''''), 255),
               NULL,
               LEFT(CONCAT(@RunParams, ' RunID=', @RunID, ' -- duplicate of surviving row ', d.KeptID), 255),
               'RemoveDuplicateGamesParameterized v4'
        FROM #Drop d JOIN dbo.HS_Scores s ON s.ID = d.ID;

        DELETE s FROM dbo.HS_Scores s JOIN #Drop d ON d.ID = s.ID;

        IF @@ROWCOUNT <> @n
        BEGIN
            ROLLBACK TRANSACTION;
            RAISERROR('Delete row count did not match - rolled back.', 16, 1);
            RETURN;
        END

        COMMIT TRANSACTION;
    END

    -- -----------------------------------------------------------------------
    -- 7. Result set 3: summary
    -- -----------------------------------------------------------------------
    SELECT
        CASE WHEN @Preview = 1 THEN 'PREVIEW (nothing changed)' ELSE 'COMMITTED' END AS Mode,
        ISNULL(@State, 'ALL') AS State,
        (SELECT COUNT(*) FROM #G) AS GamesInScope,
        @n AS DuplicatesArchived,
        @r AS ReviewOnlyPairs,
        CASE WHEN @Preview = 0 AND @n > 0 THEN CAST(@RunID AS VARCHAR(36)) END AS RunID;

    DROP TABLE #Drop; DROP TABLE #Pairs; DROP TABLE #G;
END
GO

-- ---------------------------------------------------------------------------
-- Undo one run (restores every row that run archived):
--
-- DECLARE @RunID UNIQUEIDENTIFIER = '<RunID from the summary>';
-- INSERT INTO dbo.HS_Scores (ID, [Date], Season, Home, Visitor, Neutral, Location, Location2, Line,
--        Future_Game, Source, Date_Added, OT, Forfeit, Visitor_Score, Home_Score, BatchID, Access_ID)
-- SELECT a.ID, a.[Date], a.Season, a.Home, a.Visitor, a.Neutral, a.Location, a.Location2, a.Line,
--        a.Future_Game, a.Source, a.Date_Added, a.OT, a.Forfeit, a.Visitor_Score, a.Home_Score, a.BatchID, a.Access_ID
-- FROM dbo.HS_Scores_Duplicate_Archive a
-- WHERE a.RunID = @RunID AND NOT EXISTS (SELECT 1 FROM dbo.HS_Scores s WHERE s.ID = a.ID);
-- (Margin is left out in case it is a computed column; add it if it is a plain column.)
-- ---------------------------------------------------------------------------

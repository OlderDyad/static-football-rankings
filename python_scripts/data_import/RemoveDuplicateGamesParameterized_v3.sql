-- ============================================================================
-- RemoveDuplicateGamesParameterized -- v3, fixes a real bug in v2
--
-- WHAT WENT WRONG IN v2: the archive INSERT...SELECT into
-- HS_Scores_Change_Log is a single set-based statement over the whole
-- #DuplicatesToRemove set. When ANY one row's snapshot exceeded
-- HS_Scores_Change_Log.OldValue's VARCHAR(255) limit (e.g. a long team
-- name like "Oklahoma City Heritage Hall (OK)"), the WHOLE INSERT failed
-- and rolled back to zero rows archived. Because the proc had no
-- SET XACT_ABORT ON and no transaction tying the archive INSERT and the
-- following DELETE together, execution simply continued to the DELETE
-- anyway -- so an entire batch of "duplicate" rows could be deleted with
-- ZERO audit log entries, exactly the failure mode this whole
-- archive-before-delete design existed to prevent.
--
-- FIX 1: LEFT(..., 255) on the final CONCAT so the snapshot can never
-- exceed the column's limit again, regardless of how long any field is.
-- FIX 2: SET XACT_ABORT ON, so ANY error in ANY statement aborts the
-- entire batch immediately (no partial "archive failed but delete still
-- ran" sequence is possible anymore) -- a general safety net beyond just
-- this one bug.
-- ============================================================================

ALTER PROCEDURE [dbo].[RemoveDuplicateGamesParameterized]
    @State NVARCHAR(100) = NULL,
    @SeasonStart INT = NULL,
    @SeasonEnd INT = NULL,
    @MarkForfeits BIT = 1
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @RunReason VARCHAR(400) =
        CONCAT('RemoveDuplicateGamesParameterized run: State=', ISNULL(@State, 'None'),
               ', SeasonStart=', ISNULL(CAST(@SeasonStart AS VARCHAR(10)), 'First'),
               ', SeasonEnd=', ISNULL(CAST(@SeasonEnd AS VARCHAR(10)), 'Last'));

    -- Step 1: Mark forfeit games (unchanged)
    IF @MarkForfeits = 1
    BEGIN
        UPDATE HS_Scores SET Forfeit = 1
        WHERE (Home_Score + Visitor_Score) = 1 AND Forfeit = 0
          AND (@State IS NULL OR Home LIKE '%' + @State + '%' OR Visitor LIKE '%' + @State + '%')
          AND (@SeasonStart IS NULL OR Season >= @SeasonStart)
          AND (@SeasonEnd IS NULL OR Season <= @SeasonEnd);
        PRINT 'Games marked as forfeits: ' + CAST(@@ROWCOUNT AS VARCHAR(10));

        UPDATE HS_Scores SET Forfeit = 0
        WHERE (Home_Score + Visitor_Score) <> 1 AND Forfeit = 1
          AND (@State IS NULL OR Home LIKE '%' + @State + '%' OR Visitor LIKE '%' + @State + '%')
          AND (@SeasonStart IS NULL OR Season >= @SeasonStart)
          AND (@SeasonEnd IS NULL OR Season <= @SeasonEnd);
        PRINT 'Games unmarked as forfeits: ' + CAST(@@ROWCOUNT AS VARCHAR(10));
    END

    CREATE TABLE #DuplicatesToRemove (ID UNIQUEIDENTIFIER, KeptID UNIQUEIDENTIFIER);

    -- ---------------------------------------------------------------------
    -- Step 2: Exact duplicates
    -- ---------------------------------------------------------------------
    INSERT INTO #DuplicatesToRemove (ID, KeptID)
    SELECT d.ID, x.MinID
    FROM HS_Scores d
    INNER JOIN (
        SELECT Season, Home, Visitor, Home_Score, Visitor_Score, MIN(ID) AS MinID
        FROM HS_Scores
        WHERE (@State IS NULL OR Home LIKE '%' + @State + '%' OR Visitor LIKE '%' + @State + '%')
          AND (@SeasonStart IS NULL OR Season >= @SeasonStart)
          AND (@SeasonEnd IS NULL OR Season <= @SeasonEnd)
        GROUP BY Season, Home, Visitor, Home_Score, Visitor_Score
        HAVING COUNT(*) > 1
    ) x ON d.Season = x.Season AND d.Home = x.Home AND d.Visitor = x.Visitor
        AND d.Home_Score = x.Home_Score AND d.Visitor_Score = x.Visitor_Score
        AND d.ID <> x.MinID;

    PRINT '--- Found the following REGULAR duplicates to be archived and deleted: ---';
    SELECT * FROM dbo.HS_Scores WHERE ID IN (SELECT ID FROM #DuplicatesToRemove);

    -- Archive full row snapshot to HS_Scores_Change_Log before deleting
    -- FIX 1: LEFT(...,255) guards against ever exceeding OldValue's limit again.
    INSERT INTO HS_Scores_Change_Log (ScoresID, InvestigationID, FieldChanged, OldValue, NewValue, Reason, Script)
    SELECT
        d.ID,
        NULL,
        'ROW_DELETED',
        LEFT(CONCAT('Season=', d.Season, ', Date=', CONVERT(VARCHAR(10), d.Date, 120),
               ', Home=''', d.Home, '''', ', Home_Score=', d.Home_Score,
               ', Visitor=''', d.Visitor, '''', ', Visitor_Score=', d.Visitor_Score,
               ', Location=''', ISNULL(d.Location, ''), '''',
               ', Location2=''', ISNULL(d.Location2, ''), '''',
               ', Source=''', ISNULL(d.Source, ''), '''',
               ', Forfeit=', d.Forfeit, ', OT=''', ISNULL(d.OT, ''), ''''), 255),
        NULL,
        CONCAT(@RunReason, ' -- exact duplicate of surviving row ', dup.KeptID),
        'RemoveDuplicateGamesParameterized (regular)'
    FROM dbo.HS_Scores d
    INNER JOIN #DuplicatesToRemove dup ON dup.ID = d.ID;

    DELETE FROM HS_Scores WHERE ID IN (SELECT ID FROM #DuplicatesToRemove);
    PRINT 'Regular duplicates archived and deleted: ' + CAST(@@ROWCOUNT AS VARCHAR(10));
    TRUNCATE TABLE #DuplicatesToRemove;

    -- ---------------------------------------------------------------------
    -- Step 3: Team-swapped duplicates
    -- ---------------------------------------------------------------------
    INSERT INTO #DuplicatesToRemove (ID, KeptID)
    SELECT s.ID, x.MinID
    FROM HS_Scores s
    INNER JOIN (
        SELECT
            Season,
            CASE WHEN Home < Visitor THEN Home ELSE Visitor END AS Team1,
            CASE WHEN Home < Visitor THEN Visitor ELSE Home END AS Team2,
            CASE WHEN Home_Score < Visitor_Score THEN Home_Score ELSE Visitor_Score END AS Score1,
            CASE WHEN Home_Score < Visitor_Score THEN Visitor_Score ELSE Home_Score END AS Score2,
            MIN(ID) AS MinID
        FROM HS_Scores
        WHERE (@State IS NULL OR Home LIKE '%' + @State + '%' OR Visitor LIKE '%' + @State + '%')
          AND (@SeasonStart IS NULL OR Season >= @SeasonStart)
          AND (@SeasonEnd IS NULL OR Season <= @SeasonEnd)
        GROUP BY
            Season,
            CASE WHEN Home < Visitor THEN Home ELSE Visitor END,
            CASE WHEN Home < Visitor THEN Visitor ELSE Home END,
            CASE WHEN Home_Score < Visitor_Score THEN Home_Score ELSE Visitor_Score END,
            CASE WHEN Home_Score < Visitor_Score THEN Visitor_Score ELSE Home_Score END
        HAVING COUNT(*) > 1
    ) x ON s.Season = x.Season
        AND CASE WHEN s.Home < s.Visitor THEN s.Home ELSE s.Visitor END = x.Team1
        AND CASE WHEN s.Home < s.Visitor THEN s.Visitor ELSE s.Home END = x.Team2
        AND CASE WHEN s.Home_Score < s.Visitor_Score THEN s.Home_Score ELSE s.Visitor_Score END = x.Score1
        AND CASE WHEN s.Home_Score < s.Visitor_Score THEN s.Visitor_Score ELSE s.Home_Score END = x.Score2
        AND s.ID <> x.MinID;

    PRINT '--- Found the following SWAPPED duplicates to be archived and deleted: ---';
    SELECT * FROM dbo.HS_Scores WHERE ID IN (SELECT ID FROM #DuplicatesToRemove);

    INSERT INTO HS_Scores_Change_Log (ScoresID, InvestigationID, FieldChanged, OldValue, NewValue, Reason, Script)
    SELECT
        d.ID,
        NULL,
        'ROW_DELETED',
        LEFT(CONCAT('Season=', d.Season, ', Date=', CONVERT(VARCHAR(10), d.Date, 120),
               ', Home=''', d.Home, '''', ', Home_Score=', d.Home_Score,
               ', Visitor=''', d.Visitor, '''', ', Visitor_Score=', d.Visitor_Score,
               ', Location=''', ISNULL(d.Location, ''), '''',
               ', Location2=''', ISNULL(d.Location2, ''), '''',
               ', Source=''', ISNULL(d.Source, ''), '''',
               ', Forfeit=', d.Forfeit, ', OT=''', ISNULL(d.OT, ''), ''''), 255),
        NULL,
        CONCAT(@RunReason, ' -- team/score-swapped duplicate of surviving row ', dup.KeptID),
        'RemoveDuplicateGamesParameterized (swapped)'
    FROM dbo.HS_Scores d
    INNER JOIN #DuplicatesToRemove dup ON dup.ID = d.ID;

    DELETE FROM HS_Scores WHERE ID IN (SELECT ID FROM #DuplicatesToRemove);
    PRINT 'Swapped duplicates archived and deleted: ' + CAST(@@ROWCOUNT AS VARCHAR(10));
    DROP TABLE #DuplicatesToRemove;

    PRINT '-----------------------------------';
    PRINT 'Parameters used:';
    PRINT 'State filter: ' + ISNULL(@State, 'None');
    PRINT 'Season range: ' + ISNULL(CAST(@SeasonStart AS VARCHAR(10)), 'First') + ' to ' + ISNULL(CAST(@SeasonEnd AS VARCHAR(10)), 'Last');
    PRINT 'Mark forfeits: ' + CASE WHEN @MarkForfeits = 1 THEN 'Yes' ELSE 'No' END;
    PRINT 'Process completed at ' + CONVERT(VARCHAR, GETDATE(), 120);
END

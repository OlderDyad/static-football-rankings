USE [hs_football_database]
GO

SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

CREATE OR ALTER PROCEDURE [dbo].[CalculateRankings_v5]
    @LeagueType     VARCHAR(50),
    @BeginSeason    INT,
    @EndSeason      INT,
    @Week           INT,
    @MaxLoops       INT = 2048,
    @LogFrequency   INT = 100,
    @DebugMode      BIT = 1
AS
BEGIN
    SET NOCOUNT ON;

    -- =========================================================================
    -- Configuration & Setup
    -- =========================================================================
    DECLARE @GlobalStartTime DATETIME = GETDATE();
    DECLARE @StepStart DATETIME;
    DECLARE @RankingsTable VARCHAR(100);
    DECLARE @SQL NVARCHAR(MAX);
    DECLARE @LogMsg NVARCHAR(MAX);

    -- 1. Validation: Check if dependent function exists
    IF OBJECT_ID('dbo.Loop_Query_Step_6v2') IS NULL
    BEGIN
        RAISERROR('Critical Error: Function [dbo].[Loop_Query_Step_6v2] not found. Please execute Loop_Query_Step_6v2.sql first.', 16, 1);
        RETURN;
    END

    -- 2. Get target table mapping
    SELECT @RankingsTable = RankingsTable
    FROM LeagueConfig
    WHERE LeagueType = @LeagueType;

    IF @RankingsTable IS NULL
    BEGIN
        PRINT 'Error: No configuration found for LeagueType: ' + ISNULL(@LeagueType, 'NULL');
        RETURN;
    END

    PRINT '==============================================================================';
    PRINT 'Starting Ranking Calculation V5 (Optimized & Validated)';
    PRINT 'League: ' + @LeagueType;
    PRINT 'Target Table: ' + @RankingsTable;
    PRINT 'Time: ' + CONVERT(VARCHAR(20), @GlobalStartTime, 120);
    PRINT '==============================================================================';

    -- =========================================================================
    -- Cleanup (Global)
    -- =========================================================================
    EXEC [dbo].[CleanupRankingTables];
    EXEC [dbo].[LogRankingsMemoryUsage] @BeginSeason, 'Initial Cleanup';

    -- =========================================================================
    -- Season Loop
    -- =========================================================================
    DECLARE @CurrentSeason INT = @BeginSeason;
    DECLARE @Direction INT = CASE WHEN @EndSeason >= @BeginSeason THEN 1 ELSE -1 END;

    WHILE ((@Direction = 1 AND @CurrentSeason <= @EndSeason) 
        OR (@Direction = -1 AND @CurrentSeason >= @EndSeason))
    BEGIN
        SET @StepStart = GETDATE();
        PRINT 'Processing Season: ' + CAST(@CurrentSeason AS VARCHAR);

        -- Log Season Start
        INSERT INTO dbo.RankingsProcessLog (LogTime, Season, StepDescription, Comments, RowsProcessed)
        VALUES (GETDATE(), @CurrentSeason, 'Season Start', 'Starting processing', 0);

        -- Check for data existence
        DECLARE @HasData BIT = 0;
        IF @LeagueType = '1' AND EXISTS (SELECT 1 FROM HS_Scores WHERE Season = @CurrentSeason) SET @HasData = 1;
        ELSE IF @LeagueType = '2' AND EXISTS (SELECT 1 FROM College_Scores WHERE Season = @CurrentSeason) SET @HasData = 1;
        ELSE IF @LeagueType = '3' AND EXISTS (SELECT 1 FROM NFL_Scores WHERE Season = @CurrentSeason) SET @HasData = 1;
        ELSE IF @LeagueType = '4' AND EXISTS (SELECT 1 FROM pScores WHERE Season = @CurrentSeason) SET @HasData = 1;

        IF @HasData = 0
        BEGIN
            PRINT '  -> No data for season ' + CAST(@CurrentSeason AS VARCHAR) + '. Skipping.';
            SET @CurrentSeason = @CurrentSeason + @Direction;
            CONTINUE;
        END

        BEGIN TRY
            -- =========================================================================
            -- 1. AGGRESSIVE DATA CLEANUP
            -- =========================================================================
            -- Critical: Delete ALL rows for the season from staging tables.
            -- Previous versions filtered by Week, leaving "ghost" rows from other weeks/runs
            -- that caused Cartesian explosions (duplication) in joins.
            DELETE FROM [143_Quality_Scores_Union_Query_DB] WHERE Season = @CurrentSeason;
            DELETE FROM [153_Quality_Scores_Union_Query_DB] WHERE Season = @CurrentSeason;

            SET @SQL = N'DELETE FROM ' + QUOTENAME(@RankingsTable) + ' WHERE Season = @S AND Week = @W';
            EXEC sp_executesql @SQL, N'@S INT, @W INT', @CurrentSeason, @Week;

            -- =========================================================================
            -- 2. GAME DATA PREPARATION (ScoresWinLoss)
            -- =========================================================================
            SET @StepStart = GETDATE();
            
            DELETE FROM dbo.ScoresWinLossResults WHERE Season = @CurrentSeason;
            
            PRINT '  -> Populating game data (ScoresWinLoss)...';
            EXEC dbo.ScoresWinLoss @Season = @CurrentSeason, @Week = @Week, @LeagueType = @LeagueType;
            
            DECLARE @GameCount INT = (SELECT COUNT(*) FROM dbo.ScoresWinLossResults WHERE Season = @CurrentSeason);
            PRINT '     Games Loaded: ' + CAST(@GameCount AS VARCHAR) + ' (' + CAST(DATEDIFF(MILLISECOND, @StepStart, GETDATE()) AS VARCHAR) + ' ms)';

            INSERT INTO dbo.RankingsProcessLog (LogTime, Season, StepDescription, Comments, RowsProcessed)
            VALUES (GETDATE(), @CurrentSeason, 'Game Data Ready', 'ScoresWinLoss executed', @GameCount);

            IF @GameCount = 0
            BEGIN
                PRINT '  -> WARNING: No games found for season ' + CAST(@CurrentSeason AS VARCHAR) + '. Stopping season.';
                 SET @CurrentSeason = @CurrentSeason + @Direction;
                CONTINUE;
            END

            -- =========================================================================
            -- 3. PRE-SEEDING (Step 1 of Algo)
            -- =========================================================================
            SET @StepStart = GETDATE();
            
            -- MAPPING EXPLANATION (Fixing System-Wide Column Swapping):
            -- The source function dbo.Power_Rankings_Prelim returns columns with confusing names.
            -- We map them to the CORRECT target columns in [143] based on their actual value content.
            -- 
            -- Source Column (Prelim)                        |  Content Value  | Target Column (143)
            -- --------------------------------------------- | --------------- | -------------------
            -- Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss    |  ~90.0 (Margin) | Avg_Of_Avg_Of_Home_Modified_Score
            -- Avg_Of_Avg_Of_Home_Modified_Log_Score         |  ~2.0  (Win/L)  | Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss
            -- Avg_Of_Avg_Of_Home_Modified_Score             |  ~9.0  (Log)    | Avg_Of_Avg_Of_Home_Modified_Log_Score
            
            INSERT INTO [143_Quality_Scores_Union_Query_DB] (
                Season, Home, Week, SeasonHome, Forfeit,
                Avg_Of_Avg_Of_Home_Modified_Score,          -- TARGET: Margin Rating (~90)
                Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss, -- TARGET: Win/Loss Rating (~2)
                Avg_Of_Avg_Of_Home_Modified_Log_Score,      -- TARGET: Log Rating (~9)
                Max_Min_Margin,                             
                Max_Performance, Min_Performance,
                Offense, Defense, Best_Worst_Win_Loss
            )
            SELECT
                Season, 
                Home, 
                @Week,
                CAST(Season AS NVARCHAR(255)) + Home, -- Ensure Cast matches Table Type
                0 AS Forfeit,
                ISNULL(Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss, 0), -- Maps to Margin
                ISNULL(Avg_Of_Avg_Of_Home_Modified_Log_Score, 0),      -- Maps to Win/Loss 
                ISNULL(Avg_Of_Avg_Of_Home_Modified_Score, 0),          -- Maps to Log 
                ISNULL(Max_Min_Margin, 0),
                ISNULL(Max_Performance, 0),
                ISNULL(Min_Performance, 0),
                ISNULL(Offense, 0),
                ISNULL(Defense, 0),
                ISNULL(Best_Worst_Win_Loss, 0)
            FROM dbo.Power_Rankings_Prelim(@LeagueType, @CurrentSeason);
            
            DECLARE @TeamCount BIGINT = @@ROWCOUNT;
            PRINT '  -> Pre-seeded ' + CAST(@TeamCount AS VARCHAR) + ' teams (' + CAST(DATEDIFF(MILLISECOND, @StepStart, GETDATE()) AS VARCHAR) + ' ms)';

            INSERT INTO dbo.RankingsProcessLog (LogTime, Season, StepDescription, Comments, RowsProcessed)
            VALUES (GETDATE(), @CurrentSeason, 'Pre-Seeding Complete', 'Populated [143]', @TeamCount);

            -- Validation: Check for duplicates immediately
            DECLARE @DistinctTeams INT;
            SELECT @DistinctTeams = COUNT(DISTINCT SeasonHome) FROM [143_Quality_Scores_Union_Query_DB] WHERE Season = @CurrentSeason;
            
            IF @TeamCount > @DistinctTeams
            BEGIN
                PRINT '  -> CRITICAL WARNING: Duplicate teams detected! Total: ' + CAST(@TeamCount AS VARCHAR) + ', Distinct: ' + CAST(@DistinctTeams AS VARCHAR);
                -- Consider aborting here, but we will let it proceed with warning for now.
                -- Ideally, the TRUNCATE/DELETE above solved this.
            END
            
            IF @DebugMode = 1
            BEGIN
                -- Validation: Sample Check
                DECLARE @CheckMargin FLOAT, @CheckWL FLOAT;
                SELECT TOP 1 @CheckMargin = Avg_Of_Avg_Of_Home_Modified_Score, @CheckWL = Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss
                FROM [143_Quality_Scores_Union_Query_DB] WHERE Season = @CurrentSeason ORDER BY Avg_Of_Avg_Of_Home_Modified_Score DESC;
                
                PRINT '     Validation Sample (Top Team): Margin=' + CAST(@CheckMargin AS VARCHAR) + ' (Exp ~90), WL=' + CAST(@CheckWL AS VARCHAR) + ' (Exp ~1-3)';
            END

            -- =========================================================================
            -- 4. ITERATION LOOP
            -- =========================================================================
            DECLARE @LoopCounter INT = 0;
            DECLARE @Convergence FLOAT = 1.0;
            SET @StepStart = GETDATE();

            WHILE (@LoopCounter < @MaxLoops) AND (@Convergence > 0.0001) -- Convergence threshold
            BEGIN
                -- Clear Output Table (153) for this season
                DELETE FROM [153_Quality_Scores_Union_Query_DB] WHERE Season = @CurrentSeason;

                -- Execute Loop Step (Calculates 153 from 143 logic via Loop_Query_Step_6v2)
                INSERT INTO [153_Quality_Scores_Union_Query_DB] (
                    Season, Home, Week, SeasonHome,
                    Avg_Of_Avg_Of_Home_Modified_Score,
                    Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss,
                    Avg_Of_Avg_Of_Home_Modified_Log_Score,
                    Max_Min_Margin, Max_Performance, Min_Performance,
                    Offense, Defense, Best_Worst_Win_Loss
                )
                SELECT 
                    Season, Home, @Week, CAST(Season AS NVARCHAR(255)) + Home,
                    Avg_Of_Avg_Of_Home_Modified_Score,
                    Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss,
                    Avg_Of_Avg_Of_Home_Modified_Log_Score,
                    Max_Min_Margin, Max_Performance, Min_Performance,
                    Offense, Defense, Best_Worst_Win_Loss
                FROM dbo.Loop_Query_Step_6v2(@Week);

                -- Calculate Convergence
                SELECT 
                    @Convergence = SQRT(
                        SUM(POWER(ISNULL(t153.Avg_Of_Avg_Of_Home_Modified_Score, 0) - ISNULL(t143.Avg_Of_Avg_Of_Home_Modified_Score, 0), 2)) 
                        / NULLIF(COUNT_BIG(*), 0)
                    )
                FROM [153_Quality_Scores_Union_Query_DB] t153
                JOIN [143_Quality_Scores_Union_Query_DB] t143
                    ON t153.SeasonHome = t143.SeasonHome
                WHERE t153.Season = @CurrentSeason -- Efficiency: Filter by season (though table should only have current)
                  AND t143.Season = @CurrentSeason;

                -- Prepare for next loop: Move 153 (New) -> 143 (Old/Input)
                DELETE FROM [143_Quality_Scores_Union_Query_DB] WHERE Season = @CurrentSeason;

                INSERT INTO [143_Quality_Scores_Union_Query_DB] (
                    Season, Home, Week, SeasonHome, Forfeit,
                    Avg_Of_Avg_Of_Home_Modified_Score,
                    Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss,
                    Avg_Of_Avg_Of_Home_Modified_Log_Score,
                    Max_Min_Margin, Max_Performance, Min_Performance,
                    Offense, Defense, Best_Worst_Win_Loss
                )
                SELECT 
                    Season, Home, Week, SeasonHome, 0,
                    Avg_Of_Avg_Of_Home_Modified_Score,
                    Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss,
                    Avg_Of_Avg_Of_Home_Modified_Log_Score,
                    Max_Min_Margin, Max_Performance, Min_Performance,
                    Offense, Defense, Best_Worst_Win_Loss
                FROM [153_Quality_Scores_Union_Query_DB];

                SET @LoopCounter += 1;

                -- Logging
                IF (@LoopCounter % @LogFrequency) = 0
                BEGIN
                    SET @LogMsg = 'Loop: ' + CAST(@LoopCounter AS VARCHAR) + ', Convergence: ' + CAST(@Convergence AS VARCHAR(20));
                    PRINT '    ' + @LogMsg;
                    
                    INSERT INTO dbo.RankingsProcessLog (LogTime, Season, StepDescription, Comments, RowsProcessed)
                    VALUES (GETDATE(), @CurrentSeason, 'Convergence Loop', @LogMsg, @TeamCount);
                END
            END;

            -- =========================================================================
            -- 5. FINAL INSERT (Write to Production Table)
            -- =========================================================================
            PRINT '  -> Converged after ' + CAST(@LoopCounter AS VARCHAR) + ' loops. (' + CAST(DATEDIFF(MINUTE, @StepStart, GETDATE()) AS VARCHAR) + ' mins)';
            
            INSERT INTO dbo.RankingsProcessLog (LogTime, Season, StepDescription, Comments, RowsProcessed)
            VALUES (GETDATE(), @CurrentSeason, 'Season Complete', 'Loops: ' + CAST(@LoopCounter AS VARCHAR), @TeamCount);
            
            SET @SQL = N'
            INSERT INTO ' + QUOTENAME(@RankingsTable) + ' (
                Season, Home, Week, Date_Added,
                Avg_Of_Avg_Of_Home_Modified_Score,          -- Margin Rating
                Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss, -- Win/Loss Rating
                Avg_Of_Avg_Of_Home_Modified_Log_Score,      -- Log Rating
                Max_Min_Margin,                             
                Max_Performance, Min_Performance,
                Offense, Defense, Best_Worst_Win_Loss
            )
            SELECT
                Season, Home, Week, GETDATE(),
                ROUND(ISNULL(Avg_Of_Avg_Of_Home_Modified_Score, 0), 5),
                ROUND(ISNULL(Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss, 0), 5),
                ROUND(ISNULL(Avg_Of_Avg_Of_Home_Modified_Log_Score, 0), 5),
                ROUND(ISNULL(Max_Min_Margin, 0), 5),
                ROUND(ISNULL(Max_Performance, 0), 5),
                ROUND(ISNULL(Min_Performance, 0), 5),
                ROUND(ISNULL(Offense, 0), 5),
                ROUND(ISNULL(Defense, 0), 5),
                ROUND(ISNULL(Best_Worst_Win_Loss, 0), 5)
            FROM [153_Quality_Scores_Union_Query_DB]
            WHERE Season = @S AND Week = @W';

            EXEC sp_executesql @SQL, N'@S INT, @W INT', @CurrentSeason, @Week;

            -- Clean up after finish
            DELETE FROM [143_Quality_Scores_Union_Query_DB] WHERE Season = @CurrentSeason;
            DELETE FROM [153_Quality_Scores_Union_Query_DB] WHERE Season = @CurrentSeason;

        END TRY
        BEGIN CATCH
            PRINT '  ERROR in Season ' + CAST(@CurrentSeason AS VARCHAR) + ': ' + ERROR_MESSAGE();
            
            INSERT INTO dbo.RankingsProcessLog (LogTime, Season, StepDescription, Comments, RowsProcessed)
            VALUES (GETDATE(), @CurrentSeason, 'ERROR', LEFT(ERROR_MESSAGE(), 250), 0);
        END CATCH

        SET @CurrentSeason = @CurrentSeason + @Direction;
    END

    PRINT '==============================================================================';
    PRINT 'Process Complete.';
    PRINT 'Total Duration: ' + CAST(DATEDIFF(MINUTE, @GlobalStartTime, GETDATE()) AS VARCHAR) + ' minutes.';
    PRINT '==============================================================================';
END;

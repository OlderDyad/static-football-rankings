-- ADOPTED as the active version 2026-09-19, superseding CalculateRankings_v5
-- (plain). v5 (plain) is left in place for reference but should not be run
-- going forward -- CalculateRankings_v5.sql's header has been updated to
-- point here.
--
-- Why this one and not v5_Final: v5_Final (which also exists live in the
-- database, created the same minute as this Fixed version, 2026-01-15)
-- depends on a different, two-parameter function
-- dbo.Loop_Query_Step_6v2_Fixed(@CurrentSeason, @Week), whose own source
-- was never inspected/validated in this session. v5_Fixed's actual body
-- (below) uses the already-deployed one-parameter dbo.Loop_Query_Step_6v2
-- (@Week) and simply adds `WHERE Season = @CurrentSeason` as a post-filter
-- on its output before inserting into table 153. That accomplishes the
-- same season-scoping fix v5_Final's header describes as "critical" --
-- preventing duplicate SeasonHome key collisions across multiple weeks/
-- seasons accumulated in the 143/153 staging tables -- without requiring
-- any additional, unverified database object. v5_Final's extra hardening
-- (TRUNCATE instead of DELETE, forced Season/Week on every insert, an
-- empty-table-153 check, stuck-convergence detection after 50 non-improving
-- loops) is worth adopting later once this run has been validated, but is
-- not required to get correct weekly ratings.
--
-- Scripted from the live database via SSMS Object Explorer ("Script Stored
-- Procedure as -> CREATE To") on 2026-09-19; not previously present in this
-- repo. create_date in sys.objects: 2026-01-15.

USE [hs_football_database]
GO
/****** Object:  StoredProcedure [dbo].[CalculateRankings_v5_Fixed]    Script Date: 9/19/2026 4:38:55 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

/***************************************************************************************************
 * STORED PROCEDURE: [dbo].[CalculateRankings_v5_Fixed]
 *
 * PURPOSE:
 *   Iterative PageRank-style algorithm to calculate team ratings based on game results and
 *   opponent strength. This is v5 with CRITICAL BUG FIXES applied.
 *
 * CRITICAL FIXES IN THIS VERSION:
 *   1. Added WHERE Season = @CurrentSeason to Loop_Query_Step_6v2 call (prevents constraint violations)
 *   2. Added validation that table 153 is not empty after insert
 *   3. Added ISNULL wrappers to prevent NULL aggregate warnings
 *   4. Improved cleanup to ensure no leftover data between runs
 *
 * ALGORITHM:
 *   1. Pre-seed with historical ratings from nearby seasons (Power_Rankings_Prelim)
 *   2. Iteratively refine ratings based on opponent strength
 *   3. Converge when changes between iterations fall below threshold
 *   4. Write final ratings to target table (HS_Rankings, College_Rankings, etc.)
 *
 * PARAMETERS:
 *   @LeagueType     '1'=High School, '2'=College, '3'=NFL, '4'=Pro
 *   @BeginSeason    First season to calculate (inclusive)
 *   @EndSeason      Last season to calculate (inclusive)
 *   @Week           Week number (52 = full season)
 *   @MaxLoops       Maximum iterations before forced stop (default 2048)
 *   @LogFrequency   Print convergence status every N loops (default 100)
 *   @DebugMode      Enable extra diagnostic output (default 1)
 *
 * EXAMPLE USAGE:
 *   EXEC [dbo].[CalculateRankings_v5_Fixed]
 *       @LeagueType = '1',
 *       @BeginSeason = 2024,
 *       @EndSeason = 2024,
 *       @Week = 52,
 *       @DebugMode = 1;
 *
 * VERSION HISTORY:
 *   v5_Fixed (2026-01-15): Applied critical bug fixes for convergence failure
 *   v5 (2025-12-31): Original v5 with column mapping fixes
 *   v4 (2025-12): Original SQL Server migration from Access
 *
 * AUTHOR: David McKnight / Claude
 * LAST MODIFIED: 2026-01-15
 ***************************************************************************************************/

ALTER   PROCEDURE [dbo].[CalculateRankings_v5_Fixed]
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
    PRINT 'Starting Ranking Calculation V5 (Fixed - With Critical Bug Fixes)';
    PRINT 'League: ' + @LeagueType;
    PRINT 'Target Table: ' + @RankingsTable;
    PRINT 'Time: ' + CONVERT(VARCHAR(20), @GlobalStartTime, 120);
    PRINT '==============================================================================';

    -- =========================================================================
    -- Cleanup (Global)
    -- =========================================================================
    PRINT 'Global Cleanup...';
    EXEC [dbo].[CleanupRankingTables];
    EXEC [dbo].[LogRankingsMemoryUsage] @BeginSeason, 'Initial Cleanup';

    -- =========================================================================
    -- Season Loop
    -- =========================================================================
    DECLARE @CurrentSeason INT = @BeginSeason;
    DECLARE @Direction INT = CASE WHEN @EndSeason >= @BeginSeason THEN 1 ELSE -1 END;
    DECLARE @SeasonsProcessed INT = 0;
    DECLARE @SeasonsErrored INT = 0;

    WHILE ((@Direction = 1 AND @CurrentSeason <= @EndSeason)
        OR (@Direction = -1 AND @CurrentSeason >= @EndSeason))
    BEGIN
        SET @StepStart = GETDATE();
        PRINT '';
        PRINT '------------------------------------------------------------------------------';
        PRINT 'Processing Season: ' + CAST(@CurrentSeason AS VARCHAR);
        PRINT '------------------------------------------------------------------------------';

        -- Log Season Start
        INSERT INTO dbo.RankingsProcessLog (LogTime, Season, StepDescription, Comments, RowsProcessed)
        VALUES (GETDATE(), @CurrentSeason, 'Season Start', 'Starting processing', 0);

        -- Check for data existence
        DECLARE @HasData BIT = 0;
        DECLARE @GameCount INT = 0;

        IF @LeagueType = '1'
        BEGIN
            SELECT @GameCount = COUNT(*) FROM HS_Scores WHERE Season = @CurrentSeason;
            IF @GameCount > 0 SET @HasData = 1;
        END
        ELSE IF @LeagueType = '2'
        BEGIN
            SELECT @GameCount = COUNT(*) FROM College_Scores WHERE Season = @CurrentSeason;
            IF @GameCount > 0 SET @HasData = 1;
        END
        ELSE IF @LeagueType = '3'
        BEGIN
            SELECT @GameCount = COUNT(*) FROM NFL_Scores WHERE Season = @CurrentSeason;
            IF @GameCount > 0 SET @HasData = 1;
        END
        ELSE IF @LeagueType = '4'
        BEGIN
            SELECT @GameCount = COUNT(*) FROM pScores WHERE Season = @CurrentSeason;
            IF @GameCount > 0 SET @HasData = 1;
        END

        IF @HasData = 0
        BEGIN
            PRINT '  -> No data for season ' + CAST(@CurrentSeason AS VARCHAR) + '. Skipping.';
            SET @CurrentSeason = @CurrentSeason + @Direction;
            CONTINUE;
        END

        PRINT '  -> Found ' + CAST(@GameCount AS VARCHAR) + ' games for this season';

        BEGIN TRY
            -- =========================================================================
            -- 1. AGGRESSIVE DATA CLEANUP
            -- =========================================================================
            -- Critical: Delete ALL rows for the season from staging tables.
            -- This prevents "ghost" rows from previous runs causing Cartesian explosions.
            PRINT '  Step 1: Cleaning up staging tables...';

            DELETE FROM [143_Quality_Scores_Union_Query_DB] WHERE Season = @CurrentSeason;
            DELETE FROM [153_Quality_Scores_Union_Query_DB] WHERE Season = @CurrentSeason;

            SET @SQL = N'DELETE FROM ' + QUOTENAME(@RankingsTable) + ' WHERE Season = @S AND Week = @W';
            EXEC sp_executesql @SQL, N'@S INT, @W INT', @CurrentSeason, @Week;

            PRINT '     Cleanup complete';

            -- =========================================================================
            -- 2. GAME DATA PREPARATION (ScoresWinLoss)
            -- =========================================================================
            SET @StepStart = GETDATE();
            PRINT '  Step 2: Populating game data (ScoresWinLoss)...';

            DELETE FROM dbo.ScoresWinLossResults WHERE Season = @CurrentSeason;

            EXEC dbo.ScoresWinLoss @Season = @CurrentSeason, @Week = @Week, @LeagueType = @LeagueType;

            SET @GameCount = (SELECT COUNT(*) FROM dbo.ScoresWinLossResults WHERE Season = @CurrentSeason);
            PRINT '     Loaded ' + CAST(@GameCount AS VARCHAR) + ' game records (' +
                  CAST(DATEDIFF(MILLISECOND, @StepStart, GETDATE()) AS VARCHAR) + ' ms)';

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
            PRINT '  Step 3: Pre-seeding from historical ratings...';

            -- MAPPING EXPLANATION (System-Wide Column Naming Convention):
            -- The source function dbo.Power_Rankings_Prelim returns columns with historically
            -- swapped names due to Access-to-SQL migration. We maintain this convention.
            --
            -- Source Column (Prelim)                        |  Content    | Target Column (143)
            -- --------------------------------------------- | ----------- | -------------------
            -- Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss    |  ~90 Margin | Avg_Of_Avg_Of_Home_Modified_Score
            -- Avg_Of_Avg_Of_Home_Modified_Log_Score         |  ~2  Win/L  | Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss
            -- Avg_Of_Avg_Of_Home_Modified_Score             |  ~9  Log    | Avg_Of_Avg_Of_Home_Modified_Log_Score

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
                CAST(Season AS NVARCHAR(255)) + Home,
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
            PRINT '     Pre-seeded ' + CAST(@TeamCount AS VARCHAR) + ' teams (' +
                  CAST(DATEDIFF(MILLISECOND, @StepStart, GETDATE()) AS VARCHAR) + ' ms)';

            INSERT INTO dbo.RankingsProcessLog (LogTime, Season, StepDescription, Comments, RowsProcessed)
            VALUES (GETDATE(), @CurrentSeason, 'Pre-Seeding Complete', 'Populated [143]', @TeamCount);

            -- Validation: Check for duplicates immediately
            DECLARE @DistinctTeams INT;
            SELECT @DistinctTeams = COUNT(DISTINCT SeasonHome)
            FROM [143_Quality_Scores_Union_Query_DB]
            WHERE Season = @CurrentSeason;

            IF @TeamCount > @DistinctTeams
            BEGIN
                PRINT '  -> WARNING: Duplicate teams detected! Total: ' + CAST(@TeamCount AS VARCHAR) +
                      ', Distinct: ' + CAST(@DistinctTeams AS VARCHAR);
                PRINT '     This may indicate data quality issues but will not stop processing.';
            END

            IF @DebugMode = 1
            BEGIN
                -- Validation: Sample Check
                DECLARE @CheckMargin FLOAT, @CheckWL FLOAT;
                SELECT TOP 1
                    @CheckMargin = Avg_Of_Avg_Of_Home_Modified_Score,
                    @CheckWL = Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss
                FROM [143_Quality_Scores_Union_Query_DB]
                WHERE Season = @CurrentSeason
                ORDER BY Avg_Of_Avg_Of_Home_Modified_Score DESC;

                PRINT '     Debug: Top team ratings - Margin=' + CAST(ROUND(@CheckMargin, 2) AS VARCHAR) +
                      ' (expect ~90), WL=' + CAST(ROUND(@CheckWL, 2) AS VARCHAR) + ' (expect ~1-3)';
            END

            -- =========================================================================
            -- 4. ITERATION LOOP
            -- =========================================================================
            DECLARE @LoopCounter INT = 0;
            DECLARE @Convergence FLOAT = 1.0;
            DECLARE @PrevConvergence FLOAT = 999.0;
            DECLARE @StuckCount INT = 0;

            SET @StepStart = GETDATE();
            PRINT '  Step 4: Beginning iterative refinement (target convergence < 0.0001)...';

            WHILE (@LoopCounter < @MaxLoops) AND (@Convergence > 0.0001)
            BEGIN
                -- Clear Output Table (153) for this season ONLY
                DELETE FROM [153_Quality_Scores_Union_Query_DB] WHERE Season = @CurrentSeason;

                -- *** CRITICAL FIX #1: Execute Loop Step with Season Filter ***
                -- The Loop_Query_Step_6v2 function returns ALL seasons in table 143.
                -- We MUST filter to current season to avoid constraint violations.
                INSERT INTO [153_Quality_Scores_Union_Query_DB] (
                    Season, Home, Week, SeasonHome,
                    Avg_Of_Avg_Of_Home_Modified_Score,
                    Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss,
                    Avg_Of_Avg_Of_Home_Modified_Log_Score,
                    Max_Min_Margin, Max_Performance, Min_Performance,
                    Offense, Defense, Best_Worst_Win_Loss
                )
                SELECT
                    Season,
                    Home,
                    @Week,
                    CAST(Season AS NVARCHAR(255)) + Home,
                    ISNULL(Avg_Of_Avg_Of_Home_Modified_Score, 0),
                    ISNULL(Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss, 0),
                    ISNULL(Avg_Of_Avg_Of_Home_Modified_Log_Score, 0),
                    ISNULL(Max_Min_Margin, 0),
                    ISNULL(Max_Performance, 0),
                    ISNULL(Min_Performance, 0),
                    ISNULL(Offense, 0),
                    ISNULL(Defense, 0),
                    ISNULL(Best_Worst_Win_Loss, 0)
                FROM dbo.Loop_Query_Step_6v2(@Week)
                WHERE Season = @CurrentSeason;  -- *** CRITICAL: Filter to current season ***

                -- *** CRITICAL FIX #2: Validate that insert worked ***
                DECLARE @InsertedCount INT = @@ROWCOUNT;

                IF @InsertedCount = 0
                BEGIN
                    PRINT '  -> CRITICAL ERROR: Loop_Query_Step_6v2 returned zero rows for season ' +
                          CAST(@CurrentSeason AS VARCHAR);
                    PRINT '  -> Loop iteration: ' + CAST(@LoopCounter AS VARCHAR);
                    PRINT '  -> Check if ScoresWinLossResults is populated and Loop_Query_Step_6v2 logic is correct.';

                    INSERT INTO dbo.RankingsProcessLog (LogTime, Season, StepDescription, Comments, RowsProcessed)
                    VALUES (GETDATE(), @CurrentSeason, 'ERROR', 'Loop returned zero rows at iteration ' +
                            CAST(@LoopCounter AS VARCHAR), 0);

                    RAISERROR('Loop iteration failed - no data returned from Loop_Query_Step_6v2', 16, 1);
                END

                -- Calculate Convergence (RMSE of rating changes)
                SELECT
                    @Convergence = SQRT(
                        SUM(POWER(
                            ISNULL(t153.Avg_Of_Avg_Of_Home_Modified_Score, 0) -
                            ISNULL(t143.Avg_Of_Avg_Of_Home_Modified_Score, 0),
                        2)) / NULLIF(COUNT_BIG(*), 0)
                    )
                FROM [153_Quality_Scores_Union_Query_DB] t153
                JOIN [143_Quality_Scores_Union_Query_DB] t143
                    ON t153.SeasonHome = t143.SeasonHome
                WHERE t153.Season = @CurrentSeason
                  AND t143.Season = @CurrentSeason;

                -- Check for stuck convergence (not improving)
                IF ABS(@Convergence - @PrevConvergence) < 0.00001
                BEGIN
                    SET @StuckCount += 1;
                    IF @StuckCount > 50
                    BEGIN
                        PRINT '  -> WARNING: Convergence appears stuck at ' + CAST(@Convergence AS VARCHAR(20)) +
                              '. Stopping early at iteration ' + CAST(@LoopCounter AS VARCHAR);

                        INSERT INTO dbo.RankingsProcessLog (LogTime, Season, StepDescription, Comments, RowsProcessed)
                        VALUES (GETDATE(), @CurrentSeason, 'Convergence Stuck',
                                'Stopped at iteration ' + CAST(@LoopCounter AS VARCHAR), @TeamCount);
                        BREAK;
                    END
                END
                ELSE
                BEGIN
                    SET @StuckCount = 0;
                END

                SET @PrevConvergence = @Convergence;

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
                FROM [153_Quality_Scores_Union_Query_DB]
                WHERE Season = @CurrentSeason;

                SET @LoopCounter += 1;

                -- Periodic Logging
                IF (@LoopCounter % @LogFrequency) = 0
                BEGIN
                    SET @LogMsg = 'Loop: ' + CAST(@LoopCounter AS VARCHAR) +
                                  ', Convergence: ' + CAST(ROUND(@Convergence, 6) AS VARCHAR(20));
                    PRINT '    ' + @LogMsg;

                    INSERT INTO dbo.RankingsProcessLog (LogTime, Season, StepDescription, Comments, RowsProcessed)
                    VALUES (GETDATE(), @CurrentSeason, 'Convergence Loop', @LogMsg, @TeamCount);
                END
            END;

            -- =========================================================================
            -- 5. FINAL INSERT (Write to Production Table)
            -- =========================================================================
            DECLARE @ElapsedMinutes INT = DATEDIFF(MINUTE, @StepStart, GETDATE());
            PRINT '     Converged after ' + CAST(@LoopCounter AS VARCHAR) + ' loops in ' +
                  CAST(@ElapsedMinutes AS VARCHAR) + ' minutes';
            PRINT '     Final convergence: ' + CAST(ROUND(@Convergence, 6) AS VARCHAR(20));

            INSERT INTO dbo.RankingsProcessLog (LogTime, Season, StepDescription, Comments, RowsProcessed)
            VALUES (GETDATE(), @CurrentSeason, 'Iteration Complete',
                    'Loops: ' + CAST(@LoopCounter AS VARCHAR) + ', Convergence: ' + CAST(@Convergence AS VARCHAR(20)),
                    @TeamCount);

            PRINT '  Step 5: Writing final ratings to ' + @RankingsTable + '...';

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

            DECLARE @FinalInsertCount INT = @@ROWCOUNT;
            PRINT '     Inserted ' + CAST(@FinalInsertCount AS VARCHAR) + ' teams to production table';

            -- Clean up staging tables after successful completion
            DELETE FROM [143_Quality_Scores_Union_Query_DB] WHERE Season = @CurrentSeason;
            DELETE FROM [153_Quality_Scores_Union_Query_DB] WHERE Season = @CurrentSeason;

            INSERT INTO dbo.RankingsProcessLog (LogTime, Season, StepDescription, Comments, RowsProcessed)
            VALUES (GETDATE(), @CurrentSeason, 'Season Complete',
                    'Duration: ' + CAST(@ElapsedMinutes AS VARCHAR) + 'm, Teams: ' + CAST(@FinalInsertCount AS VARCHAR),
                    @FinalInsertCount);

            SET @SeasonsProcessed += 1;
            PRINT '  Season ' + CAST(@CurrentSeason AS VARCHAR) + ' complete';

        END TRY
        BEGIN CATCH
            SET @SeasonsErrored += 1;

            PRINT '  *** ERROR in Season ' + CAST(@CurrentSeason AS VARCHAR) + ' ***';
            PRINT '  Error Message: ' + ERROR_MESSAGE();
            PRINT '  Error Line: ' + CAST(ERROR_LINE() AS VARCHAR);

            INSERT INTO dbo.RankingsProcessLog (LogTime, Season, StepDescription, Comments, RowsProcessed)
            VALUES (GETDATE(), @CurrentSeason, 'ERROR', LEFT(ERROR_MESSAGE(), 250), 0);
        END CATCH

        SET @CurrentSeason = @CurrentSeason + @Direction;
    END

    -- =========================================================================
    -- Final Summary
    -- =========================================================================
    DECLARE @TotalMinutes INT = DATEDIFF(MINUTE, @GlobalStartTime, GETDATE());

    PRINT '';
    PRINT '==============================================================================';
    PRINT 'PROCESS COMPLETE';
    PRINT '==============================================================================';
    PRINT 'Seasons Processed:  ' + CAST(@SeasonsProcessed AS VARCHAR);
    PRINT 'Seasons Errored:    ' + CAST(@SeasonsErrored AS VARCHAR);
    PRINT 'Total Duration:     ' + CAST(@TotalMinutes AS VARCHAR) + ' minutes';
    PRINT 'End Time:           ' + CONVERT(VARCHAR(20), GETDATE(), 120);
    PRINT '==============================================================================';

    INSERT INTO dbo.RankingsProcessLog (LogTime, Season, StepDescription, Comments, RowsProcessed)
    VALUES (GETDATE(), NULL, 'Process Complete',
            'Processed: ' + CAST(@SeasonsProcessed AS VARCHAR) + ', Errored: ' + CAST(@SeasonsErrored AS VARCHAR),
            @TotalMinutes);
END;

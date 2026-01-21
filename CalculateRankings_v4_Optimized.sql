USE [hs_football_database]
GO
/****** Object:  StoredProcedure [dbo].[CalculateRankings_v4_Optimized]    Script Date: 1/13/2026 9:12:42 AM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
ALTER   PROCEDURE [dbo].[CalculateRankings_v4_Optimized]
    @LeagueType  VARCHAR(50),
    @BeginSeason INT,
    @EndSeason   INT,
    @Week        INT,
    @MaxLoops    INT = 2048,
    @LogFrequency INT = 100
AS
BEGIN
    SET NOCOUNT ON;

    -- Declare all variables
    DECLARE @CurrentSeason       INT = @BeginSeason;
    DECLARE @Direction           INT = CASE WHEN @EndSeason >= @BeginSeason THEN 1 ELSE -1 END;
    DECLARE @StartTime           DATETIME = GETDATE();
    DECLARE @SeasonStartTime     DATETIME;
    DECLARE @RankingsTable       VARCHAR(100);
    DECLARE @SQL                 NVARCHAR(MAX);
    DECLARE @LastProcessedSeason INT = NULL;
    DECLARE @LoopCounter         INT;
    DECLARE @Convergence         FLOAT;
    DECLARE @LastUpdateTime      DATETIME;
    DECLARE @TeamCount           INT;
    DECLARE @RowCount            INT;
    DECLARE @LogMessage          NVARCHAR(MAX);

    -- Initial cleanup
    EXEC [dbo].[CleanupRankingTables];
    EXEC [dbo].[LogRankingsMemoryUsage] @BeginSeason, 'Initial Cleanup';

    -- Get the rankings table name
    SELECT @RankingsTable = RankingsTable
    FROM LeagueConfig
    WHERE LeagueType = @LeagueType;

    -- Initial progress message
    SET @LogMessage = 'Started processing at ' + CONVERT(VARCHAR(20), @StartTime, 120);
    PRINT @LogMessage;
    PRINT REPLICATE('-', 80);

    -- Process each season
    WHILE ((@Direction = 1 AND @CurrentSeason <= @EndSeason)
           OR (@Direction = -1 AND @CurrentSeason >= @EndSeason))
          AND @CurrentSeason IS NOT NULL
    BEGIN
        SET @SeasonStartTime = GETDATE();
        SET @LoopCounter = 0;
        SET @Convergence = 1.0;
        SET @LastUpdateTime = @SeasonStartTime;
        
        -- Log season start
        EXEC [dbo].[LogRankingsMemoryUsage] @CurrentSeason, 'Season Start';
        
        -- Season start notification
        SET @LogMessage = 'Processing ' + CAST(@CurrentSeason AS VARCHAR(4)) + 
                          ' (Started: ' + CONVERT(VARCHAR(20), @SeasonStartTime, 120) + ')';
        PRINT @LogMessage;

		DECLARE @HasData BIT = 0;

		IF @LeagueType = '1' AND EXISTS (SELECT 1 FROM HS_Scores WHERE Season = @CurrentSeason)
			SET @HasData = 1;
		ELSE IF @LeagueType = '2' AND EXISTS (SELECT 1 FROM College_Scores WHERE Season = @CurrentSeason)
			SET @HasData = 1;
		ELSE IF @LeagueType = '3' AND EXISTS (SELECT 1 FROM NFL_Scores WHERE Season = @CurrentSeason)
			SET @HasData = 1;
		ELSE IF @LeagueType = '4' AND EXISTS (SELECT 1 FROM pScores WHERE Season = @CurrentSeason)
			SET @HasData = 1;

		IF @HasData = 1
		BEGIN
            -- Clean up existing data for the current season and week
            EXEC [dbo].[CleanupRankingTables]; -- Assuming this cleans iteration tables too or is safe to call
            
            BEGIN TRY
                DELETE FROM [143_Quality_Scores_Union_Query_DB]
                WHERE Season = @CurrentSeason AND Week = @Week;

                DELETE FROM [153_Quality_Scores_Union_Query_DB]
                WHERE Season = @CurrentSeason AND Week = @Week;

                DELETE FROM [163_Quality_Scores_Union_Query_DB] -- If this is another iteration table
                WHERE Season = @CurrentSeason AND Week = @Week;

                SET @SQL = N'
                    DELETE FROM ' + QUOTENAME(@RankingsTable) + '
                    WHERE Season = @Season AND Week = @Week';
                
                EXEC sp_executesql 
                    @SQL,
                    N'@Season INT, @Week INT',
                    @CurrentSeason, 
                    @Week;

                EXEC [dbo].[LogRankingsMemoryUsage] @CurrentSeason, 'Data Cleanup Complete';
                CHECKPOINT;

-- Initialize data into 143_... table
                INSERT INTO [143_Quality_Scores_Union_Query_DB] (
                    Season, Home, Avg_Of_Avg_Of_Home_Modified_Score,
                    Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss,
                    Avg_Of_Avg_Of_Home_Modified_Log_Score,
                    Max_Min_Margin, Max_Performance, Min_Performance,
                    Offense, Defense, Best_Worst_Win_Loss,
                    Week, SeasonHome, Forfeit 
                )
                SELECT  -- This SELECT provides the data for the INSERT above
                    Season, Home, 
                    ISNULL(Avg_Of_Avg_Of_Home_Modified_Score, 0),
                    ISNULL(Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss, 0),
                    ISNULL(Avg_Of_Avg_Of_Home_Modified_Log_Score, 0),
                    ISNULL(Max_Min_Margin, 0),
                    ISNULL(Max_Performance, 0),
                    ISNULL(Min_Performance, 0),
                    ISNULL(Offense, 0),
                    ISNULL(Defense, 0),
                    ISNULL(Best_Worst_Win_Loss, 0),
                    @Week, 
                    CAST(Season AS NVARCHAR(10)) + Home,
                    0 AS Forfeit 
                FROM dbo.Power_Rankings_Prelim(@LeagueType, @CurrentSeason);

                -- Temp debug step begin:  --- THIS IS THE CORRECT PLACEMENT ---
                DECLARE @TestRowCount INT;
                SELECT @TestRowCount = COUNT(*) 
                FROM [143_Quality_Scores_Union_Query_DB] 
                WHERE Season = @CurrentSeason AND Week = @Week; 

                PRINT 'DEBUG: Row count in [143_Quality_Scores_Union_Query_DB] AFTER INSERT from Power_Rankings_Prelim for Season ' 
                        + CAST(@CurrentSeason AS VARCHAR) + ', Week ' + CAST(@Week AS VARCHAR) + ': ' + CAST(@TestRowCount AS VARCHAR);

                IF @TestRowCount = 0 
                BEGIN
                    PRINT 'DEBUG: Power_Rankings_Prelim output for this season (TOP 5) because TestRowCount was 0:';
                    SELECT TOP 5 * FROM dbo.Power_Rankings_Prelim(@LeagueType, @CurrentSeason);
                END
                -- Temp debug step end:

                -- Log initial data load (this was already here)
                EXEC [dbo].[LogRankingsMemoryUsage] @CurrentSeason, 'Initial Data Load into 143_Table';
                CHECKPOINT;


                -- Main iteration loop
                WHILE (@LoopCounter < @MaxLoops) AND (@Convergence > 0.0001)
                BEGIN
                    IF (@LoopCounter % @LogFrequency) = 0
                    BEGIN
                        SET @LogMessage = 'Loop: ' + CAST(@LoopCounter AS VARCHAR(10)) + 
                                          ', Convergence: ' + CAST(@Convergence AS VARCHAR(20));
                        
                        EXEC [dbo].[LogRankingsMemoryUsage] 
                            @CurrentSeason, 
                            'Convergence Loop',
                            NULL, -- Or @TeamCount if it's meaningful here
                            @LogMessage;
                    END

                    TRUNCATE TABLE [153_Quality_Scores_Union_Query_DB];

                    -- CHANGE 1: Add ISNULL when populating 153_... table
                    INSERT INTO [153_Quality_Scores_Union_Query_DB] (
                        Season, Home, Avg_Of_Avg_Of_Home_Modified_Score,
                        Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss,
                        Avg_Of_Avg_Of_Home_Modified_Log_Score,
                        Max_Min_Margin, Max_Performance, Min_Performance,
                        Offense, Defense, Best_Worst_Win_Loss,
                        Week, SeasonHome
                    )
                    SELECT 
                        Season, Home, 
                        ISNULL(Avg_Of_Avg_Of_Home_Modified_Score, 0),
                        ISNULL(Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss, 0),
                        ISNULL(Avg_Of_Avg_Of_Home_Modified_Log_Score, 0),
                        ISNULL(Max_Min_Margin, 0), 
                        ISNULL(Max_Performance, 0), 
                        ISNULL(Min_Performance, 0),
                        ISNULL(Offense, 0), 
                        ISNULL(Defense, 0), 
                        ISNULL(Best_Worst_Win_Loss, 0),
                        @Week, CAST(Season AS NVARCHAR(10)) + Home
                    FROM dbo.Loop_Query_Step_6(@LeagueType, @CurrentSeason, @Week);

                    -- CHANGE 2: Add ISNULL to convergence calculation
                    SELECT 
                        @Convergence = SQRT(
                            SUM(POWER(ISNULL(t153.Avg_Of_Avg_Of_Home_Modified_Score, 0) - ISNULL(t143.Avg_Of_Avg_Of_Home_Modified_Score, 0), 2)) 
                            / CASE WHEN COUNT_BIG(*) = 0 THEN 1 ELSE COUNT_BIG(*) END -- Avoid division by zero
                        ),
                        @TeamCount = COUNT_BIG(*)
                    FROM [153_Quality_Scores_Union_Query_DB] t153
                    JOIN [143_Quality_Scores_Union_Query_DB] t143
                        ON t153.SeasonHome = t143.SeasonHome
                    WHERE t153.Season = @CurrentSeason
                      AND t153.Week   = @Week
                      AND t143.Season = @CurrentSeason
                      AND t143.Week   = @Week;
                    
                    IF @TeamCount = 0 SET @Convergence = 0; -- Or handle as appropriate if no teams match

                    TRUNCATE TABLE [143_Quality_Scores_Union_Query_DB];

                    -- CHANGE 3: Add ISNULL and explicit columns when copying 153_... to 143_...
                    INSERT INTO [143_Quality_Scores_Union_Query_DB] (
                        Season, Home, Avg_Of_Avg_Of_Home_Modified_Score,
                        Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss,
                        Avg_Of_Avg_Of_Home_Modified_Log_Score,
                        Max_Min_Margin, Max_Performance, Min_Performance,
                        Offense, Defense, Best_Worst_Win_Loss,
                        Week, SeasonHome 
                        -- Add Forfeit if it should be carried over or defaulted
                        , Forfeit 
                    )
                    SELECT 
                        Season, Home,
                        ISNULL(Avg_Of_Avg_Of_Home_Modified_Score, 0),
                        ISNULL(Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss, 0),
                        ISNULL(Avg_Of_Avg_Of_Home_Modified_Log_Score, 0),
                        ISNULL(Max_Min_Margin, 0),
                        ISNULL(Max_Performance, 0),
                        ISNULL(Min_Performance, 0),
                        ISNULL(Offense, 0),
                        ISNULL(Defense, 0),
                        ISNULL(Best_Worst_Win_Loss, 0),
                        Week, SeasonHome
                        , 0 AS Forfeit -- Default Forfeit, assuming it's not in 153_... or needs reset
                    FROM [153_Quality_Scores_Union_Query_DB]
                    WHERE Season = @CurrentSeason
                      AND Week = @Week;

                    SET @LoopCounter += 1;
                    
                    IF (@LoopCounter % 500) = 0
                    BEGIN
                        CHECKPOINT;
                        SET @LogMessage = 'Completed ' + CAST(@LoopCounter AS VARCHAR(10)) + ' iterations';
                        EXEC [dbo].[LogRankingsMemoryUsage] 
                            @CurrentSeason, 
                            'Loop Checkpoint',
                            @TeamCount,
                            @LogMessage;
                    END
                END;

                -- Insert final results into the main rankings table
                SET @SQL = N'
                INSERT INTO ' + QUOTENAME(@RankingsTable) + ' (
                    Season, Home, Avg_Of_Avg_Of_Home_Modified_Score,
                    Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss,
                    Avg_Of_Avg_Of_Home_Modified_Log_Score,
                    Max_Min_Margin, Max_Performance, Min_Performance,
                    Offense, Defense, Best_Worst_Win_Loss,
                    Week, Date_Added
                )
                SELECT
                    Season, Home,
                    ROUND(ISNULL(Avg_Of_Avg_Of_Home_Modified_Score, 0), 5),
                    ROUND(ISNULL(Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss, 0), 5),
                    ROUND(ISNULL(Avg_Of_Avg_Of_Home_Modified_Log_Score, 0), 5),
                    ROUND(ISNULL(Max_Min_Margin, 0), 5),
                    ROUND(ISNULL(Max_Performance, 0), 5),
                    ROUND(ISNULL(Min_Performance, 0), 5),
                    ROUND(ISNULL(Offense, 0), 5),
                    ROUND(ISNULL(Defense, 0), 5),
                    ROUND(ISNULL(Best_Worst_Win_Loss, 0), 5),
                    Week,
                    GETDATE()
                FROM [153_Quality_Scores_Union_Query_DB] -- Final iteration results are in 153
                WHERE Season = @Season AND Week = @Week';

                EXEC sp_executesql
                    @SQL,
                    N'@Season INT, @Week INT',
                    @CurrentSeason,
                    @Week;

                EXEC [dbo].[CleanupRankingTables]; -- Cleanup iteration tables
                CHECKPOINT;

                SET @LogMessage = 'Loops: ' + CAST(@LoopCounter AS VARCHAR(10));
                EXEC [dbo].[LogRankingsMemoryUsage] 
                    @CurrentSeason, 
                    'Season Complete',
                    @TeamCount,
                    @LogMessage;

                SET @LastProcessedSeason = @CurrentSeason;

            END TRY
            BEGIN CATCH
                SET @LogMessage = ERROR_MESSAGE() + ' (Line: ' + CAST(ERROR_LINE() AS VARCHAR(10)) + ')';
                EXEC [dbo].[LogRankingsMemoryUsage] 
                    @CurrentSeason, 
                    'Error',
                    NULL,
                    @LogMessage;
                
                PRINT 'Error processing season ' + CAST(@CurrentSeason AS VARCHAR(4)) + ': ' + @LogMessage;
                
                EXEC [dbo].[CleanupRankingTables];
                THROW; -- Re-throw the error after logging and cleanup
            END CATCH;

            SET @CurrentSeason = @CurrentSeason + @Direction;
        END
        ELSE
        BEGIN
            PRINT 'No data found for season ' + CAST(@CurrentSeason AS VARCHAR(4)) + '. Skipping.';
            -- To prevent infinite loop if BeginSeason has no data and EndSeason is far,
            -- we can simply advance the season or stop.
            -- For now, let's just advance. If this is the only season, loop will end.
            SET @CurrentSeason = @CurrentSeason + @Direction;
            IF (@Direction = 1 AND @CurrentSeason > @EndSeason) OR (@Direction = -1 AND @CurrentSeason < @EndSeason)
                SET @CurrentSeason = NULL; -- Ensure loop termination
        END;
    END;

    EXEC [dbo].[CleanupRankingTables];
    EXEC [dbo].[LogRankingsMemoryUsage] NULL, 'Process Complete';

    IF @LastProcessedSeason IS NOT NULL
    BEGIN
        SET @LogMessage = 'Process completed at ' + CONVERT(VARCHAR(20), GETDATE(), 120);
        PRINT @LogMessage;
        SET @LogMessage = 'Processed seasons ' + CAST(@BeginSeason AS VARCHAR(4)) + 
                          ' to ' + CAST(@LastProcessedSeason AS VARCHAR(4));
        PRINT @LogMessage;
        SET @LogMessage = 'Total duration: ' + 
                          CAST(DATEDIFF(MINUTE, @StartTime, GETDATE()) AS VARCHAR(10)) + ' minutes';
        PRINT @LogMessage;
    END
    ELSE
    BEGIN
        PRINT 'No seasons were processed successfully.';
    END;

    -- Show memory usage summary
    SELECT TOP 10
        Season, StepDescription, MemoryUsageMB, TablesizesMB, 
        RowsProcessed, LogTime, Comments
    FROM RankingsProcessLog
    WHERE LogTime >= @StartTime -- Show logs from this run
    ORDER BY LogTime DESC;
END;

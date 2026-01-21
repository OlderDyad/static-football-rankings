USE [hs_football_database]
GO

SET NOCOUNT ON;

PRINT '=======================================================';
PRINT 'LIVE BENCHMARK (AFTER ALL FIXES)';
PRINT '=======================================================';

-- 1. Check if Duplicates Came Back?
SELECT 
    '143 Table' AS TableName,
    CountTotal = COUNT(*),
    CountDistinctKey = COUNT(DISTINCT SeasonHome)
FROM [143_Quality_Scores_Union_Query_DB] WITH (NOLOCK)
WHERE Season = 2023;

-- 2. Run the Query Logic (Top 1000 this time to be sure)
PRINT 'Running Loop Query Logic (TOP 1000)...';
DECLARE @StartTime DATETIME = GETDATE();
DECLARE @Week INT = 52;
DECLARE @Season INT = 2023;

    WITH Step0 AS (
        SELECT 
            swd.Season, 
            swd.Visitor, 
            swd.Home, 
            swd.Week,
            swd.Adj_Log_Margin, 
            swd.Adjusted_Margin, 
            swd.Adjusted_Margin_Win_Loss,
            -- Ratings from Home Team
            ISNULL(qsu1.Avg_Of_Avg_Of_Home_Modified_Score, 0) AS Home_Rating_Margin,
            ISNULL(qsu1.Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss, 0) AS Home_Rating_WinLoss,
            ISNULL(qsu1.Avg_Of_Avg_Of_Home_Modified_Log_Score, 0) AS Home_Rating_Log,
            qsu1.Offense AS Home_Offense,
            qsu1.Defense AS Home_Defense,
            qsu1.Best_Worst_Win_Loss AS Home_BestWorst,
            -- Ratings from Visitor Team
            ISNULL(qsu2.Avg_Of_Avg_Of_Home_Modified_Score, 0) AS Visitor_Rating_Margin,
            ISNULL(qsu2.Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss, 0) AS Visitor_Rating_WinLoss,
            ISNULL(qsu2.Avg_Of_Avg_Of_Home_Modified_Log_Score, 0) AS Visitor_Rating_Log,
            qsu2.Offense AS Visitor_Offense,
            qsu2.Defense AS Visitor_Defense,
            qsu2.Best_Worst_Win_Loss AS Visitor_BestWorst,
            
            swd.Visitor_Score + 1.375 AS Adj_Visitor_Score, 
            swd.Home_Score - 1.375 AS Adj_Home_Score
        FROM 
            dbo.ScoresWinLossResults swd WITH (NOLOCK) -- Add NOLOCK to avoid blocking behind running proc
            LEFT JOIN dbo.[143_Quality_Scores_Union_Query_DB] qsu1 WITH (NOLOCK) ON qsu1.SeasonHome = swd.SeasonHome
            LEFT JOIN dbo.[143_Quality_Scores_Union_Query_DB] qsu2 WITH (NOLOCK) ON qsu2.SeasonHome = swd.SeasonVisitor
        WHERE 
            swd.Week <= @Week
            AND swd.Season = @Season
    ),
    Step1_Home AS (
        SELECT
            Season, Home AS Team, Week,
            (Adjusted_Margin + Visitor_Rating_Margin) AS Margin_Performance,
            (Adjusted_Margin_Win_Loss + Visitor_Rating_WinLoss) AS Win_Loss_Performance,
            (Adj_Log_Margin + Visitor_Rating_Log) AS Log_Performance,
            (Adj_Home_Score + Visitor_Defense) AS Offense_Performance,
            (Adj_Visitor_Score - Visitor_Offense) AS Defense_Performance,
            CASE WHEN Adjusted_Margin > 0 THEN 1 ELSE 0 END AS Win,
            CASE WHEN Adjusted_Margin > 0 THEN Visitor_BestWorst ELSE NULL END AS Win_Points,
            CASE WHEN Adjusted_Margin <= 0 THEN Visitor_BestWorst ELSE NULL END AS Loss_Points
        FROM Step0
    ),
    Step2_Visitor AS (
        SELECT
            Season, Visitor AS Team, Week,
            (Home_Rating_Margin - Adjusted_Margin) AS Margin_Performance,
            (Home_Rating_WinLoss - Adjusted_Margin_Win_Loss) AS Win_Loss_Performance,
            (Home_Rating_Log - Adj_Log_Margin) AS Log_Performance,
            (Adj_Visitor_Score + Home_Defense) AS Offense_Performance,
            (Adj_Home_Score - Home_Offense) AS Defense_Performance,
            CASE WHEN Adjusted_Margin <= 0 THEN 1 ELSE 0 END AS Win,
            CASE WHEN Adjusted_Margin <= 0 THEN Home_BestWorst ELSE NULL END AS Win_Points,
            CASE WHEN Adjusted_Margin > 0 THEN Home_BestWorst ELSE NULL END AS Loss_Points
        FROM Step0
    ),
    Step3_Union AS (
        SELECT * FROM Step1_Home
        UNION ALL
        SELECT * FROM Step2_Visitor
    ),
    Step4_Agg AS (
        SELECT TOP 1000
            Season, Team, Week,
            AVG(Margin_Performance) AS Avg_Margin_Perf
        FROM Step3_Union
        GROUP BY Season, Team, Week
    )
    SELECT * FROM Step4_Agg;

PRINT 'Duration: ' + CAST(DATEDIFF(MILLISECOND, @StartTime, GETDATE()) AS VARCHAR) + ' ms';
PRINT '=======================================================';

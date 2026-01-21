USE [hs_football_database]
GO
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

-- Cleanup: Drop if it exists as a Stored Procedure or a Function
IF OBJECT_ID('dbo.Loop_Query_Step_6v2', 'P') IS NOT NULL 
    DROP PROCEDURE dbo.Loop_Query_Step_6v2;
GO
IF OBJECT_ID('dbo.Loop_Query_Step_6v2', 'IF') IS NOT NULL 
    DROP FUNCTION dbo.Loop_Query_Step_6v2;
GO

CREATE FUNCTION [dbo].[Loop_Query_Step_6v2]
(
    @Week INT
)
RETURNS TABLE
AS
RETURN
(
    -- =========================================================================
    -- Step 0: Join Scores with Previous Iteration Ratings (143 Table)
    -- =========================================================================
    WITH Step0 AS (
        SELECT 
            swd.Season, 
            swd.Visitor, 
            swd.Home, 
            swd.Week,
            swd.Adj_Log_Margin, 
            swd.Adjusted_Margin, 
            swd.Adjusted_Margin_Win_Loss,
            -- Ratings from Home Team (Iteration Input)
            ISNULL(qsu1.Avg_Of_Avg_Of_Home_Modified_Score, 0) AS Home_Rating_Margin,
            ISNULL(qsu1.Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss, 0) AS Home_Rating_WinLoss,
            ISNULL(qsu1.Avg_Of_Avg_Of_Home_Modified_Log_Score, 0) AS Home_Rating_Log,
            qsu1.Offense AS Home_Offense,
            qsu1.Defense AS Home_Defense,
            qsu1.Best_Worst_Win_Loss AS Home_BestWorst,
            -- Ratings from Visitor Team (Iteration Input)
            ISNULL(qsu2.Avg_Of_Avg_Of_Home_Modified_Score, 0) AS Visitor_Rating_Margin,
            ISNULL(qsu2.Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss, 0) AS Visitor_Rating_WinLoss,
            ISNULL(qsu2.Avg_Of_Avg_Of_Home_Modified_Log_Score, 0) AS Visitor_Rating_Log,
            qsu2.Offense AS Visitor_Offense,
            qsu2.Defense AS Visitor_Defense,
            qsu2.Best_Worst_Win_Loss AS Visitor_BestWorst,
            
            -- Game Strength Calcs
            (ISNULL(qsu1.Avg_Of_Avg_Of_Home_Modified_Score, 0) + ISNULL(qsu2.Avg_Of_Avg_Of_Home_Modified_Score, 0)) / 2.0 AS Avg_Margin_Game_Strength,
            (ISNULL(qsu1.Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss, 0) + ISNULL(qsu2.Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss, 0)) / 2.0 AS Avg_WinLoss_Game_Strength,
            (ISNULL(qsu1.Avg_Of_Avg_Of_Home_Modified_Log_Score, 0) + ISNULL(qsu2.Avg_Of_Avg_Of_Home_Modified_Log_Score, 0)) AS Avg_Log_Game_Strength,

            swd.Visitor_Score + 1.375 AS Adj_Visitor_Score, -- (2.75 / 2)
            swd.Home_Score - 1.375 AS Adj_Home_Score
        FROM 
            dbo.ScoresWinLossResults swd
            LEFT JOIN dbo.[143_Quality_Scores_Union_Query_DB] qsu1 ON qsu1.SeasonHome = swd.SeasonHome
            LEFT JOIN dbo.[143_Quality_Scores_Union_Query_DB] qsu2 ON qsu2.SeasonHome = swd.SeasonVisitor
        WHERE 
            swd.Week <= @Week
            -- AND swd.Season is handled by the caller/context usually, but ScoresWinLossResults is populated by Season.
            -- We assume ScoresWinLossResults only contains the relevant season data as configured in the stored proc.
    ),

    -- =========================================================================
    -- Step 1 & 2: Calculate Performance Metrics for Each Side
    -- =========================================================================
    Step1_Home AS (
        SELECT
            Season,
            Home AS Team,
            Week,
            -- Core Algorithm: Performance = AdjustedMargin + OpponentRating - HomeFieldAdvantageAdjustment (Implicit in Margin?)
            -- Legacy Access Logic: [Adjusted Margin] + [143...Avg Of Avg...]
            
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
            Season,
            Visitor AS Team,
            Week,
            -- For Visitor, Margin is inverted? 
            -- Visitor Perf = (OpponentRating - AdjustedMargin)? 
            -- Let's check logic. Loop_Query_Step_2 says: Visitor_Margin_Performance logic wasn't fully pasted in Step 96 but Step 0 had it.
            -- Usually: Visitor Margin = -Home Margin.
            -- Loop_Query_Step_0 had `lq0.Visitor_Margin_Performance`.
            -- Wait, standard rating logic: Rating = OpponentRating + ScoreDiff.
            -- If Home Margin = (Home - Vis) - HFA.
            -- Visitor Margin should be (Vis - Home) + HFA = -(HomeMargin).
            -- Let's assume standard symmetry.
            
            (Home_Rating_Margin - Adjusted_Margin) AS Margin_Performance,
            (Home_Rating_WinLoss - Adjusted_Margin_Win_Loss) AS Win_Loss_Performance,
            (Home_Rating_Log - Adj_Log_Margin) AS Log_Performance,
            
            (Adj_Visitor_Score + Home_Defense) AS Offense_Performance,
            (Adj_Home_Score - Home_Offense) AS Defense_Performance,

            CASE WHEN Adjusted_Margin <= 0 THEN 1 ELSE 0 END AS Win,
            CASE WHEN Adjusted_Margin <= 0 THEN Home_BestWorst ELSE NULL END AS Win_Points,
            CASE WHEN Adjusted_Margin > 0 THEN Home_BestWorst ELSE NULL END AS Loss_Points -- If lost, points from winner
        FROM Step0
    ),

    -- =========================================================================
    -- Step 3: Union Home and Visitor Performances
    -- =========================================================================
    Step3_Union AS (
        SELECT * FROM Step1_Home
        UNION ALL
        SELECT * FROM Step2_Visitor
    ),

    -- =========================================================================
    -- Step 4: Aggregate by Team (Average Performance)
    -- =========================================================================
    Step4_Agg AS (
        SELECT
            Season,
            Team,
            Week,
            ROUND(AVG(Margin_Performance), 5) AS Avg_Margin_Perf,
            ROUND(AVG(Win_Loss_Performance), 5) AS Avg_WinLoss_Perf,
            ROUND(AVG(Log_Performance), 5) AS Avg_Log_Perf,
            ROUND(MAX(Margin_Performance), 5) AS Max_Margin_Perf,
            ROUND(MIN(Margin_Performance), 5) AS Min_Margin_Perf,
            ROUND(AVG(Offense_Performance), 5) AS Avg_Offense,
            ROUND(AVG(Defense_Performance), 5) AS Avg_Defense,
            ISNULL(MAX(Win_Points), MIN(Loss_Points)) AS Best_Worst_Win_Loss
        FROM Step3_Union
        GROUP BY Season, Team, Week
    ),

    -- =========================================================================
    -- Step 6 (Final): Format for Final Output (Step 5 is just distinct passthrough)
    -- =========================================================================
    Step6_Final AS (
        SELECT
            Season,
            Team AS Home, -- Naming convention switch
            Week,
            CAST(Season AS NVARCHAR(255)) + Team AS SeasonHome,
            
            Avg_Margin_Perf AS Avg_Of_Avg_Of_Home_Modified_Score,
            Avg_WinLoss_Perf AS Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss,
            Avg_Log_Perf AS Avg_Of_Avg_Of_Home_Modified_Log_Score,
            
            (Max_Margin_Perf + Min_Margin_Perf) / 2.0 AS Max_Min_Margin,
            Max_Margin_Perf AS Max_Performance,
            Min_Margin_Perf AS Min_Performance,
            
            Avg_Offense AS Offense,
            Avg_Defense AS Defense,
            Best_Worst_Win_Loss
        FROM Step4_Agg
    )

    SELECT * FROM Step6_Final
);

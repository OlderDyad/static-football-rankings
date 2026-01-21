USE [hs_football_database]
GO
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

IF OBJECT_ID('dbo.Power_Rankings_Prelim', 'IF') IS NOT NULL
BEGIN
    PRINT 'Dropping existing function...';
    DROP FUNCTION dbo.Power_Rankings_Prelim;
    PRINT 'Dropped.';
    PRINT '';
END
GO

-- Create corrected version with Season BEFORE Home
CREATE FUNCTION [dbo].[Power_Rankings_Prelim]  
(      
    @LeagueType VARCHAR(50),      
    @Season INT  
)  
RETURNS TABLE  
AS  
RETURN  
(      
    WITH SeasonRankings AS (          
        SELECT               
            Home AS CanonicalTeamName,
            Season,              
            Avg_Of_Avg_Of_Home_Modified_Score,              
            Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss,              
            Avg_Of_Avg_Of_Home_Modified_Log_Score,              
            Max_Min_Margin,              
            Max_Performance,              
            Min_Performance,              
            Offense,              
            Defense,              
            Best_Worst_Win_Loss          
        FROM pRankings
        WHERE @LeagueType = '4'
          AND Season IN (@Season - 2, @Season - 1, @Season + 1, @Season + 2)            
          AND Week = 52
        
        UNION ALL
        
        SELECT               
            Home AS CanonicalTeamName,
            Season,              
            Avg_Of_Avg_Of_Home_Modified_Score,              
            Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss,              
            Avg_Of_Avg_Of_Home_Modified_Log_Score,              
            Max_Min_Margin,              
            Max_Performance,              
            Min_Performance,              
            Offense,              
            Defense,              
            Best_Worst_Win_Loss          
        FROM HS_Rankings
        WHERE @LeagueType = '1'
          AND Season IN (@Season - 2, @Season - 1, @Season + 1, @Season + 2)            
          AND Week = 52
        
        UNION ALL
        
        SELECT               
            Home AS CanonicalTeamName,
            Season,              
            Avg_Of_Avg_Of_Home_Modified_Score,              
            Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss,              
            Avg_Of_Avg_Of_Home_Modified_Log_Score,              
            Max_Min_Margin,              
            Max_Performance,              
            Min_Performance,              
            Offense,              
            Defense,              
            Best_Worst_Win_Loss          
        FROM College_Rankings
        WHERE @LeagueType = '2'
          AND Season IN (@Season - 2, @Season - 1, @Season + 1, @Season + 2)            
          AND Week = 52
        
        UNION ALL
        
        SELECT               
            Home AS CanonicalTeamName,
            Season,              
            Avg_Of_Avg_Of_Home_Modified_Score,              
            Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss,              
            Avg_Of_Avg_Of_Home_Modified_Log_Score,              
            Max_Min_Margin,              
            Max_Performance,              
            Min_Performance,              
            Offense,              
            Defense,              
            Best_Worst_Win_Loss          
        FROM NFL_Rankings
        WHERE @LeagueType = '3'
          AND Season IN (@Season - 2, @Season - 1, @Season + 1, @Season + 2)            
          AND Week = 52
    ),      
    TeamSeasons AS (          
        SELECT DISTINCT               
            TeamName,               
            @Season AS Season           
        FROM (              
            SELECT s.Home AS TeamName               
            FROM pScores s WHERE @LeagueType = '4'
              AND s.Season = @Season AND s.Home IS NOT NULL AND s.Home <> ''
            UNION               
            SELECT s.Visitor AS TeamName               
            FROM pScores s WHERE @LeagueType = '4'
              AND s.Season = @Season AND s.Visitor IS NOT NULL AND s.Visitor <> ''
            UNION
            SELECT s.Home AS TeamName               
            FROM HS_Scores s WHERE @LeagueType = '1'
              AND s.Season = @Season AND s.Home IS NOT NULL AND s.Home <> ''
            UNION               
            SELECT s.Visitor AS TeamName               
            FROM HS_Scores s WHERE @LeagueType = '1'
              AND s.Season = @Season AND s.Visitor IS NOT NULL AND s.Visitor <> ''
            UNION
            SELECT s.Home AS TeamName               
            FROM College_Scores s WHERE @LeagueType = '2'
              AND s.Season = @Season AND s.Home IS NOT NULL AND s.Home <> ''
            UNION               
            SELECT s.Visitor AS TeamName               
            FROM College_Scores s WHERE @LeagueType = '2'
              AND s.Season = @Season AND s.Visitor IS NOT NULL AND s.Visitor <> ''
            UNION
            SELECT s.Home AS TeamName               
            FROM NFL_Scores s WHERE @LeagueType = '3'
              AND s.Season = @Season AND s.Home IS NOT NULL AND s.Home <> ''
            UNION               
            SELECT s.Visitor AS TeamName               
            FROM NFL_Scores s WHERE @LeagueType = '3'
              AND s.Season = @Season AND s.Visitor IS NOT NULL AND s.Visitor <> ''
        ) AS AllParticipatingTeamsInSeason      
    ),      
    ExpandedSeasons AS (          
        SELECT               
            ts.TeamName,
            ts.Season,               
            ts.Season - 2 AS PrevSeason2,              
            ts.Season - 1 AS PrevSeason1,              
            ts.Season + 1 AS NextSeason1,              
            ts.Season + 2 AS NextSeason2          
        FROM TeamSeasons ts      
    ),      
    AggregatedRankings AS (          
        SELECT               
            es.TeamName,
            es.Season,               
            AVG(COALESCE(sr.Avg_Of_Avg_Of_Home_Modified_Score, 0)) AS Avg_Of_Avg_Of_Home_Modified_Score,              
            AVG(COALESCE(sr.Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss, 0)) AS Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss,              
            AVG(COALESCE(sr.Avg_Of_Avg_Of_Home_Modified_Log_Score, 0)) AS Avg_Of_Avg_Of_Home_Modified_Log_Score,              
            AVG(COALESCE(sr.Max_Min_Margin, 0)) AS Max_Min_Margin,              
            MAX(COALESCE(sr.Max_Performance, 0)) AS Max_Performance,               
            MIN(COALESCE(sr.Min_Performance, 0)) AS Min_Performance,               
            AVG(COALESCE(sr.Offense, 0)) AS Offense,              
            AVG(COALESCE(sr.Defense, 0)) AS Defense,              
            AVG(COALESCE(sr.Best_Worst_Win_Loss, 0)) AS Best_Worst_Win_Loss,              
            COUNT(sr.Season) AS SeasonsCount           
        FROM ExpandedSeasons es          
        LEFT JOIN SeasonRankings sr ON es.TeamName = sr.CanonicalTeamName
                                   AND sr.Season IN (es.PrevSeason2, es.PrevSeason1, es.NextSeason1, es.NextSeason2)          
        GROUP BY es.TeamName, es.Season       
    )      
    -- CRITICAL FIX: Return Season BEFORE Home to match expected column order
    SELECT           
        ar.Season,                    -- Changed: Season comes FIRST
        ar.TeamName AS Home,          -- Changed: Home comes SECOND
        CASE WHEN ar.SeasonsCount = 0 THEN 0 ELSE ar.Avg_Of_Avg_Of_Home_Modified_Score END AS Avg_Of_Avg_Of_Home_Modified_Score,          
        CASE WHEN ar.SeasonsCount = 0 THEN 0 ELSE ar.Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss END AS Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss,          
        CASE WHEN ar.SeasonsCount = 0 THEN 0 ELSE ar.Avg_Of_Avg_Of_Home_Modified_Log_Score END AS Avg_Of_Avg_Of_Home_Modified_Log_Score,          
        CASE WHEN ar.SeasonsCount = 0 THEN 0 ELSE ar.Max_Min_Margin END AS Max_Min_Margin,          
        CASE WHEN ar.SeasonsCount = 0 THEN 0 ELSE ar.Max_Performance END AS Max_Performance,          
        CASE WHEN ar.SeasonsCount = 0 THEN 0 ELSE ar.Min_Performance END AS Min_Performance,          
        CASE WHEN ar.SeasonsCount = 0 THEN 0 ELSE ar.Offense END AS Offense,          
        CASE WHEN ar.SeasonsCount = 0 THEN 0 ELSE ar.Defense END AS Defense,          
        CASE WHEN ar.SeasonsCount = 0 THEN 0 ELSE ar.Best_Worst_Win_Loss END AS Best_Worst_Win_Loss      
    FROM AggregatedRankings ar      
    WHERE ar.Season = @Season   
);
GO

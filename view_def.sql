
CREATE VIEW Rankings_Combined AS
SELECT 
    r.Season,
    r.Home AS Team,
    -- CORRECTED: These were swapped
    r.Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss AS Margin,        -- This is Margin (100+)
    r.Avg_Of_Avg_Of_Home_Modified_Score AS Win_Loss,               -- This is Win/Loss (single digits)
    r.Avg_Of_Avg_Of_Home_Modified_Log_Score AS Log_Score,
    r.Max_Min_Margin,
    r.Max_Performance,
    r.Min_Performance,
    r.Offense,
    r.Defense,
    r.Best_Worst_Win_Loss,
    -- Combined Rating calculation (using correct coefficient column names)
    (r.Avg_Of_Avg_Of_Home_Modified_Score * c.Win_Loss_Coef +           -- Win/Loss 
     r.Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss * c.Margin_Coef +   -- Margin
     r.Avg_Of_Avg_Of_Home_Modified_Log_Score * c.Log_Score_Coef) AS Combined_Rating,
    -- Game count for filtering
    CASE 
        WHEN r.Season < 1950 THEN 
            (SELECT COUNT(*) FROM HS_Scores s 
             WHERE (s.Home = r.Home OR s.Visitor = r.Home) 
             AND s.Season = r.Season)
        ELSE 
            (SELECT COUNT(*) FROM HS_Scores s 
             WHERE (s.Home = r.Home OR s.Visitor = r.Home) 
             AND s.Season = r.Season)
    END AS Games_Played
FROM HS_Rankings r
CROSS JOIN (
    SELECT TOP 1 
        Win_Loss_Coef, 
        Margin_Coef, 
        Log_Score_Coef 
    FROM Coefficients 
    ORDER BY ID DESC
) c
WHERE r.Week = 52  -- End of season
  AND r.Home NOT LIKE '%Freshman%'
  AND r.Home NOT LIKE '%JV%'
  AND (
    (r.Season < 1950 AND 
     (SELECT COUNT(*) FROM HS_Scores s 
      WHERE (s.Home = r.Home OR s.Visitor = r.Home) 
      AND s.Season = r.Season) >= 5)
    OR
    (r.Season >= 1950 AND 
     (SELECT COUNT(*) FROM HS_Scores s 
      WHERE (s.Home = r.Home OR s.Visitor = r.Home) 
      AND s.Season = r.Season) >= 8)
  );

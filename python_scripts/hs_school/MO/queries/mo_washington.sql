SET NOCOUNT ON;
SELECT s.Season, s.[Date], Opp = CASE WHEN s.Home = 'Washington (MO)' THEN s.Visitor ELSE s.Home END,
       WS = CASE WHEN s.Home = 'Washington (MO)' THEN s.Home_Score ELSE s.Visitor_Score END,
       OS = CASE WHEN s.Home = 'Washington (MO)' THEN s.Visitor_Score ELSE s.Home_Score END, s.Source, s.ID
FROM dbo.HS_Scores s WHERE s.Home = 'Washington (MO)' OR s.Visitor = 'Washington (MO)' ORDER BY 1, 2;

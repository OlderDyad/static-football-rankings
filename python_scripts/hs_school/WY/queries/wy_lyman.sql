-- Lyman (WY) holds Lyman (SD) and Lyman (NE) games: list its games by opponent state, and the SD/NE Lyman names
SELECT s.Season, s.[Date], s.Home, s.Home_Score, s.Visitor, s.Visitor_Score, s.Source,
       Opp = CASE WHEN s.Home = 'Lyman (WY)' THEN s.Visitor ELSE s.Home END,
       OppSt = SUBSTRING(RTRIM(CASE WHEN s.Home = 'Lyman (WY)' THEN s.Visitor ELSE s.Home END), LEN(RTRIM(CASE WHEN s.Home = 'Lyman (WY)' THEN s.Visitor ELSE s.Home END)) - 2, 2),
       s.ID
FROM dbo.HS_Scores s WHERE s.Home = 'Lyman (WY)' OR s.Visitor = 'Lyman (WY)' ORDER BY s.Season, s.[Date];
SELECT t.Team_Name, Games = (SELECT COUNT(*) FROM dbo.HS_Scores s WHERE s.Home = t.Team_Name OR s.Visitor = t.Team_Name)
FROM dbo.HS_Team_Names t WHERE t.Team_Name LIKE '%Lyman%' ORDER BY t.Team_Name;

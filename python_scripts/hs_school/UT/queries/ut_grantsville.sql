SELECT s.Season, Opp = CASE WHEN s.Home = 'Grantsville (UT)' THEN s.Visitor ELSE s.Home END, s.Source, s.ID
FROM dbo.HS_Scores s WHERE (s.Home = 'Grantsville (UT)' OR s.Visitor = 'Grantsville (UT)') AND s.Season <= 1975 ORDER BY s.Season;

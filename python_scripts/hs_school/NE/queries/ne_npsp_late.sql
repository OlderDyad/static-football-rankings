SELECT s.Season, Opp = CASE WHEN s.Home = 'North Platte St. Patrick''s (NE)' THEN s.Visitor ELSE s.Home END, s.Source, s.ID
FROM dbo.HS_Scores s WHERE (s.Home = 'North Platte St. Patrick''s (NE)' OR s.Visitor = 'North Platte St. Patrick''s (NE)') AND s.Season >= 2000 ORDER BY s.Season;

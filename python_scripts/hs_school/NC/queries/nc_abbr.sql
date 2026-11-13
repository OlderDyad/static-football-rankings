SELECT t.Team_Name, Games = (SELECT COUNT(*) FROM dbo.HS_Scores s WHERE s.Home = t.Team_Name OR s.Visitor = t.Team_Name)
FROM dbo.HS_Team_Names t WHERE t.Team_Name LIKE '%(NC)' AND (t.Team_Name LIKE 'Mt. %' OR t.Team_Name LIKE '% Mt. %' OR t.Team_Name LIKE 'St. %' OR t.Team_Name LIKE 'Ft. %')
ORDER BY 1;

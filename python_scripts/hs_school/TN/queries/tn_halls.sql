SELECT t.Team_Name, Games = (SELECT COUNT(*) FROM dbo.HS_Scores s WHERE s.Home = t.Team_Name OR s.Visitor = t.Team_Name)
FROM dbo.HS_Team_Names t WHERE t.Team_Name LIKE '%Halls%(TN)';
SELECT s.Season, Src = LEFT(s.Source, 25), Games = COUNT(*) FROM dbo.HS_Scores s WHERE s.Home = 'Knoxville Halls (TN)' OR s.Visitor = 'Knoxville Halls (TN)'
GROUP BY s.Season, LEFT(s.Source, 25) ORDER BY s.Season, 2;

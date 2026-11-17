SET NOCOUNT ON;
SELECT Src = LEFT(ISNULL(s.Source,''), 40), Era = (s.Season / 10) * 10, Games = COUNT(*)
FROM dbo.HS_Scores s WHERE s.Home_Score = 0 AND s.Visitor_Score = 0 AND s.Season >= 1975
GROUP BY LEFT(ISNULL(s.Source,''), 40), (s.Season / 10) * 10 HAVING COUNT(*) >= 10 ORDER BY Games DESC;
SELECT Era = (s.Season / 10) * 10, ZeroZero = SUM(CASE WHEN s.Home_Score = 0 AND s.Visitor_Score = 0 THEN 1 ELSE 0 END), Games = COUNT(*)
FROM dbo.HS_Scores s WHERE s.Season >= 1940 AND s.Home_Score IS NOT NULL GROUP BY (s.Season / 10) * 10 ORDER BY 1;

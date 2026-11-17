SELECT s.ID, s.Season, Dt = CONVERT(char(10), s.[Date], 120), s.Home, s.Home_Score, s.Visitor, s.Visitor_Score, Src = LEFT(s.Source, 60)
FROM dbo.HS_Scores s WHERE RTRIM(s.Home) LIKE '%(NH)' OR RTRIM(s.Visitor) LIKE '%(NH)';

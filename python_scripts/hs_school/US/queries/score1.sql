SET NOCOUNT ON;
SELECT Src = LEFT(ISNULL(s.Source,''), 30), Era = (s.Season / 10) * 10, Games = COUNT(*),
       Ex = MIN(CONCAT(s.Season, ' ', s.Home, ' ', s.Home_Score, '-', s.Visitor_Score, ' ', s.Visitor))
FROM dbo.HS_Scores s
WHERE (s.Home_Score = 1 OR s.Visitor_Score = 1) AND s.Home_Score + s.Visitor_Score > 1
  AND RTRIM(s.Home) NOT LIKE '%(ON)' AND RTRIM(s.Home) NOT LIKE '%(BC)' AND RTRIM(s.Home) NOT LIKE '%(AB)'
  AND RTRIM(s.Home) NOT LIKE '%(QC)' AND RTRIM(s.Home) NOT LIKE '%(SK)' AND RTRIM(s.Home) NOT LIKE '%(MB)'
GROUP BY LEFT(ISNULL(s.Source,''), 30), (s.Season / 10) * 10 HAVING COUNT(*) >= 15 ORDER BY Games DESC;
SELECT TOP 40 s.Season, s.[Date], s.Home, s.Home_Score, s.Visitor, s.Visitor_Score, s.Forfeit, Src = LEFT(s.Source, 70)
FROM dbo.HS_Scores s WHERE s.Source LIKE '%mhsaa%' AND (s.Home_Score = 1 OR s.Visitor_Score = 1) AND s.Home_Score + s.Visitor_Score > 1;

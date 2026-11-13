-- Every NE game with Source = '0' (imported 2015-07..2017-11). Flag = 'CONFLICT' where another source has the same game with a different opponent.
IF OBJECT_ID('tempdb..#s0') IS NOT NULL DROP TABLE #s0;
SELECT ID, Season, [Date], Home, Home_Score, Visitor, Visitor_Score, Date_Added INTO #s0 FROM dbo.HS_Scores
WHERE Source = '0' AND (RTRIM(Home) LIKE '%(NE)' OR RTRIM(Visitor) LIKE '%(NE)');
IF OBJECT_ID('tempdb..#s0c') IS NOT NULL DROP TABLE #s0c;
SELECT z.ID, OtherHome = MIN(o.Home), OtherVisitor = MIN(o.Visitor), OtherSource = MIN(o.Source)
INTO #s0c FROM #s0 z JOIN dbo.HS_Scores o ON o.Season = z.Season AND o.ID <> z.ID AND ISNULL(o.Source, '') <> '0'
  AND ABS(DATEDIFF(day, o.[Date], z.[Date])) <= 3
  AND ((o.Home_Score = z.Home_Score AND o.Visitor_Score = z.Visitor_Score) OR (o.Home_Score = z.Visitor_Score AND o.Visitor_Score = z.Home_Score))
  AND (o.Home IN (z.Home, z.Visitor) OR o.Visitor IN (z.Home, z.Visitor))
  AND NOT ((o.Home = z.Home AND o.Visitor = z.Visitor) OR (o.Home = z.Visitor AND o.Visitor = z.Home))
GROUP BY z.ID;
-- 1: by month (playoff games are late Oct / Nov)
SELECT Mon = MONTH([Date]), Games = COUNT(*) FROM #s0 GROUP BY MONTH([Date]) ORDER BY 1;
-- 2: the full list
SELECT z.Season, Date = CONVERT(varchar(10), z.[Date], 120), z.Home, z.Home_Score, z.Visitor, z.Visitor_Score,
       Flag = CASE WHEN c.ID IS NULL THEN '' ELSE 'CONFLICT' END, c.OtherHome, c.OtherVisitor, c.OtherSource,
       Added = CONVERT(varchar(10), z.Date_Added, 120), z.ID
FROM #s0 z LEFT JOIN #s0c c ON c.ID = z.ID ORDER BY z.Season, z.[Date], z.Home;

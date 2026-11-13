-- How reliable are the NE Source='0' rows? Compare each with a copy of the same game from another source
-- (same season, date within 3 days, same score pair, at least one team in common).
IF OBJECT_ID('tempdb..#z0') IS NOT NULL DROP TABLE #z0;
SELECT ID, Season, [Date], Home, Visitor, Home_Score, Visitor_Score INTO #z0 FROM dbo.HS_Scores
WHERE Source = '0' AND (RTRIM(Home) LIKE '%(NE)' OR RTRIM(Visitor) LIKE '%(NE)');
IF OBJECT_ID('tempdb..#z1') IS NOT NULL DROP TABLE #z1;
SELECT z.ID, o.Home AS OHome, o.Visitor AS OVisitor, o.Source AS OSource,
       Match = CASE WHEN (o.Home = z.Home AND o.Visitor = z.Visitor) OR (o.Home = z.Visitor AND o.Visitor = z.Home) THEN 'both teams same'
                    ELSE 'one team differs' END,
       rn = ROW_NUMBER() OVER (PARTITION BY z.ID ORDER BY CASE WHEN (o.Home = z.Home AND o.Visitor = z.Visitor) OR (o.Home = z.Visitor AND o.Visitor = z.Home) THEN 0 ELSE 1 END)
INTO #z1
FROM #z0 z JOIN dbo.HS_Scores o ON o.Season = z.Season AND o.ID <> z.ID AND ISNULL(o.Source, '') <> '0'
     AND ABS(DATEDIFF(day, o.[Date], z.[Date])) <= 3
     AND ((o.Home_Score = z.Home_Score AND o.Visitor_Score = z.Visitor_Score) OR (o.Home_Score = z.Visitor_Score AND o.Visitor_Score = z.Home_Score))
     AND (o.Home IN (z.Home, z.Visitor) OR o.Visitor IN (z.Home, z.Visitor));
-- 1: summary
SELECT Result = ISNULL(m.Match, 'no copy elsewhere'), Games = COUNT(*)
FROM #z0 z LEFT JOIN #z1 m ON m.ID = z.ID AND m.rn = 1 GROUP BY ISNULL(m.Match, 'no copy elsewhere');
-- 2: the mismatches: which name the '0' row used vs the other source
SELECT z.Season, z.Home, z.Home_Score, z.Visitor, z.Visitor_Score, m.OHome, m.OVisitor, m.OSource, z.ID
FROM #z0 z JOIN #z1 m ON m.ID = z.ID AND m.rn = 1 WHERE m.Match = 'one team differs' ORDER BY z.Season;

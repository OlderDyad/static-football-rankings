IF OBJECT_ID('tempdb..#cc_n') IS NOT NULL DROP TABLE #cc_n;
CREATE TABLE #cc_n (Name varchar(150));
INSERT INTO #cc_n
SELECT DISTINCT x.n FROM (
    SELECT n = Home FROM dbo.HS_Scores WHERE RTRIM(Home) LIKE '%(MA)' OR RTRIM(Visitor) LIKE '%(MA)'
    UNION SELECT Visitor FROM dbo.HS_Scores WHERE RTRIM(Home) LIKE '%(MA)' OR RTRIM(Visitor) LIKE '%(MA)') x
WHERE (x.n LIKE '%University%' OR x.n LIKE '% College%' OR x.n LIKE '%School of Mines%' OR x.n LIKE '%Junior College%' OR x.n LIKE '%Institute of Technology%')
  AND x.n NOT IN ('Boston College High (MA)', 'Saint Louis University (MO)', 'Washington St. John''s College (DC)', 'Windsor Assumption College Catholic (ON)',
                  'Worcester South Community-University Park-Claremont Academy (MA)', 'Worcester South-University Park-Accelerated (MA)')
  AND x.n NOT LIKE '%High%' AND x.n NOT LIKE '%Prep%' AND x.n NOT LIKE '%University Park%';

IF OBJECT_ID('tempdb..#cc_g') IS NOT NULL DROP TABLE #cc_g;
SELECT s.ID, s.Season, s.[Date], s.Home, s.Home_Score, s.Visitor, s.Visitor_Score, s.Source,
       HomeCollege = CASE WHEN hn.Name IS NULL THEN 0 ELSE 1 END, VisitorCollege = CASE WHEN vn.Name IS NULL THEN 0 ELSE 1 END
INTO #cc_g
FROM dbo.HS_Scores s
LEFT JOIN #cc_n hn ON hn.Name = s.Home
LEFT JOIN #cc_n vn ON vn.Name = s.Visitor
WHERE (RTRIM(s.Home) LIKE '%(MA)' OR RTRIM(s.Visitor) LIKE '%(MA)') AND (hn.Name IS NOT NULL OR vn.Name IS NOT NULL);

-- All candidate College_Scores matches for post-1940 games in #cc_g
SELECT g.Season, CONVERT(varchar(10), g.[Date], 120) AS G_Date, g.Home, g.Home_Score, g.Visitor, g.Visitor_Score, g.Source,
       CONVERT(varchar(10), c.[Date], 120) AS C_Date, c.Home AS C_Home, c.Home_Score AS C_HS, c.Visitor AS C_Visitor, c.Visitor_Score AS C_VS,
       g.ID, c.ID AS CollegeID
FROM #cc_g g
JOIN dbo.College_Scores c ON c.Season = g.Season AND ABS(DATEDIFF(day, c.[Date], g.[Date])) <= 2
     AND ((c.Home_Score = g.Home_Score AND c.Visitor_Score = g.Visitor_Score) OR (c.Home_Score = g.Visitor_Score AND c.Visitor_Score = g.Home_Score))
WHERE g.Season >= 1940
  AND (
      LEFT(c.Home, 5) IN (LEFT(g.Home, 5), LEFT(g.Visitor, 5))
      OR LEFT(c.Visitor, 5) IN (LEFT(g.Home, 5), LEFT(g.Visitor, 5))
      OR ( (g.Home LIKE '%New Jersey%' OR g.Visitor LIKE '%New Jersey%') AND (c.Home LIKE '%New Jersey%' OR c.Visitor LIKE '%New Jersey%' OR c.Home LIKE '%Trenton%' OR c.Visitor LIKE '%Trenton%') )
  )
ORDER BY g.Season, g.[Date];

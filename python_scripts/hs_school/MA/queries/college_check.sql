-- Step 5.0: do Massachusetts's college games have a copy in College_Scores? (season, date +-2, score pair; college-vs-HS also needs the HS name)
-- 0: College_Team_Names rows linked to a Massachusetts HS-table name (step 0 collision check)
SELECT ct.Team_ID, ct.Team_Name, ct.Kind, ct.State, ct.First_Season, ct.Last_Season, ct.Games, ct.HS_Team_ID, ct.HS_Team_Name, ct.HS_Link_Confidence,
       HS_Games = (SELECT COUNT(*) FROM dbo.HS_Scores s WHERE s.Home = ct.HS_Team_Name OR s.Visitor = ct.HS_Team_Name)
FROM dbo.College_Team_Names ct WHERE ct.HS_Team_Name LIKE '%(MA)' ORDER BY ct.HS_Team_Name;
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

-- the college-like names used (for checking)
SELECT Name FROM #cc_n ORDER BY Name;

IF OBJECT_ID('tempdb..#cc_g') IS NOT NULL DROP TABLE #cc_g;
SELECT s.ID, s.Season, s.[Date], s.Home, s.Home_Score, s.Visitor, s.Visitor_Score, s.Source,
       HomeCollege = CASE WHEN hn.Name IS NULL THEN 0 ELSE 1 END, VisitorCollege = CASE WHEN vn.Name IS NULL THEN 0 ELSE 1 END
INTO #cc_g
FROM dbo.HS_Scores s
LEFT JOIN #cc_n hn ON hn.Name = s.Home
LEFT JOIN #cc_n vn ON vn.Name = s.Visitor
WHERE (RTRIM(s.Home) LIKE '%(MA)' OR RTRIM(s.Visitor) LIKE '%(MA)') AND (hn.Name IS NOT NULL OR vn.Name IS NOT NULL);

IF OBJECT_ID('tempdb..#cc_m') IS NOT NULL DROP TABLE #cc_m;
SELECT g.ID, CollegeID = c.ID, C_Date = c.[Date], C_Home = c.Home, C_HS = c.Home_Score, C_Visitor = c.Visitor, C_VS = c.Visitor_Score,
       rn = ROW_NUMBER() OVER (PARTITION BY g.ID ORDER BY ABS(DATEDIFF(day, c.[Date], g.[Date])))
INTO #cc_m
FROM #cc_g g
JOIN dbo.College_Scores c ON c.Season = g.Season AND ABS(DATEDIFF(day, c.[Date], g.[Date])) <= 2
     AND ((c.Home_Score = g.Home_Score AND c.Visitor_Score = g.Visitor_Score) OR (c.Home_Score = g.Visitor_Score AND c.Visitor_Score = g.Home_Score))
     AND ((g.HomeCollege = 1 AND g.VisitorCollege = 1) OR c.Home IN (g.Home, g.Visitor) OR c.Visitor IN (g.Home, g.Visitor));

-- 1: summary
SELECT Kind = CASE WHEN g.HomeCollege = 1 AND g.VisitorCollege = 1 THEN 'college vs college' ELSE 'college vs HS' END,
       Era = CASE WHEN g.Season < 1940 THEN 'before 1940 (keep in both)' ELSE '1940 on' END,
       Games = COUNT(*), InCollegeScores = SUM(CASE WHEN m.ID IS NULL THEN 0 ELSE 1 END)
FROM #cc_g g LEFT JOIN #cc_m m ON m.ID = g.ID AND m.rn = 1
GROUP BY CASE WHEN g.HomeCollege = 1 AND g.VisitorCollege = 1 THEN 'college vs college' ELSE 'college vs HS' END,
         CASE WHEN g.Season < 1940 THEN 'before 1940 (keep in both)' ELSE '1940 on' END
ORDER BY 1, 2;

-- 2: every game, with its College_Scores copy if found
SELECT Kind = CASE WHEN g.HomeCollege = 1 AND g.VisitorCollege = 1 THEN 'college vs college' ELSE 'college vs HS' END,
       g.Season, g.[Date], g.Home, g.Home_Score, g.Visitor, g.Visitor_Score, g.Source,
       m.C_Date, m.C_Home, m.C_HS, m.C_Visitor, m.C_VS, g.ID, m.CollegeID
FROM #cc_g g LEFT JOIN #cc_m m ON m.ID = g.ID AND m.rn = 1
ORDER BY 1, g.Season, g.[Date];

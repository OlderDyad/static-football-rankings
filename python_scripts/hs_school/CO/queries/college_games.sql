-- Step 5.0 college games in Colorado HS_Scores.
-- 1: column lists of the college tables (so the next query can match against them)
SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, ORDINAL_POSITION
FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME IN ('College_Team_Names', 'College_Scores') ORDER BY TABLE_NAME, ORDINAL_POSITION;

-- 2: Colorado names that look like colleges (or college freshman / prep teams), with what they played
IF OBJECT_ID('tempdb..#cg_g') IS NOT NULL DROP TABLE #cg_g;
SELECT Team = Home, Opp = Visitor, Season INTO #cg_g FROM dbo.HS_Scores WHERE 1 = 0;
INSERT INTO #cg_g SELECT Home, Visitor, Season FROM dbo.HS_Scores WHERE RTRIM(Home) LIKE '%(CO)';
INSERT INTO #cg_g SELECT Visitor, Home, Season FROM dbo.HS_Scores WHERE RTRIM(Visitor) LIKE '%(CO)';
IF OBJECT_ID('tempdb..#cg_c') IS NOT NULL DROP TABLE #cg_c;
SELECT DISTINCT Team INTO #cg_c FROM #cg_g
WHERE Team LIKE '% College%' OR Team LIKE '%University%' OR Team LIKE '%Mines%' OR Team LIKE 'Colorado State%'
   OR Team LIKE '%Aggies%' OR Team LIKE '%A&M%' OR Team LIKE '%Normal%' OR Team LIKE '%Teachers%' OR Team LIKE '%Junior College%'
   OR Team LIKE 'Adams State%' OR Team LIKE '%Air Force Academy%' OR Team LIKE 'Regis (CO)' OR Team LIKE 'Regis College%'
   OR Team LIKE '%Fort Lewis%' OR Team LIKE 'Western State%' OR Team LIKE 'Mesa %' OR Team LIKE '%Freshmen%' OR Team LIKE '%Frosh%'
   OR Team LIKE 'Denver (CO)' OR Team LIKE 'Colorado (CO)' OR Team LIKE '%Seminary%' OR Team LIKE '%Institute%';
IF OBJECT_ID('tempdb..#cg_x') IS NOT NULL DROP TABLE #cg_x;
SELECT g.Team, g.Opp, g.Season, OppCollege = CASE WHEN oc.Team IS NULL THEN 0 ELSE 1 END
INTO #cg_x FROM #cg_g g JOIN #cg_c c ON c.Team = g.Team LEFT JOIN #cg_c oc ON oc.Team = g.Opp;
SELECT Team, Games = COUNT(*), FirstSeason = MIN(Season), LastSeason = MAX(Season),
       VsCollegeLike = SUM(OppCollege), VsOthers = SUM(1 - OppCollege),
       From1940 = SUM(CASE WHEN Season >= 1940 THEN 1 ELSE 0 END),
       CollegeVsCollegeFrom1940 = SUM(CASE WHEN Season >= 1940 THEN OppCollege ELSE 0 END)
FROM #cg_x GROUP BY Team ORDER BY Team;

-- 3: top opponents of each college-like name (to tell real colleges from HS / prep names)
;WITH o AS (SELECT g.Team, g.Opp, n = COUNT(*), F = MIN(g.Season), L = MAX(g.Season),
                   rn = ROW_NUMBER() OVER (PARTITION BY g.Team ORDER BY COUNT(*) DESC)
            FROM #cg_g g JOIN #cg_c c ON c.Team = g.Team GROUP BY g.Team, g.Opp)
SELECT Team, Opp, Games = n, FirstSeason = F, LastSeason = L FROM o WHERE rn <= 8 ORDER BY Team, n DESC;

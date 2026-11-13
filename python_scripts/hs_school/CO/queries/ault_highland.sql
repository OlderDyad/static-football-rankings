-- Ault Highland (CO): two schedules 1970-1982? (rural Weld County vs Denver-metro opponents)
-- 1: Ault Highland games 1965-1992, Metro = opponent is in the metro group
SELECT s.Season, s.[Date], s.Home, s.Home_Score, s.Visitor, s.Visitor_Score, s.Source,
       Opp = CASE WHEN s.Home = 'Ault Highland (CO)' THEN s.Visitor ELSE s.Home END,
       Metro = CASE WHEN (CASE WHEN s.Home = 'Ault Highland (CO)' THEN s.Visitor ELSE s.Home END) IN
              ('Thornton (CO)','Commerce City Adams City (CO)','Broomfield (CO)','Brighton (CO)','Northglenn (CO)','Westminster (CO)',
               'Denver Ranum (CO)','Denver Mullen (CO)','Aurora Regis Jesuit (CO)','Englewood (CO)','Edgewater Jefferson (CO)',
               'Denver Sheridan (CO)','Denver Lincoln (CO)','Denver Christian (CO)','Parker Ponderosa (CO)','Lafayette Centaurus (CO)',
               'Evergreen (CO)','Colorado Springs Hilltop Baptist (CO)') THEN 1 ELSE 0 END,
       s.ID
FROM dbo.HS_Scores s
WHERE (s.Home = 'Ault Highland (CO)' OR s.Visitor = 'Ault Highland (CO)') AND s.Season BETWEEN 1965 AND 1992
ORDER BY s.Season, s.[Date];

-- 2: which Colorado school might own the metro schedule: teams that played the metro group, with games per era
;WITH g AS (
    SELECT Team = Home, Opp = Visitor, Season FROM dbo.HS_Scores WHERE Season BETWEEN 1960 AND 1992 AND Home LIKE '%(CO)'
    UNION ALL
    SELECT Visitor, Home, Season FROM dbo.HS_Scores WHERE Season BETWEEN 1960 AND 1992 AND Visitor LIKE '%(CO)')
SELECT Team,
       MetroGames = SUM(CASE WHEN Opp IN ('Thornton (CO)','Commerce City Adams City (CO)','Broomfield (CO)','Brighton (CO)','Northglenn (CO)',
                         'Westminster (CO)','Denver Ranum (CO)','Denver Mullen (CO)','Aurora Regis Jesuit (CO)','Englewood (CO)') THEN 1 ELSE 0 END),
       G1960_69 = SUM(CASE WHEN Season BETWEEN 1960 AND 1969 THEN 1 ELSE 0 END),
       G1970_82 = SUM(CASE WHEN Season BETWEEN 1970 AND 1982 THEN 1 ELSE 0 END),
       G1983_92 = SUM(CASE WHEN Season BETWEEN 1983 AND 1992 THEN 1 ELSE 0 END),
       SeasonsWithGames = COUNT(DISTINCT Season)
FROM g
WHERE Team NOT LIKE '% JV (%' AND Team NOT LIKE '% B (%'
GROUP BY Team
HAVING SUM(CASE WHEN Opp IN ('Thornton (CO)','Commerce City Adams City (CO)','Broomfield (CO)','Brighton (CO)','Northglenn (CO)',
                 'Westminster (CO)','Denver Ranum (CO)','Denver Mullen (CO)','Aurora Regis Jesuit (CO)','Englewood (CO)') THEN 1 ELSE 0 END) >= 5
ORDER BY MetroGames DESC;

-- 3: MaxPreps URL mapping rows that mention Ault or Highland
SELECT u.URL, u.ProperName, u.Team_ID FROM dbo.URL_ProperName_Mapping u
WHERE u.URL LIKE '%ault%' OR u.URL LIKE '%highland%' OR u.ProperName LIKE '%Highland%' OR u.ProperName LIKE 'Ault%';

-- 1: Boston Commerce (MA) seasons and games
SELECT Season, COUNT(*) AS Games, MIN(Date) AS MinD, MAX(Date) AS MaxD
FROM dbo.HS_Scores
WHERE (Home = 'Boston Commerce (MA)' OR Visitor = 'Boston Commerce (MA)') AND ISNULL(Future_Game, 0) = 0
GROUP BY Season
ORDER BY Season;

-- 2: Boston Commerce (MA) games from 1970 onward
SELECT ID, Season, CONVERT( varchar(10), Date, 120) AS Date, Home, Home_Score, Visitor, Visitor_Score, Source
FROM dbo.HS_Scores
WHERE (Home = 'Boston Commerce (MA)' OR Visitor = 'Boston Commerce (MA)') AND Season >= 1970 AND ISNULL(Future_Game, 0) = 0
ORDER BY Date;

-- 3: 2024-09-28 Boston Latin / Dorchester Boston Latin Academy games
SELECT ID, Season, CONVERT(varchar(10), Date, 120) AS Date, Home, Home_Score, Visitor, Visitor_Score, Source
FROM dbo.HS_Scores
WHERE Season = 2024 AND Date BETWEEN '2024-09-26' AND '2024-09-30'
  AND (Home IN ('Boston Latin (MA)', 'Dorchester Boston Latin Academy (MA)') OR Visitor IN ('Boston Latin (MA)', 'Dorchester Boston Latin Academy (MA)'));

-- 4: Boston Cathedral-Matignon (MA) and Buckland Mohawk Trail Regional-Turners Falls (MA)
SELECT t.Team, COUNT(*) AS Games, MIN(Season) AS MinS, MAX(Season) AS MaxS,
       InNames = CASE WHEN EXISTS (SELECT 1 FROM dbo.HS_Team_Names n WHERE n.Team_Name = t.Team) THEN 1 ELSE 0 END,
       InMap   = CASE WHEN EXISTS (SELECT 1 FROM dbo.URL_ProperName_Mapping m WHERE m.ProperName = t.Team) THEN 1 ELSE 0 END
FROM (
    SELECT Home AS Team, Season FROM dbo.HS_Scores WHERE Home IN ('Boston Cathedral-Matignon (MA)', 'Buckland Mohawk Trail Regional-Turners Falls (MA)', 'Cambridge Matignon-St. Joseph Prep (MA)')
    UNION ALL
    SELECT Visitor, Season FROM dbo.HS_Scores WHERE Visitor IN ('Boston Cathedral-Matignon (MA)', 'Buckland Mohawk Trail Regional-Turners Falls (MA)', 'Cambridge Matignon-St. Joseph Prep (MA)')
) t
GROUP BY t.Team;

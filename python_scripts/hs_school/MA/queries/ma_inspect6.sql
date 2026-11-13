-- 1. All distinct names in HS_Scores for MA that are NOT in HS_Team_Names (excluding colleges/JV/Frosh)
SELECT x.TeamName, Games = COUNT(*), FirstSeason = MIN(Season), LastSeason = MAX(Season)
FROM (
    SELECT Season, TeamName = Home FROM dbo.HS_Scores WHERE Home LIKE '%(MA)'
    UNION ALL
    SELECT Season, TeamName = Visitor FROM dbo.HS_Scores WHERE Visitor LIKE '%(MA)'
) x
WHERE NOT EXISTS (SELECT 1 FROM dbo.HS_Team_Names t WHERE t.Team_Name = x.TeamName)
GROUP BY x.TeamName
ORDER BY Games DESC, x.TeamName;

-- 2. Check all 2024 games involving Boston Latin (MA) alongside opponent schedules to identify which 2024 games are Dorchester Boston Latin Academy (MA)
SELECT s.ID, s.Season, s.[Date], s.Home, s.Home_Score, s.Visitor, s.Visitor_Score, s.Source
FROM dbo.HS_Scores s
WHERE s.Season = 2024
  AND (s.Home = 'Boston Latin (MA)' OR s.Visitor = 'Boston Latin (MA)')
ORDER BY s.[Date], s.Source;

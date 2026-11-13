-- 1. Check HS_Scores_Change_Log for Boston Latin%
SELECT FieldChanged, OldValue, NewValue, Reason, ChangedAt, COUNT(*) AS Cnt
FROM dbo.HS_Scores_Change_Log
WHERE OldValue LIKE '%Boston Latin%' OR NewValue LIKE '%Boston Latin%'
GROUP BY FieldChanged, OldValue, NewValue, Reason, ChangedAt
ORDER BY ChangedAt DESC;

-- 2. Check Boston Latin School (MA) games by season
SELECT Season, Games = COUNT(*),
       PlayedEnglish = SUM(CASE WHEN Home LIKE '%English%' OR Visitor LIKE '%English%' THEN 1 ELSE 0 END),
       PlayedOBryant = SUM(CASE WHEN Home LIKE '%Bryant%' OR Visitor LIKE '%Bryant%' THEN 1 ELSE 0 END),
       PlayedBostonLatin = SUM(CASE WHEN Home = 'Boston Latin (MA)' OR Visitor = 'Boston Latin (MA)' THEN 1 ELSE 0 END)
FROM dbo.HS_Scores
WHERE Home = 'Boston Latin School (MA)' OR Visitor = 'Boston Latin School (MA)'
GROUP BY Season
ORDER BY Season;

-- 3. Check Springfield (MA) games (27 games, 1964-2026)
SELECT Season, [Date], Home, Home_Score, Visitor, Visitor_Score, Source, ID
FROM dbo.HS_Scores
WHERE Home = 'Springfield (MA)' OR Visitor = 'Springfield (MA)'
ORDER BY Season, [Date];

-- 4. Check Hyannis St. John (MA), Hyannis St. John Paul II (MA), Hyannis Pope John Paul II (MA) by season
SELECT TeamName, Season, Games = COUNT(*)
FROM (
    SELECT Season, TeamName = Home FROM dbo.HS_Scores WHERE Home LIKE 'Hyannis%John%'
    UNION ALL
    SELECT Season, TeamName = Visitor FROM dbo.HS_Scores WHERE Visitor LIKE 'Hyannis%John%'
) x
GROUP BY TeamName, Season
ORDER BY Season, TeamName;

-- 5. Check Everett (MA) games vs Providence (RI) or Concord (MA) across all seasons to identify the 1938-12-30..1939-02-17 yearbook schedule
SELECT Season, [Date], Home, Home_Score, Visitor, Visitor_Score, Source, ID
FROM dbo.HS_Scores
WHERE (Home = 'Everett (MA)' OR Visitor = 'Everett (MA)')
  AND (Home IN ('Concord (MA)', 'Providence (RI)', 'Providence Central (RI)') OR Visitor IN ('Concord (MA)', 'Providence (RI)', 'Providence Central (RI)'))
ORDER BY Season, [Date];

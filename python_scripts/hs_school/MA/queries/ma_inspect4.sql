-- 1. Everett 1937 schedule vs 1938-12-30..1939-02-17 yearbook schedule
SELECT Season, [Date], Home, Home_Score, Visitor, Visitor_Score, Source, ID
FROM dbo.HS_Scores
WHERE (Home = 'Everett (MA)' OR Visitor = 'Everett (MA)')
  AND (Season = 1937 OR (Season = 1938 AND [Date] >= '1938-12-01'))
ORDER BY Season, [Date];

-- 2. Check Boston Latin (MA) vs Boston Latin School (MA) vs Dorchester Boston Latin Academy (MA) in 1940-2005
SELECT Season,
       BostonLatin = SUM(CASE WHEN Home = 'Boston Latin (MA)' OR Visitor = 'Boston Latin (MA)' THEN 1 ELSE 0 END),
       BostonLatinSchool = SUM(CASE WHEN Home = 'Boston Latin School (MA)' OR Visitor = 'Boston Latin School (MA)' THEN 1 ELSE 0 END),
       DorchesterBLA = SUM(CASE WHEN Home = 'Dorchester Boston Latin Academy (MA)' OR Visitor = 'Dorchester Boston Latin Academy (MA)' THEN 1 ELSE 0 END),
       HeadToHead_BL_BLS = SUM(CASE WHEN (Home = 'Boston Latin (MA)' AND Visitor = 'Boston Latin School (MA)') OR (Home = 'Boston Latin School (MA)' AND Visitor = 'Boston Latin (MA)') THEN 1 ELSE 0 END)
FROM dbo.HS_Scores
WHERE Season BETWEEN 1940 AND 2005
  AND (Home IN ('Boston Latin (MA)', 'Boston Latin School (MA)', 'Dorchester Boston Latin Academy (MA)')
    OR Visitor IN ('Boston Latin (MA)', 'Boston Latin School (MA)', 'Dorchester Boston Latin Academy (MA)'))
GROUP BY Season
ORDER BY Season;

-- 3. Check sample games of Boston Latin School (MA) in 1970-2003 vs Boston Latin (MA) in 1970-2003
SELECT TOP 60 Season, [Date], Home, Home_Score, Visitor, Visitor_Score, Source
FROM dbo.HS_Scores
WHERE (Home IN ('Boston Latin (MA)', 'Boston Latin School (MA)') OR Visitor IN ('Boston Latin (MA)', 'Boston Latin School (MA)'))
  AND Season BETWEEN 1985 AND 1995
ORDER BY Season, [Date];

-- 4. Check North Shore Tech / Essex Tech by season
SELECT Season,
       EssexTech = SUM(CASE WHEN Home = 'Hathorne Essex Tech (MA)' OR Visitor = 'Hathorne Essex Tech (MA)' THEN 1 ELSE 0 END),
       NST = SUM(CASE WHEN Home = 'Middleton North Shore Tech (MA)' OR Visitor = 'Middleton North Shore Tech (MA)' THEN 1 ELSE 0 END),
       NST_Essex = SUM(CASE WHEN Home = 'Middleton North Shore Tech-Essex Agricultural (MA)' OR Visitor = 'Middleton North Shore Tech-Essex Agricultural (MA)' THEN 1 ELSE 0 END)
FROM dbo.HS_Scores
WHERE Home IN ('Hathorne Essex Tech (MA)', 'Middleton North Shore Tech (MA)', 'Middleton North Shore Tech-Essex Agricultural (MA)')
   OR Visitor IN ('Hathorne Essex Tech (MA)', 'Middleton North Shore Tech (MA)', 'Middleton North Shore Tech-Essex Agricultural (MA)')
GROUP BY Season
ORDER BY Season;

-- 5. Check Coyle-Cassidy vs Monsignor Coyle, and Manchester / Manchester Essex / Manchester Essex-Rockport by season
SELECT Season,
       CoyleCassidy = SUM(CASE WHEN Home = 'Taunton Coyle-Cassidy (MA)' OR Visitor = 'Taunton Coyle-Cassidy (MA)' THEN 1 ELSE 0 END),
       MonsignorCoyle = SUM(CASE WHEN Home = 'Taunton Monsignor Coyle (MA)' OR Visitor = 'Taunton Monsignor Coyle (MA)' THEN 1 ELSE 0 END),
       Manchester = SUM(CASE WHEN Home = 'Manchester (MA)' OR Visitor = 'Manchester (MA)' THEN 1 ELSE 0 END),
       ManchesterEssex = SUM(CASE WHEN Home = 'Manchester Essex (MA)' OR Visitor = 'Manchester Essex (MA)' THEN 1 ELSE 0 END),
       ManchesterEssexRockport = SUM(CASE WHEN Home = 'Manchester Essex-Rockport (MA)' OR Visitor = 'Manchester Essex-Rockport (MA)' THEN 1 ELSE 0 END)
FROM dbo.HS_Scores
WHERE Home IN ('Taunton Coyle-Cassidy (MA)', 'Taunton Monsignor Coyle (MA)', 'Manchester (MA)', 'Manchester Essex (MA)', 'Manchester Essex-Rockport (MA)')
   OR Visitor IN ('Taunton Coyle-Cassidy (MA)', 'Taunton Monsignor Coyle (MA)', 'Manchester (MA)', 'Manchester Essex (MA)', 'Manchester Essex-Rockport (MA)')
GROUP BY Season
ORDER BY Season;

-- 1. All MA URLs with game stats of their ProperName, ordered by FirstSeason DESC to spot all 2024-2026 splits
SELECT m.URL, m.ProperName, m.Team_ID,
       Games = ISNULL(s.Games, 0), s.FirstSeason, s.LastSeason
FROM dbo.URL_ProperName_Mapping m
OUTER APPLY (
    SELECT Games = COUNT(*), FirstSeason = MIN(Season), LastSeason = MAX(Season)
    FROM dbo.HS_Scores x
    WHERE x.Home = m.ProperName OR x.Visitor = m.ProperName
) s
WHERE m.ProperName LIKE '%(MA)' OR m.URL LIKE '%/ma/%'
ORDER BY ISNULL(s.FirstSeason, 9999) DESC, ISNULL(s.Games, 0) ASC;

-- 2. Check Boston Latin / Boston Latin School / Dorchester Boston Latin Academy in 2018-2026
SELECT Season, [Date], Home, Home_Score, Visitor, Visitor_Score, Source, ID
FROM dbo.HS_Scores
WHERE (Home IN ('Boston Latin (MA)', 'Boston Latin School (MA)', 'Boston Latin Academy (MA)', 'Dorchester Boston Latin Academy (MA)')
    OR Visitor IN ('Boston Latin (MA)', 'Boston Latin School (MA)', 'Boston Latin Academy (MA)', 'Dorchester Boston Latin Academy (MA)'))
  AND Season >= 2018
ORDER BY Season, [Date];

-- 3. Check HS_Team_Names details for the split pairs
SELECT ID, Team_Name, City, Mascot, YearFounded
FROM dbo.HS_Team_Names
WHERE Team_Name IN (
    'Topsfield Masconomet Regional (MA)', 'Boxford Masconomet Regional (MA)',
    'Lincoln-Sudbury (MA)', 'Sudbury Lincoln Sudbury (MA)',
    'Hamilton-Wenham Regional (MA)', 'South Hamilton Hamilton Wenham (MA)',
    'Cape Cod RVT-Harwich (MA)', 'Harwich Cape Cod RVT (MA)',
    'Boston Latin (MA)', 'Boston Latin School (MA)', 'Dorchester Boston Latin Academy (MA)',
    'Falmouth (MA)', 'Falmouth Academy (MA)',
    'Cheshire Hoosac Valley (MA)', 'Adams Hoosac Valley (MA)',
    'North Eastham Nauset Regional (MA)', 'Eastham Nauset Regional (MA)',
    'Dartmouth (MA)', 'South Dartmouth (MA)',
    'Groton Dunstable (MA)', 'Groton-Dunstable (MA)', 'Groton-Dunstable Regional (MA)',
    'Townsend North Middlesex (MA)', 'Townsend North Middlesex Regional (MA)',
    'Hyannis Pope John Paul II (MA)', 'Hyannis St. John (MA)', 'Hyannis St. John Paul II (MA)',
    'North Adams Drury (MA)', 'North Adams Drury Mount (MA)',
    'Cambridge Rindge & Latin (MA)', 'Cambridge Rindge Tech (MA)', 'Cambridge (MA)',
    'Lynn Kipp Academy (MA)', 'Lynn Collegiate-KIPP Academy (MA)',
    'Springfield Sci-Tech (MA)', 'Springfield International Charter-Springfield Sci-Tech (MA)', 'Springfield (MA)',
    'Manchester (MA)', 'Manchester Essex (MA)', 'Manchester Essex-Rockport (MA)',
    'Hathorne Essex Tech (MA)', 'Middleton North Shore Tech (MA)', 'Middleton North Shore Tech-Essex Agricultural (MA)',
    'Taunton Coyle-Cassidy (MA)', 'Taunton Monsignor Coyle (MA)'
)
ORDER BY Team_Name;

-- 4. Check the 1882 vs 1982 Andover Phillips Academy vs Phillips Exeter Academy games
SELECT Season, [Date], Home, Home_Score, Visitor, Visitor_Score, Source, ID
FROM dbo.HS_Scores
WHERE (Home LIKE '%Phillips%' AND Visitor LIKE '%Phillips%')
  AND Season IN (1882, 1982)
ORDER BY Season, [Date];

-- 5. Check 1938 Everett (MA) schedule around those Feb 1939 dates
SELECT Season, [Date], Home, Home_Score, Visitor, Visitor_Score, Source, ID
FROM dbo.HS_Scores
WHERE (Home = 'Everett (MA)' OR Visitor = 'Everett (MA)')
  AND Season IN (1938, 1939)
ORDER BY Season, [Date];

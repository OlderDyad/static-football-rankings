-- 1. All HS_Team_Names rows for MA
SELECT ID, Team_Name, City, State, Mascot
FROM dbo.HS_Team_Names
WHERE State = 'MA' OR Team_Name LIKE '%(MA)'
ORDER BY Team_Name;

-- 2. All URL_ProperName_Mapping rows for MA
SELECT m.URL, m.ProperName, m.Team_ID, t.Team_Name AS Joined_Team_Name
FROM dbo.URL_ProperName_Mapping m
LEFT JOIN dbo.HS_Team_Names t ON t.ID = m.Team_ID
WHERE m.ProperName LIKE '%(MA)' OR m.URL LIKE '%/ma/%'
ORDER BY m.ProperName, m.URL;

-- 3. Check specific candidate name pairs and their season ranges / overlap in HS_Scores
SELECT TeamName, Games = COUNT(*), FirstSeason = MIN(Season), LastSeason = MAX(Season),
       InTeamNames = CASE WHEN EXISTS (SELECT 1 FROM dbo.HS_Team_Names t WHERE t.Team_Name = x.TeamName) THEN 1 ELSE 0 END,
       MappedURLs = (SELECT COUNT(*) FROM dbo.URL_ProperName_Mapping m WHERE m.ProperName = x.TeamName)
FROM (
    SELECT Season, TeamName = Home FROM dbo.HS_Scores WHERE Home LIKE '%(MA)'
    UNION ALL
    SELECT Season, TeamName = Visitor FROM dbo.HS_Scores WHERE Visitor LIKE '%(MA)'
) x
WHERE TeamName IN (
    'Arlington (MA)', 'Arlington Spy (MA)',
    'Holyoke (MA)', 'Holyoke Purple (MA)',
    'Milford (MA)', 'Milford Scarlet (MA)',
    'Brighton (MA)', 'Brighton Kennedy (MA)',
    'Groton-Dunstable (MA)', 'Groton Dunstable (MA)',
    'Lynn Collegiate-KIPP Academy (MA)', 'Lynn Kipp Academy (MA)',
    'Topsfield Masconomet Regional (MA)', 'Boxford Masconomet Regional (MA)',
    'Lincoln-Sudbury (MA)', 'Sudbury Lincoln Sudbury (MA)',
    'Hamilton-Wenham Regional (MA)', 'South Hamilton Hamilton Wenham (MA)',
    'Cape Cod RVT-Harwich (MA)', 'Harwich Cape Cod RVT (MA)',
    'Boston Latin (MA)', 'Boston Latin School (MA)', 'Boston Latin Academy (MA)', 'Dorchester Boston Latin Academy (MA)',
    'Boston College (MA)', 'Boston College High (MA)',
    'Falmouth (MA)', 'Falmouth Academy (MA)',
    'Cheshire Hoosac Valley (MA)', 'Adams Hoosac Valley (MA)',
    'Middleborough (MA)', 'Middleboro (MA)',
    'Foxborough (MA)', 'Foxboro (MA)',
    'North Eastham Nauset Regional (MA)', 'Eastham Nauset Regional (MA)',
    'Hathorne Essex Tech (MA)', 'Middleton North Shore Tech (MA)', 'Middleton North Shore Tech-Essex Agricultural (MA)',
    'Brockton Cardinal Spellman (MA)', 'Spellman (MA)',
    'Peabody Veterans Memorial (MA)', 'Peabody (MA)',
    'Cambridge Rindge & Latin (MA)', 'Cambridge (MA)', 'Cambridge High & Latin (MA)',
    'Marion Tabor Academy (MA)', 'Tabor Academy (MA)',
    'Needham St. Sebastian''s School (MA)', 'Newton St. Sebastian''s (MA)',
    'Amherst Stockbridge (MA)', 'Stockbridge (MA)', 'Stockbridge Junior College (MA)',
    'Taunton Coyle-Cassidy (MA)', 'Taunton Monsignor Coyle (MA)',
    'Greater New Bedford RVT (MA)', 'New Bedford Vocational (MA)',
    'Randolph (MA)', 'Randolph Stetson (MA)',
    'Whitman-Hanson Regional (MA)', 'Whitman (MA)',
    'South Weymouth Weymouth (MA)', 'Weymouth South (MA)', 'Weymouth North (MA)',
    'Boston Thompson Island Farm and Trades School (MA)', ' Boston Thompson Island Farm and Trades School (MA)',
    'Easthampton Williston Northampton (MA)', 'Easthampton Williston Northampton School (MA)',
    'Springfield Commerce (MA)', 'Boston Commerce (MA)', 'Worcester Commerce (MA)',
    'Turners Falls Franklin County Tech (MA)', 'Franklin Tri-County RVT (MA)',
    'Manchester (MA)', 'Manchester Essex (MA)', 'Manchester Essex-Rockport (MA)',
    'West Roxbury (MA)', 'West Roxbury-Urban Science Academy (MA)',
    'Dorchester Burke (MA)', 'Dorchester Burke-Community Academy of Science & Health (MA)',
    'Millis (MA)', 'Millis-Hopedale (MA)',
    'Maynard (MA)', 'Maynard-Bromfield (MA)',
    'Ayer (MA)', 'Ayer Shirley (MA)', 'Ayer Shirley-Bromfield (MA)',
    'West Boylston (MA)', 'West Boylston-Tahanto (MA)',
    'Sutton (MA)', 'Sutton-Douglas (MA)',
    'Palmer (MA)', 'Palmer-Monson (MA)',
    'Holbrook (MA)', 'Holbrook-Avon (MA)',
    'Northampton-Smith Vo-Tech (MA)', 'Hatfield Smith Academy-Smith Vo-Tech (MA)',
    'Worcester Holy Name Central Catholic (MA)', 'Worcester Holy Name Central Catholic-St. Mary''s (MA)'
)
GROUP BY TeamName
ORDER BY TeamName;

-- 4. Check the 2024-2026 games of Boston College (MA), Brighton Kennedy (MA), Boston Latin (MA), Boston Latin School (MA), Boston Latin Academy (MA)
SELECT Season, [Date], Home, Home_Score, Visitor, Visitor_Score, Source, ID
FROM dbo.HS_Scores
WHERE (Home IN ('Boston College (MA)', 'Brighton Kennedy (MA)', 'Boston Latin Academy (MA)', 'Easthampton Williston Northampton (MA)')
    OR Visitor IN ('Boston College (MA)', 'Brighton Kennedy (MA)', 'Boston Latin Academy (MA)', 'Easthampton Williston Northampton (MA)'))
  AND Season >= 2020
ORDER BY Season, [Date];

-- 1. Check co-op pairs by season
SELECT TeamName, FirstSeason = MIN(Season), LastSeason = MAX(Season), Games = COUNT(*),
       SeasonsList = STRING_AGG(CAST(Season AS varchar(4)) + ':' + CAST(Cnt AS varchar(4)), ', ') WITHIN GROUP (ORDER BY Season)
FROM (
    SELECT TeamName, Season, Cnt = COUNT(*)
    FROM (
        SELECT Season, TeamName = Home FROM dbo.HS_Scores WHERE Home LIKE '%(MA)'
        UNION ALL
        SELECT Season, TeamName = Visitor FROM dbo.HS_Scores WHERE Visitor LIKE '%(MA)'
    ) a
    WHERE TeamName IN (
        'West Boylston (MA)', 'West Boylston-Tahanto (MA)',
        'Sutton (MA)', 'Sutton-Douglas (MA)',
        'Maynard (MA)', 'Maynard-Bromfield (MA)',
        'Millis (MA)', 'Millis-Hopedale (MA)',
        'Holbrook (MA)', 'Holbrook-Avon (MA)',
        'Ayer (MA)', 'Ayer Shirley (MA)', 'Ayer Shirley-Bromfield (MA)',
        'Palmer (MA)', 'Palmer-Monson (MA)',
        'West Roxbury (MA)', 'West Roxbury-Urban Science Academy (MA)',
        'Dorchester Burke (MA)', 'Dorchester Burke-Community Academy of Science & Health (MA)',
        'Northampton-Smith Vo-Tech (MA)', 'Hatfield Smith Academy-Smith Vo-Tech (MA)',
        'Worcester Holy Name Central Catholic (MA)', 'Worcester Holy Name Central Catholic-St. Mary''s (MA)',
        'Springfield Sci-Tech (MA)', 'Springfield International Charter-Springfield Sci-Tech (MA)', 'Springfield (MA)',
        'Dartmouth (MA)', 'South Dartmouth (MA)',
        'Cambridge (MA)', 'Cambridge Rindge & Latin (MA)', 'Cambridge Rindge Tech (MA)',
        'North Adams Drury (MA)', 'North Adams Drury-Mount Greylock Regional (MA)', 'North Adams Drury Mount (MA)',
        'Groton Dunstable (MA)', 'Groton-Dunstable (MA)', 'Groton-Dunstable Regional (MA)'
    )
    GROUP BY TeamName, Season
) b
GROUP BY TeamName
ORDER BY TeamName;

-- 2. Check Weymouth vs Weymouth North vs Weymouth South in 1969-1991
SELECT Season,
       Weymouth = SUM(CASE WHEN Name = 'South Weymouth Weymouth (MA)' THEN 1 ELSE 0 END),
       WeymouthNorth = SUM(CASE WHEN Name = 'Weymouth North (MA)' THEN 1 ELSE 0 END),
       WeymouthSouth = SUM(CASE WHEN Name = 'Weymouth South (MA)' THEN 1 ELSE 0 END)
FROM (
    SELECT Season, Name = Home FROM dbo.HS_Scores WHERE Home IN ('South Weymouth Weymouth (MA)', 'Weymouth North (MA)', 'Weymouth South (MA)')
    UNION ALL
    SELECT Season, Name = Visitor FROM dbo.HS_Scores WHERE Visitor IN ('South Weymouth Weymouth (MA)', 'Weymouth North (MA)', 'Weymouth South (MA)')
) x
WHERE Season BETWEEN 1968 AND 1992
GROUP BY Season
ORDER BY Season;

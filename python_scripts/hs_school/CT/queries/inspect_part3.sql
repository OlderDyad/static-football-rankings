-- Set 1: New London Buckeley (CT) 1951-2003 with matching New London (CT) or Hartford Bulkeley (CT) games
SELECT b.ID, b.Season, b.[Date], b.Home, b.Home_Score, b.Visitor, b.Visitor_Score, b.Source,
       NL_Match = (SELECT TOP 1 CONCAT(x.Home, ' ', x.Home_Score, '-', x.Visitor_Score, ' ', x.Visitor, ' (', x.[Date], ')')
                   FROM dbo.HS_Scores x
                   WHERE x.Season = b.Season AND ABS(DATEDIFF(day, x.[Date], b.[Date])) <= 2
                     AND ('New London (CT)' IN (x.Home, x.Visitor))),
       HB_Match = (SELECT TOP 1 CONCAT(x.Home, ' ', x.Home_Score, '-', x.Visitor_Score, ' ', x.Visitor, ' (', x.[Date], ')')
                   FROM dbo.HS_Scores x
                   WHERE x.Season = b.Season AND ABS(DATEDIFF(day, x.[Date], b.[Date])) <= 2
                     AND (x.Home LIKE 'Hartford Bu%(CT)' OR x.Visitor LIKE 'Hartford Bu%(CT)'))
FROM dbo.HS_Scores b
WHERE 'New London Buckeley (CT)' IN (b.Home, b.Visitor)
  AND b.Season >= 1951
ORDER BY b.Season, b.[Date];

-- Set 2: Bristol Mt. Hope (RI) pre-1993 with matching Providence Hope (RI) or Bristol (RI) games
SELECT b.ID, b.Season, b.[Date], b.Home, b.Home_Score, b.Visitor, b.Visitor_Score, b.Source,
       Hope_Match = (SELECT TOP 1 CONCAT(x.Home, ' ', x.Home_Score, '-', x.Visitor_Score, ' ', x.Visitor, ' (', x.[Date], ')')
                     FROM dbo.HS_Scores x
                     WHERE x.Season = b.Season AND ABS(DATEDIFF(day, x.[Date], b.[Date])) <= 2
                       AND ('Providence Hope (RI)' IN (x.Home, x.Visitor))),
       Bristol_Match = (SELECT TOP 1 CONCAT(x.Home, ' ', x.Home_Score, '-', x.Visitor_Score, ' ', x.Visitor, ' (', x.[Date], ')')
                        FROM dbo.HS_Scores x
                        WHERE x.Season = b.Season AND ABS(DATEDIFF(day, x.[Date], b.[Date])) <= 2
                          AND ('Bristol (RI)' IN (x.Home, x.Visitor)))
FROM dbo.HS_Scores b
WHERE 'Bristol Mt. Hope (RI)' IN (b.Home, b.Visitor)
  AND b.Season < 1993
ORDER BY b.Season, b.[Date];

-- Set 3: Pawtucket (RI) 1940-1970 with matching Tolman / East / West games
SELECT b.ID, b.Season, b.[Date], b.Home, b.Home_Score, b.Visitor, b.Visitor_Score, b.Source,
       Pawt_Match = (SELECT TOP 1 CONCAT(x.Home, ' ', x.Home_Score, '-', x.Visitor_Score, ' ', x.Visitor, ' (', x.[Date], ')')
                     FROM dbo.HS_Scores x
                     WHERE x.Season = b.Season AND ABS(DATEDIFF(day, x.[Date], b.[Date])) <= 2
                       AND (x.Home LIKE 'Pawtucket%(RI)' OR x.Visitor LIKE 'Pawtucket%(RI)')
                       AND x.ID <> b.ID)
FROM dbo.HS_Scores b
WHERE 'Pawtucket (RI)' IN (b.Home, b.Visitor)
  AND b.Season >= 1940
ORDER BY b.Season, b.[Date];

-- Set 4: Check Providence Hope (RI) 2023-2026 and Cranston (RI) 1959-1985
SELECT Season, [Date], Home, Home_Score, Visitor, Visitor_Score, Source, ID
FROM dbo.HS_Scores
WHERE ('Providence Hope (RI)' IN (Home, Visitor) AND Season >= 2023)
   OR ('Cranston (RI)' IN (Home, Visitor) AND Season >= 1959)
   OR ('Waterbury ChaseCollegiate (CT)' IN (Home, Visitor))
ORDER BY Home, Season, [Date];

-- Set 5: Check HS_Team_Names and URL_ProperName_Mapping for CT/NH/RI co-ops that showed up in UNDECIDED same_score
SELECT t.State, t.ID, t.Team_Name,
       MappedURL = (SELECT TOP 1 m.URL FROM dbo.URL_ProperName_Mapping m WHERE m.ProperName = t.Team_Name OR m.Team_ID = t.ID)
FROM dbo.HS_Team_Names t
WHERE (t.State IN ('CT', 'NH', 'RI'))
  AND (t.Team_Name LIKE '%Coventry%' OR t.Team_Name LIKE '%Coginchaug%' OR t.Team_Name LIKE '%Capital Prep%'
    OR t.Team_Name LIKE '%Creed%' OR t.Team_Name LIKE '%Windsor Locks%' OR t.Team_Name LIKE '%Stafford%'
    OR t.Team_Name LIKE '%Ellington%' OR t.Team_Name LIKE '%Sacred Heart%' OR t.Team_Name LIKE '%Central Falls%'
    OR t.Team_Name LIKE '%Country Day%' OR t.Team_Name LIKE '%Exeter%' OR t.Team_Name LIKE '%Griswold%'
    OR t.Team_Name LIKE '%Cromwell%' OR t.Team_Name LIKE '%North Smithfield%' OR t.Team_Name LIKE '%Hillsboro%'
    OR t.Team_Name LIKE '%Inter%' OR t.Team_Name LIKE '%Chase%')
ORDER BY t.State, t.Team_Name;

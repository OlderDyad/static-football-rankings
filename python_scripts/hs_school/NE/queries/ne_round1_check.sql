-- WY round 1 candidates: do the target names exist, and how many games do they have?
IF OBJECT_ID('tempdb..#w1') IS NOT NULL DROP TABLE #w1;
CREATE TABLE #w1 (Alias varchar(150), Target varchar(150), Why varchar(100));
INSERT INTO #w1 VALUES
('Lincoln North (NE)','Lincoln North Star (NE)','drift'),
('Elkhorn South (NE)','Omaha Elkhorn South (NE)','drift'),
('North Bend North Bend (NE)','North Bend Central (NE)','drift'),
('West Point West Point (NE)','West Point-Beemer (NE)','drift'),
('Humphrey Lindsay (NE)','Humphrey-Lindsay Holy Family (NE)','drift'),
('Humboldt-Table Rock (NE)','Humboldt-Table Rock-Steinauer (NE)','same school'),
('Papillion La Vista (NE)','Papillion-La Vista (NE)','same school'),
('West Point Central Catholic (NE)','West Point Guardian Angels Central Catholic (NE)','same school'),
('Humboldt  (NE)','Humboldt (NE)','double space'),
('Malbeta (NE)','Melbeta (NE)','typo'),
('Minitare (NE)','Minatare (NE)','typo'),
('Grodon (NE)','Gordon (NE)','typo'),
('Linicoln Jackson (NE)','Lincoln Jackson (NE)','typo'),
('Omaha Unversity (NE)','University of Nebraska Omaha (NE)','typo'),
('Council Bluffs Central (NE)','Council Bluffs Central (IA)','wrong state'),
('Council Bluffs Lincoln (NE)','Council Bluffs Lincoln (IA)','wrong state'),
('Council Bluffs Saint Albert Catholic (NE)','Council Bluffs St. Albert (IA)','wrong state'),
('Sioux City South (NE)','Sioux City South (IA)','wrong state'),
('Sioux City Trinity (NE)','Sioux City Trinity (IA)','wrong state'),
('Toledo Waite (NE)','Toledo Waite (OH)','wrong state'),
('Goodland (NE)','Goodland (KS)','wrong state'),
('Burns (NE)','Burns (WY)','wrong state'),
('Custer (NE)','Custer (SD)','wrong state'),
('Edgemont (NE)','Edgemont (SD)','wrong state'),
('Davenport West OPP ""Jefferson"" (NE)','Davenport West (IA)','wrong state');

-- 1: each candidate, its games, the target's games, and similar names in the target state (to pick the right spelling)
SELECT w.Alias, AliasGames = (SELECT COUNT(*) FROM dbo.HS_Scores s WHERE s.Home = w.Alias OR s.Visitor = w.Alias),
       w.Target, TargetGames = (SELECT COUNT(*) FROM dbo.HS_Scores s WHERE s.Home = w.Target OR s.Visitor = w.Target),
       TargetInTeamNames = CASE WHEN EXISTS (SELECT 1 FROM dbo.HS_Team_Names t WHERE t.Team_Name = w.Target) THEN 1 ELSE 0 END,
       AliasMapped = CASE WHEN EXISTS (SELECT 1 FROM dbo.URL_ProperName_Mapping u WHERE u.ProperName = w.Alias) THEN 1 ELSE 0 END,
       TargetMapped = CASE WHEN EXISTS (SELECT 1 FROM dbo.URL_ProperName_Mapping u WHERE u.ProperName = w.Target) THEN 1 ELSE 0 END,
       w.Why
FROM #w1 w ORDER BY w.Why, w.Alias;

-- 2: for wrong-state and doubtful targets: names in the target state that share the alias's key word
SELECT w.Alias, Candidate = t.Team_Name,
       Games = (SELECT COUNT(*) FROM dbo.HS_Scores s WHERE s.Home = t.Team_Name OR s.Visitor = t.Team_Name)
FROM #w1 w
JOIN dbo.HS_Team_Names t ON t.Team_Name LIKE '%' + RIGHT(w.Target, 4)
   AND t.Team_Name LIKE '%' + LEFT(REPLACE(REPLACE(w.Alias, 'Ft. ', 'Fort '), ' (NE)', ''), CASE WHEN CHARINDEX(' ', w.Alias) > 0 THEN CHARINDEX(' ', w.Alias) - 1 ELSE 6 END) + '%'
WHERE w.Why IN ('wrong state', 'typo')
ORDER BY w.Alias, Games DESC;


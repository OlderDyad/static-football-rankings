-- WY round 1 candidates: do the target names exist, and how many games do they have?
IF OBJECT_ID('tempdb..#w1') IS NOT NULL DROP TABLE #w1;
CREATE TABLE #w1 (Alias varchar(150), Target varchar(150), Why varchar(100));
INSERT INTO #w1 VALUES
('Las Cruces Onate (NM)','Las Cruces Organ Mountain (NM)','renamed'),
('Las Cruces Ornate (NM)','Las Cruces Organ Mountain (NM)','renamed'),
('Truth or Consequences (NM)','Truth or Consequences Hot Springs (NM)','same school'),
('Hatch (NM)','Hatch Valley (NM)','same school'),
('Abluquerque Valley (NM)','Albuquerque Valley (NM)','typo'),
('Alamagordo JV (NM)','Alamogordo JV (NM)','typo'),
('Artiesia (NM)','Artesia (NM)','typo'),
('Calrsbad JV (NM)','Carlsbad JV (NM)','typo'),
('Esnapola (NM)','Espanola Valley (NM)','typo'),
('Ojoaque (NM)','Pojoaque Valley (NM)','typo'),
('Poaoaque (NM)','Pojoaque Valley (NM)','typo'),
('Rojoaque (NM)','Pojoaque Valley (NM)','typo'),
('Mountain Air (NM)','Mountainair (NM)','typo'),
('University of New Mexicao (NM)','University of New Mexico (NM)','typo'),
('Santa Theresa JV (NM)','Santa Teresa JV (NM)','typo'),
('Mora St. Gertrude''s (NM)','Mora St. Gertrude (NM)','typo'),
('Mora, St. Gertrude (NM)','Mora St. Gertrude (NM)','typo'),
('Gadsen Anthony (NM)','Anthony Gadsden (NM)','typo'),
('Colfax Ridgeview-Lexington (NM)','Colfax Ridgeview-Lexington (IL)','wrong state'),
('Gilman Iroquois West (NM)','Gilman Iroquois West (IL)','wrong state'),
('Havana (NM)','Havana (IL)','wrong state'),
('Kewanee Wethersfield-Annawan (NM)','Kewanee Wethersfield-Annawan (IL)','wrong state'),
('Knoxville (NM)','Knoxville (IL)','wrong state'),
('Oneida ROWVA-Williamsfield (NM)','Oneida ROWVA-Williamsfield (IL)','wrong state'),
('Princeville (NM)','Princeville (IL)','wrong state'),
('Toulon Stark County (NM)','Toulon Stark County (IL)','wrong state'),
('Goddard (NM)','Goddard (KS)','wrong state');

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
   AND t.Team_Name LIKE '%' + LEFT(REPLACE(REPLACE(w.Alias, 'Ft. ', 'Fort '), ' (NM)', ''), CASE WHEN CHARINDEX(' ', w.Alias) > 0 THEN CHARINDEX(' ', w.Alias) - 1 ELSE 6 END) + '%'
WHERE w.Why IN ('wrong state', 'typo', 'renamed', 'same school')
ORDER BY w.Alias, Games DESC;


-- 3: mapping rows for the names involved
SELECT u.URL, u.ProperName, u.Team_ID FROM dbo.URL_ProperName_Mapping u
WHERE u.URL LIKE '%maxpreps.com/nm/%' AND (u.URL LIKE '%truth%' OR u.URL LIKE '%hot-springs%' OR u.URL LIKE '%onate%' OR u.URL LIKE '%organ-mountain%' OR u.URL LIKE '%hagerman%' OR u.URL LIKE '%deaf%' OR u.URL LIKE '%hatch%');

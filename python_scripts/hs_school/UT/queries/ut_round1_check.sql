-- WY round 1 candidates: do the target names exist, and how many games do they have?
IF OBJECT_ID('tempdb..#w1') IS NOT NULL DROP TABLE #w1;
CREATE TABLE #w1 (Alias varchar(150), Target varchar(150), Why varchar(100));
INSERT INTO #w1 VALUES
('Salina North Sevier (UT)','Salina North Sevier County (UT)','drift'),
('Vernal Uintah (UT)','Vernal Uintah County (UT)','drift'),
('Salina (UT)','Salina North Sevier County (UT)','same school'),
('Boxelder (UT)','Brigham City Box Elder (UT)','typo'),
('of Deaf (UT)','Utah School for the Deaf (UT)','same school'),
('Ogden Utah School for Deaf (UT)','Utah School for the Deaf (UT)','same school'),
('Mount Pleasant Sanpete (UT)','Mount Pleasant North Sanpete (UT)','same school'),
('Cokeville (UT)','Cokeville (WY)','wrong state'),
('Dove Creek (UT)','Dove Creek (CO)','wrong state'),
('Norwood (UT)','Norwood (CO)','wrong state'),
('Chatfield (UT)','Littleton Chatfield (CO)','wrong state'),
('Minico (UT)','Rupert Minico (ID)','wrong state'),
('Winnemucca Lowry (UT)','Winnemucca Lowry (NV)','wrong state'),
('Lincoln County (UT)','Panaca Lincoln County (NV)','wrong state'),
('Centennial (UT)','Centennial (ID)','wrong state'),
('Laketown North Rich (UT)','North Rich (UT)','same school');

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
   AND t.Team_Name LIKE '%' + LEFT(REPLACE(REPLACE(w.Alias, 'Ft. ', 'Fort '), ' (UT)', ''), CASE WHEN CHARINDEX(' ', w.Alias) > 0 THEN CHARINDEX(' ', w.Alias) - 1 ELSE 6 END) + '%'
WHERE w.Why IN ('wrong state', 'same school', 'typo')
ORDER BY w.Alias, Games DESC;


-- 3: the 2023 games of the wrong-state names (who did they play?)
SELECT s.Season, s.Home, s.Home_Score, s.Visitor, s.Visitor_Score, s.Source FROM dbo.HS_Scores s
WHERE s.Home IN ('Centennial (UT)','Lincoln County (UT)','Minico (UT)','Chatfield (UT)') OR s.Visitor IN ('Centennial (UT)','Lincoln County (UT)','Minico (UT)','Chatfield (UT)');
-- 4: names for the missing ProperNames
SELECT Team_Name FROM dbo.HS_Team_Names WHERE Team_Name LIKE 'Blanding%' OR Team_Name LIKE 'Fillmore%' OR Team_Name LIKE 'Monroe%(UT)' OR Team_Name LIKE 'Vernal%' OR Team_Name LIKE 'Salina%';

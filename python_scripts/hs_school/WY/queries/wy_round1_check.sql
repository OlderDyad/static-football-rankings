-- WY round 1 candidates: do the target names exist, and how many games do they have?
IF OBJECT_ID('tempdb..#w1') IS NOT NULL DROP TABLE #w1;
CREATE TABLE #w1 (Alias varchar(150), Target varchar(150), Why varchar(100));
INSERT INTO #w1 VALUES
 ('Casper (WY)','Casper Natrona County (WY)','MaxPreps drift 2024-26'),
 ('Kemmerer (WY)','Diamondville Kemmerer (WY)','MaxPreps drift 2024-26'),
 ('Gillette (WY)','Gillette Campbell County (WY)','same school'),
 ('Gillette Campbell County ''B'' (WY)','Gillette Campbell County B (WY)','spelling'),
 ('Gillette Campbell County B  (WY)','Gillette Campbell County B (WY)','double space'),
 ('Casper Natrona JV (WY)','Casper Natrona County JV (WY)','spelling'),
 ('Larmie (WY)','Laramie (WY)','typo'),
 ('Sunrisde (WY)','Sunrise (WY)','typo'),
 ('XXpton (WY)','Upton (WY)','typo'),
 ('Grand Encampment (WY)','Encampment (WY)','same school'),
 ('Lander Fremont County (WY)','Lander Valley (WY)','same school'),
 ('Rocky Mountain (WY)','Cowley Rocky Mountain (WY)','same school'),
 ('Rocky Mountain JV (WY)','Cowley Rocky Mountain JV (WY)','same school'),
 ('Byron-Rocky Mountain (WY)','Cowley Rocky Mountain (WY)','same school'),
 ('Eden (WY)','Farson-Eden (WY)','same school'),
 ('Eden-Farson (WY)','Farson-Eden (WY)','word order'),
 ('Goshen County Southeast (WY)','Yoder Southeast (WY)','same school'),
 ('Normative (WY)','Sheridan Normative Services (WY)','same school'),
 ('Seton (WY)','Cheyenne Seton Catholic (WY)','same school?'),
 ('Seton Catholic (WY)','Cheyenne Seton Catholic (WY)','same school?'),
 ('Riverton St. Stephan''s Mission (WY)','Saint Stephens (WY)','same school?'),
 ('Hanna (WY)','Hanna-Elk Mountain (WY)','same school?'),
 ('Wyoming (WY)','University of Wyoming (WY)','1904'),
 ('Fort Morgan (WY)','Fort Morgan (CO)','wrong state'),
 ('Ft. Morgan (WY)','Fort Morgan (CO)','wrong state'),
 ('Fort Collins Poudre (WY)','Fort Collins Poudre (CO)','wrong state'),
 ('Canon City Abbey (WY)','Canon City Abbey (CO)','wrong state'),
 ('Pueblo Central (WY)','Pueblo Central (CO)','wrong state'),
 ('Pueblo East (WY)','Pueblo East (CO)','wrong state'),
 ('Moffat County (WY)','Craig Moffat County (CO)','wrong state'),
 ('Sterling St. Anthony''s (WY)','Sterling St. Anthony''s (CO)','wrong state'),
 ('Greeley JV (WY)','Greeley Central JV (CO)','wrong state'),
 ('Colorado State Freshman (WY)','Colorado State University Frosh (CO)','wrong state'),
 ('Garden County (WY)','Oshkosh Garden County (NE)','wrong state'),
 ('Gering (WY)','Gering (NE)','wrong state'),
 ('Kimball JV (WY)','Kimball JV (NE)','wrong state'),
 ('Scottsbluff JV (WY)','Scottsbluff JV (NE)','wrong state'),
 ('Sidney St. Patrick''s (WY)','Sidney St. Patrick''s (NE)','wrong state'),
 ('North Platte (WY)','North Platte (NE)','wrong state'),
 ('Hot Springs (WY)','Hot Springs (SD)','wrong state'),
 ('Belle Fourche JV (WY)','Belle Fourche JV (SD)','wrong state'),
 ('Custer JV (WY)','Custer JV (SD)','wrong state'),
 ('Rapid City Cathedral (WY)','Rapid City St. Thomas More (SD)','wrong state'),
 ('Rapid City Christian (WY)','Rapid City Christian (SD)','wrong state'),
 ('Hardin JV (WY)','Hardin JV (MT)','wrong state'),
 ('Lodge Grass JV (WY)','Lodge Grass JV (MT)','wrong state'),
 ('Miles City Industrial (WY)','Miles City Pine Hills (MT)','wrong state'),
 ('Red Lodge-Roberts (WY)','Red Lodge-Roberts (MT)','wrong state'),
 ('North Rich (WY)','Randolph Rich (UT)','wrong state'),
 ('South Rich (WY)','Randolph Rich (UT)','wrong state'),
 ('Rich County (WY)','Randolph Rich (UT)','wrong state'),
 ('North Summit (WY)','Coalville North Summit (UT)','wrong state'),
 ('Ogden Bonneville (WY)','Ogden Bonneville (UT)','wrong state'),
 ('Judge Memorial JV (WY)','Salt Lake City Judge Memorial JV (UT)','wrong state'),
 ('Bear Lake (WY)','Montpelier Bear Lake (ID)','wrong state');

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
   AND t.Team_Name LIKE '%' + LEFT(REPLACE(REPLACE(w.Alias, 'Ft. ', 'Fort '), ' (WY)', ''), CASE WHEN CHARINDEX(' ', w.Alias) > 0 THEN CHARINDEX(' ', w.Alias) - 1 ELSE 6 END) + '%'
WHERE w.Why IN ('wrong state', 'same school?')
ORDER BY w.Alias, Games DESC;

-- 3: MaxPreps mapping rows for the drift names and the WY teams with no mapping that still play
SELECT u.URL, u.ProperName, u.Team_ID FROM dbo.URL_ProperName_Mapping u
WHERE u.ProperName IN ('Casper (WY)', 'Kemmerer (WY)', 'Casper Natrona County (WY)', 'Diamondville Kemmerer (WY)')
   OR u.URL LIKE '%/wy/casper/%' OR u.URL LIKE '%/wy/kemmerer/%' OR u.URL LIKE '%/wy/newcastle/%' OR u.URL LIKE '%/wy/torrington/%'
   OR u.URL LIKE '%/wy/big-piney/%' OR u.URL LIKE '%/wy/ten-sleep/%';

IF OBJECT_ID('tempdb..#w1') IS NOT NULL DROP TABLE #w1;
CREATE TABLE #w1 (Alias varchar(150), Target varchar(150), Why varchar(100));
INSERT INTO #w1 VALUES
('Aurora Houn (MO)','Aurora (MO)','drift'),
('Reeds Springs (MO)','Reeds Spring (MO)','spelling'),
('Ste Genevieve (MO)','Ste. Genevieve (MO)','drift'),
('Warrenton (MO)','Warrenton Warren County (MO)','drift'),
('Windsor (MO)','Windsor Henry County (MO)','drift'),
('New Madrid New Madrid (MO)','New Madrid County Central (MO)','drift'),
('Battle-Columbia Independent (MO)','Columbia Battle-Columbia Independent (MO)','same'),
('Kansas City Lincoln College (MO)','Kansas City Lincoln College Prep (MO)','drift'),
('Kansas City KIPP Legacy (MO)','Kansas City Kipp (MO)','same'),
('Kansas City Northland Christian (MO)','Kansas City Northland (MO)','check'),
('Saint Louis Vashon Miller Academy (MO)','Saint Louis Vashon-Miller Career Academy (MO)','drift'),
('Saint Louis University City (MO)','University City (MO)','drift'),
('Paris Madison-Faith Walk Academy (MO)','Paris-Madison-Faith Walk Academy (MO)','same'),
('Crest Ridge-Chilhowee (MO)','Centerview Crest Ridge-Chilhowee (MO)','same'),
('Saint Clair St. Clair (MO)','Saint Clair (MO)','drift'),
('Riverside Park Hill South (MO)','Kansas City Park Hill South (MO)','check'),
('Saint Louis St. Louis (MO)','Saint Louis University (MO)','check'),
('DeSoto (MO)','DeSoto-Kingston (MO)','check'),
('Joplin New Heights (MO)','Joplin McAuley Catholic (MO)','check'),
('Gallatin-Tri-County (MO)','Gallatin (MO)','check'),
('Kansas City Bishop Hogan (MO)','Kansas City Hogan Prep Academy (MO)','check'),
('Columbia Battle (MO)','Columbia Battle-Columbia Independent (MO)','check');

SELECT w.Alias, AliasGames = (SELECT COUNT(*) FROM dbo.HS_Scores s WHERE s.Home = w.Alias OR s.Visitor = w.Alias),
       w.Target, TargetGames = (SELECT COUNT(*) FROM dbo.HS_Scores s WHERE s.Home = w.Target OR s.Visitor = w.Target),
       TargetInTeamNames = CASE WHEN EXISTS (SELECT 1 FROM dbo.HS_Team_Names t WHERE t.Team_Name = w.Target) THEN 1 ELSE 0 END,
       AliasURL = (SELECT TOP 1 u.URL FROM dbo.URL_ProperName_Mapping u WHERE u.ProperName = w.Alias),
       TargetURL = (SELECT TOP 1 u.URL FROM dbo.URL_ProperName_Mapping u WHERE u.ProperName = w.Target), w.Why
FROM #w1 w ORDER BY w.Why, w.Alias;

-- 2: seasons where alias and target both have games (possible double copies), with games vs the same opponent
IF OBJECT_ID('tempdb..#w2') IS NOT NULL DROP TABLE #w2;
SELECT w.Alias, w.Target, Name = CASE WHEN s.Home IN (w.Alias, w.Target) THEN s.Home ELSE s.Visitor END,
       Opp = CASE WHEN s.Home IN (w.Alias, w.Target) THEN s.Visitor ELSE s.Home END, s.Season, s.[Date], s.Source
INTO #w2 FROM #w1 w JOIN dbo.HS_Scores s ON s.Home IN (w.Alias, w.Target) OR s.Visitor IN (w.Alias, w.Target);
SELECT a.Alias, a.Season, AliasGames = COUNT(DISTINCT a.[Date]),
       TargetGames = (SELECT COUNT(*) FROM #w2 b WHERE b.Alias = a.Alias AND b.Name = b.Target AND b.Season = a.Season),
       SameOpp = (SELECT COUNT(*) FROM #w2 b WHERE b.Alias = a.Alias AND b.Name = b.Target AND b.Season = a.Season
                  AND EXISTS (SELECT 1 FROM #w2 c WHERE c.Alias = a.Alias AND c.Name = c.Alias AND c.Season = a.Season AND c.Opp = b.Opp))
FROM #w2 a WHERE a.Name = a.Alias GROUP BY a.Alias, a.Season
HAVING (SELECT COUNT(*) FROM #w2 b WHERE b.Alias = a.Alias AND b.Name = b.Target AND b.Season = a.Season) > 0
ORDER BY a.Alias, a.Season;

-- 3: opponents per season for the 'check' pairs (alias name), 2010+ or overlap seasons
SELECT Alias, Name, Season, [Date], Opp, Source FROM #w2 WHERE Alias IN (SELECT Alias FROM #w1 WHERE Why = 'check') ORDER BY Alias, Season, [Date], Name;
-- 4: URLs for these names
SELECT u.URL, u.ProperName FROM dbo.URL_ProperName_Mapping u WHERE u.ProperName IN (SELECT Alias FROM #w1 UNION SELECT Target FROM #w1) OR u.URL LIKE '%/mo/st-louis/st-louis-university%' OR u.URL LIKE '%/mo/kansas-city/northland%';

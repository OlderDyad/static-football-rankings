IF OBJECT_ID('tempdb..#w1') IS NOT NULL DROP TABLE #w1;
CREATE TABLE #w1 (Alias varchar(150), Target varchar(150), Why varchar(100));
INSERT INTO #w1 VALUES
('Argonia Attica (KS)','Attica-Argonia (KS)','drift'),
('Brewster Triplains Brewster (KS)','Triplains-Brewster (KS)','drift'),
('Hays Thomas More (KS)','Hays Thomas More Prep-Marian (KS)','drift'),
('Inman Inman (KS)','Inman (KS)','drift'),
('Lawrence Free (KS)','Lawrence Free State (KS)','drift'),
('Otis Bison (KS)','Otis-Bison (KS)','drift'),
('Wichita Bishop Carroll (KS)','Wichita Carroll (KS)','drift'),
('Rural Vista [Hope-White City] (KS)','Hope Rural Vista (KS)','same school'),
('White City Rural Vista (KS)','Hope Rural Vista (KS)','same school'),
('Riverside [Wathena-Elwood] (KS)','Wathena Riverside [Wathena-Elwood] (KS)','same school'),
('South Sumner [Caldwell-South Haven] (KS)','Caldwell South Sumner [Caldwell-South Haven] (KS)','same school'),
('Anthony Chaparral (KS)','Anthony-Harper-Chaparral (KS)','same school'),
('Olathe Kansas School (KS)','Kansas School for the Deaf (KS)','same school'),
('Kansas City Christ Prep Academy (KS)','Lenexa Christ Prep Academy (KS)','same school'),
('W. Independent (KS)','Wichita Independent (KS)','same school'),
('Wichita The Independent School (KS)','Wichita Independent (KS)','same school');

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

-- 3: Christ Prep and Kansas School games (towns/opponents)
SELECT Name, Season, [Date], Opp, Source FROM #w2 WHERE Alias IN ('Kansas City Christ Prep Academy (KS)','Olathe Kansas School (KS)','W. Independent (KS)') AND Season BETWEEN 2015 AND 2026 ORDER BY Alias, Season, [Date], Name;

-- 4: names for the missing ProperNames
SELECT Team_Name FROM dbo.HS_Team_Names WHERE Team_Name LIKE 'Melvern%(KS)' OR Team_Name LIKE 'Overland Park S%(KS)' OR Team_Name LIKE '%Kapaun%(KS)';

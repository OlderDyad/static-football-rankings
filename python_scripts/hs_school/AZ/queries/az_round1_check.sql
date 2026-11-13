SET NOCOUNT ON;
IF OBJECT_ID('tempdb..#w1') IS NOT NULL DROP TABLE #w1;
CREATE TABLE #w1 (Alias varchar(150), Target varchar(150), Why varchar(100));
INSERT INTO #w1 VALUES
('Glendale Cortez (AZ)','Phoenix Cortez (AZ)','same school'),
('Scottsdale Arcadia (AZ)','Phoenix Arcadia (AZ)','same school'),
('Phoenix Canyon del Oro (AZ)','Tucson Canyon del Oro (AZ)','same school'),
('Ironwood (AZ)','Glendale Ironwood (AZ)','same school'),
('Mohave River Valley (AZ)','Mohave Valley River Valley (AZ)','same school'),
('Foothills (AZ)','Tucson Catalina Foothills (AZ)','check'),
('Window Rock (AZ)','Fort Defiance Window Rock (AZ)','same school'),
('Tempe Desert Vista (AZ)','Phoenix Desert Vista (AZ)','same school'),
('Page Sand (AZ)','Page (AZ)','same school'),
('Gilbert Desert Ridge (AZ)','Mesa Desert Ridge (AZ)','same school'),
('Estrella Foothills (AZ)','Goodyear Estrella Foothills (AZ)','same school'),
('Phoenix Carl Hayden Community (AZ)','Phoenix Carl Hayden (AZ)','same school'),
('Oro Valley Ironwood Ridge (AZ)','Tucson Ironwood Ridge (AZ)','same school'),
('Queen Creek Arizona Boys Ranch (AZ)','Queen Creek Canyon State Academy (AZ)','rename'),
('Arizona Boys Ranch (AZ)','Queen Creek Canyon State Academy (AZ)','rename'),
('Canyon State Academy (AZ)','Queen Creek Canyon State Academy (AZ)','same school'),
('Elfrida (AZ)','Elfrida Valley Union (AZ)','same school'),
('Carver (AZ)','Phoenix Carver (AZ)','same school'),
('Tucson Rincon (AZ)','Tucson Rincon-University (AZ)','co-op split'),
('Gila Bend Gila Bend (AZ)','Gila Bend (AZ)','drift'),
('Tempe Marcos De (AZ)','Tempe Marcos de Niza (AZ)','drift'),
('Phoenix Oconnor (AZ)','Phoenix O''Connor (AZ)','drift'),
('Phoenix Day (AZ)','Phoenix Day School for the Deaf (AZ)','drift'),
('Chandler Arizona College (AZ)','Chandler Arizona College Prep (AZ)','drift'),
('Gilbert San Tan (AZ)','Gilbert San Tan Charter (AZ)','drift'),
('American Leadership Academy - Gilbert North (AZ)','Gilbert North American Leadership Academy (AZ)','same school'),
('Gilbert Ala Gilbert (AZ)','Gilbert North American Leadership Academy (AZ)','drift'),
('American Leadership Academy - Ironwood (AZ)','Ironwood American Leadership Academy (AZ)','same school'),
('Ironwood Ala Ironwood (AZ)','Ironwood American Leadership Academy (AZ)','drift'),
('Queen Creek Ala Queen (AZ)','Queen Creek American Leadership Academy (AZ)','drift'),
('Waddell Ala West (AZ)','Waddell American Leadership Academy - West Foothills (AZ)','drift'),
('Florence Ala Anthem (AZ)','Florence American Leadership Academy - Anthem South (AZ)','drift'),
('Phoenix Indians (AZ)','Phoenix Indian (AZ)','same school'),
('Phoenix Indian School (AZ)','Phoenix Indian (AZ)','same school'),
('Tucson Indian School (AZ)','Tucson Indian (AZ)','same school');
SELECT w.Alias, AliasGames = (SELECT COUNT(*) FROM dbo.HS_Scores s WHERE s.Home = w.Alias OR s.Visitor = w.Alias),
       w.Target, TargetGames = (SELECT COUNT(*) FROM dbo.HS_Scores s WHERE s.Home = w.Target OR s.Visitor = w.Target),
       TargetInTeamNames = CASE WHEN EXISTS (SELECT 1 FROM dbo.HS_Team_Names t WHERE t.Team_Name = w.Target) THEN 1 ELSE 0 END,
       AliasURL = (SELECT TOP 1 u.URL FROM dbo.URL_ProperName_Mapping u WHERE u.ProperName = w.Alias),
       TargetURL = (SELECT TOP 1 u.URL FROM dbo.URL_ProperName_Mapping u WHERE u.ProperName = w.Target), w.Why
FROM #w1 w ORDER BY w.Why, w.Alias;
IF OBJECT_ID('tempdb..#w2') IS NOT NULL DROP TABLE #w2;
SELECT w.Alias, w.Target, Name = CASE WHEN s.Home IN (w.Alias, w.Target) THEN s.Home ELSE s.Visitor END,
       Opp = CASE WHEN s.Home IN (w.Alias, w.Target) THEN s.Visitor ELSE s.Home END, s.Season, s.[Date], s.Source
INTO #w2 FROM #w1 w JOIN dbo.HS_Scores s ON s.Home IN (w.Alias, w.Target) OR s.Visitor IN (w.Alias, w.Target);
SELECT a.Alias, a.Season, AliasGames = COUNT(*),
       TargetGames = (SELECT COUNT(*) FROM #w2 b WHERE b.Alias = a.Alias AND b.Name = b.Target AND b.Season = a.Season),
       SameOpp = (SELECT COUNT(*) FROM #w2 b WHERE b.Alias = a.Alias AND b.Name = b.Target AND b.Season = a.Season
                  AND EXISTS (SELECT 1 FROM #w2 c WHERE c.Alias = a.Alias AND c.Name = c.Alias AND c.Season = a.Season AND c.Opp = b.Opp))
FROM #w2 a WHERE a.Name = a.Alias GROUP BY a.Alias, a.Season ORDER BY a.Alias, a.Season;
-- Foothills (AZ) opponents
SELECT Season, [Date], Opp, Source FROM #w2 WHERE Alias = 'Foothills (AZ)' AND Name = 'Foothills (AZ)' ORDER BY Season, [Date];
-- names for the missing ProperNames
SELECT Team_Name, Games = (SELECT COUNT(*) FROM dbo.HS_Scores s WHERE s.Home = t.Team_Name OR s.Visitor = t.Team_Name) FROM dbo.HS_Team_Names t
WHERE Team_Name LIKE '%(AZ)' AND (Team_Name LIKE 'Bullhead%' OR Team_Name LIKE '%Millennium%' OR Team_Name LIKE '%Sequoia Pathway%' OR Team_Name LIKE '%Maryvale%'
   OR Team_Name LIKE '%Paradise Valley Christian%' OR Team_Name LIKE '%Cicero%' OR Team_Name LIKE 'Scottsdale Prep%' OR Team_Name LIKE '%James Madison%');

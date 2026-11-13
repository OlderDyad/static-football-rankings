SET NOCOUNT ON;
IF OBJECT_ID('tempdb..#p') IS NOT NULL DROP TABLE #p;
CREATE TABLE #p (O varchar(150), N varchar(150));
INSERT INTO #p VALUES
('Hoxie-Sheridan County (KS)','Hoxie (KS)'),('Shawnee Mission (KS)','Overland Park Shawnee Mission (KS)'),
('Seneca Nemaha Valley (KS)','Seneca Nemaha Central (KS)'),('Turon Fairfield (KS)','Langdon Fairfield (KS)'),
('Moran (KS)','Moran Marmaton Valley (KS)'),('Peabody (KS)','Peabody-Burns (KS)'),('Basehor (KS)','Basehor-Linwood (KS)'),
('Kansas City Bishop Miege (KS)','Shawnee Mission Bishop Miege (KS)'),('Roeland Park St. Agnes Catholic (KS)','Shawnee Mission Bishop Miege (KS)'),
('Wichita (KS)','Wichita East (KS)'),('Perry (KS)','Perry-Lecompton (KS)'),('Dighton (KS)','Ness City-Dighton (KS)'),('Ness City (KS)','Ness City-Dighton (KS)'),
('Gardner (KS)','Gardner-Edgerton (KS)'),('Acchs (KS)','Effingham Atchison County (KS)'),('Belleville (KS)','Belleville Republic County (KS)'),
('Jetmore (KS)','Jetmore Hodgeman County (KS)'),('Pomona (KS)','Pomona West Franklin (KS)'),('Alma (KS)','Alma Wabaunsee (KS)'),
('Lindsborg (KS)','Lindsborg Smoky Valley (KS)'),('Assaria Southeast of Saline (KS)','Gypsum Southeast of Saline (KS)'),
('Claflin Central Plains (KS)','Lorraine Central Plains (KS)'),('Wichita Word of Life (KS)','Park City Life Prep (KS)');
IF OBJECT_ID('tempdb..#c') IS NOT NULL DROP TABLE #c;
SELECT Name, Season, Games = COUNT(*) INTO #c FROM (
  SELECT Home AS Name, Season FROM dbo.HS_Scores WHERE Home IN (SELECT O FROM #p UNION SELECT N FROM #p)
  UNION ALL SELECT Visitor, Season FROM dbo.HS_Scores WHERE Visitor IN (SELECT O FROM #p UNION SELECT N FROM #p)) x GROUP BY Name, Season;
SELECT p.O, p.N, Season = COALESCE(o.Season, n.Season), O_Games = ISNULL(o.Games, 0), N_Games = ISNULL(n.Games, 0)
FROM #p p
JOIN (SELECT DISTINCT Season FROM #c) s ON 1 = 1
LEFT JOIN #c o ON o.Name = p.O AND o.Season = s.Season
LEFT JOIN #c n ON n.Name = p.N AND n.Season = s.Season
WHERE o.Season IS NOT NULL OR n.Season IS NOT NULL
ORDER BY p.O, p.N, 3;

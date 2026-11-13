-- NE old name vs co-op / consolidated name: games per season for each pair (to find the split year)
IF OBJECT_ID('tempdb..#cy_p') IS NOT NULL DROP TABLE #cy_p;
CREATE TABLE #cy_p (OldName varchar(150), NewName varchar(150));
INSERT INTO #cy_p VALUES
 ('Valley (NE)','Valley Douglas County West (NE)'),
 ('Oakland (NE)','Oakland-Craig (NE)'),
 ('Tekamah (NE)','Tekamah-Herman (NE)'),
 ('Dawson (NE)','Dawson-Verdon (NE)'),
 ('Wauneta (NE)','Wauneta-Palisade (NE)'),
 ('Fremont (NE)','Fremont St. Patrick''s (NE)'),
 ('Laurel (NE)','Laurel-Concord (NE)'),
 ('West Point (NE)','West Point Guardian Angels Central Catholic (NE)'),
 ('Table Rock (NE)','Table Rock-Steinauer (NE)'),
 ('Emerson (NE)','Emerson-Hubbard (NE)'),
 ('Scribner (NE)','Scribner-Snyder (NE)'),
 ('Elmwood (NE)','Elmwood-Murdock (NE)'),
 ('Diller (NE)','Diller-Odell (NE)'),
 ('Papillion (NE)','Papillion-La Vista (NE)'),
 ('Arthur (NE)','Arthur County (NE)'),
 ('Howells (NE)','Howells-Dodge (NE)'),
 ('Lawrence (NE)','Lawrence-Nelson (NE)'),
 ('Ansley (NE)','Ansley-Litchfield (NE)'),
 ('Chambers (NE)','Chambers-Wheeler Central (NE)'),
 ('Chambers-Wheeler Central (NE)','Chambers-Wheeler Central-Ewing (NE)'),
 ('Albion (NE)','Albion Boone Central (NE)'),
 ('Neligh (NE)','Neligh-Oakdale (NE)'),
 ('Bruning (NE)','Bruning-Davenport-Shickley (NE)'),
 ('Hartington (NE)','Hartington-Newcastle (NE)'),
 ('Wilber (NE)','Wilber-Clatonia (NE)'),
 ('Cedar Rapids (NE)','Cedar Rapids Riverside (NE)'),
 ('Waterloo (NE)','Waterloo-Concordia (NE)'),
 ('Benedict (NE)','Benedict Consolidated (NE)'),
 ('Harrison (NE)','Harrison Sioux County (NE)'),
 ('Albion Boone Central (NE)','Albion Boone Central-Newman Grove (NE)'),
 ('Spencer (NE)','Spencer Boyd County (NE)'),
 ('Harrisburg (NE)','Harrisburg Banner County (NE)');
IF OBJECT_ID('tempdb..#cy_g') IS NOT NULL DROP TABLE #cy_g;
SELECT Team = Home, Season INTO #cy_g FROM dbo.HS_Scores WHERE Home IN (SELECT OldName FROM #cy_p UNION SELECT NewName FROM #cy_p)
UNION ALL SELECT Visitor, Season FROM dbo.HS_Scores WHERE Visitor IN (SELECT OldName FROM #cy_p UNION SELECT NewName FROM #cy_p);
-- 1: per pair and season: games under the old name / the new name
SELECT p.OldName, p.NewName, s.Season,
       OldGames = SUM(CASE WHEN g.Team = p.OldName THEN 1 ELSE 0 END),
       NewGames = SUM(CASE WHEN g.Team = p.NewName THEN 1 ELSE 0 END)
FROM #cy_p p
JOIN (SELECT DISTINCT Season FROM #cy_g) s ON 1 = 1
JOIN #cy_g g ON g.Season = s.Season AND g.Team IN (p.OldName, p.NewName)
GROUP BY p.OldName, p.NewName, s.Season
ORDER BY p.NewName, p.OldName, s.Season;

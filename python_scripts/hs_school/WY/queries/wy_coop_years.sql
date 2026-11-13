-- WY old name vs co-op / consolidated name: games per season for each pair (to find the split year)
IF OBJECT_ID('tempdb..#cy_p') IS NOT NULL DROP TABLE #cy_p;
CREATE TABLE #cy_p (OldName varchar(150), NewName varchar(150));
INSERT INTO #cy_p VALUES
 ('Deaver (WY)','Deaver-Frannie (WY)'), ('Cowley (WY)','Cowley Rocky Mountain (WY)'), ('Guernsey (WY)','Guernsey-Sunrise (WY)'),
 ('Lingle (WY)','Lingle-Fort Laramie (WY)'), ('Farson (WY)','Farson-Eden (WY)'), ('Basin (WY)','Basin Riverside (WY)'),
 ('Upton (WY)','Upton-Sundance (WY)'), ('Sundance (WY)','Upton-Sundance (WY)'), ('Manderson (WY)','Manderson-Hyattville (WY)'),
 ('Clearmont (WY)','Arvada-Clearmont (WY)'), ('Arvada (WY)','Arvada-Clearmont (WY)'), ('Byron (WY)','Cowley Rocky Mountain (WY)'),
 ('Sunrise (WY)','Guernsey-Sunrise (WY)'), ('Manderson (WY)','Basin Riverside (WY)');
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

-- Faster version: pair counts computed once (no per-row subqueries)
IF OBJECT_ID('tempdb..#sf_c') IS NOT NULL DROP TABLE #sf_c;
CREATE TABLE #sf_c (Team varchar(150), Cand varchar(150), S1 int, S2 int);
INSERT INTO #sf_c VALUES ('North Platte St. Patrick''s (NE)', 'O''Neill Saint Mary''s (NE)', 1960, 2005),
                         ('Kimball (NE)', 'Kimball (SD)', 1930, 2010), ('Kimball (NE)', 'Kimball-White Lake (SD)', 1930, 2010);
IF OBJECT_ID('tempdb..#sf_p') IS NOT NULL DROP TABLE #sf_p;
SELECT A = s.Home, B = s.Visitor, s.Season, s.ID, s.Source INTO #sf_p FROM dbo.HS_Scores s
WHERE s.Home IN (SELECT Team FROM #sf_c UNION SELECT Cand FROM #sf_c) OR s.Visitor IN (SELECT Team FROM #sf_c UNION SELECT Cand FROM #sf_c);
IF OBJECT_ID('tempdb..#sf_u') IS NOT NULL DROP TABLE #sf_u;
SELECT X = A, Opp = B, Season, ID, Source INTO #sf_u FROM #sf_p UNION ALL SELECT B, A, Season, ID, Source FROM #sf_p;
-- 1: names
SELECT Team_Name FROM dbo.HS_Team_Names WHERE Team_Name LIKE 'O''Neill%' OR Team_Name LIKE 'Kimball%' OR Team_Name LIKE 'Polk%';
-- 2: per opponent of Team inside the window: games in window, games vs Cand (any season), games vs Team outside the window
SELECT c.Team, u.Opp, InWindow = COUNT(DISTINCT u.ID),
       VsCand = (SELECT COUNT(*) FROM #sf_u v WHERE v.X = c.Cand AND v.Opp = u.Opp),
       VsTeamOutside = (SELECT COUNT(*) FROM #sf_u v WHERE v.X = c.Team AND v.Opp = u.Opp AND (v.Season < c.S1 OR v.Season > c.S2))
FROM #sf_c c JOIN #sf_u u ON u.X = c.Team AND u.Season BETWEEN c.S1 AND c.S2
GROUP BY c.Team, c.Cand, c.S1, c.S2, u.Opp ORDER BY c.Team, COUNT(DISTINCT u.ID) DESC;
-- 3: the games
SELECT c.Team, u.Season, u.Opp, u.Source, u.ID FROM #sf_c c JOIN #sf_u u ON u.X = c.Team AND u.Season BETWEEN c.S1 AND c.S2 ORDER BY c.Team, u.Season;

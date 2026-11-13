-- Two-school names in NE: for each opponent of the name, games vs the name and vs the suspected real school
IF OBJECT_ID('tempdb..#sp_c') IS NOT NULL DROP TABLE #sp_c;
CREATE TABLE #sp_c (Team varchar(150), Cand varchar(150), S1 int, S2 int);
INSERT INTO #sp_c VALUES ('North Platte St. Patrick''s (NE)', 'O''Neill St. Mary''s (NE)', 1960, 2005),
                         ('Kimball (NE)', 'Kimball (SD)', 1930, 2010), ('Polk-Hordville (NE)', 'Polk High Plains (NE)', 1965, 1990);
-- 1: does the candidate name exist?
SELECT c.Cand, InTeamNames = CASE WHEN EXISTS (SELECT 1 FROM dbo.HS_Team_Names t WHERE t.Team_Name = c.Cand) THEN 1 ELSE 0 END,
       Games = (SELECT COUNT(*) FROM dbo.HS_Scores s WHERE s.Home = c.Cand OR s.Visitor = c.Cand) FROM #sp_c c;
SELECT Team_Name FROM dbo.HS_Team_Names WHERE Team_Name LIKE 'O''Neill%' OR Team_Name LIKE 'Kimball%' OR Team_Name LIKE 'Polk%';
-- 2: per opponent (within the window): games vs Team, vs Cand (all seasons), vs Team outside the window
IF OBJECT_ID('tempdb..#sp_g') IS NOT NULL DROP TABLE #sp_g;
SELECT c.Team, c.Cand, s.ID, s.Season, Opp = CASE WHEN s.Home = c.Team THEN s.Visitor ELSE s.Home END, s.Source
INTO #sp_g FROM #sp_c c JOIN dbo.HS_Scores s ON (s.Home = c.Team OR s.Visitor = c.Team) AND s.Season BETWEEN c.S1 AND c.S2;
IF OBJECT_ID('tempdb..#sp_o') IS NOT NULL DROP TABLE #sp_o;
SELECT Team, Cand, Opp, InWindow = COUNT(*) INTO #sp_o FROM #sp_g GROUP BY Team, Cand, Opp;
SELECT o.Team, o.Opp, o.InWindow,
       VsCand = (SELECT COUNT(*) FROM dbo.HS_Scores s WHERE (s.Home = o.Cand AND s.Visitor = o.Opp) OR (s.Visitor = o.Cand AND s.Home = o.Opp)),
       VsTeamOutside = (SELECT COUNT(*) FROM dbo.HS_Scores s JOIN #sp_c c ON c.Team = o.Team
                        WHERE (s.Season < c.S1 OR s.Season > c.S2) AND ((s.Home = o.Team AND s.Visitor = o.Opp) OR (s.Visitor = o.Team AND s.Home = o.Opp)))
FROM #sp_o o ORDER BY o.Team, o.InWindow DESC;
-- 3: the games (IDs)
SELECT Team, Cand, Season, Opp, Source, ID FROM #sp_g ORDER BY Team, Season;

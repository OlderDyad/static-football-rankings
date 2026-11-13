-- WY teams with a same-named school in another state: games vs that state's opponents where the opponent played the twin far more often
IF OBJECT_ID('tempdb..#tw_g') IS NOT NULL DROP TABLE #tw_g;
SELECT x.ID, x.Team, x.Opp, x.Season, x.Source,
       Twin = LEFT(RTRIM(x.Team), LEN(RTRIM(x.Team)) - 5) + ' (' + SUBSTRING(RTRIM(x.Opp), LEN(RTRIM(x.Opp)) - 2, 2) + ')'
INTO #tw_g
FROM (SELECT ID, Team = Home, Opp = Visitor, Season, Source FROM dbo.HS_Scores WHERE RTRIM(Home) LIKE '%(WY)'
      UNION ALL SELECT ID, Visitor, Home, Season, Source FROM dbo.HS_Scores WHERE RTRIM(Visitor) LIKE '%(WY)') x
WHERE RTRIM(x.Opp) LIKE '%([A-Z][A-Z])' AND RTRIM(x.Opp) NOT LIKE '%(WY)';
IF OBJECT_ID('tempdb..#tw_c') IS NOT NULL DROP TABLE #tw_c;
SELECT g.Team, g.Twin, g.Opp, WyGames = COUNT(*), FirstSeason = MIN(g.Season), LastSeason = MAX(g.Season)
INTO #tw_c FROM #tw_g g JOIN dbo.HS_Team_Names tn ON tn.Team_Name = g.Twin GROUP BY g.Team, g.Twin, g.Opp;
IF OBJECT_ID('tempdb..#tw_t') IS NOT NULL DROP TABLE #tw_t;
SELECT c.Team, c.Twin, c.Opp, c.WyGames, c.FirstSeason, c.LastSeason,
       TwinGames = (SELECT COUNT(*) FROM dbo.HS_Scores s WHERE (s.Home = c.Twin AND s.Visitor = c.Opp) OR (s.Visitor = c.Twin AND s.Home = c.Opp))
INTO #tw_t FROM #tw_c c;
-- 1: candidate opponents (twin played them more than twice as often, at least 3 times)
SELECT * FROM #tw_t WHERE TwinGames >= 3 AND TwinGames > 2 * WyGames ORDER BY Team, TwinGames DESC;
-- 2: the games themselves (IDs) for those candidates
SELECT g.Team, g.Twin, g.Opp, g.Season, g.Source, g.ID
FROM #tw_g g JOIN #tw_t t ON t.Team = g.Team AND t.Opp = g.Opp
WHERE t.TwinGames >= 3 AND t.TwinGames > 2 * t.WyGames ORDER BY g.Team, g.Season;

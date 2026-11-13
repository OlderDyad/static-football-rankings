-- WY names that may hold another state's same-named school (Lyman SD/NE, Sheridan MT, Cody NE, Buffalo SD, Newcastle NE ...)
-- For each WY team: games by opponent state, and whether a same-named team exists in that state.
IF OBJECT_ID('tempdb..#ws_g') IS NOT NULL DROP TABLE #ws_g;
SELECT x.Team, x.Opp, x.Season, x.ID, x.Source,
       OppSt = SUBSTRING(RTRIM(x.Opp), LEN(RTRIM(x.Opp)) - 2, 2),
       Base = LEFT(RTRIM(x.Team), LEN(RTRIM(x.Team)) - 5)
INTO #ws_g
FROM (SELECT ID, Team = Home, Opp = Visitor, Season, Source FROM dbo.HS_Scores WHERE RTRIM(Home) LIKE '%(WY)'
      UNION ALL SELECT ID, Visitor, Home, Season, Source FROM dbo.HS_Scores WHERE RTRIM(Visitor) LIKE '%(WY)') x
WHERE RTRIM(x.Opp) LIKE '%([A-Z][A-Z])';

-- 1: team x opponent-state counts where a same-named team exists in that other state
IF OBJECT_ID('tempdb..#ws_c') IS NOT NULL DROP TABLE #ws_c;
SELECT g.Team, g.OppSt, Games = COUNT(*), FirstSeason = MIN(g.Season), LastSeason = MAX(g.Season), TwinName = t.Team_Name
INTO #ws_c
FROM #ws_g g
JOIN dbo.HS_Team_Names t ON t.Team_Name = g.Base + ' (' + g.OppSt + ')'
WHERE g.OppSt <> 'WY'
GROUP BY g.Team, g.OppSt, t.Team_Name;
SELECT c.Team, c.OppSt, c.Games, c.FirstSeason, c.LastSeason, c.TwinName,
       TwinGames = (SELECT COUNT(*) FROM dbo.HS_Scores s WHERE s.Home = c.TwinName OR s.Visitor = c.TwinName),
       TeamGamesTotal = (SELECT COUNT(*) FROM #ws_g a WHERE a.Team = c.Team)
FROM #ws_c c ORDER BY c.Games DESC;

-- 2: for those teams: every opponent in the twin's state (to see which games are really the twin's)
SELECT c.Team, c.OppSt, g.Opp, Games = COUNT(*), FirstSeason = MIN(g.Season), LastSeason = MAX(g.Season)
FROM #ws_c c JOIN #ws_g g ON g.Team = c.Team AND g.OppSt = c.OppSt
GROUP BY c.Team, c.OppSt, g.Opp ORDER BY c.Team, c.OppSt, COUNT(*) DESC;

-- State road map: data-quality measures for every state (read-only). Can take a few minutes.
-- Run: python hs_cleanup.py query US state_scores.sql
IF OBJECT_ID('tempdb..#ss_t') IS NOT NULL DROP TABLE #ss_t;
SELECT x.ID, x.Team, x.Season, x.[Date], x.Opp, x.Source, x.Access_ID,
       St = SUBSTRING(RTRIM(x.Team), LEN(RTRIM(x.Team)) - 2, 2)
INTO #ss_t
FROM (SELECT ID, Team = Home, Opp = Visitor, Season, [Date], Source, Access_ID FROM dbo.HS_Scores
      UNION ALL
      SELECT ID, Visitor, Home, Season, [Date], Source, Access_ID FROM dbo.HS_Scores) x
WHERE RTRIM(x.Team) LIKE '%([A-Z][A-Z])';
CREATE INDEX ix_ss_t ON #ss_t (St, Team, [Date]);

-- names per state
IF OBJECT_ID('tempdb..#ss_n') IS NOT NULL DROP TABLE #ss_n;
SELECT St, Team, Games = COUNT(*), LastSeason = MAX(Season) INTO #ss_n FROM #ss_t GROUP BY St, Team;

-- same team, two games on the same date (different opponents)
IF OBJECT_ID('tempdb..#ss_d') IS NOT NULL DROP TABLE #ss_d;
SELECT St, Team, [Date] INTO #ss_d FROM #ss_t WHERE [Date] IS NOT NULL AND MONTH([Date]) <> 6
GROUP BY St, Team, [Date] HAVING COUNT(DISTINCT Opp) > 1;

-- same season, same two teams, same score, 2+ rows (remaining duplicate copies)
IF OBJECT_ID('tempdb..#ss_p') IS NOT NULL DROP TABLE #ss_p;
SELECT s.ID,
       T1 = CASE WHEN s.Home <= s.Visitor THEN s.Home ELSE s.Visitor END, T2 = CASE WHEN s.Home <= s.Visitor THEN s.Visitor ELSE s.Home END,
       S1 = CASE WHEN s.Home <= s.Visitor THEN s.Home_Score ELSE s.Visitor_Score END, S2 = CASE WHEN s.Home <= s.Visitor THEN s.Visitor_Score ELSE s.Home_Score END,
       s.Season
INTO #ss_p FROM dbo.HS_Scores s WHERE s.Home_Score IS NOT NULL;
IF OBJECT_ID('tempdb..#ss_q') IS NOT NULL DROP TABLE #ss_q;
SELECT T1, n = COUNT(*) - 1 INTO #ss_q FROM #ss_p GROUP BY Season, T1, T2, S1, S2 HAVING COUNT(*) > 1;

-- mapped names (MaxPreps URL)
IF OBJECT_ID('tempdb..#ss_m') IS NOT NULL DROP TABLE #ss_m;
SELECT DISTINCT Name = ProperName INTO #ss_m FROM dbo.URL_ProperName_Mapping;

-- per-state rows from each piece
IF OBJECT_ID('tempdb..#ss_g') IS NOT NULL DROP TABLE #ss_g;
SELECT St, TeamGames = COUNT(*),
       Rows2004on = SUM(CASE WHEN Season >= 2004 THEN 1 ELSE 0 END),
       OldMaxPreps2004on = SUM(CASE WHEN Season >= 2004 AND Access_ID IS NULL AND Source LIKE '%maxpreps%' AND Source NOT LIKE '%/__-__/%' THEN 1 ELSE 0 END),
       Pre1950 = SUM(CASE WHEN Season < 1950 THEN 1 ELSE 0 END),
       EstimatedDates = SUM(CASE WHEN Source = 'Mr. Dan R Ford Sr' OR Source LIKE '%classmates%' OR Source LIKE '%e-yearbook%' THEN 1 ELSE 0 END)
INTO #ss_g FROM #ss_t GROUP BY St;

IF OBJECT_ID('tempdb..#ss_x') IS NOT NULL DROP TABLE #ss_x;
SELECT n.St, Names = COUNT(*),
       TinyNames = SUM(CASE WHEN n.Games <= 2 THEN 1 ELSE 0 END),
       ActiveNoURL = SUM(CASE WHEN n.LastSeason >= 2024 AND n.Games >= 50 AND m.Name IS NULL
                               AND n.Team NOT LIKE '% JV (%' AND n.Team NOT LIKE '% B (%' THEN 1 ELSE 0 END),
       SubVarsityNames = SUM(CASE WHEN n.Team LIKE '% JV (%' OR n.Team LIKE '% B (%' OR n.Team LIKE '%Frosh%' OR n.Team LIKE '%Sophomore%' THEN 1 ELSE 0 END)
INTO #ss_x FROM #ss_n n LEFT JOIN #ss_m m ON m.Name = n.Team GROUP BY n.St;

IF OBJECT_ID('tempdb..#ss_dd') IS NOT NULL DROP TABLE #ss_dd;
SELECT St, DoubleBookedDays = COUNT(*) INTO #ss_dd FROM #ss_d GROUP BY St;
IF OBJECT_ID('tempdb..#ss_qq') IS NOT NULL DROP TABLE #ss_qq;
SELECT St = SUBSTRING(RTRIM(T1), LEN(RTRIM(T1)) - 2, 2), SameScoreCopies = SUM(n) INTO #ss_qq FROM #ss_q
WHERE RTRIM(T1) LIKE '%([A-Z][A-Z])' GROUP BY SUBSTRING(RTRIM(T1), LEN(RTRIM(T1)) - 2, 2);

IF OBJECT_ID('tempdb..#ss_a') IS NOT NULL DROP TABLE #ss_a;
SELECT St = SUBSTRING(RTRIM(Home), LEN(RTRIM(Home)) - 2, 2), Archived = COUNT(*) INTO #ss_a
FROM dbo.HS_Scores_Duplicate_Archive WHERE RTRIM(Home) LIKE '%([A-Z][A-Z])' GROUP BY SUBSTRING(RTRIM(Home), LEN(RTRIM(Home)) - 2, 2);

-- 1: the road map (one row per state; per-1,000-team-games rates make states comparable)
SELECT g.St, g.TeamGames, x.Names,
       GamesPerName = CAST(1.0 * g.TeamGames / NULLIF(x.Names, 0) AS decimal(8, 1)),
       x.TinyNames, TinyNamePct = CAST(100.0 * x.TinyNames / NULLIF(x.Names, 0) AS decimal(5, 1)),
       DoubleBookedDays = ISNULL(dd.DoubleBookedDays, 0),
       DoubleBookedPer1000 = CAST(1000.0 * ISNULL(dd.DoubleBookedDays, 0) / NULLIF(g.TeamGames, 0) AS decimal(6, 2)),
       SameScoreCopies = ISNULL(q.SameScoreCopies, 0),
       SameScorePer1000 = CAST(1000.0 * ISNULL(q.SameScoreCopies, 0) / NULLIF(g.TeamGames, 0) AS decimal(6, 2)),
       OldMaxPrepsPct2004on = CAST(100.0 * g.OldMaxPreps2004on / NULLIF(g.Rows2004on, 0) AS decimal(5, 1)),
       x.ActiveNoURL, x.SubVarsityNames,
       Pre1950Pct = CAST(100.0 * g.Pre1950 / NULLIF(g.TeamGames, 0) AS decimal(5, 1)),
       EstimatedDatePct = CAST(100.0 * g.EstimatedDates / NULLIF(g.TeamGames, 0) AS decimal(5, 1)),
       ArchivedSoFar = ISNULL(a.Archived, 0),
       CleanupStepsDone = (SELECT COUNT(*) FROM dbo.HS_Cleanup_Status c WHERE c.State = g.St AND c.Status = 'done')
FROM #ss_g g
JOIN #ss_x x ON x.St = g.St
LEFT JOIN #ss_dd dd ON dd.St = g.St
LEFT JOIN #ss_qq q ON q.St = g.St
LEFT JOIN #ss_a a ON a.St = g.St
WHERE g.TeamGames >= 500
ORDER BY g.TeamGames DESC;

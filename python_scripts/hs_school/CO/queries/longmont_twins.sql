-- The 16 games moved Longmont -> Longmont Christian (2004-2007). MaxPreps shows Longmont Christian 2006 did NOT play them.
-- Name-independent twin check: does the OPPONENT have another game within 3 days with the same score pair (any team name)?
IF OBJECT_ID('tempdb..#lt_m') IS NOT NULL DROP TABLE #lt_m;
SELECT s.ID, s.Season, s.[Date], s.Home, s.Home_Score, s.Visitor, s.Visitor_Score, s.Source,
       Opp = CASE WHEN s.Home = 'Longmont Christian (CO)' THEN s.Visitor ELSE s.Home END,
       OppScore = CASE WHEN s.Home = 'Longmont Christian (CO)' THEN s.Visitor_Score ELSE s.Home_Score END,
       OurScore = CASE WHEN s.Home = 'Longmont Christian (CO)' THEN s.Home_Score ELSE s.Visitor_Score END
INTO #lt_m
FROM dbo.HS_Scores s
WHERE s.ID IN (SELECT ScoresID FROM dbo.HS_Scores_Change_Log WHERE Script = 'hs_cleanup.py move-team' AND NewValue = 'Longmont Christian (CO)');

-- 1: each moved game and every twin found for its opponent (same score pair, within 3 days, different row)
SELECT m.Season, m.[Date], m.Home, m.Home_Score, m.Visitor, m.Visitor_Score,
       Twin_Date = t.[Date], Twin_Home = t.Home, Twin_HS = t.Home_Score, Twin_Visitor = t.Visitor, Twin_VS = t.Visitor_Score,
       Twin_Source = t.Source, Twin_AccessID = t.Access_ID, m.ID, Twin_ID = t.ID
FROM #lt_m m
LEFT JOIN dbo.HS_Scores t ON t.ID <> m.ID AND t.Season = m.Season AND ABS(DATEDIFF(day, t.[Date], m.[Date])) <= 3
     AND ((t.Home = m.Opp AND t.Home_Score = m.OppScore AND t.Visitor_Score = m.OurScore)
       OR (t.Visitor = m.Opp AND t.Visitor_Score = m.OppScore AND t.Home_Score = m.OurScore))
ORDER BY m.Season, m.[Date];

-- 2: the same check for ALL old-layer (www.maxpreps.com, no Access_ID) Colorado rows 2004-2016:
--    how many have a twin under a different name (same date +-1, same score pair, one team in common)?
IF OBJECT_ID('tempdb..#lt_o') IS NOT NULL DROP TABLE #lt_o;
SELECT ID, Season, [Date], Home, Visitor, Home_Score, Visitor_Score
INTO #lt_o FROM dbo.HS_Scores
WHERE Season BETWEEN 2004 AND 2016 AND (Home LIKE '%(CO)' OR Visitor LIKE '%(CO)') AND Home_Score IS NOT NULL;
CREATE INDEX ix_lt ON #lt_o (Season, [Date]);
SELECT o.Season, OldRows = COUNT(DISTINCT o.ID),
       TwinUnderOtherName = COUNT(DISTINCT CASE WHEN t.ID IS NOT NULL THEN o.ID END)
FROM #lt_o o
JOIN dbo.HS_Scores s ON s.ID = o.ID AND s.Access_ID IS NULL AND s.Source IN ('www.maxpreps.com', '[www.maxpreps.com]', 'MaxPreps')
LEFT JOIN #lt_o t ON t.ID <> o.ID AND t.Season = o.Season AND ABS(DATEDIFF(day, t.[Date], o.[Date])) <= 1
     AND ((t.Home = o.Home AND t.Visitor <> o.Visitor AND t.Home_Score = o.Home_Score AND t.Visitor_Score = o.Visitor_Score)
       OR (t.Visitor = o.Visitor AND t.Home <> o.Home AND t.Home_Score = o.Home_Score AND t.Visitor_Score = o.Visitor_Score)
       OR (t.Home = o.Visitor AND t.Visitor <> o.Home AND t.Home_Score = o.Visitor_Score AND t.Visitor_Score = o.Home_Score)
       OR (t.Visitor = o.Home AND t.Home <> o.Visitor AND t.Visitor_Score = o.Home_Score AND t.Home_Score = o.Visitor_Score))
GROUP BY o.Season ORDER BY o.Season;

-- 3: CO MaxPreps layers by season: old macro rows vs re-imported pipeline rows (Access_ID / per-game URL)
SELECT Season,
       OldMacroRows = SUM(CASE WHEN Access_ID IS NULL AND Source LIKE '%maxpreps%' AND Source NOT LIKE '%/__-__/%' THEN 1 ELSE 0 END),
       PipelineRows = SUM(CASE WHEN Access_ID IS NOT NULL OR Source LIKE '%maxpreps.com/%/__-__/%' THEN 1 ELSE 0 END),
       OtherRows = SUM(CASE WHEN Source NOT LIKE '%maxpreps%' OR Source IS NULL THEN 1 ELSE 0 END)
FROM dbo.HS_Scores
WHERE Season BETWEEN 2004 AND 2026 AND (Home LIKE '%(CO)' OR Visitor LIKE '%(CO)')
GROUP BY Season ORDER BY Season;

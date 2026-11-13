SET NOCOUNT ON;
-- Washington (KS): which school is each game? opponent history with the three candidate schools
IF OBJECT_ID('tempdb..#w') IS NOT NULL DROP TABLE #w;
SELECT s.ID, s.Season, s.[Date], Opp = CASE WHEN s.Home = 'Washington (KS)' THEN s.Visitor ELSE s.Home END,
       WS = CASE WHEN s.Home = 'Washington (KS)' THEN s.Home_Score ELSE s.Visitor_Score END,
       OS = CASE WHEN s.Home = 'Washington (KS)' THEN s.Visitor_Score ELSE s.Home_Score END, s.Source
INTO #w FROM dbo.HS_Scores s WHERE s.Home = 'Washington (KS)' OR s.Visitor = 'Washington (KS)';
IF OBJECT_ID('tempdb..#h') IS NOT NULL DROP TABLE #h;
SELECT Cand, Opp, Games = COUNT(*) INTO #h FROM (
  SELECT Cand = s.Home, Opp = s.Visitor FROM dbo.HS_Scores s WHERE s.Home IN ('Kansas City Washington (KS)','Washington County (KS)','Washington (MO)')
  UNION ALL SELECT s.Visitor, s.Home FROM dbo.HS_Scores s WHERE s.Visitor IN ('Kansas City Washington (KS)','Washington County (KS)','Washington (MO)')) x
GROUP BY Cand, Opp;
SELECT w.Season, w.[Date], w.Opp, w.WS, w.OS, w.Source,
  KCW = ISNULL((SELECT Games FROM #h WHERE Cand = 'Kansas City Washington (KS)' AND Opp = w.Opp), 0),
  WCO = ISNULL((SELECT Games FROM #h WHERE Cand = 'Washington County (KS)' AND Opp = w.Opp), 0),
  WMO = ISNULL((SELECT Games FROM #h WHERE Cand = 'Washington (MO)' AND Opp = w.Opp), 0), w.ID
FROM #w w ORDER BY w.Season, w.[Date];
SELECT Name, FirstSeason = MIN(Season), LastSeason = MAX(Season), Games = COUNT(*) FROM (
  SELECT Home AS Name, Season FROM dbo.HS_Scores WHERE Home IN ('Kansas City Washington (KS)','Washington County (KS)','Washington (MO)','Washington (KS)')
  UNION ALL SELECT Visitor, Season FROM dbo.HS_Scores WHERE Visitor IN ('Kansas City Washington (KS)','Washington County (KS)','Washington (MO)','Washington (KS)')) x GROUP BY Name;

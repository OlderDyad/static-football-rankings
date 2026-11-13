-- Step 6.0: Colorado dirty seasons (what the CO cleanup touched, by season)
-- 1: HS_Consolidation_Log columns (merges are logged there)
SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'HS_Consolidation_Log' ORDER BY ORDINAL_POSITION;

-- 2: per season: archived CO rows (since 2026-11-04), logged field changes, renamed (merged/moved) games, and CO games now
IF OBJECT_ID('tempdb..#ds_a') IS NOT NULL DROP TABLE #ds_a;
SELECT a.Season, n = COUNT(*) INTO #ds_a
FROM dbo.HS_Scores_Duplicate_Archive a
WHERE a.RunAt >= '2026-11-04' AND (RTRIM(a.Home) LIKE '%(CO)' OR RTRIM(a.Visitor) LIKE '%(CO)')
GROUP BY a.Season;

IF OBJECT_ID('tempdb..#ds_c') IS NOT NULL DROP TABLE #ds_c;
SELECT s.Season, n = COUNT(DISTINCT l.ScoresID) INTO #ds_c
FROM dbo.HS_Scores_Change_Log l JOIN dbo.HS_Scores s ON s.ID = l.ScoresID
WHERE l.Script LIKE 'hs_cleanup.py%' AND l.FieldChanged <> 'ROW_DELETED'
  AND (RTRIM(s.Home) LIKE '%(CO)' OR RTRIM(s.Visitor) LIKE '%(CO)')
GROUP BY s.Season;

-- games now carrying a name that the CO alias rules merged into (survivor names of merged aliases are not directly listed,
-- so count games whose name was a consolidation target in the CO rounds via the alias table)
IF OBJECT_ID('tempdb..#ds_t') IS NOT NULL DROP TABLE #ds_t;
SELECT DISTINCT Name = Standardized_Name INTO #ds_t FROM dbo.HS_Team_Name_Alias
WHERE Standardized_Name LIKE '%(CO)' AND Alias_Name <> Standardized_Name;

IF OBJECT_ID('tempdb..#ds_g') IS NOT NULL DROP TABLE #ds_g;
SELECT s.Season, Games = COUNT(*),
       MergedNameGames = SUM(CASE WHEN th.Name IS NOT NULL OR tv.Name IS NOT NULL THEN 1 ELSE 0 END)
INTO #ds_g
FROM dbo.HS_Scores s
LEFT JOIN #ds_t th ON th.Name = s.Home
LEFT JOIN #ds_t tv ON tv.Name = s.Visitor
WHERE RTRIM(s.Home) LIKE '%(CO)' OR RTRIM(s.Visitor) LIKE '%(CO)'
GROUP BY s.Season;

SELECT g.Season, CO_Games = g.Games, Archived = ISNULL(a.n, 0), FieldChanges = ISNULL(c.n, 0),
       ArchivedPlusChanged = ISNULL(a.n, 0) + ISNULL(c.n, 0),
       PctTouched = CAST(100.0 * (ISNULL(a.n, 0) + ISNULL(c.n, 0)) / NULLIF(g.Games + ISNULL(a.n, 0), 0) AS decimal(5, 1)),
       g.MergedNameGames
FROM #ds_g g LEFT JOIN #ds_a a ON a.Season = g.Season LEFT JOIN #ds_c c ON c.Season = g.Season
ORDER BY g.Season;

SET NOCOUNT ON;
IF OBJECT_ID('tempdb..#c') IS NOT NULL DROP TABLE #c;
SELECT DISTINCT c.ScoresID, c.NewValue AS MovedTo, Reason = LEFT(c.Reason, 60)
INTO #c FROM dbo.HS_Scores_Change_Log c
WHERE c.Script = 'hs_cleanup.py move-team' AND c.ChangedAt >= '2026-11-09'
  AND c.NewValue IN ('Hartford Bulkeley (CT)', 'New London (CT)', 'Bristol (RI)', 'Providence Hope (RI)', 'Springfield Commerce (MA)', 'Waterbury McTernan (CT)');
SELECT c.MovedTo, s.Season, s.[Date], Opp = CASE WHEN s.Home = c.MovedTo THEN s.Visitor ELSE s.Home END,
       TS = CASE WHEN s.Home = c.MovedTo THEN s.Home_Score ELSE s.Visitor_Score END, OS = CASE WHEN s.Home = c.MovedTo THEN s.Visitor_Score ELSE s.Home_Score END,
       s.Source, s.ID
FROM #c c JOIN dbo.HS_Scores s ON s.ID = c.ScoresID ORDER BY 1, 2, 3;
-- remaining games under the source names
SELECT Name, Games = COUNT(*), MinS = MIN(Season), MaxS = MAX(Season) FROM (
  SELECT Home AS Name, Season FROM dbo.HS_Scores WHERE Home IN ('New London Buckeley (CT)','Bristol (CT)','Bristol Mt. Hope (RI)','Boston Commerce (MA)','Hartford Bulkeley (CT)','Providence Hope (RI)','Bristol (RI)')
  UNION ALL SELECT Visitor, Season FROM dbo.HS_Scores WHERE Visitor IN ('New London Buckeley (CT)','Bristol (CT)','Bristol Mt. Hope (RI)','Boston Commerce (MA)','Hartford Bulkeley (CT)','Providence Hope (RI)','Bristol (RI)')) x GROUP BY Name;

-- Step 4.2 (national): winner-flip phantom pairs. Same two teams, same season, dates within 10 days,
-- same two numbers but credited to opposite teams (A 21-14 B and B 21-14 A). Dedup v4 does not catch these.
SET NOCOUNT ON;
IF OBJECT_ID('tempdb..#pp') IS NOT NULL DROP TABLE #pp;
SELECT s.ID, s.Season, s.[Date],
       T1 = CASE WHEN s.Home < s.Visitor THEN s.Home ELSE s.Visitor END,
       T2 = CASE WHEN s.Home < s.Visitor THEN s.Visitor ELSE s.Home END,
       S1 = CASE WHEN s.Home < s.Visitor THEN s.Home_Score ELSE s.Visitor_Score END,
       S2 = CASE WHEN s.Home < s.Visitor THEN s.Visitor_Score ELSE s.Home_Score END,
       Src = LEFT(s.Source, 80)
INTO #pp FROM dbo.HS_Scores s
WHERE s.Home_Score IS NOT NULL AND s.Visitor_Score IS NOT NULL AND s.Home_Score <> s.Visitor_Score;
CREATE INDEX ix_pp ON #pp (T1, T2, Season);
-- 1: summary by state of T1
SELECT State = RIGHT(RTRIM(a.T1), 3), Pairs = COUNT(*)
FROM #pp a JOIN #pp b ON a.T1 = b.T1 AND a.T2 = b.T2 AND a.Season = b.Season
 AND a.S1 = b.S2 AND a.S2 = b.S1 AND a.ID < b.ID AND ABS(DATEDIFF(day, a.[Date], b.[Date])) <= 10
GROUP BY RIGHT(RTRIM(a.T1), 3) ORDER BY Pairs DESC;
-- 2: every pair
SELECT a.Season, A_Date = a.[Date], a.T1, A_S1 = a.S1, a.T2, A_S2 = a.S2, A_Src = a.Src,
       B_Date = b.[Date], B_S1 = b.S1, B_S2 = b.S2, B_Src = b.Src, AID = a.ID, BID = b.ID
FROM #pp a JOIN #pp b ON a.T1 = b.T1 AND a.T2 = b.T2 AND a.Season = b.Season
 AND a.S1 = b.S2 AND a.S2 = b.S1 AND a.ID < b.ID AND ABS(DATEDIFF(day, a.[Date], b.[Date])) <= 10
ORDER BY a.T1, a.Season;

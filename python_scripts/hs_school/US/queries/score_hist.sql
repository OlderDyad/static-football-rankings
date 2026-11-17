-- Step 4.1 (national): score profile per source family. Read-only.
SET NOCOUNT ON;
IF OBJECT_ID('tempdb..#sh') IS NOT NULL DROP TABLE #sh;
SELECT Src = CASE
    WHEN s.Source IS NULL OR LTRIM(s.Source) = '' THEN '(blank)'
    WHEN s.Source LIKE '%://%' THEN LEFT(SUBSTRING(s.Source, CHARINDEX('://', s.Source) + 3, 200),
         CHARINDEX('/', SUBSTRING(s.Source, CHARINDEX('://', s.Source) + 3, 200) + '/') - 1)
    WHEN s.Source LIKE '%[_]19[0-9][0-9][_]%' OR s.Source LIKE '%[_]20[0-9][0-9][_]%'
         THEN LEFT(s.Source, PATINDEX('%[_][12][09][0-9][0-9][_]%', s.Source) - 1) + ' (newspaper file)'
    ELSE LEFT(s.Source, 40) END,
    s.Season, H = s.Home_Score, V = s.Visitor_Score,
    Hi = CASE WHEN s.Home_Score >= s.Visitor_Score THEN s.Home_Score ELSE s.Visitor_Score END,
    Lo = CASE WHEN s.Home_Score >= s.Visitor_Score THEN s.Visitor_Score ELSE s.Home_Score END,
    s.Forfeit
INTO #sh FROM dbo.HS_Scores s
WHERE s.Home_Score IS NOT NULL AND s.Visitor_Score IS NOT NULL;
-- 1: per source family (>= 200 games): oddities per 1,000 games
SELECT Src, Games = COUNT(*), FirstSeason = MIN(Season), LastSeason = MAX(Season),
       AvgTotal = CAST(AVG(CAST(H + V AS float)) AS decimal(6,1)),
       TiePct = CAST(100.0 * SUM(CASE WHEN H = V THEN 1 ELSE 0 END) / COUNT(*) AS decimal(5,1)),
       ShutoutPct = CAST(100.0 * SUM(CASE WHEN Lo = 0 AND Hi > 0 THEN 1 ELSE 0 END) / COUNT(*) AS decimal(5,1)),
       Neg = SUM(CASE WHEN H < 0 OR V < 0 THEN 1 ELSE 0 END),
       Score1 = SUM(CASE WHEN H = 1 OR V = 1 THEN 1 ELSE 0 END),
       Over100 = SUM(CASE WHEN Hi >= 100 THEN 1 ELSE 0 END),
       ZeroZero = SUM(CASE WHEN H = 0 AND V = 0 THEN 1 ELSE 0 END),
       TwoZeroNoFlag = SUM(CASE WHEN Hi = 2 AND Lo = 0 AND Forfeit IS NULL AND Season > 1949 THEN 1 ELSE 0 END),
       OneZero = SUM(CASE WHEN Hi = 1 AND Lo = 0 THEN 1 ELSE 0 END)
FROM #sh GROUP BY Src HAVING COUNT(*) >= 200
ORDER BY Games DESC;
-- 2: rows with impossible / suspicious scores (negative, exactly 1 not 1-0, 100+)
SELECT TOP 2000 s.ID, s.Season, s.[Date], s.Home, s.Home_Score, s.Visitor, s.Visitor_Score, s.Forfeit, Src = LEFT(s.Source, 80)
FROM dbo.HS_Scores s
WHERE s.Home_Score < 0 OR s.Visitor_Score < 0
   OR ((s.Home_Score = 1 OR s.Visitor_Score = 1) AND NOT (s.Home_Score + s.Visitor_Score = 1))
   OR s.Home_Score >= 100 OR s.Visitor_Score >= 100
ORDER BY s.Season, s.[Date];

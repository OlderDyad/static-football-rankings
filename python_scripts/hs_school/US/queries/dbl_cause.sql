SET NOCOUNT ON;
-- Why do PA / NJ / TX have so many double-booked dates? same team, two different games within 1 day, by source pair
IF OBJECT_ID('tempdb..#g') IS NOT NULL DROP TABLE #g;
SELECT ID, Season, [Date], Team = Home, Opp = Visitor, ST = SUBSTRING(RIGHT(RTRIM(Home), 4), 2, 2),
       Src = CASE WHEN Source LIKE '%maxpreps%' THEN 'MaxPreps' WHEN Source IS NULL OR Source = '' THEN '(blank)'
                  WHEN Source LIKE 'http%' THEN LEFT(SUBSTRING(Source, CHARINDEX('//', Source) + 2, 200), CHARINDEX('/', SUBSTRING(Source, CHARINDEX('//', Source) + 2, 200) + '/') - 1)
                  WHEN Source LIKE '%[_]19[0-9][0-9][_]%' OR Source LIKE '%[_]20[0-9][0-9][_]%' THEN 'newspaper csv' ELSE LEFT(Source, 30) END
INTO #g FROM dbo.HS_Scores WHERE [Date] IS NOT NULL AND RIGHT(RTRIM(Home), 4) IN ('(PA)', '(NJ)', '(TX)')
UNION ALL
SELECT ID, Season, [Date], Visitor, Home, SUBSTRING(RIGHT(RTRIM(Visitor), 4), 2, 2),
       CASE WHEN Source LIKE '%maxpreps%' THEN 'MaxPreps' WHEN Source IS NULL OR Source = '' THEN '(blank)'
            WHEN Source LIKE 'http%' THEN LEFT(SUBSTRING(Source, CHARINDEX('//', Source) + 2, 200), CHARINDEX('/', SUBSTRING(Source, CHARINDEX('//', Source) + 2, 200) + '/') - 1)
            WHEN Source LIKE '%[_]19[0-9][0-9][_]%' OR Source LIKE '%[_]20[0-9][0-9][_]%' THEN 'newspaper csv' ELSE LEFT(Source, 30) END
FROM dbo.HS_Scores WHERE [Date] IS NOT NULL AND RIGHT(RTRIM(Visitor), 4) IN ('(PA)', '(NJ)', '(TX)');
CREATE INDEX ix_g ON #g (Team, Season, [Date]);
IF OBJECT_ID('tempdb..#p') IS NOT NULL DROP TABLE #p;
SELECT a.ST, a.Season, SrcPair = CASE WHEN a.Src <= b.Src THEN a.Src + ' / ' + b.Src ELSE b.Src + ' / ' + a.Src END,
       SameDate = CASE WHEN a.[Date] = b.[Date] THEN 1 ELSE 0 END
INTO #p FROM #g a JOIN #g b ON b.Team = a.Team AND b.Season = a.Season AND a.ID < b.ID AND b.Opp <> a.Opp AND ABS(DATEDIFF(day, a.[Date], b.[Date])) <= 1;
-- 1: by state and source pair
SELECT ST, SrcPair, Pairs = COUNT(*), SameDayPct = 100 * SUM(SameDate) / COUNT(*), FirstSeason = MIN(Season), LastSeason = MAX(Season)
FROM #p GROUP BY ST, SrcPair HAVING COUNT(*) >= 100 ORDER BY ST, COUNT(*) DESC;
-- 2: by state and decade
SELECT ST, Decade = Season / 10 * 10, Pairs = COUNT(*) FROM #p GROUP BY ST, Season / 10 * 10 ORDER BY ST, Decade;
-- 3: games per state (for a rate)
SELECT ST, Games = COUNT(DISTINCT ID) FROM #g GROUP BY ST;

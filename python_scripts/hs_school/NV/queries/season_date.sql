-- Step 3.1 season vs date (Massachusetts). OK: date year = Season; Jan of Season+1; Season 2020 played Jan-Jun 2021 (COVID).
IF OBJECT_ID('tempdb..#sd_g') IS NOT NULL DROP TABLE #sd_g;
SELECT s.ID, s.Season, s.[Date], s.Home, s.Home_Score, s.Visitor, s.Visitor_Score, s.Source, s.Access_ID,
       DateYear = YEAR(s.[Date]), DateMonth = MONTH(s.[Date])
INTO #sd_g
FROM dbo.HS_Scores s
WHERE (RTRIM(s.Home) LIKE '%(NV)' OR RTRIM(s.Visitor) LIKE '%(NV)') AND s.[Date] IS NOT NULL
  AND NOT (YEAR(s.[Date]) = s.Season)
  AND NOT (YEAR(s.[Date]) = s.Season + 1 AND MONTH(s.[Date]) = 1)
  AND NOT (s.Season = 2020 AND YEAR(s.[Date]) = 2021 AND MONTH(s.[Date]) <= 6);
-- 1: summary by kind and source
SELECT Kind = CASE WHEN DateYear = Season + 1 THEN 'date = next year' WHEN DateYear = Season - 1 THEN 'date = previous year'
                   ELSE 'date off by 2+ years' END,
       Src = CASE WHEN Source LIKE '%maxpreps%' THEN 'MaxPreps' WHEN Source LIKE '%classmates%' OR Source LIKE '%e-yearbook%' THEN 'yearbook'
                  WHEN Source = 'Mr. Dan R Ford Sr' THEN 'Ford' WHEN Source IS NULL OR Source = '' THEN '(blank)' ELSE 'newspaper / other' END,
       Games = COUNT(*), FirstSeason = MIN(Season), LastSeason = MAX(Season)
FROM #sd_g GROUP BY CASE WHEN DateYear = Season + 1 THEN 'date = next year' WHEN DateYear = Season - 1 THEN 'date = previous year'
                   ELSE 'date off by 2+ years' END,
         CASE WHEN Source LIKE '%maxpreps%' THEN 'MaxPreps' WHEN Source LIKE '%classmates%' OR Source LIKE '%e-yearbook%' THEN 'yearbook'
              WHEN Source = 'Mr. Dan R Ford Sr' THEN 'Ford' WHEN Source IS NULL OR Source = '' THEN '(blank)' ELSE 'newspaper / other' END
ORDER BY Games DESC;
-- 2: every game
SELECT Season, [Date], Home, Home_Score, Visitor, Visitor_Score, Source, Access_ID, ID FROM #sd_g ORDER BY Season, [Date];

-- Step 3.2 forfeits (Massachusetts). HS rule: Forfeit 0 counts, 1 never counts, NULL counts except after 1949 for 1-0/0-1/2-0/0-2.
IF OBJECT_ID('tempdb..#ff_g') IS NOT NULL DROP TABLE #ff_g;
SELECT s.ID, s.Season, s.[Date], s.Home, s.Home_Score, s.Visitor, s.Visitor_Score, s.Forfeit, s.Source,
       Score = CONCAT(CASE WHEN s.Home_Score >= s.Visitor_Score THEN s.Home_Score ELSE s.Visitor_Score END, '-',
                      CASE WHEN s.Home_Score >= s.Visitor_Score THEN s.Visitor_Score ELSE s.Home_Score END)
INTO #ff_g
FROM dbo.HS_Scores s
WHERE (RTRIM(s.Home) LIKE '%(NY)' OR RTRIM(s.Visitor) LIKE '%(NY)') AND s.Home_Score IS NOT NULL AND s.Visitor_Score IS NOT NULL;
-- 1: forfeit-looking scores and flags by era
SELECT Score, Era = CASE WHEN Season <= 1949 THEN 'to 1949' ELSE 'after 1949' END,
       Flag = ISNULL(CAST(Forfeit AS varchar(5)), 'NULL'), Games = COUNT(*), FirstSeason = MIN(Season), LastSeason = MAX(Season)
FROM #ff_g WHERE Score IN ('1-0', '2-0', '0-0') OR Forfeit = 1
GROUP BY Score, CASE WHEN Season <= 1949 THEN 'to 1949' ELSE 'after 1949' END, ISNULL(CAST(Forfeit AS varchar(5)), 'NULL')
ORDER BY Score, Era, Flag;
-- 2: the 2-0 games after 1949 with no flag (real lone-safety games are dropped by the rule) and every Forfeit=1 game with a normal score
SELECT Season, [Date], Home, Home_Score, Visitor, Visitor_Score, Forfeit, Source, ID
FROM #ff_g
WHERE (Score = '2-0' AND Season > 1949 AND Forfeit IS NULL) OR (Forfeit = 1 AND Score NOT IN ('1-0', '2-0'))
ORDER BY Season, [Date];

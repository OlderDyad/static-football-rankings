-- Sheridan (WY) games vs Montana schools (some are Sheridan (MT)'s - Montana Standard / Missoulian pages)
SELECT s.Season, s.[Date], s.Home, s.Home_Score, s.Visitor, s.Visitor_Score, s.Source,
       Opp = CASE WHEN s.Home = 'Sheridan (WY)' THEN s.Visitor ELSE s.Home END, s.ID,
       OppGamesVsSheridanMT = (SELECT COUNT(*) FROM dbo.HS_Scores t WHERE (t.Home = 'Sheridan (MT)' AND t.Visitor = CASE WHEN s.Home = 'Sheridan (WY)' THEN s.Visitor ELSE s.Home END)
                                                                  OR (t.Visitor = 'Sheridan (MT)' AND t.Home = CASE WHEN s.Home = 'Sheridan (WY)' THEN s.Visitor ELSE s.Home END))
FROM dbo.HS_Scores s
WHERE (s.Home = 'Sheridan (WY)' AND RTRIM(s.Visitor) LIKE '%(MT)') OR (s.Visitor = 'Sheridan (WY)' AND RTRIM(s.Home) LIKE '%(MT)')
ORDER BY s.Season, s.[Date];

-- Longmont (CO) 2003-2010: MaxPreps shows a second (small / 8-man) schedule
-- 1: mapping rows for Longmont names
SELECT u.URL, u.ProperName, u.Team_ID FROM dbo.URL_ProperName_Mapping u
WHERE u.URL LIKE '%/longmont/%' OR u.ProperName LIKE 'Longmont%';

-- 2: Longmont (CO) games 2003-2010
SELECT s.Season, s.[Date], s.Home, s.Home_Score, s.Visitor, s.Visitor_Score, s.Source, s.BatchID, s.Date_Added, s.ID
FROM dbo.HS_Scores s
WHERE (s.Home = 'Longmont (CO)' OR s.Visitor = 'Longmont (CO)') AND s.Season BETWEEN 2003 AND 2010
ORDER BY s.Season, s.[Date];

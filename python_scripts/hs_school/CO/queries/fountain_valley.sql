-- Colorado Springs Fountain Valley (CO) 1965-1990: a second (public-school) schedule mixed in?
-- 1: Fountain Valley games 1965-1990
SELECT s.Season, s.[Date], s.Home, s.Home_Score, s.Visitor, s.Visitor_Score, s.Source,
       Opp = CASE WHEN s.Home = 'Colorado Springs Fountain Valley (CO)' THEN s.Visitor ELSE s.Home END, s.ID
FROM dbo.HS_Scores s
WHERE (s.Home = 'Colorado Springs Fountain Valley (CO)' OR s.Visitor = 'Colorado Springs Fountain Valley (CO)') AND s.Season BETWEEN 1965 AND 1990
ORDER BY s.Season, s.[Date];
-- 2: games per season 1955-1990 for Fountain Valley, Fountain-Fort Carson, Widefield (neighbours)
;WITH g AS (SELECT Team = Home, Season FROM dbo.HS_Scores WHERE Season BETWEEN 1955 AND 1990
            UNION ALL SELECT Visitor, Season FROM dbo.HS_Scores WHERE Season BETWEEN 1955 AND 1990)
SELECT Season,
       FountainValley = SUM(CASE WHEN Team = 'Colorado Springs Fountain Valley (CO)' THEN 1 ELSE 0 END),
       FountainFortCarson = SUM(CASE WHEN Team = 'Fountain-Fort Carson (CO)' THEN 1 ELSE 0 END),
       Widefield = SUM(CASE WHEN Team = 'Colorado Springs Widefield (CO)' THEN 1 ELSE 0 END)
FROM g WHERE Team IN ('Colorado Springs Fountain Valley (CO)', 'Fountain-Fort Carson (CO)', 'Colorado Springs Widefield (CO)')
GROUP BY Season ORDER BY Season;

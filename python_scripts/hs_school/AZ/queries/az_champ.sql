SET NOCOUNT ON;
-- AZ championship-page games whose date year is Season-1: is the same game already in either season?
SELECT c.Season, c.[Date], c.Home, c.Home_Score, c.Visitor, c.Visitor_Score, c.ID,
       o.Season AS O_Season, o.[Date] AS O_Date, o.Source AS O_Source, o.ID AS O_ID
FROM dbo.HS_Scores c
LEFT JOIN dbo.HS_Scores o ON o.ID <> c.ID AND o.Season IN (c.Season, c.Season - 1)
     AND ((o.Home = c.Home AND o.Visitor = c.Visitor AND o.Home_Score = c.Home_Score AND o.Visitor_Score = c.Visitor_Score)
       OR (o.Home = c.Visitor AND o.Visitor = c.Home AND o.Home_Score = c.Visitor_Score AND o.Visitor_Score = c.Home_Score))
WHERE (RIGHT(RTRIM(c.Home), 4) = '(AZ)' OR RIGHT(RTRIM(c.Visitor), 4) = '(AZ)') AND YEAR(c.[Date]) = c.Season - 1
ORDER BY c.Season;

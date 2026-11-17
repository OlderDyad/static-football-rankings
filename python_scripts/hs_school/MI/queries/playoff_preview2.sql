-- Playoff-mode team list, refined (read-only), as if run Sunday 2026-11-15.
-- A: a game in Future_Games from 6 days before to 7 days after the run date (this week's games + next week's posted games)
-- B: the team's most recent game this season was a WIN within 15 days (alive, maybe on a bye or next game not posted yet)
DECLARE @Now date = '2026-11-15', @Season int = 2026;
IF OBJECT_ID('tempdb..#pt') IS NOT NULL DROP TABLE #pt;
CREATE TABLE #pt (Team_ID int, Why varchar(20));
INSERT INTO #pt SELECT DISTINCT m.Team_ID, 'scheduled'
FROM dbo.Future_Games f
CROSS APPLY (VALUES (f.RawHomeTeam), (f.RawAwayTeam)) t(Name)
JOIN dbo.URL_ProperName_Mapping m ON m.ProperName = t.Name
WHERE f.GameDate BETWEEN DATEADD(day, -6, @Now) AND DATEADD(day, 7, @Now);
WITH g AS (
  SELECT Name = s.Home, s.[Date], Won = CASE WHEN s.Home_Score > s.Visitor_Score THEN 1 ELSE 0 END FROM dbo.HS_Scores s WHERE s.Season = @Season AND s.[Date] <= @Now
  UNION ALL SELECT s.Visitor, s.[Date], CASE WHEN s.Visitor_Score > s.Home_Score THEN 1 ELSE 0 END FROM dbo.HS_Scores s WHERE s.Season = @Season AND s.[Date] <= @Now),
last AS (SELECT Name, [Date], Won, rn = ROW_NUMBER() OVER (PARTITION BY Name ORDER BY [Date] DESC) FROM g)
INSERT INTO #pt SELECT DISTINCT m.Team_ID, 'won last game'
FROM last l JOIN dbo.URL_ProperName_Mapping m ON m.ProperName = l.Name
WHERE l.rn = 1 AND l.Won = 1 AND l.[Date] >= DATEADD(day, -15, @Now);
SELECT Why, Teams = COUNT(DISTINCT Team_ID) FROM #pt GROUP BY Why
UNION ALL SELECT 'TOTAL (distinct, valid team)', COUNT(DISTINCT p.Team_ID) FROM #pt p JOIN dbo.HS_Team_Names t ON t.ID = p.Team_ID;
SELECT State = REPLACE(RIGHT(RTRIM(t.Team_Name), 3), ')', ''), Teams = COUNT(DISTINCT p.Team_ID),
       Scheduled = COUNT(DISTINCT CASE WHEN p.Why = 'scheduled' THEN p.Team_ID END)
FROM #pt p JOIN dbo.HS_Team_Names t ON t.ID = p.Team_ID GROUP BY REPLACE(RIGHT(RTRIM(t.Team_Name), 3), ')', '') ORDER BY 2 DESC;

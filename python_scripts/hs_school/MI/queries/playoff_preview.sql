-- Preview of the playoff-mode team list (read-only). Window: games in Future_Games from 8 days ago to 7 days ahead,
-- plus teams that WON a game in the last 21 days (covers bye weeks before the playoffs).
DECLARE @Now date = CAST(GETDATE() AS date);
IF OBJECT_ID('tempdb..#pt') IS NOT NULL DROP TABLE #pt;
CREATE TABLE #pt (Team_ID int, Why varchar(20));
INSERT INTO #pt SELECT DISTINCT m.Team_ID, 'scheduled'
FROM dbo.Future_Games f
CROSS APPLY (VALUES (f.RawHomeTeam), (f.RawAwayTeam)) t(Name)
JOIN dbo.URL_ProperName_Mapping m ON m.ProperName = t.Name
WHERE f.GameDate BETWEEN DATEADD(day, -8, @Now) AND DATEADD(day, 7, @Now);
INSERT INTO #pt SELECT DISTINCT m.Team_ID, 'won recently'
FROM dbo.HS_Scores s
CROSS APPLY (VALUES (CASE WHEN s.Home_Score > s.Visitor_Score THEN s.Home WHEN s.Visitor_Score > s.Home_Score THEN s.Visitor END)) w(Name)
JOIN dbo.URL_ProperName_Mapping m ON m.ProperName = w.Name
WHERE s.[Date] >= DATEADD(day, -21, @Now) AND s.[Date] <= @Now AND w.Name IS NOT NULL;
-- 1: counts
SELECT Why, Teams = COUNT(DISTINCT Team_ID) FROM #pt GROUP BY Why
UNION ALL SELECT 'TOTAL (distinct, valid team)', COUNT(DISTINCT p.Team_ID) FROM #pt p JOIN dbo.HS_Team_Names t ON t.ID = p.Team_ID
UNION ALL SELECT 'all mapped teams (full sweep)', COUNT(DISTINCT m.Team_ID) FROM dbo.URL_ProperName_Mapping m JOIN dbo.HS_Team_Names t ON t.ID = m.Team_ID;
-- 2: Future_Games by date in the window
SELECT GameDate = CAST(f.GameDate AS date), Games = COUNT(*) FROM dbo.Future_Games f
WHERE f.GameDate BETWEEN DATEADD(day, -14, @Now) AND DATEADD(day, 14, @Now) GROUP BY CAST(f.GameDate AS date) ORDER BY 1;
-- 3: by state
SELECT State = RIGHT(RTRIM(t.Team_Name), 3), Teams = COUNT(DISTINCT p.Team_ID),
       Scheduled = COUNT(DISTINCT CASE WHEN p.Why = 'scheduled' THEN p.Team_ID END),
       WonOnly = COUNT(DISTINCT p.Team_ID) - COUNT(DISTINCT CASE WHEN p.Why = 'scheduled' THEN p.Team_ID END)
FROM #pt p JOIN dbo.HS_Team_Names t ON t.ID = p.Team_ID GROUP BY RIGHT(RTRIM(t.Team_Name), 3) ORDER BY 2 DESC;
-- 4: last games scraped by date (HS_Scores, current season)
SELECT [Date], Games = COUNT(*) FROM dbo.HS_Scores WHERE [Date] >= DATEADD(day, -21, @Now) GROUP BY [Date] ORDER BY [Date];

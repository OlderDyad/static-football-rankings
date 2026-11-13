SELECT s.ID, s.Season, Date = CONVERT(char(10), s.[Date], 120), s.Home, Home_ID = h.ID, s.Home_Score, s.Visitor, Visitor_ID = v.ID, s.Visitor_Score, s.Margin, s.Neutral, s.Location, s.Location2, s.Source, s.Date_Added, s.OT, s.Forfeit
FROM dbo.HS_Scores s
OUTER APPLY (SELECT TOP 1 ID FROM dbo.HS_Team_Names t WHERE t.Team_Name = s.Home) h
OUTER APPLY (SELECT TOP 1 ID FROM dbo.HS_Team_Names t WHERE t.Team_Name = s.Visitor) v
WHERE RTRIM(s.Home) LIKE '%(SC)' OR RTRIM(s.Visitor) LIKE '%(SC)'
ORDER BY s.Season, s.[Date], s.Home;
SELECT ID, Team_Name, City, State, Mascot, PrimaryColor, SecondaryColor, TertiaryColor, Stadium, YearFounded, Website, LogoURL, School_Logo_URL, PhotoUrl, Latitude, Longitude, Has_Team_Page, Team_Page_URL, LastUpdated
FROM dbo.HS_Team_Names t WHERE t.Team_Name LIKE '%(SC)' ORDER BY Team_Name;

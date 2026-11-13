SELECT Team_Name, Latitude, Longitude FROM dbo.HS_Team_Names WHERE Longitude IS NOT NULL;
SELECT s.ID, s.Season, s.Home, s.Visitor, Src = LEFT(s.Source, 40) FROM dbo.HS_Scores s WHERE RTRIM(s.Home) LIKE '%(VT)' OR RTRIM(s.Visitor) LIKE '%(VT)';

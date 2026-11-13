SELECT t.Team_Name, t.Longitude, Games = (SELECT COUNT(*) FROM dbo.HS_Scores s WHERE s.Home = t.Team_Name OR s.Visitor = t.Team_Name)
FROM dbo.HS_Team_Names t WHERE t.Team_Name LIKE '%Hall (KY)' OR t.Team_Name LIKE '%Hall%(KY)' OR t.Team_Name LIKE 'Grays Knob%';

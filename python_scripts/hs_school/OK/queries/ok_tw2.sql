SELECT t.Team_Name, Games = (SELECT COUNT(*) FROM dbo.HS_Scores s WHERE s.Home = t.Team_Name OR s.Visitor = t.Team_Name) FROM dbo.HS_Team_Names t
WHERE t.Team_Name LIKE '%Kiowa%' OR t.Team_Name LIKE '%Eldorado%' OR t.Team_Name LIKE 'Ada %' OR t.Team_Name LIKE '%Marshall (OK)' OR t.Team_Name LIKE 'El Dorado%' ORDER BY 1;

SELECT t.Team_Name, Games = (SELECT COUNT(*) FROM dbo.HS_Scores s WHERE s.Home = t.Team_Name OR s.Visitor = t.Team_Name)
FROM dbo.HS_Team_Names t WHERE t.Team_Name LIKE '%(NC)' AND (t.Team_Name LIKE '%Roberson%' OR t.Team_Name LIKE 'Hickory Christian%' OR t.Team_Name LIKE '%A.L. Brown%' OR t.Team_Name LIKE '%Thomas Jefferson%'
 OR t.Team_Name LIKE '%Lake Norman Charter%' OR t.Team_Name LIKE '%Pine Lake%' OR t.Team_Name LIKE '%Webb%' OR t.Team_Name LIKE 'Rutherfordton%' OR t.Team_Name LIKE '%Bear Grass%' OR t.Team_Name LIKE '%Laney%'
 OR t.Team_Name LIKE 'Wilson%Hunt%' OR t.Team_Name LIKE '%Reynolds%' OR t.Team_Name LIKE 'Winston-Salem Prep%' OR t.Team_Name LIKE '%Tabor%' OR t.Team_Name LIKE 'Winston Salem%')
ORDER BY 1;

SELECT t.Team_Name, Games = (SELECT COUNT(*) FROM dbo.HS_Scores s WHERE s.Home = t.Team_Name OR s.Visitor = t.Team_Name),
 MinS = (SELECT MIN(Season) FROM dbo.HS_Scores s WHERE s.Home = t.Team_Name OR s.Visitor = t.Team_Name),
 MaxS = (SELECT MAX(Season) FROM dbo.HS_Scores s WHERE s.Home = t.Team_Name OR s.Visitor = t.Team_Name)
FROM dbo.HS_Team_Names t
WHERE t.Team_Name LIKE 'Bell Buckle%(TN)' OR t.Team_Name LIKE 'Memphis B%Washington%(TN)' OR t.Team_Name LIKE 'Memphis Washington%(TN)' OR t.Team_Name LIKE 'Memphis Booker%'
 OR t.Team_Name LIKE 'Memphis Freedom%' OR t.Team_Name LIKE 'Morristown%West%' OR t.Team_Name LIKE 'White House Christian%' OR t.Team_Name LIKE 'Memphis Academy of%' OR t.Team_Name LIKE '%Science and Engineering%(TN)'
ORDER BY 1;
SELECT u.URL, u.ProperName FROM dbo.URL_ProperName_Mapping u WHERE u.URL LIKE '%maxpreps.com/tn/memphis/%washington%' OR u.URL LIKE '%maxpreps.com/tn/memphis/%health%' OR u.URL LIKE '%maxpreps.com/tn/memphis/%science%';

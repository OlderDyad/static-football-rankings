-- NE: mapping rows whose ProperName is missing, and the drift names (2024+ MaxPreps names)
SELECT u.URL, u.ProperName, u.Team_ID FROM dbo.URL_ProperName_Mapping u
WHERE u.URL LIKE '%maxpreps.com/ne/%' AND (u.URL LIKE '%north-star%' OR u.URL LIKE '%standing-bear%' OR u.URL LIKE '%elkhorn%' OR u.URL LIKE '%north-bend%'
   OR u.URL LIKE '%west-point%' OR u.URL LIKE '%humphrey%' OR u.URL LIKE '%lindsay%' OR u.URL LIKE '%scotus%' OR u.URL LIKE '%pope%' OR u.URL LIKE '%mount-michael%'
   OR u.URL LIKE '%humboldt%' OR u.URL LIKE '%papillion%' OR u.URL LIKE '%la-vista%' OR u.URL LIKE '%westview%' OR u.URL LIKE '%buena-vista%' OR u.URL LIKE '%christian%')
ORDER BY u.URL;
;WITH n AS (SELECT Name = Home, Season FROM dbo.HS_Scores WHERE RTRIM(Home) LIKE '%(NE)' UNION ALL SELECT Visitor, Season FROM dbo.HS_Scores WHERE RTRIM(Visitor) LIKE '%(NE)')
SELECT Name, Games = COUNT(*), F = MIN(Season), L = MAX(Season) FROM n
WHERE Name LIKE '%Scotus%' OR Name LIKE '%Pope%' OR Name LIKE '%Mount Michael%' OR Name LIKE 'Humboldt%' OR Name LIKE 'Papillion%' OR Name LIKE '%Elkhorn%'
   OR Name LIKE 'Lincoln North Star%' OR Name LIKE '%Standing Bear%' OR Name LIKE 'North Bend%' OR Name LIKE 'West Point%' OR Name LIKE 'Humphrey%' OR Name LIKE '%Lindsay%'
GROUP BY Name ORDER BY Name;

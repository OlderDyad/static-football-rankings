SELECT ID, Team_Name FROM dbo.HS_Team_Names WHERE Team_Name LIKE 'Whitman%(MA)';
SELECT Name = CASE WHEN Home LIKE 'Whitman%' THEN Home ELSE Visitor END, Era = CASE WHEN Season < 1960 THEN 'pre-1960' ELSE '1960+' END, Games = COUNT(*), MinS = MIN(Season), MaxS = MAX(Season)
FROM dbo.HS_Scores WHERE Home LIKE 'Whitman%(MA)' OR Visitor LIKE 'Whitman%(MA)'
GROUP BY CASE WHEN Home LIKE 'Whitman%' THEN Home ELSE Visitor END, CASE WHEN Season < 1960 THEN 'pre-1960' ELSE '1960+' END ORDER BY 1,2;

SELECT t.Team_Name, Games = (SELECT COUNT(*) FROM dbo.HS_Scores s WHERE s.Home = t.Team_Name OR s.Visitor = t.Team_Name) FROM dbo.HS_Team_Names t
WHERE t.Team_Name IN ('South Coffeyville (OK)','Coffeyville South (OK)','Lenapah Oklahoma Union (OK)','South Coffeyville Oklahoma Union (OK)','Oklahoma Union (OK)');
SELECT URL, ProperName FROM dbo.URL_ProperName_Mapping WHERE URL LIKE '%maxpreps.com/ok/%coffeyville%' OR URL LIKE '%maxpreps.com/ok/lenapah%' OR URL LIKE '%oklahoma-union%';

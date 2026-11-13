SELECT State, Steps = COUNT(*), Done = SUM(CASE WHEN Status IN ('done','complete') THEN 1 ELSE 0 END), LastUpdated = MAX(Updated)
FROM dbo.HS_Cleanup_Status GROUP BY State ORDER BY State;
SELECT St = RIGHT(RTRIM(Home), 4), Games = COUNT(*) FROM dbo.HS_Scores WHERE RTRIM(Home) LIKE '%([A-Z][A-Z])' GROUP BY RIGHT(RTRIM(Home), 4) HAVING COUNT(*) >= 500 ORDER BY Games DESC;

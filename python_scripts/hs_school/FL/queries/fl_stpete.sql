SELECT N = Home, L = LEN(Home), DL = DATALENGTH(Home), Games = COUNT(*), MinS = MIN(Season), MaxS = MAX(Season), Src = MAX(Source) FROM dbo.HS_Scores WHERE Home LIKE 'Saint Petersburg%' OR Home LIKE 'St. Petersburg%' GROUP BY Home ORDER BY Home;
SELECT * FROM dbo.HS_Consolidation_Log WHERE OldName LIKE 'Saint Petersburg%' ORDER BY LogID DESC;

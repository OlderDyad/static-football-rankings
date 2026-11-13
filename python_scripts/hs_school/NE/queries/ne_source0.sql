-- rows whose Source is '0' (an import with no source text): where, when, which batch
SELECT St = SUBSTRING(RTRIM(Home), LEN(RTRIM(Home)) - 2, 2), Games = COUNT(*), FirstSeason = MIN(Season), LastSeason = MAX(Season),
       Batches = COUNT(DISTINCT BatchID), FirstAdded = MIN(Date_Added), LastAdded = MAX(Date_Added), WithAccessID = SUM(CASE WHEN Access_ID IS NULL THEN 0 ELSE 1 END)
FROM dbo.HS_Scores WHERE Source = '0' AND RTRIM(Home) LIKE '%([A-Z][A-Z])'
GROUP BY SUBSTRING(RTRIM(Home), LEN(RTRIM(Home)) - 2, 2) ORDER BY COUNT(*) DESC;
-- NE Source='0' rows by season and date added
SELECT Season, Games = COUNT(*), Added = CONVERT(varchar(10), MIN(Date_Added), 120), AddedLast = CONVERT(varchar(10), MAX(Date_Added), 120), Batch = MIN(BatchID)
FROM dbo.HS_Scores WHERE Source = '0' AND (RTRIM(Home) LIKE '%(NE)' OR RTRIM(Visitor) LIKE '%(NE)') GROUP BY Season ORDER BY Season;

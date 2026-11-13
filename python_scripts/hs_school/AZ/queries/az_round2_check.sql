SET NOCOUNT ON;
SELECT Name = CASE WHEN s.Home IN ('Fountain Hills Catalina (AZ)','Tucson (AZ)','Phoenix (AZ)','Mesa Prep (AZ)','Mayer (AZ)') THEN s.Home ELSE s.Visitor END,
       s.Season, s.[Date], Opp = CASE WHEN s.Home IN ('Fountain Hills Catalina (AZ)','Tucson (AZ)','Phoenix (AZ)','Mesa Prep (AZ)','Mayer (AZ)') THEN s.Visitor ELSE s.Home END, s.Source
FROM dbo.HS_Scores s WHERE s.Home IN ('Fountain Hills Catalina (AZ)','Tucson (AZ)','Phoenix (AZ)','Mesa Prep (AZ)','Mayer (AZ)') OR s.Visitor IN ('Fountain Hills Catalina (AZ)','Tucson (AZ)','Phoenix (AZ)','Mesa Prep (AZ)','Mayer (AZ)')
ORDER BY 1, 2, 3;
SELECT URL, ProperName FROM dbo.URL_ProperName_Mapping WHERE ProperName IN ('Tucson (AZ)','Fountain Hills Catalina (AZ)','Mesa Prep (AZ)') OR URL LIKE '%/az/fountain-hills/%';
SELECT Self = COUNT(*) FROM dbo.HS_Scores WHERE Home = Visitor AND RIGHT(RTRIM(Home), 4) = '(AZ)';

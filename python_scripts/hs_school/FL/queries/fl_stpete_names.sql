SET NOCOUNT ON;
SELECT t.ID, t.Team_Name, t.City, t.Mascot, t.LogoURL, t.Latitude,
       SaintName = REPLACE(t.Team_Name, 'St. Petersburg', 'Saint Petersburg'),
       SaintExists = CASE WHEN EXISTS (SELECT 1 FROM dbo.HS_Team_Names x WHERE x.Team_Name = REPLACE(t.Team_Name, 'St. Petersburg', 'Saint Petersburg')) THEN 1 ELSE 0 END,
       Games = (SELECT COUNT(*) FROM dbo.HS_Scores s WHERE s.Home = t.Team_Name OR s.Visitor = t.Team_Name),
       URLs = (SELECT COUNT(*) FROM dbo.URL_ProperName_Mapping u WHERE u.ProperName = t.Team_Name)
FROM dbo.HS_Team_Names t WHERE t.Team_Name LIKE 'St. Petersburg%(FL)' ORDER BY t.Team_Name;
SELECT t.ID, t.Team_Name, t.City FROM dbo.HS_Team_Names t WHERE t.Team_Name LIKE 'Saint Petersburg%(FL)';
SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMNPROPERTY(OBJECT_ID('dbo.HS_Team_Names'), COLUMN_NAME, 'IsIdentity') AS IsIdentity
FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'HS_Team_Names' ORDER BY ORDINAL_POSITION;
SELECT name FROM sys.triggers WHERE parent_id = OBJECT_ID('dbo.HS_Team_Names');
SELECT c.* FROM dbo.College_Team_Names c WHERE c.HS_Team_Name LIKE 'St. Petersburg%' OR c.HS_Team_Name LIKE 'Saint Petersburg%';
SELECT TOP 5 * FROM dbo.HS_Rankings WHERE Home LIKE 'St. Petersburg Lakewood%' ORDER BY Season DESC;

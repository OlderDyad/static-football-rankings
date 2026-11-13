SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'HS_Team_Names' ORDER BY ORDINAL_POSITION;
SELECT TOP 5 * FROM dbo.HS_Team_Names WHERE Team_Name IN ('North Platte St. Patrick''s (NE)', 'O''Neill Saint Mary''s (NE)', 'Bassett Rock County (NE)', 'Hershey (NE)');

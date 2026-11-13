SELECT c.name FROM sys.columns c WHERE c.object_id = OBJECT_ID('dbo.HS_Team_Names');
SELECT TOP 5 * FROM dbo.HS_Team_Names WHERE Team_Name IN ('Knoxville Halls (TN)','Halls (TN)','Covington (TN)','Brownsville Haywood (TN)');

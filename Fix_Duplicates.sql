USE [hs_football_database]
GO

SET NOCOUNT ON;

PRINT '=======================================================';
PRINT 'FIX: PURGING STAGING TABLES (143/153)';
PRINT '=======================================================';
PRINT 'The slowness was caused by massive Data Duplication in these tables.';
PRINT 'We are wiping them clean to start fresh.';

TRUNCATE TABLE [dbo].[143_Quality_Scores_Union_Query_DB];
TRUNCATE TABLE [dbo].[153_Quality_Scores_Union_Query_DB];

PRINT 'Tables Truncated.';
PRINT '=======================================================';

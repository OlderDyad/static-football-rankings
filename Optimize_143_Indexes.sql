USE [hs_football_database]
GO

SET NOCOUNT ON;

PRINT '=======================================================';
PRINT 'OPTIMIZATION: UPGRADING INDEXES TO CLUSTERED';
PRINT '=======================================================';
PRINT 'Goal: Eliminate "Key Lookups" by moving data to the index leaf.';

-- 1. DROP EXISTING INDEXES (To make way for Clustered)
PRINT '1. Dropping existing indexes on 143/153...';

IF EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_143_SeasonHome' AND object_id = OBJECT_ID('dbo.[143_Quality_Scores_Union_Query_DB]'))
    DROP INDEX [IX_143_SeasonHome] ON [dbo].[143_Quality_Scores_Union_Query_DB];

IF EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_153_SeasonHome' AND object_id = OBJECT_ID('dbo.[153_Quality_Scores_Union_Query_DB]'))
    DROP INDEX [IX_153_SeasonHome] ON [dbo].[153_Quality_Scores_Union_Query_DB];

-- Check for any other indexes on SeasonHome just in case
IF EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_143_Quality_Scores_Season_Week_SeasonHome' AND object_id = OBJECT_ID('dbo.[143_Quality_Scores_Union_Query_DB]'))
    DROP INDEX [IX_143_Quality_Scores_Season_Week_SeasonHome] ON [dbo].[143_Quality_Scores_Union_Query_DB];

-- 2. CREATE CLUSTERED INDEXES
-- A Clustered Index sorts the actual table data by the key.
-- This means looking up "SeasonHome" gives us ALL columns immediately.
-- No more jumping around memory to find "Offense" or "Defense".

PRINT '2. Creating CLUSTERED Index on 143 (Input Table)...';
-- Note: SeasonHome is NVARCHAR(255). 
CREATE CLUSTERED INDEX [CX_143_SeasonHome] ON [dbo].[143_Quality_Scores_Union_Query_DB]
(
    [SeasonHome] ASC
);

PRINT '3. Creating CLUSTERED Index on 153 (Output Table)...';
CREATE CLUSTERED INDEX [CX_153_SeasonHome] ON [dbo].[153_Quality_Scores_Union_Query_DB]
(
    [SeasonHome] ASC
);

PRINT '=======================================================';
PRINT 'OPTIMIZATION COMPLETE.';
PRINT 'Queries using SeasonHome will now be instant.';
PRINT '=======================================================';

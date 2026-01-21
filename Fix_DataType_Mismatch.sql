USE [hs_football_database]
GO

SET NOCOUNT ON;

PRINT '==============================================================================';
PRINT 'FIX: UNIFORMIZING DATA TYPES TO NVARCHAR(255)';
PRINT '==============================================================================';

-- 1. DROP EXISTING INDEXES (Cannot alter columns with indexes on them)
PRINT '1. Dropping Indexes...';
IF EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_ScoresWinLoss_SeasonHome' AND object_id = OBJECT_ID('dbo.ScoresWinLossResults'))
    DROP INDEX [IX_ScoresWinLoss_SeasonHome] ON [dbo].[ScoresWinLossResults];

IF EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_ScoresWinLoss_SeasonVisitor' AND object_id = OBJECT_ID('dbo.ScoresWinLossResults'))
    DROP INDEX [IX_ScoresWinLoss_SeasonVisitor] ON [dbo].[ScoresWinLossResults];

IF EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_143_SeasonHome' AND object_id = OBJECT_ID('dbo.[143_Quality_Scores_Union_Query_DB]'))
    DROP INDEX [IX_143_SeasonHome] ON [dbo].[143_Quality_Scores_Union_Query_DB];

IF EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_153_SeasonHome' AND object_id = OBJECT_ID('dbo.[153_Quality_Scores_Union_Query_DB]'))
    DROP INDEX [IX_153_SeasonHome] ON [dbo].[153_Quality_Scores_Union_Query_DB];

-- 2. ALTER COLUMNS TO NVARCHAR(255) Match (Likely causing the mismatch)
PRINT '2. Altering Columns to NVARCHAR(255)...';

-- ScoresWinLossResults
ALTER TABLE [dbo].[ScoresWinLossResults] ALTER COLUMN [SeasonHome] NVARCHAR(255);
ALTER TABLE [dbo].[ScoresWinLossResults] ALTER COLUMN [SeasonVisitor] NVARCHAR(255);

-- 143 Table
ALTER TABLE [dbo].[143_Quality_Scores_Union_Query_DB] ALTER COLUMN [SeasonHome] NVARCHAR(255);

-- 153 Table
ALTER TABLE [dbo].[153_Quality_Scores_Union_Query_DB] ALTER COLUMN [SeasonHome] NVARCHAR(255);

PRINT '  -> Columns updated.';

-- 3. RECREATE INDEXES (Now on consistent types)
PRINT '3. Recreating Indexes...';

CREATE NONCLUSTERED INDEX [IX_ScoresWinLoss_SeasonHome] ON [dbo].[ScoresWinLossResults]
([SeasonHome] ASC)
INCLUDE ([Adjusted_Margin], [Adjusted_Margin_Win_Loss], [Adj_Log_Margin], [Visitor_Score], [Home_Score]);

CREATE NONCLUSTERED INDEX [IX_ScoresWinLoss_SeasonVisitor] ON [dbo].[ScoresWinLossResults]
([SeasonVisitor] ASC);

CREATE NONCLUSTERED INDEX [IX_143_SeasonHome] ON [dbo].[143_Quality_Scores_Union_Query_DB]
([SeasonHome] ASC)
INCLUDE ([Avg_Of_Avg_Of_Home_Modified_Score], [Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss]);

CREATE NONCLUSTERED INDEX [IX_153_SeasonHome] ON [dbo].[153_Quality_Scores_Union_Query_DB]
([SeasonHome] ASC);

PRINT '==============================================================================';
PRINT 'FIX COMPLETE. You can now re-run CalculateRankings_v5.';
PRINT '==============================================================================';

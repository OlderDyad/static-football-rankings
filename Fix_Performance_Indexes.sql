USE [hs_football_database]
GO

SET NOCOUNT ON;

PRINT 'Starting Performance Optimization...';

-- =============================================================================
-- 1. ADD MISSING INDEXES
--    The crash suggests a massive table scan during the loop joins.
--    We need indexes on the keys used in Loop_Query_Step_6v2.
-- =============================================================================

PRINT 'Creating Indexes on ScoresWinLossResults...';
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_ScoresWinLoss_SeasonHome' AND object_id = OBJECT_ID('dbo.ScoresWinLossResults'))
BEGIN
    CREATE NONCLUSTERED INDEX [IX_ScoresWinLoss_SeasonHome] ON [dbo].[ScoresWinLossResults]
    ([SeasonHome] ASC)
    INCLUDE ([Adjusted_Margin], [Adjusted_Margin_Win_Loss], [Adj_Log_Margin], [Visitor_Score], [Home_Score]);
    PRINT '  -> Created index on SeasonHome';
END

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_ScoresWinLoss_SeasonVisitor' AND object_id = OBJECT_ID('dbo.ScoresWinLossResults'))
BEGIN
    CREATE NONCLUSTERED INDEX [IX_ScoresWinLoss_SeasonVisitor] ON [dbo].[ScoresWinLossResults]
    ([SeasonVisitor] ASC);
    PRINT '  -> Created index on SeasonVisitor';
END

-- Indexes for the 143 Iteration Table
PRINT 'Creating Indexes on 143_Quality_Scores_Union_Query_DB...';
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_143_SeasonHome' AND object_id = OBJECT_ID('dbo.[143_Quality_Scores_Union_Query_DB]'))
BEGIN
    CREATE NONCLUSTERED INDEX [IX_143_SeasonHome] ON [dbo].[143_Quality_Scores_Union_Query_DB]
    ([SeasonHome] ASC)
    INCLUDE ([Avg_Of_Avg_Of_Home_Modified_Score], [Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss]);
    PRINT '  -> Created index on SeasonHome';
END

-- Indexes for the 153 Iteration Table (Target)
PRINT 'Creating Indexes on 153_Quality_Scores_Union_Query_DB...';
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_153_SeasonHome' AND object_id = OBJECT_ID('dbo.[153_Quality_Scores_Union_Query_DB]'))
BEGIN
    CREATE NONCLUSTERED INDEX [IX_153_SeasonHome] ON [dbo].[153_Quality_Scores_Union_Query_DB]
    ([SeasonHome] ASC);
    PRINT '  -> Created index on SeasonHome';
END

PRINT 'Index creation complete.';

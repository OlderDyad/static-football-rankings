USE [hs_football_database]
GO

SET NOCOUNT ON;

PRINT '==============================================================================';
PRINT 'LIVE DIAGNOSTIC: WHY IS THE LOOP SLOW?';
PRINT '==============================================================================';

-- 1. ROW COUNTS (Is data moving?)
PRINT '';
PRINT '1. Row Counts (Volume Analysis)';
SELECT 'ScoresWinLossResults (Game Data)' AS TableName, COUNT(*) AS Row_Count FROM dbo.ScoresWinLossResults WITH (NOLOCK)
UNION ALL
SELECT '143_Quality_Scores_Union_Query_DB (Team Ratings)', COUNT(*) FROM dbo.[143_Quality_Scores_Union_Query_DB] WITH (NOLOCK)
UNION ALL
SELECT '153_Quality_Scores_Union_Query_DB (Target)', COUNT(*) FROM dbo.[153_Quality_Scores_Union_Query_DB] WITH (NOLOCK);

-- 2. COLUMN TYPES (Verify the Fix)
PRINT '';
PRINT '2. Column Data Types (SeasonHome) - SHOULD BE NVARCHAR(255)';
SELECT 
    t.name AS TableName,
    c.name AS ColumnName,
    ty.name AS DataType,
    c.max_length AS MaxLen,
    c.collation_name
FROM sys.columns c
JOIN sys.types ty ON c.user_type_id = ty.user_type_id
JOIN sys.tables t ON c.object_id = t.object_id
WHERE t.name IN ('ScoresWinLossResults', '143_Quality_Scores_Union_Query_DB')
  AND c.name = 'SeasonHome'
ORDER BY t.name;

-- 3. INDEXES (Verify they are ACTIVE)
PRINT '';
PRINT '3. Active Indexes on SeasonHome';
SELECT 
    t.name AS TableName,
    i.name AS IndexName,
    i.type_desc AS IndexType,
    CASE WHEN i.is_disabled = 1 THEN 'DISABLED' ELSE 'ACTIVE' END AS Status
FROM sys.indexes i
JOIN sys.tables t ON i.object_id = t.object_id
JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
WHERE t.name IN ('ScoresWinLossResults', '143_Quality_Scores_Union_Query_DB')
  AND c.name IN ('SeasonHome', 'SeasonVisitor')
ORDER BY t.name;

PRINT '';
PRINT 'Diagnostic Complete.';

USE [hs_football_database]
GO

SET NOCOUNT ON;

PRINT '=======================================================';
PRINT 'PERFORMANCE DIAGNOSTIC: Indices and Types';
PRINT '=======================================================';

-- 1. Check Data Types of Join Columns
PRINT '';
PRINT '1. Column Data Types (SeasonHome):';
SELECT 
    t.name AS TableName,
    c.name AS ColumnName,
    ty.name AS DataType,
    c.max_length,
    c.collation_name
FROM sys.columns c
JOIN sys.types ty ON c.user_type_id = ty.user_type_id
JOIN sys.tables t ON c.object_id = t.object_id
WHERE t.name IN ('ScoresWinLossResults', '143_Quality_Scores_Union_Query_DB', '153_Quality_Scores_Union_Query_DB')
  AND c.name IN ('SeasonHome', 'SeasonVisitor', 'Home', 'Visitor', 'Season', 'Week')
ORDER BY t.name, c.name;

-- 2. Check Existing Indices
PRINT '';
PRINT '2. Existing Indices:';
SELECT 
    t.name AS TableName,
    i.name AS IndexName,
    i.type_desc,
    STUFF((SELECT ', ' + c.name
           FROM sys.index_columns ic
           JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
           WHERE ic.object_id = t.object_id AND ic.index_id = i.index_id
           ORDER BY ic.key_ordinal
           FOR XML PATH('')), 1, 2, '') AS Columns
FROM sys.indexes i
JOIN sys.tables t ON i.object_id = t.object_id
WHERE t.name IN ('ScoresWinLossResults', '143_Quality_Scores_Union_Query_DB', '153_Quality_Scores_Union_Query_DB')
ORDER BY t.name, i.name;

PRINT '';
PRINT 'End of Diagnostic.';

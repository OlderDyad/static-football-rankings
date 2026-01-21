USE [hs_football_database]
GO

SET NOCOUNT ON;

PRINT '=======================================================';
PRINT 'AUDIT REPORT: Win-Loss Rating Logic';
PRINT '=======================================================';

-- 1. Check Coefficients
PRINT '';
PRINT '1. HFA Coefficients:';
SELECT Home_Field_Adv_Margin AS [HFA Margin], Home_Field_Adv_Win_Loss AS [HFA WinLoss]
FROM dbo.Coefficients;

-- 2. Check Loop_Query_Step_0 Computed Columns
PRINT '';
PRINT '2. Loop_Query_Step_0 Computed Column Definitions:';
SELECT 
    name AS ColumnName, 
    definition AS Formula
FROM sys.computed_columns
WHERE object_id = OBJECT_ID('dbo.Loop_Query_Step_0')
ORDER BY name;

-- 3. Check Pre-Seeding Logic (Simulate logic from Prelim)
PRINT '';
PRINT '3. Sample Pre-Seeding Data (Top 5 from 143 table if exists):';
IF OBJECT_ID('dbo.[143_Quality_Scores_Union_Query_DB]', 'U') IS NOT NULL
BEGIN
    SELECT TOP 5 
        Season, 
        Home, 
        Avg_Of_Avg_Of_Home_Modified_Score AS [MarginRating],
        Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss AS [WinLossRating],
        Avg_Of_Avg_Of_Home_Modified_Log_Score AS [LogRating]
    FROM dbo.[143_Quality_Scores_Union_Query_DB]
    ORDER BY Avg_Of_Avg_Of_Home_Modified_Score DESC;
END
ELSE
BEGIN
    PRINT 'Table [143_Quality_Scores_Union_Query_DB] does not exist.';
END

-- 4. Check Loop_Query_Step_6 Columns (Target for iteration)
PRINT '';
PRINT '4. Loop_Query_Step_6 Column Types:';
SELECT 
    c.name, 
    t.name AS type_name, 
    c.precision, 
    c.scale
FROM sys.columns c
JOIN sys.types t ON c.user_type_id = t.user_type_id
WHERE c.object_id = OBJECT_ID('dbo.Loop_Query_Step_6');

PRINT '';
PRINT 'End of Audit.';

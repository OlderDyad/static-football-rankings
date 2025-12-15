-- ============================================================================
-- LoneStar Football Data - SQL Bulk Import Script
-- ============================================================================
-- This script imports cleaned LoneStar data from Excel into HS_Scores table
-- 
-- PREREQUISITES:
-- 1. Excel file exported as CSV (UTF-8 encoding)
-- 2. All team names already standardized via VLOOKUP
-- 3. Neutral site flags set (TRUE/FALSE)
-- 4. Source field populated with team URL
--
-- ID GENERATION:
-- - The HS_Scores.ID column is a UNIQUEIDENTIFIER (GUID)
-- - SQL automatically generates unique IDs using NEWID() function
-- - DO NOT include ID column in your Excel export
-- - Each game gets a unique GUID like: 'A1B2C3D4-E5F6-7890-ABCD-EF1234567890'
-- - This matches the MaxPreps workflow (see FinalizeMaxPrepsData procedure)
-- ============================================================================

-- Step 1: Create staging table (matches HS_Scores structure exactly)
-- Run this ONCE to set up the staging table
IF OBJECT_ID('dbo.HS_Scores_LoneStar_Staging', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.HS_Scores_LoneStar_Staging (
        -- Core game data (matches HS_Scores structure EXACTLY)
        [Date] DATE NULL,
        Season INT NULL,
        Home VARCHAR(111) NULL,                      -- varchar(111) NOT nvarchar
        Visitor VARCHAR(111) NULL,                   -- varchar(111) NOT nvarchar
        Neutral BIT NULL,
        Location VARCHAR(111) NULL,                  -- varchar(111) NOT nvarchar
        Location2 VARCHAR(255) NULL,                 -- varchar(255) NOT nvarchar
        Line INT NULL,                               -- int NOT float
        Future_Game BIT NULL,
        Source VARCHAR(255) NULL,                    -- varchar(255) NOT nvarchar
        OT INT NULL,                                 -- int NOT bit
        Forfeit BIT NULL,
        Visitor_Score INT NULL,
        Home_Score INT NULL,
        Margin INT NULL,
        Access_ID VARCHAR(255) NULL,                 -- varchar(255) - exists in HS_Scores
        -- Import tracking fields (for staging only)
        BatchID INT NULL,                            -- This exists in HS_Scores!
        Import_Date DATETIME DEFAULT GETDATE(),
        Status NVARCHAR(50) DEFAULT 'Pending'        -- Pending, Validated, Imported, Error
    );
    
    PRINT '✓ Staging table created successfully';
END
ELSE
BEGIN
    PRINT '✓ Staging table already exists';
END
GO

-- ============================================================================
-- Step 2: Bulk insert from Excel CSV
-- ============================================================================
-- IMPORTANT: Update the file path to match your actual CSV location
-- Save your Excel file as CSV (UTF-8) before running this

DECLARE @CSVPath NVARCHAR(500) = 'C:\Users\demck\OneDrive\Football_2024\static-football-rankings\excel_files\lonestar_batch_20241212.csv';
DECLARE @BatchID INT;

-- Get next batch ID
SELECT @BatchID = ISNULL(MAX(BatchID), 0) + 1 FROM dbo.HS_Scores_LoneStar_Staging;

PRINT 'Importing batch ' + CAST(@BatchID AS NVARCHAR(10)) + ' from: ' + @CSVPath;

-- Bulk insert
BEGIN TRY
    BULK INSERT dbo.HS_Scores_LoneStar_Staging
    FROM @CSVPath
    WITH (
        FIRSTROW = 2,                   -- Skip header row
        FIELDTERMINATOR = ',',          -- CSV comma-separated
        ROWTERMINATOR = '\n',           -- Newline
        CODEPAGE = '65001',             -- UTF-8 encoding
        TABLOCK,
        KEEPNULLS                       -- Preserve NULL values in empty columns
    );
    
    PRINT '✓ CSV imported successfully';
END TRY
BEGIN CATCH
    PRINT '✗ Error importing CSV:';
    PRINT ERROR_MESSAGE();
    RETURN;
END CATCH

-- Tag new records with batch ID
UPDATE dbo.HS_Scores_LoneStar_Staging
SET BatchID = @BatchID,
    Status = 'Pending'
WHERE BatchID IS NULL;

PRINT '✓ Tagged ' + CAST(@@ROWCOUNT AS NVARCHAR(10)) + ' records with Batch ID ' + CAST(@BatchID AS NVARCHAR(10));

-- ============================================================================
-- Step 3: Validate imported data
-- ============================================================================

PRINT '';
PRINT '=== BATCH VALIDATION REPORT ===';
PRINT '';

-- Summary stats
SELECT 
    'Total Games' as Metric,
    COUNT(*) as Count
FROM dbo.HS_Scores_LoneStar_Staging
WHERE BatchID = @BatchID

UNION ALL

SELECT 'Seasons Covered', 
    CAST(MIN(Season) AS NVARCHAR) + ' - ' + CAST(MAX(Season) AS NVARCHAR)
FROM dbo.HS_Scores_LoneStar_Staging
WHERE BatchID = @BatchID

UNION ALL

SELECT 'Unique Teams', 
    CAST(COUNT(DISTINCT Home) + COUNT(DISTINCT Visitor) AS NVARCHAR)
FROM dbo.HS_Scores_LoneStar_Staging
WHERE BatchID = @BatchID

UNION ALL

SELECT 'Neutral Site Games',
    CAST(COUNT(*) AS NVARCHAR)
FROM dbo.HS_Scores_LoneStar_Staging
WHERE BatchID = @BatchID AND Neutral = 1

UNION ALL

SELECT 'Forfeit Games',
    CAST(COUNT(*) AS NVARCHAR)
FROM dbo.HS_Scores_LoneStar_Staging
WHERE BatchID = @BatchID AND Forfeit = 1;

PRINT '';
PRINT '--- Data Quality Checks ---';

-- Check for missing team names
DECLARE @MissingTeams INT;
SELECT @MissingTeams = COUNT(*)
FROM dbo.HS_Scores_LoneStar_Staging
WHERE BatchID = @BatchID 
  AND (Home IS NULL OR Home = '' OR Visitor IS NULL OR Visitor = '');

IF @MissingTeams > 0
    PRINT '⚠ WARNING: ' + CAST(@MissingTeams AS NVARCHAR) + ' games with missing team names';
ELSE
    PRINT '✓ All games have team names';

-- Check for invalid scores
DECLARE @InvalidScores INT;
SELECT @InvalidScores = COUNT(*)
FROM dbo.HS_Scores_LoneStar_Staging
WHERE BatchID = @BatchID 
  AND (Home_Score < 0 OR Visitor_Score < 0 OR Home_Score > 150 OR Visitor_Score > 150);

IF @InvalidScores > 0
    PRINT '⚠ WARNING: ' + CAST(@InvalidScores AS NVARCHAR) + ' games with suspicious scores';
ELSE
    PRINT '✓ All scores are reasonable';

-- Check for incorrect margins
DECLARE @BadMargins INT;
SELECT @BadMargins = COUNT(*)
FROM dbo.HS_Scores_LoneStar_Staging
WHERE BatchID = @BatchID 
  AND Margin <> (Home_Score - Visitor_Score);

IF @BadMargins > 0
BEGIN
    PRINT '⚠ WARNING: ' + CAST(@BadMargins AS NVARCHAR) + ' games with incorrect margins';
    PRINT 'Auto-fixing margins...';
    
    UPDATE dbo.HS_Scores_LoneStar_Staging
    SET Margin = Home_Score - Visitor_Score
    WHERE BatchID = @BatchID 
      AND Margin <> (Home_Score - Visitor_Score);
    
    PRINT '✓ Margins corrected';
END
ELSE
    PRINT '✓ All margins are correct';

-- Check for unrecognized team names (not in HS_Team_Names or aliases)
PRINT '';
PRINT '--- Team Name Validation ---';

-- Note: We're checking against both HS_Team_Names and HS_Team_Name_Alias
-- Teams must exist in one of these tables

DECLARE @UnrecognizedHome INT, @UnrecognizedVisitor INT;

SELECT @UnrecognizedHome = COUNT(DISTINCT Home)
FROM dbo.HS_Scores_LoneStar_Staging S
WHERE S.BatchID = @BatchID
  AND NOT EXISTS (
      SELECT 1 FROM dbo.HS_Team_Names T WHERE T.Team_Name = S.Home
  )
  AND NOT EXISTS (
      SELECT 1 FROM dbo.HS_Team_Name_Alias A WHERE A.Standardized_Name = S.Home
  );

SELECT @UnrecognizedVisitor = COUNT(DISTINCT Visitor)
FROM dbo.HS_Scores_LoneStar_Staging S
WHERE S.BatchID = @BatchID
  AND NOT EXISTS (
      SELECT 1 FROM dbo.HS_Team_Names T WHERE T.Team_Name = S.Visitor
  )
  AND NOT EXISTS (
      SELECT 1 FROM dbo.HS_Team_Name_Alias A WHERE A.Standardized_Name = S.Visitor
  );

IF @UnrecognizedHome > 0 OR @UnrecognizedVisitor > 0
BEGIN
    PRINT '⚠ WARNING: Unrecognized team names found';
    PRINT '   Unrecognized Home teams: ' + CAST(@UnrecognizedHome AS NVARCHAR);
    PRINT '   Unrecognized Visitor teams: ' + CAST(@UnrecognizedVisitor AS NVARCHAR);
    PRINT '';
    PRINT '   Run the following query to see the list:';
    PRINT '   SELECT DISTINCT Home FROM HS_Scores_LoneStar_Staging WHERE BatchID = ' + CAST(@BatchID AS NVARCHAR) + ' AND Home NOT IN (SELECT Team_Name FROM HS_Team_Names)';
END
ELSE
    PRINT '✓ All team names recognized';

PRINT '';
PRINT '=== END VALIDATION REPORT ===';
PRINT '';

-- ============================================================================
-- Step 4: Move validated data to production HS_Scores table
-- ============================================================================
-- Only run this after validation passes!

PRINT 'Ready to import to HS_Scores table.';
PRINT '';
PRINT 'To proceed with import, run the following:';
PRINT '';
PRINT '-- Import to HS_Scores (after validation passes)';
PRINT 'EXEC dbo.sp_Import_LoneStar_Batch @BatchID = ' + CAST(@BatchID AS NVARCHAR) + ';';
PRINT '';

GO

-- ============================================================================
-- Step 5: Create import stored procedure (run ONCE to set up)
-- ============================================================================

IF OBJECT_ID('dbo.sp_Import_LoneStar_Batch', 'P') IS NOT NULL
    DROP PROCEDURE dbo.sp_Import_LoneStar_Batch;
GO

CREATE PROCEDURE dbo.sp_Import_LoneStar_Batch
    @BatchID INT,
    @SkipForfeits BIT = 1,        -- Default: skip forfeit games
    @SkipJV BIT = 0,              -- Default: include JV games
    @SkipCollege BIT = 0          -- Default: include College games
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @ImportCount INT = 0;
    DECLARE @SkipCount INT = 0;
    
    PRINT 'Importing Batch ' + CAST(@BatchID AS NVARCHAR) + ' to HS_Scores...';
    PRINT '';
    
    -- Check if batch exists
    IF NOT EXISTS (SELECT 1 FROM dbo.HS_Scores_LoneStar_Staging WHERE BatchID = @BatchID)
    BEGIN
        PRINT '✗ Error: Batch ' + CAST(@BatchID AS NVARCHAR) + ' not found in staging table';
        RETURN;
    END
    
    -- Import games to HS_Scores
    BEGIN TRANSACTION;
    
    BEGIN TRY
        -- Insert games to HS_Scores with auto-generated GUID IDs
        INSERT INTO dbo.HS_Scores (
            [Date],
            Season,
            Home,
            Visitor,
            Neutral,
            Location,
            Location2,
            Line,
            Future_Game,
            Source,
            Date_Added,
            OT,
            Forfeit,
            ID,                                         -- UNIQUEIDENTIFIER (GUID)
            Visitor_Score,
            Home_Score,
            Margin,
            BatchID,
            Access_ID
        )
        SELECT 
            [Date],
            Season,
            Home,
            Visitor,
            ISNULL(Neutral, 0),
            CASE WHEN Location = 'Unknown' THEN NULL ELSE Location END,  -- Convert 'Unknown' to NULL
            Location2,
            Line,
            ISNULL(Future_Game, 0),
            Source,
            GETDATE(),                                  -- Set current timestamp
            OT,
            ISNULL(Forfeit, 0),
            NEWID(),                                    -- Generate unique GUID for each game
            Visitor_Score,
            Home_Score,
            Margin,
            @BatchID,                                   -- Set BatchID for tracking
            Access_ID
        FROM dbo.HS_Scores_LoneStar_Staging
        WHERE BatchID = @BatchID
          AND Status = 'Pending'
          AND (@SkipForfeits = 0 OR ISNULL(Forfeit, 0) = 0);     -- Skip forfeits if flag set
        
        SET @ImportCount = @@ROWCOUNT;
        
        -- Mark imported records
        UPDATE dbo.HS_Scores_LoneStar_Staging
        SET Status = 'Imported'
        WHERE BatchID = @BatchID AND Status = 'Pending';
        
        COMMIT TRANSACTION;
        
        PRINT '✓ Successfully imported ' + CAST(@ImportCount AS NVARCHAR) + ' games to HS_Scores';
        
    END TRY
    BEGIN CATCH
        ROLLBACK TRANSACTION;
        PRINT '✗ Error during import:';
        PRINT ERROR_MESSAGE();
        RETURN;
    END CATCH
    
    -- Remove duplicates
    PRINT '';
    PRINT 'Running duplicate removal...';
    EXEC dbo.RemoveDuplicateGames;
    
    -- Final validation
    PRINT '';
    PRINT '=== IMPORT SUMMARY ===';
    
    SELECT 
        'Games Imported' as Metric,
        @ImportCount as Value
    
    UNION ALL
    
    SELECT 
        'Current Total (LoneStar)',
        COUNT(*)
    FROM dbo.HS_Scores
    WHERE Source LIKE '%lonestarfootball.net%'
    
    UNION ALL
    
    SELECT 
        'Duplicates Removed',
        @ImportCount - (SELECT COUNT(*) FROM dbo.HS_Scores WHERE Source LIKE '%lonestarfootball.net%' AND Date_Added >= CAST(GETDATE() AS DATE))
    
    UNION ALL
    
    SELECT 
        'Batch Status',
        CAST(@BatchID AS NVARCHAR) + ' - Imported'
    
    ORDER BY Metric;
    
    PRINT '';
    PRINT '✓ Import complete!';
    
END
GO

PRINT '';
PRINT '============================================================================';
PRINT 'Setup complete! Import stored procedure created.';
PRINT '============================================================================';
PRINT '';
PRINT 'USAGE:';
PRINT '1. Export Excel to CSV (UTF-8)';
PRINT '2. Update @CSVPath in Step 2 above';
PRINT '3. Run Steps 2-3 to import and validate';
PRINT '4. If validation passes, run: EXEC sp_Import_LoneStar_Batch @BatchID = [BatchID]';
PRINT '';

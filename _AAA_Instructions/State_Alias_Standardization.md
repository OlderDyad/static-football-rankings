📜 SOP: New State Alias StandardizationThis document outlines the standard procedure for identifying, aliasing, and retroactively correcting team names after a new state's data (e.g., South Dakota) has been imported.Phase 1: Generate Alias WorksheetObjective: To extract all new, un-aliased team names from the database, count their frequency, and export them to a CSV file for manual processing.Action:Set the @StartSeason variable to the first season of your new data import.Run the following SQL query in SQL Server Management Studio (SSMS).Right-click the results grid and select "Save Results As..." to create your CSV worksheet (e.g., sd_alias_worksheet.csv).SQL/*
-- =============================================
-- Script: Generate_New_Alias_Worksheet
-- Description: Finds all un-aliased team names from a recent
-- import, counts their frequency, and provides
-- a blank column for the new canonical name.
-- =============================================
*/

-- 1. Set the first season of your new data import
DECLARE @StartSeason INT = 2023; -- (Example: set to your new data's start)

-- 2. CTE to gather all team names (Home and Visitor)
WITH RawTeamList AS (
    SELECT Home AS TeamName FROM dbo.HS_Scores WHERE Season >= @StartSeason
    UNION ALL
    SELECT Visitor AS TeamName FROM dbo.HS_Scores WHERE Season >= @StartSeason
)
-- 3. Group, count, and filter
SELECT
    TeamName AS Raw_Name,
    COUNT(*) AS Frequency,
    '' AS Proper_Name  -- Blank column for you to fill in
FROM
    RawTeamList
WHERE
    -- Filter out names that are already standardized (e.g., end in '(NY)')
    RIGHT(TeamName, 4) NOT LIKE '(%)'
    -- Filter out names that are already in your master alias table
    AND TeamName NOT IN (SELECT Alias_Name FROM dbo.HS_Team_Name_Alias)
GROUP BY
    TeamName
ORDER BY
    Frequency DESC,
    Raw_Name;
Phase 2: Manual Processing (The CSV)Objective: To use your research to fill in the correct canonical name for each raw name.Action:Open the exported sd_alias_worksheet.csv file in Excel or another editor.Go row by row and fill in the Proper_Name column with the correct, full canonical name (e.g., Sioux Falls O'Gorman (SD)).Example Worksheet:Raw_NameFrequencyProper_NameO'Gorman22Sioux Falls O'Gorman (SD)Tri-Valley18Tri-Valley (SD)Platte14Platte-Geddes (SD)Lincoln21Sioux Falls Lincoln (SD)Washington20Sioux Falls Washington (SD).........Phase 3: Commit New AliasesObjective: To add your new, verified aliases to the master dbo.HS_Team_Name_Alias table.Action:Copy the new, completed alias rows from your worksheet.Paste them into your master Alias_Names_List.csv file.Run your PowerShell import script to update the database table.PowerShell# From your PowerShell terminal:
.\Import_Alias_Names.ps1
Result: Your dbo.HS_Team_Name_Alias table is now "aware" of all the new South Dakota teams and their proper names. The dbo.HS_Scores table, however, still contains the raw names.Phase 4: Retroactive Data CorrectionObjective: To "clean up" the dbo.HS_Scores table by replacing all raw names with their newly-aliased proper names.Action:Run the following SQL script. It joins the HS_Scores table against your newly populated HS_Team_Name_Alias table and updates the Home and Visitor columns in place.SQL/*
-- =============================================
-- Script: Retroactive_Alias_Correction
-- Description: Updates the HS_Scores table by replacing
-- raw team names with their standardized names
-- from the HS_Team_Name_Alias table.
-- =============================================
*/

-- Set the same start season used in Phase 1
DECLARE @StartSeason INT = 2023; -- (Example: set to your new data's start)

BEGIN TRANSACTION;

PRINT 'Retroactively updating HS_Scores with new aliases...';

-- Update the Home column
UPDATE s
SET
    s.Home = a.Standardized_Name
FROM
    dbo.HS_Scores s
JOIN
    dbo.HS_Team_Name_Alias a ON s.Home = a.Alias_Name
WHERE
    s.Season >= @StartSeason; -- Only process new seasons

PRINT CAST(@@ROWCOUNT AS VARCHAR) + ' Home team records updated.';

-- Update the Visitor column
UPDATE s
SET
    s.Visitor = a.Standardized_Name
FROM
    dbo.HS_Scores s
JOIN
    dbo.HS_Team_Name_Alias a ON s.Visitor = a.Alias_Name
WHERE
    s.Season >= @StartSeason; -- Only process new seasons

PRINT CAST(@@ROWCOUNT AS VARCHAR) + ' Visitor team records updated.';

COMMIT;
PRINT 'Retroactive update complete.';
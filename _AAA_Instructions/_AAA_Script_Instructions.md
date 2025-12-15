High School Football Database Workflow (2025)

0. 
cd C:\Users\demck\OneDrive\Football_2024\static-football-rankings\scripts\

1. **.\run_update_cycle.ps1** (The "Daily Master Switch")
When to use: Every time you make changes to Google Sheets or Add New Images. What it does:

Syncs your Google Sheet edits to SQL.

Moves images from your Desktop to the project folder.

Generates new JSON data files (with updated colors/logos).

Calls .\GenerateAllPages.ps1 automatically (Step 4 in the script).

Commits and Pushes everything to GitHub.

Use Case: "I just updated New Britain's colors in Google Sheets and saved their logo to my desktop. I want the website to update."

cd C:\Users\demck\OneDrive\Football_2024\static-football-rankings\scripts\

2. **.\GenerateAllPages.ps1** (The "Template Refresher")
When to use: Only when you change the HTML structure or JavaScript logic (like the color theming patch we just discussed). What it does:

Rebuilds every .html file in your project based on your templates.

Updates the "Last Updated" timestamp in the HTML.

Injects new script tags (like the Table Color Theming script).

Use Case: "I just ran Add-TableColorTheming.ps1 to inject new code into my page generator. Now I need to rebuild all the HTML pages so they include this new code."

PART A: SCORES & RANKINGS (The "Stats" Engine)

Run this when game scores need to be updated.

1. Scrape Scores (MaxPreps)

Tool: Python / Selenium

Location: python_scripts/

Command: **python maxpreps_excel_loop.py**

Output: Populates Excel/CSV files with raw game data.

2. Import & Transform (SQL)

Location: SQL Server Management Studio (SSMS)

Step 2.1 (Import): Bulk Insert CSV to HS_Scores_Staging.

Step 2.2 (Clean): Check TeamName_Alias_Mapping for new variations.

Step 2.3 (Transform): Run EXEC TransformStagingToScores @Season = 2024.

Step 2.4 (Dedupe): Run Duplicate Detection query to remove double-entries.

3. Calculate Rankings (SQL)

Action: Recalculates the math (Win/Loss, Margin, Ratings) for all teams.

SQL Command:

EXEC [dbo].[CalculateRankings_v4_Optimized]
    @LeagueType = '1',
    @BeginSeason = 2024,
    @EndSeason = 2024,
    @Week = 52;


PART B: TEAM IDENTITY (The "Visuals" Engine)

cd C:\Users\demck\OneDrive\Football_2024\static-football-rankings\scripts\
**.\run_update_cycle.ps1**

What this script does for you automatically:

Runs pull_sheets_to_sql.py: Saves your Google Sheet changes to SQL.

Runs ingest_images_by_id.py: Moves your images and links them in SQL.

Runs generate_site_data.py: Updates the JSON files with the new data.

Runs GenerateAllPages.ps1: Updates the HTML tables.

Git Push: Publishes everything to the live site.

Summary: Just run .\run_update_cycle.ps1. It handles everything safely.

Part B2:
To update Google Sheets, you need to run the "push" script. This script fetches the current data from your HS_Team_Names SQL table (including the new image paths and colors you just generated) and uploads it to your Google Sheet.

Here is the command to run in your terminal:

cd C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\data_import\
**python push_HS_Names_export_to_sheets.py**


2. Add Images

Action: Save images to Desktop\HS_Image_Drop.

Naming: ID_TeamName_Type.png (e.g., 1405_NewBritain_Helmet.png).

Ingest Command:

**python ingest_images_by_id.py**


3. Reset Google Sheet (Optional)

Use only if: You want to refresh the sheet with the latest SQL data.

Command: **python push_HS_Names_export_to_sheets.py**

PART C: WEBSITE PUBLISHING (The "Build" Engine)

Run this to push changes to the live internet.

The "One-Click" Master Script

cd C:\Users\demck\OneDrive\Football_2024\static-football-rankings\scripts\
File: **.\run_update_cycle.ps1**
Location: ...\scripts\

What it does:

Syncs Text: Runs pull_sheets_to_sql.py.

Syncs Images: Runs ingest_images_by_id.py.

Generates State Data: Runs generate_site_data.py (Python).

Note: Creates both state-teams-*.json and state-programs-*.json.

Note: Applies Color Translation and Image Path fixing.

Rebuilds HTML: Runs GenerateAllPages.ps1 (PowerShell).

Publishes: Commits and Pushes to GitHub Main.

Manual Generation (If needed for debugging)

State JSONs: python generate_site_data.py

Global JSONs (All-Time/Decade): Run specific .ps1 scripts in scripts/imported_SQL_json/.

============================================OLD WORKFLOW=======================================
Get Maxpreps scores

list of URLS:
C:\Users\demck\OneDrive\Football_2024\static-football-rankings\excel_files\MaxPreps_Export.xlsx

Step 1: Open Your Terminal & Activate Python Virtual Environment
Open Windows PowerShell or Command Prompt.
Navigate to your Python script folder:

cd C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts
Activate your Python virtual environment:

.\venv\Scripts\Activate
(If using Command Prompt instead of PowerShell, use venv\Scripts\activate.bat.)
Step 2: Run the Python Script
Run the script to open the chrome & Maxpreps:

C:\Users\demck\OneDrive\Football_2024\static-football-rankings\.venv\Scripts\Activate


pip install selenium
pip install pandas
pip install openpyxl

python maxpreps_excel_loop.py
The script will launch Google Chrome and load the Maxpreps Scores page.

python maxpreps_excel_loop_bak.py



_________________________________
MaxPreps Data Import Process 2025
Step 1: Initial Setup & Tables

Ensure required tables exist:

HS_Scores_Staging (raw CSV data)
TeamName_Alias_Mapping (name standardization)
URL_ProperName_Mapping (URL to name mapping)
UnmappedURL_Log (tracking problematic URLs)
Manual_Review_Games (tracking records needing review)



Step 2: Data Import to Staging
sqlCopyTRUNCATE TABLE dbo.HS_Scores_Staging;
BULK INSERT dbo.HS_Scores_Staging
FROM 'C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\all_schedules.csv'
WITH (
    FIRSTROW = 2,
    FIELDTERMINATOR = ',',
    ROWTERMINATOR = '\n',
    CODEPAGE = '65001'
);
Step 3: Name Standardization

Check for new name variations:

sqlCopy-- Find URLs with multiple team names
SELECT URL, 
       STRING_AGG(TeamName, ' | ') as TeamNameVariations,
       COUNT(*) as VariationCount
FROM (SELECT DISTINCT URL, TeamName
      FROM HS_Scores_Staging
      WHERE Status = 'Processed') x
GROUP BY URL
HAVING COUNT(*) > 1;

Update TeamName_Alias_Mapping with new variations

Step 4: Transform and Load


Run transform procedure:

sqlCopyEXEC TransformStagingToScores @Season = 2024;
Step 5: Duplicate Detection
sqlCopyWITH DuplicateGames AS (
    SELECT 
        ID,
        ROW_NUMBER() OVER (
            PARTITION BY [Date], Home, Home_Score, Visitor, Visitor_Score
            ORDER BY Date_Added ASC
        ) AS rn
    FROM HS_Scores
    WHERE Season = 2024
)
DELETE FROM HS_Scores
WHERE ID IN (
    SELECT ID 
    FROM DuplicateGames 
    WHERE rn > 1
);
Step 6: Quality Checks

Check UnmappedURL_Log for new issues
Verify name standardization worked
Sample data validation
Check for unusual scores or patterns

_________________________________
Sync Sql HS_Team_Names with excel HS_Team_Names:
C:\Users\demck\OneDrive\Football_2024\static-football-rankings\excel_files\HS_Team_Names.xltm


cd C:\Users\demck\OneDrive\Football_2024\static-football-rankings\scripts
.\fix-image-filenames.ps1

-- Review the generated SQL script:
-- C:\Users\demck\OneDrive\Football_2024\fix-image-paths.sql

-- Then execute it against your SQL Server database
-- You can use SQL Server Management Studio or:
sqlcmd -S MCKNIGHTS-PC\SQLEXPRESS01 -d hs_football_database -i "C:\Users\demck\OneDrive\Football_2024\fix-image-paths.sql"

cd C:\Users\demck\OneDrive\Football_2024\static-football-rankings\scripts
.\sync_HS_Team_Names.ps1

______________________________
make edits to HS_Team_Names
ie:

UPDATE HS_Team_Names
SET PrimaryColor = 'Crimson'
WHERE Team_Name = 'Muskegon (MI)';
___________________________________

Run in SQL to update rankings:

EXEC [dbo].[CalculateRankings]
    @LeagueType = 1,      -- Assuming '1' for high school
    @BeginSeason = 2024,     -- Starting season
    @EndSeason = 2024,       -- Ending season
    @Week = 52,              -- Week number
    @MaxLoops = 2048;        -- Optional, can be omitted to use default

===========================================
Current workflow - est: 11/27/2025:

cd C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\
python generate_site_data.py

# 1. Move to the main folder
cd ..

# 2. Add the updated JSON files
git add docs/data/states

# 3. Commit the changes
git commit -m "Updated Site Data: Teams and Programs now fully synchronized no:10"

# 4. Push to GitHub
git push origin main
============================================

Old workflow 1:
Generate .json files group by group

cd C:\Users\demck\OneDrive\Football_2024\static-football-rankings\scripts\imported_SQL_json
.\generate-all-time-programs.ps1
.\generate-all-time-teams.ps1
.\generate-decade-programs.ps1
.\generate-decade-teams.ps1
.\generate-latest-season-teams.ps1
.\generate-state-programs.ps1
.\generate-state-teams.ps1
==============================================


______________________________

Generate All .html files

cd C:\Users\demck\OneDrive\Football_2024\static-football-rankings\scripts
.\GenerateAllPages.ps1


**note C:\Users\demck\OneDrive\Football_2024\static-football-rankings\scripts\imported_SQL_json\common-functions.ps1
is a key file for html "top/dynamic" header creation.
_______________________________

Push changes to GitHub

# Navigate to repository
cd C:\Users\demck\OneDrive\Football_2024\static-football-rankings

# Add all updated files
git add docs/data/*.json
git add docs/pages/public/**/*.html

# Commit with descriptive message
git commit -m "Update json data and regenerate all HTML pages 2025d"

# Push to GitHub
git push origin main

___________________________________
cd C:\Users\demck\OneDrive\Football_2024\static-football-rankings

# Add all changed files to the staging area
git add .

# Commit the changes with a descriptive message
git commit -m "Fix banner image loading issues and standardize TopBanner implementation v5"

# Push the changes to your remote repository (GitHub)
git push origin main

______________________________

cd C:\Users\demck\OneDrive\Football_2024\static-football-rankings
git add .
git commit -m "Fix data-file paths and remove userStyle tags"
git push origin main
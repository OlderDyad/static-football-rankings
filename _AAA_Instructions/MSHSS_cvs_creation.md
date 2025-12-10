Quick Steps:

cd C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts

**.\venv\Scripts\Activate**

**python MHSAA_WebScrapper.py**

Sport: Select Football.
Start Date: Enter the first date you want to collect.
End Date: Enter the last date you want to collect.
Level: Select Varsity.
Click the ‘Search’ button manually.

Do you want to append to the existing CSV file (a) or overwrite it (w)? [a/w]:
Enter w (overwrite) to create a new CSV file for this session.

Step 5: Run Again for 8-Man Scores
Run the script again:

python MHSAA_WebScrapper.py
When the page opens, change the Level filter to 8-Man.



🏈 MHSAA Football Data Workflow (Annual Update)
Goal: Scrape all Varsity & 8-Man game scores from MHSAA.com and import them into the HS_Scores SQL table.

Phase 1: Setup & Preparation
Open Terminal (PowerShell or Command Prompt).

Navigate to the project folder:

PowerShell

cd C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts
Activate Virtual Environment:

PowerShell

.\.venv\Scripts\Activate
(If using Command Prompt: venv\Scripts\activate.bat)

Phase 2: Scrape the Data
Run the Scraper Script:

PowerShell

python MHSAA_WebScrapper.py
Note: The script now automatically handles Chrome updates. You do not need to download a driver manually.

Browser Actions:

Chrome will launch automatically.

Set Filters: Select Football, Season Year, Varsity (or 8-Man), and click Search.

Wait for the results table to load.

Capture Data:

Return to your terminal and press ENTER.

The script will scrape the pages, handling the "Green Icon" column and "Date Header" rows automatically.

Save CSV:

When prompted, choose 'w' (overwrite) for the first run (Varsity).

Optional: Run again for 8-Man, but choose 'a' (append) to add to the same file.

Result: A file named mhsaa_schedules.csv is created.

Phase 3: Clean & Generate SQL
Do not import the CSV directly into SQL. The dates are messy and margins need calculation.

Run the Generator Script:

PowerShell

python Generate_SQL_MHSAA_Import.py
What this script does:

Reads mhsaa_schedules.csv.

Standardizes Dates: Converts "OCTOBER 3" to YYYY-MM-DD.

Splits Scores: Separates "28-21" into Home/Visitor columns.

Calculates Margin: (Home_Score - Visitor_Score).

Fixes Team Names: Adds (MI) suffix to Michigan teams; leaves out-of-state teams like (OH) alone.

Generates IDs: Uses NEWID() to create valid GUIDs for the database.

Result: A file named Import_MHSAA_Clean.sql is created.

Phase 4: Import to SQL Server
Open SQL Server Management Studio (SSMS).

File > Open -> Select Import_MHSAA_Clean.sql.

Execute (F5).

Success Indicator: You should see thousands of (1 row affected) messages.

Phase 5: Verify Data
Run this query in SSMS to ensure the batch looks correct:

SQL

SELECT TOP 50 
       [Date_Added], [Date], [Home], [Visitor], 
       [Home_Score], [Visitor_Score], [Margin], [Source]
FROM [hs_football_database].[dbo].[HS_Scores]
WHERE [Season] = 2025 -- Change Year as needed
  AND [Source] = 'MHSAA'
ORDER BY [Date_Added] DESC;
Phase 6: Post-Import Cleanup (Separate Workflow)
Run the separate "Name Cleaning / Mapping" workflow to harmonize team names (e.g., mapping "AA Pioneer" to "Ann Arbor Pioneer").

Troubleshooting Tips
"SessionNotCreatedException": If Chrome updates again, just run pip install webdriver-manager --upgrade.

"Shifted Columns": If MHSAA changes their website layout (adds/removes columns), check MHSAA_WebScrapper.py and adjust the tds[] index numbers.

"NULL Margins": If margins are missing, run: UPDATE HS_Scores SET Margin = Home_Score - Visitor_Score WHERE Margin IS NULL
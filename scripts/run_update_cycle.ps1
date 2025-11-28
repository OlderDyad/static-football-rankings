# ========================================================
#  MASTER UPDATE CYCLE
#  This script handles the entire Data -> Web workflow.
#  Uncomment sections below for "Full/Seasonal" updates.
# ========================================================

# Store paths for easy navigation
$repoRoot = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings"
$scriptsDir = "$repoRoot\scripts\imported_SQL_json"
$htmlScriptsDir = "$repoRoot\scripts"

# ---------------------------------------------------------
# STEP 0: RUN SQL CALCULATIONS (SEASONAL / FULL UPDATE)
# ---------------------------------------------------------
# Only run this when new game scores are added to recalculate rankings.
# <Uncomment to enable>
# Write-Host "STEP 0: Calculating SQL Rankings..." -ForegroundColor Cyan
# python -c "import pyodbc; conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER=MCKNIGHTS-PC\SQLEXPRESS01;DATABASE=hs_football_database;Trusted_Connection=yes;'); cursor = conn.cursor(); cursor.execute('EXEC [dbo].[CalculateRankings] @LeagueType=1, @BeginSeason=2024, @EndSeason=2024, @Week=52'); conn.commit(); print('Rankings Calculated');"


# ---------------------------------------------------------
# STEP 1: DATA SYNC (Google Sheets & Images)
# ---------------------------------------------------------
# This updates the "Visuals" (Colors, Logos, Websites) for the banners.
Write-Host "--------------------------------" -ForegroundColor Cyan
Write-Host "STEP 1: Saving Google Sheet Data..." -ForegroundColor Cyan
python pull_sheets_to_sql.py

Write-Host "--------------------------------" -ForegroundColor Cyan
Write-Host "STEP 2: Ingesting Images..." -ForegroundColor Cyan
python ingest_images_by_id.py


# ---------------------------------------------------------
# STEP 2: GENERATE JSON DATA FILES
# ---------------------------------------------------------
Write-Host "--------------------------------" -ForegroundColor Cyan
Write-Host "STEP 3: Generating Web JSON Data..." -ForegroundColor Cyan

# Move to scripts folder
Set-Location $scriptsDir

# --- A. STATE UPDATES (Currently Active) ---
Write-Host "   Running State Generators..."
.\generate-state-programs.ps1
.\generate-state-teams.ps1

# --- B. FULL SITE UPDATES (Uncomment for Seasonal Update) ---
# Write-Host "   Running All-Time & Decade Generators..."
# .\generate-all-time-programs.ps1
# .\generate-all-time-teams.ps1
# .\generate-decade-programs.ps1
# .\generate-decade-teams.ps1
# .\generate-latest-season-teams.ps1


# ---------------------------------------------------------
# STEP 3: GENERATE HTML PAGES (SEASONAL / FULL UPDATE)
# ---------------------------------------------------------
# Rebuilds the actual .html files (e.g. index.html, rank pages)
# <Uncomment to enable>
# Write-Host "--------------------------------" -ForegroundColor Cyan
# Write-Host "STEP 4: Regenerating HTML Pages..." -ForegroundColor Cyan
# Set-Location $htmlScriptsDir
# .\GenerateAllPages.ps1


# ---------------------------------------------------------
# STEP 4: GITHUB PUBLISH
# ---------------------------------------------------------
Write-Host "--------------------------------" -ForegroundColor Cyan
Write-Host "STEP 5: Pushing to GitHub..." -ForegroundColor Cyan

# Move to Repo Root
Set-Location $repoRoot

# Add all changes (JSONs, Images, HTML)
git add .

# Commit with timestamp
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm"
git commit -m "Update state rankings and images via Master Cycle ($timestamp)"

# Push to Main
git push origin main

# Return to original folder
Set-Location $PSScriptRoot

Write-Host "--------------------------------" -ForegroundColor Green
Write-Host "CYCLE COMPLETE. Website is live." -ForegroundColor Green
Pause
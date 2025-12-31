# ========================================================
#  MASTER UPDATE CYCLE (v6 - Updated December 31, 2025)
#  1. Syncs Google Sheets & Images to SQL (Python)
#  2. Generates Web JSONs (Python for States AND Global)
#  3. Generates Statistics (Database & Regional)
#  4. Rebuilds HTML (PowerShell)
#  5. Publishes to GitHub
# ========================================================

$repoRoot = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings"
$pythonDir = "$repoRoot\python_scripts\data_import"
$pythonScriptsRoot = "$repoRoot\python_scripts"
$psScriptsDir = "$repoRoot\scripts\imported_SQL_json"
$htmlScriptsDir = "$repoRoot\scripts"

# ---------------------------------------------------------
# STEP 1: DATA INPUT (The Source of Truth)
# ---------------------------------------------------------
Write-Host "STEP 1: Syncing Data from Sheets & Images..." -ForegroundColor Cyan
Set-Location $pythonDir

# Save text edits from Google Sheets -> SQL
python pull_sheets_to_sql.py

# Process new images from Desktop -> SQL
python ingest_images_by_id.py

# ---------------------------------------------------------
# STEP 2: GENERATE STATE DATA (PYTHON)
# ---------------------------------------------------------
Write-Host "STEP 2: Generating State JSON Data..." -ForegroundColor Cyan

# 1. Generate State Teams & Programs (CT, TX, etc.)
python generate_site_data.py

# ---------------------------------------------------------
# STEP 3: GENERATE GLOBAL DATA (PYTHON & POWERSHELL)
# ---------------------------------------------------------
Write-Host "STEP 3: Generating Global & Decade JSON Data..." -ForegroundColor Cyan

# 2. Generate All-Time & Decade Lists (1980s, 1990s, etc.)
python generate_global_data.py
python generate_latest_season.py

# 3. Generate National Champions JSON
Write-Host "  - Generating Media National Champions..." -ForegroundColor Yellow
python generate_media_champions_json.py

Write-Host "  - Generating McKnight National Champions..." -ForegroundColor Yellow
Set-Location $psScriptsDir
.\Generate-McKnightNationalChampions.ps1
Set-Location $pythonDir

# ---------------------------------------------------------
# STEP 4: GENERATE STATISTICS (PYTHON)
# ---------------------------------------------------------
Write-Host "STEP 4: Generating Database & Regional Statistics..." -ForegroundColor Cyan
Set-Location $pythonScriptsRoot

# Generate overall database statistics (cumulative games, annual additions)
Write-Host "  - Generating Database Statistics..." -ForegroundColor Yellow
python generate_statistics_charts.py

# Generate regional statistics (5 regions matching States Index)
# Northeast, Southern, Midwest, Western, Canada
Write-Host "  - Generating Regional Statistics..." -ForegroundColor Yellow
python generate_regional_statistics.py

# ---------------------------------------------------------
# STEP 5: REBUILD HTML SHELL
# ---------------------------------------------------------
Write-Host "STEP 5: Rebuilding HTML Pages..." -ForegroundColor Cyan
Set-Location $htmlScriptsDir

# This forces the HTML tables to match your new JSON data
.\GenerateAllPages.ps1

# ---------------------------------------------------------
# STEP 6: PUBLISH
# ---------------------------------------------------------
Write-Host "STEP 6: Pushing to GitHub..." -ForegroundColor Cyan
Set-Location $repoRoot

# Stage all changes (JSON Data, HTML Pages, Statistics, and New Images)
git add .

# Commit
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm"
git commit -m "Master Cycle Update: Synced Sheets, Images, State, Global, Media & McKnight NC, and Statistics Data ($timestamp)"

# Push
git push origin main

Write-Host "--------------------------------" -ForegroundColor Green
Write-Host "CYCLE COMPLETE. Website is live." -ForegroundColor Green
Write-Host "--------------------------------" -ForegroundColor Green
Write-Host ""
Write-Host "Generated:" -ForegroundColor White
Write-Host "  - State Teams & Programs JSON" -ForegroundColor Gray
Write-Host "  - All-Time & Decade JSON" -ForegroundColor Gray
Write-Host "  - Latest Season JSON" -ForegroundColor Gray
Write-Host "  - Media National Champions JSON" -ForegroundColor Gray
Write-Host "  - McKnight National Champions JSON" -ForegroundColor Gray
Write-Host "  - Database Statistics (cumulative/annual charts)" -ForegroundColor Gray
Write-Host "  - Regional Statistics (5 regions)" -ForegroundColor Gray
Write-Host "  - All HTML Pages" -ForegroundColor Gray
Write-Host ""
Pause

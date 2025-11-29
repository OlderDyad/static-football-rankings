# ========================================================
#  MASTER UPDATE CYCLE (Corrected v2)
#  1. Syncs Google Sheets & Images to SQL (Python)
#  2. Generates Web JSONs (Python for States - CRITICAL CHANGE)
#  3. Rebuilds HTML (PowerShell - UNCOMMENTED)
#  4. Publishes to GitHub
# ========================================================

$repoRoot = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings"
$pythonDir = "$repoRoot\python_scripts\data_import"
$psScriptsDir = "$repoRoot\scripts\imported_SQL_json"
$htmlScriptsDir = "$repoRoot\scripts"

# ---------------------------------------------------------
# STEP 1: DATA INPUT (The Source of Truth)
# ---------------------------------------------------------
Write-Host "--------------------------------" -ForegroundColor Cyan
Write-Host "STEP 1: Syncing Data from Sheets & Images..." -ForegroundColor Cyan
Set-Location $pythonDir

# Save text edits from Google Sheets -> SQL
python pull_sheets_to_sql.py

# Process new images from Desktop -> SQL
python ingest_images_by_id.py

# ---------------------------------------------------------
# STEP 2: GENERATE STATE DATA (PYTHON)
# ---------------------------------------------------------
Write-Host "--------------------------------" -ForegroundColor Cyan
Write-Host "STEP 2: Generating State JSON Data (Python)..." -ForegroundColor Cyan

# CRITICAL FIX: Use the Python generator, NOT the old PowerShell scripts.
# The Python script has the 25-season filter, color translator, and image path fixes.
python generate_site_data.py

# ---------------------------------------------------------
# STEP 3: GENERATE GLOBAL LISTS (POWERSHELL LEGACY)
# ---------------------------------------------------------
# Write-Host "STEP 3: Generating Global Rankings (PowerShell)..." -ForegroundColor Cyan
# Set-Location $psScriptsDir
# Only uncomment if you need to update All-Time/Decade lists
# .\generate-all-time-programs.ps1
# .\generate-all-time-teams.ps1

# ---------------------------------------------------------
# STEP 4: REBUILD HTML SHELL (THE FIX FOR STALE TABLES)
# ---------------------------------------------------------
Write-Host "--------------------------------" -ForegroundColor Cyan
Write-Host "STEP 4: Rebuilding HTML Pages..." -ForegroundColor Cyan
Set-Location $htmlScriptsDir

# UNCOMMENTED: This forces the HTML tables to match your new JSON data
.\GenerateAllPages.ps1

# ---------------------------------------------------------
# STEP 5: PUBLISH
# ---------------------------------------------------------
Write-Host "--------------------------------" -ForegroundColor Cyan
Write-Host "STEP 5: Pushing to GitHub..." -ForegroundColor Cyan
Set-Location $repoRoot

# Stage all changes (JSON Data, HTML Pages, and New Images)
git add .

# Commit
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm"
git commit -m "Master Cycle Update: Synced Sheets, Images, JSON, and HTML ($timestamp)"

# Push
git push origin main

Write-Host "--------------------------------" -ForegroundColor Green
Write-Host "CYCLE COMPLETE. Website is live." -ForegroundColor Green
Pause
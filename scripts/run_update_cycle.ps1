# ========================================================
#  MASTER UPDATE CYCLE (Corrected v3)
#  1. Syncs Google Sheets & Images to SQL (Python)
#  2. Generates Web JSONs (Python for States AND Global)
#  3. Rebuilds HTML (PowerShell)
#  4. Publishes to GitHub
# ========================================================

$repoRoot = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings"
$pythonDir = "$repoRoot\python_scripts\data_import"
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
# STEP 3: GENERATE GLOBAL DATA (PYTHON)
# ---------------------------------------------------------
Write-Host "STEP 3: Generating Global & Decade JSON Data..." -ForegroundColor Cyan

# 2. Generate All-Time & Decade Lists (1980s, 1990s, etc.)
# This uses your new script to apply colors/logos to global lists
python generate_global_data.py
python generate_latest_season.py

# ---------------------------------------------------------
# STEP 4: REBUILD HTML SHELL
# ---------------------------------------------------------
Write-Host "STEP 4: Rebuilding HTML Pages..." -ForegroundColor Cyan
Set-Location $htmlScriptsDir

# This forces the HTML tables to match your new JSON data
.\GenerateAllPages.ps1

# ---------------------------------------------------------
# STEP 5: PUBLISH
# ---------------------------------------------------------
Write-Host "STEP 5: Pushing to GitHub..." -ForegroundColor Cyan
Set-Location $repoRoot

# Stage all changes (JSON Data, HTML Pages, and New Images)
git add .

# Commit
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm"
git commit -m "Master Cycle Update: Synced Sheets, Images, State, and Global Data ($timestamp)"

# Push
git push origin main

Write-Host "--------------------------------" -ForegroundColor Green
Write-Host "CYCLE COMPLETE. Website is live." -ForegroundColor Green
Pause
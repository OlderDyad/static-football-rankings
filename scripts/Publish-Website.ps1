###############################################################################
# Publish-Website.ps1
# Master script to:
# 1. Generate all data (JSON + Statistics)
# 2. Rebuild all HTML pages
# 3. Commit and push all changes to GitHub
###############################################################################

$separator = "=" * 80
Write-Host $separator -ForegroundColor Cyan
Write-Host "Starting Full Website Publish..." -ForegroundColor Cyan
Write-Host $separator -ForegroundColor Cyan

# --- Define Core Paths ---
# $PSScriptRoot is the folder this script is in (i.e., ...\scripts)
$scriptRoot = $PSScriptRoot
$repoRoot = (Resolve-Path (Join-Path $scriptRoot "..")).Path
$jsonScriptDir = Join-Path $scriptRoot "imported_SQL_json"

# --- 1. Generate JSON Files ---
Write-Host "`n[Step 1/4] Generating JSON data files..." -ForegroundColor Yellow
Set-Location $jsonScriptDir
& .\generate-all-time-programs.ps1
& .\generate-all-time-teams.ps1
& .\generate-decade-programs.ps1
& .\generate-decade-teams.ps1
& .\generate-latest-season-teams.ps1
& .\generate-state-programs.ps1
& .\generate-state-teams.ps1
& .\Generate-MediaNationalChampions.ps1
& .\Generate-McKnightNationalChampions.ps1
Write-Host "JSON data generation complete." -ForegroundColor Green

# --- 2. Generate Statistics ---
Write-Host "`n[Step 2/4] Generating database statistics..." -ForegroundColor Yellow
Set-Location $scriptRoot # Go back up to the main 'scripts' folder
& .\Generate-DatabaseStatistics.ps1
Write-Host "Statistics generation complete." -ForegroundColor Green

# --- 3. Generate All HTML Pages ---
Write-Host "`n[Step 3/4] Building all HTML pages..." -ForegroundColor Yellow
Set-Location $scriptRoot
& .\GenerateAllPages.ps1
Write-Host "HTML build complete." -ForegroundColor Green

# --- 4. Push to GitHub ---
Write-Host "`n[Step 4/4] Deploying to GitHub..." -ForegroundColor Yellow
Set-Location $repoRoot # Go to the top-level folder for Git

# Get a commit message from the user
$defaultMessage = "Regenerate all data and HTML pages - $(Get-Date -Format 'yyyy-MM-dd')"
$commitMessage = Read-Host -Prompt "Enter commit message (or press Enter for default)"
if ([string]::IsNullOrWhiteSpace($commitMessage)) {
    $commitMessage = $defaultMessage
}
Write-Host "Using commit message: '$commitMessage'" -ForegroundColor Gray

# Run Git commands
Write-Host "Running 'git add .'" -ForegroundColor Gray
git add .

Write-Host "Running 'git commit'" -ForegroundColor Gray
git commit -m $commitMessage

Write-Host "Running 'git push origin main'" -ForegroundColor Gray
git push origin main

Write-Host "`n$separator" -ForegroundColor Cyan
Write-Host "Publish Complete! Website is updating." -ForegroundColor Cyan
Write-Host $separator -ForegroundColor Cyan
###############################################################################
# Generate-RegionalStatistics.ps1
# Generates regional game coverage statistics and visualizations
###############################################################################

Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "🗺️  McKnight's Football Rankings - Regional Statistics Generator" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan

# Configuration
$rootDir = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings"
$pythonScriptDir = Join-Path $rootDir "python_scripts"
$dataOutputDir = Join-Path $rootDir "docs\data\regional-statistics"
$pageOutputDir = Join-Path $rootDir "docs\pages\public"
$venvPath = Join-Path $rootDir ".venv\Scripts\Activate.ps1"

Write-Host "`n📁 Checking directories..." -ForegroundColor Yellow

# Ensure directories exist
if (-not (Test-Path $dataOutputDir)) {
    Write-Host "Creating regional statistics data directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $dataOutputDir -Force | Out-Null
}

# Step 1: Activate Python virtual environment
Write-Host "`n🐍 Activating Python virtual environment..." -ForegroundColor Yellow
if (Test-Path $venvPath) {
    & $venvPath
    Write-Host "✅ Virtual environment activated" -ForegroundColor Green
} else {
    Write-Error "Virtual environment not found at: $venvPath"
    Write-Host "Please create a virtual environment first" -ForegroundColor Yellow
    exit 1
}

# Step 2: Check for required Python packages
Write-Host "`n📦 Checking Python dependencies..." -ForegroundColor Yellow
$requiredPackages = @("pyodbc", "pandas", "plotly")
$missingPackages = @()

foreach ($package in $requiredPackages) {
    $installed = & python -c "import $package" 2>&1
    if ($LASTEXITCODE -ne 0) {
        $missingPackages += $package
    }
}

if ($missingPackages.Count -gt 0) {
    Write-Host "⚠️  Missing packages: $($missingPackages -join ', ')" -ForegroundColor Yellow
    Write-Host "Installing missing packages..." -ForegroundColor Yellow
    foreach ($package in $missingPackages) {
        & pip install $package
    }
}
Write-Host "✅ All dependencies satisfied" -ForegroundColor Green

# Step 3: Check if Python script exists
$pythonScriptPath = Join-Path $pythonScriptDir "generate_regional_statistics.py"
if (-not (Test-Path $pythonScriptPath)) {
    Write-Error "Python script not found: $pythonScriptPath"
    Write-Host "Please copy generate_regional_statistics.py to the python_scripts directory" -ForegroundColor Yellow
    exit 1
}

# Step 4: Run Python script to generate visualizations
Write-Host "`n📊 Generating regional statistics visualizations..." -ForegroundColor Yellow
Write-Host "This may take a few minutes depending on database size..." -ForegroundColor Gray
Set-Location $pythonScriptDir
& python generate_regional_statistics.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Visualizations generated successfully" -ForegroundColor Green
} else {
    Write-Error "Failed to generate visualizations"
    exit 1
}

# Step 5: Verify output files
Write-Host "`n✅ Verifying output files..." -ForegroundColor Yellow

$regions = @('northeast', 'southeast', 'midwest', 'southwest', 'west', 'canada')
$allFilesExist = $true

# Check comparison chart
$comparisonChart = Join-Path $dataOutputDir "regional_comparison.html"
if (Test-Path $comparisonChart) {
    Write-Host "  ✓ regional_comparison.html" -ForegroundColor Green
} else {
    Write-Host "  ✗ regional_comparison.html - MISSING" -ForegroundColor Red
    $allFilesExist = $false
}

# Check summary file
$summaryFile = Join-Path $dataOutputDir "all_regions_summary.json"
if (Test-Path $summaryFile) {
    Write-Host "  ✓ all_regions_summary.json" -ForegroundColor Green
} else {
    Write-Host "  ✗ all_regions_summary.json - MISSING" -ForegroundColor Red
    $allFilesExist = $false
}

# Check each region's files
foreach ($region in $regions) {
    $regionDir = Join-Path $dataOutputDir $region
    Write-Host "`n  Region: $region" -ForegroundColor Cyan
    
    $expectedFiles = @(
        "games_by_state.html",
        "games_stacked.html",
        "total_by_state.html",
        "summary.json"
    )
    
    foreach ($file in $expectedFiles) {
        $filePath = Join-Path $regionDir $file
        if (Test-Path $filePath) {
            Write-Host "    ✓ $file" -ForegroundColor Green
        } else {
            Write-Host "    ✗ $file - MISSING" -ForegroundColor Red
            $allFilesExist = $false
        }
    }
}

# Step 6: Display summary statistics
Write-Host "`n📊 Regional Summary:" -ForegroundColor Yellow
if (Test-Path $summaryFile) {
    $summary = Get-Content $summaryFile -Raw | ConvertFrom-Json
    
    foreach ($region in $regions) {
        $regionKey = $region.Substring(0,1).ToUpper() + $region.Substring(1)
        if ($summary.PSObject.Properties.Name -contains $regionKey) {
            $stats = $summary.$regionKey
            Write-Host "`n  $($stats.region):" -ForegroundColor Cyan
            Write-Host "    Total Games: $($stats.total_games.ToString('N0'))" -ForegroundColor Gray
            Write-Host "    Seasons: $($stats.earliest_season)-$($stats.latest_season)" -ForegroundColor Gray
            Write-Host "    States/Provinces: $($stats.states_with_data)/$($stats.states.Count)" -ForegroundColor Gray
        }
    }
}

if ($allFilesExist) {
    Write-Host "`n🎉 All files generated successfully!" -ForegroundColor Green
    
    # Step 7: Check if HTML page exists
    $htmlPagePath = Join-Path $pageOutputDir "regional-statistics.html"
    if (-not (Test-Path $htmlPagePath)) {
        Write-Host "`n⚠️  HTML page not found at: $htmlPagePath" -ForegroundColor Yellow
        Write-Host "Please copy regional_statistics.html to this location" -ForegroundColor Yellow
    } else {
        Write-Host "`n✅ HTML page found" -ForegroundColor Green
    }
    
    Write-Host "`nNext steps:" -ForegroundColor Cyan
    Write-Host "  1. Review the generated files in: $dataOutputDir" -ForegroundColor Gray
    Write-Host "  2. Ensure regional_statistics.html is in: $pageOutputDir" -ForegroundColor Gray
    Write-Host "  3. Test locally by opening the HTML file" -ForegroundColor Gray
    Write-Host "  4. Update your home page or database statistics page with a link" -ForegroundColor Gray
    Write-Host "  5. Commit and push to GitHub:" -ForegroundColor Gray
    Write-Host "     cd $rootDir" -ForegroundColor DarkGray
    Write-Host "     git add docs/data/regional-statistics/* docs/pages/public/regional-statistics.html" -ForegroundColor DarkGray
    Write-Host "     git commit -m 'Add regional coverage statistics'" -ForegroundColor DarkGray
    Write-Host "     git push origin main" -ForegroundColor DarkGray
} else {
    Write-Error "Some files were not generated. Please check for errors above."
}

Write-Host "`n" + ("=" * 80) -ForegroundColor Cyan
Write-Host "Process complete!" -ForegroundColor Cyan
Write-Host ("=" * 80) -ForegroundColor Cyan

# ================================================================
# Export-ProjectContext.ps1
# Automated script to gather all project context materials
# for McKnight's American Football Rankings
# ================================================================

param(
    [string]$RepoRoot = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings",
    [string]$SqlServer = "McKnights-PC\SQLEXPRESS01",
    [string]$Database = "hs_football_database"
)

$ErrorActionPreference = "Stop"

# Output directories
$contextRoot = Join-Path $RepoRoot "docs\project-context"
$workflowsDir = Join-Path $contextRoot "workflows"
$schemasDir = Join-Path $contextRoot "schemas"
$proceduresDir = Join-Path $contextRoot "stored-procedures"
$queriesDir = Join-Path $contextRoot "queries"
$scriptsDir = Join-Path $contextRoot "scripts"
$architectureDir = Join-Path $contextRoot "architecture"

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Export Project Context - McKnight's American Football Rankings" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# ================================================================
# STEP 1: Create Directory Structure
# ================================================================
Write-Host "[1/6] Creating directory structure..." -ForegroundColor Yellow

$directories = @(
    $contextRoot,
    $workflowsDir,
    $schemasDir,
    $proceduresDir,
    $queriesDir,
    $scriptsDir,
    $architectureDir
)

foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "  ✓ Created: $dir" -ForegroundColor Green
    } else {
        Write-Host "  ✓ Exists: $dir" -ForegroundColor Gray
    }
}

# ================================================================
# STEP 2: Export SQL Server Objects
# ================================================================
Write-Host "`n[2/6] Exporting SQL Server objects..." -ForegroundColor Yellow

# Load SMO (SQL Server Management Objects)
try {
    [System.Reflection.Assembly]::LoadWithPartialName("Microsoft.SqlServer.SMO") | Out-Null
    $server = New-Object Microsoft.SqlServer.Management.Smo.Server($SqlServer)
    $db = $server.Databases[$Database]
    
    if ($null -eq $db) {
        throw "Database '$Database' not found on server '$SqlServer'"
    }
    
    Write-Host "  ✓ Connected to: $SqlServer\$Database" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Failed to connect to SQL Server" -ForegroundColor Red
    Write-Host "    Error: $_" -ForegroundColor Red
    Write-Host "    Note: Install SQL Server Management Studio for SMO libraries" -ForegroundColor Yellow
    Write-Host "    Skipping SQL export..." -ForegroundColor Yellow
    $skipSQL = $true
}

if (-not $skipSQL) {
    # Export Table Schemas
    Write-Host "`n  Exporting table schemas..." -ForegroundColor Cyan
    $keyTables = @(
        "HS_Scores",
        "HS_Team_Names", 
        "HS_Rankings",
        "Media_National_Champions",
        "HS_Rating_Rankings",
        "HS_Scores_LoneStar_Staging",
        "team_scraping_status",
        "scraping_batches"
    )
    
    foreach ($tableName in $keyTables) {
        try {
            $table = $db.Tables | Where-Object { $_.Name -eq $tableName -and $_.Schema -eq "dbo" }
            if ($table) {
                $scriptOptions = New-Object Microsoft.SqlServer.Management.Smo.ScriptingOptions
                $scriptOptions.ScriptDrops = $false
                $scriptOptions.IncludeHeaders = $true
                $scriptOptions.Indexes = $true
                $scriptOptions.DriAll = $true
                $scriptOptions.Statistics = $true
                
                $outputFile = Join-Path $schemasDir "$tableName.sql"
                $table.Script($scriptOptions) | Out-File -FilePath $outputFile -Force
                Write-Host "    ✓ Exported: $tableName" -ForegroundColor Green
            } else {
                Write-Host "    ✗ Not found: $tableName" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "    ✗ Error exporting $tableName : $_" -ForegroundColor Red
        }
    }
    
    # Export Stored Procedures
    Write-Host "`n  Exporting stored procedures..." -ForegroundColor Cyan
    $procedures = $db.StoredProcedures | Where-Object { -not $_.IsSystemObject }
    
    foreach ($proc in $procedures) {
        try {
            $scriptOptions = New-Object Microsoft.SqlServer.Management.Smo.ScriptingOptions
            $scriptOptions.IncludeHeaders = $true
            
            $outputFile = Join-Path $proceduresDir "$($proc.Name).sql"
            $proc.Script($scriptOptions) | Out-File -FilePath $outputFile -Force
            Write-Host "    ✓ Exported: $($proc.Name)" -ForegroundColor Green
        } catch {
            Write-Host "    ✗ Error exporting $($proc.Name): $_" -ForegroundColor Red
        }
    }
    
    # Create useful query templates
    Write-Host "`n  Creating query templates..." -ForegroundColor Cyan
    
    $queries = @{
        "find_team_by_name.sql" = @"
-- Find team by name pattern
-- Usage: Replace '%TEAM_NAME%' with actual search term
SELECT 
    ID, 
    Team_Name, 
    City, 
    State, 
    Mascot, 
    PrimaryColor, 
    SecondaryColor,
    LogoURL,
    HelmetURL
FROM HS_Team_Names
WHERE Team_Name LIKE '%TEAM_NAME%'
ORDER BY State, Team_Name;
"@
        
        "team_game_history.sql" = @"
-- Get complete game history for a team
-- Usage: Replace 'TEAM_NAME (ST)' with actual team name
SELECT 
    Date, 
    Season, 
    Home, 
    Visitor, 
    Home_Score, 
    Visitor_Score, 
    Source,
    Date_Added
FROM HS_Scores
WHERE Home = 'TEAM_NAME (ST)' 
   OR Visitor = 'TEAM_NAME (ST)'
ORDER BY Date DESC;
"@
        
        "teams_without_logos.sql" = @"
-- Find teams missing logo images
SELECT 
    ID, 
    Team_Name, 
    State,
    City,
    Mascot
FROM HS_Team_Names
WHERE (LogoURL IS NULL OR LogoURL = '')
  AND State IN ('CA', 'TX', 'FL', 'OH', 'PA') -- Adjust states as needed
ORDER BY State, Team_Name;
"@
        
        "teams_without_colors.sql" = @"
-- Find teams missing color information
SELECT 
    ID, 
    Team_Name, 
    State,
    City
FROM HS_Team_Names
WHERE (PrimaryColor IS NULL OR PrimaryColor = '')
ORDER BY State, Team_Name;
"@
        
        "top_teams_by_decade.sql" = @"
-- Get top 10 teams for a specific decade
-- Usage: Adjust BETWEEN years for desired decade
SELECT TOP 10 
    Team, 
    Season, 
    Combined, 
    Margin, 
    Win_Loss, 
    Games_Played,
    Log_Score
FROM HS_Rating_Rankings
WHERE Season BETWEEN 1950 AND 1959 -- Adjust as needed
ORDER BY Combined DESC;
"@
        
        "duplicate_games.sql" = @"
-- Find duplicate game entries
SELECT 
    Date, 
    Home, 
    Visitor, 
    Home_Score, 
    Visitor_Score, 
    COUNT(*) as DuplicateCount
FROM HS_Scores
GROUP BY Date, Home, Visitor, Home_Score, Visitor_Score
HAVING COUNT(*) > 1
ORDER BY DuplicateCount DESC;
"@
        
        "suspicious_game_counts.sql" = @"
-- Find teams with abnormally high game counts (possible merge candidates)
SELECT 
    Home as Team,
    COUNT(*) as GameCount,
    MIN(Season) as FirstSeason,
    MAX(Season) as LastSeason,
    COUNT(DISTINCT Season) as SeasonsPlayed
FROM HS_Scores
GROUP BY Home
HAVING COUNT(*) > 500 -- Adjust threshold as needed
ORDER BY GameCount DESC;
"@
        
        "recent_additions.sql" = @"
-- Show recently added games (last 7 days)
SELECT TOP 100
    Date_Added,
    Date,
    Season,
    Home,
    Visitor,
    Home_Score,
    Visitor_Score,
    Source
FROM HS_Scores
WHERE Date_Added >= DATEADD(day, -7, GETDATE())
ORDER BY Date_Added DESC, Date DESC;
"@
    }
    
    foreach ($queryName in $queries.Keys) {
        $outputFile = Join-Path $queriesDir $queryName
        $queries[$queryName] | Out-File -FilePath $outputFile -Force
        Write-Host "    ✓ Created: $queryName" -ForegroundColor Green
    }
}

# ================================================================
# STEP 3: Copy Key Script Files
# ================================================================
Write-Host "`n[3/6] Copying key script files..." -ForegroundColor Yellow

$scriptMappings = @{
    # Python scripts
    "python_scripts\data_import\pull_sheets_to_sql.py" = "pull_sheets_to_sql.py"
    "python_scripts\data_import\ingest_images_by_id.py" = "ingest_images_by_id.py"
    "python_scripts\data_import\scrape_lonestar_batch.py" = "scrape_lonestar_batch.py"
    "python_scripts\data_import\maxpreps_scraper_db.py" = "maxpreps_scraper_db.py"
    "python_scripts\generate_site_data.py" = "generate_site_data.py"
    "python_scripts\generate_global_data.py" = "generate_global_data.py"
    "python_scripts\generate_latest_season.py" = "generate_latest_season.py"
    
    # PowerShell scripts
    "scripts\run_update_cycle.ps1" = "run_update_cycle.ps1"
    "scripts\GenerateAllPages.ps1" = "GenerateAllPages.ps1"
    "scripts\imported_SQL_json\common-functions.ps1" = "common-functions.ps1"
}

foreach ($source in $scriptMappings.Keys) {
    $sourcePath = Join-Path $RepoRoot $source
    $destPath = Join-Path $scriptsDir $scriptMappings[$source]
    
    if (Test-Path $sourcePath) {
        Copy-Item -Path $sourcePath -Destination $destPath -Force
        Write-Host "  ✓ Copied: $($scriptMappings[$source])" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Not found: $source" -ForegroundColor Yellow
    }
}

# ================================================================
# STEP 4: Create Architecture Documentation
# ================================================================
Write-Host "`n[4/6] Generating architecture documentation..." -ForegroundColor Yellow

$architectureDocs = @{
    "README.md" = @"
# Project Context Documentation

This directory contains comprehensive documentation for McKnight's American Football Rankings project.

## Directory Structure

- **workflows/** - Step-by-step workflow documentation
- **schemas/** - Database table schemas (exported from SQL Server)
- **stored-procedures/** - SQL stored procedure definitions
- **queries/** - Useful SQL query templates
- **scripts/** - Key Python and PowerShell scripts (snapshots)
- **architecture/** - System architecture and design documents

## Quick Links

- [System Overview](architecture/system-overview.md)
- [Data Flow](architecture/data-flow.md)
- [Master Update Cycle](workflows/master-update-cycle.md)

## Notes

- SQL objects are automatically exported from the database
- Script files are snapshots for reference - always use GitHub repo as source of truth
- Documentation generated by: Export-ProjectContext.ps1

**Last Updated:** $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
"@
    
    "system-overview.md" = @"
# System Overview

## Purpose

McKnight's American Football Rankings is a comprehensive database and website tracking high school football team performance, statistics, and historical data from 1869 to present.

## Key Statistics

- **Teams:** 250,000+ team records
- **Games:** 5+ million games
- **Coverage:** 58 states/provinces (including Canada)
- **Time Span:** 1869 - Present (155+ years)

## Technology Stack

### Database
- **Platform:** SQL Server Express (McKnights-PC\SQLEXPRESS01)
- **Database:** hs_football_database
- **Key Tables:** HS_Scores, HS_Team_Names, HS_Rankings, Media_National_Champions

### Data Processing
- **Python 3.x** - Data import, scraping, JSON generation
- **PowerShell 7+** - HTML generation, orchestration
- **Google Sheets** - Collaborative data cleaning interface

### Website
- **Hosting:** GitHub Pages
- **Type:** Static site (HTML/CSS/JavaScript)
- **Framework:** Bootstrap 5
- **Visualization:** Plotly.js
- **Comments:** Giscus (GitHub Discussions)

### External Data Sources
- MaxPreps.com - Modern games (2004+)
- Newspapers.com - Historical research
- LoneStarFootball.net - Texas historical data
- State-specific archives

## Architecture Principles

1. **SQL Server is the single source of truth** - All data flows through SQL
2. **JSON files are the API** - HTML pages consume JSON, not SQL directly
3. **HTML pages are shells** - JavaScript populates templates dynamically
4. **Static site deployment** - No server-side processing required
5. **Git-based workflow** - Version control for code and generated files

## Rating System

Teams are ranked using a coefficient-based combined score incorporating:
- **Margin Component** - Point differential adjusted for competition
- **Win-Loss Component** - Record-based rating
- **Log Score Component** - Logarithmic scoring for extreme performances

The algorithm runs iteratively to stabilize ratings across the entire network of teams and games.

**Generated:** $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
"@
    
    "data-flow.md" = @"
# Data Flow Architecture

## Data Input Sources

### 1. MaxPreps Scraping
- **Frequency:** Weekly during season
- **Coverage:** 2004 - Present
- **Script:** maxpreps_scraper_db.py
- **Target:** HS_Scores table

### 2. Newspaper OCR
- **Source:** Newspapers.com archives
- **Coverage:** 1869 - 2003 (primarily)
- **Process:** Google Cloud Document AI → Manual cleanup → Import
- **Target:** HS_Scores table

### 3. LoneStar Football (Texas)
- **Source:** http://lonestarfootball.net
- **Coverage:** 1902 - 2003
- **Process:** Web scraping → Excel cleanup → Import
- **Target:** HS_Scores_LoneStar_Staging → HS_Scores

### 4. Google Sheets (Team Metadata)
- **Purpose:** Team colors, logos, website URLs
- **Script:** pull_sheets_to_sql.py
- **Target:** HS_Team_Names table

## Data Processing Pipeline

\`\`\`
┌─────────────────────────────────────────────────────────────┐
│                    DATA INPUT SOURCES                        │
├────────────┬──────────────┬──────────────┬─────────────────┤
│  MaxPreps  │  Newspapers  │  LoneStar   │  Google Sheets  │
│  Scraper   │     OCR      │   Scraper   │      Sync       │
└─────┬──────┴──────┬───────┴──────┬───────┴────────┬────────┘
      │             │              │                │
      v             v              v                v
┌─────────────────────────────────────────────────────────────┐
│              SQL SERVER (Source of Truth)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  HS_Scores   │  │HS_Team_Names │  │ HS_Rankings  │     │
│  │ (5M+ games)  │  │ (250K teams) │  │  (Computed)  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
      │
      v
┌─────────────────────────────────────────────────────────────┐
│            PYTHON: JSON GENERATION                           │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ generate_site_data.py     → State JSONs                │ │
│  │ generate_global_data.py   → All-Time/Decade JSONs     │ │
│  │ generate_latest_season.py → Current Season JSON       │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
      │
      v
┌─────────────────────────────────────────────────────────────┐
│          POWERSHELL: HTML GENERATION                         │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ GenerateAllPages.ps1 → Populates templates with data  │ │
│  │   - State pages (58)                                   │ │
│  │   - Decade pages (16)                                  │ │
│  │   - All-time pages                                     │ │
│  │   - Latest season page                                 │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
      │
      v
┌─────────────────────────────────────────────────────────────┐
│               GIT DEPLOYMENT                                 │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ git add . → git commit → git push origin main         │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
      │
      v
┌─────────────────────────────────────────────────────────────┐
│           GITHUB PAGES (Live Website)                        │
│  https://olderdyad.github.io/static-football-rankings/      │
└─────────────────────────────────────────────────────────────┘
\`\`\`

## Master Update Cycle

The entire pipeline is orchestrated by \`run_update_cycle.ps1\`:

1. **Sync** - Pull data from Google Sheets
2. **Images** - Process team logos/helmets
3. **Generate State JSONs** - Create per-state data files
4. **Generate Global JSONs** - Create all-time/decade data files
5. **Generate HTML** - Populate templates
6. **Deploy** - Push to GitHub Pages

**Typical runtime:** 2-5 minutes

**Generated:** $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
"@
}

foreach ($docName in $architectureDocs.Keys) {
    $outputFile = Join-Path (if ($docName -eq "README.md") { $contextRoot } else { $architectureDir }) $docName
    $architectureDocs[$docName] | Out-File -FilePath $outputFile -Force
    Write-Host "  ✓ Created: $docName" -ForegroundColor Green
}

# ================================================================
# STEP 5: Copy Workflow Documentation
# ================================================================
Write-Host "`n[5/6] Organizing workflow documentation..." -ForegroundColor Yellow

$workflowFiles = @(
    "Master_Football_Data_Workflow__2025_Edition_",
    "MaxPreps_Scraping_Workflow",
    "Google_AI_Newspaper_OCR_Workflow",
    "Newspapers.com football Scores OCR workflow",
    "LoneStar_Football_Pre-2004_Data_Import_Workflow",
    "Ambiguous_Opponent_Names_Workflow",
    "SOP__State_Alias_Consolidation_Workflow",
    "End_of_Season_MaxPreps_Workflow",
    "WORKFLOW__Adding_Team_Program_Pages_to_Rating_Tables"
)

# These would be copied from your project files
# Since they're already in the project knowledge, we'll create a reference doc
$workflowIndex = @"
# Workflow Documentation Index

All workflow documentation files are located in this directory.

## Master Workflows

- **Master_Football_Data_Workflow.md** - Overall system workflow
- **master-update-cycle.md** - Complete update pipeline

## Data Collection Workflows

- **MaxPreps_Scraping_Workflow.md** - Modern game scraping (2004+)
- **Newspaper_OCR_Workflow.md** - Historical newspaper processing
- **LoneStar_Import_Workflow.md** - Texas historical data import

## Data Quality Workflows

- **Ambiguous_Opponent_Names.md** - Resolving name conflicts
- **State_Alias_Consolidation.md** - Team name standardization
- **End_of_Season_Procedures.md** - Playoff state handling

## Website Generation

- **Team_Program_Pages.md** - Individual team page creation

## Notes

- Always refer to GitHub repository for latest code
- These workflows document the *process*, not the exact commands
- Update documentation when workflows change

**Generated:** $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
"@

$workflowIndexPath = Join-Path $workflowsDir "README.md"
$workflowIndex | Out-File -FilePath $workflowIndexPath -Force
Write-Host "  ✓ Created workflow index" -ForegroundColor Green

# Create master update cycle doc
$masterCycleDoc = @"
# Master Update Cycle Workflow

## Overview

The master update cycle (\`run_update_cycle.ps1\`) orchestrates the entire data pipeline from source data to live website.

## Prerequisites

- SQL Server running with hs_football_database accessible
- Google Sheets API credentials configured
- Git repository clean (no uncommitted changes)
- Virtual environment activated (for Python scripts)

## Execution

\`\`\`powershell
cd C:\Users\demck\OneDrive\Football_2024\static-football-rankings\scripts
.\run_update_cycle.ps1
\`\`\`

## Pipeline Steps

### Step 1: Data Synchronization
- **Script:** \`pull_sheets_to_sql.py\`
- **Purpose:** Sync team metadata from Google Sheets to SQL
- **Updates:** Colors, logos, websites, mascots
- **Duration:** ~30 seconds

### Step 2: Image Processing
- **Script:** \`ingest_images_by_id.py\`
- **Purpose:** Move team images from drop folder to storage
- **Input:** \`Desktop\HS_Image_Drop\*.{png,jpg}\`
- **Output:** \`OneDrive\Football_2024\HS_Images\*\`
- **Duration:** ~10 seconds

### Step 3: State Data Generation
- **Script:** \`generate_site_data.py\`
- **Purpose:** Create per-state JSON files for teams/programs
- **Output:** \`docs/data/states/*.json\` (58 files)
- **Duration:** ~60 seconds

### Step 4: Global Data Generation
- **Script:** \`generate_global_data.py\`
- **Purpose:** Create all-time and decade ranking JSONs
- **Output:** \`docs/data/all-time/*.json\` + decade files
- **Duration:** ~45 seconds

### Step 5: Latest Season Generation
- **Script:** \`generate_latest_season.py\`
- **Purpose:** Create current season rankings
- **Output:** \`docs/data/latest-teams.json\`
- **Duration:** ~15 seconds

### Step 6: HTML Generation
- **Script:** \`GenerateAllPages.ps1\`
- **Purpose:** Populate HTML templates with JSON data
- **Output:** All HTML files in \`docs/pages/\`
- **Duration:** ~45 seconds

### Step 7: Git Deployment
- **Commands:** \`git add\`, \`git commit\`, \`git push\`
- **Purpose:** Deploy changes to GitHub Pages
- **Duration:** ~30 seconds (depending on network)

## Total Runtime

**Typical:** 3-4 minutes
**With large changes:** 5-8 minutes

## Error Handling

If the script fails at any step:

1. **Check SQL Server connection** - Ensure instance is running
2. **Verify file permissions** - Check OneDrive sync status
3. **Review Python logs** - Check for import errors
4. **Test Git status** - Ensure no conflicts

## Manual Recovery

If a step fails, you can run individual scripts:

\`\`\`powershell
# Data sync only
cd python_scripts\data_import
python pull_sheets_to_sql.py

# JSON generation only
cd python_scripts
python generate_site_data.py
python generate_global_data.py

# HTML only
cd scripts
.\GenerateAllPages.ps1

# Deploy only
git add .
git commit -m "Manual update"
git push origin main
\`\`\`

## Verification

After successful completion:

1. Check GitHub Actions for deployment status
2. Visit live site: https://olderdyad.github.io/static-football-rankings/
3. Verify latest changes appear on relevant pages
4. Test on mobile device if UI changes made

**Generated:** $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
"@

$masterCyclePath = Join-Path $workflowsDir "master-update-cycle.md"
$masterCycleDoc | Out-File -FilePath $masterCyclePath -Force
Write-Host "  ✓ Created master update cycle documentation" -ForegroundColor Green

# ================================================================
# STEP 6: Create Maintenance Script
# ================================================================
Write-Host "`n[6/6] Creating maintenance script..." -ForegroundColor Yellow

$maintenanceScript = @"
# Update-ProjectContext.ps1
# Quick script to re-export SQL objects without regenerating all docs

param(
    [string]`$RepoRoot = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings",
    [string]`$SqlServer = "McKnights-PC\SQLEXPRESS01",
    [string]`$Database = "hs_football_database"
)

`$contextRoot = Join-Path `$RepoRoot "docs\project-context"
`$schemasDir = Join-Path `$contextRoot "schemas"
`$proceduresDir = Join-Path `$contextRoot "stored-procedures"

Write-Host "Updating SQL objects..." -ForegroundColor Cyan

try {
    [System.Reflection.Assembly]::LoadWithPartialName("Microsoft.SqlServer.SMO") | Out-Null
    `$server = New-Object Microsoft.SqlServer.Management.Smo.Server(`$SqlServer)
    `$db = `$server.Databases[`$Database]
    
    # Update stored procedures
    `$procedures = `$db.StoredProcedures | Where-Object { -not `$_.IsSystemObject }
    foreach (`$proc in `$procedures) {
        `$outputFile = Join-Path `$proceduresDir "`$(`$proc.Name).sql"
        `$proc.Script() | Out-File -FilePath `$outputFile -Force
        Write-Host "  Updated: `$(`$proc.Name)" -ForegroundColor Green
    }
    
    Write-Host "`nSQL objects updated successfully!" -ForegroundColor Green
    
} catch {
    Write-Host "Error: `$_" -ForegroundColor Red
}
"@

$maintenancePath = Join-Path $contextRoot "Update-ProjectContext.ps1"
$maintenanceScript | Out-File -FilePath $maintenancePath -Force
Write-Host "  ✓ Created maintenance script" -ForegroundColor Green

# ================================================================
# COMPLETION SUMMARY
# ================================================================
Write-Host "`n================================================================" -ForegroundColor Green
Write-Host "  PROJECT CONTEXT EXPORT COMPLETE" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Location: $contextRoot" -ForegroundColor Cyan
Write-Host ""
Write-Host "Directory Structure:" -ForegroundColor Yellow
Write-Host "  docs/project-context/" -ForegroundColor White
Write-Host "    ├── README.md (index)" -ForegroundColor Gray
Write-Host "    ├── workflows/ (process documentation)" -ForegroundColor Gray
Write-Host "    ├── schemas/ (table definitions)" -ForegroundColor Gray
Write-Host "    ├── stored-procedures/ (SQL procedures)" -ForegroundColor Gray
Write-Host "    ├── queries/ (useful SQL templates)" -ForegroundColor Gray
Write-Host "    ├── scripts/ (code snapshots)" -ForegroundColor Gray
Write-Host "    └── architecture/ (system design docs)" -ForegroundColor Gray
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Review generated documentation" -ForegroundColor White
Write-Host "  2. Add project-context folder to Git:" -ForegroundColor White
Write-Host "       git add docs/project-context" -ForegroundColor Cyan
Write-Host "       git commit -m 'Add project context documentation'" -ForegroundColor Cyan
Write-Host "       git push origin main" -ForegroundColor Cyan
Write-Host "  3. Update Claude project to reference these files" -ForegroundColor White
Write-Host ""
Write-Host "To update SQL objects only:" -ForegroundColor Yellow
Write-Host "  .\docs\project-context\Update-ProjectContext.ps1" -ForegroundColor Cyan
Write-Host ""
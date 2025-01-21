### Update-GenerateAllPages.ps1
### Run this script from the root of your project directory

$ErrorActionPreference = "Stop"

Write-Host "Starting GenerateAllPages.ps1 updates..." -ForegroundColor Cyan

# Get the script path
$scriptPath = Join-Path $PSScriptRoot "GenerateAllPages.ps1"

# Create backup
$backupPath = "$scriptPath.backup"
Copy-Item $scriptPath $backupPath
Write-Host "Created backup at: $backupPath" -ForegroundColor Yellow

# Read the script content
$content = Get-Content $scriptPath -Raw

# 1. Update template base directory path
Write-Host "Updating template base directory path..." -ForegroundColor Yellow
$oldPathPattern = '\$templateBaseDir\s*=\s*Join-Path\s+\$docsDir\s+"pages\\public\\decades\\templates"'
$newPathDefinition = '$templateBaseDir = Join-Path $docsDir "pages\public\templates"'
$content = $content -replace $oldPathPattern, $newPathDefinition

# 2. Update Test-RequiredTemplates function
Write-Host "Updating Test-RequiredTemplates function..." -ForegroundColor Yellow
$newTemplateVerification = @'
function Test-RequiredTemplates {
    $requiredTemplates = @(
        # Decade templates
        @{
            Path = Join-Path $templateBaseDir "decades\decade-teams-template.html"
            Description = "Decade Teams Template"
            Critical = $true
        },
        @{
            Path = Join-Path $templateBaseDir "decades\decade-programs-template.html"
            Description = "Decade Programs Template"
            Critical = $true
        },
        # State templates
        @{
            Path = Join-Path $templateBaseDir "states\state-teams-template.html"
            Description = "State Teams Template"
            Critical = $true
        },
        @{
            Path = Join-Path $templateBaseDir "states\state-programs-template.html"
            Description = "State Programs Template"
            Critical = $true
        },
        # All-time templates
        @{
            Path = Join-Path $templateBaseDir "all-time\all-time-teams-template.html"
            Description = "All-Time Teams Template"
            Critical = $false
        },
        @{
            Path = Join-Path $templateBaseDir "all-time\all-time-programs-template.html"
            Description = "All-Time Programs Template"
            Critical = $false
        },
        # Latest season template
        @{
            Path = Join-Path $templateBaseDir "latest-season\latest-season-template.html"
            Description = "Latest Season Template"
            Critical = $false
        },
        # Index templates
        @{
            Path = Join-Path $templateBaseDir "index\decades-index-template.html"
            Description = "Decades Index Template"
            Critical = $true
        },
        @{
            Path = Join-Path $templateBaseDir "index\states-index-template.html"
            Description = "States Index Template"
            Critical = $true
        },
        @{
            Path = Join-Path $templateBaseDir "index\all-time-index-template.html"
            Description = "All-Time Index Template"
            Critical = $false
        }
    )

    $missingTemplates = @()
    $missingCritical = $false

    Write-Host "Verifying required templates..." -ForegroundColor Yellow
    
    # First ensure template base directory exists
    if (-not (Test-Path $templateBaseDir)) {
        Write-Host "Creating template base directory: $templateBaseDir" -ForegroundColor Yellow
        New-Item -ItemType Directory -Path $templateBaseDir -Force | Out-Null
    }

    # Ensure subdirectories exist
    @("decades", "states", "all-time", "latest-season", "index") | ForEach-Object {
        $subDir = Join-Path $templateBaseDir $_
        if (-not (Test-Path $subDir)) {
            Write-Host "Creating template subdirectory: $subDir" -ForegroundColor Yellow
            New-Item -ItemType Directory -Path $subDir -Force | Out-Null
        }
    }

    foreach ($template in $requiredTemplates) {
        if (-not (Test-Path $template.Path)) {
            $status = if ($template.Critical) { "CRITICAL" } else { "WARNING" }
            $color = if ($template.Critical) { "Red" } else { "Yellow" }
            Write-Host "[$status] Missing $($template.Description): $($template.Path)" -ForegroundColor $color
            
            $missingTemplates += $template
            if ($template.Critical) {
                $missingCritical = $true
            }
        } else {
            Write-Host "[OK] Found $($template.Description)" -ForegroundColor Green
        }
    }

    if ($missingCritical) {
        Write-Warning "Critical templates are missing. Please ensure all required templates are in place."
        return $false
    }

    if ($missingTemplates.Count -gt 0) {
        Write-Warning "Some non-critical templates are missing. Certain features may be limited."
        return $false
    }

    Write-Host "All required templates verified successfully." -ForegroundColor Green
    return $true
}
'@

# Replace the old Test-RequiredTemplates function
$functionPattern = 'function Test-RequiredTemplates \{[\s\S]*?\n\}'
$content = $content -replace $functionPattern, $newTemplateVerification

# 3. Update template paths in Process-DecadeData
Write-Host "Updating Process-DecadeData function paths..." -ForegroundColor Yellow
$content = $content -replace 'Join-Path \$templateBaseDir "decade-(\w+)-template\.html"', 'Join-Path $templateBaseDir "decades\decade-$1-template.html"'

# Write the updated content
Set-Content -Path $scriptPath -Value $content

Write-Host "`nUpdates completed!" -ForegroundColor Green
Write-Host "1. Updated template base directory path"
Write-Host "2. Updated Test-RequiredTemplates function"
Write-Host "3. Updated template paths in Process-DecadeData"
Write-Host "4. Backup created at: $backupPath"
Write-Host "`nPlease review the changes and run GenerateAllPages.ps1 to test."
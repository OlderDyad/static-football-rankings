# Define the root directory of your project
$rootDir = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings"

# Define expected file paths
$expectedFiles = @(
    "$rootDir\css\styles.css"
    "$rootDir\images\football-field-top.jpg"
    "$rootDir\index.html"
    "$rootDir\pages\public\decades\index.html"
    "$rootDir\pages\public\decades\GenerateDecades.ps1"
    "$rootDir\pages\public\decades\decade-template.html"
    "$rootDir\pages\public\decades\index-template.html"
    "$rootDir\docs\js\main.js"
)

# Define expected directories
$expectedDirectories = @(
    "$rootDir\css"
    "$rootDir\images"
    "$rootDir\data\all-time"
    "$rootDir\data\decades\programs"
    "$rootDir\data\decades\teams"
    "$rootDir\data\states"
    "$rootDir\docs\js"
    "$rootDir\pages\public\decades"
)

# Check if each expected file exists
foreach ($file in $expectedFiles) {
    if (Test-Path -Path $file) {
        Write-Host "Found: $file" -ForegroundColor Green
    } else {
        Write-Host "Missing: $file" -ForegroundColor Red
    }
}

# Check if each expected directory exists
foreach ($dir in $expectedDirectories) {
    if (Test-Path -Path $dir -PathType Container) {
        Write-Host "Found Directory: $dir" -ForegroundColor Green
    } else {
        Write-Host "Missing Directory: $dir" -ForegroundColor Red
    }
}

# Check for required placeholders in decade-template.html
$decadeTemplateContent = Get-Content -Path "$rootDir\pages\public\decades\decade-template.html" -Raw
$requiredPlaceholders = @("DECADE_DISPLAY_NAME", "DECADE_NAME", "DECADE_START", "DECADE_END", "DECADE_ID", "TABLE_ROWS")

Write-Host "`nVerifying placeholders in decade-template.html..." -ForegroundColor Yellow
foreach ($placeholder in $requiredPlaceholders) {
    if ($decadeTemplateContent -match $placeholder) {
        Write-Host "Found placeholder: $placeholder" -ForegroundColor Green
    } else {
        Write-Host "Missing placeholder: $placeholder" -ForegroundColor Red
    }
}

# Check for required placeholders in index-template.html
$indexTemplateContent = Get-Content -Path "$rootDir\pages\public\decades\index-template.html" -Raw
$requiredPlaceholders = @("DECADE_CARDS")

Write-Host "`nVerifying placeholders in index-template.html..." -ForegroundColor Yellow
foreach ($placeholder in $requiredPlaceholders) {
    if ($indexTemplateContent -match $placeholder) {
        Write-Host "Found placeholder: $placeholder" -ForegroundColor Green
    } else {
        Write-Host "Missing placeholder: $placeholder" -ForegroundColor Red
    }
}

# Verify that each decade has a corresponding JSON file
$decades = @(
    @{ Name = 'pre1900'; StartYear = 1877; EndYear = 1899; DisplayName = 'Pre-1900s' }
    @{ Name = '1900s'; StartYear = 1900; EndYear = 1909; DisplayName = '1900s' }
    @{ Name = '1910s'; StartYear = 1910; EndYear = 1919; DisplayName = '1910s' }
    @{ Name = '1920s'; StartYear = 1920; EndYear = 1929; DisplayName = '1920s' }
    @{ Name = '1930s'; StartYear = 1930; EndYear = 1939; DisplayName = '1930s' }
    @{ Name = '1940s'; StartYear = 1940; EndYear = 1949; DisplayName = '1940s' }
    @{ Name = '1950s'; StartYear = 1950; EndYear = 1959; DisplayName = '1950s' }
    @{ Name = '1960s'; StartYear = 1960; EndYear = 1969; DisplayName = '1960s' }
    @{ Name = '1970s'; StartYear = 1970; EndYear = 1979; DisplayName = '1970s' }
    @{ Name = '1980s'; StartYear = 1980; EndYear = 1989; DisplayName = '1980s' }
    @{ Name = '1990s'; StartYear = 1990; EndYear = 1999; DisplayName = '1990s' }
    @{ Name = '2000s'; StartYear = 2000; EndYear = 2009; DisplayName = '2000s' }
    @{ Name = '2010s'; StartYear = 2010; EndYear = 2019; DisplayName = '2010s' }
    @{ Name = '2020s'; StartYear = 2020; EndYear = 2029; DisplayName = '2020s' }
)

Write-Host "`nVerifying JSON data files for each decade..." -ForegroundColor Yellow
foreach ($decade in $decades) {
    $jsonFileName = "decade-teams-$($decade.Name).json"
    $jsonFilePath = Join-Path "$rootDir\data\decades\teams" $jsonFileName
    if (Test-Path -Path $jsonFilePath) {
        Write-Host "Found JSON for $($decade.Name): $($jsonFilePath)" -ForegroundColor Green
    } else {
        Write-Host "Missing JSON for $($decade.Name): $($jsonFilePath)" -ForegroundColor Red
    }
}

Write-Host "`nVerification complete." -ForegroundColor Yellow
# Test Configuration
$global:staticDataDir = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\docs\data"

# Test directory structure
$testDirStructure = @{
    "decades" = @{
        "teams" = Join-Path $staticDataDir "decades\teams"
        "programs" = Join-Path $staticDataDir "decades\programs"
    }
}

# Create test directories
Write-Host "Creating test directories..." -ForegroundColor Cyan
foreach ($category in $testDirStructure.Keys) {
    if ($testDirStructure[$category] -is [hashtable]) {
        foreach ($subCategory in $testDirStructure[$category].Keys) {
            $path = $testDirStructure[$category][$subCategory]
            if (!(Test-Path $path)) { 
                New-Item -ItemType Directory -Path $path -Force | Out-Null 
                Write-Host "Created directory: $path" -ForegroundColor Green
            } else {
                Write-Host "Directory already exists: $path" -ForegroundColor Yellow
            }
        }
    }
}

# Test JSON generation with a single decade
$testDecade = @{
    Name = "1990s"
    StartYear = 1990
    EndYear = 1999
    DisplayName = "1990s"
}

# Test data generation
Write-Host "
Testing data generation for $($testDecade.DisplayName)..." -ForegroundColor Cyan

# Generate a test JSON file
$testJsonPath = Join-Path $testDirStructure.decades.teams "decade-teams-$($testDecade.Name).json"
$testData = @{
    metadata = @{
        timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss.fffZ"
        type = "decade-teams"
        yearRange = "$($testDecade.StartYear)-$($testDecade.EndYear)"
        totalItems = 1
        description = "Test data for $($testDecade.DisplayName)"
    }
    items = @(
        @{
            rank = 1
            team = "Test Team"
            season = "$($testDecade.StartYear)"
        }
    )
}

try {
    $testData | ConvertTo-Json -Depth 10 | Set-Content -Path $testJsonPath -Encoding UTF8
    Write-Host "Successfully generated test JSON: $testJsonPath" -ForegroundColor Green
    
    # Verify file exists and contains data
    if (Test-Path $testJsonPath) {
        $content = Get-Content $testJsonPath -Raw
        Write-Host "
File contents preview:"
        Write-Host ($content | Select-Object -First 5) -ForegroundColor Gray
    }
} catch {
    Write-Host "Error generating test JSON: $_" -ForegroundColor Red
}

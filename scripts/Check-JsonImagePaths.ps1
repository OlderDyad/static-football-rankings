# Check-JsonImagePaths.ps1
# This script verifies image paths in JSON files after database updates

$rootDir = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\docs"
$dataDir = Join-Path $rootDir "data"

# Teams with known issues
$teamsToCheck = @(
    "Southlake Carroll (TX)",
    "Jackson Prep (MS)",
    "Katy (TX)",
    "Chandler Hamilton (AZ)",
    "Cincinnati Archbishop Moeller (OH)",
    "Andover Phillips Academy (MA)",
    "Austin Westlake (TX)",
    "Alabaster Thompson (AL)",
    "Everett (WA)"
)

# JSON files to check
$jsonFiles = @(
    "data/decades/programs/programs-2000s.json",
    "data/decades/programs/programs-1990s.json",
    "data/decades/programs/programs-2010s.json",
    "data/states/programs/state-programs-OH.json",
    "data/states/programs/state-programs-AZ.json",
    "data/states/teams/state-teams-NH.json",
    "data/all-time/all-time-teams.json"
)

# Specific page/JSON file pairs to verify
$pagesToCheck = @(
    @{ Page = "pages/public/decades/2000s-programs.html"; DataFile = "data/decades/programs/programs-2000s.json" },
    @{ Page = "pages/public/decades/1990s-programs.html"; DataFile = "data/decades/programs/programs-1990s.json" },
    @{ Page = "pages/public/decades/2010s-programs.html"; DataFile = "data/decades/programs/programs-2010s.json" },
    @{ Page = "pages/public/states/OH-programs.html"; DataFile = "data/states/programs/state-programs-OH.json" },
    @{ Page = "pages/public/states/AZ-programs.html"; DataFile = "data/states/programs/state-programs-AZ.json" },
    @{ Page = "pages/public/states/NH-teams.html"; DataFile = "data/states/teams/state-teams-NH.json" },
    @{ Page = "pages/public/all-time/teams.html"; DataFile = "data/all-time/all-time-teams.json" },
    @{ Page = "pages/public/decades/1920s-teams.html"; DataFile = "data/decades/teams/teams-1920s.json" }
)

Write-Host "Checking JSON files for image paths..." -ForegroundColor Cyan

# Check page meta tags first
Write-Host "`nVerifying HTML page meta tags..." -ForegroundColor Yellow
foreach ($pageInfo in $pagesToCheck) {
    $pagePath = Join-Path $rootDir $pageInfo.Page
    $expected = $pageInfo.DataFile
    
    if (Test-Path $pagePath) {
        $content = Get-Content -Path $pagePath -Raw
        
        if ($content -match '<meta\s+name="data-file"\s+content="([^"]+)"') {
            $actual = $matches[1].TrimStart('/static-football-rankings/')
            
            Write-Host "Page: $($pageInfo.Page)" -ForegroundColor Yellow
            Write-Host "  Expected data file: $expected" -ForegroundColor Yellow
            Write-Host "  Actual data file: $actual" -ForegroundColor Yellow
            
            if ($actual -ne $expected) {
                Write-Host "  MISMATCH: Page is using different data file than expected!" -ForegroundColor Red
            } else {
                Write-Host "  OK: Meta tag matches expected data file" -ForegroundColor Green
            }
        } else {
            Write-Host "Page: $($pageInfo.Page) - No data-file meta tag found" -ForegroundColor Red
        }
    } else {
        Write-Host "Page not found: $pagePath" -ForegroundColor Red
    }
}

# Now check JSON files for each team
Write-Host "`nChecking JSON files for image paths..." -ForegroundColor Yellow

foreach ($jsonFile in $jsonFiles) {
    $jsonPath = Join-Path $rootDir $jsonFile
    
    if (Test-Path $jsonPath) {
        Write-Host "Checking $jsonFile..." -ForegroundColor Yellow
        try {
            $data = Get-Content -Path $jsonPath -Raw | ConvertFrom-Json
            
            # Check topItem for known teams
            if ($data.topItem) {
                $teamName = $data.topItem.team -or $data.topItem.program
                
                if ($teamsToCheck -contains $teamName) {
                    Write-Host "  Found team in topItem: $teamName" -ForegroundColor Green
                    Write-Host "    Logo URL: $($data.topItem.logoURL)" -ForegroundColor Yellow
                    Write-Host "    School Logo URL: $($data.topItem.schoolLogoURL)" -ForegroundColor Yellow
                    
                    # Check for old paths that should have been updated
                    if ($data.topItem.logoURL -like "*fbce2bd4*" -or 
                        $data.topItem.logoURL -like "*5ea6ab6a*" -or
                        $data.topItem.logoURL -like "*/images*" -or
                        $data.topItem.logoURL -like "* *") {
                        Write-Host "    WARNING: Logo URL appears to be using old path!" -ForegroundColor Red
                    }
                    
                    if ($data.topItem.schoolLogoURL -like "*CISD_Secondary*" -or 
                        $data.topItem.schoolLogoURL -like "*Mascot_Logo*" -or
                        $data.topItem.schoolLogoURL -like "*/images*" -or
                        $data.topItem.schoolLogoURL -like "* *") {
                        Write-Host "    WARNING: School Logo URL appears to be using old path!" -ForegroundColor Red
                    }
                }
            }
            
            # Check items array for known teams
            if ($data.items) {
                foreach ($item in $data.items) {
                    $itemName = $item.team -or $item.program
                    
                    if ($teamsToCheck -contains $itemName) {
                        Write-Host "  Found team in items: $itemName" -ForegroundColor Green
                        
                        # Check if the item has logo/school logo properties
                        if ($item.PSObject.Properties.Name -contains 'logoURL') {
                            Write-Host "    Logo URL: $($item.logoURL)" -ForegroundColor Yellow
                            
                            if ($item.logoURL -like "*fbce2bd4*" -or 
                                $item.logoURL -like "*5ea6ab6a*" -or
                                $item.logoURL -like "*/images*" -or
                                $item.logoURL -like "* *") {
                                Write-Host "    WARNING: Logo URL appears to be using old path!" -ForegroundColor Red
                            }
                        } else {
                            Write-Host "    WARNING: Item does not have logoURL property" -ForegroundColor Red
                        }
                        
                        if ($item.PSObject.Properties.Name -contains 'schoolLogoURL') {
                            Write-Host "    School Logo URL: $($item.schoolLogoURL)" -ForegroundColor Yellow
                            
                            if ($item.schoolLogoURL -like "*CISD_Secondary*" -or 
                                $item.schoolLogoURL -like "*Mascot_Logo*" -or
                                $item.schoolLogoURL -like "*/images*" -or
                                $item.schoolLogoURL -like "* *") {
                                Write-Host "    WARNING: School Logo URL appears to be using old path!" -ForegroundColor Red
                            }
                        } else {
                            Write-Host "    WARNING: Item does not have schoolLogoURL property" -ForegroundColor Red
                        }
                    }
                }
            }
            
        } catch {
            Write-Host "  Error parsing JSON file: $_" -ForegroundColor Red
        }
    } else {
        Write-Host "JSON file not found: $jsonPath" -ForegroundColor Red
    }
}

Write-Host "`nJSON file check complete!" -ForegroundColor Cyan
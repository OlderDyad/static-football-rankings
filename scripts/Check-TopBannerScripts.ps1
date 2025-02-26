# Check-TopBannerScripts.ps1
$rootDir = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\docs\pages\public"
$htmlFiles = Get-ChildItem -Path $rootDir -Filter "*.html" -Recurse

$issuesFound = $false

foreach ($file in $htmlFiles) {
    $content = Get-Content $file.FullName -Raw
    
    # Check for proper import
    if ($content -match "import \{ createTeamHeader \}" -or 
        $content -match "teamHeader\.js" -or
        !($content -match "import \{ TopBanner \} from '/static-football-rankings/js/modules/topBanner\.js'")) {
        Write-Host "Issue in file $($file.FullName): Using wrong import or missing TopBanner import" -ForegroundColor Red
        $issuesFound = $true
    }
}

if (-not $issuesFound) {
    Write-Host "All files are using the correct TopBanner import" -ForegroundColor Green
}
# .\generate-all-json-files.ps1

$scriptsDir = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\scripts\imported_SQL_json"

# Array of scripts to run in order
$scripts = @(
    "generate-all-time-programs.ps1",
    "generate-all-time-teams.ps1",
    "generate-decade-programs.ps1",
    "generate-decade-teams.ps1",
    "generate-latest-season-teams.ps1",
    "generate-state-programs.ps1",
    "generate-state-teams.ps1"
)

Write-Host "Starting JSON file generation..." -ForegroundColor Green

foreach ($script in $scripts) {
    $scriptPath = Join-Path $scriptsDir $script
    
    if (Test-Path $scriptPath) {
        Write-Host "`nExecuting $script..." -ForegroundColor Cyan
        try {
            & $scriptPath
            Write-Host "Successfully completed $script" -ForegroundColor Green
        }
        catch {
            Write-Error "Error executing $script : $_"
            Write-Host "Press any key to continue with next script or Ctrl+C to abort..." -ForegroundColor Yellow
            $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
        }
    }
    else {
        Write-Warning "Script not found: $scriptPath"
        Write-Host "Press any key to continue with next script or Ctrl+C to abort..." -ForegroundColor Yellow
        $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
    }
}

Write-Host "`nAll JSON file generation complete!" -ForegroundColor Green
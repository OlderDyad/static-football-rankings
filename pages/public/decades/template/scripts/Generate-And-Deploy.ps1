# Generate-And-Deploy.ps1

# Record start time
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"

try {
    Write-Host "Starting generation process at $timestamp"
    
    # Run generation scripts
    .\UpdateTemplate.ps1
    if ($LASTEXITCODE -ne 0) { throw "UpdateTemplate.ps1 failed" }
    
    .\Create-DecadePages.ps1
    if ($LASTEXITCODE -ne 0) { throw "Create-DecadePages.ps1 failed" }
    
    .\CreateDecadesIndex.ps1
    if ($LASTEXITCODE -ne 0) { throw "CreateDecadesIndex.ps1 failed" }
    
    .\ValidatePages.ps1
    if ($LASTEXITCODE -ne 0) { throw "ValidatePages.ps1 failed" }

    # Git operations
    Push-Location C:\Users\demck\OneDrive\Football_2024\static-football-rankings
    git add .
    git commit -m "Generate new Decade HTML v$timestamp"
    git push origin main
    Pop-Location

    Write-Host "Deployment complete! View at:"
    Write-Host "https://olderdyad.github.io/static-football-rankings/pages/public/decades/index.html"

} catch {
    Write-Error "Process failed: $_"
    exit 1
}
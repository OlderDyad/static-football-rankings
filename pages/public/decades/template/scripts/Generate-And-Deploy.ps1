# Generate-And-Deploy.ps1

# Record start time
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$rootDir = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings"

try {
    Write-Host "Starting generation process at $timestamp"
    
    # Run generation scripts without requiring file checks first
    Write-Host "Running UpdateTemplate.ps1..."
    .\UpdateTemplate.ps1
    if ($LASTEXITCODE -ne 0) { throw "UpdateTemplate.ps1 failed" }
    
    Write-Host "Running Create-DecadePages.ps1..."
    .\Create-DecadePages.ps1
    if ($LASTEXITCODE -ne 0) { throw "Create-DecadePages.ps1 failed" }
    
    Write-Host "Running CreateDecadesIndex.ps1..."
    .\CreateDecadesIndex.ps1
    if ($LASTEXITCODE -ne 0) { throw "CreateDecadesIndex.ps1 failed" }
    
    Write-Host "Running ValidatePages.ps1..."
    .\ValidatePages.ps1
    if ($LASTEXITCODE -ne 0) { throw "ValidatePages.ps1 failed" }

    # Git operations
    Write-Host "Performing Git operations..."
    Push-Location $rootDir
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
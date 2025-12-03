# Fix-TimestampBug.ps1
# Run this script to fix the case-insensitive TIMESTAMP replacement issue
# that breaks the comments section JavaScript code

$filePath = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\scripts\GenerateAllPages.ps1"

Write-Host "Reading GenerateAllPages.ps1..." -ForegroundColor Yellow
$content = Get-Content $filePath -Raw

# Count occurrences before fix
$beforeCount = ([regex]::Matches($content, "-replace 'TIMESTAMP'")).Count
Write-Host "Found $beforeCount occurrences of -replace 'TIMESTAMP'" -ForegroundColor Cyan

# Replace all occurrences of case-insensitive -replace with case-sensitive -creplace
$content = $content -replace "-replace 'TIMESTAMP'", "-creplace 'TIMESTAMP'"

# Save the file
Set-Content -Path $filePath -Value $content -Encoding UTF8

# Count occurrences after fix
$afterContent = Get-Content $filePath -Raw
$afterCount = ([regex]::Matches($afterContent, "-creplace 'TIMESTAMP'")).Count

Write-Host "Converted to $afterCount occurrences of -creplace 'TIMESTAMP'" -ForegroundColor Green
Write-Host ""
Write-Host "Fix applied successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Run GenerateAllPages.ps1 to regenerate all HTML files"
Write-Host "2. Push changes to GitHub"
Write-Host ""
Write-Host "Commands:" -ForegroundColor Cyan
Write-Host "  cd C:\Users\demck\OneDrive\Football_2024\static-football-rankings\scripts"
Write-Host "  .\GenerateAllPages.ps1"
Write-Host "  cd .."
Write-Host "  git add ."
Write-Host '  git commit -m "Fix TIMESTAMP replacement bug breaking comments"'
Write-Host "  git push origin main"
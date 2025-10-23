# Simple encoding checker
param(
    [string]$FilePath = ".\Generate-RegionalStatistics.ps1"
)

Write-Host "Checking file: $FilePath" -ForegroundColor Cyan
Write-Host ""

$content = Get-Content $FilePath -Raw -Encoding UTF8
$lines = $content -split "`n"

$issueCount = 0
for ($i = 0; $i -lt $lines.Count; $i++) {
    $line = $lines[$i]
    $lineNum = $i + 1
    
    # Check for LEFT double quote (U+201C)
    if ($line -match [char]0x201C) {
        Write-Host "Line ${lineNum}: LEFT CURLY QUOTE" -ForegroundColor Red
        Write-Host "  $line" -ForegroundColor Yellow
        $issueCount++
    }
    
    # Check for RIGHT double quote (U+201D)
    if ($line -match [char]0x201D) {
        Write-Host "Line ${lineNum}: RIGHT CURLY QUOTE" -ForegroundColor Red
        Write-Host "  $line" -ForegroundColor Yellow
        $issueCount++
    }
    
    # Check for LEFT single quote (U+2018)
    if ($line -match [char]0x2018) {
        Write-Host "Line ${lineNum}: LEFT CURLY APOSTROPHE" -ForegroundColor Red
        Write-Host "  $line" -ForegroundColor Yellow
        $issueCount++
    }
    
    # Check for RIGHT single quote (U+2019)
    if ($line -match [char]0x2019) {
        Write-Host "Line ${lineNum}: RIGHT CURLY APOSTROPHE" -ForegroundColor Red
        Write-Host "  $line" -ForegroundColor Yellow
        $issueCount++
    }
}

if ($issueCount -eq 0) {
    Write-Host "No curly quote issues found!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "Found $issueCount line(s) with curly quotes" -ForegroundColor Red
    Write-Host "Run fix-encoding-simple.ps1 to fix automatically" -ForegroundColor Yellow
}
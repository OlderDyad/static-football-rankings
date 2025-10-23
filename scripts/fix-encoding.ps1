# Simple encoding fixer
param(
    [string]$FilePath = ".\Generate-RegionalStatistics.ps1"
)

Write-Host "Fixing file: $FilePath" -ForegroundColor Cyan

# Read the file
$content = Get-Content $FilePath -Raw -Encoding UTF8

# Store original for comparison
$originalLength = $content.Length

# Fix LEFT double quote (U+201C) to regular "
$content = $content -replace [char]0x201C, '"'

# Fix RIGHT double quote (U+201D) to regular "
$content = $content -replace [char]0x201D, '"'

# Fix LEFT single quote (U+2018) to regular '
$content = $content -replace [char]0x2018, "'"

# Fix RIGHT single quote (U+2019) to regular '
$content = $content -replace [char]0x2019, "'"

# Fix em dash (U+2014) to regular -
$content = $content -replace [char]0x2014, '-'

# Fix en dash (U+2013) to regular -
$content = $content -replace [char]0x2013, '-'

# Fix non-breaking space (U+00A0) to regular space
$content = $content -replace [char]0x00A0, ' '

# Fix ellipsis (U+2026) to ...
$content = $content -replace [char]0x2026, '...'

# Create backup
$backupPath = $FilePath + ".backup"
Copy-Item $FilePath $backupPath -Force
Write-Host "Backup created: $backupPath" -ForegroundColor Green

# Save fixed content
$content | Set-Content $FilePath -Encoding UTF8 -NoNewline

$newLength = $content.Length
if ($originalLength -ne $newLength) {
    Write-Host "File fixed and saved!" -ForegroundColor Green
    Write-Host "Changed $($originalLength - $newLength) characters" -ForegroundColor Yellow
} else {
    Write-Host "No changes needed!" -ForegroundColor Green
}
# Set paths
$filePath = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\data\all-time-programs-fifty.json"
$cleanFile = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\data\all-time-programs-fifty-clean.json"

# Read the original file
Write-Host "Reading JSON file..."
$content = Get-Content -Path $filePath -Raw
Write-Host "Original file size: $($content.Length) bytes"

# Examine the problematic area
$errorPosition = 4000
$start = [Math]::Max(0, $errorPosition - 10)
$length = 20

Write-Host "`nExamining characters around position $errorPosition..."
Write-Host "Character details from position $start to $($start + $length - 1):"

# Show detailed character information
$content.Substring($start, $length).ToCharArray() | ForEach-Object {
    $charInt = [int]$_
    $hex = '{0:X2}' -f $charInt
    $desc = switch ($charInt) {
        0  { "Null" }
        9  { "Tab" }
        10 { "Line Feed" }
        13 { "Carriage Return" }
        32 { "Space" }
        default { 
            if ($charInt -lt 32) { "Control" }
            else { "Printable" }
        }
    }
    Write-Host "Position $($start + $foreach.Index): [$_] ASCII: $charInt Hex: $hex Type: $desc"
}

# Create cleaned version
Write-Host "`nCreating cleaned version..."
$cleanContent = $content
$cleanContent = $cleanContent -replace '[\x00-\x09\x0B\x0C\x0E-\x1F\x7F]', '' # Remove control chars except LF(10) and CR(13)
$cleanContent = $cleanContent -replace '[\r\n]+', '' # Remove all newlines
$cleanContent = $cleanContent -replace '\\(?!["\\/bfnrt]|u[0-9a-fA-F]{4})', '\\\\' # Escape backslashes
$cleanContent = $cleanContent -replace '\t', ' ' # Replace tabs with spaces

# Save cleaned file
$cleanContent | Set-Content -Path $cleanFile -NoNewline -Encoding UTF8
Write-Host "Cleaned file saved to: $cleanFile"
Write-Host "Cleaned file size: $($cleanContent.Length) bytes"

# Validate JSON
Write-Host "`nValidating cleaned JSON..."
try {
    $null = $cleanContent | ConvertFrom-Json
    Write-Host "JSON validation successful!"
} catch {
    Write-Host "JSON validation failed: $_"
    if ($_.Exception.Message -match "position (\d+)") {
        $pos = [int]$Matches[1]
        $start = [Math]::Max(0, $pos - 10)
        $length = 20
        Write-Host "`nExamining error location..."
        $cleanContent.Substring($start, $length).ToCharArray() | ForEach-Object {
            $charInt = [int]$_
            $hex = '{0:X2}' -f $charInt
            Write-Host "[$_] ASCII: $charInt Hex: $hex"
        }
    }
}
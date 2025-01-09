# examine_json.ps1
$filePath = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\data\all-time-programs-fifty.json"

# Read the file content
$content = Get-Content -Path $filePath -Raw

# Output file size
Write-Host "File size: $($content.Length) bytes"

# Function to show character details
function Show-CharacterDetails {
    param (
        [string]$text,
        [int]$start,
        [int]$length
    )
    
    Write-Host "`nCharacter details from position $start to $($start + $length - 1):"
    $text.Substring($start, $length).ToCharArray() | 
        ForEach-Object {
            $charInt = [int]$_
            $hex = '{0:X2}' -f $charInt
            Write-Host "Character: [$_] ASCII: $charInt Hex: $hex"
        }
}

# Show details around position 4000
$start = [Math]::Max(0, 3990)
$length = 20
Show-CharacterDetails $content $start $length

# Save a clean version of the JSON
$cleanContent = $content -replace "[\x00-\x1F]", ""  # Remove all control characters
$cleanContent = $cleanContent -replace "\\[rn]", ""  # Remove escaped newlines
$cleanContent = $cleanContent -replace "\\/", "/"    # Clean up escaped forward slashes
$cleanContent = $cleanContent -replace "\\\\", "\"   # Clean up double backslashes

# Save cleaned content
$cleanFile = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\data\all-time-programs-fifty-clean.json"
$cleanContent | Set-Content -Path $cleanFile -NoNewline -Encoding UTF8

Write-Host "`nCleaned JSON file saved to: $cleanFile"
Write-Host "Original size: $($content.Length) bytes"
Write-Host "Cleaned size: $($cleanContent.Length) bytes"
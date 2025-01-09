# Set the source and destination directories
$sourceDir = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings"
$destinationDir = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings_backup"

# Create the destination directory if it doesn't exist
if (!(Test-Path $destinationDir)) {
  New-Item -ItemType Directory -Path $destinationDir | Out-Null
  Write-Host "Created backup directory: $destinationDir"
}

# Copy the entire source directory to the destination
Copy-Item -Path $sourceDir -Destination $destinationDir -Recurse -Force

Write-Host "Repository backed up to: $destinationDir"
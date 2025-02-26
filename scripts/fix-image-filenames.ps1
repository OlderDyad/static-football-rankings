# Enhanced script to standardize image files and handle WebP conversion
# Enhanced version of fix-image-filenames.ps1

param(
    [switch]$ConvertWebP = $true # Set to $false to skip WebP conversion
)

$imageRootPath = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\docs\images\Teams"
$sqlUpdateScriptPath = "C:\Users\demck\OneDrive\Football_2024\fix-image-paths.sql"
$logFile = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\scripts\logs\image-fix.log"

# Ensure log directory exists
$logDir = Split-Path $logFile
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

# Start logging
Get-Date | Out-File $logFile
"Starting enhanced image filename cleanup process..." | Tee-Object -FilePath $logFile -Append

# Check if System.Drawing is available (needed for image conversion)
try {
    Add-Type -AssemblyName System.Drawing
    $canConvertImages = $true
    "System.Drawing available for image conversion" | Out-File $logFile -Append
} catch {
    "WARNING: System.Drawing assembly not available. WebP conversion will be skipped." | Tee-Object -FilePath $logFile -Append
    $canConvertImages = $false
    $ConvertWebP = $false
}

# Function to convert WebP to PNG (if possible)
function Convert-WebPToPng {
    param(
        [string]$SourcePath,
        [string]$DestinationPath
    )
    
    try {
        if (-not $canConvertImages) {
            "WARNING: Image conversion not available. Copying file instead." | Out-File $logFile -Append
            Copy-Item -Path $SourcePath -Destination $DestinationPath -Force
            return
        }
        
        # Use System.Drawing to convert image
        $image = [System.Drawing.Image]::FromFile($SourcePath)
        $image.Save($DestinationPath, [System.Drawing.Imaging.ImageFormat]::Png)
        $image.Dispose()
        
        "Converted WebP to PNG: $DestinationPath" | Out-File $logFile -Append
        return $true
    } catch {
        "WARNING: Failed to convert image. Copying file instead: $_" | Out-File $logFile -Append
        Copy-Item -Path $SourcePath -Destination $DestinationPath -Force
        return $false
    }
}

# Function to recursively process directories - enhanced to handle WebP files
function Process-Directory {
    param (
        [string]$dirPath,
        [System.Collections.ArrayList]$sqlUpdates
    )
    
    # Get all files in current directory
    $files = Get-ChildItem -Path $dirPath -File
    
    foreach ($file in $files) {
        $originalName = $file.Name
        $extension = [System.IO.Path]::GetExtension($file.FullName).ToLower()
        $nameWithoutExt = [System.IO.Path]::GetFileNameWithoutExtension($file.FullName)
        
        # Handle WebP files if conversion is enabled
        $needsConversion = ($extension -eq ".webp" -and $ConvertWebP -and $canConvertImages)
        $newExtension = if ($needsConversion) { ".png" } else { $extension }
        
        # Process filename - replace spaces with underscores
        $newNameWithoutExt = $nameWithoutExt -replace ' ', '_'
        $newName = "$newNameWithoutExt$newExtension"
        
        # Only process if the name would change or needs conversion
        if ($originalName -ne $newName -or $needsConversion) {
            $originalPath = $file.FullName
            $newPath = Join-Path -Path $dirPath -ChildPath $newName
            
            "Processing: $originalName -> $newName" | Tee-Object -FilePath $logFile -Append
            
            # If WebP conversion needed
            if ($needsConversion) {
                "Converting WebP to PNG: $originalName" | Tee-Object -FilePath $logFile -Append
                $success = Convert-WebPToPng -SourcePath $originalPath -Destination $newPath
                
                # Delete original WebP after successful conversion
                if ($success -and (Test-Path $newPath)) {
                    Remove-Item -Path $originalPath -Force
                    "Removed original WebP file after conversion: $originalPath" | Out-File $logFile -Append
                }
            } else {
                # Just rename the file
                "Renaming: $originalName -> $newName" | Tee-Object -FilePath $logFile -Append
                Rename-Item -Path $originalPath -NewName $newName -Force
            }
            
            # Generate SQL update statement
            $originalRelativePath = $originalPath.Replace($imageRootPath, "images/Teams").Replace("\", "/")
            $newRelativePath = $newPath.Replace($imageRootPath, "images/Teams").Replace("\", "/")
            
            $sqlLine = "UPDATE HS_Team_Names SET LogoURL = REPLACE(LogoURL, '$originalRelativePath', '$newRelativePath') WHERE LogoURL LIKE '%$originalRelativePath%';"
            $sqlUpdates.Add($sqlLine) | Out-Null
            
            $sqlLine = "UPDATE HS_Team_Names SET School_Logo_URL = REPLACE(School_Logo_URL, '$originalRelativePath', '$newRelativePath') WHERE School_Logo_URL LIKE '%$originalRelativePath%';"
            $sqlUpdates.Add($sqlLine) | Out-Null
        }
    }
    
    # Process subdirectories
    $subdirs = Get-ChildItem -Path $dirPath -Directory
    foreach ($dir in $subdirs) {
        Process-Directory -dirPath $dir.FullName -sqlUpdates $sqlUpdates
    }
}

# Main script
"Starting image filename cleanup process..." | Tee-Object -FilePath $logFile -Append

# Create ArrayList for SQL updates
$sqlUpdates = New-Object System.Collections.ArrayList

# Process all image directories
Process-Directory -dirPath $imageRootPath -sqlUpdates $sqlUpdates

# Write SQL update script
$sqlHeader = @"
-- SQL script to update image paths in database
-- Generated on $(Get-Date)
-- This script updates both LogoURL and School_Logo_URL fields

"@
$sqlUpdates.Insert(0, $sqlHeader)
$sqlUpdates | Out-File -FilePath $sqlUpdateScriptPath -Encoding utf8

"`nDone! Processed $(($sqlUpdates.Count-1)/2) files." | Tee-Object -FilePath $logFile -Append
"SQL update script generated at: $sqlUpdateScriptPath" | Tee-Object -FilePath $logFile -Append
"Please review the SQL script before executing it against your database." | Tee-Object -FilePath $logFile -Append
"To execute, run: sqlcmd -S MCKNIGHTS-PC\SQLEXPRESS01 -d hs_football_database -i `"$sqlUpdateScriptPath`"" | Tee-Object -FilePath $logFile -Append
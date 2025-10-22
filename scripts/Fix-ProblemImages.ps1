# Fix-ProblemImages.ps1
# This script fixes specific image issues found in the database

$rootDir = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\docs"
$imageDir = Join-Path $rootDir "images\Teams"
$sqlUpdateScriptPath = "C:\Users\demck\OneDrive\Football_2024\fix-problem-images.sql"
$logFile = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\scripts\logs\image-fix.log"

# Ensure log directory exists
$logDir = Split-Path $logFile
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

# Start logging
Get-Date | Out-File $logFile
"Starting image fix for problem teams..." | Tee-Object -FilePath $logFile -Append

# Try to load System.Drawing for image conversion
try {
    Add-Type -AssemblyName System.Drawing
    $canConvertImages = $true
    "System.Drawing assembly loaded successfully" | Out-File $logFile -Append
} catch {
    "WARNING: System.Drawing assembly not available. WebP conversion will be limited." | Tee-Object -FilePath $logFile -Append
    $canConvertImages = $false
}

# Define problem teams based on database report
$problemTeams = @(
    @{
        Name = "Southlake Carroll (TX)"
        CurrentLogoURL = "images/Teams/TX/Southlake_Carroll/fbce2bd4-14b1-4d70-affe-b7d2d746a418.webp"
        CurrentSchoolLogoURL = "images/Teams/TX/Southlake_Carroll/CISD_SecondarySeal_CarrollHigh.png"
        NewLogoURL = "images/Teams/TX/Southlake_Carroll/Carroll_Dragons_logo.png"
        NewSchoolLogoURL = "images/Teams/TX/Southlake_Carroll/Carroll_Dragons_school.png"
        PrimaryColor = "Green"
        SecondaryColor = "White"
        Issue = "WebP Format"
    },
    @{
        Name = "Jackson Prep (MS)"
        CurrentLogoURL = "images/Teams/MS/Jackson_Prep/5ea6ab6a-9528-4f3c-9694-fb9c9e0e6257.webp"
        CurrentSchoolLogoURL = "images/Teams/MS/Jackson_Prep/JPprepcrest.png"
        NewLogoURL = "images/Teams/MS/Jackson_Prep/Jackson_Prep_Patriots_logo.png"
        NewSchoolLogoURL = "images/Teams/MS/Jackson_Prep/Jackson_Prep_Patriots_school.png"
        PrimaryColor = "Blue"
        SecondaryColor = "Red"
        Issue = "WebP Format"
    },
    @{
        Name = "Alabaster Thompson (AL)"
        CurrentLogoURL = "images/Teams/AL/Alabaster Thompson/Mascot_Logo.webp"
        CurrentSchoolLogoURL = "images/Teams/AL/Alabaster Thompson/_Thompson_High_School_Logo.png"
        NewLogoURL = "images/Teams/AL/Alabaster_Thompson/Thompson_Warriors_logo.png"
        NewSchoolLogoURL = "images/Teams/AL/Alabaster_Thompson/Thompson_Warriors_school.png"
        PrimaryColor = "Scarlet Red"
        SecondaryColor = "Black"
        Issue = "WebP Format, Spaces in Directory"
    },
    @{
        Name = "Austin Westlake (TX)"
        CurrentLogoURL = "/images/Teams/TX/Austin_Westlake/Austin-Westlake-Chaparrals1-large.png"
        CurrentSchoolLogoURL = "images/Teams/TX/Austin_Westlake/Westlake_HS.jpeg"
        NewLogoURL = "images/Teams/TX/Austin_Westlake/Westlake_Chaparrals_logo.png"
        NewSchoolLogoURL = "images/Teams/TX/Austin_Westlake/Westlake_Chaparrals_school.png"
        PrimaryColor = "Red"
        SecondaryColor = "Blue"
        Issue = "Leading Slash in Path"
    },
    @{
        Name = "Pinson Clay-Chalkville (AL)"
        CurrentLogoURL = "images/Teams/AL/Pinson Clay-Chalkville/Mascot_Logo.png"
        CurrentSchoolLogoURL = "images/Teams/AL/Pinson Clay-Chalkville/School_logo.png"
        NewLogoURL = "images/Teams/AL/Pinson_Clay_Chalkville/Clay_Chalkville_Cougars_logo.png"
        NewSchoolLogoURL = "images/Teams/AL/Pinson_Clay_Chalkville/Clay_Chalkville_Cougars_school.png"
        PrimaryColor = "Navy Blue"
        SecondaryColor = "Silver"
        Issue = "Spaces in Directory"
    },
    @{
        Name = "Chandler Hamilton (AZ)"
        CurrentLogoURL = "images/Teams/AZ/Chandler_Hamilton/Hamilton_High_School_Mascot.jpeg"
        CurrentSchoolLogoURL = "images/Teams/AZ/Chandler_Hamilton/Hamilton-High.png"
        NewLogoURL = "images/Teams/AZ/Chandler_Hamilton/Hamilton_Huskies_logo.png"
        NewSchoolLogoURL = "images/Teams/AZ/Chandler_Hamilton/Hamilton_Huskies_school.png"
        PrimaryColor = "Black"
        SecondaryColor = "Maroon"
        Issue = "Complex Filenames"
    },
    @{
        Name = "Katy (TX)"
        CurrentLogoURL = "images/Teams/TX/Katy/Katy_High_School_Logo.png"
        CurrentSchoolLogoURL = "images/Teams/TX/Katy/gb-logo.png"
        NewLogoURL = "images/Teams/TX/Katy/Katy_Tigers_logo.png"
        NewSchoolLogoURL = "images/Teams/TX/Katy/Katy_Tigers_school.png"
        PrimaryColor = "Red"
        SecondaryColor = "White"
        Issue = "Simple Path Check"
    }
)

# SQL updates
$sqlUpdates = New-Object System.Collections.ArrayList

# Function to convert WebP to PNG
function Convert-WebPToPng {
    param(
        [string]$SourcePath,
        [string]$DestinationPath
    )
    
    try {
        if (-not $canConvertImages) {
            "WARNING: Image conversion not available. Creating placeholder image instead." | Out-File $logFile -Append
            return $false
        }
        
        if (-not (Test-Path $SourcePath)) {
            "WARNING: Source file not found: $SourcePath" | Out-File $logFile -Append
            return $false
        }
        
        # Use System.Drawing to convert image
        $image = [System.Drawing.Image]::FromFile($SourcePath)
        $image.Save($DestinationPath, [System.Drawing.Imaging.ImageFormat]::Png)
        $image.Dispose()
        
        "Converted image: $SourcePath -> $DestinationPath" | Out-File $logFile -Append
        return $true
    } catch {
        "ERROR: Failed to convert image: $_" | Out-File $logFile -Append
        return $false
    }
}

# Function to create placeholder image
function Create-PlaceholderImage {
    param(
        [string]$OutputPath,
        [string]$TeamName,
        [string]$PrimaryColor,
        [string]$Type = "logo" # "logo" or "school"
    )
    
    try {
        if (-not $canConvertImages) {
            "WARNING: System.Drawing not available. Cannot create placeholder image." | Out-File $logFile -Append
            return $false
        }
        
        # Create directory if it doesn't exist
        $directory = Split-Path -Path $OutputPath -Parent
        if (-not (Test-Path $directory)) {
            New-Item -ItemType Directory -Path $directory -Force | Out-Null
            "Created directory: $directory" | Out-File $logFile -Append
        }
        
        # Parse color (handle named colors too)
        $colorObj = switch ($PrimaryColor.ToLower()) {
            "blue" { [System.Drawing.Color]::Blue }
            "red" { [System.Drawing.Color]::Red }
            "green" { [System.Drawing.Color]::Green }
            "navy blue" { [System.Drawing.Color]::Navy }
            "scarlet red" { [System.Drawing.Color]::Firebrick }
            "black" { [System.Drawing.Color]::Black }
            "maroon" { [System.Drawing.Color]::Maroon }
            default { 
                try {
                    if ($PrimaryColor.StartsWith("#")) {
                        $r = [Convert]::ToInt32($PrimaryColor.Substring(1, 2), 16)
                        $g = [Convert]::ToInt32($PrimaryColor.Substring(3, 2), 16)
                        $b = [Convert]::ToInt32($PrimaryColor.Substring(5, 2), 16)
                        [System.Drawing.Color]::FromArgb($r, $g, $b)
                    } else {
                        [System.Drawing.Color]::Navy # Default to navy if parsing fails
                    }
                }
                catch {
                    [System.Drawing.Color]::Navy # Default if parsing fails
                }
            }
        }
        
        # Create image
        $bitmap = New-Object System.Drawing.Bitmap 300, 300
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $graphics.Clear($colorObj)
        
        # Add text
        $teamDisplayName = $TeamName.Split('(')[0].Trim()
        if ($Type -eq "logo") {
            $text = "${teamDisplayName}"
        } else {
            $text = "${teamDisplayName} School"
        }
        
        $brush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::White)
        $font = New-Object System.Drawing.Font("Arial", 20, [System.Drawing.FontStyle]::Bold)
        $stringFormat = New-Object System.Drawing.StringFormat
        $stringFormat.Alignment = [System.Drawing.StringAlignment]::Center
        $stringFormat.LineAlignment = [System.Drawing.StringAlignment]::Center
        $rect = New-Object System.Drawing.RectangleF(0, 0, 300, 300)
        
        $graphics.DrawString($text, $font, $brush, $rect, $stringFormat)
        
        # Save the image
        $bitmap.Save($OutputPath, [System.Drawing.Imaging.ImageFormat]::Png)
        $graphics.Dispose()
        $bitmap.Dispose()
        
        "Created placeholder image: $OutputPath" | Out-File $logFile -Append
        return $true
    } catch {
        "ERROR: Failed to create placeholder image: $_" | Out-File $logFile -Append
        return $false
    }
}

# Process each team
foreach ($team in $problemTeams) {
    "Processing team: $($team.Name) - Issue: $($team.Issue)" | Tee-Object -FilePath $logFile -Append
    
    # Normalize paths
    $currentLogoPath = $team.CurrentLogoURL.TrimStart('/')
    $currentSchoolLogoPath = $team.CurrentSchoolLogoURL.TrimStart('/')
    
    # Full paths in the file system
    $logoFullPath = Join-Path $rootDir $currentLogoPath
    $schoolLogoFullPath = Join-Path $rootDir $currentSchoolLogoPath
    $newLogoFullPath = Join-Path $rootDir $team.NewLogoURL
    $newSchoolLogoFullPath = Join-Path $rootDir $team.NewSchoolLogoURL
    
    # Create directories if they don't exist
    $newLogoDir = Split-Path -Path $newLogoFullPath -Parent
    $newSchoolLogoDir = Split-Path -Path $newSchoolLogoFullPath -Parent
    
    if (-not (Test-Path $newLogoDir)) {
        New-Item -ItemType Directory -Path $newLogoDir -Force | Out-Null
        "Created directory: $newLogoDir" | Out-File $logFile -Append
    }
    
    if (-not (Test-Path $newSchoolLogoDir)) {
        New-Item -ItemType Directory -Path $newSchoolLogoDir -Force | Out-Null
        "Created directory: $newSchoolLogoDir" | Out-File $logFile -Append
    }
    
    # Process logo
    $logoSuccess = $false
    if (Test-Path $logoFullPath) {
        "Found logo: $logoFullPath" | Out-File $logFile -Append
        
        # Get file extension
        $extension = [System.IO.Path]::GetExtension($logoFullPath).ToLower()
        
        if ($extension -eq ".webp") {
            # Convert WebP to PNG
            $logoSuccess = Convert-WebPToPng -SourcePath $logoFullPath -DestinationPath $newLogoFullPath
        } else {
            # Copy and standardize other image formats
            try {
                Copy-Item -Path $logoFullPath -Destination $newLogoFullPath -Force
                $logoSuccess = $true
                "Copied logo: $logoFullPath -> $newLogoFullPath" | Out-File $logFile -Append
            } catch {
                "ERROR: Failed to copy logo: $_" | Out-File $logFile -Append
            }
        }
    } else {
        "WARNING: Logo not found: $logoFullPath" | Out-File $logFile -Append
    }
    
    # Create placeholder if needed
    if (-not $logoSuccess) {
        "Creating placeholder logo for: $($team.Name)" | Out-File $logFile -Append
        Create-PlaceholderImage -OutputPath $newLogoFullPath -TeamName $team.Name -PrimaryColor $team.PrimaryColor -Type "logo"
    }
    
    # Process school logo
    $schoolLogoSuccess = $false
    if (Test-Path $schoolLogoFullPath) {
        "Found school logo: $schoolLogoFullPath" | Out-File $logFile -Append
        
        # Get file extension
        $extension = [System.IO.Path]::GetExtension($schoolLogoFullPath).ToLower()
        
        if ($extension -eq ".webp") {
            # Convert WebP to PNG
            $schoolLogoSuccess = Convert-WebPToPng -SourcePath $schoolLogoFullPath -DestinationPath $newSchoolLogoFullPath
        } else {
            # Copy and standardize other image formats
            try {
                Copy-Item -Path $schoolLogoFullPath -Destination $newSchoolLogoFullPath -Force
                $schoolLogoSuccess = $true
                "Copied school logo: $schoolLogoFullPath -> $newSchoolLogoFullPath" | Out-File $logFile -Append
            } catch {
                "ERROR: Failed to copy school logo: $_" | Out-File $logFile -Append
            }
        }
    } else {
        "WARNING: School logo not found: $schoolLogoFullPath" | Out-File $logFile -Append
    }
    
    # Create placeholder if needed
    if (-not $schoolLogoSuccess) {
        "Creating placeholder school logo for: $($team.Name)" | Out-File $logFile -Append
        Create-PlaceholderImage -OutputPath $newSchoolLogoFullPath -TeamName $team.Name -PrimaryColor $team.PrimaryColor -Type "school"
    }
    
    # Generate SQL updates
    $sqlLine = "UPDATE HS_Team_Names SET LogoURL = '$($team.NewLogoURL)' WHERE Team_Name = '$($team.Name)';"
    $sqlUpdates.Add($sqlLine) | Out-Null
    
    $sqlLine = "UPDATE HS_Team_Names SET School_Logo_URL = '$($team.NewSchoolLogoURL)' WHERE Team_Name = '$($team.Name)';"
    $sqlUpdates.Add($sqlLine) | Out-Null
    
    "Finished processing team: $($team.Name)" | Out-File $logFile -Append
}

# Write SQL update script
if ($sqlUpdates.Count -gt 0) {
    $sqlHeader = @"
-- SQL script to update team image paths
-- Generated on $(Get-Date)
-- This script fixes image paths for teams with loading issues

"@
    $sqlUpdates.Insert(0, $sqlHeader)
    $sqlUpdates | Out-File -FilePath $sqlUpdateScriptPath -Encoding utf8
    
    "SQL update script generated at: $sqlUpdateScriptPath" | Tee-Object -FilePath $logFile -Append
    "To execute, run: sqlcmd -S MCKNIGHTS-PC\SQLEXPRESS01 -d hs_football_database -i `"$sqlUpdateScriptPath`"" | Tee-Object -FilePath $logFile -Append
} else {
    "No SQL updates needed" | Tee-Object -FilePath $logFile -Append
}

"Image fix process complete!" | Tee-Object -FilePath $logFile -Append
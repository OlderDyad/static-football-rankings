# Define paths and connection string
$logFile = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\scripts\imported_SQL_json\logs\media-national-champions.log"
$outputDir = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\docs\data\media-national-champions"
$connectionString = "Server=MCKNIGHTS-PC\SQLEXPRESS01;Database=hs_football_database;Trusted_Connection=True;TrustServerCertificate=True"

# Ensure directories exist and clear old files
New-Item -ItemType Directory -Force -Path (Split-Path $logFile) | Out-Null
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
Remove-Item "$outputDir\media-national-champions.json" -ErrorAction SilentlyContinue

# Start logging
Get-Date | Out-File $logFile
"Starting Media National Champions generation" | Tee-Object -FilePath $logFile -Append

# Import common functions
. ".\common-functions.ps1"

# Helper function to safely parse decimal values
function Parse-DecimalSafe {
    param (
        [Parameter(Mandatory=$false)]
        [object]$Value,
        [decimal]$DefaultValue = 0
    )
    
    try {
        if ($null -eq $Value -or [string]::IsNullOrWhiteSpace("$Value")) {
            return $DefaultValue
        }
        return [decimal]::Parse("$Value")
    }
    catch {
        "Warning: Could not parse value '$Value' to decimal, using default value $DefaultValue" | Tee-Object -FilePath $logFile -Append
        return $DefaultValue
    }
}

# Helper function to safely parse integer values
function Parse-IntSafe {
    param (
        [Parameter(Mandatory=$false)]
        [object]$Value,
        [int]$DefaultValue = 0
    )
    
    try {
        if ($null -eq $Value -or [string]::IsNullOrWhiteSpace("$Value")) {
            return $DefaultValue
        }
        return [int]::Parse("$Value")
    }
    catch {
        "Warning: Could not parse value '$Value' to integer, using default value $DefaultValue" | Tee-Object -FilePath $logFile -Append
        return $DefaultValue
    }
}

try {
    # Connect to the database
    $connection = Connect-Database
    Write-Host "Database connection established"
    
    # Execute SQL query to get media national champions
    Write-Host "Processing Media National Champions..."
    $command = New-Object System.Data.SqlClient.SqlCommand("EXEC Get_Media_National_Champions", $connection)
    $adapter = New-Object System.Data.SqlClient.SqlDataAdapter($command)
    $championsDataset = New-Object System.Data.DataSet
    $adapter.Fill($championsDataset)

    if ($championsDataset.Tables.Count -gt 0 -and $championsDataset.Tables[0].Rows.Count -gt 0) {
        $championsTable = $championsDataset.Tables[0]
        Write-Host $championsTable.Rows.Count
        Write-Host "Retrieved $($championsTable.Rows.Count) Media National Champions"

        # Sort champions by combined score (descending) if available
        $sortedChampions = @($championsTable.Rows)
        
        # Create a sorted list with NULL combined scores last
        $sortedChampions = $sortedChampions | Sort-Object {
            if ($null -eq $_.combined -or [string]::IsNullOrWhiteSpace($_.combined)) {
                [decimal]::MinValue  # Put rows with no combined score at the end
            } else {
                try {
                    [decimal]::Parse("$($_.combined)")
                } catch {
                    [decimal]::MinValue
                }
            }
        } -Descending

        # Get the top champion by combined score for the banner
        $topChampion = $null
        foreach ($row in $sortedChampions) {
            if ($null -ne $row["combined"] -and -not [string]::IsNullOrWhiteSpace($row["combined"])) {
                $topChampion = $row
                break
            }
        }

        # If no champion has a combined score, use the most recent one
        if ($null -eq $topChampion) {
            $topChampion = ($championsTable.Rows | Sort-Object -Property year -Descending)[0]
        }

        # Get metadata for the top champion
        Write-Host "Fetching metadata for: $($topChampion["team"])"
        $topTeamName = $topChampion["team"]
        $metadata = Get-TeamMetadata -connection $connection -TeamName $topTeamName -isProgram $false
        Write-Host "Metadata fetched for: $topTeamName"
        
        # Convert DataTable to array of objects
        $champions = @()
        foreach ($row in $championsTable.Rows) {
            $champion = [ordered]@{
                year = $row["year"]
                team = $row["team"]
                state = $row["state"]
                combined = Parse-DecimalSafe -Value $row["combined"]
                margin = Parse-DecimalSafe -Value $row["margin"]
                win_loss = Parse-DecimalSafe -Value $row["win_loss"]
                offense = Parse-DecimalSafe -Value $row["offense"]
                defense = Parse-DecimalSafe -Value $row["defense"]
                games_played = Parse-IntSafe -Value $row["games_played"]
                source = $row["source"]
                record = $row["record"]
                logoURL = $row["logoURL"]
                schoolLogoURL = $row["schoolLogoURL"]
                backgroundColor = $row["backgroundColor"]
                textColor = $row["textColor"]
                mascot = $row["mascot"]
            }
            $champions += $champion
        }
        
        # Sort by combined score (descending)
        $champions = $champions | Sort-Object combined -Descending


# In Generate-MediaNationalChampions.ps1, replace the topChampionObj creation with this:
$topChampionObj = [PSCustomObject]@{
    year = $topChampion["year"]
    team = $topChampion["team"] 
    state = $topChampion["state"]
    combined = Parse-DecimalSafe -Value $topChampion["combined"]
    margin = Parse-DecimalSafe -Value $topChampion["margin"]
    win_loss = Parse-DecimalSafe -Value $topChampion["win_loss"]
    offense = Parse-DecimalSafe -Value $topChampion["offense"]
    defense = Parse-DecimalSafe -Value $topChampion["defense"]
    games_played = Parse-IntSafe -Value $topChampion["games_played"]
    source = $topChampion["source"]
    record = $topChampion["record"]
    logoURL = $topChampion["logoURL"]
    schoolLogoURL = $topChampion["schoolLogoURL"]
    backgroundColor = $topChampion["backgroundColor"] 
    textColor = $topChampion["textColor"]
    mascot = $topChampion["mascot"]
}

# Instead of trying to merge metadata, directly set key values:
if ($metadata -and $metadata.PrimaryColor) {
    $topChampionObj.backgroundColor = $metadata.PrimaryColor
}
if ($metadata -and $metadata.SecondaryColor) {
    $topChampionObj.textColor = $metadata.SecondaryColor
}
if ($metadata -and $metadata.LogoURL) {
    $topChampionObj.logoURL = $metadata.LogoURL
}
if ($metadata -and $metadata.School_Logo_URL) {
    $topChampionObj.schoolLogoURL = $metadata.School_Logo_URL
}
if ($metadata -and $metadata.Mascot) {
    $topChampionObj.mascot = $metadata.Mascot
}

        # Create JSON structure
        $jsonData = @{
            topItem = $topChampionObj
            items = $champions
            metadata = @{
                timestamp = (Get-Date).ToString("o")
                type = "media-national-champions"
                yearRange = "all-time"
                totalItems = $champions.Count
                description = "Media National Champions"
            }
        }

        # Write JSON data to file
        $outputPath = Join-Path $outputDir "media-national-champions.json"
        $jsonData | ConvertTo-Json -Depth 10 | Set-Content -Path $outputPath -Force
        Write-Host "File written: $outputPath"
        Write-Host "File last modified: $(Get-Item $outputPath).LastWriteTime"

        # Log success
        "File generated: $outputPath" | Tee-Object -FilePath $logFile -Append
    } else {
        Write-Host "No Media National Champions data available in the dataset" -ForegroundColor Yellow
        "No Media National Champions data available in the dataset" | Tee-Object -FilePath $logFile -Append
    }
}
catch {
    Write-Host "Error: $_" -ForegroundColor Red
    "Error: $_" | Tee-Object -FilePath $logFile -Append
}
finally {
    if ($connection -and $connection.State -eq 'Open') {
        $connection.Close()
        Write-Host "Database connection closed"
    }
}

"Media National Champions generation complete" | Tee-Object -FilePath $logFile -Append
# Define paths and connection string
$logFile = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\scripts\imported_SQL_json\logs\mcknight-national-champions.log"
$outputDir = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\docs\data\mcknight-national-champions"
# $connectionString is handled by Connect-Database in common-functions

# Ensure directories exist and clear old files
New-Item -ItemType Directory -Force -Path (Split-Path $logFile) | Out-Null
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
Remove-Item "$outputDir\mcknight-national-champions.json" -ErrorAction SilentlyContinue

# Start logging
Get-Date | Out-File $logFile
"Starting McKnight National Champions generation" | Tee-Object -FilePath $logFile -Append

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

    # Execute SQL query to get McKnight national champions
    Write-Host "Processing McKnight National Champions..."
    $command = New-Object System.Data.SqlClient.SqlCommand("EXEC dbo.Get_McKnight_National_Champions", $connection)
    $adapter = New-Object System.Data.SqlClient.SqlDataAdapter($command)
    $dataset = New-Object System.Data.DataSet
    $adapter.Fill($dataset)

    if ($dataset.Tables.Count -gt 0 -and $dataset.Tables[0].Rows.Count -gt 0) {
        $championsTable = $dataset.Tables[0]
        Write-Host "Retrieved $($championsTable.Rows.Count) McKnight National Champions"

        # Convert DataTable to array of objects and ensure proper data types
        $champions = @()
        foreach ($row in $championsTable.Rows) {
            
            # --- PHASE 4: LINK GENERATION LOGIC ---
            $linkHtml = ""
            
            # Check if Has_Team_Page column exists (in case SQL wasn't updated yet)
            if ($championsTable.Columns.Contains("Has_Team_Page") -and $row["Has_Team_Page"] -eq 1 -and -not [string]::IsNullOrEmpty($row["Team_Page_URL"])) {
                # Page Exists: Blue Link Icon
                $url = $row["Team_Page_URL"]
                $linkHtml = "<a href='$url' class='team-link icon-only' title='View Team Page'><i class='fas fa-external-link-alt'></i></a>"
            } else {
                # No Page: Gray Square
                $linkHtml = "<span class='no-page-icon' title='Page coming soon'>&#9633;</span>"
            }
            # --------------------------------------

            $champion = [PSCustomObject]@{
                year = $row["year"]
                team = $row["team"]
                state = $row["state"]
                record = $row["Record"] # Explicitly adding Record
                sources = $row["Sources"] # Explicitly adding Sources
                combined = Parse-DecimalSafe -Value $row["combined"]
                margin = Parse-DecimalSafe -Value $row["margin"]
                win_loss = Parse-DecimalSafe -Value $row["win_loss"]
                offense = Parse-DecimalSafe -Value $row["offense"]
                defense = Parse-DecimalSafe -Value $row["defense"]
                games_played = Parse-IntSafe -Value $row["games_played"]
                
                logoURL = $row["logoURL"]
                schoolLogoURL = $row["schoolLogoURL"]
                backgroundColor = $row["backgroundColor"]
                textColor = $row["textColor"]
                mascot = $row["mascot"]
                
                # Add the generated HTML to the JSON object
                teamLinkHtml = $linkHtml
            }
            $champions += $champion
        }

        # Get most recent champion for the topItem
        $mostRecentYear = ($champions | Sort-Object -Property year -Descending)[0].year
        $topChampion = $champions | Where-Object { $_.year -eq $mostRecentYear }

        # Create JSON structure with champions sorted by year
        $jsonData = @{
            topItem = $topChampion
            items = $champions
            metadata = @{
                timestamp = (Get-Date).ToString("o")
                type = "mcknight-national-champions"
                yearRange = "all-time"
                totalItems = $champions.Count
                description = "McKnight's American Football National Champions"
            }
        }

        # Write JSON data to file
        $outputPath = Join-Path $outputDir "mcknight-national-champions.json"
        # Increased depth to ensure objects serialize correctly
        $jsonString = ConvertTo-Json -InputObject $jsonData -Depth 10 
        [System.IO.File]::WriteAllText($outputPath, $template, [System.Text.UTF8Encoding]::new($false))

        Write-Host "File written: $outputPath"
        Write-Host "File last modified: $(Get-Item $outputPath).LastWriteTime"

        # Log success
        "File generated: $outputPath" | Tee-Object -FilePath $logFile -Append
    } else {
        Write-Host "No McKnight National Champions data available in the dataset" -ForegroundColor Yellow
        "No McKnight National Champions data available in the dataset" | Tee-Object -FilePath $logFile -Append
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

"McKnight National Champions generation complete" | Tee-Object -FilePath $logFile -Append
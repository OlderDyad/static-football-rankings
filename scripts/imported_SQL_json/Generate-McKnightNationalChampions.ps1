# Generate-McKnightNationalChampions.ps1
# UPDATED: Uses snake_case field names to match All-Time Teams
# UPDATED: Fixed link field names (hasTeamPage, teamPageUrl)

# Define paths and connection string
$logFile = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\scripts\imported_SQL_json\logs\mcknight-national-champions.log"
$outputDir = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\docs\data\mcknight-national-champions"

# Ensure directories exist and clear old files
New-Item -ItemType Directory -Force -Path (Split-Path $logFile) | Out-Null
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
Remove-Item "$outputDir\mcknight-national-champions.json" -ErrorAction SilentlyContinue

# Start logging
Get-Date | Out-File $logFile
"Starting McKnight National Champions generation (SNAKE_CASE VERSION)" | Tee-Object -FilePath $logFile -Append

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

try {
    # Connect to the database
    $connection = Connect-Database
    Write-Host "Database connection established"

    # Execute stored procedure (FIXED: removed sp_ prefix)
    Write-Host "Processing McKnight National Champions (Rating-based)..."
    $command = New-Object System.Data.SqlClient.SqlCommand("EXEC dbo.Get_McKnight_National_Champions", $connection)
    $adapter = New-Object System.Data.SqlClient.SqlDataAdapter($command)
    $dataset = New-Object System.Data.DataSet
    $adapter.Fill($dataset)

    if ($dataset.Tables.Count -gt 0 -and $dataset.Tables[0].Rows.Count -gt 0) {
        $championsTable = $dataset.Tables[0]
        Write-Host "Retrieved $($championsTable.Rows.Count) McKnight National Champions"

        # Convert DataTable to array of objects
        $champions = @()
        foreach ($row in $championsTable.Rows) {
            
            # Generate link HTML (FIXED: using hasTeamPage and teamPageUrl)
            $linkHtml = ""
            if ($row["HasTeamPage"] -eq 1 -and -not [string]::IsNullOrEmpty($row["TeamPageUrl"])) {
                $url = $row["TeamPageUrl"]
                $linkHtml = "<a href='$url' class='team-link' title='View Team Page'><i class='fas fa-external-link-alt'></i></a>"
            } else {
                $linkHtml = "<span class='no-page-icon' style='color:#ddd;' title='Page coming soon'>&#9633;</span>"
            }
            
            # CRITICAL: Use SNAKE_CASE to match All-Time Teams JSON structure
            $champion = [PSCustomObject]@{
                year = $row["year"]
                team = $row["team"]
                state = $row["state"]
                record = $row["record"]
                wins = $row["wins"]
                losses = $row["losses"]
                ties = $row["ties"]
                combined = Parse-DecimalSafe -Value $row["combined"]
                margin = Parse-DecimalSafe -Value $row["margin"]
                win_loss = Parse-DecimalSafe -Value $row["win_loss"]      # SNAKE_CASE!
                offense = Parse-DecimalSafe -Value $row["offense"]
                defense = Parse-DecimalSafe -Value $row["defense"]
                games_played = $row["games_played"]                       # SNAKE_CASE!
                
                logoURL = $row["logoURL"]
                schoolLogoURL = $row["schoolLogoURL"]
                backgroundColor = $row["backgroundColor"]
                textColor = $row["textColor"]
                mascot = $row["mascot"]
                
                teamId = $row["teamId"]
                hasTeamPage = [bool]$row["HasTeamPage"]
                teamPageUrl = $row["TeamPageUrl"]
                teamLinkHtml = $linkHtml
            }
            $champions += $champion
        }

        # Get most recent champion for topItem
        $mostRecentYear = ($champions | Sort-Object -Property year -Descending)[0].year
        $topChampion = $champions | Where-Object { $_.year -eq $mostRecentYear }

        # Create JSON structure
        $jsonData = @{
            topItem = $topChampion
            items = $champions
            metadata = @{
                timestamp = (Get-Date).ToString("o")
                type = "mcknight-national-champions"
                description = "McKnight's National Champions (Rating-Based)"
                totalItems = $champions.Count
                source = "HS_Rankings"
            }
        }

        # Write JSON data to file
        $outputPath = Join-Path $outputDir "mcknight-national-champions.json"
        $jsonString = ConvertTo-Json -InputObject $jsonData -Depth 10 
        Set-Content -Path $outputPath -Value $jsonString -Encoding UTF8

        Write-Host "File written: $outputPath"
        Write-Host "Total champions: $($champions.Count)"
        "File generated: $outputPath" | Tee-Object -FilePath $logFile -Append
        "Total champions: $($champions.Count)" | Tee-Object -FilePath $logFile -Append
    } else {
        Write-Host "No McKnight National Champions data available" -ForegroundColor Yellow
        "No data available" | Tee-Object -FilePath $logFile -Append
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
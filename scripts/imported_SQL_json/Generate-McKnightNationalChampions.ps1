# Generate-McKnightNationalChampions.ps1
# Generates JSON data for McKnight's National Champions page
# Based on all-time teams structure

$logFile = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\scripts\imported_SQL_json\logs\mcknight-national-champions.log"
$outputDir = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\docs\data\mcknight-national-champions"

# Setup directories
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
        return $DefaultValue
    }
}

try {
    # Connect to the database
    $connection = Connect-Database
    Write-Host "Database connection established"

    # Execute stored procedure to get McKnight National Champions
    Write-Host "Processing McKnight National Champions..."
    $command = New-Object System.Data.SqlClient.SqlCommand("EXEC dbo.Get_McKnight_National_Champions", $connection)
    $adapter = New-Object System.Data.SqlClient.SqlDataAdapter($command)
    $dataset = New-Object System.Data.DataSet
    $adapter.Fill($dataset)

    if ($dataset.Tables.Count -gt 0 -and $dataset.Tables[0].Rows.Count -gt 0) {
        $championsTable = $dataset.Tables[0]
        Write-Host "Retrieved $($championsTable.Rows.Count) McKnight National Champions"

        # Convert DataTable to array of objects matching all-time teams structure
        $champions = @()
        foreach ($row in $championsTable.Rows) {
            
            $champion = [PSCustomObject]@{
                year = $row["year"]
                team = $row["team"]
                state = $row["state"]
                combined = Parse-DecimalSafe -Value $row["combined"]
                margin = Parse-DecimalSafe -Value $row["margin"]
                win_loss = Parse-DecimalSafe -Value $row["win_loss"]
                offense = Parse-DecimalSafe -Value $row["offense"]
                defense = Parse-DecimalSafe -Value $row["defense"]
                games_played = $row["games_played"]
                logoURL = $row["logoURL"]
                schoolLogoURL = $row["schoolLogoURL"]
                backgroundColor = $row["backgroundColor"]
                textColor = $row["textColor"]
                mascot = $row["mascot"]
                teamId = $row["teamId"]
                hasTeamPage = [bool]$row["HasTeamPage"]
                teamPageUrl = $row["TeamPageUrl"]
            }
            $champions += $champion
        }

        # Get most recent champion (top item) for banner
        $topChampion = $champions | Sort-Object -Property year -Descending | Select-Object -First 1

        # Build JSON structure matching all-time teams format
        $jsonData = @{
            topItem = $topChampion
            items = $champions
            metadata = @{
                timestamp = (Get-Date).ToString("o")
                type = "mcknight-national-champions"
                description = "McKnight's National Champions by Combined Rating"
                totalItems = $champions.Count
            }
        }

        # Write JSON to file
        $outputPath = Join-Path $outputDir "mcknight-national-champions.json"
        $jsonString = ConvertTo-Json -InputObject $jsonData -Depth 10
        Set-Content -Path $outputPath -Value $jsonString -Encoding UTF8

        Write-Host "✓ Successfully wrote $($champions.Count) champions to JSON"
        Write-Host "✓ Teams with pages: $(($champions | Where-Object { $_.hasTeamPage }).Count)"
        "File generated: $outputPath" | Tee-Object -FilePath $logFile -Append
    }
    else {
        Write-Host "No champion data available in the dataset" -ForegroundColor Yellow
        "No champion data available" | Tee-Object -FilePath $logFile -Append
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
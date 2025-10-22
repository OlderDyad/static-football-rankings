# Define paths and connection string
$logFile = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\scripts\imported_SQL_json\logs\all-time-teams.log"
$outputDir = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\docs\data\all-time"
$connectionString = "Server=MCKNIGHTS-PC\SQLEXPRESS01;Database=hs_football_database;Trusted_Connection=True;TrustServerCertificate=True"

# Ensure directories exist and clear old files
New-Item -ItemType Directory -Force -Path (Split-Path $logFile) | Out-Null
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
Remove-Item "$outputDir\all-time-teams.json" -ErrorAction SilentlyContinue

# Start logging
Get-Date | Out-File $logFile
"Starting all-time teams generation" | Tee-Object -FilePath $logFile -Append

# Import common functions
. ".\common-functions.ps1"

try {
    # Connect to the database
    $connection = Connect-Database
    Write-Host "Database connection established"
    
    # Execute SQL query to get all-time teams
    Write-Host "Processing all-time teams..."
    $command = New-Object System.Data.SqlClient.SqlCommand("EXEC GetAllTimeTeams", $connection)
    $adapter = New-Object System.Data.SqlClient.SqlDataAdapter($command)
    $teamsDataset = New-Object System.Data.DataSet
    $adapter.Fill($teamsDataset)

    if ($teamsDataset.Tables.Count -gt 0 -and $teamsDataset.Tables[0].Rows.Count -gt 0) {
        $teamsTable = $teamsDataset.Tables[0]

        # Get metadata for the top team
        $topTeamName = $teamsTable.Rows[0].team
        $metadata = Get-TeamMetadata -connection $connection -TeamName $topTeamName -isProgram $false

        # Format team data using the Format-TeamData function
        $jsonData = Format-TeamData -teams $teamsTable -metadata $metadata -description "All-time top teams" -yearRange "all-time"

        # Write JSON data to file
        $outputPath = Join-Path $outputDir "all-time-teams.json"
        $jsonData | ConvertTo-Json -Depth 10 | Set-Content -Path $outputPath -Force
        Write-Host "File written: $outputPath"
        Write-Host "File last modified: $(Get-Item $outputPath).LastWriteTime"

        # Log success
        "File generated: $outputPath" | Tee-Object -FilePath $logFile -Append
    } else {
        Write-Host "No team data available in the dataset" -ForegroundColor Yellow
        "No team data available in the dataset" | Tee-Object -FilePath $logFile -Append
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



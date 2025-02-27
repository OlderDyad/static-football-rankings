# Define paths and connection string
$logFile = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\scripts\imported_SQL_json\logs\latest-season-teams.log"
$outputDir = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\docs\data\latest"
$connectionString = "Server=MCKNIGHTS-PC\SQLEXPRESS01;Database=hs_football_database;Trusted_Connection=True;TrustServerCertificate=True"

# Ensure directories exist and clear old files
New-Item -ItemType Directory -Force -Path (Split-Path $logFile) | Out-Null
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
Remove-Item "$outputDir\latest-teams.json" -ErrorAction SilentlyContinue

# Start logging
Get-Date | Out-File $logFile
"Starting latest season teams generation" | Tee-Object -FilePath $logFile -Append

# Import common functions
. ".\common-functions.ps1"

try {
    # Connect to the database
    $connection = Connect-Database
    Write-Host "Database connection established"

    # Execute the GetLatestSeasonTeams stored procedure
    Write-Host "Fetching the latest season and rankings..."
    $parameters = @(
        (New-SqlParameter -ParameterName "@PageNumber" -SqlType Int -Value 1),
        (New-SqlParameter -ParameterName "@PageSize" -SqlType Int -Value 1000),
        (New-SqlParameter -ParameterName "@SearchTerm" -SqlType NVarChar -Value "")
    )

    $command = New-Object System.Data.SqlClient.SqlCommand("EXEC GetLatestSeasonTeams @PageNumber, @PageSize, @SearchTerm", $connection)
    foreach ($param in $parameters) {
        $command.Parameters.Add($param) | Out-Null
    }

    $adapter = New-Object System.Data.SqlClient.SqlDataAdapter($command)
    $dataset = New-Object System.Data.DataSet
    $adapter.Fill($dataset)

    if ($dataset.Tables.Count -gt 0 -and $dataset.Tables[0].Rows.Count -gt 0) {
        $teamsTable = $dataset.Tables[0]

        # Extract the latest season
        $latestSeason = $teamsTable.Rows[0].Season
        Write-Host "Latest season identified: $latestSeason"
        "Latest season identified: $latestSeason" | Tee-Object -FilePath $logFile -Append

        # Get metadata for the top team
        $topTeamName = $teamsTable.Rows[0].Team
        $metadata = Get-TeamMetadata -connection $connection -TeamName $topTeamName -isProgram $false

        # Format team data using the Format-TeamData function
        $jsonData = Format-TeamData -teams $teamsTable -metadata $metadata -description "Latest season teams" -yearRange $latestSeason

        # Write JSON data to file
        $outputPath = Join-Path $outputDir "latest-teams.json"
        $jsonData | ConvertTo-Json -Depth 10 | Set-Content -Path $outputPath -Force
        Write-Host "File written: $outputPath"
        Write-Host "File last modified: $(Get-Item $outputPath).LastWriteTime"

        # Log success
        "File generated: $outputPath" | Tee-Object -FilePath $logFile -Append
    } else {
        Write-Host "No team data available for the latest season" -ForegroundColor Yellow
        "No team data available for the latest season" | Tee-Object -FilePath $logFile -Append
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









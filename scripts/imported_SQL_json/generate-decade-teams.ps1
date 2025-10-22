# Paths and connection string
$logFile = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\scripts\imported_SQL_json\logs\decade-teams.log"
$outputDir = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\docs\data\decades\teams"
$connectionString = "Server=MCKNIGHTS-PC\SQLEXPRESS01;Database=hs_football_database;Trusted_Connection=True;TrustServerCertificate=True"

# Ensure directories exist
New-Item -ItemType Directory -Force -Path (Split-Path $logFile) | Out-Null
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

# Start logging
Get-Date | Out-File $logFile
"Starting decade teams generation" | Tee-Object -FilePath $logFile -Append

# Import common functions and constants
. ".\common-functions.ps1"
. ".\constants.ps1"

# Default parameters
$pageNumber = 1
$pageSize = 1000
$searchTerm = [DBNull]::Value  # Explicitly pass a DBNull for @SearchTerm

# Loop through decades
foreach ($decade in $decades) {
    $decadeStart = $decade.StartYear
    $decadeName = $decade.Name
    $decadeDisplayName = $decade.DisplayName

    try {
        # Connect to the database
        $connection = Connect-Database
        Write-Host "Database connection established for decade: $decadeDisplayName"

        # Define the output parameter
        $totalCountParam = New-SqlParameter -ParameterName "@TotalCount" -SqlType Int -Direction Output -Value $null

        # Parameters for the stored procedure
        $parameters = @(
            (New-SqlParameter -ParameterName "@DecadeStart" -SqlType Int -Value $decadeStart),
            (New-SqlParameter -ParameterName "@PageNumber" -SqlType Int -Value $pageNumber),
            (New-SqlParameter -ParameterName "@PageSize" -SqlType Int -Value $pageSize),
            (New-SqlParameter -ParameterName "@SearchTerm" -SqlType NVarChar -Value $searchTerm),
            $totalCountParam
        )

        # Execute stored procedure
        Write-Host "Fetching teams for decade: $decadeDisplayName..."
        $command = New-Object System.Data.SqlClient.SqlCommand("EXEC GetTeamsByDecade @DecadeStart, @PageNumber, @PageSize, @SearchTerm, @TotalCount OUTPUT", $connection)
        foreach ($param in $parameters) {
            $command.Parameters.Add($param) | Out-Null
        }

        $adapter = New-Object System.Data.SqlClient.SqlDataAdapter($command)
        $dataset = New-Object System.Data.DataSet
        $adapter.Fill($dataset) | Out-Null

        if ($dataset.Tables.Count -gt 0 -and $dataset.Tables[0].Rows.Count -gt 0) {
            $teamsTable = $dataset.Tables[0]

            # Get metadata for the top team
            $topTeamName = $teamsTable.Rows[0].Team
            $metadata = Get-TeamMetadata -connection $connection -TeamName $topTeamName -isProgram $false

            # Format the JSON data
            $jsonData = Format-TeamData -teams $teamsTable -metadata $metadata -description "Teams for ${decadeDisplayName}" -yearRange "${decadeStart}-${decadeStart + 9}"

            # Write JSON file
            $outputPath = Join-Path $outputDir "teams-${decadeName}.json"
            $jsonData | ConvertTo-Json -Depth 10 | Set-Content $outputPath -Force
            Write-Host "File written: $outputPath"
            "File generated: $outputPath" | Tee-Object -FilePath $logFile -Append
        } else {
            Write-Host "No data found for ${decadeDisplayName}" -ForegroundColor Yellow
            "No data found for ${decadeDisplayName}" | Tee-Object -FilePath $logFile -Append
        }

        # Log total count
        $totalCount = $totalCountParam.Value
        Write-Host "Total teams for ${decadeDisplayName}: $totalCount"
        "Total teams for ${decadeDisplayName}: $totalCount" | Tee-Object -FilePath $logFile -Append
    }
    catch {
        Write-Host "Error: $_" -ForegroundColor Red
        "Error: $_" | Tee-Object -FilePath $logFile -Append
    }
    finally {
        if ($connection -and $connection.State -eq 'Open') {
            $connection.Close()
            Write-Host "Database connection closed for ${decadeDisplayName}"
        }
    }
}

"Decade teams generation complete" | Tee-Object -FilePath $logFile -Append

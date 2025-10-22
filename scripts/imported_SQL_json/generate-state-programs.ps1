# Paths and connection string
$logFile = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\scripts\imported_SQL_json\logs\state-teams.log"
$outputDir = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\docs\data\states\teams"
$connectionString = "Server=MCKNIGHTS-PC\SQLEXPRESS01;Database=hs_football_database;Trusted_Connection=True;TrustServerCertificate=True"

# Ensure directories exist
New-Item -ItemType Directory -Force -Path (Split-Path $logFile) | Out-Null
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

# Start logging
Get-Date | Out-File $logFile
"Starting state teams generation" | Tee-Object -FilePath $logFile -Append

# Import common functions and constants
. ".\common-functions.ps1"
. ".\constants.ps1"

# Default parameters
$pageNumber = 1
$pageSize = 1000
$searchTerm = [DBNull]::Value

# Loop through states
foreach ($state in $regions) {
    $stateFormatted = "($state)"
    Write-Host "`nProcessing state: $stateFormatted"
    
    try {
        $connection = Connect-Database
        Write-Host "Database connection established"

        # Get teams for state
        $parameters = @(
            (New-SqlParameter -ParameterName "@State" -SqlType NVarChar -Value $stateFormatted),
            (New-SqlParameter -ParameterName "@PageNumber" -SqlType Int -Value $pageNumber),
            (New-SqlParameter -ParameterName "@PageSize" -SqlType Int -Value $pageSize),
            (New-SqlParameter -ParameterName "@SearchTerm" -SqlType NVarChar -Value $searchTerm)
        )

        $command = New-Object System.Data.SqlClient.SqlCommand("EXEC GetTeamsByState @State, @PageNumber, @PageSize, @SearchTerm", $connection)
        foreach ($param in $parameters) {
            $command.Parameters.Add($param) | Out-Null
        }

        $adapter = New-Object System.Data.SqlClient.SqlDataAdapter($command)
        $dataset = New-Object System.Data.DataSet
        $adapter.Fill($dataset)

        if ($dataset.Tables.Count -gt 0 -and $dataset.Tables[0].Rows.Count -gt 0) {
            $teamsTable = $dataset.Tables[0]
            
            # Get metadata for the top team
            $topTeamName = $teamsTable.Rows[0].Team
            Write-Host "Getting metadata for: $topTeamName"
            
            $metadata = Get-TeamMetadata -connection $connection -TeamName $topTeamName -isProgram $false
            if (-not $metadata) {
                Write-Host "Warning: No metadata found for $topTeamName" -ForegroundColor Yellow
                $metadata = @{
                    Mascot = ""
                    backgroundColor = "Navy"
                    textColor = "White"
                    LogoURL = ""
                    School_Logo_URL = ""
                }
            }

            # Format and save data
            $jsonData = Format-TeamData -teams $teamsTable `
                                      -metadata $metadata `
                                      -description "Top teams for state: $stateFormatted" `
                                      -yearRange "All-Time" `
                                      -stateFormatted $stateFormatted

            $outputPath = Join-Path $outputDir "state-teams-$state.json"
            $jsonData | ConvertTo-Json -Depth 10 | Set-Content -Path $outputPath
            Write-Host "File written: $outputPath"
            "File generated: $outputPath" | Tee-Object -FilePath $logFile -Append
        } else {
            Write-Host "No data found for state: $stateFormatted" -ForegroundColor Yellow
            "No data found for state: $stateFormatted" | Tee-Object -FilePath $logFile -Append
        }
    }
    catch {
        Write-Host "Error processing state $stateFormatted : $_" -ForegroundColor Red
        $_ | Out-File $logFile -Append
    }
    finally {
        if ($connection -and $connection.State -eq 'Open') {
            $connection.Close()
            Write-Host "Database connection closed"
        }
    }
}

"State teams generation complete" | Tee-Object -FilePath $logFile -Append

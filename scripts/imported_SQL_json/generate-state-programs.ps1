# Paths and connection string
$logFile = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\scripts\imported_SQL_json\logs\state-programs.log"
$outputDir = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\docs\data\states\programs"
$connectionString = "Server=MCKNIGHTS-PC\SQLEXPRESS01;Database=hs_football_database;Trusted_Connection=True;TrustServerCertificate=True"

# Ensure directories exist
New-Item -ItemType Directory -Force -Path (Split-Path $logFile) | Out-Null
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

# Start logging
Get-Date | Out-File $logFile
"Starting state programs generation" | Tee-Object -FilePath $logFile -Append

# Import common functions and constants
. ".\common-functions.ps1"
. ".\constants.ps1"

# Default parameters
$pageNumber = 1
$pageSize = 2000  # Increased to 2000 as requested
$minSeasons = 25   # Added minimum seasons parameter
$searchTerm = [DBNull]::Value

# Loop through states
foreach ($state in $regions) {
    $stateFormatted = "($state)"
    Write-Host "`nProcessing state: $stateFormatted"
    
    try {
        $connection = Connect-Database
        Write-Host "Database connection established"

        # Get programs for state
        $parameters = @(
            (New-SqlParameter -ParameterName "@State" -SqlType NVarChar -Value $stateFormatted),
            (New-SqlParameter -ParameterName "@MinSeasons" -SqlType Int -Value $minSeasons),
            (New-SqlParameter -ParameterName "@PageNumber" -SqlType Int -Value $pageNumber),
            (New-SqlParameter -ParameterName "@PageSize" -SqlType Int -Value $pageSize),
            (New-SqlParameter -ParameterName "@SearchTerm" -SqlType NVarChar -Value $searchTerm)
        )

        $command = New-Object System.Data.SqlClient.SqlCommand("EXEC GetProgramsByState @State, @MinSeasons, @PageNumber, @PageSize, @SearchTerm", $connection)
        foreach ($param in $parameters) {
            $command.Parameters.Add($param) | Out-Null
        }

        $adapter = New-Object System.Data.SqlClient.SqlDataAdapter($command)
        $dataset = New-Object System.Data.DataSet
        $adapter.Fill($dataset) | Out-Null

        if ($dataset.Tables.Count -gt 0 -and $dataset.Tables[0].Rows.Count -gt 0) {
            $programsTable = $dataset.Tables[0]
            $topProgramName = $programsTable.Rows[0].program
            Write-Host "Getting metadata for: $topProgramName"
            
            $metadata = Get-TeamMetadata -connection $connection -TeamName $topProgramName -isProgram $true
            if (-not $metadata) {
                Write-Host "Warning: No metadata found for $topProgramName" -ForegroundColor Yellow
                $metadata = @{
                    Mascot = ""
                    backgroundColor = "Navy"
                    textColor = "White"
                    LogoURL = ""
                    School_Logo_URL = ""
                }
            }

            # Format and save data
            $jsonData = Format-ProgramData -programs $programsTable `
                                         -metadata $metadata `
                                         -description "Top programs for state: $stateFormatted"

            $outputPath = Join-Path $outputDir "state-programs-$state.json"
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

"State programs generation complete" | Tee-Object -FilePath $logFile -Append

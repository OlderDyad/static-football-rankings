# =============================================================================
# generate-decade-programs.ps1 - FIXED VERSION
# =============================================================================
# This version uses AddWithValue for simpler, more reliable parameter passing
# =============================================================================

# Paths and connection string
$logFile = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\scripts\imported_SQL_json\logs\decade-programs.log"
$outputDir = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\docs\data\decades\programs"
$connectionString = "Server=MCKNIGHTS-PC\SQLEXPRESS01;Database=hs_football_database;Trusted_Connection=True;TrustServerCertificate=True"

# Ensure directories exist
New-Item -ItemType Directory -Force -Path (Split-Path $logFile) | Out-Null
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

# Start logging
Get-Date | Out-File $logFile
"Starting decade programs generation" | Tee-Object -FilePath $logFile -Append

# Import common functions and constants
. ".\common-functions.ps1"
. ".\constants.ps1"

# =============================================================================
# KEY PARAMETER: Minimum seasons required for a program to appear
# =============================================================================
# For completed decades: 7 seasons (70% of decade)
# For current decade (2020s): Calculate dynamically based on current year
# =============================================================================
$currentYear = (Get-Date).Year
$defaultMinSeasons = 7

# Page parameters
$pageNumber = 1
$pageSize = 5000  # Get all programs

# Loop through decades
foreach ($decade in $decades) {
    $decadeStart = $decade.StartYear
    $decadeEnd = $decadeStart + 9
    $decadeName = $decade.Name
    $decadeDisplayName = $decade.DisplayName

    # Calculate appropriate MinSeasons for this decade
    # For current/incomplete decade, use 70% of available years
    if ($currentYear -le $decadeEnd) {
        $availableYears = $currentYear - $decadeStart + 1
        $minSeasons = [Math]::Max(1, [Math]::Floor($availableYears * 0.7))
        Write-Host "Current decade detected. Available years: $availableYears, MinSeasons: $minSeasons" -ForegroundColor Yellow
    } else {
        $minSeasons = $defaultMinSeasons
    }

    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "Processing: $decadeDisplayName" -ForegroundColor Cyan
    Write-Host "Decade: $decadeStart - $decadeEnd" -ForegroundColor Cyan
    Write-Host "MinSeasons filter: $minSeasons" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan

    try {
        # Connect to the database
        $connection = New-Object System.Data.SqlClient.SqlConnection($connectionString)
        $connection.Open()
        Write-Host "Database connection established" -ForegroundColor Green

        # Create command with simpler parameter passing using AddWithValue
        $command = New-Object System.Data.SqlClient.SqlCommand
        $command.Connection = $connection
        $command.CommandText = "EXEC GetProgramsByDecade @DecadeStart, @MinSeasons, @PageNumber, @PageSize, @SearchTerm, @TotalCount OUTPUT"
        
        # Add parameters using AddWithValue (simpler and more reliable)
        $command.Parameters.AddWithValue("@DecadeStart", $decadeStart) | Out-Null
        $command.Parameters.AddWithValue("@MinSeasons", $minSeasons) | Out-Null
        $command.Parameters.AddWithValue("@PageNumber", $pageNumber) | Out-Null
        $command.Parameters.AddWithValue("@PageSize", $pageSize) | Out-Null
        $command.Parameters.AddWithValue("@SearchTerm", [DBNull]::Value) | Out-Null
        
        # Add output parameter
        $totalCountParam = $command.Parameters.Add("@TotalCount", [System.Data.SqlDbType]::Int)
        $totalCountParam.Direction = [System.Data.ParameterDirection]::Output

        Write-Host "Executing stored procedure with MinSeasons = $minSeasons..." -ForegroundColor Yellow

        # Execute
        $adapter = New-Object System.Data.SqlClient.SqlDataAdapter($command)
        $dataset = New-Object System.Data.DataSet
        $rowCount = $adapter.Fill($dataset)
        
        Write-Host "Query returned $rowCount rows" -ForegroundColor Green

        if ($dataset.Tables.Count -gt 0 -and $dataset.Tables[0].Rows.Count -gt 0) {
            $programsTable = $dataset.Tables[0]
            
            # Verify the filter worked - check minimum seasons in results
            $minSeasonsInResults = ($programsTable | Measure-Object -Property seasons -Minimum).Minimum
            $maxSeasonsInResults = ($programsTable | Measure-Object -Property seasons -Maximum).Maximum
            Write-Host "Seasons range in results: $minSeasonsInResults to $maxSeasonsInResults" -ForegroundColor Cyan
            
            if ($minSeasonsInResults -lt $minSeasons) {
                Write-Host "WARNING: Found programs with fewer than $minSeasons seasons!" -ForegroundColor Red
                Write-Host "This indicates the filter is not working correctly." -ForegroundColor Red
            }

            # Get metadata for the top program
            $topProgramName = $programsTable.Rows[0].program
            Write-Host "Top program: $topProgramName" -ForegroundColor Green
            
            $metadata = Get-TeamMetadata -connection $connection -TeamName $topProgramName -isProgram $true

            # Format the JSON data
            $jsonData = Format-ProgramData -programs $programsTable -metadata $metadata -description "Programs for ${decadeDisplayName} (${minSeasons}+ seasons)"

            # Write JSON file
            $outputPath = Join-Path $outputDir "programs-${decadeName}.json"
            $jsonData | ConvertTo-Json -Depth 10 | Set-Content $outputPath -Force
            Write-Host "File written: $outputPath" -ForegroundColor Green
            "File generated: $outputPath" | Tee-Object -FilePath $logFile -Append
        } else {
            Write-Host "No data found for ${decadeDisplayName}" -ForegroundColor Yellow
            "No data found for ${decadeDisplayName}" | Tee-Object -FilePath $logFile -Append
        }

        # Log total count
        $totalCount = $totalCountParam.Value
        Write-Host "Total programs for ${decadeDisplayName}: $totalCount" -ForegroundColor Cyan
        "Total programs for ${decadeDisplayName}: $totalCount" | Tee-Object -FilePath $logFile -Append
    }
    catch {
        Write-Host "Error: $_" -ForegroundColor Red
        Write-Host "Stack trace: $($_.ScriptStackTrace)" -ForegroundColor Red
        "Error: $_" | Tee-Object -FilePath $logFile -Append
    }
    finally {
        if ($connection -and $connection.State -eq 'Open') {
            $connection.Close()
            Write-Host "Database connection closed" -ForegroundColor Gray
        }
    }
}

"Decade programs generation complete" | Tee-Object -FilePath $logFile -Append
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "COMPLETE: All decade programs generated" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green




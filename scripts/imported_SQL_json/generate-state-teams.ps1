# Paths and connection string
$logFile = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\scripts\imported_SQL_json\logs\state-teams.log"
$outputDir = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\docs\data\states\teams"
$connectionString = "Server=MCKNIGHTS-PC\SQLEXPRESS01;Database=hs_football_database;Trusted_Connection=True;TrustServerCertificate=True"

Write-Host "Script starting..." -ForegroundColor Green

# Ensure directories exist
Write-Host "Creating directories..."
New-Item -ItemType Directory -Force -Path (Split-Path $logFile) | Out-Null
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

# Start logging
Write-Host "Initializing log file..."
Get-Date | Out-File $logFile
"Starting state teams generation" | Tee-Object -FilePath $logFile -Append

# Import common functions and constants
Write-Host "Importing common functions..."
. ".\common-functions.ps1"
. ".\constants.ps1"

# Verify regions array
Write-Host "Regions to process: $($regions.Count)"
Write-Host "First few regions: $($regions[0..2] -join ', ')"

foreach ($state in $regions) {
   $stateFormatted = "($state)"
   Write-Host "`nProcessing state: $stateFormatted" -ForegroundColor Cyan
   
   try {
       Write-Host "Attempting database connection..."
       $connection = Connect-Database
       Write-Host "Database connection established" -ForegroundColor Green

       Write-Host "Setting up SQL command for state: $stateFormatted"
       $command = New-Object System.Data.SqlClient.SqlCommand("EXEC GetTeamsByState @State, @PageNumber, @PageSize, @SearchTerm", $connection)
       $command.Parameters.AddWithValue("@State", $stateFormatted) | Out-Null
       $command.Parameters.AddWithValue("@PageNumber", 1) | Out-Null
       $command.Parameters.AddWithValue("@PageSize", 1000) | Out-Null
       $command.Parameters.AddWithValue("@SearchTerm", [DBNull]::Value) | Out-Null

       Write-Host "Executing SQL command..."
       $adapter = New-Object System.Data.SqlClient.SqlDataAdapter($command)
       $dataset = New-Object System.Data.DataSet
       $adapter.Fill($dataset)

       Write-Host "Checking dataset results..."
       Write-Host "Dataset has $($dataset.Tables.Count) tables"
       
       if ($dataset.Tables.Count -gt 0) {
           Write-Host "First table has $($dataset.Tables[0].Rows.Count) rows"
       }

       if ($dataset.Tables[0].Rows.Count -gt 0) {
           $teamsTable = $dataset.Tables[0]
           $topTeamName = $teamsTable.Rows[0].Team
           Write-Host "Processing top team: $topTeamName" -ForegroundColor Yellow

           Write-Host "Getting metadata for: $topTeamName"
           $metadata = Get-TeamMetadata -connection $connection -TeamName $topTeamName -isProgram $false
           
           if (-not $metadata) {
               Write-Host "No metadata found - using defaults" -ForegroundColor Yellow
               $metadata = @{
                   Mascot = ""
                   backgroundColor = "Navy"
                   textColor = "White"
                   LogoURL = ""
                   School_Logo_URL = ""
               }
           } else {
               Write-Host "Metadata found successfully" -ForegroundColor Green
           }

           Write-Host "Formatting team data..."
           $jsonData = Format-StateTeamData -teams $teamsTable `
                                           -metadata $metadata `
                                           -description "Top teams for state: $stateFormatted" `
                                           -yearRange "All-Time" `
                                           -stateFormatted $stateFormatted

           $outputPath = Join-Path $outputDir "state-teams-$state.json"
           Write-Host "Writing data to: $outputPath"
           $jsonData | ConvertTo-Json -Depth 10 | Set-Content -Path $outputPath
           
           Write-Host "File written successfully" -ForegroundColor Green
           "File generated: $outputPath" | Tee-Object -FilePath $logFile -Append
           
           Write-Host "Total teams for $stateFormatted : $($teamsTable.Rows.Count)" -ForegroundColor Cyan
           "Total teams for $stateFormatted : $($teamsTable.Rows.Count)" | Tee-Object -FilePath $logFile -Append
       } else {
           Write-Host "No data found for $stateFormatted" -ForegroundColor Yellow
           "No data found for $stateFormatted" | Tee-Object -FilePath $logFile -Append
           Write-Host "Total teams for $stateFormatted : 0" -ForegroundColor Yellow
           "Total teams for $stateFormatted : 0" | Tee-Object -FilePath $logFile -Append
       }
   }
   catch {
       Write-Host "Error processing state $stateFormatted : $_" -ForegroundColor Red
       Write-Host "Stack Trace: $($_.ScriptStackTrace)" -ForegroundColor Red
       $_ | Out-File $logFile -Append
   }
   finally {
       if ($connection -and $connection.State -eq 'Open') {
           $connection.Close()
           Write-Host "Database connection closed for $stateFormatted" -ForegroundColor Gray
       }
   }
}

Write-Host "`nState teams generation complete" -ForegroundColor Green
"State teams generation complete" | Tee-Object -FilePath $logFile -Append

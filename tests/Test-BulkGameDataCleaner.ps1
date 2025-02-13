# Test-BulkGameDataCleaner.ps1

# Set project root and paths explicitly
$projectRoot = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings"
$modulePath = "$projectRoot\Modules\GameDataCleaner\GameDataCleaner.psm1"
$csvPath = "$projectRoot\python_scripts\all_schedules.csv"
$logsPath = "$projectRoot\logs"

# Set up console output capture
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$consoleLog = "$projectRoot\logs\console_output_$timestamp.txt"
Start-Transcript -Path $consoleLog

Write-Host "Script starting - all output will be saved to: $consoleLog"

Write-Host "Using paths:"
Write-Host "Project root: $projectRoot"
Write-Host "Module path: $modulePath"
Write-Host "CSV path: $csvPath"
Write-Host "Logs path: $logsPath"

# Create logs directory if it doesn't exist
if (-not (Test-Path $logsPath)) {
   New-Item -ItemType Directory -Path $logsPath -Force
}

# Import module
Remove-Module GameDataCleaner -ErrorAction SilentlyContinue
Import-Module $modulePath -Force

# Initialize logging
$logPath = Initialize-GameDataLogger

Write-Host "`nReading CSV file from: $csvPath"
Write-Host "Press Enter to begin processing..."
Read-Host

try {
   $rawGames = Import-Csv $csvPath
   $totalGames = $rawGames.Count
   Write-Host "Found $totalGames games to process"

   # Initialize tracking
   $processed = 0
   $errors = @()
   $cleanedGames = @()
   $dataQualityIssues = @()

   foreach ($game in $rawGames) {
       $processed++
       if ($processed % 1000 -eq 0) {
        Write-Host "Processed $processed of $totalGames games"
    }

       # Check for data quality issues
       $qualityIssues = @()
       
       # Check for missing or malformed URLs
       if ([string]::IsNullOrWhiteSpace($game.URL) -or -not $game.URL.StartsWith("http")) {
           $qualityIssues += "Invalid or missing URL"
       }
       if ([string]::IsNullOrWhiteSpace($game.OpponentURL) -or -not $game.OpponentURL.StartsWith("http")) {
           $qualityIssues += "Invalid or missing OpponentURL"
       }

       # Check for missing scores
       if ([string]::IsNullOrWhiteSpace($game.Score) -or -not $game.Score.Contains("-")) {
           $qualityIssues += "Invalid or missing Score"
       }

       # Check for missing essential data
       if ([string]::IsNullOrWhiteSpace($game.TeamName)) {
           $qualityIssues += "Missing TeamName"
       }
       if ([string]::IsNullOrWhiteSpace($game.Opponent)) {
           $qualityIssues += "Missing Opponent"
       }
       if ([string]::IsNullOrWhiteSpace($game.Date)) {
           $qualityIssues += "Missing Date"
       }

       # Convert CSV object to hashtable
       $gameData = @{
           TeamName = $game.TeamName
           State = $game.State
           URL = $game.URL
           Date = $game.Date
           Location = $game.Location
           Opponent = $game.Opponent
           WL = $game.WL
           Score = $game.Score
           OpponentURL = $game.OpponentURL
           ScrapedAt = $game.ScrapedAt
           Status = $game.Status
       }

       # If there are quality issues, log them but continue processing
       if ($qualityIssues.Count -gt 0) {
           $dataQualityIssues += @{
               TeamName = $game.TeamName
               Opponent = $game.Opponent
               Date = $game.Date
               Issues = $qualityIssues -join "; "
               RawData = $game | ConvertTo-Json
           }
       }

       try {
           $cleanedGame = Convert-RawGameData -Season 2024 -RawData $gameData -LogPath $logPath
           $cleanedGames += $cleanedGame
       }
       catch {
           $errors += @{
               TeamName = $game.TeamName
               Opponent = $game.Opponent
               Date = $game.Date
               Error = $_.Exception.Message
               RawData = $game | ConvertTo-Json
           }
       }
   }

   # Detailed Analysis Section
   Write-Host "`nPress Enter to view detailed analysis..."
   Read-Host
   
   Write-Host "`n=== Detailed Analysis ==="
   
   if ($cleanedGames.Count -gt 0) {
       Write-Host "`nFirst Successful Conversion:"
       Write-Host "`nOriginal Data:"
       $firstSuccess = $rawGames[0]
       $firstSuccess | Format-Table TeamName, Opponent, Date, Location, Score, WL -AutoSize
       
       Write-Host "`nCleaned Data (First Game):"
       $firstClean = $cleanedGames[0]
       [PSCustomObject]@{
           GameDate = $firstClean.GameDate
           Season = $firstClean.Season
           HomeTeam = $firstClean.HomeTeam
           VisitorTeam = $firstClean.VisitorTeam
           HomeScore = $firstClean.HomeScore
           VisitorScore = $firstClean.VisitorScore
           Forfeit = $firstClean.Forfeit
           IsNeutral = $firstClean.IsNeutral
           Location = $firstClean.Location
           Margin = $firstClean.Margin
       } | Format-Table -AutoSize
   }

   if ($errors.Count -gt 0) {
       Write-Host "`nFirst 3 Errors:"
       $errors | Select-Object -First 3 | ForEach-Object {
           Write-Host "`nTeam: $($_.TeamName)"
           Write-Host "Opponent: $($_.Opponent)"
           Write-Host "Date: $($_.Date)"
           Write-Host "Error: $($_.Error)"
           Write-Host "Raw Data: $($_.RawData)"
           Write-Host "-----------------"
       }
   }

   if ($dataQualityIssues.Count -gt 0) {
       Write-Host "`nFirst 3 Quality Issues:"
       $dataQualityIssues | Select-Object -First 3 | ForEach-Object {
           Write-Host "`nTeam: $($_.TeamName)"
           Write-Host "Opponent: $($_.Opponent)"
           Write-Host "Date: $($_.Date)"
           Write-Host "Issues: $($_.Issues)"
           Write-Host "-----------------"
       }
   }

   # Summary Report
   Write-Host "`nPress Enter to view summary report..."
   Read-Host

   Write-Host "`n=== Processing Summary ==="
   Write-Host "Total games processed: $totalGames"
   Write-Host "Successfully cleaned: $($cleanedGames.Count)"
   Write-Host "Processing errors: $($errors.Count)"
   Write-Host "Data quality issues: $($dataQualityIssues.Count)"

   # Save detailed reports
   $timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    
   if ($errors.Count -gt 0) {
       $errorFile = "$logsPath\processing_errors_$timestamp.csv"
       $errors | Export-Csv -Path $errorFile -NoTypeInformation
       Write-Host "`nProcessing errors saved to: $errorFile"
   }

   if ($dataQualityIssues.Count -gt 0) {
       $qualityFile = "$logsPath\quality_issues_$timestamp.csv"
       $dataQualityIssues | Export-Csv -Path $qualityFile -NoTypeInformation
       Write-Host "Data quality issues saved to: $qualityFile"
   }

   # Sample of cleaned data
   Write-Host "`nSample of cleaned games (first 5):"
   $cleanedGames | Select-Object -First 5 | ForEach-Object {
       [PSCustomObject]@{
           GameDate = $_.GameDate
           HomeTeam = $_.HomeTeam
           VisitorTeam = $_.VisitorTeam
           HomeScore = $_.HomeScore
           VisitorScore = $_.VisitorScore
           Forfeit = $_.Forfeit
           IsNeutral = $_.IsNeutral
           Location = $_.Location
       }
   } | Format-Table -AutoSize

} # Close the main try block
catch {
   Write-Host "Error reading CSV file: $_"
}

Stop-Transcript
Write-Host "`nScript complete. Check $consoleLog for full output."
Write-Host "Press Enter to exit..."
Read-Host
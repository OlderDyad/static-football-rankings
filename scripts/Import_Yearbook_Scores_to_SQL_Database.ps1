# Import Yearbook Scores to SQL Database

# Configuration
$sourceFile = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\excel_files\Yearbook_Scores.txt"
$sqlServer = "MCKNIGHTS-PC\SQLEXPRESS01"
$database = "hs_football_database"
$logFile = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\scripts\logs\yearbook_import_log.txt"

# Create log directory if it doesn't exist
$logDir = Split-Path $logFile -Parent
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

# Start logging
Start-Transcript -Path $logFile -Force
Write-Host "Starting Yearbook Scores import at $(Get-Date)"
Write-Host "Source file: $sourceFile"

# Verify file exists
if (-not (Test-Path $sourceFile)) {
    Write-Host "ERROR: Source file not found at $sourceFile" -ForegroundColor Red
    Stop-Transcript
    exit 1
}

try {
    # Read file as raw text first
    $rawText = Get-Content -Path $sourceFile -Raw

    # Handle different line endings
    $lines = $rawText -split "`r`n" | Where-Object { $_ -ne "" }
    if ($lines.Count -eq 0) {
        $lines = $rawText -split "`n" | Where-Object { $_ -ne "" }
    }
    
    Write-Host "Found $($lines.Count) lines in file."
    
    # Display sample of data to verify format
    Write-Host "Sample data (first 2 lines):"
    $lines | Select-Object -First 2 | ForEach-Object { Write-Host $_ }
    
    # Create SQL connection
    Write-Host "Connecting to SQL Server..."
    $connectionString = "Server=$sqlServer;Database=$database;Integrated Security=True;"
    $connection = New-Object System.Data.SqlClient.SqlConnection($connectionString)
    $connection.Open()
    
    # Initialize counters
    $totalRows = 0
    $successRows = 0
    $errorRows = 0
    
    Write-Host "Beginning data import..."

    # Process each line
    foreach ($line in $lines) {
        $totalRows++
        
        try {
            # Skip empty lines
            if ([string]::IsNullOrWhiteSpace($line)) {
                Write-Host "Skipping empty line $totalRows" -ForegroundColor Yellow
                continue
            }

            Write-Host "`nProcessing line $totalRows" -ForegroundColor Cyan
            
            # Split the line by tabs (since your data appears tab-delimited)
            $parts = $line -split "\t"
            
            # Extract fields based on their position in tab-delimited format
            if ($parts.Count -lt 11) {
                Write-Host "Not enough fields in line: $($parts.Count)" -ForegroundColor Yellow
                continue
            }
            
            # Correct field positions based on your data
            $gameDate = $parts[0].Trim()
            $season = $parts[1].Trim()
            $homeTeam = $parts[2].Trim()
            $visitorTeam = $parts[4].Trim()
            
            # Safer parsing with better error handling
            $homeScore = 0
            $visitorScore = 0
            $margin = 0
            
            if (-not [int]::TryParse($parts[3].Trim(), [ref]$homeScore)) {
                Write-Host "Warning: Could not parse home score '$($parts[3])'" -ForegroundColor Yellow
            }
            
            if (-not [int]::TryParse($parts[5].Trim(), [ref]$visitorScore)) {
                Write-Host "Warning: Could not parse visitor score '$($parts[5])'" -ForegroundColor Yellow
            }
            
            if (-not [int]::TryParse($parts[6].Trim(), [ref]$margin)) {
                Write-Host "Warning: Could not parse margin '$($parts[6])'" -ForegroundColor Yellow
            }
            
            $forfeitText = $parts[7].Trim()
            $forfeit = if ($forfeitText -eq "TRUE") { 1 } else { 0 }
            
            # Handle source - index 11
            $source = if ($parts.Count -gt 11 -and -not [string]::IsNullOrWhiteSpace($parts[11])) {
                $parts[11].Trim()
            } else {
                "Yearbook Import"
            }
            
            Write-Host "Date: $gameDate"
            Write-Host "Season: $season"
            Write-Host "Home: $homeTeam"
            Write-Host "Home Score: $homeScore"
            Write-Host "Visitor: $visitorTeam"
            Write-Host "Visitor Score: $visitorScore"
            Write-Host "Margin: $margin"
            Write-Host "Forfeit: $forfeit"
            Write-Host "Source: $source"
            
            # Skip if essential fields are missing
            if ([string]::IsNullOrWhiteSpace($gameDate) -or 
                [string]::IsNullOrWhiteSpace($season) -or 
                [string]::IsNullOrWhiteSpace($homeTeam) -or 
                [string]::IsNullOrWhiteSpace($visitorTeam)) {
                Write-Host "Skipping row $totalRows - Missing essential data" -ForegroundColor Yellow
                continue
            }
            
            # Format date to YYYY-MM-DD if needed
            if ($gameDate -match '(\d+)/(\d+)/(\d+)') {
                $month = $matches[1].PadLeft(2, '0')
                $day = $matches[2].PadLeft(2, '0')
                $year = $matches[3]
                if ($year.Length -eq 2) {
                    $year = if ([int]$year -gt 50) { "19$year" } else { "20$year" }
                }
                $gameDate = "$year-$month-$day"
            }
            
            # Generate a unique ID and timestamp
            $id = [Guid]::NewGuid().ToString().ToUpper()
            $dateAdded = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
            
            # Create SQL command
            $command = $connection.CreateCommand()
            $command.CommandText = @"
INSERT INTO [dbo].[HS_Scores] (
    [Date], [Season], [Home], [Visitor], [Neutral], 
    [Location], [Location2], [Line], [Future_Game], 
    [Source], [Date_Added], [OT], [Forfeit], [ID], 
    [Visitor_Score], [Home_Score], [Margin], [Access_ID]
) VALUES (
    @Date, @Season, @HomeTeam, @VisitorTeam, 0, 
    @HomeTeam, NULL, NULL, 0, 
    @Source, @DateAdded, 0, @Forfeit, @ID, 
    @VisitorScore, @HomeScore, @Margin, NULL
)
"@
            # Add parameters
            $command.Parameters.AddWithValue("@Date", $gameDate) | Out-Null
            $command.Parameters.AddWithValue("@Season", $season) | Out-Null
            $command.Parameters.AddWithValue("@HomeTeam", $homeTeam) | Out-Null
            $command.Parameters.AddWithValue("@VisitorTeam", $visitorTeam) | Out-Null
            $command.Parameters.AddWithValue("@Source", $source) | Out-Null
            $command.Parameters.AddWithValue("@DateAdded", $dateAdded) | Out-Null
            $command.Parameters.AddWithValue("@Forfeit", $forfeit) | Out-Null
            $command.Parameters.AddWithValue("@ID", $id) | Out-Null
            $command.Parameters.AddWithValue("@VisitorScore", $visitorScore) | Out-Null
            $command.Parameters.AddWithValue("@HomeScore", $homeScore) | Out-Null
            $command.Parameters.AddWithValue("@Margin", $margin) | Out-Null
            
            # Execute the command
            $rowsAffected = $command.ExecuteNonQuery()
            $successRows++
            
            Write-Host "Row $totalRows - $gameDate - $homeTeam vs $visitorTeam - Successfully imported" -ForegroundColor Green
            
        } catch {
            $errorRows++
            Write-Host "ERROR processing row $totalRows - $_" -ForegroundColor Red
            Write-Host "Raw data: $line" -ForegroundColor Red
        }
    }
    
    # Summary
    Write-Host "`nImport Summary:"
    Write-Host "Total rows processed: $totalRows"
    Write-Host "Successfully imported: $successRows"
    Write-Host "Errors: $errorRows"
    
} catch {
    Write-Host "ERROR: $_" -ForegroundColor Red
    Write-Host $_.ScriptStackTrace
} finally {
    # Close connection
    if ($connection -and $connection.State -eq 'Open') {
        $connection.Close()
        Write-Host "Database connection closed."
    }
    
    Stop-Transcript
}
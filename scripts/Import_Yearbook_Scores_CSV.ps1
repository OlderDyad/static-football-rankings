# Import Yearbook Scores from CSV to SQL Database

# Configuration
$sourceFile = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\excel_files\Yearbook_Scores.csv"
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
Write-Host "Starting Yearbook Scores CSV import at $(Get-Date)"
Write-Host "Source file: $sourceFile"

# Verify file exists
if (-not (Test-Path $sourceFile)) {
    Write-Host "ERROR: Source file not found at $sourceFile" -ForegroundColor Red
    Stop-Transcript
    exit 1
}

try {
    # Import CSV with proper encoding
    Write-Host "Importing CSV data..."
    $data = Import-Csv -Path $sourceFile -Encoding UTF8
    
    Write-Host "Found $($data.Count) records in CSV."
    
    # Display sample of data to verify format
    Write-Host "Sample data (first record):"
    $data | Select-Object -First 1 | Format-List
    
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

    # Process each record
    foreach ($record in $data) {
        $totalRows++
        
        try {
            Write-Host "`nProcessing record $totalRows" -ForegroundColor Cyan
            
            # Extract fields from CSV record
            $gameDate = $record.Date.Trim()
            $season = $record.Season.Trim()
            $homeTeam = $record.Home.Trim()
            $visitorTeam = $record.Visitor.Trim()
            
            # Safe parsing for numeric fields
            $homeScore = 0
            $visitorScore = 0
            $margin = 0
            
            if (-not [int]::TryParse($record.'Home Score', [ref]$homeScore)) {
                Write-Host "Warning: Could not parse home score '$($record.'Home Score')'" -ForegroundColor Yellow
            }
            
            if (-not [int]::TryParse($record.'Visitor Score', [ref]$visitorScore)) {
                Write-Host "Warning: Could not parse visitor score '$($record.'Visitor Score')'" -ForegroundColor Yellow
            }
            
            if (-not [int]::TryParse($record.Margin, [ref]$margin)) {
                Write-Host "Warning: Could not parse margin '$($record.Margin)'" -ForegroundColor Yellow
            }
            
           # Handle forfeit flag - a game is a forfeit if the combined score equals 1
           $forfeit = 0
           if (($homeScore + $visitorScore) -eq 1) {
               $forfeit = 1
               Write-Host "Forfeit detected - combined score equals 1" -ForegroundColor Yellow
           }

            # Handle source field
            $source = if (-not [string]::IsNullOrWhiteSpace($record.Source)) {
                $record.Source.Trim()
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
                Write-Host "Skipping record $totalRows - Missing essential data" -ForegroundColor Yellow
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
            
            Write-Host "Record $totalRows - $gameDate - $homeTeam vs $visitorTeam - Successfully imported" -ForegroundColor Green
            
        } catch {
            $errorRows++
            Write-Host "ERROR processing record $totalRows - $_" -ForegroundColor Red
            Write-Host "Raw data: $($record | ConvertTo-Json -Compress)" -ForegroundColor Red
        }
    }
    
    # Summary
    Write-Host "`nImport Summary:"
    Write-Host "Total records processed: $totalRows"
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
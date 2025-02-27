# Import-MediaChampions.ps1
$dataFile = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\excel_files\National Champion Teams.txt"
$logFile = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\scripts\imported_SQL_json\logs\import-champions.log"
$connectionString = "Server=MCKNIGHTS-PC\SQLEXPRESS01;Database=hs_football_database;Trusted_Connection=True;TrustServerCertificate=True"

# Ensure log directory exists
New-Item -ItemType Directory -Force -Path (Split-Path $logFile) | Out-Null

# Start logging
Get-Date | Out-File $logFile
"Starting import of national champions data" | Tee-Object -FilePath $logFile -Append

# Read the data file
"Reading data file: $dataFile" | Tee-Object -FilePath $logFile -Append
$lines = Get-Content $dataFile | Where-Object { $_ -match '\S' } # Remove empty lines
"Found $($lines.Count) lines to process" | Tee-Object -FilePath $logFile -Append

try {
    # Connect to the database
    $connection = New-Object System.Data.SqlClient.SqlConnection($connectionString)
    $connection.Open()
    "Connected to database" | Tee-Object -FilePath $logFile -Append

    # Clear existing data
    $clearCommand = New-Object System.Data.SqlClient.SqlCommand("DELETE FROM dbo.Media_National_Champions", $connection)
    $clearCommand.ExecuteNonQuery() | Out-Null
    "Cleared existing data" | Tee-Object -FilePath $logFile -Append

    # Prepare insert command
    $insertSql = "INSERT INTO dbo.Media_National_Champions (ID, Season, Team_Name, Wins, Losses, Ties, Notes) VALUES (@ID, @Season, @Team_Name, @Wins, @Losses, @Ties, @Notes)"
    
    $count = 0
    foreach ($line in $lines) {
        try {
            # Use ConvertFrom-CSV to properly handle quoted fields
            $fields = $line | ConvertFrom-Csv -Header "ID", "Season", "Team_Name", "Wins", "Losses", "Ties", "Notes", "SeasonTeam"
            
            $cmd = New-Object System.Data.SqlClient.SqlCommand($insertSql, $connection)
            
            # Add parameters with values
            $cmd.Parameters.AddWithValue("@ID", $fields.ID) | Out-Null
            $cmd.Parameters.AddWithValue("@Season", $fields.Season) | Out-Null
            $cmd.Parameters.AddWithValue("@Team_Name", $fields.Team_Name) | Out-Null
            $cmd.Parameters.AddWithValue("@Wins", $fields.Wins) | Out-Null
            $cmd.Parameters.AddWithValue("@Losses", $fields.Losses) | Out-Null
            $cmd.Parameters.AddWithValue("@Ties", $fields.Ties) | Out-Null
            $cmd.Parameters.AddWithValue("@Notes", $fields.Notes) | Out-Null
            
            # Execute command
            $cmd.ExecuteNonQuery() | Out-Null
            $count++
            
            if ($count % 10 -eq 0) {
                "Processed $count records..." | Tee-Object -FilePath $logFile -Append
            }
        } catch {
            "Error processing line: $line" | Tee-Object -FilePath $logFile -Append
            "Error: $_" | Tee-Object -FilePath $logFile -Append
        }
    }
} catch {
    "Critical error: $_" | Tee-Object -FilePath $logFile -Append
} finally {
    if ($connection -and $connection.State -eq 'Open') {
        $connection.Close()
        "Database connection closed" | Tee-Object -FilePath $logFile -Append
    }
}

"Imported $count records successfully!" | Tee-Object -FilePath $logFile -Append
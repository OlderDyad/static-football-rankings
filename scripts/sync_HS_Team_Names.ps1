# Define paths and connection string
$excelPath = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\excel_files\HS_Team_Names.xlsx"
$csvPath = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\excel_files\HS_Team_Names.csv"
$logFile = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\scripts\logs\team-names-sync.log"
$connectionString = "Server=MCKNIGHTS-PC\SQLEXPRESS01;Database=hs_football_database;Trusted_Connection=True;TrustServerCertificate=True"

# Ensure log directory exists
$logDir = Split-Path $logFile
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

# Start logging
Get-Date | Out-File $logFile
"Starting HS_Team_Names sync process from Excel via CSV" | Tee-Object -FilePath $logFile -Append

# First, manually export from Excel to CSV
Write-Host "Please manually export the Excel sheet 'HS_Football_Names' to CSV at: $csvPath"
Write-Host "Once exported, press Enter to continue..."
Read-Host | Out-Null

if (-not (Test-Path $csvPath)) {
    Write-Host "CSV file not found. Please export the Excel sheet and try again." -ForegroundColor Red
    exit
}

try {
    # Import CSV
    $csvData = Import-Csv $csvPath
    Write-Host "CSV data loaded: $($csvData.Count) rows"

    # Connect to database
    $connection = New-Object System.Data.SqlClient.SqlConnection($connectionString)
    $connection.Open()
    Write-Host "Database connection established"

    # Get existing SQL data
    $command = New-Object System.Data.SqlClient.SqlCommand(
        "SELECT * FROM HS_Team_Names", $connection)
    $adapter = New-Object System.Data.SqlClient.SqlDataAdapter($command)
    $dataset = New-Object System.Data.DataSet
    $adapter.Fill($dataset)
    $sqlData = $dataset.Tables[0]
    Write-Host "SQL data loaded: $($sqlData.Rows.Count) rows"

    # Compare and sync
    foreach ($csvRow in $csvData) {
        # Clean and prepare team name
        $teamName = $csvRow.Team_Name.Trim()
        
        # Skip if team name is empty
        if ([string]::IsNullOrWhiteSpace($teamName)) {
            Write-Host "Skipping row with empty team name" -ForegroundColor Yellow
            continue
        }
        
        # Check for duplicates in CSV
        $duplicateCount = ($csvData | Where-Object { $_.Team_Name.Trim() -eq $teamName }).Count
        if ($duplicateCount -gt 1) {
            Write-Host "Warning: Duplicate team name found in CSV: $teamName" -ForegroundColor Yellow
            "Warning: Duplicate team name found in CSV: $teamName" | Out-File $logFile -Append
        }
        
        # Find existing row in SQL
        $existingRow = $sqlData.Select("Team_Name = '$teamName'")
        
        # Handle NULL values in CSV
        $city = if ([string]::IsNullOrWhiteSpace($csvRow.City)) { [DBNull]::Value } else { $csvRow.City.Trim() }
        $state = if ([string]::IsNullOrWhiteSpace($csvRow.State)) { [DBNull]::Value } else { $csvRow.State.Trim() }
        $mascot = if ([string]::IsNullOrWhiteSpace($csvRow.Mascot)) { [DBNull]::Value } else { $csvRow.Mascot.Trim() }
        $primaryColor = if ([string]::IsNullOrWhiteSpace($csvRow.PrimaryColor)) { [DBNull]::Value } else { $csvRow.PrimaryColor.Trim() }
        $secondaryColor = if ([string]::IsNullOrWhiteSpace($csvRow.SecondaryColor)) { [DBNull]::Value } else { $csvRow.SecondaryColor.Trim() }
        $tertiaryColor = if ([string]::IsNullOrWhiteSpace($csvRow.TertiaryColor)) { [DBNull]::Value } else { $csvRow.TertiaryColor.Trim() }
        $stadium = if ([string]::IsNullOrWhiteSpace($csvRow.Stadium)) { [DBNull]::Value } else { $csvRow.Stadium.Trim() }
        $yearFounded = if ([string]::IsNullOrWhiteSpace($csvRow.YearFounded)) { [DBNull]::Value } else { [int]$csvRow.YearFounded }
        $conference = if ([string]::IsNullOrWhiteSpace($csvRow.Conference)) { [DBNull]::Value } else { $csvRow.Conference.Trim() }
        $division = if ([string]::IsNullOrWhiteSpace($csvRow.Division)) { [DBNull]::Value } else { $csvRow.Division.Trim() }
        $website = if ([string]::IsNullOrWhiteSpace($csvRow.Website)) { [DBNull]::Value } else { $csvRow.Website.Trim() }
        $logoURL = if ([string]::IsNullOrWhiteSpace($csvRow.LogoURL)) { [DBNull]::Value } else { $csvRow.LogoURL.Trim() }
        $schoolLogoURL = if ([string]::IsNullOrWhiteSpace($csvRow.School_Logo_URL)) { [DBNull]::Value } else { $csvRow.School_Logo_URL.Trim() }
        
        if ($existingRow.Count -gt 0) {
            # Existing team - update
            Write-Host "Updating team: $teamName"
            
            $updateQuery = @"
                UPDATE HS_Team_Names SET
                    City = @City,
                    State = @State,
                    Mascot = @Mascot,
                    PrimaryColor = @PrimaryColor,
                    SecondaryColor = @SecondaryColor,
                    TertiaryColor = @TertiaryColor,
                    Stadium = @Stadium,
                    YearFounded = @YearFounded,
                    Conference = @Conference,
                    Division = @Division,
                    Website = @Website,
                    LogoURL = @LogoURL,
                    School_Logo_URL = @SchoolLogoURL,
                    LastUpdated = GETDATE()
                WHERE Team_Name = @TeamName
"@
            $updateCmd = New-Object System.Data.SqlClient.SqlCommand($updateQuery, $connection)
            
            # Add parameters
            $updateCmd.Parameters.AddWithValue("@TeamName", $teamName)
            $updateCmd.Parameters.AddWithValue("@City", $city)
            $updateCmd.Parameters.AddWithValue("@State", $state)
            $updateCmd.Parameters.AddWithValue("@Mascot", $mascot)
            $updateCmd.Parameters.AddWithValue("@PrimaryColor", $primaryColor)
            $updateCmd.Parameters.AddWithValue("@SecondaryColor", $secondaryColor)
            $updateCmd.Parameters.AddWithValue("@TertiaryColor", $tertiaryColor)
            $updateCmd.Parameters.AddWithValue("@Stadium", $stadium)
            $updateCmd.Parameters.AddWithValue("@YearFounded", $yearFounded)
            $updateCmd.Parameters.AddWithValue("@Conference", $conference)
            $updateCmd.Parameters.AddWithValue("@Division", $division)
            $updateCmd.Parameters.AddWithValue("@Website", $website)
            $updateCmd.Parameters.AddWithValue("@LogoURL", $logoURL)
            $updateCmd.Parameters.AddWithValue("@SchoolLogoURL", $schoolLogoURL)

            $updateCmd.ExecuteNonQuery()
            "Updated: $teamName" | Out-File $logFile -Append -Force
        }
        else {
            # New team - insert
            Write-Host "Adding new team: $teamName"
            
            $insertQuery = @"
                INSERT INTO HS_Team_Names (
                    Team_Name, City, State, Mascot, 
                    PrimaryColor, SecondaryColor, TertiaryColor,
                    Stadium, YearFounded, Conference, Division, 
                    Website, LogoURL, School_Logo_URL, LastUpdated
                ) VALUES (
                    @TeamName, @City, @State, @Mascot,
                    @PrimaryColor, @SecondaryColor, @TertiaryColor,
                    @Stadium, @YearFounded, @Conference, @Division,
                    @Website, @LogoURL, @SchoolLogoURL, GETDATE()
                )
"@
            $insertCmd = New-Object System.Data.SqlClient.SqlCommand($insertQuery, $connection)
            
            # Add parameters
            $insertCmd.Parameters.AddWithValue("@TeamName", $teamName)
            $insertCmd.Parameters.AddWithValue("@City", $city)
            $insertCmd.Parameters.AddWithValue("@State", $state)
            $insertCmd.Parameters.AddWithValue("@Mascot", $mascot) 
            $insertCmd.Parameters.AddWithValue("@PrimaryColor", $primaryColor)
            $insertCmd.Parameters.AddWithValue("@SecondaryColor", $secondaryColor)
            $insertCmd.Parameters.AddWithValue("@TertiaryColor", $tertiaryColor)
            $insertCmd.Parameters.AddWithValue("@Stadium", $stadium)
            $insertCmd.Parameters.AddWithValue("@YearFounded", $yearFounded)
            $insertCmd.Parameters.AddWithValue("@Conference", $conference)
            $insertCmd.Parameters.AddWithValue("@Division", $division)
            $insertCmd.Parameters.AddWithValue("@Website", $website)
            $insertCmd.Parameters.AddWithValue("@LogoURL", $logoURL)
            $insertCmd.Parameters.AddWithValue("@SchoolLogoURL", $schoolLogoURL)

            $insertCmd.ExecuteNonQuery()
            "Inserted: $teamName" | Out-File $logFile -Append -Force
        }
    }

    # Check for teams in SQL but not in CSV
    $csvTeamNames = $csvData | ForEach-Object { $_.Team_Name.Trim() } | Where-Object { ![string]::IsNullOrWhiteSpace($_) }
    
    foreach ($sqlRow in $sqlData.Rows) {
        if ($csvTeamNames -notcontains $sqlRow.Team_Name) {
            Write-Host "Team found in SQL but not in CSV: $($sqlRow.Team_Name)" -ForegroundColor Yellow
            "Team found in SQL but not in CSV: $($sqlRow.Team_Name)" | Out-File $logFile -Append -Force
        }
    }

    # Clean up
    if (Test-Path $csvPath) {
        Remove-Item $csvPath -Force
    }
}
catch {
    Write-Host "Error: $_" -ForegroundColor Red
    $_ | Out-File $logFile -Append -Force
}
finally {
    if ($connection -and $connection.State -eq 'Open') {
        $connection.Close()
        Write-Host "Database connection closed"
    }
}

"Sync process complete" | Tee-Object -FilePath $logFile -Append
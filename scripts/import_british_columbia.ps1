# Clean and import British Columbia scores
$inputPath = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\excel_files\British_Columbia_Scores.txt"
$cleanedPath = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\excel_files\British_Columbia_Scores_Clean.txt"
$sqlServer = "MCKNIGHTS-PC\SQLEXPRESS01"
$database = "hs_football_database"

Write-Host "Step 1: Reading original file..." -ForegroundColor Yellow
$data = Import-Csv -Path $inputPath -Delimiter "`t"
Write-Host "Found $($data.Count) rows in original file" -ForegroundColor Green

Write-Host "Step 2: Cleaning data..." -ForegroundColor Yellow
$cleanedData = @()

foreach ($row in $data) {
    # Create a new clean row
    $cleanRow = [ordered]@{}
    
    # Process each column and clean the data
    foreach ($prop in $row.PSObject.Properties) {
        $name = $prop.Name
        $value = $prop.Value
        
        # Replace 'NULL' with empty string
        if ($value -eq "NULL") {
            $value = ""
        }
        
        # Remove any problematic characters
        if ($value) {
            $value = $value.Trim().Replace("`t", " ").Replace("`r", "").Replace("`n", " ")
        }
        
        # For scores, ensure they're numeric or empty
        if ($name -eq "Visitor Score" -or $name -eq "Home Score" -or $name -eq "Margin" -or $name -eq "OT") {
            if (-not [string]::IsNullOrWhiteSpace($value) -and -not [int]::TryParse($value, [ref]$null)) {
                Write-Host "Non-numeric value found: '$value' in column $name - will be cleared" -ForegroundColor Red
                $value = ""
            }
        }
        
        # Add to clean row
        $cleanRow[$name] = $value
    }
    
    # Add to clean data array
    $cleanedData += [PSCustomObject]$cleanRow
}

Write-Host "Step 3: Saving cleaned data..." -ForegroundColor Yellow
$cleanedData | Export-Csv -Path $cleanedPath -Delimiter "`t" -NoTypeInformation -Encoding UTF8
Write-Host "Cleaned data saved to $cleanedPath" -ForegroundColor Green

Write-Host "Step 4: Importing cleaned data..." -ForegroundColor Yellow
# Connect to SQL Server
$connectionString = "Server=$sqlServer;Database=$database;Integrated Security=True;"
$connection = New-Object System.Data.SqlClient.SqlConnection
$connection.ConnectionString = $connectionString

try {
    $connection.Open()
    Write-Host "Successfully connected to database" -ForegroundColor Green
    
    # Insert SQL statement
    $insertSql = @"
    INSERT INTO [dbo].[HS_Scores]
    ([Date], [Season], [Home], [Visitor], [Neutral], [Location], [Location2],
     [Line], [Future_Game], [Source], [Date_Added], [OT], [Forfeit],
     [ID], [Visitor_Score], [Home_Score], [Margin], [Access_ID])
    VALUES
    (@Date, @Season, @Home, @Visitor, @Neutral, @Location, @Location2,
     @Line, @FutureGame, @Source, @DateAdded, @OT, @Forfeit,
     NEWID(), @VisitorScore, @HomeScore, @Margin, NULL)
"@
    
    $cmd = New-Object System.Data.SqlClient.SqlCommand($insertSql, $connection)
    
    # Add parameters
    $cmd.Parameters.Add("@Date", [System.Data.SqlDbType]::Date)
    $cmd.Parameters.Add("@Season", [System.Data.SqlDbType]::Int)
    $cmd.Parameters.Add("@Home", [System.Data.SqlDbType]::VarChar, 255)
    $cmd.Parameters.Add("@Visitor", [System.Data.SqlDbType]::VarChar, 255)
    $cmd.Parameters.Add("@Neutral", [System.Data.SqlDbType]::Bit)
    $cmd.Parameters.Add("@Location", [System.Data.SqlDbType]::VarChar, 255)
    $cmd.Parameters.Add("@Location2", [System.Data.SqlDbType]::VarChar, 255)
    $cmd.Parameters.Add("@Line", [System.Data.SqlDbType]::VarChar, 50)
    $cmd.Parameters.Add("@FutureGame", [System.Data.SqlDbType]::Bit)
    $cmd.Parameters.Add("@Source", [System.Data.SqlDbType]::VarChar, 255)
    $cmd.Parameters.Add("@DateAdded", [System.Data.SqlDbType]::DateTime)
    $cmd.Parameters.Add("@OT", [System.Data.SqlDbType]::Int)
    $cmd.Parameters.Add("@Forfeit", [System.Data.SqlDbType]::Bit)
    $cmd.Parameters.Add("@VisitorScore", [System.Data.SqlDbType]::Int)
    $cmd.Parameters.Add("@HomeScore", [System.Data.SqlDbType]::Int)
    $cmd.Parameters.Add("@Margin", [System.Data.SqlDbType]::Int)
    
    # Initialize counters
    $successCount = 0
    $errorCount = 0
    $totalRows = $cleanedData.Count
    
    # Process each row
    foreach ($row in $cleanedData) {
        try {
            # Reset parameters
            foreach ($param in $cmd.Parameters) {
                $param.Value = [System.DBNull]::Value
            }
            
            # Date
            if (-not [string]::IsNullOrWhiteSpace($row.Date)) {
                try {
                    $cmd.Parameters["@Date"].Value = [DateTime]::Parse($row.Date)
                } catch {
                    # If date parsing fails, leave as null
                }
            }
            
            # Season
            if (-not [string]::IsNullOrWhiteSpace($row.Season)) {
                try {
                    $cmd.Parameters["@Season"].Value = [int]::Parse($row.Season)
                } catch {
                    # If parsing fails, leave as null
                }
            }
            
            # Home team
            $homeTeam = $row.Home
            if (-not [string]::IsNullOrWhiteSpace($homeTeam)) {
                $cmd.Parameters["@Home"].Value = $homeTeam
            }
            
            # Visitor team
            $visitorTeam = $row.Visitor
            if (-not [string]::IsNullOrWhiteSpace($visitorTeam)) {
                $cmd.Parameters["@Visitor"].Value = $visitorTeam
            }
            
            # Neutral site
            $neutral = if ($row.PSObject.Properties.Name -contains "Nuetral") { $row.Nuetral } else { $row.Neutral }
            $neutralValue = if ($neutral -eq "TRUE") { 1 } else { 0 }
            $cmd.Parameters["@Neutral"].Value = $neutralValue
            
            # Location fields
            if (-not [string]::IsNullOrWhiteSpace($row.Location)) {
                $cmd.Parameters["@Location"].Value = $row.Location
            }
            
            if (-not [string]::IsNullOrWhiteSpace($row.Location2)) {
                $cmd.Parameters["@Location2"].Value = $row.Location2
            }
            
            # Line
            if (-not [string]::IsNullOrWhiteSpace($row.Line)) {
                $cmd.Parameters["@Line"].Value = $row.Line
            }
            
            # Future game
            $futureGame = if ($row.PSObject.Properties.Name -contains "Future Game") { $row.'Future Game' } else { "FALSE" }
            $futureGameValue = if ($futureGame -eq "TRUE") { 1 } else { 0 }
            $cmd.Parameters["@FutureGame"].Value = $futureGameValue
            
            # Source
            if (-not [string]::IsNullOrWhiteSpace($row.Source)) {
                $cmd.Parameters["@Source"].Value = $row.Source
            }
            
            # Date added
            $cmd.Parameters["@DateAdded"].Value = Get-Date
            
            # OT
            if (-not [string]::IsNullOrWhiteSpace($row.OT)) {
                try {
                    $cmd.Parameters["@OT"].Value = [int]::Parse($row.OT)
                } catch {
                    # Leave as null
                }
            }
            
            # Forfeit
            $forfeitValue = if ($row.Forfeit -eq "TRUE") { 1 } else { 0 }
            $cmd.Parameters["@Forfeit"].Value = $forfeitValue
            
            # Scores
            $visitorScoreField = if ($row.PSObject.Properties.Name -contains "Visitor Score") { "Visitor Score" } else { "VisitorScore" }
            if (-not [string]::IsNullOrWhiteSpace($row.$visitorScoreField)) {
                try {
                    $cmd.Parameters["@VisitorScore"].Value = [int]::Parse($row.$visitorScoreField)
                } catch {
                    # Leave as null
                }
            }
            
            $homeScoreField = if ($row.PSObject.Properties.Name -contains "Home Score") { "Home Score" } else { "HomeScore" }
            if (-not [string]::IsNullOrWhiteSpace($row.$homeScoreField)) {
                try {
                    $cmd.Parameters["@HomeScore"].Value = [int]::Parse($row.$homeScoreField)
                } catch {
                    # Leave as null
                }
            }
            
            # Margin
            if (-not [string]::IsNullOrWhiteSpace($row.Margin)) {
                try {
                    $cmd.Parameters["@Margin"].Value = [int]::Parse($row.Margin)
                } catch {
                    # Leave as null
                }
            }
            
            # Execute insert
            $cmd.ExecuteNonQuery() | Out-Null
            $successCount++
            
            # Show progress
            if ($successCount % 100 -eq 0 -or $successCount -eq 1 -or $successCount -eq $totalRows) {
                Write-Host "Progress: $successCount of $totalRows rows processed ($([math]::Round(($successCount/$totalRows) * 100))%)" -ForegroundColor Green
            }
        }
        catch {
            $errorCount++
            Write-Host "Error importing row: $($row.Date) $($row.Home) vs $($row.Visitor)" -ForegroundColor Red
            Write-Host $_.Exception.Message -ForegroundColor Red
            
            if ($errorCount -gt 10) {
                Write-Host "Too many errors, stopping import" -ForegroundColor Red
                break
            }
        }
    }
    
    # Close connection
    $connection.Close()
    
    # Final results
    Write-Host "Import complete: $successCount rows imported successfully, $errorCount errors" -ForegroundColor Green
}
catch {
    Write-Host "Connection error: $($_.Exception.Message)" -ForegroundColor Red
    if ($connection.State -eq 'Open') {
        $connection.Close()
    }
}
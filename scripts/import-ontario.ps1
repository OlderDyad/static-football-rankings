# Full import for Ontario scores with fixed TryParse
$inputPath = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\excel_files\Ontario_Scores_Clean.txt"
$sqlServer = "MCKNIGHTS-PC\SQLEXPRESS01" # Update with your server name
$database = "hs_football_database"       # Update with your database name

# Read the cleaned file
$data = Import-Csv -Path $inputPath -Delimiter "`t"
Write-Host "Found $($data.Count) rows to import" -ForegroundColor Green

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
    $totalRows = $data.Count
    
    # Process each row
    foreach ($row in $data) {
        try {
            # Reset parameters
            foreach ($param in $cmd.Parameters) {
                $param.Value = [System.DBNull]::Value
            }
            
            # Date - Simpler approach
            if (-not [string]::IsNullOrWhiteSpace($row.Date)) {
                try {
                    $cmd.Parameters["@Date"].Value = [DateTime]::Parse($row.Date)
                } catch {
                    # If date parsing fails, leave as null
                }
            }
            
            # Season - Simpler approach
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
                if ($homeTeam -like "*(Ont)") {
                    $homeTeam = $homeTeam.Substring(0, $homeTeam.Length - 5) + " (ON)"
                }
                $cmd.Parameters["@Home"].Value = $homeTeam
            }
            
            # Visitor team
            $visitorTeam = $row.Visitor
            if (-not [string]::IsNullOrWhiteSpace($visitorTeam)) {
                if ($visitorTeam -like "*(Ont)") {
                    $visitorTeam = $visitorTeam.Substring(0, $visitorTeam.Length - 5) + " (ON)"
                }
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
            
            # Date added - simpler approach
            $dateAddedField = if ($row.PSObject.Properties.Name -contains "Date Added") { "Date Added" } else { "DateAdded" }
            if (-not [string]::IsNullOrWhiteSpace($row.$dateAddedField)) {
                try {
                    $cmd.Parameters["@DateAdded"].Value = [DateTime]::Parse($row.$dateAddedField)
                } catch {
                    $cmd.Parameters["@DateAdded"].Value = Get-Date
                }
            } else {
                $cmd.Parameters["@DateAdded"].Value = Get-Date
            }
            
            # OT - simpler approach
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
            
            # Scores - simpler approach
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
            
            # Margin - simpler approach
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
            
            if ($errorCount -gt 50) {
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
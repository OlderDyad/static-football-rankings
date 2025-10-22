# PowerShell script to import CSV scores
$csvPath = "H:\Users\demck\Google Drive\Documents\Football\HSF\Newspapers\Staged\cleaned_scores.csv"
$sqlServer = "MCKNIGHTS-PC\SQLEXPRESS01"
$database = "hs_football_database"

# Read the CSV file
$data = Import-Csv -Path $csvPath
Write-Host "Found $($data.Count) rows to import" -ForegroundColor Green

# Connect to SQL Server
$connectionString = "Server=$sqlServer;Database=$database;Integrated Security=True;"
$connection = New-Object System.Data.SqlClient.SqlConnection
$connection.ConnectionString = $connectionString

try {
    $connection.Open()
    Write-Host "Successfully connected to database" -ForegroundColor Green
    
    # Insert SQL statement (adjust fields as needed)
    $insertSql = @"
    INSERT INTO [dbo].[HS_Scores]
    ([Home], [Home_Score], [Visitor], [Visitor_Score], [Forfeit], [ID], [Season], [Date], [Date_Added])
    VALUES
    (@Home, @HomeScore, @Visitor, @VisitorScore, @Forfeit, NEWID(), 2024, GETDATE(), GETDATE())
"@
    
    $cmd = New-Object System.Data.SqlClient.SqlCommand($insertSql, $connection)
    
    # Add parameters (adjust as needed)
    $cmd.Parameters.Add("@Home", [System.Data.SqlDbType]::VarChar, 255)
    $cmd.Parameters.Add("@HomeScore", [System.Data.SqlDbType]::Int)
    $cmd.Parameters.Add("@Visitor", [System.Data.SqlDbType]::VarChar, 255)
    $cmd.Parameters.Add("@VisitorScore", [System.Data.SqlDbType]::Int)
    $cmd.Parameters.Add("@Forfeit", [System.Data.SqlDbType]::Bit)
    
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
            
            # Set parameters
            $cmd.Parameters["@Home"].Value = $row.Home
            
            if (-not [string]::IsNullOrWhiteSpace($row.Home_Score)) {
                try {
                    $cmd.Parameters["@HomeScore"].Value = [int]::Parse($row.Home_Score)
                } catch {
                    # Leave as null
                }
            }
            
            $cmd.Parameters["@Visitor"].Value = $row.Visitor
            
            if (-not [string]::IsNullOrWhiteSpace($row.Visitor_Score)) {
                try {
                    $cmd.Parameters["@VisitorScore"].Value = [int]::Parse($row.Visitor_Score)
                } catch {
                    # Leave as null
                }
            }
            
            $cmd.Parameters["@Forfeit"].Value = if ($row.Forfeit -eq "True") { 1 } else { 0 }
            
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
            Write-Host "Error importing row: $($row.Home) vs $($row.Visitor)" -ForegroundColor Red
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
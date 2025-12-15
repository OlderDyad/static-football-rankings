# ============================================================================
# LoneStar Excel to SQL Importer (PowerShell)
# ============================================================================
# Reads directly from Excel workbook, converts formats, imports to staging table
# ============================================================================

$excelPath = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\excel_files\HSF Texas 2025.xlsx"
$sheetName = "Lonestar"
$serverName = "McKnights-PC\SQLEXPRESS01"
$databaseName = "hs_football_database"

Write-Host "=== LoneStar Excel to SQL Importer ===" -ForegroundColor Cyan
Write-Host "Excel File: $excelPath" -ForegroundColor Gray
Write-Host "Sheet: $sheetName" -ForegroundColor Gray

# ============================================================================
# STEP 1: Open Excel and Read Data
# ============================================================================

Write-Host "`nOpening Excel workbook..." -ForegroundColor Yellow

$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false

try {
    $workbook = $excel.Workbooks.Open($excelPath)
    $worksheet = $workbook.Worksheets.Item($sheetName)
    
    # Find last row with data
    $lastRow = $worksheet.UsedRange.Rows.Count
    Write-Host "Found $lastRow rows in worksheet" -ForegroundColor Green
    
    # Column mapping (Excel columns AA through AP = columns 27 through 42)
    # AA=27, AB=28, AC=29, AD=30, AE=31, AF=32, AG=33, AH=34, AI=35, AJ=36, AK=37, AL=38, AM=39, AN=40, AO=41, AP=42
    
    $colDate = 27          # AA
    $colSeason = 28        # AB
    $colVisitor = 29       # AC
    $colVisitorScore = 30  # AD
    $colHome = 31          # AE
    $colHomeScore = 32     # AF
    $colMargin = 33        # AG
    $colNeutral = 34       # AH
    $colLocation = 35      # AI
    $colLocation2 = 36     # AJ
    $colLine = 37          # AK
    $colFutureGame = 38    # AL
    $colSource = 39        # AM
    $colOT = 40            # AN
    $colForfeit = 41       # AO (last is 42=AP but you said Forfeit is last, so using 41)
    
    Write-Host "Reading data from columns AA through AP (27-42)..." -ForegroundColor Yellow
    
    # Read all data into memory
    $dataRows = @()
    $headerRow = 1  # Assuming row 1 is headers
    $startRow = 2   # Data starts at row 2
    
    for ($row = $startRow; $row -le $lastRow; $row++) {
        # Show progress
        if (($row - $startRow) % 500 -eq 0) {
            Write-Host "Reading row $row of $lastRow..." -ForegroundColor Gray
        }
        
        # Read each cell
        $dateValue = $worksheet.Cells.Item($row, $colDate).Value2
        $seasonValue = $worksheet.Cells.Item($row, $colSeason).Value2
        $visitorValue = $worksheet.Cells.Item($row, $colVisitor).Value2
        $visitorScoreValue = $worksheet.Cells.Item($row, $colVisitorScore).Value2
        $homeValue = $worksheet.Cells.Item($row, $colHome).Value2
        $homeScoreValue = $worksheet.Cells.Item($row, $colHomeScore).Value2
        $marginValue = $worksheet.Cells.Item($row, $colMargin).Value2
        $neutralValue = $worksheet.Cells.Item($row, $colNeutral).Value2
        $locationValue = $worksheet.Cells.Item($row, $colLocation).Value2
        $location2Value = $worksheet.Cells.Item($row, $colLocation2).Value2
        $lineValue = $worksheet.Cells.Item($row, $colLine).Value2
        $futureGameValue = $worksheet.Cells.Item($row, $colFutureGame).Value2
        $sourceValue = $worksheet.Cells.Item($row, $colSource).Value2
        $otValue = $worksheet.Cells.Item($row, $colOT).Value2
        $forfeitValue = $worksheet.Cells.Item($row, $colForfeit).Value2
        
        # Skip if essential fields are empty
        if (-not $homeValue -or -not $visitorValue) {
            continue
        }
        
        # Convert Excel date serial number to actual date
        if ($dateValue -is [double]) {
            $dateValue = [DateTime]::FromOADate($dateValue)
        }
        
        $dataRows += [PSCustomObject]@{
            Date = $dateValue
            Season = $seasonValue
            Visitor = $visitorValue
            Visitor_Score = $visitorScoreValue
            Home = $homeValue
            Home_Score = $homeScoreValue
            Margin = $marginValue
            Neutral = $neutralValue
            Location = $locationValue
            Location2 = $location2Value
            Line = $lineValue
            Future_Game = $futureGameValue
            Source = $sourceValue
            OT = $otValue
            Forfeit = $forfeitValue
        }
    }
    
    Write-Host "`nLoaded $($dataRows.Count) data rows from Excel" -ForegroundColor Green
    
}
catch {
    Write-Host "Error reading Excel: $_" -ForegroundColor Red
    exit
}
finally {
    # Close Excel
    $workbook.Close($false)
    $excel.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($worksheet) | Out-Null
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($workbook) | Out-Null
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($excel) | Out-Null
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
    Write-Host "Excel closed" -ForegroundColor Gray
}

if ($dataRows.Count -eq 0) {
    Write-Host "No data found to import!" -ForegroundColor Red
    exit
}

# Show sample
Write-Host "`nFirst row sample:" -ForegroundColor Yellow
$dataRows[0] | Format-List

# ============================================================================
# STEP 2: Connect to SQL Server and Import
# ============================================================================

Write-Host "`nConnecting to SQL Server..." -ForegroundColor Yellow

$connectionString = "Server=$serverName;Database=$databaseName;Integrated Security=True;TrustServerCertificate=True;"
$connection = New-Object System.Data.SqlClient.SqlConnection($connectionString)

try {
    $connection.Open()
    Write-Host "Connected to SQL Server" -ForegroundColor Green
    
    # Get next BatchID
    $batchCmd = $connection.CreateCommand()
    $batchCmd.CommandText = "SELECT ISNULL(MAX(BatchID), 0) + 1 FROM dbo.HS_Scores_LoneStar_Staging"
    $batchID = $batchCmd.ExecuteScalar()
    Write-Host "Using Batch ID: $batchID" -ForegroundColor Cyan
    
    # Prepare insert command
    $insertCmd = $connection.CreateCommand()
    $insertCmd.CommandText = @"
INSERT INTO dbo.HS_Scores_LoneStar_Staging (
    [Date], Season, Home, Visitor, Neutral, Location, Location2, 
    Line, Future_Game, Source, OT, Forfeit, Visitor_Score, Home_Score, 
    Margin, BatchID, Status
)
VALUES (
    @Date, @Season, @Home, @Visitor, @Neutral, @Location, @Location2,
    @Line, @Future_Game, @Source, @OT, @Forfeit, @Visitor_Score, @Home_Score,
    @Margin, @BatchID, 'Pending'
)
"@
    
    # Add parameters
    [void]$insertCmd.Parameters.Add("@Date", [System.Data.SqlDbType]::Date)
    [void]$insertCmd.Parameters.Add("@Season", [System.Data.SqlDbType]::Int)
    [void]$insertCmd.Parameters.Add("@Home", [System.Data.SqlDbType]::VarChar, 111)
    [void]$insertCmd.Parameters.Add("@Visitor", [System.Data.SqlDbType]::VarChar, 111)
    [void]$insertCmd.Parameters.Add("@Neutral", [System.Data.SqlDbType]::Bit)
    [void]$insertCmd.Parameters.Add("@Location", [System.Data.SqlDbType]::VarChar, 111)
    [void]$insertCmd.Parameters.Add("@Location2", [System.Data.SqlDbType]::VarChar, 255)
    [void]$insertCmd.Parameters.Add("@Line", [System.Data.SqlDbType]::Int)
    [void]$insertCmd.Parameters.Add("@Future_Game", [System.Data.SqlDbType]::Bit)
    [void]$insertCmd.Parameters.Add("@Source", [System.Data.SqlDbType]::VarChar, 255)
    [void]$insertCmd.Parameters.Add("@OT", [System.Data.SqlDbType]::Int)
    [void]$insertCmd.Parameters.Add("@Forfeit", [System.Data.SqlDbType]::Bit)
    [void]$insertCmd.Parameters.Add("@Visitor_Score", [System.Data.SqlDbType]::Int)
    [void]$insertCmd.Parameters.Add("@Home_Score", [System.Data.SqlDbType]::Int)
    [void]$insertCmd.Parameters.Add("@Margin", [System.Data.SqlDbType]::Int)
    [void]$insertCmd.Parameters.Add("@BatchID", [System.Data.SqlDbType]::Int)
    
    # Insert rows
    $successCount = 0
    $errorCount = 0
    $errors = @()
    
    Write-Host "`nImporting data..." -ForegroundColor Yellow
    
    foreach ($row in $dataRows) {
        try {
            # Date
            if ($row.Date -is [DateTime]) {
                $insertCmd.Parameters["@Date"].Value = $row.Date
            } else {
                # Try to parse
                $insertCmd.Parameters["@Date"].Value = [DateTime]::Parse($row.Date)
            }
            
            # Season
            $insertCmd.Parameters["@Season"].Value = [int]$row.Season
            
            # Team names
            $insertCmd.Parameters["@Home"].Value = $row.Home
            $insertCmd.Parameters["@Visitor"].Value = $row.Visitor
            
            # Scores
            $insertCmd.Parameters["@Visitor_Score"].Value = [int]$row.Visitor_Score
            $insertCmd.Parameters["@Home_Score"].Value = [int]$row.Home_Score
            $insertCmd.Parameters["@Margin"].Value = [int]$row.Margin
            
            # Neutral (handle TRUE/FALSE, 1/0, or actual boolean)
            if ($row.Neutral -eq $true -or $row.Neutral -eq "TRUE" -or $row.Neutral -eq 1) {
                $insertCmd.Parameters["@Neutral"].Value = 1
            } else {
                $insertCmd.Parameters["@Neutral"].Value = 0
            }
            
            # Location (handle "Unknown" and nulls)
            if ($row.Location -and $row.Location -ne "Unknown" -and $row.Location -ne "") {
                $insertCmd.Parameters["@Location"].Value = $row.Location
            } else {
                $insertCmd.Parameters["@Location"].Value = [DBNull]::Value
            }
            
            # Location2
            if ($row.Location2) {
                $insertCmd.Parameters["@Location2"].Value = $row.Location2
            } else {
                $insertCmd.Parameters["@Location2"].Value = [DBNull]::Value
            }
            
            # Line
            if ($row.Line) {
                $insertCmd.Parameters["@Line"].Value = [int]$row.Line
            } else {
                $insertCmd.Parameters["@Line"].Value = [DBNull]::Value
            }
            
            # Future_Game
            if ($row.Future_Game -eq $true -or $row.Future_Game -eq "TRUE" -or $row.Future_Game -eq 1) {
                $insertCmd.Parameters["@Future_Game"].Value = 1
            } else {
                $insertCmd.Parameters["@Future_Game"].Value = [DBNull]::Value
            }
            
            # Source
            $insertCmd.Parameters["@Source"].Value = if ($row.Source) { $row.Source } else { "LoneStar" }
            
            # OT
            if ($row.OT) {
                $insertCmd.Parameters["@OT"].Value = [int]$row.OT
            } else {
                $insertCmd.Parameters["@OT"].Value = [DBNull]::Value
            }
            
            # Forfeit
            if ($row.Forfeit -eq $true -or $row.Forfeit -eq "TRUE" -or $row.Forfeit -eq 1) {
                $insertCmd.Parameters["@Forfeit"].Value = 1
            } else {
                $insertCmd.Parameters["@Forfeit"].Value = [DBNull]::Value
            }
            
            # BatchID
            $insertCmd.Parameters["@BatchID"].Value = $batchID
            
            # Execute insert
            [void]$insertCmd.ExecuteNonQuery()
            $successCount++
            
            # Progress indicator
            if ($successCount % 100 -eq 0) {
                Write-Host "Imported $successCount rows..." -ForegroundColor Gray
            }
        }
        catch {
            $errorCount++
            $errorMsg = "Row $($successCount + $errorCount): $_ | Home: $($row.Home) | Visitor: $($row.Visitor) | Date: $($row.Date)"
            $errors += $errorMsg
            
            if ($errorCount -le 10) {
                Write-Host $errorMsg -ForegroundColor Yellow
            }
        }
    }
    
    Write-Host "`n=== IMPORT COMPLETE ===" -ForegroundColor Green
    Write-Host "Successfully imported: $successCount rows" -ForegroundColor Green
    Write-Host "Errors: $errorCount rows" -ForegroundColor $(if ($errorCount -gt 0) { "Yellow" } else { "Green" })
    Write-Host "Batch ID: $batchID" -ForegroundColor Cyan
    
    if ($errors.Count -gt 0) {
        Write-Host "`nFirst 10 errors:" -ForegroundColor Yellow
        $errors | Select-Object -First 10 | ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
        
        # Save all errors to file
        $errorFile = "C:\Temp\lonestar_import_errors_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"
        $errors | Out-File -FilePath $errorFile -Encoding UTF8
        Write-Host "`nAll errors saved to: $errorFile" -ForegroundColor Yellow
    }
    
    Write-Host "`n=== NEXT STEPS ===" -ForegroundColor Cyan
    Write-Host "1. Verify data in staging table:" -ForegroundColor White
    Write-Host "   SELECT TOP 10 * FROM HS_Scores_LoneStar_Staging WHERE BatchID = $batchID" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. Run validation and import to production:" -ForegroundColor White
    Write-Host "   EXEC dbo.sp_Import_LoneStar_Batch @BatchID = $batchID" -ForegroundColor Gray
    Write-Host ""
}
catch {
    Write-Host "Database error: $_" -ForegroundColor Red
}
finally {
    if ($connection.State -eq 'Open') {
        $connection.Close()
        Write-Host "`nDatabase connection closed" -ForegroundColor Gray
    }
}
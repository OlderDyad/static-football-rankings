# Bulk-Load-RawText-Files.ps1

# --- CONFIGURATION ---
$sourceFolder = "J:\Users\demck\Google Drive\Documents\Football\HSF\Newspapers\Completed"
$sqlServer = "MCKNIGHTS-PC\SQLEXPRESS01"
$database = "hs_football_database"
# --- End Configuration ---

# --- SCRIPT LOGIC ---
Write-Host "Starting bulk load of raw score data from text files..." -ForegroundColor Green
Write-Host "Source Folder: $sourceFolder"

if (-not (Test-Path $sourceFolder)) {
    Write-Host "ERROR: Source folder not found." -ForegroundColor Red
    exit
}

try {
    # Connect to the database
    $connectionString = "Server=$sqlServer;Database=$database;Integrated Security=True;"
    $connection = New-Object System.Data.SqlClient.SqlConnection($connectionString)
    $connection.Open()
    Write-Host "Successfully connected to database."

    # Optional: Truncate the table for a clean run
    $confirmation = Read-Host "Do you want to clear all existing data from [dbo.RawScoreData] first? (y/n)"
    if ($confirmation -eq 'y') {
        Write-Host "Clearing [dbo.RawScoreData] table..."
        $truncateCmd = $connection.CreateCommand()
        $truncateCmd.CommandText = "TRUNCATE TABLE dbo.RawScoreData"
        $truncateCmd.ExecuteNonQuery()
        Write-Host "Table cleared." -ForegroundColor Yellow
    }

    # Get all .txt files from the source folder and its subdirectories
    $files = Get-ChildItem -Path $sourceFolder -Filter "*.txt" -Recurse
    $fileCount = $files.Count
    Write-Host "Found $fileCount text files to process."

    $totalLinesInserted = 0
    $fileIndex = 0

    # Prepare the INSERT command once for efficiency
    $insertCmd = $connection.CreateCommand()
    $insertCmd.CommandText = "INSERT INTO dbo.RawScoreData (SourceFile, RawLineText) VALUES (@SourceFile, @RawLine)"
    $insertCmd.Parameters.Add("@SourceFile", [System.Data.SqlDbType]::NVarChar, 255) | Out-Null
    $insertCmd.Parameters.Add("@RawLine", [System.Data.SqlDbType]::NVarChar, 500) | Out-Null

    # Loop through each file
    foreach ($file in $files) {
        $fileIndex++
        Write-Host "Processing file $fileIndex of $fileCount : $($file.Name)"
        $lines = Get-Content $file.FullName

        # Loop through each line in the current file
        foreach ($line in $lines) {
            if (-not [string]::IsNullOrWhiteSpace($line)) {
                $insertCmd.Parameters["@SourceFile"].Value = $file.Name
                $insertCmd.Parameters["@RawLine"].Value = $line.Trim()
                $insertCmd.ExecuteNonQuery() | Out-Null
                $totalLinesInserted++
            }
        }
    }

    Write-Host "---"
    Write-Host "BULK LOAD COMPLETE!" -ForegroundColor Green
    Write-Host "Total lines inserted into [dbo.RawScoreData]: $totalLinesInserted"

}
catch {
    Write-Host "AN ERROR OCCURRED: $_" -ForegroundColor Red
}
finally {
    if ($connection -and $connection.State -eq 'Open') {
        $connection.Close()
        Write-Host "Database connection closed."
    }
}
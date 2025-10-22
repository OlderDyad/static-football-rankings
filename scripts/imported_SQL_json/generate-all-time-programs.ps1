# Add to start of generate-all-time-programs.ps1
$logFile = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\scripts\imported_SQL_json\logs\all-time-programs.log"
$outputDir = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\docs\data\all-time"

# Ensure directories exist and clear old files
New-Item -ItemType Directory -Force -Path (Split-Path $logFile)
New-Item -ItemType Directory -Force -Path $outputDir
Remove-Item "$outputDir\all-time-programs-*.json" -ErrorAction SilentlyContinue

# Start logging
Get-Date | Out-File $logFile
"Starting all-time programs generation" | Tee-Object -FilePath $logFile -Append

# Import common functions
. ".\common-functions.ps1"

$outputDir = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\docs\data\all-time"
if (Test-Path $outputDir) {
    Remove-Item "$outputDir\all-time-programs-*.json"
} else {
    New-Item -ItemType Directory -Path $outputDir -Force
}

try {
    $connection = Connect-Database
    Write-Host "Database connection established"

    @(25, 50, 100) | ForEach-Object {
        $minSeasons = $_
        Write-Host "`nProcessing $minSeasons+ seasons programs..."
        
        $command = New-Object System.Data.SqlClient.SqlCommand("EXEC GetAllTimePrograms @MinSeasons", $connection)
        $command.Parameters.AddWithValue("@MinSeasons", $minSeasons)
        
        $adapter = New-Object System.Data.SqlClient.SqlDataAdapter($command)
        $programsDataset = New-Object System.Data.DataSet
        $adapter.Fill($programsDataset)

        if ($programsDataset.Tables[0].Rows.Count -gt 0) {
            $metadata = Get-TeamMetadata -connection $connection -TeamName $programsDataset.Tables[0].Rows[0].program -isProgram $true
            $jsonData = Format-ProgramData -programs $programsDataset.Tables[0] -metadata $metadata -description "All-time top programs ($minSeasons+ seasons)"
            
            $outputPath = Join-Path $outputDir "all-time-programs-$minSeasons.json"
            Write-Host "Writing to $outputPath"
            $jsonData | ConvertTo-Json -Depth 10 | Set-Content -Path $outputPath -Force
        }

        if (Test-Path $outputPath) {
            $lastWriteTime = (Get-Item $outputPath).LastWriteTime
            Write-Host "File written: $outputPath (Last Modified: $lastWriteTime)"
        } else {
            Write-Host "File write failed: $outputPath" -ForegroundColor Red
        }
    }
}
catch {
    Write-Host "Error: $_" -ForegroundColor Red
}
finally {
    if ($connection -and $connection.State -eq 'Open') {
        $connection.Close()
    }
}

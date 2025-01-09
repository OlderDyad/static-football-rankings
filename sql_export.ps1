# sql_export.ps1
$ScriptPath = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings"
$ServerName = "MCKNIGHTS-PC\SQLEXPRESS01"
$DatabaseName = "hs_football_database"
$OutputDir = Join-Path $ScriptPath "data"
$LogFile = Join-Path $ScriptPath "export_log.txt"

# Ensure output directory exists
if (-not (Test-Path $OutputDir)) {
    New-Item -Path $OutputDir -ItemType Directory -Force
}

# Function to log messages
function Write-Log {
    param($Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "$timestamp - $Message"
    Write-Host $logMessage
    Add-Content -Path $LogFile -Value $logMessage
}

Write-Log "Script started"

try {
    Write-Log "Executing SQL query..."
    $results = Invoke-Sqlcmd -ServerInstance $ServerName -Database $DatabaseName -Query $query -QueryTimeout 120 -MaxCharLength 1000000
    
    if ($results) {
        Write-Log "Results received. Processing JSON data..."
        
        $jsonData = $results.JsonData
        Write-Log "JSON data length: $($jsonData.Length) characters"
        
        # Validate JSON before saving
        try {
            $null = $jsonData | ConvertFrom-Json
            Write-Log "JSON validation successful"
            
            # Save to file
            $outputPath = Join-Path $OutputDir "all-time-programs-fifty.json"
            [System.IO.File]::WriteAllText($outputPath, $jsonData, [System.Text.Encoding]::UTF8)
            Write-Log "File saved successfully to: $outputPath"
            
            # Verify file size
            $fileInfo = Get-Item $outputPath
            Write-Log "File size: $($fileInfo.Length) bytes"
        }
        catch {
            Write-Log "ERROR: Invalid JSON data:"
            Write-Log $_.Exception.Message
        }
    }
    else {
        Write-Log "No results returned from query"
    }
}
catch {
    Write-Log "Error executing query:"
    Write-Log $_.Exception.Message
}

Write-Log "Script completed"

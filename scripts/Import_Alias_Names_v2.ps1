# Import Alias Names and Update Database Records (v2 - Corrected)
# This version correctly uses the 'Standardized_Name' column and allows for a dynamic file path.

param (
    [Parameter(Mandatory=$true)]
    [string]$AliasFilePath, # e.g., "C:\path\to\your\MA_Alais_Proper.csv"

    [Parameter(Mandatory=$false)]
    [string]$StateFilter = $null # Optional state filter e.g. "(MA)"
)

# --- Configuration ---
$sqlServer = "MCKNIGHTS-PC\SQLEXPRESS01"
$database = "hs_football_database"
$logFile = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\scripts\logs\alias_import_log_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"

# --- Script Body ---
# Create log directory if it doesn't exist
$logDir = Split-Path $logFile -Parent
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

# Start logging
Start-Transcript -Path $logFile -Force
Write-Host "Starting Alias Names Import at $(Get-Date)"
Write-Host "Source file: $AliasFilePath"
if ($StateFilter) {
    Write-Host "State filter: $StateFilter"
}

# Verify file exists
if (-not (Test-Path $AliasFilePath)) {
    Write-Host "ERROR: Source file not found at $AliasFilePath" -ForegroundColor Red
    Stop-Transcript
    exit 1
}

try {
    # Read CSV file - Expects headers 'Alias_Name' and 'Standardized_Name'
    Write-Host "Reading alias CSV file..."
    $aliases = Import-Csv -Path $AliasFilePath -Encoding UTF8

    # Filter aliases by state if specified
    if ($StateFilter) {
        $filteredAliases = $aliases | Where-Object { 
            ($_.Alias_Name -like "*$StateFilter*")
        }
        Write-Host "Filtered from $($aliases.Count) to $($filteredAliases.Count) aliases for state $StateFilter" -ForegroundColor Yellow
        $aliases = $filteredAliases
    }

    # Check for duplicate aliases in the source file
    Write-Host "Checking for duplicate aliases in CSV file..."
    $duplicateAliases = $aliases | Group-Object -Property Alias_Name | Where-Object { $_.Count -gt 1 }
    
    if ($duplicateAliases.Count -gt 0) {
        Write-Host "ERROR: Duplicate aliases found in CSV file. Please fix before proceeding." -ForegroundColor Red
        $duplicateAliases | ForEach-Object { Write-Host "  Alias '$($_.Name)' appears $($_.Count) times" -ForegroundColor Red }
        Stop-Transcript
        exit 1
    }
    
    Write-Host "No duplicate aliases found in source file." -ForegroundColor Green

    # Create SQL connection
    Write-Host "Connecting to SQL Server..."
    $connection = New-Object System.Data.SqlClient.SqlConnection("Server=$sqlServer;Database=$database;Integrated Security=True;")
    $connection.Open()

    # Insert aliases into database
    Write-Host "Importing aliases..."
    # CORRECTED: Using the correct column names 'Alias_Name' and 'Standardized_Name'
    $insertCommand = $connection.CreateCommand()
    $insertCommand.CommandText = "INSERT INTO dbo.HS_Team_Name_Alias (Alias_Name, Standardized_Name, Newspaper_Region) VALUES (@AliasName, @StandardizedName, @Region)"
    $insertCommand.Parameters.Add("@AliasName", [System.Data.SqlDbType]::NVarChar, 255) | Out-Null
    $insertCommand.Parameters.Add("@StandardizedName", [System.Data.SqlDbType]::NVarChar, 255) | Out-Null
    $insertCommand.Parameters.Add("@Region", [System.Data.SqlDbType]::NVarChar, 50) | Out-Null


    $aliasCount = 0
    foreach ($alias in $aliases) {
        # Skip empty rows
        if ([string]::IsNullOrWhiteSpace($alias.Alias_Name) -or [string]::IsNullOrWhiteSpace($alias.Standardized_Name)) {
            Write-Host "  Skipping empty row" -ForegroundColor Yellow
            continue
        }

        # CORRECTED: Referencing the correct CSV headers
        $insertCommand.Parameters["@AliasName"].Value = $alias.Alias_Name.Trim()
        $insertCommand.Parameters["@StandardizedName"].Value = $alias.Standardized_Name.Trim()
        $insertCommand.Parameters["@Region"].Value = '*Global*' # Set default region

        try {
            # Check if alias already exists before inserting
            $checkCmd = $connection.CreateCommand()
            $checkCmd.CommandText = "SELECT COUNT(*) FROM dbo.HS_Team_Name_Alias WHERE Alias_Name = @CheckAlias"
            $checkCmd.Parameters.AddWithValue("@CheckAlias", $alias.Alias_Name.Trim()) | Out-Null
            $exists = $checkCmd.ExecuteScalar()

            if ($exists -eq 0) {
                $insertCommand.ExecuteNonQuery() | Out-Null
                $aliasCount++
            } else {
                Write-Host "  Skipping existing alias: $($alias.Alias_Name)" -ForegroundColor Cyan
            }
        }
        catch {
            Write-Host "  Error inserting alias: $($alias.Alias_Name) -> $($alias.Standardized_Name)" -ForegroundColor Red
            Write-Host "  $($_.Exception.Message)" -ForegroundColor Red
        }
    }

    Write-Host "Imported $aliasCount new aliases successfully" -ForegroundColor Green

    Write-Host "`nAlias import process completed!" -ForegroundColor Green
}
catch {
    Write-Host "FATAL ERROR: $_" -ForegroundColor Red
    Write-Host $_.ScriptStackTrace
}
finally {
    if ($connection -and $connection.State -eq 'Open') {
        $connection.Close()
        Write-Host "Database connection closed."
    }
    Stop-Transcript
}
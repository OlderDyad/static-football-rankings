# --- Configuration ---
$ServerName = "MCKNIGHTS-PC\SQLEXPRESS01"
$DatabaseName = "hs_football_database"

# --- Script ---

if (-not (Get-Module -ListAvailable -Name SqlServer)) {
    Write-Host "The 'SqlServer' PowerShell module is not installed. Installing it now..."
    Install-Module -Name SqlServer -Scope CurrentUser -Repository PSGallery -Force
}
Import-Module -Name SqlServer

$CsvFilePath = "J:\Users\demck\Google Drive\Documents\Football\HSF\Newspapers\Staged\Alias_Correction_Sheet.csv"
$AliasColumnName = "Unrecognized_Alias"

Write-Host "--- Starting Alias Search Script (Searching HS_Team_Names) ---"

if (-not (Test-Path $CsvFilePath)) {
    Write-Error "ERROR: The file was not found at the specified path: $CsvFilePath"
    return
}

try {
    $Aliases = (Import-Csv -Path $CsvFilePath).$AliasColumnName | Where-Object { $_ -ne $null -and $_ -ne "" } | Get-Unique
    Write-Host "Found $($Aliases.Count) unique aliases to search for."
}
catch {
    Write-Error "Error reading or parsing CSV file: $_"
    return
}

# --- Process each alias ---
foreach ($Alias in $Aliases) {
    Write-Host "`n"
    Write-Host ("=" * 50)
    Write-Host "Searching for alias: '$Alias'"
    Write-Host ("=" * 50)

    # *** THIS QUERY HAS BEEN UPDATED TO SEARCH THE HS_Team_Names TABLE ***
    $Query = @"
SELECT
    Team_Name,
    City,
    State
FROM
    dbo.HS_Team_Names
WHERE
    Team_Name LIKE '%$Alias%'
ORDER BY
    State, City, Team_Name;
"@

    try {
        $Results = Invoke-Sqlcmd -ServerInstance $ServerName -Database $DatabaseName -Query $Query

        if ($Results) {
            Write-Host "Found $($Results.Count) potential matches in the master team list:"
            $Results | Format-Table -AutoSize
        }
        else {
            Write-Host "No potential matches found in HS_Team_Names."
        }
    }
    catch {
        Write-Error "An error occurred executing query for '$Alias': $_"
    }
}

Write-Host "`n--- Script Complete. ---"
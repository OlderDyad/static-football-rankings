# Generate-McKnightNationalChampions.ps1
# CLEAN VERSION - Proper field handling

$logFile = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\scripts\imported_SQL_json\logs\mcknight-national-champions.log"
$outputDir = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\docs\data\mcknight-national-champions"

# Setup
New-Item -ItemType Directory -Force -Path (Split-Path $logFile) | Out-Null
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
Remove-Item "$outputDir\mcknight-national-champions.json" -ErrorAction SilentlyContinue

Get-Date | Out-File $logFile
"Starting McKnight National Champions generation" | Tee-Object -FilePath $logFile -Append

# Import common functions
. ".\common-functions.ps1"

function Parse-DecimalSafe {
    param($Value, $Default = 0)
    try {
        if ($null -eq $Value -or [string]::IsNullOrWhiteSpace("$Value")) { return $Default }
        return [decimal]::Parse("$Value")
    }
    catch { return $Default }
}

try {
    $connection = Connect-Database
    Write-Host "Database connected"

    Write-Host "Executing: Get_McKnight_National_Champions"
    $command = New-Object System.Data.SqlClient.SqlCommand("EXEC dbo.Get_McKnight_National_Champions", $connection)
    $adapter = New-Object System.Data.SqlClient.SqlDataAdapter($command)
    $dataset = New-Object System.Data.DataSet
    $adapter.Fill($dataset)

    if ($dataset.Tables.Count -gt 0 -and $dataset.Tables[0].Rows.Count -gt 0) {
        $table = $dataset.Tables[0]
        Write-Host "Retrieved $($table.Rows.Count) champions"

        $champions = @()
        foreach ($row in $table.Rows) {
            
            # Build link HTML
            $linkHtml = if ($row["HasTeamPage"] -eq 1 -and -not [string]::IsNullOrEmpty($row["TeamPageUrl"])) {
                "<a href='$($row["TeamPageUrl"])' class='team-link' title='View Team Page'><i class='fas fa-external-link-alt'></i></a>"
            } else {
                "<span class='no-page-icon' style='color:#ddd;' title='Page coming soon'>&#9633;</span>"
            }
            
            $champion = [PSCustomObject]@{
                year = $row["year"]
                team = $row["team"]
                state = $row["state"]
                record = $row["record"]
                combined = Parse-DecimalSafe $row["combined"]
                margin = Parse-DecimalSafe $row["margin"]
                win_loss = Parse-DecimalSafe $row["win_loss"]
                offense = Parse-DecimalSafe $row["offense"]
                defense = Parse-DecimalSafe $row["defense"]
                games_played = $row["games_played"]
                logoURL = $row["logoURL"]
                schoolLogoURL = $row["schoolLogoURL"]
                backgroundColor = $row["backgroundColor"]
                textColor = $row["textColor"]
                mascot = $row["mascot"]
                teamId = $row["teamId"]
                hasTeamPage = [bool]$row["HasTeamPage"]
                teamPageUrl = $row["TeamPageUrl"]
                teamLinkHtml = $linkHtml
            }
            $champions += $champion
        }

        # Get most recent champion for banner
        $topChampion = $champions | Sort-Object -Property year -Descending | Select-Object -First 1

        $jsonData = @{
            topItem = $topChampion
            items = $champions
            metadata = @{
                timestamp = (Get-Date).ToString("o")
                type = "mcknight-national-champions"
                description = "McKnight's National Champions"
                totalItems = $champions.Count
            }
        }

        $outputPath = Join-Path $outputDir "mcknight-national-champions.json"
        $jsonString = ConvertTo-Json -InputObject $jsonData -Depth 10
        Set-Content -Path $outputPath -Value $jsonString -Encoding UTF8

        Write-Host "✓ Wrote $($champions.Count) champions"
        Write-Host "✓ With team pages: $(($champions | Where-Object { $_.hasTeamPage }).Count)"
        "Complete: $outputPath" | Tee-Object -FilePath $logFile -Append
    }
}
catch {
    Write-Host "Error: $_" -ForegroundColor Red
    "Error: $_" | Tee-Object -FilePath $logFile -Append
}
finally {
    if ($connection -and $connection.State -eq 'Open') {
        $connection.Close()
    }
}

"McKnight generation complete" | Tee-Object -FilePath $logFile -Append
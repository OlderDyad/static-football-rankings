# common-functions.ps1
$connectionString = "Server=MCKNIGHTS-PC\SQLEXPRESS01;Database=hs_football_database;Trusted_Connection=True;TrustServerCertificate=True"

function Connect-Database {
    $connection = New-Object System.Data.SqlClient.SqlConnection($connectionString)
    $connection.Open()
    return $connection
}

function Get-TeamMetadata {
    param (
        $connection,
        $TeamName,
        $isProgram
    )

    Write-Host "Fetching metadata for: $TeamName"

    try {
        $command = New-Object System.Data.SqlClient.SqlCommand("EXEC GetTeamMetadata_test_v1 @TeamName", $connection)
        $command.Parameters.Add((New-SqlParameter -ParameterName "@TeamName" -SqlType NVarChar -Value $TeamName)) | Out-Null

        $adapter = New-Object System.Data.SqlClient.SqlDataAdapter($command)
        $dataset = New-Object System.Data.DataSet
        $adapter.Fill($dataset) | Out-Null

        if ($dataset.Tables.Count -gt 0 -and $dataset.Tables[0].Rows.Count -gt 0) {
            $row = $dataset.Tables[0].Rows[0]
            $metadata = @{
                Mascot = if ($row["Mascot"]) { $row["Mascot"].ToString() } else { "" }
                backgroundColor = if ($row["backgroundColor"]) { $row["backgroundColor"].ToString() } else { "Navy" }
                textColor = if ($row["textColor"]) { $row["textColor"].ToString() } else { "White" }
                LogoURL = if ($row["LogoURL"]) { $row["LogoURL"].ToString() } else { "" }
                School_Logo_URL = if ($row["School_Logo_URL"]) { $row["School_Logo_URL"].ToString() } else { "" }
            }
            Write-Host "Metadata fetched for: $TeamName"
            return $metadata
        } else {
            Write-Host "No metadata found for: $TeamName" -ForegroundColor Yellow
            return $null
        }
    } catch {
        Write-Host "Error fetching metadata for: $TeamName - $_" -ForegroundColor Red
        return $null
    }
}

function Get-TeamMetadata-old {
    param($connection, $TeamName, $isProgram)
    Write-Host "Getting metadata for: $TeamName"
    $command = New-Object System.Data.SqlClient.SqlCommand("EXEC GetTeamMetadata_test_v1 @TeamName", $connection)
    $command.Parameters.AddWithValue("@TeamName", $TeamName)
    
    $adapter = New-Object System.Data.SqlClient.SqlDataAdapter($command)
    $dataset = New-Object System.Data.DataSet
    $adapter.Fill($dataset)
    
    if ($dataset.Tables.Count -gt 0) {
        $lastTable = $dataset.Tables[$dataset.Tables.Count - 1]
        if ($lastTable.Rows.Count -gt 0) {
            $row = $lastTable.Rows[0]
            return @{
                Mascot = if ($row["Mascot"]) { $row["Mascot"].ToString() } else { "" }
                backgroundColor = if ($row["backgroundColor"]) { $row["backgroundColor"].ToString() } else { "Navy" }
                textColor = if ($row["textColor"]) { $row["textColor"].ToString() } else { "White" }
                LogoURL = if ($row["LogoURL"]) { $row["LogoURL"].ToString() } else { "" }
                School_Logo_URL = if ($row["School_Logo_URL"]) { $row["School_Logo_URL"].ToString() } else { "" }
            }
        }
    }
    return $null
    if ($metadata) {
        Write-Host "Found metadata with Mascot: $($metadata.Mascot)" 
    }
    return $metadata
}

# Add to common-functions.ps1
function Format-ProgramData {
    param($programs, $metadata, $description)
    
    $jsonData = @{
        metadata = @{
            timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
            type = "programs"
            yearRange = "all-time"
            totalItems = $programs.Rows.Count
            description = $description
        }
        topItem = @{
            rank = [int]$programs.Rows[0].rank
            program = $programs.Rows[0].program
            seasons = [int]$programs.Rows[0].seasons
            combined = [Math]::Round([double]$programs.Rows[0].combined, 3).ToString("F3")
            margin = [Math]::Round([double]$programs.Rows[0].margin, 3).ToString("F3")
            win_loss = [Math]::Round([double]$programs.Rows[0].win_loss, 3).ToString("F3")
            offense = [Math]::Round([double]$programs.Rows[0].offense, 3).ToString("F3")
            defense = [Math]::Round([double]$programs.Rows[0].defense, 3).ToString("F3")
            state = $programs.Rows[0].state.ToString().PadRight(4).Substring(0,4)
            mascot = if ($metadata) { $metadata.Mascot } else { "" }
            backgroundColor = if ($metadata) { $metadata.backgroundColor } else { "Navy" }
            textColor = if ($metadata) { $metadata.textColor } else { "White" }
            logoURL = if ($metadata) { $metadata.LogoURL } else { "" }
            schoolLogoURL = if ($metadata) { $metadata.School_Logo_URL } else { "" }
        }
        items = @($programs.Rows | ForEach-Object {
            @{
                rank = [int]$_.rank
                program = $_.program
                seasons = [int]$_.seasons
                combined = [Math]::Round([double]$_.combined, 3).ToString("F3")
                margin = [Math]::Round([double]$_.margin, 3).ToString("F3")
                win_loss = [Math]::Round([double]$_.win_loss, 3).ToString("F3")
                offense = [Math]::Round([double]$_.offense, 3).ToString("F3")
                defense = [Math]::Round([double]$_.defense, 3).ToString("F3")
                state = $_.state.ToString().PadRight(4).Substring(0,4)
            }
        })
    }
    
    Write-Host "Generated data for $($programs.Rows[0].program) with $($programs.Rows.Count) items"
    return $jsonData
}

function Format-TeamData {
    param($teams, $metadata, $description, $yearRange)
    
    $jsonData = @{
        metadata = @{
            timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
            type = "teams" 
            yearRange = $yearRange
            totalItems = $teams.Rows.Count
            description = $description
        }
        topItem = @{
            rank = [int]$teams.Rows[0].rank
            team = $teams.Rows[0].team
            season = [int]$teams.Rows[0].season 
            combined = [Math]::Round([double]$teams.Rows[0].combined, 3).ToString("F3")
            margin = [Math]::Round([double]$teams.Rows[0].margin, 3).ToString("F3")
            win_loss = [Math]::Round([double]$teams.Rows[0].win_loss, 3).ToString("F3")
            offense = [Math]::Round([double]$teams.Rows[0].offense, 3).ToString("F3")
            defense = [Math]::Round([double]$teams.Rows[0].defense, 3).ToString("F3")
            state = $teams.Rows[0].state.ToString().PadRight(4).Substring(0,4)
            games_played = [int]$teams.Rows[0].games_played
            mascot = if ($metadata) { $metadata.Mascot } else { "" }
            backgroundColor = if ($metadata) { $metadata.backgroundColor } else { "Navy" }
            textColor = if ($metadata) { $metadata.textColor } else { "White" }
            logoURL = if ($metadata) { $metadata.LogoURL } else { "" }
            schoolLogoURL = if ($metadata) { $metadata.School_Logo_URL } else { "" }
        }
        items = @($teams.Rows | ForEach-Object {
            @{
                rank = [int]$_.rank
                team = $_.team
                season = [int]$_.season
                combined = [Math]::Round([double]$_.combined, 3).ToString("F3")
                margin = [Math]::Round([double]$_.margin, 3).ToString("F3")
                win_loss = [Math]::Round([double]$_.win_loss, 3).ToString("F3")
                offense = [Math]::Round([double]$_.offense, 3).ToString("F3")
                defense = [Math]::Round([double]$_.defense, 3).ToString("F3")
                state = $_.state.ToString().PadRight(4).Substring(0,4)
                games_played = [int]$_.games_played
            }
        })
    }
    
    Write-Host "Generated data for $($teams.Rows[0].team) with $($teams.Rows.Count) items"
    return $jsonData
 }

 function New-SqlParameter {
    param (
        [string]$ParameterName,
        [System.Data.SqlDbType]$SqlType,
        $Value,
        [System.Data.ParameterDirection]$Direction = [System.Data.ParameterDirection]::Input
    )
    
    $param = New-Object System.Data.SqlClient.SqlParameter
    $param.ParameterName = $ParameterName
    $param.SqlDbType = $SqlType
    if ($Value -ne $null) {
        $param.Value = $Value
    }
    $param.Direction = $Direction
    return $param
}

function Format-StateTeamData {
    param(
        $teams, 
        $metadata, 
        $description, 
        $yearRange,
        $stateFormatted  # Added parameter for state
    )
    
    Write-Host "Formatting state team data for $($teams.Rows[0].Team)"
    Write-Host "Row fields: $($teams.Columns.ColumnName -join ', ')"

    $jsonData = @{
        metadata = @{
            timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
            type = "state-teams" 
            yearRange = $yearRange
            totalItems = $teams.Rows.Count
            description = $description
        }
        topItem = @{
            rank = [int]$teams.Rows[0].Rank
            team = $teams.Rows[0].Team
            season = [int]$teams.Rows[0].Season
            combined = [Math]::Round([double]$teams.Rows[0].Combined, 3).ToString("F3")
            margin = [Math]::Round([double]$teams.Rows[0].Margin, 3).ToString("F3")
            win_loss = [Math]::Round([double]$teams.Rows[0].Win_Loss, 3).ToString("F3")
            offense = [Math]::Round([double]$teams.Rows[0].Offense, 3).ToString("F3")
            defense = [Math]::Round([double]$teams.Rows[0].Defense, 3).ToString("F3")
            state = $stateFormatted
            games_played = [int]$teams.Rows[0].Games_Played
            mascot = if ($metadata) { $metadata.Mascot } else { "" }
            backgroundColor = if ($metadata) { $metadata.backgroundColor } else { "Navy" }
            textColor = if ($metadata) { $metadata.textColor } else { "White" }
            logoURL = if ($metadata) { $metadata.LogoURL } else { "" }
            schoolLogoURL = if ($metadata) { $metadata.School_Logo_URL } else { "" }
        }
        items = @($teams.Rows | ForEach-Object {
            @{
                rank = [int]$_.Rank
                team = $_.Team
                season = [int]$_.Season
                combined = [Math]::Round([double]$_.Combined, 3).ToString("F3")
                margin = [Math]::Round([double]$_.Margin, 3).ToString("F3")
                win_loss = [Math]::Round([double]$_.Win_Loss, 3).ToString("F3")
                offense = [Math]::Round([double]$_.Offense, 3).ToString("F3")
                defense = [Math]::Round([double]$_.Defense, 3).ToString("F3")
                state = $stateFormatted
                games_played = [int]$_.Games_Played
            }
        })
    }
    
    return $jsonData
}

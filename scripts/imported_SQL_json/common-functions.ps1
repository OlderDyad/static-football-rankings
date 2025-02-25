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
                # Map from PrimaryColor and SecondaryColor to backgroundColor and textColor
                backgroundColor = if ($row["PrimaryColor"]) { $row["PrimaryColor"].ToString() } else { "Navy" }
                textColor = if ($row["SecondaryColor"]) { $row["SecondaryColor"].ToString() } else { "White" }
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
    
    # Add debug output
    Write-Host "Formatting program data with $($programs.Rows.Count) rows"
    
    try {
        # Safe toString function for null values
        function SafeToString($value, $defaultValue = "0") {
            if ($null -eq $value -or [DBNull]::Value.Equals($value)) {
                return $defaultValue
            }
            return $value.ToString()
        }
        
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
                combined = SafeToString([double]$programs.Rows[0].combined, "0.000")
                margin = SafeToString([double]$programs.Rows[0].margin, "0.000")
                win_loss = SafeToString([double]$programs.Rows[0].win_loss, "0.000")
                offense = SafeToString([double]$programs.Rows[0].offense, "0.000")
                defense = SafeToString([double]$programs.Rows[0].defense, "0.000")
                state = SafeToString($programs.Rows[0].state)
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
                    combined = SafeToString([double]$_.combined, "0.000")
                    margin = SafeToString([double]$_.margin, "0.000")
                    win_loss = SafeToString([double]$_.win_loss, "0.000")
                    offense = SafeToString([double]$_.offense, "0.000")
                    defense = SafeToString([double]$_.defense, "0.000")
                    state = SafeToString($_.state)
                }
            })
        }
        
        Write-Host "Generated data for $($programs.Rows[0].program) with $($programs.Rows.Count) items"
        return $jsonData
    }
    catch {
        Write-Host "Error in Format-ProgramData: $_" -ForegroundColor Red
        Write-Host "Error details: $($_.ScriptStackTrace)" -ForegroundColor Red
        throw
    }
}

function Format-TeamData {
    param($teams, $metadata, $description, $yearRange, $stateFormatted = "")
    
    # Add debug output
    Write-Host "Formatting team data with $($teams.Rows.Count) rows"
    
    try {
        # Improved SafeToString function with explicit array handling
        function SafeToString($value, $defaultValue = "0") {
            if ($null -eq $value -or [DBNull]::Value.Equals($value)) {
                return $defaultValue
            }
            
            # Handle array type explicitly (this is likely the issue)
            if ($value -is [Array]) {
                if ($value.Length -gt 0) {
                    $firstVal = $value[0]
                    if ($firstVal -is [System.Double] -or $firstVal -is [System.Decimal]) {
                        return [double]::Parse($firstVal.ToString()).ToString("0.000")
                    }
                    return $firstVal.ToString()
                }
                return $defaultValue
            }
            
            # Handle numeric types
            if ($value -is [System.Double] -or $value -is [System.Decimal]) {
                return [double]::Parse($value.ToString()).ToString("0.000")
            }
            
            # Default string conversion
            return $value.ToString()
        }
        
        # Determine state to use
        $stateToUse = if ([string]::IsNullOrEmpty($stateFormatted)) { 
            SafeToString($teams.Rows[0].State) 
        } else { 
            $stateFormatted 
        }
        
        $jsonData = @{
            metadata = @{
                timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
                type = "teams" 
                yearRange = $yearRange
                totalItems = $teams.Rows.Count
                description = $description
            }
            topItem = @{
                rank = [int]$teams.Rows[0].Rank
                team = $teams.Rows[0].Team
                season = [int]$teams.Rows[0].Season 
                # Use SafeToString to handle arrays
                combined = SafeToString($teams.Rows[0].Combined, "0.000")
                margin = SafeToString($teams.Rows[0].Margin, "0.000")
                win_loss = SafeToString($teams.Rows[0].Win_Loss, "0.000")
                offense = SafeToString($teams.Rows[0].Offense, "0.000")
                defense = SafeToString($teams.Rows[0].Defense, "0.000")
                state = $stateToUse
                games_played = [int]$teams.Rows[0].Games_Played
                mascot = if ($metadata) { $metadata.Mascot } else { "" }
                backgroundColor = if ($metadata) { $metadata.backgroundColor } else { "Navy" }
                textColor = if ($metadata) { $metadata.textColor } else { "White" }
                logoURL = if ($metadata) { $metadata.LogoURL } else { "" }
                schoolLogoURL = if ($metadata) { $metadata.School_Logo_URL } else { "" }
            }
            items = @($teams.Rows | ForEach-Object {
                $itemState = if ([string]::IsNullOrEmpty($stateFormatted)) { 
                    SafeToString($_.State) 
                } else { 
                    $stateFormatted 
                }
                
                @{
                    rank = [int]$_.Rank
                    team = $_.Team
                    season = [int]$_.Season
                    # Use SafeToString to handle arrays
                    combined = SafeToString($_.Combined, "0.000")
                    margin = SafeToString($_.Margin, "0.000")
                    win_loss = SafeToString($_.Win_Loss, "0.000")
                    offense = SafeToString($_.Offense, "0.000")
                    defense = SafeToString($_.Defense, "0.000")
                    state = $itemState
                    games_played = [int]$_.Games_Played
                }
            })
        }
        
        Write-Host "Generated data for $($teams.Rows[0].Team) with $($teams.Rows.Count) items"
        return $jsonData
    }
    catch {
        Write-Host "Error in Format-TeamData: $_" -ForegroundColor Red
        Write-Host "Error details: $($_.ScriptStackTrace)" -ForegroundColor Red
        throw
    }
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
        $stateFormatted
    )
    
    try {
        # Improved SafeToString function with explicit array handling
        function SafeToString($value, $defaultValue = "0") {
            if ($null -eq $value -or [DBNull]::Value.Equals($value)) {
                return $defaultValue
            }
            
            # Handle array type explicitly
            if ($value -is [Array]) {
                if ($value.Length -gt 0) {
                    $firstVal = $value[0]
                    if ($firstVal -is [System.Double] -or $firstVal -is [System.Decimal]) {
                        return [double]::Parse($firstVal.ToString()).ToString("0.000")
                    }
                    return $firstVal.ToString()
                }
                return $defaultValue
            }
            
            # Handle numeric types
            if ($value -is [System.Double] -or $value -is [System.Decimal]) {
                return [double]::Parse($value.ToString()).ToString("0.000")
            }
            
            # Default string conversion
            return $value.ToString()
        }
        
        Write-Host "Formatting state team data for $($teams.Rows[0].Team)"
        
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
                combined = SafeToString($teams.Rows[0].Combined, "0.000")
                margin = SafeToString($teams.Rows[0].Margin, "0.000")
                win_loss = SafeToString($teams.Rows[0].Win_Loss, "0.000")
                offense = SafeToString($teams.Rows[0].Offense, "0.000")
                defense = SafeToString($teams.Rows[0].Defense, "0.000")
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
                    combined = SafeToString($_.Combined, "0.000")
                    margin = SafeToString($_.Margin, "0.000")
                    win_loss = SafeToString($_.Win_Loss, "0.000")
                    offense = SafeToString($_.Offense, "0.000")
                    defense = SafeToString($_.Defense, "0.000")
                    state = $stateFormatted
                    games_played = [int]$_.Games_Played
                }
            })
        }
        
        return $jsonData
    }
    catch {
        Write-Host "Error in Format-StateTeamData: $_" -ForegroundColor Red
        Write-Host "Error details: $($_.ScriptStackTrace)" -ForegroundColor Red
        throw
    }
}
# Modules/GameDataCleaner/Public/GameDataFunctions.ps1

function Initialize-GameDataLogger {
    [CmdletBinding()]
    param (
        [string]$LogPath = ".\logs\game-data-cleaner.log"
    )
    
    $logDir = Split-Path $LogPath -Parent
    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir | Out-Null
    }
    
    return $LogPath
 }
 
 function Write-GameLog {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory=$true)]
        [string]$Message,
        [ValidateSet('Information', 'Warning', 'Error', 'Debug')]
        [string]$Level = "Information",
        [string]$LogPath
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "$timestamp [$Level] $Message"
    Add-Content -Path $LogPath -Value $logEntry
 }
 
 function Convert-RawGameData {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory=$true)]
        [int]$Season,
        [Parameter(Mandatory=$true)]
        [hashtable]$RawData,
        [string]$LogPath
    )
    
    try {
        # Detailed logging of input data
        Write-GameLog -Message "Starting to clean game data for game: $($RawData.TeamName) vs $($RawData.Opponent)" -LogPath $LogPath
        Write-GameLog -Message "Input data: $(($RawData | ConvertTo-Json))" -Level "Debug" -LogPath $LogPath
 
        # Initialize all fields from SQL schema
        $cleanedData = @{
            GameDate = $null
            Season = $Season
            HomeTeam = $null
            VisitorTeam = $null
            IsNeutral = $false
            Location = $null
            Location2 = $null
            Line = $null
            FutureGame = $false
            Source = "MaxPreps: " + $RawData.URL.Trim()  # Updated to identify source system
            DateAdded = Get-Date
            OT = $null
            Forfeit = $false
            HomeScore = $null
            VisitorScore = $null
            Margin = $null
            Access_ID = $null
        }
 
        # Validate required fields
        $requiredFields = @('TeamName', 'Opponent', 'Date', 'Location', 'URL')
        foreach ($field in $requiredFields) {
            if (-not $RawData.ContainsKey($field)) {
                throw "Missing required field: $field"
            }
            if ([string]::IsNullOrWhiteSpace($RawData[$field])) {
                throw "Required field is empty: $field"
            }
        }
 
        # Check for missing score or WL - these might be forfeits or canceled games
        if ([string]::IsNullOrWhiteSpace($RawData.Score) -or [string]::IsNullOrWhiteSpace($RawData.WL)) {
            Write-GameLog -Message "Missing score or WL data - possible forfeit/canceled game" -Level "Warning" -LogPath $LogPath
            $cleanedData.Forfeit = $true
        }
 
        # Parse date with error handling
        try {
            $dateStr = $RawData.Date.Trim()
            $dateParts = $dateStr.Split('/')
            if ($dateParts.Count -ne 2) {
                throw "Invalid date format. Expected MM/DD, got: $dateStr"
            }
            Write-GameLog -Message "Parsing date: $dateStr" -Level "Debug" -LogPath $LogPath
            $cleanedData.GameDate = Get-Date -Year $Season -Month $dateParts[0] -Day $dateParts[1]
        }
        catch {
            Write-GameLog -Message "Date parsing error: $_" -Level "Error" -LogPath $LogPath
            throw "Failed to parse date '$dateStr': $_"
        }
 
        # Determine teams and location with error handling
        try {
            Write-GameLog -Message "Processing team arrangement" -Level "Debug" -LogPath $LogPath
            $teamResult = Get-TeamArrangement `
                -TeamName $RawData.TeamName.Trim() `
                -Opponent $RawData.Opponent.Trim() `
                -Location $RawData.Location.Trim()
            
            $cleanedData.HomeTeam = $teamResult.HomeTeam
            $cleanedData.VisitorTeam = $teamResult.VisitorTeam
            $cleanedData.IsNeutral = $teamResult.IsNeutral
            $cleanedData.Location = $teamResult.HomeTeam  # Set Location to HomeTeam name
        }
        catch {
            Write-GameLog -Message "Team arrangement error: $_" -Level "Error" -LogPath $LogPath
            throw "Failed to process team arrangement: $_"
        }
 
        # Parse scores only if not marked as forfeit
        if (-not $cleanedData.Forfeit) {
            try {
                Write-GameLog -Message "Processing scores" -Level "Debug" -LogPath $LogPath
                $scoreResult = Get-ParsedScores `
                    -Score $RawData.Score.Trim() `
                    -WinLoss $RawData.WL.Trim() `
                    -IsTeamNameHome ($cleanedData.HomeTeam -eq $RawData.TeamName.Trim())
                
                $cleanedData.HomeScore = $scoreResult.HomeScore
                $cleanedData.VisitorScore = $scoreResult.VisitorScore
                
                # Calculate margin
                if ($null -ne $cleanedData.HomeScore -and $null -ne $cleanedData.VisitorScore) {
                    $cleanedData.Margin = $cleanedData.HomeScore - $cleanedData.VisitorScore
                }
            }
            catch {
                Write-GameLog -Message "Score parsing error: $_" -Level "Error" -LogPath $LogPath
                throw "Failed to parse scores: $_"
            }
        }
 
        Write-GameLog -Message "Successfully cleaned game data" -LogPath $LogPath
        Write-GameLog -Message "Output data: $(($cleanedData | ConvertTo-Json))" -Level "Debug" -LogPath $LogPath
        
        return $cleanedData
    }
    catch {
        Write-GameLog -Message "Error cleaning game data: $_" -Level "Error" -LogPath $LogPath
        throw $_
    }
 }
 
 Export-ModuleMember -Function Initialize-GameDataLogger, Write-GameLog, Convert-RawGameData
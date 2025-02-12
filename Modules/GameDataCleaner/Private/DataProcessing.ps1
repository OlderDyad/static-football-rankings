# Modules/GameDataCleaner/Private/DataProcessing.ps1

function Get-TeamArrangement {
    [CmdletBinding()]
    param (
        [string]$TeamName,
        [string]$Opponent,
        [string]$Location
    )
    
    $isNeutral = [string]::IsNullOrEmpty($Location)
    $isAway = $Location -eq "@"
    
    if ($isAway) {
        return @{
            HomeTeam = $Opponent
            VisitorTeam = $TeamName
            IsNeutral = $isNeutral
        }
    }
    
    return @{
        HomeTeam = $TeamName
        VisitorTeam = $Opponent
        IsNeutral = $isNeutral
    }
}

function Get-ParsedScores {
    [CmdletBinding()]
    param (
        [string]$Score,
        [string]$WinLoss,
        [bool]$IsTeamNameHome
    )
    
    if ([string]::IsNullOrEmpty($Score)) {
        return @{
            HomeScore = $null
            VisitorScore = $null
        }
    }
    
    $scoreParts = $Score.Split('-')
    $score1 = [int]$scoreParts[0]
    $score2 = [int]$scoreParts[1]
    
    if ($score1 -eq $score2) {
        return @{
            HomeScore = $score1
            VisitorScore = $score2
        }
    }
    
    $isWin = $WinLoss.ToUpper() -eq "W"
    
    if ($IsTeamNameHome) {
        if ($isWin) {
            return @{ HomeScore = $score1; VisitorScore = $score2 }
        }
        return @{ HomeScore = $score2; VisitorScore = $score1 }
    }
    else {
        if ($isWin) {
            return @{ HomeScore = $score2; VisitorScore = $score1 }
        }
        return @{ HomeScore = $score1; VisitorScore = $score2 }
    }
}
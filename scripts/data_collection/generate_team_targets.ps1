param(
    [string]$ServerInstance = "localhost\SQLEXPRESS",
    [string]$Database = "hs_football_database",
    [string]$OutputDir = ".\targets"
)

if (!(Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

Write-Host "🎯 Generating data collection targets..."
Write-Host "   Server: $ServerInstance"
Write-Host "   Database: $Database"
Write-Host "   Output: $OutputDir"
Write-Host ""

# --- TARGET TYPE 1: ISLAND PROGRAMS ---
Write-Host "📊 Identifying island programs..."

$IslandProgramsSql = @"
WITH RunChanges AS (
SELECT R1.Home as Team, R1.Season, ABS(R2.Margin - R1.Margin) as Margin_Change
FROM HS_Rankings_Convergence_Master R1
INNER JOIN HS_Rankings_Convergence_Master R2 ON R1.Home = R2.Home AND R1.Season = R2.Season AND R2.Run_Number = R1.Run_Number + 1
),
TeamVolatility AS (
SELECT RC.Team, RC.Season, AVG(RC.Margin_Change) as Avg_Volatility,
COUNT(DISTINCT S.Date) as Games_Played,
COUNT(DISTINCT CASE WHEN S.Home = RC.Team THEN S.Visitor ELSE S.Home END) as Unique_Opponents
FROM RunChanges RC
LEFT JOIN HS_Scores S ON (S.Home = RC.Team OR S.Visitor = RC.Team) AND S.Season = RC.Season
GROUP BY RC.Team, RC.Season
),
ProgramSummary AS (
SELECT Team as Program, COUNT(*) as Volatile_Seasons, AVG(Avg_Volatility) as Program_Avg_Volatility,
AVG(Games_Played) as Avg_Games_Per_Season, AVG(Unique_Opponents) as Avg_Opponents_Per_Season,
MIN(Season) as First_Volatile_Season, MAX(Season) as Last_Volatile_Season,
STRING_AGG(CAST(Season AS VARCHAR), ', ') WITHIN GROUP (ORDER BY Season) as Affected_Seasons,
RIGHT(Team, 4) as State_Code
FROM TeamVolatility
WHERE Avg_Volatility > 10
GROUP BY Team
HAVING COUNT(*) >= 2
)
SELECT Program, State_Code, Volatile_Seasons,
CAST(Program_Avg_Volatility AS DECIMAL(10,2)) as Avg_Volatility,
CAST(Avg_Games_Per_Season AS DECIMAL(10,1)) as Avg_Games,
CAST(Avg_Opponents_Per_Season AS DECIMAL(10,1)) as Avg_Opponents,
First_Volatile_Season, Last_Volatile_Season, Affected_Seasons,
CASE WHEN Volatile_Seasons >= 5 THEN 'CRITICAL' WHEN Volatile_Seasons >= 3 THEN 'HIGH' ELSE 'MEDIUM' END as Priority,
'Island Program' as Issue_Type
FROM ProgramSummary
ORDER BY Volatile_Seasons DESC, Program_Avg_Volatility DESC
"@

try {
    $IslandPrograms = Invoke-Sqlcmd -ServerInstance $ServerInstance -Database $Database -Query $IslandProgramsSql -ErrorAction Stop
    if ($null -ne $IslandPrograms) {
        $IslandPrograms | Export-Csv -Path "$OutputDir\island_programs.csv" -NoTypeInformation
        Write-Host "✅ Island programs: $(@($IslandPrograms).Count) identified"
    }
} catch {
    Write-Host "⚠️ Island programs query failed: $($_.Exception.Message)"
}

# --- TARGET TYPE 2: ELITE LOW-GAME TEAMS ---
Write-Host "📊 Identifying elite teams with too few games..."

$EliteLowGameSql = @"
WITH RankedTeams AS (
SELECT Home as Team, Season,
CAST(Avg_Of_Avg_Of_Home_Modified_Score AS DECIMAL(10,2)) as Margin,
CAST((Avg_Of_Avg_Of_Home_Modified_Score * 0.724 + Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss * 0.766 + Avg_Of_Avg_Of_Home_Modified_Log_Score * 0.791) AS DECIMAL(10,2)) as Combined,
ROW_NUMBER() OVER (PARTITION BY Season ORDER BY (Avg_Of_Avg_Of_Home_Modified_Score * 0.724 + Avg_Of_Avg_Of_Home_Modified_Score_Win_Loss * 0.766 + Avg_Of_Avg_Of_Home_Modified_Log_Score * 0.791) DESC) as Season_Rank
FROM HS_Rankings WHERE Week = 52
),
GameCounts AS (
SELECT RT.Team, RT.Season, RT.Margin, RT.Combined, RT.Season_Rank,
COUNT(DISTINCT S.Date) as Games_Played,
COUNT(DISTINCT CASE WHEN S.Home = RT.Team THEN S.Visitor ELSE S.Home END) as Unique_Opponents,
RIGHT(RT.Team, 4) as State_Code
FROM RankedTeams RT
LEFT JOIN HS_Scores S ON (S.Home = RT.Team OR S.Visitor = RT.Team) AND S.Season = RT.Season
GROUP BY RT.Team, RT.Season, RT.Margin, RT.Combined, RT.Season_Rank
)
SELECT Team, Season, State_Code, Season_Rank, Margin, Combined, Games_Played, Unique_Opponents,
CASE WHEN Season_Rank <= 100 AND Games_Played < 8 THEN 'CRITICAL' WHEN Season_Rank <= 500 AND Games_Played < 6 THEN 'HIGH' ELSE 'MEDIUM' END as Priority,
'Low Games' as Issue_Type
FROM GameCounts WHERE Season_Rank <= 1000 AND Games_Played < 8
ORDER BY Season_Rank, Games_Played
"@

try {
    $EliteLowGame = Invoke-Sqlcmd -ServerInstance $ServerInstance -Database $Database -Query $EliteLowGameSql -ErrorAction Stop
    if ($null -ne $EliteLowGame) {
        $EliteLowGame | Export-Csv -Path "$OutputDir\elite_lowgame.csv" -NoTypeInformation
        Write-Host "✅ Elite low-game teams: $(@($EliteLowGame).Count) identified"
    }
} catch {
    Write-Host "❌ Elite low-game query failed: $($_.Exception.Message)"
}

Write-Host "`n=== PROCESS COMPLETE ==="
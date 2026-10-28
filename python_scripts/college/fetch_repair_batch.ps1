# fetch_repair_batch.ps1 -- opponent-history fetches for the schools that played Northern Colorado and
# Central Arkansas most often (to repair their lost-points rows) -- each site in its own background job,
# so they run in parallel (the 30 s delay is per site). Reads the web only; safe during a rerate.
# Run from python_scripts\college:  .\fetch_repair_batch.ps1      Progress: Get-Job   Logs: schedules\logs\
$sites = @(
  @("https://gomountaineers.com",       "Western Colorado"),
  @("https://goeasternathletics.com",   "Eastern New Mexico"),
  @("https://minesathletics.com",       "Colorado Mines"),
  @("https://goaugie.com",              "Augustana SD"),
  @("https://msumavericks.com",         "Minn St-Mankato"),
  @("https://cctigers.com",             "Colorado College"),
  @("https://gothunderwolves.com",      "Colorado St-Pueblo"),
  @("https://ucmathletics.com",         "Central Missouri"),
  @("https://gochoctaws.com",           "Mississippi College"),
  @("https://hardingsports.com",        "Harding")
)
New-Item -ItemType Directory -Force schedules\logs | Out-Null
$here = Get-Location
foreach ($s in $sites) {
  $log = "schedules\logs\" + ($s[1] -replace '[^A-Za-z0-9]+','_') + ".log"
  Start-Job -Name $s[1] -ScriptBlock {
    param($dir, $site, $team, $log)
    Set-Location $dir
    python fetch_opponent_history.py --site $site --team $team *> $log
  } -ArgumentList $here, $s[0], $s[1], $log | Out-Null
  Write-Host "started: $($s[1])  ->  $log"
}

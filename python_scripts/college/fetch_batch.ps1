# fetch_batch.ps1 -- run opponent-history fetches in parallel, one background job per site.
# Sites and team names come from a CSV (Site,Team), default schedules\fetch_list.csv.
# Reads the web only; safe during a rerate.  Progress: Get-Job    Logs: schedules\logs\
# Usage (from python_scripts\college):  .\fetch_batch.ps1   or   .\fetch_batch.ps1 schedules\other_list.csv
param([string]$list = "schedules\fetch_list.csv")
New-Item -ItemType Directory -Force schedules\logs | Out-Null
Get-Job | Where-Object { $_.State -ne 'Running' } | Remove-Job
$here = Get-Location
foreach ($s in (Import-Csv $list)) {
  $log = "schedules\logs\" + ($s.Team -replace '[^A-Za-z0-9]+','_') + ".log"
  Start-Job -Name $s.Team -ScriptBlock {
    param($dir, $site, $team, $log)
    Set-Location $dir
    python fetch_opponent_history.py --site $site --team $team *> $log
  } -ArgumentList $here, $s.Site, $s.Team, $log | Out-Null
  Write-Host "started: $($s.Team)  ->  $log"
}

# winsipedia_batch.ps1 -- fetch Winsipedia season pages for a list of schools, ONE AT A TIME (same host,
# 10 s between pages). List: schedules\winsipedia_list.csv (Slug,Team,Home,Years). Reads the web only;
# safe during a rerate or the HS run. A wrong slug stops after one page. Pages are cached.
# Run from python_scripts\college:  .\winsipedia_batch.ps1   (log: schedules\logs\winsipedia_batch.log)
param([string]$list = "schedules\winsipedia_list.csv")
New-Item -ItemType Directory -Force schedules\logs | Out-Null
foreach ($s in (Import-Csv $list)) {
  Write-Host "=== $($s.Team)  ($($s.Slug), $($s.Years))"
  python fetch_winsipedia.py --slug $s.Slug --team $s.Team --home $s.Home --years $s.Years 2>&1 |
    Where-Object { $_ -notmatch '^\s+\d{4}: ' } | Tee-Object -Append -FilePath schedules\logs\winsipedia_batch.log
}

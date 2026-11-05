<#
run_hs_rerate_nights.ps1  -- overnight HS re-rates after the 2026-10-29 HS/college detangle fixes.
Each night = about 6 seasons (~1.5 h each, ~9 h). Runs seasons oldest-first within a night and stops
at the first failure. Never start it while a college run (daily full / Sunday weekly) or the
Wednesday HS current-season run is going -- the rating procedures lock each other.

  .\run_hs_rerate_nights.ps1 -List          show every night's seasons
  .\run_hs_rerate_nights.ps1 -Night 1       run night 1
  .\run_hs_rerate_nights.ps1 -Night 1 -WhatIf   print the commands only

Nights 1-5: seasons whose games changed a lot (merges, duplicates, renames). Night 5 is short
            (1952 + college 1899) -- fits on a Wednesday after the HS current-season run.
Nights 6+ : the remaining Saylor phantom seasons (one fake game removed per season; small effect) --
            skip these if a full historical HS run is coming anyway.
#>
param([int]$Night = 0, [switch]$List, [switch]$WhatIf)

$Week = 52
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$log  = Join-Path $here "hs_rerate_nights.log"

# each night = list of runs; each run = @(league, begin, end).  The leading comma keeps a one-run night
# from being flattened by PowerShell.
$nights = New-Object System.Collections.ArrayList
[void]$nights.Add(@( ,@(1,1957,1960) ) + @( ,@(1,2024,2025) ))                  # 1: MUS dups; BC High + MUS 2024-25 (2026 = Wed run)
[void]$nights.Add(@( ,@(1,1961,1966) ))                                          # 2: MUS dups (1964 rename only)
[void]$nights.Add(@( ,@(1,1899,1899) ) + @( ,@(1,1906,1906) ) + @( ,@(1,1934,1934) ) + @( ,@(1,1939,1939) ) + @( ,@(1,1967,1968) ))  # 3: SLU; MUS
[void]$nights.Add(@( ,@(1,1940,1941) ) + @( ,@(1,1945,1945) ) + @( ,@(1,1947,1949) ))  # 4: SLU (1949 also BC)
[void]$nights.Add(@( ,@(1,1952,1952) ) + @( ,@(2,1899,1899) ))                   # 5: BC; then COLLEGE 1899
$done = @(1899,1906,1934,1939,1940,1941,1945,1947,1948,1949,1952) + (1957..1968)
$rest = @((1886..2004) | Where-Object { $done -notcontains $_ })
for ($i = 0; $i -lt $rest.Count; $i += 6) {
  $chunk = @($rest[$i..([Math]::Min($i + 5, $rest.Count - 1))])
  $runs = @(); $b = $chunk[0]; $p = $chunk[0]
  for ($j = 1; $j -lt $chunk.Count; $j++) {
    $s = $chunk[$j]
    if ($s -eq $p + 1) { $p = $s } else { $runs += ,@(1,$b,$p); $b = $s; $p = $s }
  }
  $runs += ,@(1,$b,$p)
  [void]$nights.Add($runs)
}

function Show($k) {
  $night = $nights[$k - 1]
  $txt = ($night | ForEach-Object { $l = if ($_[0] -eq 2) {"COLLEGE "} else {""}; if ($_[1] -eq $_[2]) {"$l$($_[1])"} else {"$l$($_[1])-$($_[2])"} }) -join ", "
  $cnt = ($night | ForEach-Object { $_[2] - $_[1] + 1 } | Measure-Object -Sum).Sum
  "Night {0,2}: {1}  ({2} seasons, ~{3} h)" -f $k, $txt, $cnt, ($cnt * 1.5)
}

if ($List -or $Night -eq 0) { for ($k = 1; $k -le $nights.Count; $k++) { Show $k }; return }
if ($Night -lt 1 -or $Night -gt $nights.Count) { Write-Host "No night $Night (1-$($nights.Count))."; exit 1 }

Set-Location $here
Write-Host (Show $Night)
foreach ($r in $nights[$Night - 1]) {
  $league, $b, $e = $r
  $cmd = "python run_full_rankings_recalc.py --league $league --begin $b --end $e --week $Week --yes --no-snapshot"
  if ($WhatIf) { Write-Host "  $cmd"; continue }
  $t0 = Get-Date
  Add-Content $log "$($t0.ToString('yyyy-MM-dd HH:mm')) night $Night START  $cmd"
  & python run_full_rankings_recalc.py --league $league --begin $b --end $e --week $Week --yes --no-snapshot
  $rc = $LASTEXITCODE
  $mins = [int]((Get-Date) - $t0).TotalMinutes
  Add-Content $log "$((Get-Date).ToString('yyyy-MM-dd HH:mm')) night $Night END rc=$rc ($mins min)  league $league $b-$e"
  if ($rc -ne 0) { Write-Host "FAILED (rc=$rc) on league $league $b-$e -- stopping. See $log"; exit $rc }
}
Write-Host "Night $Night finished. Log: $log"

# top100_watcher.ps1  (added 2026-11-14)
#
# Runs top100_tracker.py on Saturday and Sunday mornings during the season
# (same no-Task-Scheduler approach as maxpreps_watcher.ps1: leave this window
# open/minimized; it loops forever).
#
#   Saturday 06:30  - after the nightly scraper's 5 AM cap (Friday's games)
#   Sunday   05:30  - before weekly_pipeline.py starts the week's batch at 06:00
#                     (the pipeline waits while the tracker holds the scraper
#                     lock, so the two never scrape at the same time)
#
# Start it:
#   cd C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\data_import
#   powershell -ExecutionPolicy Bypass -File .\top100_watcher.ps1
# Season window: runs only from August 15 through January 15.

$ScriptDir = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\data_import"
$WatcherLog = Join-Path $ScriptDir "top100_watcher_log.txt"
$Runs = @{ "Saturday" = @(6, 30); "Sunday" = @(5, 30) }

function Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - $msg"
    Add-Content -Path $WatcherLog -Value $line
    Write-Host $line
}

function InSeason($d) {
    $md = $d.Month * 100 + $d.Day
    return ($md -ge 815) -or ($md -le 115)
}

function NextRun {
    $now = Get-Date
    for ($i = 0; $i -le 7; $i++) {
        $day = $now.Date.AddDays($i)
        $hm = $Runs[$day.DayOfWeek.ToString()]
        if ($hm) {
            $t = $day.AddHours($hm[0]).AddMinutes($hm[1])
            if ($t -gt $now) { return $t }
        }
    }
}

Log "=== Top 100 watcher started (PID $PID): Saturday 06:30 and Sunday 05:30 ==="
while ($true) {
    $target = NextRun
    $wait = [int]($target - (Get-Date)).TotalSeconds
    Log "Next run $($target.ToString('ddd yyyy-MM-dd HH:mm')) (in $([math]::Round($wait/3600,1)) h)."
    while ($wait -gt 0) {
        $chunk = [math]::Min($wait, 3600)
        Start-Sleep -Seconds $chunk
        $wait -= $chunk
    }
    if (-not (InSeason (Get-Date))) {
        Log "Off-season (runs Aug 15 - Jan 15); skipping."
        continue
    }
    Log "Launching top100_tracker.py"
    try {
        Push-Location $ScriptDir
        & python top100_tracker.py 2>&1 | ForEach-Object { Add-Content -Path $WatcherLog -Value "    $_" }
        Log "top100_tracker.py exited with code $LASTEXITCODE"
    } catch {
        Log "top100_tracker.py threw an error: $_"
    } finally {
        Pop-Location
    }
}

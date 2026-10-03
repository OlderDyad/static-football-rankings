# maxpreps_watcher.ps1
#
# Path B (2026-09-17): Task Scheduler's "Run whether user is logged on or
# not" mode needs a real account password, and this account is passwordless
# (Windows Hello PIN only, no working password for that credential prompt) --
# so that path is closed. "Run only when user is logged on" (the original
# setup) was tested extensively and consistently failed too (5 separate
# fixes, all ruled out -- chromedriver cache, headless, GPU, elevation,
# Defender) with chromedriver's own verbose log showing Chrome launches with
# a fully valid command and exits with zero further information, pointing at
# something structural about Task Scheduler's logon session specifically.
#
# This script sidesteps Task Scheduler entirely. It runs as an ordinary
# process inside whatever interactive session you start it from -- the exact
# same kind of session every single manual test has succeeded in, every
# time, no exceptions. It loops forever: sleep until the next 9PM, run the
# scraper via the existing run_maxpreps_scraper.ps1 wrapper (unchanged --
# same 8-hour runtime cap, same orphaned-process cleanup), then compute the
# next night's 9PM and sleep again.
#
# HOW TO USE:
#   1. Test it manually first: just run this script directly in a normal
#      PowerShell window and leave the window open/minimized. Screen sleep
#      does NOT stop it (only the screen goes dark -- this process keeps
#      running in the background exactly like your successful manual tests
#      have). Logging out or restarting the PC WILL stop it.
#   2. Once you trust it, put a shortcut to this script in your Startup
#      folder (Win+R, type shell:startup, Enter) so it relaunches
#      automatically every time you log in -- survives reboots without you
#      needing to remember to start it by hand. Shortcut target:
#        powershell.exe -ExecutionPolicy Bypass -WindowStyle Minimized -File "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\data_import\maxpreps_watcher.ps1"

$ScriptDir = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\data_import"
$WrapperScript = Join-Path $ScriptDir "run_maxpreps_scraper.ps1"
$WatcherLog = Join-Path $ScriptDir "maxpreps_watcher_log.txt"
$TargetHour = 21   # 9 PM, matches run_maxpreps_scraper.ps1's 8-hour cap (9PM -> 5AM)

function Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - $msg"
    Add-Content -Path $WatcherLog -Value $line
    Write-Host $line
}

Log "=== Watcher started (PID $PID) -- will run the scraper nightly at ${TargetHour}:00, no Task Scheduler involved ==="

while ($true) {
    $now = Get-Date
    $target = Get-Date -Hour $TargetHour -Minute 0 -Second 0
    if ($now -ge $target) {
        $target = $target.AddDays(1)
    }
    $waitSeconds = [int]($target - $now).TotalSeconds

    Log "Next run scheduled for $($target.ToString('yyyy-MM-dd HH:mm:ss')) (waiting $([math]::Round($waitSeconds/3600,1)) hours)."

    # Sleep in <=1-hour chunks instead of one long Start-Sleep, so the log
    # shows periodic heartbeats confirming the watcher is still alive
    # (useful for glancing at the log without needing to check Task
    # Manager), and so Ctrl+C / window close is responsive rather than
    # blocked inside a single multi-hour sleep call.
    while ($waitSeconds -gt 0) {
        $chunk = [math]::Min($waitSeconds, 3600)
        Start-Sleep -Seconds $chunk
        $waitSeconds -= $chunk
        if ($waitSeconds -gt 0) {
            Log "Still waiting -- $([math]::Round($waitSeconds/3600,1)) hour(s) until next run."
        }
    }

    Log "Target time reached -- launching run_maxpreps_scraper.ps1"
    try {
        & $WrapperScript
    } catch {
        Log "run_maxpreps_scraper.ps1 threw an error: $_"
    }
    Log "Scraper wrapper finished. Looping back to compute tomorrow's run time."
}

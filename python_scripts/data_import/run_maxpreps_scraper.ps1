# run_maxpreps_scraper.ps1
#
# Wrapper for Task Scheduler. Handles: correct working directory, venv
# activation, a hard runtime cap (stops the scrape before 5AM even if a
# single run is still going), and a wrapper-level log so you can tell
# "task never fired" apart from "task fired, script had a problem" --
# separate from maxpreps_scraper_db.py's own log file
# (maxpreps_scraper_log.txt in the same folder).
#
# EDIT if this path ever changes:
$ScriptDir = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\data_import"
$VenvActivate = $null   # confirmed 2026-09-13: no venv, script is run with system python directly

$WrapperLog = Join-Path $ScriptDir "maxpreps_wrapper_log.txt"
$MaxRuntimeMinutes = 480   # 2026-09-14: widened from 7 to 8 hours (9PM -> 5AM) to
                           # raise nightly throughput from ~1400 to ~1600 teams,
                           # based on the observed ~18 sec/team pace from batch 33's
                           # full 2000-team manual run. Task Scheduler trigger must
                           # also be moved from 10:00PM to 9:00PM for this to take effect.

function Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - $msg"
    Add-Content -Path $WrapperLog -Value $line
    Write-Host $line
}

Log "=== Wrapper started ==="
Set-Location $ScriptDir

if ($VenvActivate -and (Test-Path $VenvActivate)) {
    Log "Activating venv: $VenvActivate"
    & $VenvActivate
} else {
    Log "No venv activation configured/found; using system Python on PATH."
}

# Launch the scraper as a child process so we can enforce the runtime cap
# without killing the wrapper itself.
$proc = Start-Process -FilePath "python" -ArgumentList "maxpreps_scraper_db.py" `
    -WorkingDirectory $ScriptDir -PassThru -NoNewWindow

Log "Launched maxpreps_scraper_db.py (PID $($proc.Id)). Runtime cap: $MaxRuntimeMinutes minutes."

$finished = $proc.WaitForExit($MaxRuntimeMinutes * 60 * 1000)

if (-not $finished) {
    Log "Runtime cap hit ($MaxRuntimeMinutes min) -- stopping the scraper before it runs into the day."
    # Per-team commits mean the in-progress team is the only work lost;
    # everything already scraped this run is saved. Kill the whole process
    # tree in case Selenium spawned a chromedriver/chrome child.
    try {
        Stop-Process -Id $proc.Id -Force -ErrorAction Stop
        Log "Sent Force stop to PID $($proc.Id)."
    } catch {
        Log "Stop-Process failed (process may have already exited): $_"
    }
    # Clean up any orphaned chromedriver/chrome processes this run spawned.
    Get-Process chromedriver -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Get-Process chrome -ErrorAction SilentlyContinue | Where-Object { $_.StartTime -gt (Get-Date).AddMinutes(-$MaxRuntimeMinutes) } | Stop-Process -Force -ErrorAction SilentlyContinue
    Log "Orphaned chromedriver/recent chrome processes cleaned up."
} else {
    Log "maxpreps_scraper_db.py exited on its own with code $($proc.ExitCode)."
}

Log "=== Wrapper finished ==="

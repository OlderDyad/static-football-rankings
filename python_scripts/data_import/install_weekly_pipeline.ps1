# install_weekly_pipeline.ps1
#
# One-time switch from the nightly 9PM watcher (maxpreps_watcher.ps1) to the
# weekly pipeline (weekly_pipeline.py). Safe to re-run.
#   1. Stops any running maxpreps_watcher.ps1 process (it would otherwise
#      start a new batch every night once the weekly batch finishes).
#      Does NOT touch a scraper run (python) that's currently going.
#   2. Removes the old "MaxPreps Watcher" Startup shortcut.
#   3. Adds a "MaxPreps Weekly Pipeline" Startup shortcut that runs
#      weekly_pipeline.py --loop on every login.
# It does not start the pipeline -- see the message at the end.

$ScriptDir = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\data_import"
$Startup = [Environment]::GetFolderPath('Startup')

# 1. Stop the old watcher
$watchers = Get-CimInstance Win32_Process -Filter "Name='powershell.exe' OR Name='pwsh.exe'" |
    Where-Object { $_.CommandLine -like '*maxpreps_watcher.ps1*' }
if ($watchers) {
    foreach ($w in $watchers) {
        Stop-Process -Id $w.ProcessId -Force
        Write-Host "Stopped old watcher (PID $($w.ProcessId))."
    }
} else {
    Write-Host "No running maxpreps_watcher.ps1 found."
}

# 2. Remove the old shortcut
$old = Join-Path $Startup "MaxPreps Watcher.lnk"
if (Test-Path $old) {
    Remove-Item $old
    Write-Host "Removed old Startup shortcut: $old"
}

# 3. New shortcut
$new = Join-Path $Startup "MaxPreps Weekly Pipeline.lnk"
$shell = New-Object -ComObject WScript.Shell
$sc = $shell.CreateShortcut($new)
$sc.TargetPath = "powershell.exe"
$sc.Arguments = "-ExecutionPolicy Bypass -WindowStyle Hidden -Command `"Set-Location '$ScriptDir'; python weekly_pipeline.py --loop`""
$sc.WorkingDirectory = $ScriptDir
$sc.Description = "Weekly MaxPreps scrape -> ratings -> publish pipeline"
$sc.Save()
Write-Host "Created Startup shortcut: $new"

Write-Host ""
Write-Host "Done. The pipeline starts automatically at your next login."
Write-Host "To start it now instead (run once immediately, then weekly):"
Write-Host "  Start-Process powershell.exe -WindowStyle Hidden -WorkingDirectory `"$ScriptDir`" -ArgumentList '-ExecutionPolicy Bypass -Command `"python weekly_pipeline.py --now --loop`"'"
Write-Host "Check progress any time in weekly_pipeline_status.txt (same folder)."

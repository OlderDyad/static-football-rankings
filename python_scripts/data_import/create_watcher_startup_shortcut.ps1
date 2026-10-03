# One-time setup: creates a shortcut in the current user's Startup folder
# so maxpreps_watcher.ps1 relaunches automatically on every login, without
# needing to be started by hand after a reboot/logout.

$WatcherScript = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\data_import\maxpreps_watcher.ps1"
$StartupFolder = [Environment]::GetFolderPath('Startup')
$ShortcutPath = Join-Path $StartupFolder "MaxPreps Watcher.lnk"

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$WatcherScript`""
$Shortcut.WorkingDirectory = Split-Path $WatcherScript
$Shortcut.Description = "Launches the MaxPreps overnight scraper watcher on login"
$Shortcut.Save()

Write-Host "Created: $ShortcutPath"
Write-Host "The watcher will now start automatically on your next login."
Write-Host "It will NOT start immediately from running this script -- start it manually this one time if you want it running right now:"
Write-Host "  Start-Process powershell.exe -ArgumentList '-ExecutionPolicy Bypass -File `"$WatcherScript`"' -WindowStyle Hidden"

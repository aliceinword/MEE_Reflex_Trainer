# Creates a desktop shortcut for MEE Reflex Trainer with the custom app icon.
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$launcher = Join-Path $projectRoot "run_app.bat"
$icon = Join-Path $projectRoot "assets\app_icon.ico"
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "MEE Reflex Trainer.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $launcher
$shortcut.WorkingDirectory = $projectRoot
$shortcut.IconLocation = "$icon,0"
$shortcut.Description = "Start MEE Reflex Trainer"
$shortcut.Save()

Write-Host "Shortcut created: $shortcutPath"

# One-time helper: creates a desktop shortcut for AstrAI BI with the custom icon.
$WshShell = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktop 'AstrAI BI.lnk'

$shortcut = $WshShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = 'C:\Projet PFE\Launch-AstrAI.bat'
$shortcut.WorkingDirectory = 'C:\Projet PFE'
$shortcut.IconLocation = 'C:\Projet PFE\icon.ico,0'
$shortcut.Description = 'AstrAI BI - Claims Intelligence Platform'
$shortcut.WindowStyle = 7   # minimized terminal
$shortcut.Save()

Write-Host "Shortcut created at: $shortcutPath" -ForegroundColor Green

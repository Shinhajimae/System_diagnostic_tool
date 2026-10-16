@echo off
setlocal
set "DIAGNOSTIC_SETUP=%~dp0scripts\setup_background.ps1"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value; $setupArguments='-NoProfile -ExecutionPolicy Bypass -File '+[char]34+$env:DIAGNOSTIC_SETUP+[char]34+' -StartupUserSid '+$sid; try { $p=Start-Process powershell.exe -Verb RunAs -ArgumentList $setupArguments -Wait -PassThru; exit $p.ExitCode } catch { Write-Host $_.Exception.Message; exit 1 }"
if errorlevel 1 (
 echo Background setup was cancelled or failed.
 pause
 exit /b 1
)
echo Open Diagnostic.exe or Sensors.exe directly from this folder.
echo Choose Start with Windows yourself in the Sensors tray menu.
pause

@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\build_project.ps1"
if errorlevel 1 exit /b 1
pause

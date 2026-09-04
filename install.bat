@echo off
setlocal
cd /d "%~dp0"
echo Installing SYSU Course Grabber...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install.ps1"
if errorlevel 1 (
  echo.
  echo Install failed. See the message above.
  pause
  exit /b 1
)
echo Done.
pause


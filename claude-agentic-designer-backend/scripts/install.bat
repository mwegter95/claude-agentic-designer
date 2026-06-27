@echo off
REM Double-clickable wrapper for install.ps1.
REM Bypasses the PowerShell execution policy and keeps the window open so you
REM can read any output or errors.
setlocal
echo == Claude Agentic Designer - backend install ==
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
echo.
echo ------------------------------------------------------------
echo Install finished. Press any key to close this window.
pause >nul
endlocal

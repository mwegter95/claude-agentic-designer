@echo off
REM Double-clickable wrapper for run_server.ps1.
REM Bypasses the PowerShell execution policy and keeps the window open so you
REM can read any output or errors (the window stays up while the server runs).
setlocal
echo == Claude Agentic Designer - backend server ==
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_server.ps1"
echo.
echo ------------------------------------------------------------
echo Server stopped. Press any key to close this window.
pause >nul
endlocal

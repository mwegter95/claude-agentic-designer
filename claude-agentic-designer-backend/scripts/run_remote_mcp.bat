@echo off
REM Double-clickable wrapper: expose the MCP server via localtunnel for the
REM Claude-for-PowerPoint add-in. Bypasses the PowerShell execution policy and
REM keeps the window open.
setlocal
echo == Claude Agentic Designer - remote MCP (localtunnel) ==
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_remote_mcp.ps1"
echo.
echo ------------------------------------------------------------
echo Tunnel stopped. Press any key to close this window.
pause >nul
endlocal

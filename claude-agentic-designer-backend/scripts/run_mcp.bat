@echo off
REM Double-clickable wrapper for run_mcp.ps1 (manual MCP server inspection).
REM Bypasses the PowerShell execution policy and keeps the window open.
setlocal
echo == Claude Agentic Designer - MCP server (manual run) ==
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_mcp.ps1"
echo.
echo ------------------------------------------------------------
echo MCP server stopped. Press any key to close this window.
pause >nul
endlocal

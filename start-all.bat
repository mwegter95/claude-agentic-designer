@echo off
setlocal enableextensions
REM ============================================================
REM  Claude Agentic Designer - start everything (Windows)
REM  Launches the backend FastAPI server and the frontend Vite
REM  dev server, each in its own window.
REM ============================================================

set "ROOT=%~dp0"
set "BACKEND=%ROOT%claude-agentic-designer-backend"

echo == Claude Agentic Designer - starting everything ==

REM --- Sanity checks -----------------------------------------
where py >nul 2>nul
if errorlevel 1 (
  echo ERROR: The Python launcher 'py' was not found on PATH.
  echo Install Python 3 from https://www.python.org ^(check "Add python.exe to PATH"^)
  echo or run:  winget install Python.Python.3.12
  pause
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo ERROR: 'npm' was not found on PATH. Install Node.js from https://nodejs.org
  pause
  exit /b 1
)

REM --- Frontend dependencies ---------------------------------
if not exist "%ROOT%node_modules" (
  echo Installing frontend dependencies ^(npm install^)...
  call npm install --prefix "%ROOT%"
  if errorlevel 1 (
    echo ERROR: npm install failed.
    pause
    exit /b 1
  )
)

REM --- Launch backend in its own window ----------------------
REM run_server.ps1 self-bootstraps the venv with 'py -3' and installs requirements.
echo Starting backend server window...
start "Claude Agentic Designer - Backend" powershell -NoExit -ExecutionPolicy Bypass -File "%BACKEND%\scripts\run_server.ps1"

REM --- Launch frontend in its own window ---------------------
echo Starting frontend dev server window...
start "Claude Agentic Designer - Frontend" cmd /k "cd /d "%ROOT%" && npm run dev"

echo.
echo ------------------------------------------------------------
echo  Backend:  http://127.0.0.1:8787   (SSE: /api/events/stream)
echo  Frontend: http://127.0.0.1:5273
echo ------------------------------------------------------------
echo Two windows opened. Close them to stop the servers.
echo.
endlocal

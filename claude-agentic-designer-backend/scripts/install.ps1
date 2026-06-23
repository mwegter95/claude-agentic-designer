# One-time setup for the backend on a fresh Windows machine (PowerShell).
# If scripts are blocked, run once:
#   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

Write-Host "== Claude Agentic Designer - backend install =="

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command py -ErrorAction SilentlyContinue }
if (-not $python) {
  Write-Error "Python 3 is required. Install from https://www.python.org (check 'Add python.exe to PATH') or 'winget install Python.Python.3.12'."
  exit 1
}

& $python.Source -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt

$soffice = "C:\Program Files\LibreOffice\program\soffice.exe"
if (-not (Test-Path $soffice) -and -not (Get-Command soffice -ErrorAction SilentlyContinue)) {
  Write-Host ""
  Write-Host "WARNING: LibreOffice (soffice) not found - slide rendering will be skipped." -ForegroundColor Yellow
  Write-Host "Install it with:  winget install TheDocumentFoundation.LibreOffice"
}

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  Write-Host "Created .env from .env.example - edit it to configure Microsoft 365 if needed."
}

Write-Host "Done. Start the server with:  .\scripts\run_server.ps1"

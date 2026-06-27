# Diagnose the Claude Agentic Designer extension on Windows.
#   Usage:  .\scripts\diagnose.ps1            (diagnose this repo's backend)
#           .\scripts\diagnose.ps1 -ExtDir "C:\path\to\installed\extension"
#
# Reproduces the extension's startup OUTSIDE Claude Desktop so you can see the
# real Python error behind "Could not attach to MCP server".
param(
  [string]$ExtDir = ""
)
$ErrorActionPreference = "Continue"

function Section($t) { Write-Host "`n==== $t ====" -ForegroundColor Cyan }

# Resolve the backend/extension folder (the one containing launcher.py).
if (-not $ExtDir) {
  $ExtDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}
Write-Host "Extension dir: $ExtDir"

Section "Python launcher"
& py -3 --version
if ($LASTEXITCODE -ne 0) {
  Write-Host "ERROR: 'py -3' did not run. The manifest launches 'py -3'." -ForegroundColor Red
  Write-Host "Install Python 3 from https://www.python.org and re-test." -ForegroundColor Red
}
& py -3 -c "import sys; print('exe:', sys.executable)"

Section "Dependency import check (with bundled ./lib)"
$probe = @"
import sys, os
here = r'$ExtDir'
lib = os.path.join(here, 'lib')
if os.path.isdir(lib): sys.path.insert(0, lib)
sys.path.insert(0, here)
mods = ['mcp', 'fastapi', 'uvicorn', 'pptx', 'pydantic', 'pydantic_core', 'sse_starlette']
for m in mods:
    try:
        __import__(m); print(f'  OK   {m}')
    except Exception as e:
        print(f'  FAIL {m}: {e}')
print('lib present:', os.path.isdir(lib))
print('webui present:', os.path.isfile(os.path.join(here, 'webui', 'index.html')))
"@
& py -3 -c $probe

Section "Self-test startup (starts companion server, probes ports, exits)"
$env:CLAUDE_DESIGNER_SELFTEST = "1"
$env:CLAUDE_DESIGNER_OPEN_BROWSER = "0"
& py -3 (Join-Path $ExtDir "launcher.py")
Remove-Item Env:\CLAUDE_DESIGNER_SELFTEST -ErrorAction SilentlyContinue

Section "launcher.log"
$log = Join-Path $ExtDir "workspace\logs\launcher.log"
if (Test-Path $log) { Get-Content $log -Tail 40 } else { Write-Host "(no launcher.log yet at $log)" }

Section "companion-server.log"
$slog = Join-Path $ExtDir "workspace\logs\companion-server.log"
if (Test-Path $slog) { Get-Content $slog -Tail 30 } else { Write-Host "(no companion-server.log yet)" }

Section "Claude Desktop MCP logs"
$claudeLogs = Join-Path $env:APPDATA "Claude\logs"
if (Test-Path $claudeLogs) {
  Get-ChildItem $claudeLogs -Filter "*.log" | Sort-Object LastWriteTime -Desc |
    Select-Object -First 5 Name, LastWriteTime, Length | Format-Table -AutoSize
  Write-Host "Tip: open the newest mcp*.log above for Claude's view of the spawn."
} else {
  Write-Host "(no Claude logs dir at $claudeLogs)"
}

Write-Host "`nDone. Paste the FAIL lines and any traceback above to get unblocked." -ForegroundColor Green

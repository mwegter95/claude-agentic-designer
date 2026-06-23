# Start the Claude Agentic Designer event/orchestration server (Windows / PowerShell).
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

# Load .env (simple KEY=VALUE lines) into the process environment.
if (Test-Path ".env") {
  Get-Content ".env" | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
      $idx = $line.IndexOf("=")
      $key = $line.Substring(0, $idx).Trim()
      $val = $line.Substring($idx + 1).Trim()
      if ($key) { [Environment]::SetEnvironmentVariable($key, $val) }
    }
  }
}

$envHost = if ($env:CLAUDE_DESIGNER_HOST) { $env:CLAUDE_DESIGNER_HOST } else { "127.0.0.1" }
$port = if ($env:CLAUDE_DESIGNER_PORT) { $env:CLAUDE_DESIGNER_PORT } else { "8787" }

if (-not (Test-Path ".venv")) {
  Write-Host "Creating virtual environment..."
  python -m venv .venv
}
& .\.venv\Scripts\python.exe -m pip install -q --disable-pip-version-check -r requirements.txt

Write-Host "Server on http://${envHost}:${port}  (SSE: /api/events/stream)"
& .\.venv\Scripts\python.exe -m uvicorn server.app:app --host $envHost --port $port

# Expose the MCP server to the internet for the Claude-for-PowerPoint add-in.
# Starts the MCP server over HTTP (SSE) and a localtunnel with a constant subdomain.
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $PSScriptRoot
Set-Location $here

# Load .env (simple KEY=VALUE lines) into the process environment.
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $idx = $line.IndexOf("=")
            $key = $line.Substring(0, $idx).Trim()
            $val = $line.Substring($idx + 1).Trim()
            # Strip trailing inline comments and surrounding quotes.
            $val = ($val -replace '\s+#.*$', '').Trim('"').Trim("'")
            if ($key) { [Environment]::SetEnvironmentVariable($key, $val) }
        }
    }
}

$transport = if ($env:CLAUDE_DESIGNER_MCP_TRANSPORT -and $env:CLAUDE_DESIGNER_MCP_TRANSPORT -ne "stdio") { $env:CLAUDE_DESIGNER_MCP_TRANSPORT } else { "sse" }
$port = if ($env:CLAUDE_DESIGNER_MCP_PORT) { $env:CLAUDE_DESIGNER_MCP_PORT } else { "3333" }
$subdomain = if ($env:LT_SUBDOMAIN) { $env:LT_SUBDOMAIN } else { "claude-agentic-designer" }
$env:CLAUDE_DESIGNER_MCP_TRANSPORT = $transport

if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..."
    if (Get-Command py -ErrorAction SilentlyContinue) { py -3 -m venv .venv } else { python -m venv .venv }
}
& .\.venv\Scripts\python.exe -m pip install -q --disable-pip-version-check -r requirements.txt

$route = if ($transport -eq "streamable-http") { "/mcp" } else { "/sse" }

Write-Host "== Claude Agentic Designer - remote MCP =="
Write-Host "Transport: $transport   Port: $port   Subdomain: $subdomain"
Write-Host ""
Write-Host "Public URL (give this to Claude's Custom Connector):"
Write-Host "  https://$subdomain.loca.lt$route"
Write-Host ""

# Start the MCP HTTP server in its own window.
Start-Process powershell -ArgumentList @(
    "-NoExit", "-ExecutionPolicy", "Bypass", "-Command",
    "Set-Location '$here'; `$env:CLAUDE_DESIGNER_MCP_TRANSPORT='$transport'; .\.venv\Scripts\python.exe mcp_server.py"
)

# Give the server a moment to bind, then start localtunnel (npx avoids a global install).
Start-Sleep -Seconds 3
npx --yes localtunnel --port $port --subdomain $subdomain

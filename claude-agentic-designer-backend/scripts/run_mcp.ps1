# Run the MCP server for manual inspection (Claude Desktop launches it itself).
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $PSScriptRoot
Set-Location $here

$venvPy = Join-Path $here ".venv\Scripts\python.exe"
if (Test-Path $venvPy) {
    $py = $venvPy
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $py = "py"
} else {
    $py = "python"
}

# Use the MCP Inspector if available; otherwise run plain stdio.
if (Get-Command mcp -ErrorAction SilentlyContinue) {
    & mcp dev mcp_server.py
} else {
    & $py mcp_server.py
}

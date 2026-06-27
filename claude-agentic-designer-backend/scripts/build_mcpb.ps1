# Build the Claude Desktop extension bundle (.mcpb) on Windows.
# Source-only bundle: launcher.py creates the venv and installs requirements on
# first run, so no platform binaries need to be vendored here.
$ErrorActionPreference = "Stop"

$Backend = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Out = Join-Path (Resolve-Path (Join-Path $Backend "..")).Path "claude-agentic-designer.mcpb"

if (-not (Test-Path (Join-Path $Backend "manifest.json"))) {
  Write-Error "manifest.json not found in $Backend"
}

# Stage a clean copy (Compress-Archive has no exclude support).
$Stage = Join-Path ([System.IO.Path]::GetTempPath()) ("cad-mcpb-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $Stage | Out-Null

$exclude = @(".venv", "lib", "__pycache__", "node_modules", "webui")
Get-ChildItem -Path $Backend -Force | Where-Object {
  $_.Name -notin $exclude -and $_.Name -ne ".env" -and $_.Name -ne ".deps-installed"
} | ForEach-Object {
  Copy-Item $_.FullName -Destination $Stage -Recurse -Force
}

# Build the companion UI and stage it as ./webui so the FastAPI server serves it
# same-origin (no Node/Vite needed at runtime on the target machine).
$Root = (Resolve-Path (Join-Path $Backend "..")).Path
Write-Host "Building companion UI (npm run build)..."
Push-Location $Root
& npm run build
if ($LASTEXITCODE -ne 0) { Pop-Location; Write-Error "npm run build failed" }
Pop-Location
Copy-Item (Join-Path $Root "dist") (Join-Path $Stage "webui") -Recurse -Force

# Vendor dependencies into ./lib (native Windows wheels) so the installed
# extension starts instantly with no first-run pip install (which would blow the
# MCP attach timeout). mcp_server.py / launcher.py add ./lib to sys.path.
Write-Host "Vendoring dependencies into lib (this may take a minute)..."
$libDir = Join-Path $Stage "lib"
New-Item -ItemType Directory -Path $libDir | Out-Null
& py -3 -m pip install --quiet --disable-pip-version-check `
  --target $libDir -r (Join-Path $Backend "requirements.txt")
if ($LASTEXITCODE -ne 0) { Write-Error "pip install --target failed" }

# Drop any __pycache__/*.pyc and workspace run artifacts that slipped through.
Get-ChildItem -Path $Stage -Recurse -Force -Include "__pycache__", "*.pyc" |
  Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
$ws = Join-Path $Stage "workspace"
if (Test-Path $ws) {
  Remove-Item (Join-Path $ws "runs") -Recurse -Force -ErrorAction SilentlyContinue
  Remove-Item (Join-Path $ws "logs") -Recurse -Force -ErrorAction SilentlyContinue
  Remove-Item (Join-Path $ws "events.jsonl") -Force -ErrorAction SilentlyContinue
}

if (Test-Path $Out) { Remove-Item $Out -Force }
$zip = [System.IO.Path]::ChangeExtension($Out, ".zip")
if (Test-Path $zip) { Remove-Item $zip -Force }

# Compress the *contents* of the stage so manifest.json is at the archive root.
Compress-Archive -Path (Join-Path $Stage "*") -DestinationPath $zip -Force
Move-Item $zip $Out -Force
Remove-Item $Stage -Recurse -Force

Write-Host "Built: $Out"
Write-Host "Install it by double-clicking the .mcpb (Claude Desktop -> Settings -> Extensions)."

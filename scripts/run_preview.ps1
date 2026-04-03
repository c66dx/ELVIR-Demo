$ErrorActionPreference = "Stop"

# Run backend (SQLite + seed) and frontend in separate terminals.
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptRoot
$backendDir = Join-Path $repoRoot "code\backend"
$frontendDir = Join-Path $repoRoot "code\frontend"

$backendCmd = "cd `"$backendDir`"; `$env:ENV='dev'; `$env:DATABASE_URL='sqlite:///./elvir_demo.db'; python -m pip install -r requirements.txt; python seed.py; python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
$frontendCmd = "cd `"$frontendDir`"; npm install; npm start"

Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

Write-Host "Preview started:"
Write-Host "Backend: http://localhost:8000"
Write-Host "Frontend: http://localhost:4200"

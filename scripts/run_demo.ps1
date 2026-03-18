$ErrorActionPreference = "Stop"

# Run backend in demo mode using SQLite + seed (no Docker, no migrations).
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptRoot
$backendDir = Join-Path $repoRoot "code\backend"

Set-Location $backendDir

$env:ENV = "dev"
$env:DATABASE_URL = "sqlite:///./elvir_demo.db"

python seed.py
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

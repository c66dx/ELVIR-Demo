#!/usr/bin/env bash
set -euo pipefail

# Run backend in demo mode using SQLite + seed (no Docker, no migrations).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKEND_DIR="${REPO_ROOT}/code/backend"

cd "${BACKEND_DIR}"

export ENV="dev"
export DATABASE_URL="sqlite:///./elvir_demo.db"

python seed.py
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

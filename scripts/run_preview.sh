#!/usr/bin/env bash
set -euo pipefail

# Run backend (SQLite + seed) and frontend together.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKEND_DIR="${REPO_ROOT}/code/backend"
FRONTEND_DIR="${REPO_ROOT}/code/frontend"

(
  cd "${BACKEND_DIR}"
  export ENV="dev"
  export DATABASE_URL="sqlite:///./elvir_demo.db"
  python -m pip install -r requirements.txt
  python seed.py
  python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
) &
BACKEND_PID=$!

cleanup() {
  kill "${BACKEND_PID}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

cd "${FRONTEND_DIR}"
npm install
npm start

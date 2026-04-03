#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/code/backend"
FRONTEND_DIR="$ROOT_DIR/code/frontend"
MIGRATION_DB="$BACKEND_DIR/ci_migration.db"

SKIP_FRONTEND="false"
REQUIRE_MIGRATIONS="false"
RUN_FRONTEND_UNIT_TESTS="true"

for arg in "$@"; do
  case "$arg" in
    --skip-frontend)
      SKIP_FRONTEND="true"
      ;;
    --require-migrations)
      REQUIRE_MIGRATIONS="true"
      ;;
    --frontend-unit-tests)
      RUN_FRONTEND_UNIT_TESTS="true"
      ;;
    *)
      echo "❌ Opción no reconocida: $arg"
      echo "Uso: ./scripts/quality_gate.sh [--skip-frontend] [--require-migrations] [--frontend-unit-tests]"
      exit 2
      ;;
  esac
done

echo "=== [check] Python >= 3.11 ==="
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" || {
  echo "❌ Se requiere Python 3.11 o superior. Actual: $(python -V 2>&1)"
  exit 1
}

echo "=== [backend] ruff ==="
(
  cd "$BACKEND_DIR"
  PYTHONPATH=. python -m ruff check .
)

echo "=== [backend] mypy ==="
(
  cd "$BACKEND_DIR"
  PYTHONPATH=. python -m mypy --config-file ../../pyproject.toml
)

echo "=== [backend] migraciones Alembic ==="
(
  cd "$BACKEND_DIR"
  rm -f "$MIGRATION_DB"
  if command -v alembic >/dev/null 2>&1; then
    DATABASE_URL="sqlite:///./ci_migration.db" alembic upgrade head
  else
    if [[ "$REQUIRE_MIGRATIONS" == "true" ]]; then
      echo "❌ Alembic no disponible y se solicitó --require-migrations"
      exit 1
    fi
    echo "⚠️  Alembic no disponible en este entorno local; se omite validación de migraciones."
  fi
)

echo "=== [backend] pytest + cobertura (mín. 70%, ver pyproject.toml) ==="
(
  cd "$BACKEND_DIR"
  PYTHONPATH=. python -m pytest -q --cov=app --cov-fail-under=70
)

if [[ "$SKIP_FRONTEND" == "false" ]]; then
  echo "=== [pre] package-lock frontend ==="
  python "$ROOT_DIR/scripts/check_frontend_lock_sync.py"

  echo "=== [frontend] build (smoke, production) ==="
  (
    cd "$FRONTEND_DIR"
    npm run build
  )
else
  echo "=== [frontend] omitido (--skip-frontend) ==="
fi

if [[ "$RUN_FRONTEND_UNIT_TESTS" == "true" ]]; then
  echo "=== [frontend] unit tests (npm run test:ci) ==="
  (
    cd "$FRONTEND_DIR"
    npm run test:ci
  )
fi

echo "✅ Quality gate completado (alineado con CI: ruff, mypy, alembic, pytest --cov, frontend build prod + tests)"

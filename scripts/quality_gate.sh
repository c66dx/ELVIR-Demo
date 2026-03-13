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

echo "[1/3] Validando migraciones Alembic..."
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

echo "[2/3] Ejecutando tests backend..."
(
  cd "$BACKEND_DIR"
  PYTHONPATH=. python -m unittest discover -s tests -v
)

if [[ "$SKIP_FRONTEND" == "false" ]]; then
  echo "[pre] Verificando alineación package-lock frontend..."
  python "$ROOT_DIR/scripts/check_frontend_lock_sync.py"

  echo "[3/3] Compilando frontend (smoke build)..."
  (
    cd "$FRONTEND_DIR"
    npm run build -- --configuration development
  )
else
  echo "[3/3] Frontend omitido por bandera --skip-frontend"
fi

if [[ "$RUN_FRONTEND_UNIT_TESTS" == "true" ]]; then
  echo "[extra] Ejecutando tests unitarios frontend con cobertura mínima..."
  (
    cd "$FRONTEND_DIR"
    npm run test:ci
  )
fi

echo "✅ Quality gate completado"

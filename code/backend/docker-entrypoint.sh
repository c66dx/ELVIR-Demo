#!/bin/sh
set -e
cd /app
python -m alembic upgrade head

# Por defecto sin access log de uvicorn (el middleware elvir.api ya registra cada request).
# UVICORN_ACCESS_LOG=1 para depuración con el log de acceso estándar de uvicorn.
EXTRA_ARGS=""
if [ "${UVICORN_ACCESS_LOG:-0}" != "1" ]; then
  EXTRA_ARGS="--no-access-log"
fi
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 $EXTRA_ARGS

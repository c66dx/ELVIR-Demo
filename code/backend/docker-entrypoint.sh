#!/bin/sh
set -e
cd /app

# Los volúmenes Docker en /app/uploads suelen ser propiedad de root; el proceso de la API corre como `elvir`.
# En Docker Desktop (Windows/WSL2) chown a veces no surte efecto sobre volúmenes nombrados; chmod asegura escritura.
mkdir -p /app/uploads/youths /app/uploads/profiles /app/uploads/audio
chown -R elvir:elvir /app/uploads 2>/dev/null || true
chmod -R 777 /app/uploads

EXTRA_ARGS=""
if [ "${UVICORN_ACCESS_LOG:-0}" != "1" ]; then
  EXTRA_ARGS="--no-access-log"
fi

gosu elvir python -m alembic upgrade head
exec gosu elvir uvicorn app.main:app --host 0.0.0.0 --port 8000 $EXTRA_ARGS

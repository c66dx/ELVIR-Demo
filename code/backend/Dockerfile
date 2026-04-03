# API ELVIR (FastAPI + Uvicorn). Contexto de build: este directorio (code/backend).
FROM python:3.11-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

RUN mkdir -p uploads/youths uploads/profiles uploads/audio

COPY docker-entrypoint.sh /docker-entrypoint.sh
# Evita shebang roto si el script se guardó con CRLF (build en Windows).
RUN sed -i 's/\r$//' /docker-entrypoint.sh \
    && chmod +x /docker-entrypoint.sh \
    && groupadd --system elvir \
    && useradd --system --gid elvir --home /app --no-create-home elvir \
    && chown -R elvir:elvir /app /docker-entrypoint.sh

EXPOSE 8000

# El entrypoint debe ejecutarse como root para ajustar permisos del volumen montado en /app/uploads.
USER root

# Liveness (sin BD); readiness en orquestadores vía GET /health/ready
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=4).read()" || exit 1

ENTRYPOINT ["/docker-entrypoint.sh"]

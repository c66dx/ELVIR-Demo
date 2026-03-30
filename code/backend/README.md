# ELVIR Backend

API REST del backend de la plataforma ELVIR, construida con FastAPI y SQLAlchemy.

Para una visión orientada a **revisión técnica o auditoría** (capas, seguridad, CI), ver [ARCHITECTURE.md](ARCHITECTURE.md).

## Requisitos

- Python 3.11+
- pip

## Instalación

```bash
cd code/backend
pip install -r requirements.txt
```

## Ejecución

1. Crear base de datos y cargar datos iniciales:

```bash
python -m alembic upgrade head
python seed.py
```

2. Iniciar el servidor:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

La API estará disponible en `http://localhost:8000`.

- Documentación Swagger: `http://localhost:8000/docs`
- Documentación ReDoc: `http://localhost:8000/redoc`
- Health resumen: `http://localhost:8000/health` (status + versión, sin BD)
- Liveness (solo proceso): `http://localhost:8000/health/live` — útil para `livenessProbe`
- Readiness (incluye BD): `http://localhost:8000/health/ready` — útil para `readinessProbe` (503 si la BD no responde)
- Métricas operativas: `http://localhost:8000/health/metrics`
- Desde la raíz del repo, chequeo externo de readiness (BD): `python scripts/check_health_ready.py --url http://localhost:8000/health/ready`
- Header de trazabilidad: respuestas incluyen `X-Request-ID` (si no viene en request, se genera).

### Observabilidad

- Los loggers bajo el namespace `elvir` (p. ej. `elvir.api`) incluyen automáticamente el **`request_id`** de la petición en curso (texto: prefijo `request_id=…`; JSON en prod: campo `request_id`), para correlacionar con la línea de acceso HTTP y con la cabecera de respuesta.
- Métricas acumuladas en memoria: `GET /health/metrics` (conteos por estado HTTP, etc.).
- Tras un **proxy inverso** (nginx, ingress), definir `RATE_LIMIT_TRUST_X_FORWARDED_FOR=true` solo si confiás en la cadena de proxies, para que el rate limit use la IP real del cliente (`X-Forwarded-For`).

## Usuarios de prueba (tras ejecutar seed, rama **main**)

| Email | Contraseña | Rol |
|-------|------------|-----|
| joven1@test.cl | test123 | JOVEN |
| joven2@test.cl | test123 | JOVEN (login deshabilitado en perfil de prueba) |
| prof@test.cl | test123 | PROFESIONAL |
| admin@test.cl | test123 | ADMIN |

Otra rama (p. ej. preview) puede definir más cuentas (Gmail, etc.): usar una BD acorde a ese `seed.py`.

## Configuración

Copiar `.env.example` a `.env` y ajustar si es necesario. Variables de entorno (opcional, archivo `.env`):

- `ENV`: Entorno de ejecución (`dev`, `staging`, `prod` o `production`).
- `LOG_LEVEL`: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` (default `INFO`).
- `LOG_JSON`: si no se define, en **`ENV=prod`** los logs del logger `elvir` van en **JSON una línea** (agregadores / CloudWatch); en `dev`/`staging` por defecto es texto legible. `LOG_JSON=true` o `false` fuerza el formato.
- `AUTO_CREATE_TABLES`: bandera heredada/deprecada (el startup ya no ejecuta `create_all`; usar migraciones Alembic).
- `DATABASE_URL`: URL de conexión PostgreSQL (default: `postgresql://elvir:elvir@localhost:5432/elvir`)
- `SECRET_KEY`: Clave para JWT (**obligatorio en producción**; generar con `openssl rand -hex 32`).
  - En `ENV=prod`, el backend rechaza el valor por defecto y exige **al menos 32 caracteres**.
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Vida del token JWT y de las cookies de sesión (default 1440 = 24 h).
- `CORS_ORIGINS`: Orígenes permitidos para CORS (default: `http://localhost:4200`)
- `APP_BASE_URL`: URL base para enlaces de activación (default: `http://localhost:4200`)
- `LIVEAVATAR_API_KEY`, `LIVEAVATAR_CONTEXT_ID`, `LIVEAVATAR_AVATAR_ID`, `LIVEAVATAR_VOICE_ID`: Para integración con LiveAvatar (simulación con avatar)
- `LIVEAVATAR_WEBHOOK_SECRET`: Token opcional para autorizar recepción de evaluaciones externas.
- `RATE_LIMIT_TRUST_X_FORWARDED_FOR`: Ver sección [Observabilidad](#observabilidad) (default `false`).
- **Almacenamiento de ficheros** (`STORAGE_BACKEND`): por defecto `local` (carpeta `uploads/` montada en `/uploads`). Para escalar con varias réplicas del API o mucho volumen, usar `s3` con un bucket compatible (AWS S3, MinIO, Cloudflare R2, etc.): definir `S3_BUCKET`, `S3_PUBLIC_BASE_URL` (URL base pública de los objetos), credenciales y opcionalmente `S3_ENDPOINT_URL` (MinIO) y `S3_KEY_PREFIX` (prefijo de clave en el bucket).

### Migración local → S3 y ciclo de vida del bucket

- **Migración de ficheros ya guardados en disco**: desde la raíz del repositorio, con las mismas variables `S3_*` que usará el backend, ejecutar `scripts/migrate_uploads_to_s3.py` (`--dry-run` para simular, `--skip-existing` para no sobrescribir objetos que ya existen). Después, poner `STORAGE_BACKEND=s3` y **actualizar las URLs en PostgreSQL** si antes apuntaban a `/uploads/...`: plantilla comentada en `scripts/rewrite_upload_urls_after_s3.sql` (tablas `users`, `youths`, `session_audios`; `support_material` solo filas cuya URL empiece por el prefijo antiguo, para no tocar enlaces externos).
- **Ciclo de vida (lifecycle)**: en el proveedor S3-compatible conviene definir reglas acordes a retención legal y coste: por ejemplo transición a almacenamiento más barato (S3 Standard → IA o Glacier) tras N días, expiración de objetos temporales si los hubiera, y si activas **versionado**, una regla para eliminar versiones no actuales pasado un tiempo. MinIO/R2 tienen conceptos equivalentes (ILM en MinIO). Ajusta políticas según normativa local sobre datos de menores y copias de seguridad.

## Conectar el frontend

El frontend usa `ApiService` y se conecta a `http://localhost:8000/api/v1` por defecto. La URL se configura en `code/frontend/src/environments/environment.ts`.

## Webhook de evaluacion (LiveAvatar u otro servicio)

Endpoint para recibir evaluaciones externas y guardarlas en `sessions.metrics`:

```
POST /api/v1/sessions/evaluation
Header opcional: X-ELVIR-Webhook-Secret: <token>
Body: { session_id | liveavatar_session_id, evaluation, source? }
```

Si `LIVEAVATAR_WEBHOOK_SECRET` esta configurado en `.env`, el header es obligatorio.

## Limpieza de datos (dev)

Script para limpiar datos no-seed (mantiene usuarios/roles seed):

```bash
python clean_user_data.py
python clean_user_data.py --delete-uploads
python clean_user_data.py --skip-reseed
```



## Testing

Ejecutar tests backend (recomendado; es lo que usa CI):

```bash
cd code/backend
pip install -r requirements.txt -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q --cov=app
```

## CI mínimo (GitHub Actions)

Workflow en `.github/workflows/ci.yml`:

- **Backend (rápido):** `ruff check`, `black --check app`, `mypy`, migraciones Alembic con SQLite de archivo, `pytest` con cobertura mínima del paquete `app`, build de imagen Docker.
- **Backend (PostgreSQL):** job `backend-tests-postgres` con servicio Postgres 16, `alembic upgrade head` y `pytest` con `DATABASE_URL` hacia ese servicio (misma suite; valida SQL/migraciones como en producción).
- **Frontend:** `npm ci` + `npm run test:ci` + `npm run build -- --configuration development`.
- **Lockfile frontend:** `python ../../scripts/check_frontend_lock_sync.py` para alinear `package-lock.json` con `package.json`.




## Verificación operacional externa (simple)

Además de revisar `/health/metrics` manualmente, puedes ejecutar un chequeo externo simple:

```bash
python scripts/check_health_metrics.py --url http://localhost:8000/health/metrics --fail-on-alert
```

- Si hay alertas activas (por ejemplo `error_rate_high`), el script termina con código de salida `1` cuando usas `--fail-on-alert`.
- Esto permite integrarlo en cron, monitor externo o pipeline de operación ligera.

## Migraciones de base de datos (Alembic)

Se incorpora base de migraciones versionadas en `code/backend/alembic`.

Comandos recomendados:

```bash
cd code/backend
python -m alembic upgrade head
```

Crear nueva revisión:

```bash
cd code/backend
python -m alembic revision -m "descripcion_del_cambio"
```

> Nota: `AUTO_CREATE_TABLES` está deprecado en arranque. Para cualquier entorno, priorizar migraciones Alembic.

## Imagen Docker

Build (desde la raíz del repo o con contexto `code/backend`):

```bash
docker build -t elvir-api:local ./code/backend
```

La imagen ejecuta `alembic upgrade head` al iniciar y levanta uvicorn en el puerto **8000**. El proceso corre como usuario no root (`elvir`).

- **HEALTHCHECK** de Docker: `GET /health/live` (solo proceso; no comprueba BD).
- En Kubernetes u orquestadores similares, usar **`readinessProbe`** contra `GET /health/ready` para la base de datos.
- **`UVICORN_ACCESS_LOG=1`**: habilita el access log estándar de uvicorn (por defecto está desactivado; el middleware `elvir.api` ya registra cada petición).

Variables típicas en runtime: `ENV=prod`, `DATABASE_URL`, `SECRET_KEY`, `LOG_LEVEL`, `LOG_JSON` (ver sección Configuración).



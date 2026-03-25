# ELVIR Backend

API REST del backend de la plataforma ELVIR, construida con FastAPI y SQLAlchemy.

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
- Health simple: `http://localhost:8000/health`
- Health con DB: `http://localhost:8000/health/live`
- Métricas operativas: `http://localhost:8000/health/metrics`
- Header de trazabilidad: respuestas incluyen `X-Request-ID` (si no viene en request, se genera).

## Usuarios de prueba (tras ejecutar seed)

| Email | Contraseña | Rol |
|-------|------------|-----|
| elvir.demo+joven1@gmail.com | test123 | JOVEN |
| elvir.demo+joven2@gmail.com | test123 | JOVEN |
| elvir.demo+joven3@gmail.com … joven6 | test123 | JOVEN |
| prof@test.cl | test123 | PROFESIONAL |
| admin@test.cl | test123 | ADMIN |

## Configuración

Copiar `.env.example` a `.env` y ajustar si es necesario. Variables de entorno (opcional, archivo `.env`):

- `ENV`: Entorno de ejecución (`dev`, `staging`, `prod` o `production`).
- `AUTO_CREATE_TABLES`: bandera heredada/deprecada (el startup ya no ejecuta `create_all`; usar migraciones Alembic).
- `DATABASE_URL`: URL de conexión PostgreSQL (default: `postgresql://elvir:elvir@localhost:5432/elvir`)
- `SECRET_KEY`: Clave para JWT (**obligatorio en producción**; generar con `openssl rand -hex 32`).
  - En `ENV=prod`, el backend rechaza el valor por defecto por seguridad.
- `CORS_ORIGINS`: Orígenes permitidos para CORS (default: `http://localhost:4200`)
- `APP_BASE_URL`: URL base para enlaces de activación (default: `http://localhost:4200`)
- `LIVEAVATAR_API_KEY`, `LIVEAVATAR_CONTEXT_ID`, `LIVEAVATAR_AVATAR_ID`, `LIVEAVATAR_VOICE_ID`: Para integración con LiveAvatar (simulación con avatar)
- `LIVEAVATAR_WEBHOOK_SECRET`: Token opcional para autorizar recepción de evaluaciones externas.

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

Ejecutar tests backend:

```bash
cd code/backend
PYTHONPATH=. python -m unittest discover -s tests -v
```


## CI mínimo (GitHub Actions)

Se agregó un workflow en `.github/workflows/ci.yml` que ejecuta:

- Backend: instalación de dependencias + validación de migraciones (`DATABASE_URL=sqlite:///./ci_migration.db python -m alembic upgrade head`) + tests (`PYTHONPATH=. python -m unittest discover -s tests -v`).
- Frontend: `npm ci` + `npm run test:ci` (bloqueante con cobertura mínima) + `npm run build -- --configuration development`.
- Frontend lockfile alignment check: `python ../../scripts/check_frontend_lock_sync.py` (desde `code/frontend` en CI) para asegurar reproducibilidad de `npm ci`.




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




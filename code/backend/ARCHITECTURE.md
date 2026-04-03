# Arquitectura del backend ELVIR

Documento breve para auditorías, incorporación de desarrolladores y presentación del sistema.

## Stack

- **Runtime:** **Python 3.11+** (no soportado 3.10: `StrEnum`, `datetime.UTC`, tipado y CI alineados a 3.11). **FastAPI** (ASGI), **Uvicorn**. Docker y GitHub Actions fijan 3.11; en despliegues tipo Render conviene `runtime.txt` en la raíz del servicio (ver repo).
- **Datos:** **SQLAlchemy** 2.x sobre **PostgreSQL** en producción; migraciones con **Alembic** (`alembic/versions/`).
- **Validación:** Pydantic v2 en `app/schemas/`.
- **Seguridad:** JWT y cookies HttpOnly, **CSRF** en mutaciones con cookie, **slowapi** para rate limiting, cabeceras de seguridad HTTP (incl. **HSTS** solo si `ENV=prod`).

## Capas

| Capa | Ubicación | Rol |
|------|-----------|-----|
| HTTP | `app/routers/` | Rutas, dependencias de auth/roles, delegación a servicios. |
| Dominio / aplicación | `app/services/` | Reglas de negocio, acceso a sesión DB, orquestación. |
| Persistencia | `app/models/` | Modelos SQLAlchemy; tablas y relaciones. |
| Contratos API | `app/schemas/` | Request/response y errores tipados expuestos al cliente. |
| Infraestructura | `app/core/` | Errores unificados (`ErrorCode`, `request_id`), middleware (CSRF, auditoría, métricas), almacenamiento local/S3, logging. |

Los routers no deberían contener lógica pesada; si crece, extraer a servicios.

## Errores y API

- Respuestas de error coherentes: cuerpo con `detail` y objeto `error` (código, mensaje, `request_id`).
- OpenAPI en `/docs` y `/redoc`: esquema `ErrorResponse` reutilizado; cabecera **`X-Request-ID`** en respuestas para correlación con logs.

## Observabilidad

- Logger `elvir` (y sub-loggers como `elvir.api`) con **`request_id`** en contexto (`contextvars`).
- Endpoints **`/health`**, **`/health/live`**, **`/health/ready`**, **`/health/metrics`** para probes y métricas operativas.

## Ficheros y escalado

- Por defecto ficheros bajo `uploads/` servidos en `/uploads`; opción **`STORAGE_BACKEND=s3`** (bucket compatible) para varias réplicas sin disco compartido. Ver `README.md` y scripts en la raíz del repo.

## Puertas de calidad (CI)

En cada PR/push (`.github/workflows/ci.yml`), sobre `code/backend`:

1. **Ruff** — lint (imports, errores comunes, pyupgrade).
2. **Black** — formato (`black --check app`), línea 120 (ver `pyproject.toml` en la raíz del repo).
3. **mypy** — tipado estático en `app/core` y `app/schemas` (alcance acotado a coste razonable).
4. **Alembic** — `upgrade head` contra SQLite en el job principal.
5. **pytest** — tests con cobertura mínima del paquete `app` (SQLite en memoria por defecto vía `tests/conftest.py`).

**Job adicional `backend-tests-postgres`:** servicio **PostgreSQL 16**, `alembic upgrade head` y la **misma suite pytest** con `DATABASE_URL` apuntando al contenedor. Así se validan migraciones y consultas en el dialecto real de producción, no solo SQLite.

Desarrollo local típico tras instalar `requirements-dev.txt`:

```bash
cd code/backend
python -m ruff check app
python -m black app
python -m mypy --config-file ../../pyproject.toml
PYTHONPATH=. python -m pytest -q --cov=app
```

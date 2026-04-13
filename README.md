# ELVIR — Entrenador Laboral Virtual con IA

Plataforma web para simulaciones de entrevistas laborales asistidas por IA, que apoya a jóvenes de Teletón con discapacidad. Incluye frontend Angular y backend FastAPI, con integración al servicio externo LiveAvatar para el avatar conversacional.

**Autora del repositorio:** Catalina  
**Contexto:** Universidad Andrés Bello (UNAB)

---

## Inicio rápido (demo local con SQLite)

Requisitos mínimos: **Python 3.11+** y **Node.js 18+**.

Backend (SQLite + seed):

```bash
cd code/backend
python -m pip install -r requirements.txt
# Crear .env demo (solo una vez)
printf "ENV=dev\nDATABASE_URL=sqlite:///./elvir_demo.db\n" > .env
python seed.py
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd code/frontend
npm install
npm start
```

La app queda en `http://localhost:4200` y el backend en `http://localhost:8000`.

> Nota: `seed.py` crea tablas y carga datos de prueba; se puede ejecutar más de una vez sin duplicar.

---

## Desarrollo con PostgreSQL (Docker)

```bash
# Levantar PostgreSQL
docker compose up -d

# Backend
cd code/backend
pip install -r requirements.txt
python -m alembic upgrade head
python seed.py
python -m uvicorn app.main:app --reload --port 8000
```

Si no existe `.env`, copia `.env.example` a `.env`:
- Windows: `copy .env.example .env`
- Linux/Mac: `cp .env.example .env`

La URL por defecto de PostgreSQL es `postgresql://elvir:elvir@localhost:5432/elvir` (compatible con `docker compose`).

---

## Credenciales de prueba (seed)

| Email | Contraseña | Rol |
|-------|------------|-----|
| `elvir.demo+joven1@gmail.com` | `test123` | JOVEN |
| `elvir.demo+joven2@gmail.com` | `test123` | JOVEN (login deshabilitado) |
| `elvir.demo+joven3@gmail.com` | `test123` | JOVEN |
| `elvir.demo+joven4@gmail.com` | `test123` | JOVEN |
| `elvir.demo+joven5@gmail.com` | `test123` | JOVEN |
| `elvir.demo+joven6@gmail.com` | `test123` | JOVEN |
| `prof@test.cl` | `test123` | PROFESIONAL |
| `admin@test.cl` | `test123` | ADMIN |

---

## LiveAvatar (contextos)

- Cada combinación **cargo + caso** tiene un `context_id`.
- Los IDs se guardan en `simulation_templates.liveavatar_context_id`.
- Para sincronizar por nombre desde LiveAvatar:

```bash
cd code/backend
python scripts/sync_liveavatar_contexts.py --apply-db --timeout 60 --retries 2 --fail-missing
```

Variables necesarias:
- `LIVEAVATAR_API_KEY`
- `LIVEAVATAR_AVATAR_ID`
- `LIVEAVATAR_VOICE_ID`
- `LIVEAVATAR_API_BASE` (por defecto `https://api.liveavatar.com/v1`)

Detalles completos en `docs/liveavatar/integracion-liveavatar.md`.

---

## Health-check y keep-alive

El backend expone:
- `GET /health`
- `GET /health/live`
- `GET /health/ready`

Para evitar que Render “duerma”, puedes pingear `https://<tu-backend>/health/live` cada 5–10 minutos (ej. UptimeRobot).

---

## Estructura del proyecto

- `code/frontend/` — Angular (SPA) por roles.
- `code/backend/` — FastAPI + SQLAlchemy + PostgreSQL.
- `docs/` — arquitectura, flujos, modelo de datos, API y LiveAvatar.

Índice de docs: `docs/README.md`.

---

## Quality gate (recomendado antes de push/PR)

```bash
./scripts/quality_gate.sh
```

Solo backend:

```bash
./scripts/quality_gate.sh --skip-frontend
```

Chequeo rápido de reproducibilidad frontend (package/lock):

```bash
python scripts/check_frontend_lock_sync.py
```

Chequeo operativo externo:

```bash
python scripts/check_health_metrics.py --url http://localhost:8000/health/metrics --fail-on-alert
```

Readiness (conexión a base de datos):

```bash
python scripts/check_health_ready.py --url http://localhost:8000/health/ready
```

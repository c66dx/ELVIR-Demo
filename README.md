# ELVIR — Entrenador Laboral Virtual con IA

Plataforma web para simulaciones de entrevistas laborales asistidas por IA, que apoya a jóvenes de Teletón con discapacidad. Incluye documentación, frontend Angular y backend FastAPI, con integración al servicio externo LiveAvatar para el avatar conversacional.

**Autora:** Catalina  
**Contexto:** Práctica profesional — UNAB

---

## Modo demo rápido (sin Docker, solo seed)

Pensado para mostrar la interfaz con datos de prueba sin instalar PostgreSQL ni correr migraciones.
Si solo quieres demo, usa la branch `preview-seed`.

Requisitos mínimos: Python 3.11+ y Node.js 18+.

```bash
git clone https://github.com/c66dx/ELVIR-Demo.git
cd ELVIR-Demo
git checkout preview-seed
```

### Backend (SQLite)

Windows (PowerShell):

```powershell
cd code/backend
python -m pip install -r requirements.txt
cd ../..
.\scripts\run_demo.ps1
```

Linux/Mac:

```bash
cd code/backend
python -m pip install -r requirements.txt
cd ../..
./scripts/run_demo.sh
```

El backend queda en `http://localhost:8000`.

### Todo en un comando (backend + frontend)

Windows (PowerShell):

```powershell
.\scripts\run_preview.ps1
```

Linux/Mac / Git Bash:

```bash
./scripts/run_preview.sh
```

Esto abre dos terminales o procesos: backend en `http://localhost:8000` y frontend en `http://localhost:4200`.

### Frontend

```bash
cd code/frontend
npm install
npm start
```

La app queda en `http://localhost:4200`.

> Nota: `seed.py` crea tablas y carga datos de prueba; se puede ejecutar más de una vez sin duplicar.

## Ejecutar en otro PC (pasos completos)

Para clonar y ejecutar el proyecto en cualquier Windows, Mac o Linux.

### 1. Instalar requisitos previos

| Herramienta | Versión | Descarga |
|-------------|---------|----------|
| **Git** | Cualquiera | https://git-scm.com/downloads |
| **Python** | 3.11 o superior | https://www.python.org/downloads/ |
| **Node.js** | 18 o superior (LTS recomendado) | https://nodejs.org/ |
| **Docker** | Cualquiera | https://www.docker.com/get-started (para PostgreSQL) |

**Importante:** Al instalar Python, marcar la opción *"Add Python to PATH"*. Al instalar Node.js, se instala también npm automáticamente.

### 2. Clonar el repositorio

```bash
git clone https://github.com/c66dx/ELVIR-Demo.git
cd ELVIR-Demo
```

### 3. Configurar y ejecutar el backend

Abre una terminal:

```bash
# 1. Levantar PostgreSQL (Docker)
docker compose up -d

# 2. Backend
cd code/backend
pip install -r requirements.txt
python -m alembic upgrade head
python seed.py
python -m uvicorn app.main:app --reload --port 8000
```

Deja esta terminal abierta. El backend queda en `http://localhost:8000`.

**Si no existe `.env`:** copia `.env.example` a `.env`:
- Windows: `copy .env.example .env`
- Linux/Mac: `cp .env.example .env`  
La URL de PostgreSQL por defecto es `postgresql://elvir:elvir@localhost:5432/elvir` (compatible con `docker compose`).

### 4. Configurar y ejecutar el frontend

Abre **otra terminal** (la del backend sigue corriendo):

```bash
cd code/frontend
npm install
npm start
```

Espera a que compile (~30 segundos). La app queda en `http://localhost:4200`.

### 5. Abrir la aplicación

Abre el navegador en **http://localhost:4200** e inicia sesión con:

| Email | Contraseña | Rol |
|-------|------------|-----|
| joven1@test.cl | test123 | JOVEN |
| joven2@test.cl | test123 | JOVEN |
| prof@test.cl | test123 | PROFESIONAL |
| admin@test.cl | test123 | ADMIN |

### Problemas frecuentes

| Error | Solución |
|-------|----------|
| `python` no reconocido | Instala Python y añádelo al PATH, o usa `py` (Windows) en lugar de `python` |
| `pip` no reconocido | Ejecuta `python -m pip install -r requirements.txt` |
| `npm` no reconocido | Instala Node.js desde nodejs.org (incluye npm) |
| Puerto 8000 o 4200 en uso | Cierra otros programas que los usen, o cambia el puerto en el comando |
| El frontend no conecta al backend | Asegúrate de que el backend esté corriendo en la terminal 1 antes de abrir la app |

---

## Cómo leer este proyecto

Te explico cómo navegar todo esto para que no te pierdas. Yo lo organicé así porque primero necesitas entender *qué* hace el sistema y *cómo* está pensado; después ya tiene sentido meterse al código.

### Paso 1: Empieza por la documentación

Todo lo que diseñé está en `docs/`. Ahí está el “por qué” y el “cómo” antes de tocar una línea de código.

**Orden que yo seguiría:**

1. **`docs/arquitectura/`**  
   Arquitectura en tres capas: frontend (Angular), backend (FastAPI) y el servicio externo LiveAvatar. Qué hace cada parte y cómo se conectan.

2. **`docs/flujos/`**  
   Flujos del joven, profesional y admin. Cómo entra cada uno, qué pantallas ve, qué puede hacer. Incluye diagramas SVG (flujo joven, profesional, admin, activación, LiveAvatar).

3. **`docs/modelo-datos/`**  
   Modelo de datos: entidades, relaciones, diccionario y diagramas Mermaid (ERD, flowcharts, secuencias). Base para entender la persistencia.

4. **`docs/api/`**  
   Endpoints del backend. Contratos, qué espera cada ruta y qué devuelve.

5. **`docs/flujos/roles-y-permisos.md`**  
   Roles (JOVEN, PROFESIONAL, ADMIN), alcance de cada uno y reglas de negocio.

6. **`docs/liveavatar/integracion-liveavatar.md`**  
   Flujo de integración con LiveAvatar (Context Dinámico): construcción del prompt, PATCH al contexto, creación de sesión.

7. **`docs/propuesta/`**  
   Propuesta técnica original, addendum y contexto del proyecto.

Con eso ya tienes el mapa mental del sistema. A partir de ahí, el código encaja en ese diseño.

---

### Paso 2: El código

El código está en `code/`:

- **`code/frontend/`** — SPA Angular 19+ con componentes standalone, rutas por rol, guards (auth, guest, role) y conectada al backend FastAPI. Integra LiveAvatar vía LiveKit para la simulación conversacional.
- **`code/backend/`** — API REST FastAPI con SQLAlchemy y PostgreSQL. Autenticación JWT, gestión de jóvenes, sesiones, material de apoyo e integración con LiveAvatar.

**Para entender el frontend:**

1. **`code/frontend/README.md`** — Estructura del proyecto: carpetas, modelos, servicios, guards, features.
2. **Estructura rápida:**
   - `src/app/core/` → Modelos, servicios, guards (auth, guest, role)
   - `src/app/layout/` → Shell, sidebar, topbar
   - `src/app/features/` → Funcionalidades por rol (auth, joven, profesional, admin)
   - `src/app/shared/` → Componentes reutilizables

3. **Roles:**
   - **Joven:** Dashboard, simulaciones con avatar, historial, material de apoyo
   - **Profesional:** Dashboard, gestión de jóvenes, sesiones supervisadas, sugerir material
   - **Admin:** Acceso completo y gestión de invitaciones

---

## Qué incluye esta entrega

- **`docs/`** — Documentación técnica, flujos, arquitectura, modelo de datos, diagramas Mermaid
- **`code/frontend/`** — Aplicación web Angular 19 (MVP funcional, conectada al backend)
- **`code/backend/`** — API REST FastAPI con PostgreSQL (MVP)

El frontend usa `ApiService` que llama al backend. La URL base se configura en `code/frontend/src/environments/environment.ts` (desarrollo: `http://localhost:8000/api/v1`).

## Webhook de evaluacion (LiveAvatar u otro servicio)

Endpoint para recibir evaluaciones externas y guardarlas en `sessions.metrics`:

```
POST /api/v1/sessions/evaluation
Header opcional: X-ELVIR-Webhook-Secret: <token>
Body: { session_id | liveavatar_session_id, evaluation, source? }
```

Si `LIVEAVATAR_WEBHOOK_SECRET` esta configurado en `.env`, el header es obligatorio.

## Limpieza de datos (dev)

```bash
python code/backend/clean_user_data.py
python code/backend/clean_user_data.py --delete-uploads
python code/backend/clean_user_data.py --skip-reseed
```


---

## Quality gate (recomendado antes de push/PR)

Para validar en un solo comando lo que más impacta la nota final (migraciones + tests backend + build frontend):

```bash
./scripts/quality_gate.sh
```

Si estás trabajando solo backend:

```bash
./scripts/quality_gate.sh --skip-frontend
```

Si quieres que falle explícitamente cuando no pueda validar migraciones:

```bash
./scripts/quality_gate.sh --require-migrations
```

Si además quieres correr unit tests frontend (cuando las dependencias de test estén instaladas):

```bash
./scripts/quality_gate.sh --frontend-unit-tests
```

Este gate replica los checks críticos de CI y facilita una evidencia reproducible de calidad.

Verificación rápida de reproducibilidad frontend (package/lock):

```bash
python scripts/check_frontend_lock_sync.py
```


### Chequeo operacional externo rápido (alertas de salud)

Para validar desde fuera del backend el estado operativo y alertas simples (`/health/metrics`):

```bash
python scripts/check_health_metrics.py --url http://localhost:8000/health/metrics --fail-on-alert
```

Esto sirve para integrarlo en un cron o monitor externo liviano y fallar cuando exista una alerta activa.

---

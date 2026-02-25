# Estructura del Frontend ELVIR

Este documento explica la organización del frontend de la plataforma ELVIR para que cualquier persona que trabaje en el proyecto entienda qué hay en cada carpeta y para qué sirve.

---

## Visión general

El frontend es una **SPA (Single Page Application)** construida con **Angular** (versión 19+). Usa componentes **standalone**, routing con guards por rol, y se conecta al backend FastAPI vía `ApiService`. La arquitectura sigue un patrón por **features** (funcionalidades) y separa claramente core, layout, features y shared.

---

## Raíz del proyecto (`frontend/`)

- **`src/`** — Código fuente de la aplicación
- **`angular.json`** — Configuración de Angular CLI
- **`package.json`** — Dependencias y scripts del proyecto

---

## Punto de entrada (`src/`)

### `main.ts`
Arranca la aplicación Angular. Importa `AppComponent` y `appConfig`, y hace el bootstrap. Es el primer archivo que se ejecuta.

### `index.html`
HTML base. Contiene `<app-root>`, donde Angular monta la app.

### `styles.scss`
Estilos globales aplicados a toda la aplicación.

---

## Código de la app (`src/app/`)

### `app.component.ts`
Componente raíz. Solo define un `<router-outlet>` donde se renderizan las rutas.

### `app.config.ts`
Configuración de la aplicación: providers (router, zone, etc.). Aquí se registran servicios globales y la configuración del router.

### `app.routes.ts`
Define todas las rutas de la aplicación. Incluye:
- Rutas públicas (login)
- Rutas protegidas con `authGuard` (requieren login)
- Rutas por rol (`jovenGuard`, `profesionalGuard`)
- Rutas hijas dentro del layout (AppShell)

---

## Core (`src/app/core/`)

Contiene la lógica compartida, modelos, servicios y guards. No depende de features concretas.

### `core/models/`
Interfaces y tipos TypeScript que representan las entidades del dominio:

| Archivo | Descripción |
|---------|-------------|
| `types.model.ts` | Tipos base: `Role`, `SessionStatus`, `SessionMode`, `Difficulty`, `MaterialType` |
| `user.model.ts` | `User`, `UserRole` |
| `youth.model.ts` | `Youth` (joven) |
| `professional.model.ts` | `Professional` |
| `job-role.model.ts` | `JobRole` (cargo/rol de trabajo) |
| `case.model.ts` | `Case` (caso de simulación) |
| `simulation-template.model.ts` | `SimulationTemplate` (plantilla cargo+caso) |
| `session.model.ts` | `Session` (sesión de simulación) |
| `support-material.model.ts` | `SupportMaterial` (material de apoyo) |
| `material-suggestion.model.ts` | `MaterialSuggestion` (material sugerido a un joven) |
| `material-view.model.ts` | `MaterialView` (registro de material visto) |
| `interview-summary.model.ts` | `InterviewSummary` (resumen de entrevista) |
| `index.ts` | Reexporta todos los modelos |

### `core/services/`
Servicios inyectables usados en toda la app:

| Servicio | Función |
|----------|---------|
| `auth.service.ts` | Autenticación: token y rol en `localStorage`, login/logout, `isLoggedIn()`, `getRole()` |
| `api.service.ts` | Cliente HTTP para el backend FastAPI: login, catálogos, sesiones, material, jóvenes, etc. |
| `youth.service.ts` | Obtiene el `youthId` del usuario JOVEN actual a partir de `getMe()` y la lista de jóvenes |
| `session-end.service.ts` | Guarda el resultado de una sesión finalizada (COMPLETADA, CANCELADA, ERROR) para mostrarlo en `SessionEndComponent` |

### `core/guards/`
Guards de rutas que controlan el acceso:

| Guard | Función |
|-------|---------|
| `auth.guard.ts` | Solo permite acceso si el usuario está logueado. Si no, redirige a `/login` |
| `guest.guard.ts` | Solo permite acceso a usuarios no logueados (ej. login). Si está logueado, redirige al dashboard según rol |
| `role.guard.ts` | `jovenGuard` y `profesionalGuard`: restringen rutas por rol. Si el rol no coincide, redirige al dashboard correspondiente |

---

## Layout (`src/app/layout/`)

Componentes que definen la estructura visual común de la app (shell, sidebar, topbar).

### `app-shell/`
- **`app-shell.component.ts`** — Contenedor principal: sidebar + topbar + área de contenido
- **`app-shell.component.html`** — Estructura HTML del layout
- **`app-shell.component.scss`** — Estilos del layout

### `sidebar/`
- **`sidebar.component.ts`** — Menú lateral con enlaces según rol (JOVEN, PROFESIONAL o ADMIN)
- **`sidebar.component.html`** — Lista de `RouterLink` con `RouterLinkActive`
- **`sidebar.component.scss`** — Estilos del sidebar

### `topbar/`
- **`topbar.component.ts`** — Barra superior con logout
- **`topbar.component.html`** — Contenido del topbar
- **`topbar.component.scss`** — Estilos del topbar

---

## Features (`src/app/features/`)

Cada feature agrupa los componentes de una funcionalidad. Cada componente suele tener `.ts`, `.html` y `.scss`.

### `features/auth/`
Autenticación.

#### `login/`
- **`login.component.ts`** — Formulario de login, llama a `ApiService.login()`, guarda sesión con `AuthService.setSession()` y redirige según rol
- **`login.component.html`** — Formulario email/password
- **`login.component.scss`** — Estilos del login

#### `activate/`
- **`activate.component.*`** — Pantalla de activación de cuenta: el joven define su contraseña usando el token de invitación

---

### `features/joven/`
Funcionalidades para el rol JOVEN.

#### `dashboard/`
- **`dashboard-joven.component.*`** — Dashboard del joven: KPIs (total sesiones, última sesión) y enlaces a Nueva Simulación, Historial y Material

#### `simulacion/`
Flujo de simulaciones del joven.

| Componente | Función |
|-------------|---------|
| **`nueva-simulacion.component.*`** | Formulario para elegir cargo y caso. Crea sesión y navega a la simulación |
| **`simulacion-detail.component.*`** | Pantalla de simulación: iframe LiveAvatar (placeholder), cargo/caso seleccionados, botones Finalizar/Cancelar/Simular error. Maneja sesión no encontrada y error de conexión |
| **`session-end/`** | **`session-end.component.*`** — Pantalla final tras cerrar sesión: muestra estado (COMPLETADA, CANCELADA, ERROR) y botón para volver |

#### `historial/`
- **`historial-joven.component.*`** — Lista del historial de sesiones del joven

#### `material/`
- **`material-joven.component.*`** — Material de apoyo: secciones "Sugerido para ti" y "Catálogo", con indicador Visto/No visto

---

### `features/profesional/`
Funcionalidades para el rol PROFESIONAL.

#### `dashboard/`
- **`dashboard-profesional.component.*`** — Dashboard: KPIs y enlace a Jóvenes

#### `jovenes/`
Gestión de jóvenes.

| Componente | Función |
|-------------|---------|
| **`jovenes-list.component.*`** | Tabla de jóvenes con acciones Ver, Editar, Desactivar |
| **`joven-form.component.*`** | Formulario crear/editar joven (reutilizado) |
| **`joven-detail-wrapper.component.ts`** | Wrapper con `router-outlet` para rutas hijas del perfil |
| **`perfil-joven.component.*`** | Perfil del joven: datos, historial, botones "Registrar resumen" y "Sugerir material" |
| **`supervisada/`** | **`supervised-start.component.*`** — Inicio de simulación supervisada: selección cargo/caso y botón para iniciar |

---

### `features/admin/`
Funcionalidades para el rol ADMIN.

| Componente | Función |
|-------------|---------|
| **`dashboard-admin.component.*`** | Dashboard: enlaces a Profesionales y Material |
| **`profesionales-list.component.*`** | Lista de profesionales con acciones Crear, Editar |
| **`profesional-form.component.*`** | Formulario crear/editar profesional |
| **`material-form.component.*`** | Formulario subir material general |

---

## Shared (`src/app/shared/`)

Componentes reutilizables entre features.

### `status-badge/`
- **`status-badge.component.ts`** — Badge que muestra el estado de una sesión (EN_CURSO, COMPLETADA, CANCELADA, ERROR) con colores distintos

---

## Flujo de rutas (resumen)

```
/login                    → LoginComponent (guestGuard)
'' (AppShell)
├── /joven/simulacion/nueva     → NuevaSimulacionComponent (jovenGuard)
├── /joven/simulacion/:sessionId → SimulacionDetailComponent (authGuard)
├── /session-end                → SessionEndComponent (authGuard)
├── /joven (jovenGuard)
│   ├── /dashboard              → DashboardJovenComponent
│   ├── /simulacion/nueva       → NuevaSimulacionComponent
│   ├── /historial              → HistorialJovenComponent
│   └── /material               → MaterialJovenComponent
├── /profesional (profesionalGuard)
│   ├── /dashboard              → DashboardProfesionalComponent
│   └── /jovenes
│       ├── ''                  → JovenesListComponent
│       ├── /nuevo              → JovenFormComponent
│       └── /:youthId
│           ├── ''              → PerfilJovenComponent
│           ├── /editar         → JovenFormComponent
│           └── /supervisada/nueva → SupervisedStartComponent
└── /admin (adminGuard)
    ├── /dashboard              → DashboardAdminComponent
    ├── /profesionales          → ProfesionalesListComponent
    ├── /profesionales/nuevo    → ProfesionalFormComponent
    └── /material/nuevo         → MaterialFormComponent
```

---

## Cómo añadir una nueva funcionalidad

1. **Modelos** — Si hace falta, añadir interfaces en `core/models/`
2. **Servicios** — Lógica de negocio o llamadas API en `core/services/`
3. **Feature** — Crear carpeta en `features/` con componentes
4. **Rutas** — Registrar rutas en `app.routes.ts` con los guards adecuados
5. **Navegación** — Añadir enlaces en `sidebar` si corresponde

---

## Notas técnicas

- **Standalone components**: No hay módulos NgModule; cada componente se declara como standalone
- **API**: `ApiService` llama al backend FastAPI (`environment.apiUrl`). Requiere backend en ejecución para funcionar.
- **Auth**: Token JWT y rol en `localStorage`. El login se hace contra el backend vía `ApiService.login()`.
- **RBAC**: Tres roles: `JOVEN`, `PROFESIONAL` y `ADMIN`. Los guards y el sidebar filtran por rol

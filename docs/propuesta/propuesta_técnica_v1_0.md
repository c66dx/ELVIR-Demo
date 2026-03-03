# Propuesta Técnica y Planificación Detallada  
## Plataforma Web para habilitación de ELVIR  
### Simulador de Entrevista Laboral asistido por IA

---

# 0. Control del documento

- **Versión:** v1.0 (adaptada a definición vigente)  
- **Autora:** Catalina  
- **Fecha:** 29/01/2026  
- **Contexto:** Práctica profesional – Desarrollo MVP (demo funcional)  
- **Documento base:** “Front_Back_Simulador_de_Entrevista_Laboral.pdf”  
- **Actualización técnica vigente:** Ver `addendum_v1_1.md` + docs (arquitectura, flujos, modelo y API)

---

# 1. Propósito del documento

Este documento especifica la propuesta técnica (frontend + backend + persistencia + integración con servicio externo) y la planificación para construir un **MVP (demo funcional)** de la plataforma web que habilita ELVIR.

El objetivo es asegurar trazabilidad entre:

- Casos de uso y requisitos
- Pantallas
- Arquitectura del sistema
- Modelo de datos + diccionario
- Endpoints del backend
- Decisiones sobre integración con LiveAvatar

---

# 2. Objetivo del proyecto

Diseñar e implementar una plataforma web funcional que permita la habilitación de ELVIR, apoyando a jóvenes de Teletón en la preparación de entrevistas laborales mediante el consumo de un servicio externo (LiveAvatar) tratado como **caja negra**.

El sistema debe permitir:

- Simulación de entrevistas con avatar conversacional.
- Registro estructurado de sesiones (trazabilidad de intentos).
- Seguimiento por parte de profesionales (historial + resumen cualitativo + sugerencias).
- Gestión básica de material de apoyo.

---

# 3. Alcance del MVP

## 3.1 Alcance funcional

Se implementan los siguientes casos de uso (MVP):

- **CU-01** Iniciar sesión (roles: joven / profesional)
- **CU-02** Acceder a simulación de entrevista (joven)
- **CU-03** Acceder a material de apoyo (joven)
- **CU-04** Visualizar jóvenes asignados (profesional)
- **CU-05** Gestionar perfil de joven (profesional)
- **CU-06** Visualizar perfil e historial del joven (profesional)
- **CU-07** Registrar resumen cualitativo de sesión (profesional)
- **CU-08** Sugerir material de apoyo posterior a sesión (profesional)

> Nota de contexto: el documento base menciona “grabación audio/video” y “análisis automático”. En el MVP vigente, esto se trata como **fuera de alcance** salvo que LiveAvatar entregue algo listo y exportable sin desarrollo adicional.

---

## 3.2 Pantallas incluidas (Frontend Angular)

1. Inicio de sesión
2. Dashboard Joven
3. Simulación de entrevista (vista con integración de avatar)
4. Historial de sesiones (joven)
5. Material de apoyo (joven)
6. Dashboard Profesional (tabla/listado de jóvenes)
7. Perfil del joven (historial + acciones)
8. Formulario crear/editar joven

---

## 3.3 Alcance técnico mínimo (Backend + DB)

- API REST en Python (**FastAPI recomendado**)
- Persistencia relacional para:
  - Usuarios y roles
  - Jóvenes
  - Profesionales
  - Asignaciones
  - Catálogos (cargos / casos)
  - Plantillas de simulación (mapeo hacia LiveAvatar)
  - Sesiones + estados + timestamps
  - Eventos de sesión (trazabilidad ligera; opcional MVP pero recomendado)
  - Resúmenes cualitativos
  - Material de apoyo + sugerencias + vistas
  - Competencias (catálogo + evaluación por sesión) **si ya está definido el catálogo** (si no, se deja como MVP+)
- Integración con LiveAvatar tratada como **caja negra**
- Registro de métricas simples (derivadas o retornadas por proveedor cuando aplique)

---

# 4. Fuera de alcance

- Implementación o entrenamiento de modelos IA propios.
- Procesamiento avanzado de audio/video (STT, emoción, prosodia) como desarrollo ELVIR.
- Producto final productivo (es demo funcional).
- Diseño gráfico avanzado (se prioriza claridad y usabilidad).
- Sistemas complejos de analítica/BI.

> Si LiveAvatar entrega resúmenes/evaluaciones, ELVIR puede **registrarlos/mostrarlos**, pero no los implementa internamente en esta etapa.

---

# 5. Stakeholders

- **Joven:** usuario final del simulador.
- **Profesional Teletón:** seguimiento, gestión y retroalimentación.
- **Equipo ELVIR / UNAB:** contraparte técnica y validación conceptual.

---

# 6. Requisitos del sistema

## 6.1 Requisitos funcionales (resumen)

- **RF-01** Autenticación por credenciales
- **RF-02** Identificación de rol y redirección
- **RF-03** Simulación de entrevista vía servicio externo (LiveAvatar)
- **RF-04** Registro estructurado de sesión (intento) y su estado
- **RF-05** Gestión de jóvenes (crear/editar/desactivar)
- **RF-06** Visualización de historial de sesiones
- **RF-07** Registro de resumen cualitativo por sesión (profesional)
- **RF-08** Gestión de material de apoyo + consumo
- **RF-09** Asociación de competencias por sesión (si catálogo está definido)
- **RF-10** Control de acceso por rol

---

## 6.2 Requisitos no funcionales (resumen)

- Accesibilidad básica (teclado, foco visible, botones grandes)
- Seguridad por roles (autorización en backend)
- Protección y minimización de datos personales
- Arquitectura mantenible y modular
- Logs/eventos mínimos para depurar integración (trazabilidad)

---

# 7. Propuesta técnica (Arquitectura)

## 7.1 Arquitectura lógica

1. **Frontend Angular (TypeScript)**
   - SPA en navegador
   - Consume API REST del backend
   - Integra LiveAvatar dentro de la UI (embed y/o runtime/SDK en cliente, según mecanismo real)

2. **Backend FastAPI (Python)**
   - Orquestador y “fuente de verdad” del estado ELVIR
   - Lógica de negocio + control de acceso + persistencia
   - Coordina integración con LiveAvatar (crear/inicializar sesiones, guardar IDs/URLs/payloads)

3. **Servicio externo LiveAvatar**
   - Ejecuta la experiencia conversacional con avatar
   - Maneja sesión de entrevista y comportamiento del avatar (caja negra)

---

## 7.2 Flujo técnico de simulación (vigente)

1. Usuario inicia una nueva simulación desde ELVIR.
2. Frontend crea sesión en ELVIR: `POST /sessions` (asociada a `simulation_template_id`).
3. Backend registra `SESSIONS` con estado `EN_CURSO`.
4. Backend coordina el “start” con LiveAvatar (según método disponible):
   - Obtiene configuración (template → context/avatar/voice)
   - Solicita creación/arranque en LiveAvatar
   - Guarda `liveavatar_session_id` y/o `embed_url`/payload en la sesión (si aplica)
5. Frontend renderiza la experiencia LiveAvatar (iframe o runtime JS).
6. Al terminar, ELVIR cierra/actualiza sesión:
   - `POST /sessions/{id}/close`
   - Registra timestamps + estado final + métricas simples
7. Profesional puede registrar resumen cualitativo y sugerir material.

### Nota importante: selección de “caso”
En el diseño del MVP, **cargos/casos** existen como dominio ELVIR para construir UI y trazabilidad.
Si finalmente Teletón/LiveAvatar define que el “caso” se decide automáticamente (por evaluación), se ajusta el flujo así:

- El usuario elige **cargo** (o plantilla base)
- El “caso” puede quedar como:
  - `case_id` **nullable** en `SESSIONS`, o
  - `case_id` definido inicialmente y luego actualizado por el sistema
- Se agrega un evento/actualización: `CASE_ASSIGNED` o `session.case_id` actualizado post-evaluación

(esto se aterriza cuando se confirme el mecanismo real del proveedor)

---

# 8. Stack tecnológico

## 8.1 Frontend
- Angular (TypeScript)
- Angular Material (o equivalente)
- Guards por rol
- Servicios + interceptors (auth token)

## 8.2 Backend
- Python (FastAPI)
- SQLAlchemy
- Alembic
- JWT (o equivalente)
- Tests: Pytest

## 8.3 Base de datos
- PostgreSQL (desarrollo y producción)

---

# 9. Modelo de datos (MVP vigente)

Entidades principales (según `modelo_datos.md` + `diccionario_datos.md`):

- USERS
- YOUTH
- PROFESSIONALS
- ASSIGNMENTS
- JOB_ROLES
- CASES
- SIMULATION_TEMPLATES
- SESSIONS
- SESSION_EVENTS (recomendado)
- INTERVIEW_SUMMARIES
- COMPETENCIES
- COMPETENCY_LEVELS
- SESSION_COMPETENCIES
- SUPPORT_MATERIAL
- MATERIAL_VIEWS
- MATERIAL_SUGGESTIONS

## Decisión estructural clave

Separación entre:

- **SIMULATION_TEMPLATES** → configuración reusable (mapea a LiveAvatar)
- **SESSIONS** → ejecuciones reales (intentos, con estados y trazabilidad)

---

# 10. API del backend (resumen)

> Definición completa en: `docs/api/endpoints.md`

## Autenticación
- `POST /auth/login`
- `GET /auth/me`

## Jóvenes
- `GET /youths`
- `POST /youths`
- `GET /youths/{id}`
- `PUT /youths/{id}`
- `PATCH /youths/{id}/deactivate`

## Asignaciones
- `POST /assignments`
- `GET /professionals/{id}/assignments`
- `PATCH /assignments/{id}/end`

## Catálogos
- `GET /job-roles`
- `GET /cases`
- `GET /simulation-templates`

## Sesiones
- `POST /sessions`
- `GET /sessions?youth_id=`
- `GET /sessions/{id}`
- `POST /sessions/{id}/start`
- `POST /sessions/{id}/close`
- `GET /sessions/{id}/events`

## Resumen cualitativo
- `POST /sessions/{id}/summary`

## Competencias (si aplica MVP)
- `GET /competencies`
- `GET /competency-levels`
- `POST /sessions/{id}/competencies`
- `GET /sessions/{id}/competencies`

## Material
- `GET /support-material`
- `POST /support-material/suggest`
- `GET /youths/{id}/material-suggestions`
- `POST /support-material/{material_id}/view`

---

# 11. Criterios de aceptación (MVP)

## CU-01 Login
- Token válido
- Redirección correcta por rol

## CU-02 Simulación
- Sesión creada y persistida
- Integración visible con LiveAvatar dentro de ELVIR (iframe/runtime)
- Cierre de sesión con estado final + timestamps

## CU-04 / CU-05 Gestión profesional
- Tabla de jóvenes funcional
- CRUD operativo (crear/editar/desactivar)
- Asignación joven–profesional registrada

## CU-06 / CU-07 Seguimiento
- Historial visible por joven
- Resumen cualitativo registrable y consultable

## CU-08 Material
- Profesional sugiere material
- Joven visualiza material sugerido
- Registro de consumo (views)

---

# 12. Plan de pruebas

## Unitarias (backend)
- Auth (login ok/fail)
- CRUD youths
- Sesiones (create/start/close)
- Control de acceso por rol

## Integración
- Flujo completo joven: login → sesión → start → close → historial
- Flujo profesional: login → lista → crear/editar → ver perfil → sugerir material → resumen

## UI manual
- Navegación por rol
- Manejo de errores (401/403/404)
- Estados de carga (loading) y errores

---

# 13. Planificación (9 semanas – 360 horas)

## Fases (WBS resumida)

A. Diseño y arquitectura  
B. Backend  
C. Frontend  
D. Integración + validación + documentación  

## Hitos

- **H1:** Arquitectura + Modelo + API (docs cerrados)
- **H2:** Backend base funcional (auth + youths + sessions)
- **H3:** Frontend integrado (login + dashboards + flujos base)
- **H4:** Integración LiveAvatar validada end-to-end
- **H5:** Documentación final + demo funcional


---

# 14. Gestión de riesgos (resumen)

- **R1:** Cambios o falta de credenciales/API LiveAvatar  
  - Mitigación: adapter/capa integración + mocks + registro de eventos

- **R2:** Problemas de “inmersión” (embed/SDK/iframe)  
  - Mitigación: probar alternativas (embed vs runtime) + prototipo temprano

- **R3:** Expansión de alcance (“meter IA propia”, audio/video, etc.)  
  - Mitigación: fuera de alcance explícito + acuerdos por escrito

- **R4:** Datos sensibles / privacidad  
  - Mitigación: minimización + roles + no logs con PII + soft delete

---

# 15. Entregables

1. Repositorio (frontend + backend)
2. Documentación técnica (carpeta `/docs`):
   - Arquitectura
   - Flujos
   - Modelo de datos
   - Diccionario de datos
   - Endpoints
   - Addendum (decisiones)
3. Manual de usuario (joven/profesional)
4. Evidencia de demo (capturas / video / guía)
5. Resultados de pruebas (checklist + incidencias)

---

# 16. Trazabilidad

Los casos de uso se vinculan explícitamente a:

- Endpoints
- Entidades del modelo
- Pantallas implementadas
- Estados de sesión
- Resúmenes, sugerencias y (si aplica) competencias por sesión

La evolución técnica se documenta en `addendum_v1_1.md`.

## 17. Alineación con Documento Base: Supuestos y Dependencias del MVP

En esta sección se explicitan ciertos aspectos del documento base que, para el alcance de este MVP, dependen de servicios externos o se implementan en una versión simplificada.

El objetivo es dejar formalmente declarado qué se implementa directamente en ELVIR y qué depende del servicio externo (LiveAvatar), evitando ambigüedades respecto al alcance técnico.

---

### 17.1 Grabación de audio y/o video

El documento base menciona la grabación de audio y/o video de las simulaciones.

En el alcance actual del MVP:

- La plataforma registra metadatos estructurados de sesión (timestamps, estado, métricas simples).
- La ejecución audiovisual (voz y representación del avatar) depende completamente del servicio externo LiveAvatar.
- ELVIR no implementa almacenamiento propio de archivos de audio o video.
- No se persiste contenido audiovisual en la base de datos del backend.

Esta decisión responde a:

- Minimización de datos sensibles.
- Reducción de complejidad técnica en el MVP.
- Separación clara de responsabilidades entre ELVIR y el proveedor externo.

La incorporación de almacenamiento audiovisual propio queda considerada como posible extensión futura.

---

### 17.2 Resúmenes automáticos generados por IA

El requisito RF-09 establece la generación de resúmenes automáticos por IA.

En el MVP:

- ELVIR no implementa generación de resúmenes mediante modelos propios.
- Si el servicio externo (LiveAvatar u otro servicio IA asociado) retorna un resumen estructurado, este puede almacenarse asociado a la sesión.
- Independientemente de lo anterior, el sistema permite registrar un resumen cualitativo manual por parte del profesional mediante la entidad `INTERVIEW_SUMMARIES`.

Esto asegura cumplimiento funcional del requisito sin introducir desarrollo de IA interna.

No se desarrolla en esta etapa:

- Procesamiento adicional de texto.
- Evaluación automática avanzada.
- Modelos propios de análisis conversacional.

---

### 17.3 Métricas y curvas de seguimiento

El documento base menciona métricas de desempeño y curvas de seguimiento.

Para el MVP se define un conjunto mínimo de métricas:

- Duración de la sesión.
- Número de turnos (si es provisto por el servicio externo o calculable).
- Estado final de la sesión (`COMPLETADA`, `CANCELADA`, `ERROR`).
- Evaluación estructurada por competencias (si el profesional la registra).
- Frecuencia y fechas de uso.

La visualización inicial se implementa como:

- Historial cronológico de sesiones.
- Comparación básica entre intentos.
- Visualización estructurada por sesión individual.

No se implementan:

- Modelos estadísticos complejos.
- Análisis longitudinal automatizado.
- Algoritmos de progresión predictiva.

Esto mantiene el alcance del MVP alineado con una demo funcional robusta.

---

### 17.4 Dependencia del servicio externo (LiveAvatar)

La IA conversacional y el avatar se consumen como servicio externo tratado como caja negra.

ELVIR:

- No implementa modelos de IA propios.
- No modifica comportamiento interno del avatar.
- No controla directamente la lógica conversacional.
- Orquesta sesiones y persiste metadatos.

La arquitectura contempla una capa de adaptación en el backend para manejar:

- Identificadores técnicos (context_id, avatar_id, session_id).
- Posibles cambios en el contrato de integración.
- Gestión de errores externos.

Esto reduce el riesgo técnico identificado en etapas tempranas del proyecto.

---

### 17.5 Declaración explícita de alcance del MVP

El presente MVP prioriza:

- Flujo completo de simulación funcional end-to-end.
- Gestión estructurada de jóvenes.
- Registro formal de sesiones diferenciadas.
- Trazabilidad técnica mínima pero suficiente.
- Integración documentada con servicio externo.

Quedan fuera del alcance del MVP:

- Entrenamiento o ajuste de modelos de IA.
- Persistencia de audio/video.
- Evaluación automática avanzada.
- Dashboards analíticos complejos.

Estas funcionalidades se consideran evoluciones futuras sin alterar la arquitectura base definida.

---

# 18. Especificacion de pantallas (detalle MVP)

Esta seccion completa el nivel de detalle de UI, alineada con:
- Flujos de usuario (`/docs/flujos`)
- API (`/docs/api/endpoints.md`)
- Modelo de datos (`/docs/modelo-datos`)
- Mockups low-fi (`/docs/mockups/low-fidelity`), frontend Angular (`/frontend`)

## 18.1 Login

**Campos**
- Email
- Contrasena
- Seleccion de rol (Joven / Profesional)

**Acciones**
- Ingresar (POST `/auth/login`)
- Redireccion por rol tras `GET /auth/me`

**Estados**
- Loading (autenticando)
- Error credenciales
- Error servidor

**Reglas**
- Si `role` = JOVEN y `login_enabled` = false, bloquear login y mostrar mensaje.

---

## 18.2 Dashboard Joven

**Contenido**
- Resumen rapido: sesiones totales, ultima sesion, duracion media.
- Lista de ultimas sesiones con estado.
- Material sugerido y catalogo recomendado.

**Acciones**
- Iniciar simulacion (POST `/sessions`)
- Ver historial (GET `/sessions?youth_id=`)
- Ver material sugerido (GET `/youths/{id}/material-suggestions`)
- Registrar visualizacion (POST `/support-material/{material_id}/view`)

---

## 18.3 Simulacion (Joven / Supervisada)

**Contenido**
- Contexto de simulacion (cargo, caso, objetivo).
- Area de avatar (embed LiveAvatar).
- Barra de control (pausar, cancelar, finalizar).

**Acciones**
- Crear sesion (POST `/sessions`)
- Iniciar LiveAvatar (POST `/sessions/{id}/start`)
- Cerrar sesion (POST `/sessions/{id}/close`)

**Estados**
- EN_CURSO, COMPLETADA, CANCELADA, ERROR

**Notas**
- Si el caso no es seleccionado por el joven, resolver plantilla via
  `GET /simulation-templates/resolve?job_role_id=`.

---

## 18.4 Historial Joven

**Contenido**
- Tabla de sesiones: fecha, cargo, caso, duracion, estado.
- KPIs derivados: promedio duracion, sesiones completadas, incidentes.
- Resumen cualitativo (si existe).

**Acciones**
- Filtrar por estado o rango de fechas.
- Ver detalle de sesion (GET `/sessions/{id}`).

---

## 18.5 Material de apoyo (Joven)

**Contenido**
- Lista de sugerencias del profesional.
- Catalogo general con filtros (cargo/caso).

**Acciones**
- Marcar visto (POST `/support-material/{material_id}/view`)
- Filtrar por cargo/caso (GET `/support-material?job_role_id=&case_id=`)

---

## 18.6 Dashboard Profesional

**Contenido**
- KPIs: jovenes activos, sesiones semana, alertas tecnicas.
- Tabla principal de jovenes con estado, login, ultima sesion y alertas.
- Filtros: estado, ultima sesion, modo, login, asignacion.

**Acciones**
- Crear joven (POST `/youths`)
- Editar joven (PUT `/youths/{id}`)
- Desactivar joven (PATCH `/youths/{id}/deactivate`)
- Iniciar sesion supervisada (POST `/sessions`)

---

## 18.7 Perfil del Joven (Profesional)

**Contenido**
- Datos del joven + estado de asignacion.
- Historial de sesiones.
- Resumen cualitativo editable.
- Sugerir material.

**Acciones**
- Ver perfil (GET `/youths/{id}`)
- Ver sesiones (GET `/sessions?youth_id=`)
- Guardar resumen (POST `/sessions/{id}/summary`)
- Sugerir material (POST `/support-material/suggest`)

---

## 18.8 Crear / Editar Joven

**Campos**
- display_name
- identifier
- phone
- login_enabled
- general_notes

**Acciones**
- Crear (POST `/youths`)
- Editar (PUT `/youths/{id}`)
- Desactivar (PATCH `/youths/{id}/deactivate`)

---

# 19. Reglas de negocio y validaciones

- Solo PROFESIONAL puede crear/editar/desactivar jovenes.
- Un joven puede tener 0..N asignaciones, pero solo 1 activa a la vez.
- `login_enabled = false` impide login de joven; solo modo supervisado.
- Sesiones:
  - `EN_CURSO` solo puede pasar a `COMPLETADA`, `CANCELADA` o `ERROR`.
  - `ended_at` debe estar presente si estado != `EN_CURSO`.
- `mode = SUPERVISADA` requiere `professional_id` en sesion.
- `SIMULATION_TEMPLATES` debe existir y estar `is_active = true`.
- Sugerencias de material:
  - Solo profesional.
  - `session_id` opcional, `reason` recomendado.
- Material views:
  - Registrar `seen_at`.
  - Regla de unicidad segun definicion final (una vista vs historial).

---

# 20. Control de acceso por rol (RBAC)

- JOVEN:
  - Accede a simulacion, historial propio y material sugerido.
  - No ve lista de jovenes ni puede administrar perfiles.
- PROFESIONAL:
  - Gestiona jovenes asignados.
  - Registra resumenes cualitativos.
  - Sugiere material.
- ADMIN (opcional MVP):
  - Gestion de catalogos (cargos, casos, plantillas).

---

# 21. Trazabilidad UI - API - Datos

| Caso de uso | Pantalla(s) | Endpoints | Entidades |
|---|---|---|---|
| CU-01 Login | Login | POST /auth/login, GET /auth/me | USERS |
| CU-02 Simulacion | Simulacion | POST /sessions, POST /sessions/{id}/start, POST /sessions/{id}/close | SESSIONS, SIMULATION_TEMPLATES |
| CU-03 Material | Material joven | GET /support-material, POST /support-material/{id}/view | SUPPORT_MATERIAL, MATERIAL_VIEWS |
| CU-04 Lista jovenes | Dashboard profesional | GET /youths | YOUTH, ASSIGNMENTS |
| CU-05 Gestion joven | Crear/Editar | POST /youths, PUT /youths/{id}, PATCH /youths/{id}/deactivate | YOUTH |
| CU-06 Perfil joven | Perfil profesional | GET /youths/{id}, GET /sessions?youth_id= | YOUTH, SESSIONS |
| CU-07 Resumen | Perfil profesional | POST /sessions/{id}/summary | INTERVIEW_SUMMARIES |
| CU-08 Sugerir material | Perfil profesional | POST /support-material/suggest | MATERIAL_SUGGESTIONS |

---

# 22. Estados UI y manejo de errores

**Estados comunes**
- Loading
- Empty state (sin datos)
- Error 401/403 (sesion expirada o sin permisos)
- Error 404 (recurso inexistente)
- Error 500 (fallo servidor)

**Mensajes clave**
- Login invalido.
- No hay sesiones registradas.
- No hay material sugerido.
- Error al iniciar LiveAvatar (reintentar).

---

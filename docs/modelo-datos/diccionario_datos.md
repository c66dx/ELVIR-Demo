# Diccionario de datos – ELVIR (MVP)

Este documento describe el **diccionario de datos** del MVP de ELVIR, alineado con:
- Flujos (Joven / Profesional)
- Modelo ERD (`docs/modelo-datos/erd.svg`)
- Endpoints (`docs/api/endpoints.md`)
- Decisión de arquitectura **Opción A**: ELVIR mantiene el dominio (cargos/casos/plantillas) y LiveAvatar se consume como caja negra para ejecutar la entrevista.

> Convenciones:
> - `PK`: Primary Key
> - `FK`: Foreign Key
> - `NN`: Not Null
> - `UQ`: Unique
> - Timestamps en ISO 8601 (UTC recomendado)

---

## 1. USERS

**Propósito:** credenciales y rol del usuario del sistema (autenticación).  
**Notas:** No contiene datos clínicos/educativos; solo identidad de acceso y permisos.

**Roles y alcance:**
- **JOVEN:** simulaciones, historial, material sugerido.
- **PROFESIONAL:** crear/editar jóvenes asignados, sesiones supervisadas, resúmenes, sugerir material, subir material propio.
- **ADMIN:** crear profesionales, subir material general. *No gestiona catálogos* (cargos, casos, plantillas); eso es responsabilidad externa.

| Campo | Tipo | Restricciones | Descripción |
|------|------|---------------|-------------|
| id | int | PK, NN | Identificador interno |
| email | string | UQ, NN | Email de login |
| password_hash | string | NN | Hash de contraseña |
| role | enum | NN | `JOVEN` \| `PROFESIONAL` \| `ADMIN` |
| is_active | boolean | NN | Permite deshabilitar acceso sin borrar |
| created_at | datetime | NN | Creación |
| updated_at | datetime | NN | Última actualización |

---

## 2. YOUTH

**Propósito:** perfil funcional del joven (puede o no tener credenciales).  
**Notas clave:** `user_id` puede ser null para soporte de **acceso supervisado**.

| Campo | Tipo | Restricciones | Descripción |
|------|------|---------------|-------------|
| id | int | PK, NN | Identificador del joven |
| user_id | int | FK → USERS.id, nullable | Vincula credenciales si el joven tiene login |
| login_enabled | boolean | NN | Si el joven puede iniciar sesión por sí mismo |
| display_name | string | NN | Nombre para UI |
| identifier | string | nullable | RUT/ID institucional (si aplica) |
| phone | string | nullable | Contacto (opcional) |
| year_of_birth | int | nullable | Año de nacimiento |
| diagnosis | text | nullable | Diagnóstico (si aplica) |
| is_active | boolean | NN | Activo/inactivo (soft) |
| general_notes | text | nullable | Notas generales del proceso (no estructuradas) |
| profile_checklist | json/text | nullable | Array de slugs de competencias/características marcadas por el profesional (ej. `["comunicacion","trabajo_equipo"]`). Checklist predefinido de perfil postulante. |
| created_at | datetime | NN | Creación |
| updated_at | datetime | NN | Última actualización |

---

## 3. PROFESSIONALS

**Propósito:** perfil funcional del profesional (siempre autenticado).  
**Nota:** Los profesionales son creados por un usuario con rol ADMIN (no hay auto-registro). En el MVP se cargan vía seed; en producción, Admin usa `POST /professionals`.

| Campo | Tipo | Restricciones | Descripción |
|------|------|---------------|-------------|
| id | int | PK, NN | Identificador del profesional |
| user_id | int | FK → USERS.id, NN | Usuario autenticado asociado |
| display_name | string | NN | Nombre para UI |
| specialty | string | nullable | Especialidad (opcional) |
| institution | string | nullable | Institución (ej. Teletón) |
| is_active | boolean | NN | Activo/inactivo |
| created_at | datetime | NN | Creación |
| updated_at | datetime | NN | Última actualización |

---

## 4. YOUTH_INVITATIONS

**Propósito:** invitaciones para que el joven active su cuenta y defina su contraseña.  
**Flujo:** El profesional crea un joven con `login_enabled = true` e ingresa su email. El backend crea YOUTH (sin `user_id`) y una invitación. El profesional entrega el enlace al joven; el joven define su contraseña; el backend crea USERS, vincula YOUTH e invalida la invitación.

| Campo | Tipo | Restricciones | Descripción |
|------|------|---------------|-------------|
| id | int | PK, NN | Identificador |
| youth_id | int | FK → YOUTH.id, NN | Joven invitado |
| email | string | NN | Email del joven (para crear USERS al activar) |
| token | string | UQ, NN | Token único (UUID) para el enlace |
| expires_at | datetime | NN | Expiración (ej. 7 días) |
| used_at | datetime | nullable | Momento en que se usó (activación exitosa) |
| created_at | datetime | NN | Creación |

**Regla:** Una invitación es de un solo uso. Si `used_at` no es null, el token ya no es válido.

---

## 5. ASSIGNMENTS

**Propósito:** relación joven–profesional (historizable).  
**Por qué existe:** permite cambios de responsable sin modificar campos fijos en YOUTH/PROFESSIONALS.

| Campo | Tipo | Restricciones | Descripción |
|------|------|---------------|-------------|
| id | int | PK, NN | Identificador de asignación |
| youth_id | int | FK → YOUTH.id, NN | Joven asignado |
| professional_id | int | FK → PROFESSIONALS.id, NN | Profesional responsable |
| status | enum | NN | `ACTIVO` \| `INACTIVO` |
| assigned_at | datetime | NN | Inicio de la asignación |
| ended_at | datetime | nullable | Fin (si aplica) |

**Regla sugerida:** un joven puede tener 0..N asignaciones; normalmente 1 activa.

**Regla de asignación:** Cuando un profesional crea un joven (`POST /youths`), se crea automáticamente una asignación ACTIVA entre ese joven y ese profesional. No existe flujo de Admin asignando jóvenes a profesionales.

**Regla de negocio:** A nivel de aplicación, se recomienda que un joven tenga como máximo una asignación ACTIVA a la vez. Si se requiere múltiples profesionales activos simultáneamente, se puede permitir; en ese caso, documentar la regla de negocio explícitamente.

---

## 6. JOB_ROLES

**Propósito:** catálogo de cargos/puestos (dominio ELVIR).  
**Nota:** no depende de LiveAvatar; LiveAvatar solo ejecuta el contexto mapeado.  
**Integración Context Dinámico:** los campos `description`, `objetivo` y `competencias` permiten construir el prompt dinámico para LiveAvatar (PATCH al contexto antes de cada sesión).

| Campo | Tipo | Restricciones | Descripción |
|------|------|---------------|-------------|
| id | int | PK, NN | Identificador |
| slug | string | UQ, NN | Identificador estable (`retail_vendedor`) |
| name | string | NN | Nombre visible |
| description | text | nullable | Descripción del cargo (para prompt) |
| objetivo | text | nullable | Objetivo del rol (para prompt) |
| competencias | text/json | nullable | Competencias clave, array o texto (para prompt) |
| is_active | boolean | NN | Habilitado para selección |

---

## 7. CASES

**Propósito:** catálogo de casos / dificultad (dominio ELVIR).  
**Integración Context Dinámico:** el campo `prompt_instructions` permite construir el prompt dinámico con las instrucciones de intervención para cada caso.

| Campo | Tipo | Restricciones | Descripción |
|------|------|---------------|-------------|
| id | int | PK, NN | Identificador |
| slug | string | UQ, NN | Identificador estable (`alta`, `media`, etc.) |
| name | string | NN | Nombre visible |
| difficulty | enum | NN | `NORMAL` \| `BAJA` \| `MEDIA` \| `ALTA` |
| prompt_instructions | text | nullable | Instrucciones de intervención para el prompt (regulación emocional, presentación, expectativas) |
| is_active | boolean | NN | Habilitado para selección |

---

## 8. SIMULATION_TEMPLATES

**Propósito:** **plantilla reusable** (cargo × caso) con el mapeo hacia LiveAvatar.  
**Clave:** separa *configuración* de *ejecución real* (SESSIONS).

**Integración Context Dinámico:** se usa un único `liveavatar_context_id` compartido. El backend construye el prompt desde JOB_ROLES + CASES, hace PATCH al contexto en LiveAvatar, y luego crea la sesión. **Implementación actual:** 16 plantillas (4 cargos × 4 casos) en seed. Cargos: Operario, Atención de Público, Administrativo, Técnico-Profesional. Casos: Normal, Baja, Media, Alta.

| Campo | Tipo | Restricciones | Descripción |
|------|------|---------------|-------------|
| id | int | PK, NN | Identificador |
| job_role_id | int | FK → JOB_ROLES.id, NN | Cargo asociado |
| case_id | int | FK → CASES.id, NN | Caso asociado |
| liveavatar_context_id | string | NN | Context ID en LiveAvatar (único si Context Dinámico; o uno por plantilla si 16 contexts) |
| liveavatar_avatar_id | string | NN | ID de avatar en LiveAvatar (definido por id en código) |
| liveavatar_voice_id | string | NN | ID de voz en LiveAvatar (definido por id en código) |
| is_active | boolean | NN | Plantilla activa |
| created_at | datetime | NN | Creación |
| updated_at | datetime | NN | Última actualización |

**Regla sugerida:** UQ (job_role_id, case_id) para evitar duplicados.

---

## 9. SESSIONS

**Propósito:** **cada intento real** del joven (autogestionado o supervisado).  

| Campo | Tipo | Restricciones | Descripción |
|------|------|---------------|-------------|
| id | int | PK, NN | Identificador |
| youth_id | int | FK → YOUTH.id, NN | Joven |
| professional_id | int | FK → PROFESSIONALS.id, nullable | Profesional supervisor (si aplica) |
| simulation_template_id | int | FK → SIMULATION_TEMPLATES.id, NN | Plantilla utilizada |
| mode | enum | NN | `AUTOGESTIONADA` \| `SUPERVISADA` |
| liveavatar_session_id | string | nullable | Session ID generado por LiveAvatar |
| started_at | datetime | NN | Inicio |
| ended_at | datetime | nullable | Fin |
| status | enum | NN | `EN_CURSO` \| `COMPLETADA` \| `CANCELADA` \| `ERROR` |
| duration_seconds | int | nullable | Duración (derivable, pero útil) |
| metrics | json | nullable | Métricas simples (turnos, etc.) |
| created_at | datetime | NN | Creación |
| updated_at | datetime | NN | Última actualización |

**Reglas sugeridas:**
- `ended_at` NN solo si status ∈ {COMPLETADA, CANCELADA, ERROR}.
- `professional_id` NN si mode = SUPERVISADA.

---

## 10. SESSION_EVENTS

**Propósito:** trazabilidad ligera de eventos relevantes por sesión (debug + auditoría MVP).  
**Clave:** ayuda a monitorear el riesgo de integración con LiveAvatar.

| Campo | Tipo | Restricciones | Descripción |
|------|------|---------------|-------------|
| id | int | PK, NN | Identificador |
| session_id | int | FK → SESSIONS.id, NN | Sesión |
| event_type | enum/string | NN | Ej: `CREATED`, `LIVEAVATAR_STARTED`, `ENDED`, `ERROR` |
| occurred_at | datetime | NN | Momento del evento |
| payload | json/text | nullable | Datos asociados (id externos, mensaje error, etc.) |

---

## 11. INTERVIEW_SUMMARIES

**Propósito:** resumen cualitativo redactado por el profesional para una sesión.  
**Regla:** 0..1 resumen por sesión (en MVP).

| Campo | Tipo | Restricciones | Descripción |
|------|------|---------------|-------------|
| id | int | PK, NN | Identificador |
| session_id | int | FK → SESSIONS.id, NN | Sesión resumida |
| professional_id | int | FK → PROFESSIONALS.id, NN | Autor |
| summary_text | text | NN | Texto cualitativo |
| competency_tags | json | nullable | Tags simples (MVP) |
| created_at | datetime | NN | Creación |
| updated_at | datetime | NN | Última actualización |

**Nota:** aunque exista evaluación estructurada (SESSION_COMPETENCIES), `competency_tags` es útil como resumen rápido.

**Nota sobre resúmenes automáticos (LiveAvatar):** Si LiveAvatar entrega resúmenes automáticos en el futuro, se puede considerar: hacer `professional_id` nullable y añadir campo `source` (enum: `PROFESSIONAL` | `LIVEAVATAR`), o mantener `professional_id` NN y almacenar resúmenes de LiveAvatar en una extensión del modelo. En el MVP se mantiene `professional_id` NN (solo resúmenes manuales del profesional).

---

## 12. SUPPORT_MATERIAL

**Propósito:** catálogo de recursos (videos, PDFs, links).  
**Filtros opcionales:** por cargo y/o caso.

**Quién sube material:**
- **ADMIN:** material general (visible para todos los profesionales y jóvenes).
- **PROFESIONAL:** material propio (visible solo para ese profesional y sus jóvenes asignados).
- El campo `created_by` (professional_id nullable) indica el propietario: null = Admin; valor = Profesional.

| Campo | Tipo | Restricciones | Descripción |
|------|------|---------------|-------------|
| id | int | PK, NN | Identificador |
| title | string | NN | Título |
| description | text | nullable | Descripción |
| type | enum | NN | `VIDEO` \| `PDF` \| `LINK` |
| url | string | NN | URL o ruta |
| job_role_id | int | FK → JOB_ROLES.id, nullable | Filtro por cargo |
| case_id | int | FK → CASES.id, nullable | Filtro por caso |
| created_by | int | FK → PROFESSIONALS.id, nullable | null = Admin (material general); valor = Profesional (material propio) |
| active | boolean | NN | Disponible |
| created_at | datetime | NN | Creación |
| updated_at | datetime | NN | Última actualización |

---

## 13. MATERIAL_VIEWS

**Propósito:** registrar consumo efectivo de material por parte del joven.

| Campo | Tipo | Restricciones | Descripción |
|------|------|---------------|-------------|
| id | int | PK, NN | Identificador |
| youth_id | int | FK → YOUTH.id, NN | Joven |
| material_id | int | FK → SUPPORT_MATERIAL.id, NN | Recurso |
| seen_at | datetime | NN | Timestamp visualización |

**Regla:** Para el MVP se permite múltiples registros por (youth_id, material_id) para mantener historial de visualizaciones. Si en el futuro solo interesa "visto alguna vez", se puede añadir UQ (youth_id, material_id) o filtrar por vista más reciente.

---

## 14. MATERIAL_SUGGESTIONS

**Propósito:** sugerencias de material hechas por profesional (opcionalmente asociadas a una sesión).

| Campo | Tipo | Restricciones | Descripción |
|------|------|---------------|-------------|
| id | int | PK, NN | Identificador |
| youth_id | int | FK → YOUTH.id, NN | Joven |
| material_id | int | FK → SUPPORT_MATERIAL.id, NN | Recurso sugerido |
| professional_id | int | FK → PROFESSIONALS.id, NN | Quien sugiere |
| session_id | int | FK → SESSIONS.id, nullable | Sesión relacionada |
| reason | text | nullable | Motivo de sugerencia |
| suggested_at | datetime | NN | Timestamp sugerencia |

---

## 15. COMPETENCIES

**Propósito:** catálogo configurable de competencias (desacoplado del joven).  
**Nota:** evita campos fijos por joven.

| Campo | Tipo | Restricciones | Descripción |
|------|------|---------------|-------------|
| id | int | PK, NN | Identificador |
| slug | string | UQ, NN | Identificador estable (`comunicacion`) |
| name | string | NN | Nombre visible |
| description | text | nullable | Descripción |
| is_active | boolean | NN | Activo |

---

## 16. COMPETENCY_LEVELS

**Propósito:** catálogo de niveles (bajo/medio/alto u otros).

| Campo | Tipo | Restricciones | Descripción |
|------|------|---------------|-------------|
| id | int | PK, NN | Identificador |
| slug | string | UQ, NN | `BAJO` \| `MEDIO` \| `ALTO` |
| label | string | NN | Etiqueta visible |
| sort_order | int | NN | Orden |

---

## 17. SESSION_COMPETENCIES

**Propósito:** evaluación estructurada de competencias por sesión.  
**Nota:** permite historial por sesión y posteriormente derivar un “estado actual” del joven sin campos fijos.

| Campo | Tipo | Restricciones | Descripción |
|------|------|---------------|-------------|
| id | int | PK, NN | Identificador |
| session_id | int | FK → SESSIONS.id, NN | Sesión evaluada |
| competency_id | int | FK → COMPETENCIES.id, NN | Competencia |
| level_id | int | FK → COMPETENCY_LEVELS.id, NN | Nivel asignado |
| comment | text | nullable | Observación |
| created_at | datetime | NN | Timestamp |

**Regla sugerida:** UQ (session_id, competency_id) para una evaluación por competencia en una sesión.

---

## 18. Relaciones clave (resumen)

- USERS 1–0/1 YOUTH (login opcional del joven)
- YOUTH 0–N YOUTH_INVITATIONS (invitaciones pendientes para activar cuenta)
- USERS 1–1 PROFESSIONALS
- YOUTH 1–N SESSIONS
- SIMULATION_TEMPLATES 1–N SESSIONS
- SESSIONS 1–N SESSION_EVENTS
- SESSIONS 0–1 INTERVIEW_SUMMARIES
- SESSIONS 0–N SESSION_COMPETENCIES
- COMPETENCIES 1–N SESSION_COMPETENCIES
- COMPETENCY_LEVELS 1–N SESSION_COMPETENCIES
- SUPPORT_MATERIAL 1–N MATERIAL_SUGGESTIONS / MATERIAL_VIEWS
- PROFESSIONALS 0–N SUPPORT_MATERIAL (created_by)
- YOUTH 1–N MATERIAL_SUGGESTIONS / MATERIAL_VIEWS
- PROFESSIONALS 1–N MATERIAL_SUGGESTIONS
- YOUTH N–N PROFESSIONALS (vía ASSIGNMENTS)

---

## 19. Campos mínimos vs extensiones

**Mínimos MVP (prioridad alta):**
- USERS, YOUTH, YOUTH_INVITATIONS, PROFESSIONALS, ASSIGNMENTS
- JOB_ROLES, CASES, SIMULATION_TEMPLATES
- SESSIONS (con status + timestamps + liveavatar_session_id)
- SUPPORT_MATERIAL, MATERIAL_SUGGESTIONS, MATERIAL_VIEWS
- INTERVIEW_SUMMARIES (al menos summary_text)

**Extensión MVP+:**
- SESSION_EVENTS (si quieren trazabilidad fina)
- COMPETENCIES / LEVELS / SESSION_COMPETENCIES (si ya definen catálogo final)
- Campos adicionales en `metrics` (si LiveAvatar entrega datos)
- Rol ADMIN: crear profesionales, crear material. Campo `created_by` en SUPPORT_MATERIAL.

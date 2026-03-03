# API REST – Endpoints del backend ELVIR (v1.2, opción A)

Este documento describe los endpoints principales de la API REST del backend de la plataforma ELVIR, alineados con el modelo de datos y los flujos definidos para el MVP.

**Opción A (decisión de arquitectura):** LiveAvatar se consume como caja negra para ejecutar la entrevista (avatar + sesión). ELVIR mantiene un **catálogo de dominio** (cargos/casos) y el **mapeo** hacia LiveAvatar (context/avatar/voice) mediante `SIMULATION_TEMPLATES`, evitando hardcodear valores en el frontend y manteniendo trazabilidad.

**Nota sobre el demo inicial:** los 16 prompts (4 cargos × 4 casos) están definidos en LiveAvatar como *Contexts*. En ELVIR, esas combinaciones se representan como dominio y se mapean a `liveavatar_context_id` vía `SIMULATION_TEMPLATES`.


---

## 1. Convenciones generales

- Base URL (ejemplo):

  `/api/v1`

- Autenticación basada en token (JWT o equivalente).
- Rutas protegidas requieren header:

  `Authorization: Bearer <token>`

- Roles:
  - `JOVEN` – simulaciones, historial, material sugerido
  - `PROFESIONAL` – jóvenes asignados, sesiones, resúmenes, sugerir material, subir material propio
  - `ADMIN` – crear profesionales, subir material general (no gestiona catálogos)

---

## 2. Autenticación y usuarios

### 2.1 Login

**POST** `/auth/login`

Autentica a un usuario y retorna token + rol. Al hacer login, se crea un registro en `platform_sessions` (entrada a la plataforma) para métricas.

#### Request

~~~json
{
  "email": "usuario@ejemplo.cl",
  "password": "password"
}
~~~

#### Response

~~~json
{
  "access_token": "jwt_token",
  "role": "PROFESIONAL",
  "user_id": 12
}
~~~

---

### 2.2 Logout

**POST** `/auth/logout`

Registra el cierre de sesión en la plataforma (actualiza `ended_at` en `platform_sessions`). Requiere autenticación. El frontend lo llama antes de limpiar el token local.

#### Response

~~~json
{
  "ok": true
}
~~~

---

### 2.3 Usuario autenticado

**GET** `/auth/me`

Obtiene la información del usuario autenticado.

#### Response

~~~json
{
  "user_id": 12,
  "role": "PROFESIONAL",
  "email": "usuario@ejemplo.cl"
}
~~~

---

### 2.4 Validar token de activación (opcional)

**GET** `/auth/activate/validate?token=xxx`

Valida si un token de invitación es válido (existe, no expirado, no usado). El frontend lo usa para mostrar el formulario de activación o un mensaje de error.

#### Response (válido)

~~~json
{
  "valid": true,
  "email": "maria.lopez@ejemplo.cl",
  "display_name": "María López",
  "is_change_email": false
}
~~~

`is_change_email`: `true` cuando el joven ya tiene cuenta (cambio de correo); en ese caso el formulario pide contraseña actual para confirmar.

#### Response (inválido)

~~~json
{
  "valid": false,
  "error": "TOKEN_EXPIRED"
}
~~~

`error` puede ser: `TOKEN_EXPIRED`, `TOKEN_USED`, `TOKEN_NOT_FOUND`.

---

### 2.5 Activar cuenta (joven)

**POST** `/auth/activate`

- **Primera activación:** El joven define su contraseña. Crea el usuario (USERS), lo vincula al YOUTH e invalida la invitación.
- **Cambio de correo:** El joven confirma con su contraseña actual; opcionalmente puede definir una nueva. Actualiza email y/o contraseña en el usuario existente.

#### Request (primera activación)

~~~json
{
  "token": "abc123-def456-...",
  "password": "contraseña_segura"
}
~~~

#### Request (cambio de correo)

~~~json
{
  "token": "abc123-def456-...",
  "current_password": "contraseña_actual",
  "password": "nueva_contraseña_opcional"
}
~~~

#### Response

~~~json
{
  "success": true,
  "message": "Cuenta activada. Ya puedes iniciar sesión."
}
~~~

Tras la activación, el joven puede hacer login con su email y la contraseña definida.

---

### 2.6 Cambiar contraseña

**POST** `/auth/change-password`

Permite al usuario autenticado (JOVEN, PROFESIONAL o ADMIN) cambiar su contraseña.  
Requiere enviar la contraseña actual y la nueva contraseña.

#### Request

~~~json
{
  "current_password": "mi_contraseña_actual",
  "new_password": "mi_nueva_contraseña_segura"
}
~~~

- `new_password` debe tener al menos 6 caracteres.

#### Response

~~~json
{
  "success": true,
  "message": "Contraseña actualizada correctamente"
}
~~~

#### Errores

- `400 Bad Request`  
  - `"detail": "La nueva contraseña debe tener al menos 6 caracteres"`  
  - `"detail": "Contraseña actual incorrecta"`
- `401 Unauthorized` si no hay JWT válido.

---

## 2.5 Profesionales (gestión por Admin)

> Solo usuarios con rol ADMIN pueden crear profesionales. En el MVP los profesionales se cargan vía seed; en producción, Admin usa estos endpoints.

### 2.5.1 Listar profesionales

**GET** `/professionals`

Lista todos los profesionales activos. Requiere rol ADMIN.

#### Response

~~~json
[
  {
    "id": 3,
    "user_id": 15,
    "display_name": "María González",
    "specialty": "Terapia ocupacional",
    "institution": "Teletón Santiago",
    "is_active": true
  }
]
~~~

---

### 2.5.2 Crear profesional

**POST** `/professionals`

Crea un nuevo profesional con credenciales. Requiere rol ADMIN.

#### Request

~~~json
{
  "email": "nuevo.prof@institucion.cl",
  "password": "contraseña_inicial",
  "display_name": "María González",
  "specialty": "Terapia ocupacional",
  "institution": "Teletón Santiago"
}
~~~

#### Response

~~~json
{
  "id": 3,
  "user_id": 15,
  "display_name": "María González",
  "specialty": "Terapia ocupacional",
  "institution": "Teletón Santiago",
  "is_active": true
}
~~~

---

### 2.5.3 Actualizar profesional

**PUT** `/professionals/{professional_id}`

Actualiza los datos de perfil de un profesional (no modifica email ni contraseña). Requiere rol ADMIN.

#### Request

~~~json
{
  "display_name": "María González (actualizado)",
  "specialty": "Terapia ocupacional",
  "institution": "Teletón Valparaíso",
  "is_active": true
}
~~~

- `display_name`: obligatorio.
- `specialty`, `institution`, `is_active`: opcionales (si se omiten, conservan el valor actual).

#### Response

~~~json
{
  "id": 3,
  "user_id": 15,
  "display_name": "María González (actualizado)",
  "specialty": "Terapia ocupacional",
  "institution": "Teletón Valparaíso",
  "is_active": true
}
~~~

---

## 3. Jóvenes (gestión por profesional)

> En el MVP el profesional administra jóvenes (crear/ver/editar/desactivar) y puede habilitar o no el login del joven (`login_enabled`).  
> La relación joven–profesional se modela con asignaciones (ASSIGNMENTS).

### 3.1 Listar jóvenes (tabla principal profesional)

**GET** `/youths`

Retorna lista de jóvenes **asignados al profesional autenticado** (vía ASSIGNMENTS con status ACTIVO), con campos útiles para tabla: estado, último intento, etc.

**Query params (opcionales):**

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `search` | string | Buscar por nombre o identificador |
| `is_active` | boolean | Filtrar por estado (true/false) |
| `login_enabled` | boolean | Filtrar por login habilitado (true/false) |

#### Response (ejemplo)

~~~json
[
  {
    "id": 5,
    "display_name": "María García",
    "identifier": "ID001",
    "login_enabled": true,
    "is_active": true,
    "status_label": "Con sesiones",
    "last_session": {
      "id": 42,
      "started_at": "2026-02-10T15:40:00Z",
      "status": "COMPLETADA"
    }
  }
]
~~~

---

### 3.2 Crear joven

**POST** `/youths`

Si `login_enabled = true`, el campo `email` es **obligatorio**. El backend crea el YOUTH sin credenciales, genera una invitación y devuelve `activation_url` para que el profesional entregue al joven. Si `login_enabled = false`, no se requiere email.

> **Nota:** El `identifier` (JOV-001, JOV-002, …) lo genera el sistema automáticamente; no se envía en el request.

#### Request (login deshabilitado)

~~~json
{
  "display_name": "Juan Pérez",
  "phone": "+56912345678",
  "login_enabled": false,
  "general_notes": "Observaciones generales del proceso (opcional)."
}
~~~

#### Request (login habilitado)

~~~json
{
  "display_name": "María López",
  "phone": "+56987654321",
  "login_enabled": true,
  "email": "maria.lopez@ejemplo.cl",
  "general_notes": "Opcional."
}
~~~

#### Response (login deshabilitado)

~~~json
{
  "id": 6,
  "display_name": "Juan Pérez",
  "identifier": "ID002",
  "login_enabled": false,
  "is_active": true
}
~~~

#### Response (login habilitado)

~~~json
{
  "id": 7,
  "display_name": "María López",
  "identifier": "ID003",
  "login_enabled": true,
  "is_active": true,
  "activation_url": "https://elvir.app/activar?token=abc123-def456-..."
}
~~~

El profesional debe entregar `activation_url` al joven (en persona, WhatsApp, etc.). El joven abre el enlace, define su contraseña y activa su cuenta.

---

### 3.3 Obtener perfil de joven

**GET** `/youths/{youth_id}`

~~~json
{
  "id": 5,
  "display_name": "María García",
  "identifier": "ID001",
  "phone": "+56911111111",
  "login_enabled": true,
  "is_active": true,
  "general_notes": "Notas generales del proceso (opcional).",
  "profile_checklist": ["comunicacion", "trabajo_equipo", "puntualidad"]
}
~~~

`profile_checklist`: array de slugs del checklist de perfil postulante (competencias/características marcadas por el profesional). Predefinido en el frontend.

---

### 3.4 Editar joven

**PUT** `/youths/{youth_id}`

Si se habilita `login_enabled` para un joven que aún no tiene cuenta activa (`user_id` null), incluir `email` para generar una invitación. La respuesta incluirá `activation_url` en ese caso.

~~~json
{
  "display_name": "María García",
  "identifier": "ID001",
  "phone": "+56911111111",
  "login_enabled": true,
  "email": "maria.garcia@ejemplo.cl",
  "general_notes": "Notas actualizadas (opcional)."
}
~~~

#### Response (cuando se genera invitación)

~~~json
{
  "id": 5,
  "display_name": "María García",
  "login_enabled": true,
  "is_active": true,
  "activation_url": "https://elvir.app/activar?token=abc123-..."
}
~~~

---

### 3.5 Desactivar joven (soft delete)

**PATCH** `/youths/{youth_id}/deactivate`

~~~json
{
  "id": 5,
  "is_active": false
}
~~~

---

### 3.6 Cambiar email del joven

**POST** `/youths/{youth_id}/change-email`

Cambia el email del joven y genera un nuevo enlace de activación. Requiere que el joven tenga `login_enabled`. Si el joven ya tiene cuenta activa, actualiza el email en USERS; si no, crea una nueva invitación. El profesional entrega el nuevo enlace al joven.

#### Request

~~~json
{
  "new_email": "nuevo@correo.cl"
}
~~~

#### Response

~~~json
{
  "id": 5,
  "display_name": "María García",
  "email": "nuevo@correo.cl",
  "activation_url": "https://elvir.app/activar?token=xyz789-..."
}
~~~

---

### 3.7 Accesos a la plataforma (entradas/salidas)

**GET** `/youths/{youth_id}/platform-sessions`

Lista los registros de login/logout del joven (cuándo entró y salió de la plataforma). Solo aplica si el joven tiene `user_id` (cuenta activada). PROFESIONAL: jóvenes asignados. JOVEN: solo su propio historial. ADMIN: cualquier joven.

#### Response

~~~json
[
  {
    "id": 1,
    "user_id": 5,
    "started_at": "2026-02-26T10:00:00Z",
    "ended_at": "2026-02-26T11:30:00Z"
  },
  {
    "id": 2,
    "user_id": 5,
    "started_at": "2026-02-26T14:00:00Z",
    "ended_at": null
  }
]
~~~

`ended_at` null indica sesión activa (aún no ha cerrado sesión).

---

## 4. Asignaciones (joven–profesional)

### 4.1 Listar asignaciones de un profesional

**GET** `/professionals/{professional_id}/assignments`

~~~json
[
  {
    "id": 10,
    "youth_id": 5,
    "professional_id": 2,
    "status": "ACTIVO",
    "assigned_at": "2026-02-01T10:00:00Z",
    "ended_at": null
  }
]
~~~

---

### 4.2 Asignar joven a profesional

**POST** `/assignments`

~~~json
{
  "youth_id": 5,
  "professional_id": 2
}
~~~

---

### 4.3 Finalizar asignación

**PATCH** `/assignments/{assignment_id}/end`

~~~json
{
  "status": "INACTIVO"
}
~~~

---

## 5. Catálogos (dominio ELVIR)

> Estos catálogos representan el dominio (cargos/casos) y permiten construir UI sin hardcodear valores.  
> **Importante:** Aunque el demo original define los contexts en LiveAvatar, en ELVIR podemos mantener este catálogo para trazabilidad y para no depender de valores “pegados” en el frontend.

### 5.1 Listar cargos/puestos

**GET** `/job-roles`

Los campos `description`, `objetivo` y `competencias` se usan para construir el prompt dinámico (Context Dinámico / LiveAvatar).

~~~json
[
  {
    "id": 1,
    "slug": "retail_vendedor",
    "name": "Vendedor(a) Retail",
    "description": "Atención al cliente en tienda, venta de productos, manejo de caja.",
    "objetivo": "Simular entrevista para puesto de vendedor en retail.",
    "competencias": ["comunicación", "atención al cliente", "ventas", "trabajo en equipo"],
    "is_active": true
  },
  {
    "id": 2,
    "slug": "recepcionista",
    "name": "Recepcionista",
    "description": "Recepción de visitas, manejo de llamadas, agenda.",
    "objetivo": "Evaluar habilidades para puesto de recepcionista.",
    "competencias": ["comunicación", "organización", "atención al público"],
    "is_active": true
  }
]
~~~

---

### 5.2 Listar casos / niveles de dificultad (catálogo)

**GET** `/cases`

El campo `prompt_instructions` contiene las instrucciones de intervención para el prompt dinámico (Context Dinámico / LiveAvatar).

~~~json
[
  {
    "id": 1,
    "slug": "normal",
    "name": "Entrevista normal",
    "difficulty": "NORMAL",
    "prompt_instructions": "Entrevista estándar. Mantener tono profesional y empático. Preguntas típicas de selección.",
    "is_active": true
  },
  {
    "id": 2,
    "slug": "baja",
    "name": "Dificultad baja (empático)",
    "difficulty": "BAJA",
    "prompt_instructions": "Entrevistadora muy empática y acogedora. Dar más tiempo para responder. Refuerzo positivo frecuente.",
    "is_active": true
  },
  {
    "id": 3,
    "slug": "media",
    "name": "Dificultad media (guiada)",
    "difficulty": "MEDIA",
    "prompt_instructions": "Nivel medio de apoyo. Guiar con preguntas abiertas. Ofrecer ejemplos si el candidato duda.",
    "is_active": true
  },
  {
    "id": 4,
    "slug": "alta",
    "name": "Dificultad alta (poco empático)",
    "difficulty": "ALTA",
    "prompt_instructions": "Entrevistadora más directa y con menos paciencia. Preguntas más desafiantes. Menos refuerzo.",
    "is_active": true
  }
]
~~~


---

## 6. Plantillas de simulación (SIMULATION_TEMPLATES)

`SIMULATION_TEMPLATES` representa el **mapeo** entre dominio ELVIR y LiveAvatar:

- dominio: cargo × caso
- LiveAvatar: `context_id`, `avatar_id`, `voice_id`

### 6.1 Listar plantillas disponibles

**GET** `/simulation-templates`

Filtros opcionales:
- `job_role_id`
- `case_id`

Ejemplos:
- `/simulation-templates?job_role_id=1`
- `/simulation-templates?case_id=4`

#### Response (ejemplo)

~~~json
[
  {
    "id": 3,
    "job_role": { "id": 1, "slug": "retail_vendedor", "name": "Vendedor(a) Retail" },
    "case": { "id": 2, "slug": "baja", "difficulty": "BAJA", "name": "Dificultad baja (empático)" },
    "liveavatar_context_id": "ctx_abc123",
    "liveavatar_avatar_id": "avt_01",
    "liveavatar_voice_id": "voice_01",
    "is_active": true
  }
]
~~~

---

### 6.2 Resolver plantilla para iniciar simulación (modo “Joven elige solo cargo”)

**GET** `/simulation-templates/resolve?job_role_id=1`

Retorna una plantilla lista para usar cuando el usuario **no selecciona caso**.  
La regla de resolución puede ser simple en MVP: `normal` por defecto, o “última recomendación” si existe.

#### Response (ejemplo)

~~~json
{
  "id": 1,
  "job_role": { "id": 1, "slug": "retail_vendedor", "name": "Vendedor(a) Retail" },
  "case": { "id": 1, "slug": "normal", "difficulty": "NORMAL", "name": "Entrevista normal" },
  "liveavatar_context_id": "ctx_default_001",
  "liveavatar_avatar_id": "avt_01",
  "liveavatar_voice_id": "voice_01",
  "is_active": true,
  "resolution_reason": "DEFAULT_CASE"
}
~~~

---

### 6.3 Obtener detalle de una plantilla

**GET** `/simulation-templates/{template_id}`

---

### 6.4 (Opcional MVP) Administrar plantillas

- **POST** `/simulation-templates`
- **PUT** `/simulation-templates/{template_id}`
- **PATCH** `/simulation-templates/{template_id}/deactivate`

---

## 7. Sesiones (SESSIONS – ejecuciones reales)

### 7.1 Crear sesión (inicio de intento)

**POST** `/sessions`

Crea una sesión asociada a un joven y una plantilla.  
El `mode` define si es autogestionada o supervisada.

#### Request

~~~json
{
  "youth_id": 5,
  "simulation_template_id": 3,
  "mode": "AUTOGESTIONADA"
}
~~~

#### Response (ejemplo)

~~~json
{
  "id": 42,
  "youth_id": 5,
  "professional_id": null,
  "simulation_template_id": 3,
  "mode": "AUTOGESTIONADA",
  "status": "EN_CURSO",
  "started_at": "2026-02-10T15:40:00Z"
}
~~~

---

### 7.2 Listar sesiones (historial)

**GET** `/sessions?youth_id=5`

~~~json
[
  {
    "id": 42,
    "simulation_template_id": 3,
    "mode": "AUTOGESTIONADA",
    "status": "COMPLETADA",
    "started_at": "2026-02-10T15:40:00Z",
    "ended_at": "2026-02-10T15:55:00Z",
    "duration_seconds": 900
  }
]
~~~

---

### 7.3 Obtener detalle de sesión

**GET** `/sessions/{session_id}`

~~~json
{
  "id": 42,
  "youth_id": 5,
  "professional_id": null,
  "simulation_template_id": 3,
  "mode": "AUTOGESTIONADA",
  "status": "EN_CURSO",
  "started_at": "2026-02-10T15:40:00Z",
  "ended_at": null,
  "duration_seconds": null,
  "liveavatar_session_id": null,
  "metrics": {
    "turn_count": 0
  }
}
~~~

---

### 7.4 Orquestación: iniciar sesión en LiveAvatar

**POST** `/sessions/{session_id}/start`

Inicia la experiencia con LiveAvatar según la plantilla. El backend obtiene el prompt (contenido de Catalina; archivos o catálogo), hace PATCH al contexto en LiveAvatar, crea la sesión y devuelve los datos para que el frontend conecte (LiveKit: `livekit_url`, `access_token`; o embed si aplica). Ver `docs/integracion-liveavatar.md`.

#### Response (ejemplo)

~~~json
{
  "session_id": 42,
  "liveavatar_session_id": "lav_sess_987",
  "embed": {
    "type": "iframe",
    "url": "https://liveavatar.example/embed/lav_sess_987"
  }
}
~~~

---

### 7.5 Cerrar sesión

**POST** `/sessions/{session_id}/close`

Cierra la sesión y registra estado final + métricas. Si la sesión tiene `liveavatar_session_id`, el backend obtiene automáticamente la transcripción desde LiveAvatar (`GET /v1/sessions/{id}/transcript`) y la persiste en `SESSION_TRANSCRIPTS`. Si el fetch falla (timeout, 404, etc.), la sesión se cierra igual; no se bloquea el cierre.

#### Request

~~~json
{
  "status": "COMPLETADA",
  "metrics": {
    "turn_count": 12,
    "duration_seconds": 900
  }
}
~~~

#### Response (ejemplo)

~~~json
{
  "id": 42,
  "status": "COMPLETADA",
  "ended_at": "2026-02-10T15:55:00Z",
  "duration_seconds": 900
}
~~~

---

### 7.6 Obtener transcripción de sesión

**GET** `/sessions/{session_id}/transcript`

Obtiene la transcripción de la conversación de una sesión. Requiere acceso a la sesión (joven propio o profesional asignado). Si no existe transcripción (sesión sin LiveAvatar o fetch fallido), retorna `null` o 404 según implementación.

#### Response (ejemplo)

~~~json
{
  "transcript_data": [
    {
      "role": "user",
      "transcript": "Hola, soy María y vengo a postular al cargo.",
      "absolute_timestamp": 1739184000,
      "relative_timestamp": 0
    },
    {
      "role": "avatar",
      "transcript": "Buenos días María. Cuéntame un poco sobre tu experiencia.",
      "absolute_timestamp": 1739184005,
      "relative_timestamp": 5
    }
  ],
  "session_active": false,
  "fetched_at": "2026-02-10T15:55:01Z"
}
~~~

---

## 8. Eventos de sesión (SESSION_EVENTS)

Este bloque aporta trazabilidad y depuración (útil para el riesgo de integración del avatar).

### 8.1 Listar eventos de una sesión

**GET** `/sessions/{session_id}/events`

~~~json
[
  {
    "id": 101,
    "session_id": 42,
    "event_type": "CREATED",
    "occurred_at": "2026-02-10T15:40:00Z",
    "payload": { "source": "backend" }
  },
  {
    "id": 102,
    "session_id": 42,
    "event_type": "LIVEAVATAR_STARTED",
    "occurred_at": "2026-02-10T15:41:00Z",
    "payload": { "liveavatar_session_id": "lav_sess_987" }
  }
]
~~~

---

### 8.2 Registrar evento (interno)

**POST** `/sessions/{session_id}/events`

Endpoint documentado por completitud (puede considerarse interno).

---

## 9. Resúmenes cualitativos (INTERVIEW_SUMMARIES)

> MVP: el resumen puede ser escrito por el profesional.  
> Si LiveAvatar entrega resúmenes automáticos en el futuro, ELVIR puede almacenarlos sin cambiar el modelo base.

### 9.1 Crear/actualizar resumen

**POST** `/sessions/{session_id}/summary`

~~~json
{
  "summary_text": "Buen manejo de comunicación. Reforzar seguridad al responder preguntas abiertas.",
  "competency_tags": ["comunicacion", "seguridad"]
}
~~~

---

## 10. Competencias (COMPETENCIES / COMPETENCY_LEVELS / SESSION_COMPETENCIES)

Este bloque mantiene competencias desacopladas del perfil del joven (sin campos fijos).

### 10.1 Listar catálogo de competencias

**GET** `/competencies`

~~~json
[
  { "id": 1, "slug": "comunicacion", "name": "Comunicación", "is_active": true },
  { "id": 2, "slug": "regulacion_emocional", "name": "Regulación emocional", "is_active": true }
]
~~~

---

### 10.2 Listar niveles de competencia

**GET** `/competency-levels`

~~~json
[
  { "id": 1, "slug": "BAJO", "label": "Bajo", "sort_order": 1 },
  { "id": 2, "slug": "MEDIO", "label": "Medio", "sort_order": 2 },
  { "id": 3, "slug": "ALTO", "label": "Alto", "sort_order": 3 }
]
~~~

---

### 10.3 Registrar evaluación por sesión

**POST** `/sessions/{session_id}/competencies`

~~~json
{
  "items": [
    { "competency_slug": "comunicacion", "level_slug": "MEDIO", "comment": "Buena claridad general." },
    { "competency_slug": "regulacion_emocional", "level_slug": "BAJO", "comment": "Nerviosismo al inicio." }
  ]
}
~~~

---

### 10.4 Obtener evaluación por sesión

**GET** `/sessions/{session_id}/competencies`

~~~json
{
  "session_id": 42,
  "items": [
    {
      "competency": { "slug": "comunicacion", "name": "Comunicación" },
      "level": { "slug": "MEDIO", "label": "Medio" },
      "comment": "Buena claridad general."
    }
  ]
}
~~~

---

## 11. Material de apoyo (SUPPORT_MATERIAL / MATERIAL_SUGGESTIONS / MATERIAL_VIEWS)

**Quién sube material:**
- **ADMIN:** material general (visible para todos). `created_by` = null.
- **PROFESIONAL:** material propio (visible solo para sus jóvenes asignados). `created_by` = professional_id.

### 11.1 Listar material

**GET** `/support-material`

Filtros opcionales:
- `job_role_id`
- `case_id`

Para JOVEN: ve material general + material sugerido por su profesional.
Para PROFESIONAL: ve material general + su material propio (created_by = su id).
Para ADMIN: ve todo.

~~~json
[
  {
    "id": 8,
    "title": "Técnicas de comunicación efectiva",
    "description": "Consejos prácticos para entrevistas.",
    "type": "VIDEO",
    "url": "https://example.com/video",
    "job_role_id": 1,
    "case_id": null,
    "active": true
  }
]
~~~

---

### 11.2 Crear material (Admin o Profesional)

**POST** `/support-material`

Crea un nuevo recurso. ADMIN crea material general (`created_by` null). PROFESIONAL crea material propio (`created_by` = su id).

#### Request

~~~json
{
  "title": "Técnicas de comunicación efectiva",
  "description": "Consejos prácticos para entrevistas.",
  "type": "VIDEO",
  "url": "https://example.com/video",
  "job_role_id": 1,
  "case_id": null
}
~~~

#### Response

~~~json
{
  "id": 9,
  "title": "Técnicas de comunicación efectiva",
  "description": "Consejos prácticos para entrevistas.",
  "type": "VIDEO",
  "url": "https://example.com/video",
  "job_role_id": 1,
  "case_id": null,
  "created_by": null,
  "active": true
}
~~~

---

### 11.3 Sugerir material (profesional → joven)

**POST** `/support-material/suggest`

~~~json
{
  "youth_id": 5,
  "material_id": 8,
  "session_id": 42,
  "reason": "Refuerzo posterior a la simulación: comunicación efectiva."
}
~~~

---

### 11.4 Listar sugerencias de un joven

**GET** `/youths/{youth_id}/material-suggestions`

~~~json
[
  {
    "id": 3,
    "material_id": 8,
    "professional_id": 2,
    "session_id": 42,
    "reason": "Refuerzo posterior a la simulación.",
    "suggested_at": "2026-02-10T16:05:00Z"
  }
]
~~~

---

### 11.5 Registrar visualización (joven)

**POST** `/support-material/{material_id}/view`

~~~json
{
  "youth_id": 5
}
~~~

---

## 12. Estados y manejo de errores

Códigos HTTP estándar:

- 200 OK
- 201 Created
- 400 Bad Request
- 401 Unauthorized
- 403 Forbidden
- 404 Not Found
- 500 Internal Server Error

---

## 13. Alcance del API (MVP)

La API definida en este documento cubre el alcance del MVP. Queda fuera de alcance:

- Persistencia de audio/video.
- Análisis avanzado automatizado.
- Webhooks externos / streaming complejo.

Estas extensiones pueden incorporarse posteriormente sin romper la estructura base.

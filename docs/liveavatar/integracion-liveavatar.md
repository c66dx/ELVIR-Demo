# Integración con LiveAvatar – Enfoque Context Dinámico

Este documento describe el flujo de integración con LiveAvatar siguiendo el enfoque **Context Dinámico** (referencia: `docs/referencia-catalina/Context Dinámico`), donde el contexto es variable según cargo y parámetros, y el avatar/voz se definen por id en el código.

---

## 0. Contexto y alcance (instrucciones Catalina Valle)

La plataforma ELVIR es una **aplicación web** que permite:

- **Jóvenes:** practicar simulaciones de entrevista, ver historial, recibir retroalimentación, acceder a material de apoyo.
- **Profesionales:** gestionar jóvenes, crear perfiles, sugerir material, supervisar sesiones, escribir resúmenes.

**Integración con LiveAvatar:** El avatar y la conversación se consumen como servicio externo. ELVIR no implementa IA conversacional; LiveAvatar provee la experiencia del avatar + entrevista.

**Objetivos de integración (según instrucciones):**

- Desarrollar la Simulación de Entrevista funcional con LiveAvatar.
- El **Context debe ser variable** según cargo y otros parámetros por definir.
- Avatar y voz definidos por id dentro del código.
- Base de referencia: zip **Context Dinámico** (ver `docs/referencia-catalina/Context Dinámico`).

**Origen del contenido de los prompts:** Catalina creó el contenido (rol del avatar, cargos, casos/indicaciones) en:
- **Prompt Builder** (`docs/referencia-catalina/Prompt Builder/`): genera 16 prompts completos (4 cargos × 4 indicaciones) en `output_prompts/`.
- **Context Dinámico** (`docs/referencia-catalina/Context Dinámico/`): roles y casos embebidos en el HTML, el frontend los ensambla y envía por PATCH.

**Tu rol:** No debes crear ni modificar el contenido de los prompts. Usas lo que Catalina proporcionó. Tu tarea es implementar el **mecanismo** para que el contexto sea variable: cuando el usuario seleccione cargo + caso, tu sistema envíe el prompt correcto a LiveAvatar.

---

## 1. Requisitos de integración

- **Context variable** según cargo y otros parámetros por definir.
- **Avatar y voz** definidos por id dentro del código.
- **Base de referencia:** zip Context Dinámico.

---

## 2. Enfoque Context Dinámico

### 2.1 Idea general

En lugar de tener 16 contextos precreados en LiveAvatar (uno por cargo × caso), se usa **un único contexto** cuyo prompt se actualiza dinámicamente antes de cada sesión mediante PATCH a la API de LiveAvatar.

### 2.2 Flujo técnico

```
1. Usuario selecciona cargo + caso en el frontend
2. Frontend → Backend: POST /sessions (crea SESSION en BD)
3. Frontend → Backend: POST /sessions/{id}/start
4. Backend (ELVIR):
   a) Obtiene el prompt correspondiente (ver sección 3: archivos o catálogo)
   b) PATCH https://api.liveavatar.com/v1/contexts/{context_id}
      Body: { name, prompt, opening_text }
   c) POST https://api.liveavatar.com/v1/sessions/token
      Body: { mode, avatar_id, avatar_persona: { language, voice_id, context_id } }
   d) POST https://api.liveavatar.com/v1/sessions/start
      Header: Authorization: Bearer {session_token}
   e) Devuelve al frontend: livekit_url, access_token
5. Frontend conecta a LiveKit con livekit-client y reproduce video/audio (implementado en `simulacion-detail.component.ts`)
```

El contenido del prompt viene de la referencia de Catalina. Tu backend solo lo **obtiene** y lo **envía** a LiveAvatar; no lo creas ni lo modificas.

### 2.3 Variables de entorno (backend)

Configurar en `code/backend/.env`:

| Variable | Descripción |
|----------|-------------|
| `LIVEAVATAR_API_KEY` | API key para autenticación |
| `LIVEAVATAR_AVATAR_ID` | ID del avatar |
| `LIVEAVATAR_VOICE_ID` | ID de la voz |
| `LIVEAVATAR_CONTEXT_ID` | ID del contexto único (se actualiza con PATCH) |

Si no están configuradas, el endpoint `/sessions/{id}/start` devuelve un placeholder.

---

## 3. Obtención del prompt (contenido de Catalina)

El **contenido** de los prompts lo creó Catalina. No lo modificas. Tu backend solo lo obtiene y lo envía a LiveAvatar.

**Dos formas de implementarlo:**

### Opción A: Archivos del Prompt Builder

Catalina generó 16 prompts completos en `docs/referencia-catalina/Prompt Builder/output_prompts/` (ejemplo: `prompt_administrativo_normal.txt`, `prompt_operario_apoyo_regulacion_emocional.txt`).

Tu backend:

1. Recibe `cargo_id` + `case_id` (o equivalente).
2. Busca el archivo correspondiente (mapeo cargo×caso → nombre de archivo).
3. Lee el contenido del archivo.
4. Envía ese contenido a LiveAvatar con PATCH.

No hay concatenación; solo lectura de archivo.

### Opción B: Catálogo (estilo Context Dinámico)

El demo Context Dinámico tiene roles y casos en el HTML. Puedes copiar ese contenido a tu BD (JOB_ROLES, CASES) como seed y ensamblar el prompt al vuelo (base + cargo + caso) igual que hace el frontend del demo.

En ese caso, el contenido viene de la referencia; tú solo lo almacenas y lo concatenas.

### Resumen

| Opción | Fuente del contenido | Tu backend hace |
|--------|----------------------|-----------------|
| A      | Archivos `output_prompts/` | Lee archivo → PATCH |
| B      | BD (seed desde Context Dinámico) | Ensambla desde BD → PATCH |

---

## 4. Modelo de datos alineado

| Entidad | Uso |
|---------|-----|
| **JOB_ROLES** | Catálogo para la UI (selector de cargo). Con Opción B también aporta contenido al prompt. |
| **CASES** | Catálogo para la UI (selector de caso/dificultad). Con Opción B también aporta contenido al prompt. |
| **SIMULATION_TEMPLATES** | Mapeo cargo×caso → archivo (Opción A) o referencia en BD (Opción B). IDs de LiveAvatar: context_id, avatar_id, voice_id. |

En enfoque Context Dinámico, todas las plantillas pueden compartir el mismo `liveavatar_context_id`; el backend lo actualiza con PATCH antes de cada sesión.

---

## 5. API de LiveAvatar (referencia)

- **Base URL:** `https://api.liveavatar.com/v1`
- **Autenticación:** header `X-API-KEY: {LIVEAVATAR_API_KEY}`
- **PATCH /contexts/{id}** – Actualizar prompt del contexto
- **POST /sessions/token** – Crear token de sesión
- **POST /sessions/start** – Iniciar sesión (devuelve livekit_url, livekit_client_token)
- **GET /sessions/{session_id}/transcript** – Obtener transcripción de la conversación (role, transcript, timestamps)

---

## 6. Implementación actual (Opción B)

**Estado:** Implementado en `code/backend/`.

| Componente | Ubicación |
|------------|-----------|
| Prompt base | `app/prompts/prompt_base.txt` |
| Ensamblaje | `app/services/prompt_builder.py` |
| Integración LiveAvatar | `app/services/liveavatar.py` |
| Endpoint start | `app/routers/sessions.py` → `POST /sessions/{id}/start` |
| Seed (16 plantillas) | `seed.py` — 4 cargos × 4 casos |

**Cargos (seed):** Operario, Atención de Público, Administrativo, Técnico-Profesional. Contenido alineado con `cargos.json` y `Context Dinámico/roles-data`.  
**Casos (seed):** Normal, Baja, Media, Alta dificultad. Las instrucciones de prompt provienen de `indicaciones.json` (normal, apoyo_regulacion_emocional, alta_estructuracion_respuesta, exigencia_alta_presentacion_discapacidad).

**Diagrama:**

![Flujo integración LiveAvatar](../flujos/Flujo_integración_LiveAvatar.svg)

**Fuente Mermaid:** `docs/modelo-datos/flowchart-liveavatar.mmd`

---

## 7. Transcripción de sesión

Al cerrar una sesión (`POST /sessions/{id}/close`), el backend obtiene la transcripción desde LiveAvatar:

1. Si `session.liveavatar_session_id` existe, llama a `GET https://api.liveavatar.com/v1/sessions/{liveavatar_session_id}/transcript`.
2. Si la respuesta es exitosa, persiste el resultado en la tabla `SESSION_TRANSCRIPTS`.
3. Si el fetch falla (404, timeout, etc.), la sesión se cierra igual; no se bloquea el flujo.

El profesional puede consultar la transcripción vía `GET /sessions/{id}/transcript` al redactar el resumen cualitativo.

---


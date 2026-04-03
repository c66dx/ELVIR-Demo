# Integración con LiveAvatar – Enfoque Context Dinámico

> **Material de referencia opcional:** Los zips y carpetas *Prompt Builder* / *Context Dinámico* pueden existir en una carpeta local de material de diseño (nombre según el equipo; no siempre está versionada). Si no aparece tras clonar, el flujo técnico sigue siendo el descrito aquí y en el backend.

Este documento describe el flujo de integración con LiveAvatar siguiendo el enfoque **Context Dinámico** (referencia histórica: el zip **Context Dinámico** del material de diseño original), donde el contexto es variable según cargo y parámetros, y el avatar/voz se definen por id en el código.

---

## 0. Contexto y alcance

La plataforma ELVIR es una **aplicación web** que permite:

- **Jóvenes:** practicar simulaciones de entrevista, ver historial, recibir retroalimentación, acceder a material de apoyo.
- **Profesionales:** gestionar jóvenes, crear perfiles, sugerir material, supervisar sesiones, escribir resúmenes.

**Integración con LiveAvatar:** El avatar y la conversación se consumen como servicio externo. ELVIR no implementa IA conversacional; LiveAvatar provee la experiencia del avatar + entrevista.

**Objetivos de integración:**

- Desarrollar la Simulación de Entrevista funcional con LiveAvatar.
- El **Context debe ser variable** según cargo y otros parámetros por definir.
- Avatar y voz definidos por id dentro del código.
- Base de referencia: zip **Context Dinámico** (ver material de diseño / bloque inicial de este documento).

**Origen del contenido de los prompts:** El rol del avatar, cargos e indicaciones provienen del diseño de contenido del proyecto. En el material de referencia suelen aparecer como:
- **Prompt Builder** (carpeta *Prompt Builder/* con `output_prompts/`): 16 prompts completos (4 cargos × 4 indicaciones).
- **Context Dinámico** (carpeta *Context Dinámico/*): roles y casos embebidos en el HTML; el demo original ensambla y envía por PATCH.

**Responsabilidad de implementación:** El texto de los prompts es **contenido de producto** gestionado fuera del código de integración. La implementación en ELVIR consiste en el **mecanismo** para que el contexto sea variable: cuando el usuario seleccione cargo + caso, el backend debe enviar el prompt correcto a LiveAvatar (lectura desde archivos, catálogo en BD o ensamblado equivalente).

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

El contenido del prompt se obtiene del catálogo o archivos de diseño; el backend lo **lee** y lo **envía** a LiveAvatar según la configuración del producto, sin alterar el texto en la capa de integración.

### 2.3 Variables de entorno (backend)

Configurar en `code/backend/.env`:

| Variable | Descripción |
|----------|-------------|
| `LIVEAVATAR_API_KEY` | API key para autenticación |
| `LIVEAVATAR_AVATAR_ID` | ID del avatar |
| `LIVEAVATAR_VOICE_ID` | ID de la voz |
| `LIVEAVATAR_CONTEXT_ID` | ID del contexto único (se actualiza con PATCH) |

Si no están configuradas, el endpoint `/sessions/{id}/start` devuelve un placeholder.

**Idioma y acento:** El backend envía `avatar_persona.language: "es"` al crear el token. El acento depende del **Voice ID** en LiveAvatar, no de un locale regional en la API. Resumen para equipo e investigación: [ENTREGA-investigacion-voz.md](./ENTREGA-investigacion-voz.md).

---

## 3. Obtención del prompt (contenido de diseño)

El **texto** de los prompts es contenido de producto. En la implementación, el backend lo obtiene desde la fuente configurada y lo envía a LiveAvatar.

**Dos formas de implementarlo:**

### Opción A: Archivos del Prompt Builder

Ejemplo: 16 prompts completos en `…/Prompt Builder/output_prompts/` (ruta local según el material disponible), p. ej. `prompt_administrativo_normal.txt`, `prompt_operario_apoyo_regulacion_emocional.txt`.

El backend:

1. Recibe `cargo_id` + `case_id` (o equivalente).
2. Busca el archivo correspondiente (mapeo cargo×caso → nombre de archivo).
3. Lee el contenido del archivo.
4. Envía ese contenido a LiveAvatar con PATCH.

No hay concatenación; solo lectura de archivo.

### Opción B: Catálogo (estilo Context Dinámico)

El demo Context Dinámico tiene roles y casos en el HTML. Ese contenido puede copiarse a la BD (`JOB_ROLES`, `CASES`) como seed y ensamblarse al vuelo (base + cargo + caso), como en el frontend del demo.

En ese caso, el contenido se almacena en BD y se concatena según reglas de negocio.

### Resumen

| Opción | Fuente del contenido | El backend hace |
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

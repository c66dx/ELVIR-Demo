# Addendum v1.1 – Actualización técnica de la propuesta ELVIR

**Proyecto:** Plataforma Web para habilitación de ELVIR  
**Versión:** v1.1  
**Autora:** Catalina  
**Fecha:** Febrero 2026  
**Contexto:** Práctica profesional — UNAB  
**Documento base:** Propuesta técnica v1.0 (29/01/2026)

---

## 1. Contexto de la actualización

Desde la versión v1.0 de la propuesta técnica, el diseño del sistema ha evolucionado a partir de:

- Desarrollo de mockups y flujos detallados (joven y profesional).
- Refinamiento del modelo de datos (separación explícita de sesión).
- Discusión técnica sobre la integración con LiveAvatar.
- Necesidad de clarificar responsabilidades entre ELVIR y el servicio externo.
- Formalización del dominio propio de la plataforma (cargos, casos, plantillas).

El presente addendum documenta las decisiones arquitectónicas y estructurales incorporadas en la versión actual del diseño (v1.1), manteniendo el alcance funcional original del MVP.

---

## 2. Cambios principales respecto a v1.0

### 2.1 Separación formal entre configuración y ejecución

En la versión v1.0 el modelo conceptual distinguía entrevistas, pero no formalizaba claramente la diferencia entre:

- La **configuración reusable** de una entrevista.
- La **ejecución concreta** realizada por un joven.

En v1.1 se consolida esta separación mediante:

- `SIMULATION_TEMPLATES` → configuración reusable  
- `SESSIONS` → ejecución real (intento concreto)

#### SIMULATION_TEMPLATES
Define:
- Cargo (`JOB_ROLES`)
- Caso/dificultad (`CASES`)
- Identificadores técnicos hacia LiveAvatar:
  - `liveavatar_context_id`
  - `liveavatar_avatar_id`
  - `liveavatar_voice_id`

#### SESSIONS
Representa:
- Cada intento real del joven.
- Estado (`EN_CURSO`, `COMPLETADA`, `CANCELADA`, `ERROR`).
- Timestamps.
- Modo (`AUTOGESTIONADA` / `SUPERVISADA`).
- Identificador técnico externo (`liveavatar_session_id`).

Esta separación:

- Permite historial limpio.
- Evita duplicación de configuración.
- Soporta múltiples intentos por joven.
- Responde directamente al feedback sobre la necesidad de una “tabla de sesión” independiente.

---

### 2.2 Introducción de SESSION_EVENTS (trazabilidad técnica)

Se agrega la entidad:

- `SESSION_EVENTS`

Propósito:

- Registrar eventos relevantes:
  - `CREATED`
  - `LIVEAVATAR_STARTED`
  - `ENDED`
  - `ERROR`
- Facilitar depuración.
- Mitigar riesgo técnico de integración con LiveAvatar.

Esta entidad:

- No cambia el alcance funcional del MVP.
- Mejora robustez y observabilidad del sistema.
- Permite diferenciar fallas técnicas de cancelaciones voluntarias.

---

### 2.3 Formalización del dominio ELVIR (cargos y casos)

En el demo inicial (30/01/2026), los prompts estaban definidos directamente en LiveAvatar como *Contexts*.

En v1.1 se formaliza el dominio propio de ELVIR mediante:

- `JOB_ROLES`
- `CASES`
- `SIMULATION_TEMPLATES`

ELVIR mantiene el catálogo y el mapeo hacia:

- `liveavatar_context_id`
- `liveavatar_avatar_id`
- `liveavatar_voice_id`

Ventajas:

- No se hardcodean valores en el frontend.
- El backend controla la lógica de negocio.
- Se desacopla el dominio interno del proveedor externo.
- Se mantiene trazabilidad entre cargo/caso y sesión real.

---

### 2.4 Competencias desacopladas del perfil del joven

En v1.0 las métricas eran principalmente libres o generales.

En v1.1 se define un modelo estructurado y desacoplado:

- `COMPETENCIES`
- `COMPETENCY_LEVELS`
- `SESSION_COMPETENCIES`

Esto permite:

- No agregar campos fijos al perfil del joven.
- Registrar evaluaciones por sesión.
- Extender el catálogo sin modificar la estructura base.
- Derivar estado longitudinal sin romper el modelo.

Esta decisión responde al criterio de mantener estados y grados de competencia como entidades independientes.

---

### 2.5 Clarificación de la integración con LiveAvatar

Se explicita que:

- LiveAvatar es tratado como **caja negra**.
- ELVIR no implementa ni entrena modelos IA.
- La conversación ocurre fuera de ELVIR.
- ELVIR solo:
  - Crea/inicia sesión.
  - Guarda referencias técnicas.
  - Controla estados.
  - Registra trazabilidad.

A la fecha de esta versión:

- No se cuenta con contrato final de integración.
- No se dispone de credenciales definitivas.
- El mecanismo puede ser:
  - Embebido (iframe), y/o
  - Runtime/SDK en navegador.

La arquitectura se diseña para soportar cualquiera de estas variantes sin romper el modelo base.

---

## 3. Confirmación de arquitectura (Opción A consolidada)

Se confirma arquitectura lógica en 3 capas:

1. **Frontend Angular**
2. **Backend Python (FastAPI)**
3. **Servicio externo LiveAvatar**

El backend actúa como:

- Orquestador de sesiones.
- Controlador de estados.
- Gestor del dominio ELVIR.
- Punto único de persistencia.
- Intermediario técnico hacia LiveAvatar.

### Aclaración clave

No existe comunicación directa lógica de negocio:

Frontend → LiveAvatar


Toda creación y control de sesión debe pasar por el backend ELVIR para mantener trazabilidad y coherencia del estado.

(La experiencia visual puede embebirse, pero el estado se controla desde backend).

---

## 4. Impacto en la API

La API se amplía y consolida para cubrir:

- Catálogos:
  - `/job-roles`
  - `/cases`
- Plantillas:
  - `/simulation-templates`
- Sesiones:
  - `/sessions`
  - `/sessions/{id}/start`
  - `/sessions/{id}/close`
- Eventos:
  - `/sessions/{id}/events`
- Competencias:
  - `/competencies`
  - `/sessions/{id}/competencies`
- Material:
  - `/support-material`
  - `/support-material/suggest`

El detalle completo se encuentra en:

docs/api/endpoints.md


---

## 5. Impacto en el modelo de datos

El modelo actualizado incorpora:

- Separación configuración / ejecución.
- Entidad explícita de sesión.
- Entidad de eventos.
- Modelo desacoplado de competencias.
- Material de apoyo con trazabilidad de sugerencia y visualización.

El detalle completo se encuentra en:

docs/modelo-datos/diccionario_datos.md
docs/modelo-datos/erd.svg


---

## 6. Confirmación de alcance

El alcance funcional del MVP **no cambia** respecto a la versión v1.0.

Se mantiene:

- Demo funcional.
- Integración con IA externa.
- No entrenamiento de modelos.
- Métricas simples.
- Interfaz clara priorizada sobre diseño avanzado.

Las modificaciones de v1.1 corresponden a:

- Mejora estructural.
- Mayor trazabilidad.
- Mejor alineación con feedback técnico.
- Mayor coherencia entre flujos, base de datos y API.
- Clarificación explícita de responsabilidades frente a LiveAvatar.

---

## 7. Conclusión

La versión v1.1 consolida el diseño técnico del MVP de ELVIR, fortaleciendo:

- Separación de responsabilidades.
- Robustez del modelo de datos.
- Claridad en la integración con servicio externo.
- Escalabilidad futura sin romper la estructura base.

Este addendum formaliza la evolución técnica del proyecto y deja alineada la documentación con el estado actual del diseño arquitectónico y del modelo de datos.

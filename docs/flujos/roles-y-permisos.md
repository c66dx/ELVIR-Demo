# Roles y permisos – ELVIR

Este documento resume los roles del sistema, sus alcances y las reglas de negocio acordadas.

---

## 1. Roles

| Rol | Descripción | Alcance |
|-----|-------------|---------|
| **JOVEN** | Usuario que realiza simulaciones de entrevistas | Simulaciones, historial, material sugerido por su profesional |
| **PROFESIONAL** | Usuario que gestiona jóvenes y su seguimiento | Crear/editar jóvenes asignados, sesiones supervisadas, resúmenes, sugerir material, subir material propio |
| **ADMIN** | Usuario administrador del sistema | Crear profesionales, subir material general |

---

## 2. Alcance por rol

### 2.1 JOVEN

- Iniciar sesión (si tiene credenciales) o acceso supervisado.
- Realizar simulaciones (autogestionadas o supervisadas).
- Ver historial de sesiones y resúmenes.
- Ver material general y material sugerido por su profesional.
- Registrar visualización de material.

### 2.2 PROFESIONAL

- Crear jóvenes (automáticamente queda asignado).
- Editar y desactivar jóvenes asignados.
- Iniciar sesiones supervisadas.
- Escribir resúmenes cualitativos por sesión.
- Sugerir material a sus jóvenes asignados.
- **Subir material propio** (visible solo para él y sus jóvenes).
- Ver perfil del joven (incl. checklist de perfil postulante).

### 2.3 ADMIN

- **Crear profesionales** (dar de alta nuevos usuarios con rol PROFESIONAL).
- **Subir material general** (visible para todos los profesionales y jóvenes).

---

## 3. Reglas de negocio clave

### 3.1 Asignación joven–profesional

- Cuando un profesional crea un joven, se crea automáticamente una asignación ACTIVA.
- No existe flujo de Admin asignando jóvenes a profesionales.

### 3.2 Material de apoyo

- **Material general:** creado por Admin (`created_by` = null). Visible para todos.
- **Material propio:** creado por Profesional (`created_by` = professional_id). Visible solo para ese profesional y sus jóvenes asignados.
- El profesional sugiere material (existente) a jóvenes concretos mediante MATERIAL_SUGGESTIONS.

### 3.3 Checklist de perfil postulante

- Lista predefinida de 9 ítems (comunicación, trabajo en equipo, puntualidad, etc.).
- El profesional **marca** los que aplican al joven (no los escribe).
- Se almacena como array de slugs en YOUTH.profile_checklist.

### 3.4 Catálogos

- JOB_ROLES, CASES, SIMULATION_TEMPLATES: gestionados externamente. Admin no los toca.

---

## 4. Endpoints por rol

| Endpoint | JOVEN | PROFESIONAL | ADMIN |
|----------|-------|-------------|-------|
| POST /auth/login | ✓ | ✓ | ✓ |
| GET /youths | ✓ (solo el suyo) | ✓ (asignados) | — |
| POST /youths | — | ✓ | — |
| PUT /youths/{id} | — | ✓ (asignados) | — |
| POST /professionals | — | — | ✓ |
| GET /support-material | ✓ (filtrado) | ✓ (filtrado) | ✓ |
| POST /support-material | — | ✓ (propio) | ✓ (general) |
| POST /support-material/suggest | — | ✓ | — |

---


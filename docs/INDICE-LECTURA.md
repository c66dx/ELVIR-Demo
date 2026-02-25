# Guía de lectura – Documentación ELVIR

Este índice indica **en qué orden leer** la documentación para entender el proyecto de forma progresiva. No duplica contenido: cada enlace lleva al documento original.

---

## Orden sugerido

### 1. Contexto y propósito
**¿Qué es ELVIR y para qué existe?**

| Documento | Qué aprenderás |
|-----------|-----------------|
| [Propuesta técnica v1.0](propuesta/propuesta_técnica_v1_0.md) | Objetivo del proyecto, casos de uso, requisitos, alcance del MVP |
| [Addendum v1.1](propuesta/addendum_v1_1.md) | Cambios desde v1.0: separación sesión/plantilla, decisiones arquitectónicas |

---

### 2. Arquitectura
**¿Cómo está construido el sistema?**

| Documento | Qué aprenderás |
|-----------|-----------------|
| [Arquitectura](arquitectura/arquitectura.md) | Tres capas (frontend, backend, LiveAvatar), responsabilidades, flujo técnico de una simulación |

---

### 3. Flujos y roles
**¿Qué hace cada usuario en la plataforma?**

| Documento | Qué aprenderás |
|-----------|-----------------|
| [Flujos de usuario](flujos/flujos.md) | Flujo del joven, profesional y admin; diagramas de flujo; acceso supervisado y activación de cuenta |
| [Roles y permisos](flujos/roles-y-permisos.md) | JOVEN, PROFESIONAL, ADMIN: alcance, reglas de negocio |

---

### 4. Modelo de datos
**¿Qué se guarda y cómo se relaciona?**

| Documento | Qué aprenderás |
|-----------|-----------------|
| [Modelo de datos](modelo-datos/modelo_datos.md) | Entidades, relaciones, diagramas ER |
| [Diccionario de datos](modelo-datos/diccionario_datos.md) | Definición de cada campo y tabla |

---

### 5. Integración
**¿Cómo se conecta con LiveAvatar?**

| Documento | Qué aprenderás |
|-----------|-----------------|
| [Integración LiveAvatar](liveavatar/integracion-liveavatar.md) | Context Dinámico, PATCH al contexto, flujo de creación de sesión |

---

### 6. API
**¿Qué endpoints expone el backend?**

| Documento | Qué aprenderás |
|-----------|-----------------|
| [Endpoints](api/endpoints.md) | Contratos de cada ruta: request, response, autenticación |

---

## Lectura rápida (solo lo esencial)

Si tienes poco tiempo, lee en este orden:

1. [Arquitectura](arquitectura/arquitectura.md) – visión general
2. [Flujos](flujos/flujos.md) – qué hace cada rol
3. [Roles y permisos](flujos/roles-y-permisos.md) – alcance de cada uno

---

## Guía de diagramas

| Documento | Uso |
|-----------|-----|
| [Guía de gráficos](GUIA-GRAFICOS.md) | Explica qué representa cada diagrama y cuándo leerlo (para personas nuevas en el proyecto) |

---

## Para la práctica profesional

| Documento | Uso |
|-----------|-----|
| [Guía de gráficos](GUIA-GRAFICOS.md) | Explicaciones para presentar cada diagrama de forma clara |

---

## Código (después de la documentación)

| Documento | Uso |
|-----------|-----|
| [Frontend README](../code/frontend/README.md) | Estructura del frontend, carpetas, modelos, servicios, guards |
| [Backend README](../code/backend/README.md) | Cómo ejecutar el backend, instalación, configuración |

---

*Los diagramas en `docs/arquitectura/`, `docs/flujos/` y `docs/modelo-datos/` complementan los .md anteriores. Ver [Guía de gráficos](GUIA-GRAFICOS.md) para explicaciones detalladas.*

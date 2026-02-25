# Guía de los gráficos y diagramas – ELVIR

Esta guía explica **qué representa cada diagrama** y **cuándo conviene consultarlo** para alguien que está conociendo el proyecto por primera vez.

---

## Diagramas de arquitectura

### 1. Arquitectura general (`arquitectura/Arquitectura.svg`)

**¿Qué muestra?**  
Las tres capas del sistema y cómo se comunican entre sí.

**Elementos principales:**
- **Frontend (Angular):** La interfaz web que usa el joven y el profesional. Consume la API del backend y muestra el avatar.
- **Backend (FastAPI):** El servidor que orquesta todo: autenticación, base de datos, integración con LiveAvatar.
- **LiveAvatar:** Servicio externo que provee el avatar conversacional y la IA. ELVIR no implementa IA; la consume como caja negra.

**Cuándo leerlo:** Al inicio, para entender la estructura general del sistema.

---

### 2. Diagrama de secuencia (`arquitectura/ddsecuencias.svg`)

**¿Qué muestra?**  
El flujo técnico paso a paso de una simulación: qué hace el frontend, el backend y LiveAvatar en cada momento.

**Secuencia típica:**
1. Usuario elige cargo y caso en el frontend.
2. Frontend pide al backend crear sesión.
3. Backend guarda la sesión en BD.
4. Backend obtiene el prompt y hace PATCH al contexto en LiveAvatar.
5. Backend crea la sesión en LiveAvatar y recibe token/URL.
6. Frontend conecta a LiveKit y reproduce el avatar.
7. La conversación ocurre en LiveAvatar.
8. Al finalizar, el backend cierra la sesión y actualiza el estado.

**Cuándo leerlo:** Cuando quieras entender el flujo técnico detallado o depurar la integración con LiveAvatar.

---

## Diagramas de flujos de usuario

### 3. Resumen de roles (`flujos/resumen_roles.svg`)

**¿Qué muestra?**  
Una vista general de los tres roles (JOVEN, PROFESIONAL, ADMIN) y sus principales acciones.

**Elementos:**
- **JOVEN:** Dashboard, simulaciones, historial, material de apoyo.
- **PROFESIONAL:** Dashboard, gestión de jóvenes, sesiones supervisadas, resúmenes, sugerir material.
- **ADMIN:** Crear profesionales, subir material general.

**Cuándo leerlo:** Como primer acercamiento a quién hace qué en la plataforma.

---

### 4. Flujo del joven (`flujos/flujo_joven.svg`)

**¿Qué muestra?**  
El recorrido completo de un joven en la plataforma: desde que accede hasta que termina una simulación y revisa material.

**Pasos principales:**
- Acceso (login propio o supervisado).
- Nueva simulación o historial.
- Ejecución con avatar (LiveAvatar).
- Cierre de sesión.
- Material de apoyo sugerido.

**Cuándo leerlo:** Para entender la experiencia del joven y el ciclo de práctica.

---

### 5. Flujo del profesional (`flujos/flujo_profesional.svg`)

**¿Qué muestra?**  
Las acciones del profesional: gestión de jóvenes, sesiones supervisadas, resúmenes, sugerir material.

**Pasos principales:**
- Listado de jóvenes asignados.
- Ver perfil, editar, crear joven.
- Iniciar sesión supervisada.
- Registrar resumen de entrevista.
- Sugerir material de apoyo.

**Cuándo leerlo:** Para entender cómo el profesional acompaña a los jóvenes.

---

### 6. Flujo del admin (`flujos/flujo_admin.svg`)

**¿Qué muestra?**  
Las funciones del administrador: crear profesionales y subir material general.

**Elementos:**
- Crear profesionales (email, contraseña, nombre, etc.).
- Subir material visible para todos (sin `created_by`).

**Cuándo leerlo:** Para entender el alcance del rol admin (limitado a usuarios y material general).

---

### 7. Flujo de activación de cuenta (`flujos/flujo_activacion_cuenta.svg`)

**¿Qué muestra?**  
El proceso cuando un profesional crea un joven con login habilitado: cómo el joven recibe un enlace, define su contraseña y activa su cuenta.

**Pasos principales:**
1. Profesional crea joven con email y marca "Login habilitado".
2. Backend genera invitación con token.
3. Profesional entrega enlace al joven.
4. Joven abre enlace, define contraseña.
5. Backend crea usuario y lo vincula al joven.
6. Joven puede iniciar sesión.

**Cuándo leerlo:** Para entender el flujo de invitación y activación de cuentas.

---

### 8. Flujo integración LiveAvatar (`flujos/Flujo_integración_LiveAvatar.svg`)

**¿Qué muestra?**  
Cómo ELVIR se conecta con LiveAvatar para cada simulación: selección de cargo/caso, PATCH al contexto, creación de sesión, conexión del frontend.

**Elementos:**
- Usuario elige cargo + caso.
- Backend obtiene prompt y actualiza el contexto en LiveAvatar (Context Dinámico).
- Backend crea sesión en LiveAvatar.
- Frontend recibe token/URL y conecta a LiveKit.

**Cuándo leerlo:** Para entender la integración con el servicio externo del avatar.

---

### 9. Estados de sesión (`flujos/estados_sesion.svg`)

**¿Qué muestra?**  
Los estados por los que pasa una sesión de simulación: EN_CURSO, COMPLETADA, CANCELADA, ERROR.

**Elementos:**
- Transiciones entre estados.
- Diferenciación entre finalización normal, cancelación voluntaria y error técnico.

**Cuándo leerlo:** Para entender el ciclo de vida de una sesión y la trazabilidad.

---

## Diagramas del modelo de datos

### 10. Diagrama entidad–relación (`modelo-datos/erd.svg`)

**¿Qué muestra?**  
Las tablas de la base de datos y sus relaciones: usuarios, jóvenes, profesionales, sesiones, material, sugerencias, etc.

**Entidades principales:**
- **USERS:** Credenciales (email, rol).
- **YOUTHS:** Perfiles de jóvenes.
- **PROFESSIONALS:** Perfiles de profesionales.
- **ASSIGNMENTS:** Asignación profesional–joven.
- **SESSIONS:** Sesiones de simulación.
- **SUPPORT_MATERIAL:** Material de apoyo.
- **MATERIAL_SUGGESTIONS:** Material sugerido por profesional a un joven.

**Cuándo leerlo:** Para entender qué datos persiste el sistema y cómo se relacionan.

---

## Orden sugerido para leer los gráficos

1. **Resumen de roles** → visión general de quién hace qué.
2. **Arquitectura general** → cómo está construido el sistema.
3. **Flujo del joven** → experiencia principal del usuario final.
4. **Flujo del profesional** → experiencia del acompañante.
5. **Estados de sesión** → ciclo de vida de una simulación.
6. **Flujo integración LiveAvatar** → conexión con el avatar.
7. **Diagrama de secuencia** → detalle técnico del flujo.
8. **Diagrama ER** → modelo de datos.
9. **Flujo admin** y **Flujo activación** → cuando necesites esos flujos concretos.

---


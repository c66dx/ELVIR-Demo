# Manual de usuario — ELVIR (v1)

**Versión del documento:** 1.1 (piloto)  
**Aplicación:** ELVIR — plataforma de práctica de entrevistas laborales con avatar.  
**Audiencia:** jóvenes usuarios, tutores (profesionales) y administradores.

---

## 1. Introducción

### 1.1 ¿Qué es ELVIR?

ELVIR es una aplicación web que permite **practicar entrevistas de trabajo** en un entorno guiado: el joven configura un contexto de simulación, revisa una sala previa y realiza la entrevista con un **avatar** (simulación tipo videollamada). Los **tutores** dan seguimiento a los jóvenes asignados, revisan sesiones y pueden sugerir material de apoyo. Los **administradores** gestionan tutores, material y consultas de uso según el despliegue del piloto.

### 1.2 Roles en el sistema

| Rol | Descripción breve |
|-----|---------------------|
| **Joven** | Practica entrevistas, ve historial, retroalimentación y material sugerido. |
| **Profesional (tutor)** | Administra jóvenes asignados, revisa entrevistas y puede acompañar flujos supervisados cuando aplique. |
| **Administrador** | Panel de gestión: tutores, material, usuarios/logs y auditoría. |

### 1.3 Requisitos

- Navegador actualizado (Chrome, Edge o Firefox recomendados).  
- Conexión a internet estable (audio y video según la configuración del piloto).  
- **Permiso de micrófono** en el navegador cuando la entrevista lo requiera.  
- **URL** y **credenciales** las entrega el equipo del proyecto (en demostraciones también pueden verse en la pantalla de inicio de sesión o en el README del repositorio).

### 1.4 Glosario breve

| Término | Significado en ELVIR |
|---------|----------------------|
| **Sesión / simulación** | Una entrevista de práctica concreta, desde la configuración hasta el cierre. |
| **Sala previa** | Pantalla donde eliges cargo, escenario y briefing antes de conectar con la entrevista. |
| **Avatar / entrevistador virtual** | Personaje que conduce la entrevista (en la interfaz aparece como modalidad videollamada con entrevistadora IA). |
| **Retroalimentación** | Comentarios o resumen asociados a una sesión ya realizada (cuando el flujo del piloto lo habilita). |
| **Material** | Documentos o recursos de apoyo que el tutor o el administrador asocian al proceso. |
| **Simulación supervisada** | Flujo en que el tutor inicia o acompaña la práctica desde el perfil del joven (si está habilitado en tu entorno). |

---

## 2. Acceso e identificación

### 2.1 Iniciar sesión

1. Abre la URL del entorno (desarrollo, preview o producción piloto).  
2. En la pantalla de **inicio de sesión**, introduce **correo** y **contraseña** y confirma.  
3. Si tus datos son correctos, entrarás al **panel** correspondiente a tu rol.

**Figura sugerida:** `docs/manual-usuario/img/01-login.png` — Vista completa del inicio de sesión.

### 2.2 Primera vez y contraseña

- **Activación de cuenta:** si aplica, usa el enlace o instrucciones que te envió el equipo (en la aplicación suele existir una ruta de activación para completar el registro).  
- **Cambiar contraseña:** con sesión iniciada, suele alcanzar con el enlace **Cambiar contraseña** del menú de usuario (barra superior) o la ruta dedicada del sistema; los **administradores** acceden a **Mi perfil** en ese menú, que lleva al cambio de contraseña.

**Figura sugerida:** `docs/manual-usuario/img/02-cambiar-contrasena.png`

### 2.3 Credenciales de demostración (solo entornos de prueba)

En repositorios y despliegues demo, las cuentas de prueba están en el **README** del proyecto (en **main** suelen ser `joven1@test.cl` / `joven2@test.cl`, tutor y admin `@test.cl`; otra rama puede listar más jóvenes). **No uses esas claves en un entorno real de producción.**

### 2.4 Barra superior y menú de usuario (todas las sesiones iniciadas)

En la parte superior verás el nombre **ELVIR**, logos institucionales si aplican, y a la derecha:

- **Tema claro / oscuro:** alterna la apariencia de la aplicación.  
- **Campana de notificaciones** (rol **Joven**): abre un listado; puedes **marcar todo como leído** o abrir cada aviso.  
- **Tu nombre o iniciales:** al pulsarlo se abre el menú con **Mi Cuenta** (joven y tutor) o **Mi perfil** (administrador) y **Cerrar sesión**.  
- **Cerrar sesión:** pide confirmación (*¿Seguro que quieres cerrar sesión?*); al aceptar, sales de la aplicación.

A la **izquierda** está el **menú lateral** (se puede contraer o expandir con la flecha del borde del menú) con las secciones según tu rol.

**Figura sugerida:** `docs/manual-usuario/img/00-barra-superior.png` — Barra superior con menú de usuario abierto (sin datos sensibles).

---

## 3. Manual — Rol joven

Con rol **Joven**, el menú lateral incluye **Entrevista**, **Historial**, **Retroalimentación**, **Material** y **Notificaciones**. La entrada principal a la práctica es **Entrevista**.

### 3.1 Nueva entrevista (sala previa y simulación)

1. En el menú, elige **Entrevista** (es la pantalla principal al entrar como joven).  
2. Verás la **sala previa de entrevista**, con un texto que indica que debes confirmar rol, escenario y briefing antes de la videollamada.  
3. Recorre los **pasos en pantalla** (numerados en la interfaz):  
   - **Cargo:** selecciona o busca el cargo al que postulas; define el perfil del caso.  
   - **Escenario:** elige el nivel de dificultad u opciones que ofrezca el sistema.  
   - **Briefing:** completa el contexto de la empresa o situación que pida el formulario.  
   - **Ingreso:** cuando el formulario esté válido, avanza para **conectar** a la preparación, sala de espera y entrevista en vivo (la app te irá guiando).  
4. **Micrófono:** si el navegador lo solicita, **permite el acceso** para que la entrevista funcione.

**Figuras sugeridas:**  
- `03-joven-nueva-simulacion.png` — Sala previa con pasos Cargo / Escenario / Briefing / Ingreso.  
- `04-joven-preparacion.png` — Pantalla de preparación.  
- `05-joven-espera.png` — Sala de espera.  
- `06-joven-entrevista.png` — Entrevista en curso (sin datos personales reales visibles).

### 3.2 Historial

Menú **Historial**. Ahí aparecen las sesiones anteriores; puedes abrir el detalle cuando esté disponible.

**Figura sugerida:** `07-joven-historial.png`

### 3.3 Retroalimentación

Menú **Retroalimentación**: listado de sesiones con comentarios o resúmenes. Al elegir una fila o elemento se abre el **detalle** de esa sesión.

**Figura sugerida:** `08-joven-retroalimentacion.png`

### 3.4 Material de apoyo

Menú **Material**: recursos que tu tutor o el sistema han asociado a tu proceso.

**Figura sugerida:** `09-joven-material.png`

### 3.5 Notificaciones y cuenta

- **Notificaciones:** también desde el menú lateral, además de la campana superior.  
- **Mi Cuenta:** desde el menú de usuario (arriba a la derecha) o el lateral, según versión; ahí revisas datos básicos de tu perfil.

**Figuras sugeridas:** `10-joven-notificaciones.png`, `11-joven-cuenta.png`

### 3.6 Fin de sesión

Al terminar una simulación, la aplicación puede mostrar una **pantalla de cierre** con resumen o siguientes pasos, según la configuración del piloto.

---

## 4. Manual — Rol tutor (profesional)

Con rol **Profesional**, el menú lateral incluye **Dashboard**, **Jóvenes**, **Entrevistas** y **Material**.

### 4.1 Dashboard

Resumen y accesos rápidos al trabajo diario con tus jóvenes asignados.

**Figura sugerida:** `12-profesional-dashboard.png`

### 4.2 Jóvenes

- **Listado:** todos los jóvenes que puedes gestionar.  
- **Nuevo joven:** alta de ficha (datos que pida el formulario).  
- **Perfil de un joven:** al abrir un joven ves métricas, historial y acciones (por ejemplo sugerir material).  
- **Editar:** modifica los datos del joven.  
- **Simulación supervisada:** si tu entorno la tiene activa, suele iniciarse desde el perfil del joven (flujo dedicado).

**Figuras sugeridas:** `13-profesional-lista-jovenes.png`, `14-profesional-perfil-joven.png`, `15-profesional-supervisada.png` (si aplica).

### 4.3 Entrevistas (sesiones)

- **Listado** de sesiones de tus jóvenes.  
- **Detalle** de una sesión: revisión de lo ocurrido en la entrevista (transcripción o vista según piloto).

**Figura sugerida:** `16-profesional-sesiones.png`

### 4.4 Material

- **Catálogo** de material disponible.  
- **Alta de material** (`/profesional/material/nuevo`): en despliegues donde el tutor puede crear recursos.

**Figura sugerida:** `17-profesional-material.png`

### 4.5 Acompañar una entrevista (vista tutor)

Cuando debas entrar a la misma sesión que el joven (preparación, espera o entrevista), usa los enlaces o acciones que el sistema muestre desde el perfil o la sesión; las pantallas son análogas a las del joven pero en contexto tutor.

**Figura sugerida:** `18-profesional-simulacion.png`

### 4.6 Cuenta del profesional

**Mi Cuenta** en el menú de usuario: datos y preferencias de tu usuario tutor.

---

## 5. Manual — Rol administrador

El menú incluye **Dashboard**, **Usuarios y logs**, **Auditoría**, **Tutores** y **Material**. Desde el menú de usuario, **Mi perfil** lleva al **cambio de contraseña** del administrador.

| Sección | Uso |
|--------|-----|
| **Dashboard** | Resumen administrativo |
| **Usuarios y logs** | Consulta de usuarios y registros de actividad |
| **Auditoría** | Registro de auditoría |
| **Tutores** | Listado; alta y edición de cuentas tutor |
| **Material** | Catálogo y alta de material |

**Figuras sugeridas:** `19-admin-dashboard.png`, `20-admin-profesionales.png`, `21-admin-material.png`

> **Nota para el piloto:** si los participantes no usan rol administrador, esta sección puede omitirse en el PDF que entregues solo a jóvenes y tutores.

---

## 6. Preguntas frecuentes (FAQ)

**¿Olvidé mi contraseña?**  
Contacta al responsable del piloto o al soporte indicado por el equipo; el recupero de clave depende de cómo esté configurado el entorno.

**¿Por qué no veo una opción en el menú?**  
Las pantallas dependen del **rol**. Si crees que tu rol es incorrecto, pide ayuda a un administrador.

**¿La entrevista no inicia o se corta el audio?**  
Comprueba conexión, permisos del navegador (**micrófono**) y usa un navegador recomendado. Indica hora aproximada y tu correo de usuario al reportar el problema.

**¿Cómo cambio entre tema claro y oscuro?**  
Usa el control **Tema claro / Tema oscuro** en la barra superior.

**¿Las notificaciones del joven son las mismas que el menú Notificaciones?**  
La **campana** arriba y la sección **Notificaciones** del menú enlazan el mismo tipo de avisos; en la campana puedes marcar todo como leído.

**¿Dónde reporto un error?**  
Por el canal acordado con **ITiSB** o el contacto del proyecto (por ejemplo, David Araya).

---

## 7. Contacto y soporte

- **Organización / proyecto:** ITiSB — plataforma ELVIR.  
- **Consultas funcionales o piloto:** contacto designado por el equipo (p. ej. David Araya).  
- **Incidencias técnicas:** según el proceso definido para tu institución o despliegue.

---

## 8. Anexo — Capturas sugeridas para PDF (10–12 páginas)

Prioriza estas imágenes al armar el documento final:

1. `01-login.png`  
2. `00-barra-superior.png` (opcional pero mejora la sección común)  
3. `03-joven-nueva-simulacion.png` o `06-joven-entrevista.png`  
4. `07-joven-historial.png`  
5. `08-joven-retroalimentacion.png`  
6. `12-profesional-dashboard.png`  
7. `14-profesional-perfil-joven.png`  
8. `16-profesional-sesiones.png`  
9. `19-admin-dashboard.png` (solo si admin participa en el piloto)  
10. `02-cambiar-contrasena.png` o `09-joven-material.png`

**Consejo:** resolución 1280×720 o 1920×1080; cuentas demo; oculta u ofusca datos personales reales.

---

## Apéndice A — Referencia de rutas URL (soporte)

Solo para **soporte técnico** o documentación interna; el usuario final puede ignorar esta tabla.

| Área | Ruta (ejemplo) |
|------|----------------|
| Login | `/login` |
| Activación | `/activar` |
| Cambiar contraseña | `/cambiar-contrasena` |
| Fin de sesión simulación | `/session-end` |
| Joven — nueva simulación | `/joven/simulacion/nueva` |
| Joven — simulación | `/joven/simulacion/:sessionId` (+ `/preparacion`, `/espera`) |
| Joven — historial, retro, material, notif., cuenta | `/joven/historial`, `/joven/retroalimentacion`, `/joven/material`, `/joven/notificaciones`, `/joven/cuenta` |
| Profesional — dashboard, jóvenes, sesiones, material | `/profesional/dashboard`, `/profesional/jovenes`, `/profesional/sesiones`, `/profesional/material` |
| Profesional — simulación | `/profesional/simulacion/:sessionId` (+ `/preparacion`, `/espera`) |
| Admin | `/admin/dashboard`, `/admin/usuarios`, `/admin/auditoria`, `/admin/profesionales`, `/admin/material` |

---

## 9. Borrador de correo (equipo → David)

**Asunto:** Manual de usuario ELVIR v1

> Hola David,  
>  
> Te compartimos la **versión actualizada del manual de usuario** de ELVIR (`docs/manual-usuario-elvir.md`), pensada para convertirse en un PDF de **unas 10–12 páginas** al incorporar las capturas en `docs/manual-usuario/img/`.  
>  
> Incluye glosario, uso de la barra superior (tema, notificaciones, cierre de sesión), flujo real de la **sala previa** (cargo, escenario, briefing, ingreso), secciones por rol (**joven**, **tutor**, **admin**), FAQ y un apéndice de rutas para soporte.  
>  
> Si necesitas versión **Word** o **Google Docs**, podemos exportar o maquetar en plantilla institucional en el plazo que acordemos.  
>  
> Saludos,  
> [Nombre — ITiSB]

---

*Fin del documento v1.1.*

# ADR 0001: Estrategia de autenticación y almacenamiento de sesión

- **Estado:** Aceptado
- **Fecha:** 2026-03-06

## Contexto

El frontend inicialmente manejaba JWT en storage accesible por JavaScript, lo que elevaba el riesgo de exfiltración de token ante XSS.

## Decisión

Migrar a sesión basada en **cookie HttpOnly** emitida por backend y enviada por el cliente con `withCredentials`.

- Backend (`/auth/login`) establece cookie de acceso (`AUTH_COOKIE_NAME`) con `HttpOnly`.
- Dependencias de auth aceptan token desde `Authorization: Bearer` o cookie de sesión (compatibilidad progresiva).
- Frontend deja de persistir el token y conserva solo el rol para UI/ruteo.

## Consecuencias

### Positivas

- Menor exposición del token a scripts en frontend.
- Compatibilidad progresiva durante migración (header o cookie).
- Menor acoplamiento de UI con detalles del token.

### Negativas

- Requiere mantener y validar estrategia **CSRF** en cambios futuros de auth.
- Debe ajustarse política `SameSite`/`Secure` según entorno y dominio de despliegue.

## Mitigaciones actuales

- Cookie `HttpOnly` en login y limpieza en logout.
- `withCredentials` habilitado en interceptor frontend.
- Protección CSRF reforzada: double-submit (cookie + header), validación de origen y token CSRF firmado ligado al usuario autenticado.
- Cabeceras de hardening HTTP (incluyendo CSP) aplicadas en backend.

## Plan de evolución

- Endurecer estrategia CSRF con pruebas e2e y controles de rotación/revocación según necesidades.
- Definir política estricta de cookies por ambiente (`Secure` y `SameSite`).
- Incorporar pruebas automatizadas de flujo auth/cookies en CI.

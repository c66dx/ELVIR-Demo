# ADR 0002: Estrategia de esquema de base de datos y migraciones

- **Estado:** Parcialmente adoptado
- **Fecha:** 2026-03-05

## Contexto

El backend hoy permite `AUTO_CREATE_TABLES` para facilitar entornos locales. En producción se bloquea por validación de configuración.

## Decisión

Mantener `AUTO_CREATE_TABLES` únicamente para desarrollo local y avanzar a migraciones versionadas como mecanismo oficial de cambios de esquema.

## Consecuencias

### Positivas

- Evita cambios de esquema implícitos en producción.
- Favorece trazabilidad y rollback controlado.

### Negativas

- Requiere disciplina operativa para aplicar migraciones en despliegues.
- Incrementa trabajo inicial de bootstrap de migraciones.

## Estado actual

- `AUTO_CREATE_TABLES` se valida y restringe en producción.
- Falta incorporar toolchain de migraciones versionadas como paso obligatorio de release.

## Plan de evolución

- Introducir Alembic con baseline inicial.
- Definir procedimiento de `upgrade`/`downgrade` por ambiente.
- Integrar verificación de migraciones en CI/CD.

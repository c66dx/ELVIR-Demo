# Contribuir al Frontend ELVIR

Guía breve para mantener el frontend consistente y fácil de revisar.

## Estructura y convenciones

- **Core** (`src/app/core`): servicios, guards, modelos y utilidades compartidas.
- **Features** (`src/app/features`): componentes por rol/feature.
- **Shared** (`src/app/shared`): UI reutilizable, a11y, utils de plantilla.
- **Layout** (`src/app/layout`): shell, sidebar, topbar.

## Rutas y guards

- Rutas principales en `src/app/app.routes.ts`.
- Áreas por rol usan `loadChildren` y guards por rol.
- Si agregas una feature nueva, define rutas en el archivo de la feature y enlázalas desde el `routes` principal.

## HTTP y servicios

- Servicios HTTP por dominio (`AuthApiService`, `YouthApiService`, etc.).
- Evita agregar endpoints en capas que no correspondan al dominio.
- Usa helpers de `api-http-helpers.ts` para `str()` y `withRequestId()` cuando corresponda.

## Tipos compartidos

- Tipos transversales viven en `api-types.ts` o `admin-api.types.ts`.

## Estilo y formato

- Formateo con Prettier:

```bash
npm run format
npm run format:check
```

## Tests

- Prioridad: **servicios + guards + utilidades**.
- Evitar tests de componentes triviales.
- `npm run test:ci` valida cobertura global.

## Checklist antes de subir cambios

1. `npm run lint`
2. `npm run build`
3. `npm run test:ci`

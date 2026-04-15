# Documentación ELVIR

**Autora del repositorio:** Catalina.

Mapa de la carpeta `docs/` y enlaces canónicos. El README en la raíz del repositorio describe el orden de lectura sugerido para nuevos colaboradores.

## Por tema

| Área | Contenido |
|------|-----------|
| **Arquitectura** | [`arquitectura/arquitectura.md`](arquitectura/arquitectura.md) — visión general cliente–servidor y LiveAvatar |
| **Flujos** | [`flujos/flujos.md`](flujos/flujos.md) — recorridos por rol; [`flujos/roles-y-permisos.md`](flujos/roles-y-permisos.md) |
| **Modelo de datos** | [`modelo-datos/modelo_datos.md`](modelo-datos/modelo_datos.md), [`modelo-datos/diccionario_datos.md`](modelo-datos/diccionario_datos.md) |
| **API** | [`api/endpoints.md`](api/endpoints.md) — contratos REST (v1.3); colección Postman en [`api/ELVIR-API.postman_collection.json`](api/ELVIR-API.postman_collection.json) |
| **LiveAvatar** | [`liveavatar/integracion-liveavatar.md`](liveavatar/integracion-liveavatar.md) — **documento canónico** de integración (Context Dinámico) |
| **Deploy** | [`infra/deploy-northflank.md`](infra/deploy-northflank.md) — backend FastAPI en Northflank Sandbox con Supabase + Vercel |
| **Errores** | [`errors.md`](errors.md) — formato de errores y `X-Request-ID` |
| **Decisiones (ADR)** | [`adr/`](adr/) |
| **Propuesta / addendum** | [`propuesta/`](propuesta/) — contexto e hitos del proyecto |

## Material de referencia externo

- **Prompt Builder / Context Dinámico:** material de diseño (zips y carpetas) que puede existir solo en entornos locales; no siempre está en el remoto. Ver [`liveavatar/integracion-liveavatar.md`](liveavatar/integracion-liveavatar.md).

## Changelog local

- `docs/CHANGELOG.md` puede existir solo en entornos locales (según `.gitignore`). Para historial público, usar mensajes de commit o un changelog versionado en Git.

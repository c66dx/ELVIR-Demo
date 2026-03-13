# ADR 0003: Fallback operativo para integración LiveAvatar

- **Estado:** Aceptado
- **Fecha:** 2026-03-05

## Contexto

La plataforma depende de servicios externos (LiveAvatar). En fallas de proveedor, la experiencia de simulación puede degradarse o bloquear flujo.

## Decisión

Adoptar un enfoque de fallback controlado: cuando falle la integración externa, mantener operativos los flujos mínimos de sesión con manejo explícito de errores.

## Consecuencias

### Positivas

- Mayor resiliencia funcional ante fallas externas.
- Mejor experiencia para usuario al recibir errores comprensibles.

### Negativas

- Riesgo de discrepancia funcional entre modo integrado y modo degradado.
- Necesidad de monitoreo para no normalizar estado degradado.

## Criterios operativos

- Registrar errores de integración con `request_id` para trazabilidad.
- Entregar mensajes de error consistentes a frontend.
- Evitar que una falla externa corrompa el estado de sesión.

## Plan de evolución

- Definir SLO/SLA de dependencia externa.
- Añadir métricas de tasa de fallback y alertas operativas.
- Incorporar pruebas de resiliencia de integración en CI.

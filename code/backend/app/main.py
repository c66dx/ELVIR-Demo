"""Aplicación FastAPI ELVIR."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from app.config import settings
from app.core.logging_config import configure_logging

configure_logging(settings)

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import ErrorCode, build_error_payload, get_request_id, localize_email_validation_errors
from app.core.limiter import limiter
from app.core.middleware import (
    audit_log_middleware,
    csrf_protection_middleware,
    get_request_metrics_snapshot,
    request_id_middleware,
    security_headers_middleware,
)
from app.database import engine
from app.models import (  # noqa: F401 - asegurar tablas creadas
    AuditLog,
    Competency,
    CompetencyLevel,
    PlatformSession,
    SessionAudio,
    SessionCompetency,
    SessionTranscript,
)
from app.routers import admin, assignments, auth, catalogs, material, professionals, sessions, summaries, upload, youths
from app.schemas.common import ErrorResponse
from app.schemas.health import (
    HealthLiveResponse,
    HealthMetricsResponse,
    HealthReadyFailure,
    HealthReadyOk,
    HealthSummaryResponse,
    RootMessage,
)

logger = logging.getLogger("elvir.api")

ALERT_ERROR_RATE_THRESHOLD = 0.05
ALERT_MIN_REQUESTS = 20


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "startup env=%s version=%s json_logs=%s log_level=%s",
        settings.ENV,
        app.version,
        settings.use_json_logs,
        settings.LOG_LEVEL,
    )
    if settings.AUTO_CREATE_TABLES:
        logger.warning(
            "AUTO_CREATE_TABLES está deprecado en startup; usa migraciones Alembic (python -m alembic upgrade head)."
        )
    yield
    # limpieza si hace falta


_OPENAPI_DESCRIPTION = """API REST del backend **ELVIR**: simulaciones de entrevistas laborales con jóvenes y profesionales.

**Convenciones:** rutas bajo `/api/v1`. Errores con cuerpo `detail` + `error` (código, mensaje, `request_id`). Cabecera `X-Request-ID` en respuestas.

**Autenticación:** JWT (`Authorization: Bearer`) o cookie HttpOnly tras `POST /api/v1/auth/login`. Las mutaciones con cookie requieren protección CSRF (cabecera configurada + origen permitido)."""

app = FastAPI(
    title="ELVIR API",
    description=_OPENAPI_DESCRIPTION,
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "health",
            "description": "Estado del servicio, métricas internas y probes (liveness / readiness).",
        },
        {
            "name": "auth",
            "description": "Login, cierre de sesión, perfil (`/me`), activación de invitaciones y cambio de credenciales.",
        },
        {
            "name": "catalogs",
            "description": "Catálogos de dominio (roles, casos, plantillas de simulación, etc.) para armar el contexto de sesión.",
        },
        {
            "name": "sessions",
            "description": "Creación y listado de sesiones de simulación, eventos, audio, transcripción y métricas.",
        },
        {
            "name": "summaries",
            "description": "Resúmenes de entrevista asociados a sesiones.",
        },
        {
            "name": "material",
            "description": "Material de apoyo, sugerencias y seguimiento de lectura.",
        },
        {
            "name": "professionals",
            "description": "Perfil y operaciones del profesional vinculado al usuario autenticado.",
        },
        {
            "name": "upload",
            "description": "Subida de ficheros públicos (material, administración) con límites de tamaño y tipo.",
        },
        {
            "name": "assignments",
            "description": "Asignaciones joven–profesional y contexto de trabajo.",
        },
        {
            "name": "youths",
            "description": "Alta, búsqueda y perfil de jóvenes (según rol).",
        },
        {
            "name": "admin",
            "description": "Gestión y auditoría (solo rol **ADMIN**).",
        },
    ],
)
app.state.limiter = limiter


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """429 con el mismo formato que el resto de errores (`detail` + `error`), cabeceras slowapi preservadas."""
    payload = build_error_payload(
        f"Demasiadas solicitudes. {exc.detail}",
        code=ErrorCode.RATE_LIMIT_EXCEEDED,
        request_id=get_request_id(request),
    )
    response = JSONResponse(status_code=429, content=payload)
    response = request.app.state.limiter._inject_headers(response, getattr(request.state, "view_rate_limit", None))
    return _attach_request_id(request, response)


app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-Total-Count",
        "X-Total-Unread",
        "X-Page",
        "X-Page-Size",
        "X-Request-ID",
        "Retry-After",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
    ],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(youths.router, prefix="/api/v1")
app.include_router(catalogs.router, prefix="/api/v1")
app.include_router(sessions.router, prefix="/api/v1")
app.include_router(material.router, prefix="/api/v1")
app.include_router(summaries.router, prefix="/api/v1")
app.include_router(professionals.router, prefix="/api/v1")
app.include_router(upload.router, prefix="/api/v1")
app.include_router(assignments.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")

# Carpeta de archivos subidos
uploads_dir = Path(__file__).resolve().parent.parent / "uploads"
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

app.middleware("http")(request_id_middleware)
app.middleware("http")(security_headers_middleware)
app.middleware("http")(csrf_protection_middleware)
app.middleware("http")(audit_log_middleware)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    error_schema = ErrorResponse.model_json_schema(ref_template="#/components/schemas/{model}")
    definitions = error_schema.pop("$defs", {})
    components = openapi_schema.setdefault("components", {})
    schemas = components.setdefault("schemas", {})
    for name, schema in definitions.items():
        schemas.setdefault(name, schema)
    schemas.setdefault("ErrorResponse", error_schema)
    responses = components.setdefault("responses", {})
    codes_desc = ", ".join(code.value for code in ErrorCode)
    headers = components.setdefault("headers", {})
    headers.setdefault(
        "X-Request-ID",
        {
            "description": "Request identifier for tracing and debugging.",
            "schema": {"type": "string"},
        },
    )
    responses.setdefault(
        "ErrorResponse",
        {
            "description": f"Error estándar de la API. Códigos: {codes_desc}.",
            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}},
            "headers": {"X-Request-ID": {"$ref": "#/components/headers/X-Request-ID"}},
        },
    )
    responses.setdefault(
        "RateLimitExceeded",
        {
            "description": "Demasiadas solicitudes; mismo cuerpo que otros errores (`error.code` = "
            f"{ErrorCode.RATE_LIMIT_EXCEEDED.value}). Cabeceras: DEFAULT_API_RATE_LIMIT, LOGIN_RATE_LIMIT, "
            "ACTIVATE_*_RATE_LIMIT, AUTH_ACCOUNT_CHANGE_RATE_LIMIT, PROFILE_PHOTO_RATE_LIMIT, "
            "STAFF_UPLOAD_RATE_LIMIT, ADMIN_API_RATE_LIMIT.",
            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}},
            "headers": {
                "X-Request-ID": {"$ref": "#/components/headers/X-Request-ID"},
                "Retry-After": {
                    "description": "Tiempo sugerido antes de reintentar (si slowapi inyecta cabeceras).",
                    "schema": {"type": "string"},
                },
                "X-RateLimit-Limit": {"schema": {"type": "string"}},
                "X-RateLimit-Remaining": {"schema": {"type": "string"}},
                "X-RateLimit-Reset": {"schema": {"type": "string"}},
            },
        },
    )
    error_status_codes = ["400", "401", "403", "404", "409", "422", "429", "500"]
    for path_item in openapi_schema.get("paths", {}).values():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if not isinstance(operation, dict):
                continue
            if method.startswith("x-"):
                continue
            responses = operation.setdefault("responses", {})
            for code in error_status_codes:
                if code == "422":
                    responses[code] = {"$ref": "#/components/responses/ErrorResponse"}
                elif code == "429":
                    responses.setdefault(code, {"$ref": "#/components/responses/RateLimitExceeded"})
                else:
                    responses.setdefault(code, {"$ref": "#/components/responses/ErrorResponse"})
            for response in responses.values():
                if not isinstance(response, dict) or "$ref" in response:
                    continue
                response_headers = response.setdefault("headers", {})
                response_headers.setdefault("X-Request-ID", {"$ref": "#/components/headers/X-Request-ID"})
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


def _attach_request_id(request: Request, response: JSONResponse) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    headers = dict(exc.headers) if exc.headers else None
    payload = build_error_payload(exc.detail, code=ErrorCode.HTTP_ERROR, request_id=get_request_id(request))
    response = JSONResponse(status_code=exc.status_code, content=payload, headers=headers)
    return _attach_request_id(request, response)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    detail = localize_email_validation_errors(exc.errors())
    payload = build_error_payload(detail, code=ErrorCode.VALIDATION_ERROR, request_id=get_request_id(request))
    response = JSONResponse(status_code=422, content=payload)
    return _attach_request_id(request, response)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception("request_id=%s unhandled_exception", request_id)
    payload = build_error_payload("Internal Server Error", code=ErrorCode.INTERNAL_SERVER_ERROR, request_id=request_id)
    response = JSONResponse(status_code=500, content=payload)
    return _attach_request_id(request, response)


def _database_ok() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@app.get("/", response_model=RootMessage)
@limiter.exempt
def root():
    return RootMessage(message="ELVIR API", docs="/docs")


@app.get("/health", tags=["health"], response_model=HealthSummaryResponse)
@limiter.exempt
def health():
    """Resumen rápido: servicio arriba (sin comprobar BD)."""
    return HealthSummaryResponse(status="ok", service="elvir-api", version=app.version)


@app.get("/health/metrics", tags=["health"], response_model=HealthMetricsResponse)
@limiter.exempt
def health_metrics():
    """Métricas operativas base para monitoreo y alertas simples."""
    metrics = get_request_metrics_snapshot()
    total = metrics.get("requests_total", 0)
    errors = metrics.get("requests_by_status_bucket:5xx", 0)
    error_rate = (errors / total) if total else 0.0
    alerts = {
        "error_rate_high": total >= ALERT_MIN_REQUESTS and error_rate > ALERT_ERROR_RATE_THRESHOLD,
    }
    return HealthMetricsResponse(
        metrics={
            "requests_total": total,
            "requests_5xx": errors,
            "error_rate_5xx": round(error_rate, 4),
        },
        thresholds={
            "error_rate_5xx": ALERT_ERROR_RATE_THRESHOLD,
            "minimum_requests": ALERT_MIN_REQUESTS,
        },
        alerts=alerts,
    )


@app.get("/health/live", tags=["health"], response_model=HealthLiveResponse)
@limiter.exempt
def health_live():
    """Liveness: el proceso responde (sin BD ni servicios externos). Para probes `livenessProbe`."""
    return HealthLiveResponse()


@app.get(
    "/health/ready",
    tags=["health"],
    response_model=HealthReadyOk,
    responses={
        503: {
            "description": "Base de datos no accesible.",
            "model": HealthReadyFailure,
        }
    },
)
@limiter.exempt
def health_ready():
    """Readiness: base de datos accesible (`SELECT 1`). 503 si no hay conexión. Para probes `readinessProbe`."""
    if _database_ok():
        return HealthReadyOk(status="ok", checks={"database": "ok"})
    return JSONResponse(
        status_code=503,
        content=HealthReadyFailure(status="error", checks={"database": "down"}).model_dump(),
    )

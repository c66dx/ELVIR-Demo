"""Aplicación FastAPI ELVIR."""
from contextlib import asynccontextmanager
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy import text

from app.config import settings
from app.database import engine
from app.core.middleware import (
    request_id_middleware,
    security_headers_middleware,
    csrf_protection_middleware,
    get_request_metrics_snapshot,
    audit_log_middleware,
)
from app.models import (  # noqa: F401 - ensure tables created
    SessionTranscript,
    SessionAudio,
    PlatformSession,
    Competency,
    CompetencyLevel,
    SessionCompetency,
    AuditLog,
)
from app.routers import auth, youths, catalogs, sessions, material, summaries, professionals, upload, assignments, admin

logger = logging.getLogger("elvir.api")

ALERT_ERROR_RATE_THRESHOLD = 0.05
ALERT_MIN_REQUESTS = 20


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.AUTO_CREATE_TABLES:
        logger.warning(
            "AUTO_CREATE_TABLES está deprecado en startup; usa migraciones Alembic (python -m alembic upgrade head)."
        )
    yield
    # cleanup si hace falta


app = FastAPI(
    title="ELVIR API",
    description="API REST del backend ELVIR - Plataforma de simulaciones de entrevistas laborales",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count", "X-Page", "X-Page-Size", "X-Request-ID"],
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


def _attach_request_id(request: Request, response: JSONResponse) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    headers = dict(exc.headers) if exc.headers else None
    response = JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=headers)
    return _attach_request_id(request, response)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    response = JSONResponse(status_code=422, content={"detail": exc.errors()})
    return _attach_request_id(request, response)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception("request_id=%s unhandled_exception", request_id)
    response = JSONResponse(status_code=500, content={"detail": "Internal Server Error"})
    return _attach_request_id(request, response)

@app.get("/")
def root():
    return {"message": "ELVIR API", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}




@app.get("/health/metrics")
def health_metrics():
    """Métricas operativas base para monitoreo y alertas simples."""
    metrics = get_request_metrics_snapshot()
    total = metrics.get("requests_total", 0)
    errors = metrics.get("requests_by_status_bucket:5xx", 0)
    error_rate = (errors / total) if total else 0.0
    alerts = {
        "error_rate_high": total >= ALERT_MIN_REQUESTS and error_rate > ALERT_ERROR_RATE_THRESHOLD,
    }
    return {
        "metrics": {
            "requests_total": total,
            "requests_5xx": errors,
            "error_rate_5xx": round(error_rate, 4),
        },
        "thresholds": {
            "error_rate_5xx": ALERT_ERROR_RATE_THRESHOLD,
            "minimum_requests": ALERT_MIN_REQUESTS,
        },
        "alerts": alerts,
    }


@app.get("/health/live")
def live_health():
    """Healthcheck profundo: valida conectividad con base de datos."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "ok"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "error", "database": "down"})


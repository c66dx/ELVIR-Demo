"""Middlewares HTTP reutilizables de la API."""

from __future__ import annotations

from collections import Counter
import logging
import hmac
from urllib.parse import urlparse
from time import perf_counter
from threading import Lock
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.security import decode_token, decode_csrf_token
from app.database import SessionLocal
from app.models.audit_log import AuditLog

logger = logging.getLogger("elvir.api")

REQUEST_METRICS_LOCK = Lock()
REQUEST_METRICS = Counter()


def _record_request_metric(method: str, path: str, status_code: int):
    bucket = f"{status_code // 100}xx"
    with REQUEST_METRICS_LOCK:
        REQUEST_METRICS["requests_total"] += 1
        REQUEST_METRICS[f"requests_by_status_bucket:{bucket}"] += 1
        REQUEST_METRICS[f"requests_by_method:{method}"] += 1
        REQUEST_METRICS[f"requests_by_path:{path}"] += 1


def get_request_metrics_snapshot() -> dict[str, int]:
    with REQUEST_METRICS_LOCK:
        return dict(REQUEST_METRICS)


def reset_request_metrics():
    with REQUEST_METRICS_LOCK:
        REQUEST_METRICS.clear()


CSRF_EXEMPT_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/activate",
    "/api/v1/auth/activate/validate",
}

AUDIT_EXEMPT_PREFIXES = (
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/uploads",
)


def _should_audit_request(method: str, path: str) -> bool:
    if method in {"GET", "HEAD", "OPTIONS"}:
        return False
    if not path.startswith("/api/"):
        return False
    for prefix in AUDIT_EXEMPT_PREFIXES:
        if path == prefix or path.startswith(prefix + "/"):
            return False
    return True


def _infer_entity_from_path(path: str) -> tuple[str | None, str | None]:
    trimmed = path
    if trimmed.startswith("/api/v1/"):
        trimmed = trimmed[len("/api/v1/"):]
    elif trimmed.startswith("/api/"):
        trimmed = trimmed[len("/api/"):]
    parts = [p for p in trimmed.split("/") if p]
    if not parts:
        return None, None
    if parts[0] == "admin" and len(parts) > 1:
        parts = parts[1:]
    entity = parts[0]
    mapping = {
        "youths": "youth",
        "professionals": "professional",
        "sessions": "session",
        "assignments": "assignment",
        "support-material": "material",
        "materials": "material",
        "summaries": "summary",
        "catalogs": "catalog",
        "auth": "auth",
        "upload": "upload",
    }
    entity_type = mapping.get(entity, entity.rstrip("s"))
    entity_id = None
    if len(parts) > 1 and parts[1].isdigit():
        entity_id = parts[1]
    return entity_type, entity_id


def _infer_action(method: str, path: str) -> str:
    if "/auth/login" in path:
        return "login"
    if "/auth/logout" in path:
        return "logout"
    if "/auth/activate" in path:
        return "activate"
    if method == "POST":
        return "create"
    if method in {"PUT", "PATCH"}:
        return "update"
    if method == "DELETE":
        return "delete"
    return method.lower()


def _extract_client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else None


def _normalize_origin(origin: str | None) -> str | None:
    if not origin:
        return None
    origin = origin.strip().rstrip('/')
    parsed = urlparse(origin)
    if not parsed.scheme or not parsed.netloc:
        return None
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        return None

    host = parsed.hostname
    if not host or parsed.username or parsed.password:
        return None
    try:
        port = parsed.port
    except ValueError:
        return None
    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        return f"{scheme}://{host}"
    if port:
        return f"{scheme}://{host}:{port}"
    return f"{scheme}://{host}"


def _extract_origin_from_referer(referer: str | None) -> str | None:
    return _normalize_origin(referer)


def _is_allowed_origin(origin: str | None) -> bool:
    normalized = _normalize_origin(origin)
    if not normalized:
        return False
    allowed = {
        normalized_allowed
        for o in settings.cors_origins_list
        if (normalized_allowed := _normalize_origin(o))
    }
    return normalized in allowed


async def request_id_middleware(request: Request, call_next):
    """Propaga o genera X-Request-ID, y registra una traza básica por request."""
    request_id = request.headers.get("X-Request-ID") or uuid4().hex
    request.state.request_id = request_id
    start = perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = (perf_counter() - start) * 1000
        logger.exception(
            "request_id=%s method=%s path=%s status=500 duration_ms=%.2f",
            request_id,
            request.method,
            request.url.path,
            elapsed_ms,
        )
        _record_request_metric(request.method, request.url.path, 500)
        raise

    elapsed_ms = (perf_counter() - start) * 1000
    response.headers["X-Request-ID"] = request_id
    _record_request_metric(request.method, request.url.path, response.status_code)
    logger.info(
        "request_id=%s method=%s path=%s status=%s duration_ms=%.2f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


async def security_headers_middleware(request: Request, call_next):
    """Agrega cabeceras base de hardening HTTP a todas las respuestas."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "camera=(), geolocation=(), interest-cohort=()")
    path = request.url.path or ""
    if path.startswith("/docs") or path.startswith("/redoc") or path == "/openapi.json":
        docs_csp = (
            "default-src 'self' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "font-src 'self' data: https://cdn.jsdelivr.net; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; base-uri 'none'"
        )
        response.headers.setdefault("Content-Security-Policy", docs_csp)
    else:
        response.headers.setdefault("Content-Security-Policy", settings.SECURITY_CSP)
    return response


async def csrf_protection_middleware(request: Request, call_next):
    """Aplica validación CSRF para métodos mutables cuando hay sesión por cookie."""
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        if request.url.path in CSRF_EXEMPT_PATHS:
            return await call_next(request)

        auth_cookie = (request.cookies.get(settings.AUTH_COOKIE_NAME) or "").strip()
        if auth_cookie:
            origin = (request.headers.get("Origin") or "").strip()
            referer_origin = _extract_origin_from_referer(request.headers.get("Referer"))
            effective_origin = origin or referer_origin
            if not _is_allowed_origin(effective_origin):
                return JSONResponse(status_code=403, content={"detail": "Origen no permitido"})

            csrf_cookie = (request.cookies.get(settings.CSRF_COOKIE_NAME) or "").strip()
            csrf_header = (request.headers.get(settings.CSRF_HEADER_NAME) or "").strip()
            csrf_match = bool(csrf_cookie and csrf_header) and hmac.compare_digest(csrf_cookie, csrf_header)
            if not csrf_match:
                return JSONResponse(status_code=403, content={"detail": "CSRF token inválido o ausente"})

            csrf_payload = decode_csrf_token(csrf_cookie)
            access_payload = decode_token(auth_cookie)
            if not csrf_payload or not access_payload or csrf_payload.get("sub") != access_payload.get("sub"):
                return JSONResponse(status_code=403, content={"detail": "CSRF token inválido o desalineado"})

    return await call_next(request)


async def audit_log_middleware(request: Request, call_next):
    """Guarda trazabilidad básica de mutaciones en audit_logs."""
    if not _should_audit_request(request.method, request.url.path):
        return await call_next(request)

    response = None
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception as exc:
        status_code = getattr(exc, "status_code", 500)
        raise
    finally:
        db = None
        try:
            db = SessionLocal()
            request_id = getattr(request.state, "request_id", None)
            actor_user_id = getattr(request.state, "user_id", None)
            actor_role = getattr(request.state, "user_role", None)
            entity_type, entity_id = _infer_entity_from_path(request.url.path)
            action = _infer_action(request.method, request.url.path)
            ip_address = _extract_client_ip(request)
            user_agent = request.headers.get("User-Agent")

            log = AuditLog(
                request_id=request_id,
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                status_code=status_code,
                method=request.method,
                path=request.url.path,
                ip_address=ip_address,
                user_agent=user_agent,
                payload={"query": request.url.query} if request.url.query else None,
            )
            db.add(log)
            db.commit()
        except Exception:
            logger.exception("request_id=%s audit_log_failed", getattr(request.state, "request_id", "unknown"))
        finally:
            try:
                if db:
                    db.close()
            except Exception:
                pass


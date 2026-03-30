"""Configuración de logging: texto legible en dev/staging, JSON en producción (una línea por evento)."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from app.config import Settings
from app.core.request_context import current_request_id

_LOGGED_EXTRA_PREFIX = "elvir_"


class RequestIdContextFilter(logging.Filter):
    """Añade `elvir_request_id` al registro si hay petición activa y no vino en `extra`."""

    def filter(self, record: logging.LogRecord) -> bool:
        if getattr(record, "elvir_request_id", None):
            return True
        rid = current_request_id.get()
        if rid:
            setattr(record, "elvir_request_id", rid)
        return True


class ElvirTextFormatter(logging.Formatter):
    """Formatter texto: antepone `request_id=` si el filtro o `extra` lo aportaron."""

    def format(self, record: logging.LogRecord) -> str:
        line = super().format(record)
        rid = getattr(record, "elvir_request_id", None)
        if rid:
            return f"request_id={rid} {line}"
        return line


class JsonLogFormatter(logging.Formatter):
    """Una línea JSON por registro; incluye campos `extra` con prefijo `elvir_` (sin prefijo en salida)."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key.startswith(_LOGGED_EXTRA_PREFIX) and key != "elvir_message":
                out_key = key[len(_LOGGED_EXTRA_PREFIX) :]
                payload[out_key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def _resolve_level(name: str) -> int:
    return getattr(logging, name.upper(), logging.INFO)


def configure_logging(settings: Settings) -> None:
    """Configura el logger raíz `elvir` (y descendientes como `elvir.api`). Idempotente si ya hay handlers."""
    level = _resolve_level(settings.LOG_LEVEL)
    root_elvir = logging.getLogger("elvir")
    root_elvir.setLevel(level)

    if root_elvir.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdContextFilter())
    if settings.use_json_logs:
        handler.setFormatter(JsonLogFormatter())
    else:
        handler.setFormatter(
            ElvirTextFormatter(
                fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
    root_elvir.addHandler(handler)
    root_elvir.propagate = False


def emit_http_access_log(
    logger: logging.Logger,
    settings: Settings,
    *,
    request_id: str,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    error: bool = False,
) -> None:
    """Una entrada de acceso HTTP por petición (texto o JSON según `settings.use_json_logs`)."""
    if settings.use_json_logs:
        extra = {
            "elvir_request_id": request_id,
            "elvir_method": method,
            "elvir_path": path,
            "elvir_status": status_code,
            "elvir_duration_ms": round(duration_ms, 2),
            "elvir_event": "http_request_error" if error else "http_request",
        }
        if error:
            logger.exception("http_request_failed", extra=extra)
        else:
            logger.info("http_request", extra=extra)
        return

    # `request_id` va en el mensaje solo en JSON; en texto lo antepone `ElvirTextFormatter` + contexto.
    msg = f"method={method} path={path} status={status_code} duration_ms={duration_ms:.2f}"
    if error:
        logger.exception(msg)
    else:
        logger.info(msg)

"""Helpers para respuestas de error consistentes."""
from enum import Enum
from typing import Any

from fastapi import Request


class ErrorCode(str, Enum):
    HTTP_ERROR = "HTTP_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    CSRF_FORBIDDEN = "CSRF_FORBIDDEN"


def build_error_payload(
    detail: Any,
    *,
    code: str | ErrorCode | None = None,
    request_id: str | None = None,
) -> dict:
    """Construye payload de error compatible con la API existente (detail) y con metadatos extra."""
    payload: dict = {"detail": detail}
    message = detail if isinstance(detail, str) else "Request error"
    error_obj: dict = {"message": message}
    if code:
        error_obj["code"] = code.value if isinstance(code, ErrorCode) else code
    if request_id:
        error_obj["request_id"] = request_id
    payload["error"] = error_obj
    return payload


def get_request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)

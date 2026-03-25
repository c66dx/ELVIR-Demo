"""Helpers para respuestas de error consistentes."""
from enum import Enum
from typing import Any

from fastapi import Request

_EMAIL_FIELDS = frozenset({"email", "new_email"})


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


def localize_email_validation_errors(errors: list[Any]) -> list[Any]:
    """Pone en español mensajes 422 de Pydantic para campos de correo (suelen venir en inglés)."""
    out: list[Any] = []
    for err in errors:
        if not isinstance(err, dict):
            out.append(err)
            continue
        e = dict(err)
        loc = e.get("loc")
        field = loc[-1] if isinstance(loc, (list, tuple)) and loc else None
        if field not in _EMAIL_FIELDS:
            out.append(e)
            continue
        msg = str(e.get("msg", ""))
        lower = msg.lower()
        err_type = e.get("type")
        if err_type == "missing" or "field required" in lower:
            e["msg"] = "El correo es obligatorio."
        elif any(s in lower for s in ("not a valid email", "email address", "invalid email", "value is not a valid")):
            e["msg"] = "Introduce un correo electrónico válido."
        out.append(e)
    return out

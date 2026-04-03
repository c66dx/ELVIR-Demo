"""Rate limiting con slowapi (por IP en endpoints sensibles)."""

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.config import settings


def get_rate_limit_key(request: Request) -> str:
    """Clave por IP: detrás de proxy de confianza, primer salto de X-Forwarded-For."""
    if settings.RATE_LIMIT_TRUST_X_FORWARDED_FOR:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            first = forwarded.split(",")[0].strip()
            if first:
                return first
    return get_remote_address(request)


limiter = Limiter(
    key_func=get_rate_limit_key,
    default_limits=[settings.DEFAULT_API_RATE_LIMIT],
)

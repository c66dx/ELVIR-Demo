"""Dependencias de FastAPI: auth, current user."""

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import decode_token
from app.database import get_db
from app.models.professional import Professional
from app.models.user import User
from app.models.youth import Youth

security = HTTPBearer(auto_error=False)
MAX_TOKEN_LENGTH = 4096


def _has_inner_whitespace(value: str) -> bool:
    return any(ch.isspace() for ch in value)


def _is_valid_token_candidate(value: str) -> bool:
    return bool(value) and len(value) <= MAX_TOKEN_LENGTH and not _has_inner_whitespace(value)


def _resolve_access_token(request: Request, credentials: HTTPAuthorizationCredentials | None) -> str | None:
    """Resuelve token desde Bearer header o cookie HttpOnly de sesión."""
    if credentials:
        scheme = str(getattr(credentials, "scheme", "") or "").strip().lower()
        if scheme == "bearer":
            raw_token = getattr(credentials, "credentials", "")
            header_token = raw_token.strip() if isinstance(raw_token, str) else ""
            if _is_valid_token_candidate(header_token):
                return header_token
    cookie_token = request.cookies.get(settings.AUTH_COOKIE_NAME)
    cookie_token = cookie_token.strip() if cookie_token else ""
    if not cookie_token:
        return None
    return cookie_token if _is_valid_token_candidate(cookie_token) else None


def get_current_user_id(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> int | None:
    """Obtiene el user_id del token JWT. Retorna None si no hay token."""
    token = _resolve_access_token(request, credentials)
    if not token:
        return None
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        return None
    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        return None
    request.state.user_id = user_id
    return user_id


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Obtiene el usuario actual. 401 si no autenticado."""
    token = _resolve_access_token(request, credentials)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    request.state.user_id = user.id
    request.state.user_role = user.role
    return user


def get_current_professional(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Professional:
    """Obtiene el profesional actual. 403 si no es profesional."""
    prof = db.query(Professional).filter(Professional.user_id == user.id, Professional.is_active == True).first()
    if not prof:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado: se requiere rol profesional"
        )
    return prof


def get_current_youth(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Youth:
    """Obtiene el joven actual. 403 si no es joven."""
    youth = db.query(Youth).filter(Youth.user_id == user.id).first()
    if not youth:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado: se requiere rol joven")
    return youth


def get_current_admin(
    user: User = Depends(get_current_user),
) -> User:
    """Obtiene el usuario actual. 403 si no es Admin."""
    if user.role != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado: se requiere rol Admin")
    return user

"""Dependencias de FastAPI: auth, current user."""
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.professional import Professional
from app.models.youth import Youth
from app.core.security import decode_token

security = HTTPBearer(auto_error=False)


def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[int]:
    """Obtiene el user_id del token JWT. Retorna None si no hay token."""
    if not credentials:
        return None
    payload = decode_token(credentials.credentials)
    if not payload or "sub" not in payload:
        return None
    return int(payload["sub"])


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Obtiene el usuario actual. 401 si no autenticado."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = int(payload["sub"])
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_professional(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Professional:
    """Obtiene el profesional actual. 403 si no es profesional."""
    prof = db.query(Professional).filter(Professional.user_id == user.id, Professional.is_active == True).first()
    if not prof:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado: se requiere rol profesional")
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

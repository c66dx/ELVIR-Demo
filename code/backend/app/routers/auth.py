"""Router de autenticación."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.youth import Youth
from app.models.youth_invitation import YouthInvitation
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    MeResponse,
    ActivateValidateResponse,
    ActivateRequest,
    ActivateResponse,
)
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """Autentica usuario por email/contraseña. Retorna JWT. Rechaza si inactivo o joven sin login_enabled."""
    user = db.query(User).filter(User.email.ilike(data.email)).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario deshabilitado")
    if user.role == "JOVEN":
        youth = db.query(Youth).filter(Youth.user_id == user.id).first()
        if youth and not youth.login_enabled:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="El acceso para este usuario está deshabilitado",
            )
    token = create_access_token(data={"sub": str(user.id), "role": user.role})
    return LoginResponse(access_token=token, role=user.role, user_id=user.id)


@router.get("/me", response_model=MeResponse)
def get_me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Retorna datos del usuario autenticado (user_id, role, email, professional_id/youth_id si aplica)."""
    professional_id = None
    youth_id = None
    if user.role == "PROFESIONAL":
        from app.models.professional import Professional
        prof = db.query(Professional).filter(Professional.user_id == user.id).first()
        if prof:
            professional_id = prof.id
    elif user.role == "JOVEN":
        youth = db.query(Youth).filter(Youth.user_id == user.id).first()
        if youth:
            youth_id = youth.id
    return MeResponse(user_id=user.id, role=user.role, email=user.email, professional_id=professional_id, youth_id=youth_id)


@router.get("/activate/validate", response_model=ActivateValidateResponse)
def validate_activation_token(token: str, db: Session = Depends(get_db)):
    """Valida token de invitación: existe, no usado, no expirado. Para mostrar formulario de activación."""
    inv = db.query(YouthInvitation).filter(YouthInvitation.token == token).first()
    if not inv:
        return ActivateValidateResponse(valid=False, error="TOKEN_NOT_FOUND")
    if inv.used_at:
        return ActivateValidateResponse(valid=False, error="TOKEN_USED")
    if inv.expires_at < datetime.now(timezone.utc):
        return ActivateValidateResponse(valid=False, error="TOKEN_EXPIRED")
    youth = db.query(Youth).filter(Youth.id == inv.youth_id).first()
    return ActivateValidateResponse(
        valid=True,
        email=inv.email,
        display_name=youth.display_name if youth else None,
    )


@router.post("/activate", response_model=ActivateResponse)
def activate_account(data: ActivateRequest, db: Session = Depends(get_db)):
    """Activa cuenta del joven: crea USERS, vincula YOUTH, invalida invitación. Requiere token válido."""
    inv = db.query(YouthInvitation).filter(YouthInvitation.token == data.token).first()
    if not inv:
        return ActivateResponse(success=False, error="TOKEN_NOT_FOUND")
    if inv.used_at:
        return ActivateResponse(success=False, error="TOKEN_USED")
    if inv.expires_at < datetime.now(timezone.utc):
        return ActivateResponse(success=False, error="TOKEN_EXPIRED")
    existing = db.query(User).filter(User.email.ilike(inv.email)).first()
    if existing:
        return ActivateResponse(success=False, error="EMAIL_ALREADY_EXISTS")
    user = User(
        email=inv.email.lower(),
        password_hash=get_password_hash(data.password),
        role="JOVEN",
        is_active=True,
    )
    db.add(user)
    db.flush()
    youth = db.query(Youth).filter(Youth.id == inv.youth_id).first()
    if youth:
        youth.user_id = user.id
    inv.used_at = datetime.now(timezone.utc)
    db.commit()
    return ActivateResponse(success=True, message="Cuenta activada. Ya puedes iniciar sesión.")

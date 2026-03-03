"""Router de autenticación."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.youth import Youth
from app.models.youth_invitation import YouthInvitation
from app.models.platform_session import PlatformSession
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    MeResponse,
    ActivateValidateResponse,
    ActivateRequest,
    ActivateResponse,
    ChangePasswordRequest,
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
    db.add(PlatformSession(user_id=user.id))
    db.commit()
    return LoginResponse(access_token=token, role=user.role, user_id=user.id)


@router.post("/logout")
def logout(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Registra cierre de sesión en plataforma (para métricas)."""
    from sqlalchemy import desc
    active = (
        db.query(PlatformSession)
        .filter(PlatformSession.user_id == user.id, PlatformSession.ended_at.is_(None))
        .order_by(desc(PlatformSession.started_at))
        .first()
    )
    if active:
        active.ended_at = datetime.now(timezone.utc)
        db.commit()
    return {"ok": True}


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
    is_change_email = youth is not None and youth.user_id is not None
    return ActivateValidateResponse(
        valid=True,
        email=inv.email,
        display_name=youth.display_name if youth else None,
        is_change_email=is_change_email,
    )


@router.post("/activate", response_model=ActivateResponse)
def activate_account(data: ActivateRequest, db: Session = Depends(get_db)):
    """Activa cuenta del joven: crea USERS, vincula YOUTH, invalida invitación.
    Si el joven ya tiene user_id (cambio de email), actualiza User.email y password."""
    inv = db.query(YouthInvitation).filter(YouthInvitation.token == data.token).first()
    if not inv:
        return ActivateResponse(success=False, error="TOKEN_NOT_FOUND")
    if inv.used_at:
        return ActivateResponse(success=False, error="TOKEN_USED")
    if inv.expires_at < datetime.now(timezone.utc):
        return ActivateResponse(success=False, error="TOKEN_EXPIRED")
    youth = db.query(Youth).filter(Youth.id == inv.youth_id).first()
    if youth and youth.user_id:
        user = db.query(User).filter(User.id == youth.user_id).first()
        if user:
            if not data.current_password or not data.current_password.strip():
                return ActivateResponse(success=False, error="CURRENT_PASSWORD_REQUIRED")
            if not verify_password(data.current_password, user.password_hash):
                return ActivateResponse(success=False, error="CURRENT_PASSWORD_INVALID")
            existing = db.query(User).filter(User.email.ilike(inv.email)).first()
            if existing and existing.id != user.id:
                return ActivateResponse(success=False, error="EMAIL_ALREADY_EXISTS")
            user.email = inv.email.lower()
            if data.password and data.password.strip():
                user.password_hash = get_password_hash(data.password)
            inv.used_at = datetime.now(timezone.utc)
            db.commit()
            return ActivateResponse(success=True, message="Email actualizado. Ya puedes iniciar sesión.")
    if not data.password or not data.password.strip():
        return ActivateResponse(success=False, error="PASSWORD_REQUIRED")
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
    if youth:
        youth.user_id = user.id
    inv.used_at = datetime.now(timezone.utc)
    db.commit()
    return ActivateResponse(success=True, message="Cuenta activada. Ya puedes iniciar sesión.")


@router.post("/change-password")
def change_password(
    data: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cambia la contraseña del usuario autenticado (joven o profesional). Requiere contraseña actual."""
    if len(data.new_password) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La nueva contraseña debe tener al menos 6 caracteres")
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contraseña actual incorrecta")
    user.password_hash = get_password_hash(data.new_password)
    db.commit()
    return {"success": True, "message": "Contraseña actualizada correctamente"}

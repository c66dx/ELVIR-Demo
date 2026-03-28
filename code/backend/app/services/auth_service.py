"""Lógica de login, sesión de plataforma, activación y cambio de credenciales."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Response, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import (
    create_access_token,
    create_csrf_token,
    get_password_hash,
    verify_password,
)
from app.models.platform_session import PlatformSession
from app.models.professional import Professional
from app.models.professional_invitation import ProfessionalInvitation
from app.models.user import User
from app.models.youth import Youth
from app.models.youth_invitation import YouthInvitation
from app.schemas.auth import (
    ActivateRequest,
    ActivateResponse,
    ActivateValidateResponse,
    ChangeEmailRequest,
    ChangeEmailResponse,
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    MeResponse,
)


def _expires_at_utc(dt: datetime) -> datetime:
    """SQLite puede devolver datetimes naive; normaliza a UTC para comparar con now."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def set_session_cookies(response: Response, token: str, csrf_token: str) -> None:
    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.is_production,
        samesite="none" if settings.is_production else "lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        secure=settings.is_production,
        samesite="none" if settings.is_production else "lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )


def clear_session_cookies(response: Response) -> None:
    response.delete_cookie(key=settings.AUTH_COOKIE_NAME, path="/")
    response.delete_cookie(key=settings.CSRF_COOKIE_NAME, path="/")


def login_user(db: Session, data: LoginRequest) -> tuple[LoginResponse, str]:
    """Autentica, registra platform_session y devuelve respuesta + CSRF para cookies."""
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
    csrf_token = create_csrf_token(subject=str(user.id))
    db.add(PlatformSession(user_id=user.id))
    db.commit()
    return (
        LoginResponse(access_token=token, role=user.role, user_id=user.id),
        csrf_token,
    )


def end_active_platform_session(db: Session, user: User) -> None:
    active = (
        db.query(PlatformSession)
        .filter(PlatformSession.user_id == user.id, PlatformSession.ended_at.is_(None))
        .order_by(desc(PlatformSession.started_at))
        .first()
    )
    if active:
        active.ended_at = datetime.now(timezone.utc)
        db.commit()


def build_me_response(db: Session, user: User) -> MeResponse:
    professional_id = None
    youth_id = None
    if user.role == "PROFESIONAL":
        prof = db.query(Professional).filter(Professional.user_id == user.id).first()
        if prof:
            professional_id = prof.id
    elif user.role == "JOVEN":
        youth = db.query(Youth).filter(Youth.user_id == user.id).first()
        if youth:
            youth_id = youth.id
    return MeResponse(
        user_id=user.id,
        role=user.role,
        email=user.email,
        profile_photo_url=user.profile_photo_url,
        professional_id=professional_id,
        youth_id=youth_id,
    )


def validate_activation_token(db: Session, token: str) -> ActivateValidateResponse:
    now = datetime.now(timezone.utc)
    inv = db.query(YouthInvitation).filter(YouthInvitation.token == token).first()
    if inv:
        if inv.used_at:
            return ActivateValidateResponse(valid=False, error="TOKEN_USED")
        if _expires_at_utc(inv.expires_at) < now:
            return ActivateValidateResponse(valid=False, error="TOKEN_EXPIRED")
        youth = db.query(Youth).filter(Youth.id == inv.youth_id).first()
        is_change_email = youth is not None and youth.user_id is not None
        if youth and youth.user_id:
            linked = db.query(User).filter(User.id == youth.user_id).first()
            if linked and not linked.is_active:
                is_change_email = False
        return ActivateValidateResponse(
            valid=True,
            email=inv.email,
            display_name=youth.display_name if youth else None,
            is_change_email=is_change_email,
        )

    prof_inv = db.query(ProfessionalInvitation).filter(ProfessionalInvitation.token == token).first()
    if not prof_inv:
        return ActivateValidateResponse(valid=False, error="TOKEN_NOT_FOUND")
    if prof_inv.used_at:
        return ActivateValidateResponse(valid=False, error="TOKEN_USED")
    if _expires_at_utc(prof_inv.expires_at) < now:
        return ActivateValidateResponse(valid=False, error="TOKEN_EXPIRED")
    prof = db.query(Professional).filter(Professional.id == prof_inv.professional_id).first()
    is_change_email = False
    if prof and prof.user_id:
        linked_user = db.query(User).filter(User.id == prof.user_id).first()
        if linked_user and linked_user.is_active:
            is_change_email = True
    return ActivateValidateResponse(
        valid=True,
        email=prof_inv.email,
        display_name=prof.display_name if prof else None,
        is_change_email=is_change_email,
    )


def activate_account(db: Session, data: ActivateRequest) -> ActivateResponse:
    now = datetime.now(timezone.utc)
    inv = db.query(YouthInvitation).filter(YouthInvitation.token == data.token).first()
    if inv:
        if inv.used_at:
            return ActivateResponse(success=False, error="TOKEN_USED")
        if _expires_at_utc(inv.expires_at) < now:
            return ActivateResponse(success=False, error="TOKEN_EXPIRED")
        youth = db.query(Youth).filter(Youth.id == inv.youth_id).first()
        if youth and youth.user_id:
            user = db.query(User).filter(User.id == youth.user_id).first()
            if user:
                if user.is_active:
                    if not data.current_password or not data.current_password.strip():
                        return ActivateResponse(success=False, error="CURRENT_PASSWORD_REQUIRED")
                    if not verify_password(data.current_password, user.password_hash):
                        return ActivateResponse(success=False, error="CURRENT_PASSWORD_INVALID")
                else:
                    if not data.password or not data.password.strip():
                        return ActivateResponse(success=False, error="PASSWORD_REQUIRED")
                existing = db.query(User).filter(User.email.ilike(inv.email)).first()
                if existing and existing.id != user.id:
                    return ActivateResponse(success=False, error="EMAIL_ALREADY_EXISTS")
                user.email = inv.email.lower()
                if data.password and data.password.strip():
                    user.password_hash = get_password_hash(data.password)
                if not user.is_active:
                    user.is_active = True
                inv.used_at = now
                db.commit()
                return ActivateResponse(success=True, message="Correo actualizado. Ya puedes iniciar sesión.")
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
        inv.used_at = now
        db.commit()
        return ActivateResponse(success=True, message="Cuenta activada. Ya puedes iniciar sesión.")

    prof_inv = db.query(ProfessionalInvitation).filter(ProfessionalInvitation.token == data.token).first()
    if not prof_inv:
        return ActivateResponse(success=False, error="TOKEN_NOT_FOUND")
    if prof_inv.used_at:
        return ActivateResponse(success=False, error="TOKEN_USED")
    if _expires_at_utc(prof_inv.expires_at) < now:
        return ActivateResponse(success=False, error="TOKEN_EXPIRED")

    prof = db.query(Professional).filter(Professional.id == prof_inv.professional_id).first()
    if not prof:
        return ActivateResponse(success=False, error="TOKEN_NOT_FOUND")

    user = db.query(User).filter(User.id == prof.user_id).first() if prof.user_id else None
    is_change_email = user is not None and user.is_active
    if is_change_email:
        if not data.current_password or not data.current_password.strip():
            return ActivateResponse(success=False, error="CURRENT_PASSWORD_REQUIRED")
        if not verify_password(data.current_password, user.password_hash):
            return ActivateResponse(success=False, error="CURRENT_PASSWORD_INVALID")
        existing = db.query(User).filter(User.email.ilike(prof_inv.email)).first()
        if existing and existing.id != user.id:
            return ActivateResponse(success=False, error="EMAIL_ALREADY_EXISTS")
        user.email = prof_inv.email.lower()
        if data.password and data.password.strip():
            user.password_hash = get_password_hash(data.password)
        prof_inv.used_at = now
        db.commit()
        return ActivateResponse(success=True, message="Correo actualizado. Ya puedes iniciar sesión.")

    if not data.password or not data.password.strip():
        return ActivateResponse(success=False, error="PASSWORD_REQUIRED")
    if user is None:
        existing = db.query(User).filter(User.email.ilike(prof_inv.email)).first()
        if existing:
            return ActivateResponse(success=False, error="EMAIL_ALREADY_EXISTS")
        user = User(
            email=prof_inv.email.lower(),
            password_hash=get_password_hash(data.password),
            role="PROFESIONAL",
            is_active=True,
        )
        db.add(user)
        db.flush()
        prof.user_id = user.id
    else:
        existing = db.query(User).filter(User.email.ilike(prof_inv.email)).first()
        if existing and existing.id != user.id:
            return ActivateResponse(success=False, error="EMAIL_ALREADY_EXISTS")
        user.email = prof_inv.email.lower()
        user.password_hash = get_password_hash(data.password)
        user.is_active = True

    prof_inv.used_at = now
    db.commit()
    return ActivateResponse(success=True, message="Cuenta activada. Ya puedes iniciar sesión.")


def change_password(db: Session, user: User, data: ChangePasswordRequest) -> dict:
    if len(data.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La nueva contraseña debe tener al menos 6 caracteres",
        )
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contraseña actual incorrecta")
    user.password_hash = get_password_hash(data.new_password)
    db.commit()
    return {"success": True, "message": "Contraseña actualizada correctamente"}


def request_email_change(db: Session, user: User, data: ChangeEmailRequest) -> ChangeEmailResponse:
    if user.role not in ("JOVEN", "PROFESIONAL"):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Contraseña actual incorrecta")

    new_email = data.new_email.lower().strip()
    if not new_email:
        raise HTTPException(status_code=400, detail="Correo inválido")
    if user.email.lower() == new_email:
        raise HTTPException(status_code=400, detail="El correo ya es el actual")
    existing = db.query(User).filter(User.email.ilike(new_email)).first()
    if existing and existing.id != user.id:
        raise HTTPException(status_code=409, detail="El correo ya está registrado")

    now = datetime.now(timezone.utc)
    token = str(uuid.uuid4())
    expires = now + timedelta(days=7)
    if user.role == "JOVEN":
        youth = db.query(Youth).filter(Youth.user_id == user.id).first()
        if not youth:
            raise HTTPException(status_code=404, detail="Joven no encontrado")
        if not youth.login_enabled:
            raise HTTPException(status_code=400, detail="El joven no tiene login habilitado")
        (
            db.query(YouthInvitation)
            .filter(YouthInvitation.youth_id == youth.id, YouthInvitation.used_at.is_(None))
            .update({"used_at": now}, synchronize_session=False)
        )
        db.add(YouthInvitation(youth_id=youth.id, email=new_email, token=token, expires_at=expires))
    else:
        prof = db.query(Professional).filter(Professional.user_id == user.id).first()
        if not prof:
            raise HTTPException(status_code=404, detail="Profesional no encontrado")
        (
            db.query(ProfessionalInvitation)
            .filter(ProfessionalInvitation.professional_id == prof.id, ProfessionalInvitation.used_at.is_(None))
            .update({"used_at": now}, synchronize_session=False)
        )
        db.add(ProfessionalInvitation(professional_id=prof.id, email=new_email, token=token, expires_at=expires))
    activation_url = f"{settings.APP_BASE_URL}/activar?token={token}"
    db.commit()
    return ChangeEmailResponse(
        success=True,
        message="Se generó un enlace de confirmación para cambiar el correo.",
        activation_url=activation_url,
    )

"""Router de autenticación."""
from fastapi import APIRouter, Depends, Request, Response, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    MeResponse,
    ActivateValidateResponse,
    ActivateRequest,
    ActivateResponse,
    ChangePasswordRequest,
    ChangeEmailRequest,
    ChangeEmailResponse,
)
from app.core.dependencies import get_current_user
from app.services.profile_photo import persist_profile_photo_upload
from app.services.auth_service import (
    activate_account,
    build_me_response,
    change_password,
    clear_session_cookies,
    end_active_platform_session,
    login_user,
    request_email_change,
    set_session_cookies,
    validate_activation_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """Autentica usuario por email/contraseña. Retorna JWT. Rechaza si inactivo o joven sin login_enabled."""
    body, csrf_token = login_user(db, data)
    set_session_cookies(response, body.access_token, csrf_token)
    return body


@router.post("/logout")
def logout(response: Response, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Registra cierre de sesión en plataforma (para métricas)."""
    end_active_platform_session(db, user)
    clear_session_cookies(response)
    return {"ok": True}


@router.get("/me", response_model=MeResponse)
def get_me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Retorna datos del usuario autenticado (user_id, role, email, professional_id/youth_id si aplica)."""
    return build_me_response(db, user)


@router.get("/activate/validate", response_model=ActivateValidateResponse)
def validate_activation_token_endpoint(token: str, db: Session = Depends(get_db)):
    """Valida token de invitación: existe, no usado, no expirado. Para mostrar formulario de activación."""
    return validate_activation_token(db, token)


@router.post("/activate", response_model=ActivateResponse)
def activate_account_endpoint(data: ActivateRequest, db: Session = Depends(get_db)):
    """Activa cuenta del joven o del profesional.
    Para jóvenes: crea USERS, vincula YOUTH, invalida invitación.
    Para profesionales: activa el usuario y asigna contraseña."""
    return activate_account(db, data)


@router.post("/change-password")
def change_password_endpoint(
    data: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cambia la contraseña del usuario autenticado (joven o profesional). Requiere contraseña actual."""
    return change_password(db, user, data)


@router.post("/change-email", response_model=ChangeEmailResponse)
def change_email(
    data: ChangeEmailRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Solicita cambio de email para usuario autenticado (joven o profesional). Genera invitación y devuelve activation_url."""
    return request_email_change(db, user, data)


@router.post("/me/photo")
def upload_profile_photo(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sube foto de perfil del usuario autenticado."""
    base = f"{request.url.scheme}://{request.url.netloc}".rstrip("/")
    url = persist_profile_photo_upload(db, user, file, base)
    return {"url": url}

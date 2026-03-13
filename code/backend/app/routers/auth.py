"""Router de autenticación."""
from datetime import datetime, timezone, timedelta
from pathlib import Path
import uuid
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, HTTPException, Response, status, UploadFile, File, Request
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
    ChangeEmailRequest,
    ChangeEmailResponse,
)
from app.core.security import verify_password, get_password_hash, create_access_token, create_csrf_token
from app.config import settings
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

PROFILE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
PROFILE_MAX_MB = 5
PROFILE_MAX_BYTES = PROFILE_MAX_MB * 1024 * 1024
PROFILE_CHUNK_SIZE = 1024 * 1024
PROFILE_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "profiles"


def _ensure_profile_dir():
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)


def _save_profile_stream(file: UploadFile, destination: Path) -> None:
    total_written = 0
    with destination.open("wb") as out:
        while True:
            chunk = file.file.read(PROFILE_CHUNK_SIZE)
            if not chunk:
                break
            total_written += len(chunk)
            if total_written > PROFILE_MAX_BYTES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Imagen demasiado grande. Máximo: {PROFILE_MAX_MB} MB",
                )
            out.write(chunk)


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, response: Response, db: Session = Depends(get_db)):
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
    csrf_token = create_csrf_token(subject=str(user.id))
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
    db.add(PlatformSession(user_id=user.id))
    db.commit()
    return LoginResponse(access_token=token, role=user.role, user_id=user.id)


@router.post("/logout")
def logout(response: Response, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
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
    response.delete_cookie(key=settings.AUTH_COOKIE_NAME, path="/")
    response.delete_cookie(key=settings.CSRF_COOKIE_NAME, path="/")
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
    return MeResponse(
        user_id=user.id,
        role=user.role,
        email=user.email,
        profile_photo_url=user.profile_photo_url,
        professional_id=professional_id,
        youth_id=youth_id,
    )


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
    if youth and youth.user_id:
        user = db.query(User).filter(User.id == youth.user_id).first()
        if user and not user.is_active:
            is_change_email = False
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


@router.post("/change-email", response_model=ChangeEmailResponse)
def change_email(
    data: ChangeEmailRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Solicita cambio de email para joven autenticado. Genera invitación y devuelve activation_url."""
    if user.role != "JOVEN":
        raise HTTPException(status_code=403, detail="Acceso denegado")
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Contraseña actual incorrecta")
    youth = db.query(Youth).filter(Youth.user_id == user.id).first()
    if not youth:
        raise HTTPException(status_code=404, detail="Joven no encontrado")
    if not youth.login_enabled:
        raise HTTPException(status_code=400, detail="El joven no tiene login habilitado")

    new_email = data.new_email.lower().strip()
    if not new_email:
        raise HTTPException(status_code=400, detail="Email inválido")
    if user.email.lower() == new_email:
        raise HTTPException(status_code=400, detail="El email ya es el actual")
    existing = db.query(User).filter(User.email.ilike(new_email)).first()
    if existing and existing.id != user.id:
        raise HTTPException(status_code=409, detail="El email ya está registrado")

    now = datetime.now(timezone.utc)
    (
        db.query(YouthInvitation)
        .filter(YouthInvitation.youth_id == youth.id, YouthInvitation.used_at.is_(None))
        .update({"used_at": now}, synchronize_session=False)
    )
    token = str(uuid.uuid4())
    expires = now + timedelta(days=7)
    db.add(YouthInvitation(youth_id=youth.id, email=new_email, token=token, expires_at=expires))
    activation_url = f"{settings.APP_BASE_URL}/activar?token={token}"
    db.commit()
    return ChangeEmailResponse(
        success=True,
        message="Se generó un enlace de confirmación para cambiar el email.",
        activation_url=activation_url,
    )


@router.post("/me/photo")
def upload_profile_photo(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sube foto de perfil del usuario autenticado."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo vacío")
    ext = Path(file.filename).suffix.lower()
    if ext not in PROFILE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Extensión no permitida. Permitidas: {', '.join(sorted(PROFILE_EXTENSIONS))}",
        )

    _ensure_profile_dir()
    unique_name = f"profile_{user.id}_{uuid.uuid4().hex}{ext}"
    file_path = PROFILE_DIR / unique_name
    try:
        _save_profile_stream(file, file_path)
    except HTTPException:
        if file_path.exists():
            file_path.unlink(missing_ok=True)
        raise
    except OSError as e:
        if file_path.exists():
            file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Error al guardar archivo: {str(e)}")
    finally:
        file.file.close()

    # Limpia foto anterior si está en /uploads/profiles
    if user.profile_photo_url:
        try:
            parsed = urlparse(user.profile_photo_url)
            old_path = parsed.path or ""
            if old_path.startswith("/uploads/profiles/"):
                old_name = old_path.replace("/uploads/profiles/", "", 1)
                old_file = PROFILE_DIR / old_name
                if old_file.exists():
                    old_file.unlink(missing_ok=True)
        except Exception:
            pass

    base = f"{request.url.scheme}://{request.url.netloc}".rstrip("/")
    user.profile_photo_url = f"{base}/uploads/profiles/{unique_name}"
    db.commit()
    return {"url": user.profile_photo_url}


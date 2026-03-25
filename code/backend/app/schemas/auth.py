"""Esquemas de autenticación."""
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    role: str
    user_id: int


class MeResponse(BaseModel):
    user_id: int
    role: str
    email: EmailStr
    profile_photo_url: str | None = None
    professional_id: int | None = None  # Solo cuando role=PROFESIONAL
    youth_id: int | None = None  # Solo cuando role=JOVEN


class ActivateValidateResponse(BaseModel):
    valid: bool
    email: EmailStr | None = None
    display_name: str | None = None
    error: str | None = None
    is_change_email: bool = False  # Verdadero cuando el usuario ya tiene cuenta (cambio de correo)


class ActivateRequest(BaseModel):
    token: str
    password: str | None = None  # Nueva contraseña (obligatoria en primera activación, opcional en cambio de correo)
    current_password: str | None = None  # Contraseña actual (obligatoria solo en cambio de correo)


class ActivateResponse(BaseModel):
    success: bool
    message: str | None = None
    error: str | None = None  # Usado por la interfaz cuando success=False


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class ChangeEmailRequest(BaseModel):
    new_email: EmailStr
    current_password: str


class ChangeEmailResponse(BaseModel):
    success: bool
    message: str | None = None
    activation_url: str | None = None


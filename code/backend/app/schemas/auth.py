"""Esquemas de autenticación."""
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    role: str
    user_id: int


class MeResponse(BaseModel):
    user_id: int
    role: str
    email: str
    professional_id: int | None = None  # Solo cuando role=PROFESIONAL
    youth_id: int | None = None  # Solo cuando role=JOVEN


class ActivateValidateResponse(BaseModel):
    valid: bool
    email: str | None = None
    display_name: str | None = None
    error: str | None = None
    is_change_email: bool = False  # True cuando el joven ya tiene cuenta (cambio de correo)


class ActivateRequest(BaseModel):
    token: str
    password: str | None = None  # Nueva contraseña (obligatoria en primera activación, opcional en cambio de correo)
    current_password: str | None = None  # Contraseña actual (obligatoria solo en cambio de correo)


class ActivateResponse(BaseModel):
    success: bool
    message: str | None = None
    error: str | None = None  # Usado por frontend cuando success=False


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

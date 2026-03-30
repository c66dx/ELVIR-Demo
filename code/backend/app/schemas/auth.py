"""Esquemas de autenticación."""

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=2000)


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
    token: str = Field(..., min_length=1, max_length=500)
    password: str | None = Field(
        None,
        max_length=2000,
    )  # Nueva contraseña (obligatoria en primera activación, opcional en cambio de correo)
    current_password: str | None = Field(None, max_length=2000)  # Contraseña actual (cambio de correo)


class ActivateResponse(BaseModel):
    success: bool
    message: str | None = None
    error: str | None = None  # Usado por la interfaz cuando success=False


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=2000)
    new_password: str = Field(..., min_length=1, max_length=2000)


class ChangeEmailRequest(BaseModel):
    new_email: EmailStr
    current_password: str = Field(..., min_length=1, max_length=2000)


class ChangeEmailResponse(BaseModel):
    success: bool
    message: str | None = None
    activation_url: str | None = None

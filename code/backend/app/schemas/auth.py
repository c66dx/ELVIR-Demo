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


class ActivateRequest(BaseModel):
    token: str
    password: str


class ActivateResponse(BaseModel):
    success: bool
    message: str | None = None
    error: str | None = None  # Usado por frontend cuando success=False

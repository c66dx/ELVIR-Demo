"""Esquemas de jóvenes."""
import json
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, model_validator, EmailStr


class YouthBase(BaseModel):
    display_name: str
    rut: Optional[str] = None
    phone: Optional[str] = None
    year_of_birth: Optional[int] = None
    diagnosis: Optional[str] = None
    login_enabled: bool = False
    general_notes: Optional[str] = None
    profile_checklist: Optional[list[str]] = None


class YouthCreate(YouthBase):
    """El identificador lo genera el sistema (JOV-001, JOV-002, ...)."""
    email: Optional[EmailStr] = None

    @model_validator(mode="after")
    def email_required_if_login(self):
        if self.login_enabled and not self.email:
            raise ValueError("El correo es obligatorio cuando el inicio de sesión está habilitado")
        return self


class YouthUpdate(BaseModel):
    display_name: Optional[str] = None
    # identificador no es editable
    rut: Optional[str] = None
    phone: Optional[str] = None
    year_of_birth: Optional[int] = None
    diagnosis: Optional[str] = None
    login_enabled: Optional[bool] = None
    general_notes: Optional[str] = None
    profile_checklist: Optional[list[str]] = None
    email: Optional[EmailStr] = None


class YouthChangeEmailRequest(BaseModel):
    new_email: EmailStr


def parse_profile_checklist(val) -> list[str]:
    """Convierte profile_checklist desde BD (JSON string) a lista de strings."""
    if val is None:
        return []
    if isinstance(val, list):
        return [str(x) for x in val if x]
    if isinstance(val, str):
        try:
            parsed = json.loads(val)
            return [str(x) for x in parsed] if isinstance(parsed, list) else []
        except (json.JSONDecodeError, TypeError):
            return []
    return []


class YouthResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    display_name: str
    identifier: Optional[str] = None
    rut: Optional[str] = None
    email: Optional[str] = None  # del usuario cuando tiene user_id
    profile_photo_url: Optional[str] = None
    phone: Optional[str] = None
    year_of_birth: Optional[int] = None
    diagnosis: Optional[str] = None
    login_enabled: bool
    is_active: bool
    general_notes: Optional[str] = None
    profile_checklist: Optional[list[str]] = None
    activation_url: Optional[str] = None

    class Config:
        from_attributes = True


class LastSessionInfo(BaseModel):
    id: int
    started_at: datetime
    status: str
    ended_at: Optional[datetime] = None


class YouthWithLastSession(YouthResponse):
    status_label: Optional[str] = None
    last_session: Optional[LastSessionInfo] = None


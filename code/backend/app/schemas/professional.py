"""Esquemas Pydantic del recurso profesionales."""
from datetime import datetime

from pydantic import BaseModel, field_validator


class ProfessionalResponse(BaseModel):
    id: int
    user_id: int
    display_name: str
    specialty: str | None
    institution: str | None
    profile_photo_url: str | None = None
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProfessionalCreateResponse(ProfessionalResponse):
    activation_url: str | None = None


class ProfessionalUpdate(BaseModel):
    display_name: str
    specialty: str | None = None
    institution: str | None = None
    is_active: bool | None = None


class ProfessionalCreate(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def email_format(cls, v: str) -> str:
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Formato de correo inválido")
        return v.lower()

    display_name: str
    specialty: str | None = None
    institution: str | None = None

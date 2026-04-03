"""Esquemas Pydantic del recurso profesionales."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


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
    display_name: str = Field(..., min_length=1, max_length=255)
    specialty: str | None = Field(None, max_length=255)
    institution: str | None = Field(None, max_length=255)
    is_active: bool | None = None

    @field_validator("display_name")
    @classmethod
    def display_name_strip(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("El nombre para mostrar es obligatorio")
        return s

    @field_validator("specialty", "institution")
    @classmethod
    def optional_strip(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        return s or None


class ProfessionalCreate(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def email_format(cls, v: str) -> str:
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Formato de correo inválido")
        return v.lower()

    display_name: str = Field(..., min_length=1, max_length=255)
    specialty: str | None = Field(None, max_length=255)
    institution: str | None = Field(None, max_length=255)

    @field_validator("display_name")
    @classmethod
    def display_name_strip(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("El nombre para mostrar es obligatorio")
        return s

    @field_validator("specialty", "institution")
    @classmethod
    def optional_strip(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        return s or None

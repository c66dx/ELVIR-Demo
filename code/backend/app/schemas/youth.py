"""Esquemas de jóvenes."""

import json
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

_MAX_NOTES = 50_000
_MAX_CHECKLIST_ITEMS = 40
_MAX_CHECKLIST_ITEM_LEN = 100


class YouthBase(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=255)
    rut: str | None = Field(None, max_length=20)
    phone: str | None = Field(None, max_length=50)
    year_of_birth: int | None = Field(None, ge=1900, le=2100)
    diagnosis: str | None = Field(None, max_length=_MAX_NOTES)
    login_enabled: bool = False
    general_notes: str | None = Field(None, max_length=_MAX_NOTES)
    profile_checklist: list[str] | None = Field(None, max_length=_MAX_CHECKLIST_ITEMS)

    @field_validator("display_name")
    @classmethod
    def display_name_strip(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("El nombre es obligatorio")
        return s

    @field_validator("rut", "phone")
    @classmethod
    def optional_strip_or_none(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        return s or None

    @field_validator("profile_checklist")
    @classmethod
    def normalize_checklist(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        out: list[str] = []
        for x in v:
            if not isinstance(x, str):
                continue
            t = x.strip()
            if t and len(t) <= _MAX_CHECKLIST_ITEM_LEN:
                out.append(t)
        return out or None


class YouthCreate(YouthBase):
    """El identificador lo genera el sistema (JOV-001, JOV-002, ...)."""

    email: EmailStr | None = None

    @model_validator(mode="after")
    def email_required_if_login(self):
        if self.login_enabled and not self.email:
            raise ValueError("El correo es obligatorio cuando el inicio de sesión está habilitado")
        return self


class YouthUpdate(BaseModel):
    display_name: str | None = Field(None, min_length=1, max_length=255)
    rut: str | None = Field(None, max_length=20)
    phone: str | None = Field(None, max_length=50)
    year_of_birth: int | None = Field(None, ge=1900, le=2100)
    diagnosis: str | None = Field(None, max_length=_MAX_NOTES)
    login_enabled: bool | None = None
    general_notes: str | None = Field(None, max_length=_MAX_NOTES)
    profile_checklist: list[str] | None = Field(None, max_length=_MAX_CHECKLIST_ITEMS)
    email: EmailStr | None = None

    @field_validator("display_name")
    @classmethod
    def display_name_opt_strip(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        if not s:
            raise ValueError("El nombre no puede estar vacío")
        return s

    @field_validator("rut", "phone")
    @classmethod
    def optional_strip_or_none_update(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        return s or None

    @field_validator("profile_checklist")
    @classmethod
    def normalize_checklist_update(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        out: list[str] = []
        for x in v:
            if not isinstance(x, str):
                continue
            t = x.strip()
            if t and len(t) <= _MAX_CHECKLIST_ITEM_LEN:
                out.append(t)
        return out or None


class YouthChangeEmailRequest(BaseModel):
    new_email: EmailStr


class YouthLookupRequest(BaseModel):
    """POST /youths/lookup: lista de IDs de jóvenes."""

    ids: list[int] = Field(..., min_length=1, max_length=200)

    @field_validator("ids")
    @classmethod
    def ids_positive_unique(cls, v: list[int]) -> list[int]:
        if any(i < 1 for i in v):
            raise ValueError("Los IDs deben ser enteros positivos")
        return list(dict.fromkeys(v))


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
    user_id: int | None = None
    display_name: str
    identifier: str | None = None
    rut: str | None = None
    email: str | None = None  # del usuario cuando tiene user_id
    profile_photo_url: str | None = None
    phone: str | None = None
    year_of_birth: int | None = None
    diagnosis: str | None = None
    login_enabled: bool
    is_active: bool
    general_notes: str | None = None
    profile_checklist: list[str] | None = None
    activation_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class LastSessionInfo(BaseModel):
    id: int
    started_at: datetime
    status: str
    ended_at: datetime | None = None


class YouthWithLastSession(YouthResponse):
    status_label: str | None = None
    last_session: LastSessionInfo | None = None

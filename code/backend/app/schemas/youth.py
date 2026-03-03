"""Esquemas de jóvenes."""
import json
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, model_validator


class YouthBase(BaseModel):
    display_name: str
    phone: Optional[str] = None
    login_enabled: bool = False
    general_notes: Optional[str] = None
    profile_checklist: Optional[list[str]] = None


class YouthCreate(YouthBase):
    """identifier lo genera el sistema (JOV-001, JOV-002, ...)."""
    email: Optional[str] = None

    @model_validator(mode="after")
    def email_required_if_login(self):
        if self.login_enabled and not self.email:
            raise ValueError("email es obligatorio cuando login_enabled es true")
        return self


class YouthUpdate(BaseModel):
    display_name: Optional[str] = None
    # identifier no es editable
    phone: Optional[str] = None
    year_of_birth: Optional[int] = None
    diagnosis: Optional[str] = None
    login_enabled: Optional[bool] = None
    general_notes: Optional[str] = None
    profile_checklist: Optional[list[str]] = None
    email: Optional[str] = None


class YouthChangeEmailRequest(BaseModel):
    new_email: str


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
    email: Optional[str] = None  # del User cuando tiene user_id
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

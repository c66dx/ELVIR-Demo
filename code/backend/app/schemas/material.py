"""Esquemas de material de apoyo."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

MaterialType = Literal["VIDEO", "PDF", "LINK"]

_MAX_TITLE = 255
_MAX_URL = 500
_MAX_DESC = 50_000
_MAX_REASON = 2_000


class CreateMaterialRequest(BaseModel):
    title: str = Field(..., max_length=_MAX_TITLE)
    description: str | None = Field(None, max_length=_MAX_DESC)
    type: MaterialType
    url: str = Field(..., max_length=_MAX_URL)
    job_role_id: int | None = Field(None, ge=1)
    case_id: int | None = Field(None, ge=1)

    @field_validator("title")
    @classmethod
    def title_nonempty(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("El título es obligatorio")
        return s

    @field_validator("description")
    @classmethod
    def description_optional(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        return s or None

    @field_validator("url")
    @classmethod
    def url_nonempty(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("La URL es obligatoria")
        return s


class SuggestMaterialRequest(BaseModel):
    youth_id: int = Field(..., ge=1)
    material_id: int = Field(..., ge=1)
    session_id: int | None = Field(None, ge=1)
    reason: str | None = Field(None, max_length=_MAX_REASON)

    @field_validator("reason")
    @classmethod
    def reason_optional(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        return s or None


class RecordViewRequest(BaseModel):
    youth_id: int = Field(..., ge=1)

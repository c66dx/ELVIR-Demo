"""Esquemas comunes: catálogos, plantillas."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class JobRoleResponse(BaseModel):
    id: int
    slug: str
    name: str
    description: str | None = None
    objetivo: str | None = None
    area: str | None = None
    nivel_experiencia: str | None = None
    competencias: Any | None = None  # arreglo JSON o texto
    tecnologias: Any | None = None  # arreglo JSON o texto
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class CaseResponse(BaseModel):
    id: int
    slug: str
    name: str
    difficulty: str
    prompt_instructions: str | None = None
    description: str | None = None
    intervencion_regulacion_emocional: str | None = None
    intervencion_presentacion_personal: str | None = None
    intervencion_expectativas_empresa: str | None = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class JobRoleRef(BaseModel):
    id: int
    slug: str
    name: str


class CaseRef(BaseModel):
    id: int
    slug: str
    difficulty: str
    name: str


class SimulationTemplateResponse(BaseModel):
    id: int
    job_role: JobRoleRef
    case: CaseRef
    liveavatar_context_id: str
    liveavatar_avatar_id: str
    liveavatar_voice_id: str
    is_active: bool
    resolution_reason: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ErrorDetail(BaseModel):
    message: str = Field(..., description="Mensaje legible del error.")
    code: str | None = Field(None, description="Codigo estandar del error.")
    request_id: str | None = Field(None, description="ID de trazabilidad de la request.")


class ErrorResponse(BaseModel):
    detail: Any = Field(..., description="Detalle del error (string o lista para validacion).")
    error: ErrorDetail = Field(..., description="Metadatos del error.")

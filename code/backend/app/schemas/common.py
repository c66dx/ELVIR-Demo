"""Esquemas comunes: catálogos, plantillas."""
from typing import Optional, List, Any

from pydantic import BaseModel


class JobRoleResponse(BaseModel):
    id: int
    slug: str
    name: str
    description: Optional[str] = None
    objetivo: Optional[str] = None
    competencias: Optional[Any] = None  # JSON array o string
    is_active: bool

    class Config:
        from_attributes = True


class CaseResponse(BaseModel):
    id: int
    slug: str
    name: str
    difficulty: str
    prompt_instructions: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


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
    resolution_reason: Optional[str] = None

    class Config:
        from_attributes = True

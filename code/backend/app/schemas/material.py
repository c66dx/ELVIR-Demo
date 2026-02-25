"""Esquemas de material de apoyo."""
from typing import Optional

from pydantic import BaseModel


class CreateMaterialRequest(BaseModel):
    title: str
    description: Optional[str] = None
    type: str  # VIDEO, PDF, LINK
    url: str
    job_role_id: Optional[int] = None
    case_id: Optional[int] = None


class SuggestMaterialRequest(BaseModel):
    youth_id: int
    material_id: int
    session_id: Optional[int] = None
    reason: Optional[str] = None


class RecordViewRequest(BaseModel):
    youth_id: int

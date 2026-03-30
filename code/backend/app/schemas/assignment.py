"""Esquemas de asignaciones joven–profesional."""

from pydantic import BaseModel, Field


class AssignmentCreate(BaseModel):
    youth_id: int = Field(..., ge=1)
    professional_id: int = Field(..., ge=1)

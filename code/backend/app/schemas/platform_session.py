"""Esquemas para sesiones de plataforma (login/logout)."""
from datetime import datetime
from pydantic import BaseModel


class PlatformSessionResponse(BaseModel):
    """Registro de entrada/salida a la plataforma."""

    id: int
    user_id: int
    started_at: datetime
    ended_at: datetime | None

    class Config:
        from_attributes = True

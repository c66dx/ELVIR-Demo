"""Esquemas para sesiones de plataforma (login/logout)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PlatformSessionResponse(BaseModel):
    """Registro de entrada/salida a la plataforma."""

    id: int
    user_id: int
    started_at: datetime
    ended_at: datetime | None

    model_config = ConfigDict(from_attributes=True)

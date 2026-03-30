"""Esquemas de audio de sesión."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SessionAudioResponse(BaseModel):
    id: int
    session_id: int
    url: str
    content_type: str | None = None
    file_size_bytes: int | None = None
    duration_seconds: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

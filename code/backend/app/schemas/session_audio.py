"""Esquemas de audio de sesión."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SessionAudioResponse(BaseModel):
    id: int
    session_id: int
    url: str
    content_type: Optional[str] = None
    file_size_bytes: Optional[int] = None
    duration_seconds: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

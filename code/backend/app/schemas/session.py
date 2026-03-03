"""Esquemas de sesiones."""
from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel


class SessionCreate(BaseModel):
    youth_id: int
    simulation_template_id: int
    mode: str  # AUTOGESTIONADA, SUPERVISADA
    professional_id: Optional[int] = None


class SessionResponse(BaseModel):
    id: int
    youth_id: int
    professional_id: Optional[int] = None
    simulation_template_id: int
    mode: str
    status: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    liveavatar_session_id: Optional[str] = None
    metrics: Optional[dict[str, Any]] = None

    class Config:
        from_attributes = True


class SessionCloseRequest(BaseModel):
    status: str  # COMPLETADA, CANCELADA, ERROR
    metrics: Optional[dict[str, Any]] = None
    motivo: Optional[str] = None  # Para ERROR: LIVEAVATAR_CONNECTION, etc.


class SessionStartResponse(BaseModel):
    session_id: int
    liveavatar_session_id: str
    embed: dict | None = None  # { type: "iframe", url: "..." } - legacy
    livekit_url: str | None = None
    access_token: str | None = None


class SessionEventResponse(BaseModel):
    id: int
    session_id: int
    event_type: str
    occurred_at: datetime
    payload: Optional[dict] = None

    class Config:
        from_attributes = True


class TranscriptEntry(BaseModel):
    role: str  # "user" | "avatar"
    transcript: str
    absolute_timestamp: int
    relative_timestamp: int


class TranscriptResponse(BaseModel):
    transcript_data: list[TranscriptEntry]
    session_active: Optional[bool] = None
    fetched_at: Optional[datetime] = None

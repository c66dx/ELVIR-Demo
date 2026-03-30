"""Esquemas de sesiones."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class SessionCreate(BaseModel):
    youth_id: int = Field(..., ge=1)
    simulation_template_id: int = Field(..., ge=1)
    mode: Literal["AUTOGESTIONADA", "SUPERVISADA"]
    professional_id: int | None = Field(None, ge=1)


class SessionResponse(BaseModel):
    id: int
    youth_id: int
    professional_id: int | None = None
    simulation_template_id: int
    mode: Literal["AUTOGESTIONADA", "SUPERVISADA"]
    status: Literal["EN_CURSO", "COMPLETADA", "CANCELADA", "ERROR"]
    started_at: datetime
    ended_at: datetime | None = None
    duration_seconds: int | None = None
    liveavatar_session_id: str | None = None
    metrics: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)


class SessionCloseRequest(BaseModel):
    status: Literal["COMPLETADA", "CANCELADA", "ERROR"]
    metrics: dict[str, Any] | None = None
    motivo: str | None = Field(None, max_length=500)  # Para ERROR: LIVEAVATAR_CONNECTION, etc.


class SessionStartResponse(BaseModel):
    session_id: int
    liveavatar_session_id: str
    embed: dict | None = None  # { type: "iframe", url: "..." } - heredado
    livekit_url: str | None = None
    access_token: str | None = None


class SessionEventResponse(BaseModel):
    id: int
    session_id: int
    event_type: str
    occurred_at: datetime
    payload: dict | None = None

    model_config = ConfigDict(from_attributes=True)


class TranscriptEntry(BaseModel):
    role: str  # valores: "user" | "avatar"
    transcript: str
    absolute_timestamp: int
    relative_timestamp: int


class TranscriptResponse(BaseModel):
    transcript_data: list[TranscriptEntry]
    session_active: bool | None = None
    fetched_at: datetime | None = None


class SessionMonthlyStat(BaseModel):
    month: str
    count: int


class SessionStatsResponse(BaseModel):
    total: int
    completed: int
    cancelled: int
    error: int
    in_progress: int
    monthly: list[SessionMonthlyStat]


class SessionEvaluationRequest(BaseModel):
    session_id: int | None = Field(None, ge=1)
    liveavatar_session_id: str | None = Field(None, max_length=200)
    evaluation: Any
    source: str | None = Field(None, max_length=100)


class SessionCompetencyItem(BaseModel):
    competency_slug: str = Field(..., min_length=1, max_length=200)
    level_slug: str = Field(..., min_length=1, max_length=200)
    comment: str | None = Field(None, max_length=10_000)


class SessionCompetenciesRequest(BaseModel):
    items: list[SessionCompetencyItem] = Field(..., max_length=200)


class SessionEventCreate(BaseModel):
    event_type: str = Field(..., min_length=1, max_length=120)
    payload: dict | None = None

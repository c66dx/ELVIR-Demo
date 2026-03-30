"""Esquemas para notificaciones."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class YouthNotificationResponse(BaseModel):
    id: int
    youth_id: int
    type: str
    title: str
    message: str
    link: str | None = None
    entity_type: str | None = None
    entity_id: int | None = None
    created_at: datetime
    read_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class NotificationReadRequest(BaseModel):
    """Marcar notificaciones como leídas. Lista vacía no actualiza filas."""

    ids: list[int] = Field(default_factory=list, max_length=500)

    @field_validator("ids")
    @classmethod
    def ids_non_negative(cls, v: list[int]) -> list[int]:
        if any(i < 1 for i in v):
            raise ValueError("Los IDs deben ser positivos")
        return v

"""Esquemas para notificaciones."""
from datetime import datetime
from pydantic import BaseModel


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

    class Config:
        from_attributes = True


class NotificationReadRequest(BaseModel):
    ids: list[int] = []

"""Helpers para crear notificaciones de joven."""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.notification import YouthNotification


def upsert_youth_notification(
    db: Session,
    *,
    youth_id: int,
    type: str,
    title: str,
    message: str,
    link: str | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
) -> YouthNotification:
    """Crea o actualiza una notificación única por entidad."""
    now = datetime.now(timezone.utc)
    existing = None
    if entity_type and entity_id is not None:
        existing = (
            db.query(YouthNotification)
            .filter(
                YouthNotification.youth_id == youth_id,
                YouthNotification.entity_type == entity_type,
                YouthNotification.entity_id == entity_id,
            )
            .first()
        )

    if existing:
        existing.type = type
        existing.title = title
        existing.message = message
        existing.link = link
        existing.created_at = now
        existing.read_at = None
        return existing

    notification = YouthNotification(
        youth_id=youth_id,
        type=type,
        title=title,
        message=message,
        link=link,
        entity_type=entity_type,
        entity_id=entity_id,
        created_at=now,
    )
    db.add(notification)
    return notification

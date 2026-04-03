"""Consultas y actualizaciones de notificaciones de jóvenes."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session as DBSession

from app.models.notification import YouthNotification


def fetch_youth_notifications(
    db: DBSession,
    youth_id: int,
    page: int | None,
    page_size: int | None,
    unread_only: bool | None,
) -> tuple[list[YouthNotification], dict[str, str]]:
    """Lista notificaciones con contadores y cabeceras de listado (siempre las mismas claves que el router)."""
    use_pagination = bool(page or page_size)
    if use_pagination:
        page = page or 1
        page_size = page_size or 20

    q = db.query(YouthNotification).filter(YouthNotification.youth_id == youth_id)
    if unread_only:
        q = q.filter(YouthNotification.read_at.is_(None))

    total = q.order_by(None).count()
    unread_total = (
        db.query(YouthNotification)
        .filter(YouthNotification.youth_id == youth_id, YouthNotification.read_at.is_(None))
        .count()
    )

    headers = {
        "X-Total-Count": str(total),
        "X-Total-Unread": str(unread_total),
        "X-Page": str(page or 1),
        "X-Page-Size": str(page_size or total),
    }

    q = q.order_by(YouthNotification.created_at.desc(), YouthNotification.id.desc())
    if use_pagination:
        q = q.offset((page - 1) * page_size).limit(page_size)

    return q.all(), headers


def mark_youth_notifications_read(db: DBSession, youth_id: int, notification_ids: list[int]) -> int:
    """Marca como leídas las notificaciones indicadas. Retorna filas actualizadas."""
    if not notification_ids:
        return 0
    now = datetime.now(UTC)
    updated = (
        db.query(YouthNotification)
        .filter(YouthNotification.youth_id == youth_id, YouthNotification.id.in_(notification_ids))
        .update({"read_at": now}, synchronize_session=False)
    )
    db.commit()
    return updated


def mark_all_youth_notifications_read(db: DBSession, youth_id: int) -> int:
    now = datetime.now(UTC)
    updated = (
        db.query(YouthNotification)
        .filter(YouthNotification.youth_id == youth_id, YouthNotification.read_at.is_(None))
        .update({"read_at": now}, synchronize_session=False)
    )
    db.commit()
    return updated

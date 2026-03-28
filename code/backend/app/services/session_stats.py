"""Agregados y series mensuales de sesiones."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import case, func
from sqlalchemy.orm import Session as OrmSession

from app.models.session import Session as SessionModel
from app.models.user import User
from app.schemas.session import SessionMonthlyStat, SessionStatsResponse
from app.services.session_access import build_sessions_query


def _month_key(year: int, month: int) -> str:
    return f"{year}-{month:02d}"


def compute_session_stats(
    db: OrmSession,
    user: User,
    youth_id: int | None,
    months: int,
) -> SessionStatsResponse:
    """Resumen de sesiones (conteos por estado y curva mensual de completadas)."""
    sessions_q = build_sessions_query(db, user, youth_id)
    now = datetime.now(timezone.utc)

    month_keys: list[str] = []
    for i in range(months - 1, -1, -1):
        m = now.month - i
        y = now.year + (m - 1) // 12
        m = (m - 1) % 12 + 1
        month_keys.append(_month_key(y, m))
    first_year, first_month = month_keys[0].split("-")
    range_start = datetime(int(first_year), int(first_month), 1, tzinfo=timezone.utc)

    if sessions_q is None:
        return SessionStatsResponse(
            total=0,
            completed=0,
            cancelled=0,
            error=0,
            in_progress=0,
            monthly=[SessionMonthlyStat(month=k, count=0) for k in month_keys],
        )

    totals = sessions_q.with_entities(
        func.count(SessionModel.id).label("total"),
        func.sum(case((SessionModel.status == "COMPLETADA", 1), else_=0)).label("completed"),
        func.sum(case((SessionModel.status == "CANCELADA", 1), else_=0)).label("cancelled"),
        func.sum(case((SessionModel.status == "ERROR", 1), else_=0)).label("error"),
        func.sum(case((SessionModel.status == "EN_CURSO", 1), else_=0)).label("in_progress"),
    ).first()

    month_counts: dict[str, int] = {}
    bind = db.get_bind()
    dialect = bind.dialect.name if bind is not None else ""
    if dialect == "postgresql":
        month_rows = (
            sessions_q.filter(
                SessionModel.status == "COMPLETADA",
                SessionModel.ended_at.isnot(None),
                SessionModel.ended_at >= range_start,
            )
            .with_entities(func.date_trunc("month", SessionModel.ended_at).label("month"), func.count(SessionModel.id))
            .group_by("month")
            .all()
        )
        for month_dt, count in month_rows:
            if month_dt:
                month_counts[_month_key(month_dt.year, month_dt.month)] = int(count or 0)
    else:
        rows = (
            sessions_q.filter(
                SessionModel.status == "COMPLETADA",
                SessionModel.ended_at.isnot(None),
                SessionModel.ended_at >= range_start,
            )
            .with_entities(SessionModel.ended_at)
            .all()
        )
        for (ended_at,) in rows:
            if not ended_at:
                continue
            key = _month_key(ended_at.year, ended_at.month)
            if key in month_counts:
                month_counts[key] += 1
            else:
                month_counts[key] = 1

    return SessionStatsResponse(
        total=int(totals.total or 0),
        completed=int(totals.completed or 0),
        cancelled=int(totals.cancelled or 0),
        error=int(totals.error or 0),
        in_progress=int(totals.in_progress or 0),
        monthly=[SessionMonthlyStat(month=k, count=month_counts.get(k, 0)) for k in month_keys],
    )

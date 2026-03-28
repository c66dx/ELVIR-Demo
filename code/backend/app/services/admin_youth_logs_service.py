"""Logs de plataforma y entrevistas de un joven (panel admin)."""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session as DBSession

from app.models.platform_session import PlatformSession
from app.models.professional import Professional
from app.models.session import Session as SessionModel
from app.models.youth import Youth
from app.schemas.admin import (
    AdminInterviewLogItem,
    AdminListMeta,
    AdminPlatformLogItem,
    AdminYouthLogsMeta,
    AdminYouthLogsResponse,
)


def build_youth_logs_response(
    db: DBSession,
    youth_id: int,
    *,
    platform_page: int | None,
    platform_page_size: int | None,
    interviews_page: int | None,
    interviews_page_size: int | None,
) -> AdminYouthLogsResponse:
    youth = db.query(Youth).filter(Youth.id == youth_id).first()
    if not youth:
        raise HTTPException(status_code=404, detail="Joven no encontrado")

    platform_use_pagination = bool(platform_page or platform_page_size)
    interviews_use_pagination = bool(interviews_page or interviews_page_size)
    if platform_use_pagination:
        platform_page = platform_page or 1
        platform_page_size = platform_page_size or 50
    if interviews_use_pagination:
        interviews_page = interviews_page or 1
        interviews_page_size = interviews_page_size or 50

    platform_logs: list[AdminPlatformLogItem] = []
    platform_meta: AdminListMeta | None = None
    if youth.user_id:
        platform_q = db.query(PlatformSession).filter(PlatformSession.user_id == youth.user_id)
        if platform_use_pagination:
            total = platform_q.order_by(None).count()
            offset = (platform_page - 1) * platform_page_size
            platform_rows = (
                platform_q.order_by(PlatformSession.started_at.desc())
                .offset(offset)
                .limit(platform_page_size)
                .all()
            )
            platform_meta = AdminListMeta(total=total, page=platform_page, page_size=platform_page_size)
        else:
            platform_rows = platform_q.order_by(PlatformSession.started_at.desc()).all()
        platform_logs = [AdminPlatformLogItem(started_at=p.started_at, ended_at=p.ended_at) for p in platform_rows]
    elif platform_use_pagination:
        platform_meta = AdminListMeta(total=0, page=platform_page, page_size=platform_page_size)

    sessions_q = db.query(SessionModel).filter(SessionModel.youth_id == youth_id)
    interviews_meta: AdminListMeta | None = None
    if interviews_use_pagination:
        total = sessions_q.order_by(None).count()
        offset = (interviews_page - 1) * interviews_page_size
        sessions = (
            sessions_q.order_by(SessionModel.started_at.desc())
            .offset(offset)
            .limit(interviews_page_size)
            .all()
        )
        interviews_meta = AdminListMeta(total=total, page=interviews_page, page_size=interviews_page_size)
    else:
        sessions = sessions_q.order_by(SessionModel.started_at.desc()).all()
    prof_ids = [s.professional_id for s in sessions if s.professional_id]
    prof_map: dict[int, str] = {}
    if prof_ids:
        profs = db.query(Professional.id, Professional.display_name).filter(Professional.id.in_(prof_ids)).all()
        prof_map = {p[0]: p[1] for p in profs}

    interviews = [
        AdminInterviewLogItem(
            id=s.id,
            started_at=s.started_at,
            ended_at=s.ended_at,
            status=s.status,
            mode=s.mode,
            professional_id=s.professional_id,
            professional_name=prof_map.get(s.professional_id) if s.professional_id else None,
        )
        for s in sessions
    ]

    meta = None
    if platform_use_pagination or interviews_use_pagination:
        meta = AdminYouthLogsMeta(platform=platform_meta, interviews=interviews_meta)

    return AdminYouthLogsResponse(platform_sessions=platform_logs, interviews=interviews, meta=meta)

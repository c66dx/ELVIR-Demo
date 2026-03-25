"""Router de administración: control de usuarios y logs."""
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query
from pydantic import BaseModel
from sqlalchemy import and_, func
from sqlalchemy import or_
from sqlalchemy.orm import Session as DBSession

from app.core.dependencies import get_current_admin
from app.database import get_db
from app.models.assignment import Assignment
from app.models.audit_log import AuditLog
from app.models.interview_summary import InterviewSummary
from app.models.material_suggestion import MaterialSuggestion
from app.models.material_view import MaterialView
from app.models.platform_session import PlatformSession
from app.models.professional import Professional
from app.models.session import Session as SessionModel
from app.models.session_audio import SessionAudio
from app.models.session_competency import SessionCompetency
from app.models.session_event import SessionEvent
from app.models.session_transcript import SessionTranscript
from app.models.user import User
from app.models.youth import Youth
from app.models.youth_invitation import YouthInvitation
from app.models.professional_invitation import ProfessionalInvitation

router = APIRouter(prefix="/admin", tags=["admin"])
UPLOADS_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
YOUTH_UPLOAD_DIR = UPLOADS_DIR / "youths"
PROFILE_UPLOAD_DIR = UPLOADS_DIR / "profiles"
AUDIO_UPLOAD_DIR = UPLOADS_DIR / "audio"


def _delete_upload_file(url: str | None, prefix: str, base_dir: Path) -> bool:
    if not url:
        return False
    try:
        parsed = urlparse(url)
        path = parsed.path or ""
        if not path.startswith(prefix):
            return False
        filename = path.replace(prefix, "", 1)
        file_path = base_dir / filename
        if file_path.exists():
            file_path.unlink(missing_ok=True)
            return True
    except Exception:
        return False
    return False


class AdminAssignedProfessional(BaseModel):
    id: int
    display_name: str
    email: str | None = None
    is_active: bool


class AdminYouthRow(BaseModel):
    id: int
    user_id: int | None = None
    display_name: str
    identifier: str | None = None
    rut: str | None = None
    email: str | None = None
    profile_photo_url: str | None = None
    login_enabled: bool
    is_active: bool
    login_type: str
    last_login_at: datetime | None = None
    last_interview_at: datetime | None = None
    last_interview_status: str | None = None
    last_interview_mode: str | None = None
    assigned_professional: AdminAssignedProfessional | None = None


class AdminProfessionalRow(BaseModel):
    id: int
    user_id: int
    display_name: str
    email: str | None = None
    profile_photo_url: str | None = None
    is_active: bool
    login_type: str
    last_login_at: datetime | None = None


class AdminListMeta(BaseModel):
    total: int
    page: int
    page_size: int


class AdminUsersOverviewMeta(BaseModel):
    youths: AdminListMeta | None = None
    professionals: AdminListMeta | None = None


class AdminUsersOverviewResponse(BaseModel):
    youths: list[AdminYouthRow]
    professionals: list[AdminProfessionalRow]
    meta: AdminUsersOverviewMeta | None = None


class AdminPlatformLogItem(BaseModel):
    started_at: datetime
    ended_at: datetime | None = None


class AdminInterviewLogItem(BaseModel):
    id: int
    started_at: datetime
    ended_at: datetime | None = None
    status: str
    mode: str
    professional_id: int | None = None
    professional_name: str | None = None


class AdminYouthLogsMeta(BaseModel):
    platform: AdminListMeta | None = None
    interviews: AdminListMeta | None = None


class AdminYouthLogsResponse(BaseModel):
    platform_sessions: list[AdminPlatformLogItem]
    interviews: list[AdminInterviewLogItem]
    meta: AdminYouthLogsMeta | None = None


class AuditLogRow(BaseModel):
    id: int
    request_id: str | None = None
    actor_user_id: int | None = None
    actor_role: str | None = None
    actor_email: str | None = None
    action: str
    entity_type: str | None = None
    entity_id: str | None = None
    status_code: int
    method: str
    path: str
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogRow]
    meta: AdminListMeta


def _get_last_login_map(db: DBSession, user_ids: list[int]) -> dict[int, datetime]:
    if not user_ids:
        return {}
    latest_per_user = (
        db.query(
            PlatformSession.user_id.label("user_id"),
            func.max(PlatformSession.started_at).label("max_started_at"),
        )
        .filter(PlatformSession.user_id.in_(user_ids))
        .group_by(PlatformSession.user_id)
        .subquery()
    )
    rows = (
        db.query(PlatformSession.user_id, PlatformSession.started_at)
        .join(
            latest_per_user,
            and_(
                PlatformSession.user_id == latest_per_user.c.user_id,
                PlatformSession.started_at == latest_per_user.c.max_started_at,
            ),
        )
        .all()
    )
    return {r[0]: r[1] for r in rows}


def _get_last_session_map(db: DBSession, youth_ids: list[int]) -> dict[int, SessionModel]:
    if not youth_ids:
        return {}
    latest_per_youth = (
        db.query(
            SessionModel.youth_id.label("youth_id"),
            func.max(SessionModel.started_at).label("max_started_at"),
        )
        .filter(SessionModel.youth_id.in_(youth_ids))
        .group_by(SessionModel.youth_id)
        .subquery()
    )
    sessions = (
        db.query(SessionModel)
        .join(
            latest_per_youth,
            and_(
                SessionModel.youth_id == latest_per_youth.c.youth_id,
                SessionModel.started_at == latest_per_youth.c.max_started_at,
            ),
        )
        .order_by(SessionModel.youth_id.asc(), SessionModel.started_at.desc(), SessionModel.id.desc())
        .all()
    )
    by_youth: dict[int, SessionModel] = {}
    for s in sessions:
        if s.youth_id not in by_youth:
            by_youth[s.youth_id] = s
    return by_youth


def _get_active_assignment_map(db: DBSession, youth_ids: list[int]) -> dict[int, Assignment]:
    if not youth_ids:
        return {}
    latest_per_youth = (
        db.query(
            Assignment.youth_id.label("youth_id"),
            func.max(Assignment.assigned_at).label("max_assigned_at"),
        )
        .filter(Assignment.status == "ACTIVO", Assignment.youth_id.in_(youth_ids))
        .group_by(Assignment.youth_id)
        .subquery()
    )
    assignments = (
        db.query(Assignment)
        .join(
            latest_per_youth,
            and_(
                Assignment.youth_id == latest_per_youth.c.youth_id,
                Assignment.assigned_at == latest_per_youth.c.max_assigned_at,
            ),
        )
        .all()
    )
    return {a.youth_id: a for a in assignments}


def _get_pending_invitation_email_map(db: DBSession, youth_ids: list[int]) -> dict[int, str]:
    if not youth_ids:
        return {}
    latest_per_youth = (
        db.query(
            YouthInvitation.youth_id.label("youth_id"),
            func.max(YouthInvitation.created_at).label("max_created_at"),
        )
        .filter(YouthInvitation.youth_id.in_(youth_ids), YouthInvitation.used_at.is_(None))
        .group_by(YouthInvitation.youth_id)
        .subquery()
    )
    rows = (
        db.query(YouthInvitation.youth_id, YouthInvitation.email)
        .join(
            latest_per_youth,
            and_(
                YouthInvitation.youth_id == latest_per_youth.c.youth_id,
                YouthInvitation.created_at == latest_per_youth.c.max_created_at,
            ),
        )
        .all()
    )
    return {r[0]: r[1] for r in rows}


def _resolve_login_type(has_email: bool) -> str:
    return "HABILITADO" if has_email else "NO_HABILITADO"


def _disable_youth_login(db: DBSession, youth: Youth) -> None:
    if youth.user_id:
        user = db.query(User).filter(User.id == youth.user_id).first()
        if user:
            user.is_active = False
            user.email = f"disabled+{user.id}@invalid.local"
    now = datetime.now(timezone.utc)
    (
        db.query(YouthInvitation)
        .filter(YouthInvitation.youth_id == youth.id, YouthInvitation.used_at.is_(None))
        .update({"used_at": now}, synchronize_session=False)
    )


@router.get("/users/overview", response_model=AdminUsersOverviewResponse)
def get_users_overview(
    admin=Depends(get_current_admin),
    db: DBSession = Depends(get_db),
    tab: Literal["youths", "professionals"] | None = Query(None),
    page: int | None = Query(None, ge=1),
    page_size: int | None = Query(None, ge=1, le=200),
    search: str | None = Query(None, min_length=1),
):
    search_term = search.strip() if search else None
    use_pagination = bool(tab or page or page_size or search_term)
    if use_pagination:
        page = page or 1
        page_size = page_size or 50

    youths: list[Youth] = []
    professionals: list[Professional] = []
    youths_total = 0
    professionals_total = 0

    if tab in (None, "youths"):
        youths_q = db.query(Youth)
        if search_term:
            like = f"%{search_term}%"
            youths_q = youths_q.outerjoin(User, Youth.user_id == User.id).filter(
                or_(
                    Youth.display_name.ilike(like),
                    Youth.identifier.ilike(like),
                    User.email.ilike(like),
                )
            )
        if use_pagination:
            youths_total = youths_q.order_by(None).count()
            offset = (page - 1) * page_size
            youths = youths_q.order_by(Youth.id.asc()).offset(offset).limit(page_size).all()
        else:
            youths = youths_q.order_by(Youth.id.asc()).all()

    if tab in (None, "professionals"):
        professionals_q = db.query(Professional)
        if search_term:
            like = f"%{search_term}%"
            professionals_q = professionals_q.outerjoin(User, Professional.user_id == User.id).filter(
                or_(
                    Professional.display_name.ilike(like),
                    User.email.ilike(like),
                )
            )
        if use_pagination:
            professionals_total = professionals_q.order_by(None).count()
            offset = (page - 1) * page_size
            professionals = professionals_q.order_by(Professional.id.asc()).offset(offset).limit(page_size).all()
        else:
            professionals = professionals_q.order_by(Professional.id.asc()).all()

    youth_ids = [y.id for y in youths]
    user_ids = [y.user_id for y in youths if y.user_id] + [p.user_id for p in professionals if p.user_id]

    user_rows = db.query(User).filter(User.id.in_(user_ids)).all() if user_ids else []
    user_map: dict[int, User] = {u.id: u for u in user_rows}
    last_login_map = _get_last_login_map(db, user_ids) if user_ids else {}
    last_session_map = _get_last_session_map(db, youth_ids) if youth_ids else {}
    assignment_map = _get_active_assignment_map(db, youth_ids) if youth_ids else {}
    invitation_email_map = _get_pending_invitation_email_map(db, youth_ids) if youth_ids else {}

    professional_ids = [a.professional_id for a in assignment_map.values()]
    prof_rows = db.query(Professional).filter(Professional.id.in_(professional_ids)).all() if professional_ids else []
    prof_map = {p.id: p for p in prof_rows}

    youth_rows: list[AdminYouthRow] = []
    for y in youths:
        user = user_map.get(y.user_id) if y.user_id else None
        email = None
        if y.login_enabled and y.user_id and user and user.is_active:
            email = user.email
        elif not y.user_id:
            email = invitation_email_map.get(y.id)
        profile_photo_url = None
        if y.photo_url:
            profile_photo_url = y.photo_url
        elif user and user.profile_photo_url:
            profile_photo_url = user.profile_photo_url
        last_login_at = last_login_map.get(y.user_id) if y.user_id else None
        last_session = last_session_map.get(y.id)
        assignment = assignment_map.get(y.id)
        assigned_professional = None
        if assignment:
            prof = prof_map.get(assignment.professional_id)
            if prof:
                prof_user = user_map.get(prof.user_id)
                assigned_professional = AdminAssignedProfessional(
                    id=prof.id,
                    display_name=prof.display_name,
                    email=prof_user.email if prof_user else None,
                    is_active=prof.is_active,
                )
        youth_rows.append(
            AdminYouthRow(
                id=y.id,
                user_id=y.user_id,
                display_name=y.display_name,
                identifier=y.identifier,
                rut=y.rut,
                email=email,
                profile_photo_url=profile_photo_url,
                login_enabled=y.login_enabled,
                is_active=y.is_active,
                login_type=_resolve_login_type(bool(email)),
                last_login_at=last_login_at,
                last_interview_at=last_session.started_at if last_session else None,
                last_interview_status=last_session.status if last_session else None,
                last_interview_mode=last_session.mode if last_session else None,
                assigned_professional=assigned_professional,
            )
        )

    professional_rows: list[AdminProfessionalRow] = []
    for p in professionals:
        user = user_map.get(p.user_id)
        email = user.email if user and user.is_active else None
        professional_rows.append(
            AdminProfessionalRow(
                id=p.id,
                user_id=p.user_id,
                display_name=p.display_name,
                email=email,
                profile_photo_url=user.profile_photo_url if user else None,
                is_active=p.is_active,
                login_type=_resolve_login_type(bool(email)),
                last_login_at=last_login_map.get(p.user_id),
            )
        )

    meta = None
    if use_pagination:
        meta = AdminUsersOverviewMeta()
        if tab in (None, "youths"):
            meta.youths = AdminListMeta(total=youths_total, page=page, page_size=page_size)
        if tab in (None, "professionals"):
            meta.professionals = AdminListMeta(total=professionals_total, page=page, page_size=page_size)

    return AdminUsersOverviewResponse(youths=youth_rows, professionals=professional_rows, meta=meta)


@router.delete("/youths/{youth_id}")
def admin_delete_youth(
    youth_id: int,
    admin=Depends(get_current_admin),
    db: DBSession = Depends(get_db),
):
    youth = db.query(Youth).filter(Youth.id == youth_id).first()
    if not youth:
        raise HTTPException(status_code=404, detail="Joven no encontrado")
    now = datetime.now(timezone.utc)
    youth.is_active = False
    youth.login_enabled = False
    _disable_youth_login(db, youth)
    (
        db.query(Assignment)
        .filter(Assignment.youth_id == youth_id, Assignment.status == "ACTIVO")
        .update({"status": "INACTIVO", "ended_at": now}, synchronize_session=False)
    )
    db.commit()
    return {"ok": True}


@router.delete("/professionals/{professional_id}")
def admin_delete_professional(
    professional_id: int,
    admin=Depends(get_current_admin),
    db: DBSession = Depends(get_db),
):
    professional = db.query(Professional).filter(Professional.id == professional_id).first()
    if not professional:
        raise HTTPException(status_code=404, detail="Tutor no encontrado")
    now = datetime.now(timezone.utc)
    professional.is_active = False
    if professional.user_id:
        user = db.query(User).filter(User.id == professional.user_id).first()
        if user:
            user.is_active = False
            user.email = f"disabled+{user.id}@invalid.local"
    (
        db.query(ProfessionalInvitation)
        .filter(ProfessionalInvitation.professional_id == professional_id, ProfessionalInvitation.used_at.is_(None))
        .update({"used_at": now}, synchronize_session=False)
    )
    (
        db.query(Assignment)
        .filter(Assignment.professional_id == professional_id, Assignment.status == "ACTIVO")
        .update({"status": "INACTIVO", "ended_at": now}, synchronize_session=False)
    )
    db.commit()
    return {"ok": True}


@router.get("/youths/{youth_id}/logs", response_model=AdminYouthLogsResponse)
def admin_get_youth_logs(
    youth_id: int,
    admin=Depends(get_current_admin),
    db: DBSession = Depends(get_db),
    platform_page: int | None = Query(None, ge=1),
    platform_page_size: int | None = Query(None, ge=1, le=200),
    interviews_page: int | None = Query(None, ge=1),
    interviews_page_size: int | None = Query(None, ge=1, le=200),
):
    """Devuelve logs históricos del joven: accesos (platform_sessions) y sesiones de entrevista."""
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


@router.get("/audit-logs", response_model=AuditLogListResponse)
def list_audit_logs(
    admin=Depends(get_current_admin),
    db: DBSession = Depends(get_db),
    page: int | None = Query(None, ge=1),
    page_size: int | None = Query(None, ge=1, le=200),
    search: str | None = Query(None, min_length=1),
    action: str | None = Query(None),
    entity_type: str | None = Query(None),
    status_code: int | None = Query(None, ge=100, le=599),
    actor_user_id: int | None = Query(None, ge=1),
    method: str | None = Query(None),
):
    page = page or 1
    page_size = page_size or 50
    search_term = search.strip() if search else None
    action_term = action.strip().lower() if action else None
    entity_term = entity_type.strip().lower() if entity_type else None
    method_term = method.strip().upper() if method else None

    q = db.query(AuditLog, User.email).outerjoin(User, AuditLog.actor_user_id == User.id)

    if action_term:
        q = q.filter(AuditLog.action == action_term)
    if entity_term:
        q = q.filter(AuditLog.entity_type == entity_term)
    if status_code:
        q = q.filter(AuditLog.status_code == status_code)
    if actor_user_id:
        q = q.filter(AuditLog.actor_user_id == actor_user_id)
    if method_term:
        q = q.filter(AuditLog.method == method_term)
    if search_term:
        like = f"%{search_term}%"
        q = q.filter(
            or_(
                AuditLog.request_id.ilike(like),
                AuditLog.entity_id.ilike(like),
                AuditLog.path.ilike(like),
                User.email.ilike(like),
            )
        )

    total = q.order_by(None).count()
    rows = (
        q.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [
        AuditLogRow(
            id=log.id,
            request_id=log.request_id,
            actor_user_id=log.actor_user_id,
            actor_role=log.actor_role,
            actor_email=email,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            status_code=log.status_code,
            method=log.method,
            path=log.path,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            created_at=log.created_at,
        )
        for log, email in rows
    ]

    return AuditLogListResponse(
        items=items,
        meta=AdminListMeta(total=total, page=page, page_size=page_size),
    )


@router.delete("/youths/{youth_id}/hard")
def admin_hard_delete_youth(
    youth_id: int,
    admin=Depends(get_current_admin),
    db: DBSession = Depends(get_db),
):
    youth = db.query(Youth).filter(Youth.id == youth_id).first()
    if not youth:
        raise HTTPException(status_code=404, detail="Joven no encontrado")

    user_id = youth.user_id
    user = db.query(User).filter(User.id == user_id).first() if user_id else None
    if user_id:
        linked_prof = db.query(Professional).filter(Professional.user_id == user_id).first()
        if linked_prof:
            raise HTTPException(status_code=409, detail="El usuario está asociado a un profesional")

    youth_photo_url = youth.photo_url
    user_photo_url = user.profile_photo_url if user else None

    session_ids = [row[0] for row in db.query(SessionModel.id).filter(SessionModel.youth_id == youth_id).all()]
    audio_urls: list[str] = []

    deleted_session_events = 0
    deleted_session_summaries = 0
    deleted_session_transcripts = 0
    deleted_session_audio = 0
    deleted_session_competencies = 0
    deleted_sessions = 0

    if session_ids:
        audio_urls = [row[0] for row in db.query(SessionAudio.url).filter(SessionAudio.session_id.in_(session_ids)).all()]
        deleted_session_events = db.query(SessionEvent).filter(SessionEvent.session_id.in_(session_ids)).delete(synchronize_session=False)
        deleted_session_summaries = db.query(InterviewSummary).filter(InterviewSummary.session_id.in_(session_ids)).delete(synchronize_session=False)
        deleted_session_transcripts = db.query(SessionTranscript).filter(SessionTranscript.session_id.in_(session_ids)).delete(synchronize_session=False)
        deleted_session_audio = db.query(SessionAudio).filter(SessionAudio.session_id.in_(session_ids)).delete(synchronize_session=False)
        deleted_session_competencies = db.query(SessionCompetency).filter(SessionCompetency.session_id.in_(session_ids)).delete(synchronize_session=False)
        deleted_sessions = db.query(SessionModel).filter(SessionModel.youth_id == youth_id).delete(synchronize_session=False)

    deleted_views = db.query(MaterialView).filter(MaterialView.youth_id == youth_id).delete(synchronize_session=False)
    deleted_suggestions = db.query(MaterialSuggestion).filter(MaterialSuggestion.youth_id == youth_id).delete(synchronize_session=False)
    deleted_assignments = db.query(Assignment).filter(Assignment.youth_id == youth_id).delete(synchronize_session=False)
    deleted_invitations = db.query(YouthInvitation).filter(YouthInvitation.youth_id == youth_id).delete(synchronize_session=False)

    deleted_platform_sessions = 0
    deleted_audit_logs = 0
    deleted_users = 0
    if user_id:
        deleted_platform_sessions = db.query(PlatformSession).filter(PlatformSession.user_id == user_id).delete(synchronize_session=False)
        deleted_audit_logs = db.query(AuditLog).filter(AuditLog.actor_user_id == user_id).delete(synchronize_session=False)

    deleted_youths = db.query(Youth).filter(Youth.id == youth_id).delete(synchronize_session=False)

    if user_id:
        deleted_users = db.query(User).filter(User.id == user_id).delete(synchronize_session=False)

    db.commit()

    removed_files = 0
    if _delete_upload_file(youth_photo_url, "/uploads/youths/", YOUTH_UPLOAD_DIR):
        removed_files += 1
    if _delete_upload_file(user_photo_url, "/uploads/profiles/", PROFILE_UPLOAD_DIR):
        removed_files += 1
    for url in audio_urls:
        if _delete_upload_file(url, "/uploads/audio/", AUDIO_UPLOAD_DIR):
            removed_files += 1

    return {
        "ok": True,
        "deleted": {
            "session_events": deleted_session_events,
            "session_summaries": deleted_session_summaries,
            "session_transcripts": deleted_session_transcripts,
            "session_audio": deleted_session_audio,
            "session_competencies": deleted_session_competencies,
            "sessions": deleted_sessions,
            "material_views": deleted_views,
            "material_suggestions": deleted_suggestions,
            "assignments": deleted_assignments,
            "youth_invitations": deleted_invitations,
            "platform_sessions": deleted_platform_sessions,
            "audit_logs": deleted_audit_logs,
            "youths": deleted_youths,
            "users": deleted_users,
            "removed_files": removed_files,
        },
    }






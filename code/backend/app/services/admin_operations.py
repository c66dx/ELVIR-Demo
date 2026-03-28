"""Operaciones de administración: baja lógica, borrado duro y limpieza de ficheros."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from fastapi import HTTPException
from sqlalchemy.orm import Session as DBSession

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
from app.services.youth_queries import disable_youth_login

UPLOADS_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
YOUTH_UPLOAD_DIR = UPLOADS_DIR / "youths"
PROFILE_UPLOAD_DIR = UPLOADS_DIR / "profiles"
AUDIO_UPLOAD_DIR = UPLOADS_DIR / "audio"


def delete_upload_file(url: str | None, prefix: str, base_dir: Path) -> bool:
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


def apply_admin_soft_delete_youth(db: DBSession, youth_id: int) -> dict:
    youth = db.query(Youth).filter(Youth.id == youth_id).first()
    if not youth:
        raise HTTPException(status_code=404, detail="Joven no encontrado")
    now = datetime.now(timezone.utc)
    youth.is_active = False
    youth.login_enabled = False
    disable_youth_login(db, youth)
    (
        db.query(Assignment)
        .filter(Assignment.youth_id == youth_id, Assignment.status == "ACTIVO")
        .update({"status": "INACTIVO", "ended_at": now}, synchronize_session=False)
    )
    db.commit()
    return {"ok": True}


def apply_admin_soft_delete_professional(db: DBSession, professional_id: int) -> dict:
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


def apply_hard_delete_youth(db: DBSession, youth_id: int) -> dict:
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
    if delete_upload_file(youth_photo_url, "/uploads/youths/", YOUTH_UPLOAD_DIR):
        removed_files += 1
    if delete_upload_file(user_photo_url, "/uploads/profiles/", PROFILE_UPLOAD_DIR):
        removed_files += 1
    for url in audio_urls:
        if delete_upload_file(url, "/uploads/audio/", AUDIO_UPLOAD_DIR):
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

#!/usr/bin/env python3
"""
Clean user-created data for local testing.
Keeps seed data (test users, youths, roles, cases, templates, competencies).

Deletes:
- Sessions and related data (events, summaries, transcripts, audio, competencies)
- Platform sessions
- Material views/suggestions
- Support materials (then re-seeds the 4 defaults unless --skip-reseed)
- Youth invitations
- Audit logs
- Non-seed youths, professionals, users (preserves seed emails and JOV-001..JOV-004)

Optional:
- --delete-uploads removes files under backend/uploads
- --skip-reseed keeps support materials empty after cleanup
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import SessionLocal
from app.models.audit_log import AuditLog
from app.models.interview_summary import InterviewSummary
from app.models.assignment import Assignment
from app.models.material_suggestion import MaterialSuggestion
from app.models.material_view import MaterialView
from app.models.platform_session import PlatformSession
from app.models.professional import Professional
from app.models.session import Session as SessionModel
from app.models.session_audio import SessionAudio
from app.models.session_competency import SessionCompetency
from app.models.session_event import SessionEvent
from app.models.session_transcript import SessionTranscript
from app.models.support_material import SupportMaterial
from app.models.user import User
from app.models.youth import Youth
from app.models.youth_invitation import YouthInvitation


UPLOADS_DIR = Path(__file__).resolve().parent / "uploads"
SEED_USER_EMAILS = {
    "joven1@test.cl",
    "joven2@test.cl",
    "prof@test.cl",
    "admin@test.cl",
}
SEED_YOUTH_IDENTIFIERS = {"JOV-001", "JOV-002", "JOV-003", "JOV-004"}


def _delete_upload_files() -> int:
    if not UPLOADS_DIR.exists():
        return 0
    removed = 0
    for path in UPLOADS_DIR.rglob("*"):
        if not path.is_file():
            continue
        if path.name == ".gitkeep":
            continue
        try:
            path.unlink()
            removed += 1
        except OSError:
            pass
    # Remove empty directories (but keep uploads root)
    for path in sorted([p for p in UPLOADS_DIR.rglob("*") if p.is_dir()], reverse=True):
        try:
            if not any(path.iterdir()):
                path.rmdir()
        except OSError:
            pass
    return removed


def clean(db: Session) -> dict[str, int]:
    """Delete user-created data, respecting FK order."""
    deleted: dict[str, int] = {}

    seed_user_ids = {row[0] for row in db.query(User.id).filter(User.email.in_(SEED_USER_EMAILS)).all()}
    seed_professional_ids = set()
    if seed_user_ids:
        seed_professional_ids = {
            row[0]
            for row in db.query(Professional.id).filter(Professional.user_id.in_(seed_user_ids)).all()
        }

    seed_youth_ids: set[int] = set()
    seed_filters = []
    if seed_user_ids:
        seed_filters.append(Youth.user_id.in_(seed_user_ids))
    if SEED_YOUTH_IDENTIFIERS:
        seed_filters.append(Youth.identifier.in_(SEED_YOUTH_IDENTIFIERS))
    if seed_filters:
        seed_youth_ids = {row[0] for row in db.query(Youth.id).filter(or_(*seed_filters)).all()}

    deleted["session_events"] = db.query(SessionEvent).delete()
    deleted["session_summaries"] = db.query(InterviewSummary).delete()
    deleted["session_transcripts"] = db.query(SessionTranscript).delete()
    deleted["session_audio"] = db.query(SessionAudio).delete()
    deleted["session_competencies"] = db.query(SessionCompetency).delete()
    deleted["sessions"] = db.query(SessionModel).delete()
    deleted["platform_sessions"] = db.query(PlatformSession).delete()
    deleted["material_views"] = db.query(MaterialView).delete()
    deleted["material_suggestions"] = db.query(MaterialSuggestion).delete()
    deleted["support_materials"] = db.query(SupportMaterial).delete()
    deleted["youth_invitations"] = db.query(YouthInvitation).delete()
    deleted["audit_logs"] = db.query(AuditLog).delete()
    deleted["assignments"] = db.query(Assignment).delete()

    if seed_youth_ids:
        deleted["youths"] = db.query(Youth).filter(~Youth.id.in_(seed_youth_ids)).delete()
    else:
        deleted["youths"] = db.query(Youth).delete()

    if seed_professional_ids:
        deleted["professionals"] = (
            db.query(Professional).filter(~Professional.id.in_(seed_professional_ids)).delete()
        )
    else:
        deleted["professionals"] = db.query(Professional).delete()

    if seed_user_ids:
        deleted["users"] = db.query(User).filter(~User.id.in_(seed_user_ids)).delete()
    else:
        deleted["users"] = db.query(User).delete()

    db.commit()
    return deleted


def reseed_material(db: Session) -> None:
    """Recreate the 4 default materials from seed."""
    from app.models.job_role import JobRole
    from app.models.case import Case

    jr1 = db.query(JobRole).filter(JobRole.slug == "operario").first()
    c1 = db.query(Case).filter(Case.slug == "normal").first()
    materials = [
        SupportMaterial(title="Tecnicas de comunicacion", description="Guia basica", type="VIDEO",
                        url="https://example.com/v1", job_role_id=jr1.id if jr1 else None,
                        case_id=c1.id if c1 else None, active=True),
        SupportMaterial(title="Lenguaje corporal", type="PDF", url="https://example.com/p1",
                        job_role_id=jr1.id if jr1 else None, active=True),
        SupportMaterial(title="Preguntas frecuentes retail", type="VIDEO", url="https://example.com/v2",
                        case_id=c1.id if c1 else None, active=True),
        SupportMaterial(title="Introduccion a entrevistas", type="LINK", url="https://example.com/l1",
                        active=True),
    ]
    for m in materials:
        db.add(m)
    db.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean user data from the database.")
    parser.add_argument("--delete-uploads", action="store_true", help="Delete files under backend/uploads")
    parser.add_argument("--skip-reseed", action="store_true", help="Do not recreate default materials")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        deleted = clean(db)
        if not args.skip_reseed:
            reseed_material(db)
        removed_files = _delete_upload_files() if args.delete_uploads else 0

        print("Cleanup completed:")
        for key, value in deleted.items():
            print(f"  - {value} {key}")
        if not args.skip_reseed:
            print("  - 4 support materials (seed)")
        if args.delete_uploads:
            print(f"  - {removed_files} files removed from uploads")
        print("\nSeed data (users, youths, roles, cases, templates, competencies) preserved.")
    finally:
        db.close()

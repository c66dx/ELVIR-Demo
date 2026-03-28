"""Lectura de transcripciones de sesión."""
from __future__ import annotations

from sqlalchemy.orm import Session as OrmSession

from app.models.session_transcript import SessionTranscript
from app.schemas.session import TranscriptResponse


def get_transcript_response(db: OrmSession, session_id: int) -> TranscriptResponse | None:
    """Devuelve TranscriptResponse o None. El caller debe haber validado acceso a la sesión."""
    transcript = db.query(SessionTranscript).filter(SessionTranscript.session_id == session_id).first()
    if not transcript:
        return None
    return TranscriptResponse(
        transcript_data=transcript.transcript_data,
        session_active=transcript.session_active,
        fetched_at=transcript.fetched_at,
    )

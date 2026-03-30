"""Persistencia de audio grabado para sesiones completadas."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session as OrmSession

from app.core.storage import get_storage
from app.models.session_audio import SessionAudio
from app.models.user import User

SESSION_AUDIO_EXTENSIONS = {".webm", ".ogg", ".wav", ".mp3", ".m4a"}
SESSION_AUDIO_MAX_MB = 30
SESSION_AUDIO_MAX_BYTES = SESSION_AUDIO_MAX_MB * 1024 * 1024


def allowed_audio_extensions_message() -> str:
    return ", ".join(sorted(SESSION_AUDIO_EXTENSIONS))


def persist_session_audio_upload(
    db: OrmSession,
    session_id: int,
    file: UploadFile,
    duration_seconds: int | None,
    public_base_url: str,
) -> SessionAudio:
    """
    Guarda el archivo y crea o actualiza SessionAudio.
    El caller debe haber validado sesión, permisos y estado COMPLETADA.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo vacío")
    ext = Path(file.filename).suffix.lower()
    if ext not in SESSION_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Extensión no permitida. Permitidas: {allowed_audio_extensions_message()}",
        )

    content_type = file.content_type
    filename = f"session_{session_id}_{uuid.uuid4().hex}{ext}"
    relative_key = f"audio/{filename}"
    storage = get_storage()

    try:
        url, size = storage.save_upload(
            file,
            relative_key=relative_key,
            max_bytes=SESSION_AUDIO_MAX_BYTES,
            public_base_url=public_base_url,
            oversize_detail=f"Audio demasiado grande. Máximo: {SESSION_AUDIO_MAX_MB} MB",
        )
    finally:
        try:
            file.file.close()
        except Exception:
            pass

    existing = db.query(SessionAudio).filter(SessionAudio.session_id == session_id).first()
    if existing:
        try:
            storage.delete_public_url(existing.url or "")
        except Exception:
            pass
        existing.url = url
        existing.content_type = content_type
        existing.file_size_bytes = size
        existing.duration_seconds = duration_seconds
        db.commit()
        db.refresh(existing)
        return existing

    audio = SessionAudio(
        session_id=session_id,
        url=url,
        content_type=content_type,
        file_size_bytes=size,
        duration_seconds=duration_seconds,
    )
    db.add(audio)
    db.commit()
    db.refresh(audio)
    return audio


def upload_session_audio_for_user(
    db: OrmSession,
    session_id: int,
    user: User,
    file: UploadFile,
    duration_seconds: int | None,
    public_base_url: str,
) -> SessionAudio:
    """Acceso a sesión, estado COMPLETADA y persistencia de audio."""
    from app.services.session_access import require_session_access

    session = require_session_access(db, session_id, user)
    if session.status != "COMPLETADA":
        raise HTTPException(status_code=409, detail="Audio disponible solo para sesiones completadas")
    return persist_session_audio_upload(db, session_id, file, duration_seconds, public_base_url)


def get_session_audio_record(db: OrmSession, session_id: int) -> SessionAudio | None:
    """Metadata de audio de una sesión o None. El caller debe haber validado acceso."""
    return db.query(SessionAudio).filter(SessionAudio.session_id == session_id).first()

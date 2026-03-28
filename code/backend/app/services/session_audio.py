"""Persistencia de audio grabado para sesiones completadas."""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session as OrmSession

from app.models.session_audio import SessionAudio
from app.models.user import User

SESSION_AUDIO_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "audio"
SESSION_AUDIO_EXTENSIONS = {".webm", ".ogg", ".wav", ".mp3", ".m4a"}
SESSION_AUDIO_MAX_MB = 30
SESSION_AUDIO_MAX_BYTES = SESSION_AUDIO_MAX_MB * 1024 * 1024
SESSION_AUDIO_CHUNK_SIZE = 1024 * 1024


def allowed_audio_extensions_message() -> str:
    return ", ".join(sorted(SESSION_AUDIO_EXTENSIONS))


def _ensure_session_audio_dir() -> None:
    SESSION_AUDIO_DIR.mkdir(parents=True, exist_ok=True)


def _save_audio_stream(file: UploadFile, destination: Path) -> int:
    """Guarda audio por chunks y retorna tamaño total escrito."""
    total_written = 0
    with destination.open("wb") as out:
        while True:
            chunk = file.file.read(SESSION_AUDIO_CHUNK_SIZE)
            if not chunk:
                break
            total_written += len(chunk)
            if total_written > SESSION_AUDIO_MAX_BYTES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Audio demasiado grande. Máximo: {SESSION_AUDIO_MAX_MB} MB",
                )
            out.write(chunk)
    return total_written


def persist_session_audio_upload(
    db: OrmSession,
    session_id: int,
    file: UploadFile,
    duration_seconds: int | None,
    public_base_url: str,
) -> SessionAudio:
    """
    Guarda el archivo en disco y crea o actualiza SessionAudio.
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

    _ensure_session_audio_dir()
    filename = f"session_{session_id}_{uuid.uuid4().hex}{ext}"
    file_path = SESSION_AUDIO_DIR / filename
    try:
        size = _save_audio_stream(file, file_path)
    except HTTPException:
        if file_path.exists():
            file_path.unlink(missing_ok=True)
        raise
    except OSError as e:
        if file_path.exists():
            file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Error al guardar audio: {str(e)}") from e
    finally:
        try:
            file.file.close()
        except Exception:
            pass

    base = public_base_url.rstrip("/")
    url = f"{base}/uploads/audio/{filename}"

    existing = db.query(SessionAudio).filter(SessionAudio.session_id == session_id).first()
    if existing:
        try:
            old_url = existing.url or ""
            if "/uploads/audio/" in old_url:
                old_name = old_url.split("/uploads/audio/")[-1]
                old_path = SESSION_AUDIO_DIR / old_name
                if old_path.exists():
                    old_path.unlink(missing_ok=True)
        except Exception:
            pass
        existing.url = url
        existing.content_type = file.content_type
        existing.file_size_bytes = size
        existing.duration_seconds = duration_seconds
        db.commit()
        db.refresh(existing)
        return existing

    audio = SessionAudio(
        session_id=session_id,
        url=url,
        content_type=file.content_type,
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

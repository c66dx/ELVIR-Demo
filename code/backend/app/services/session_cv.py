"""Subida de CV (PDF) asociado a una sesión."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session as OrmSession

from app.core.storage import get_storage
from app.models.session import Session as SessionModel
from app.models.user import User

SESSION_CV_EXTENSIONS = {".pdf"}
SESSION_CV_MAX_MB = 10
SESSION_CV_MAX_BYTES = SESSION_CV_MAX_MB * 1024 * 1024


def allowed_cv_extensions_message() -> str:
    return ", ".join(sorted(SESSION_CV_EXTENSIONS))


def _close_upload_file(file: UploadFile) -> None:
    try:
        file.file.close()
    except Exception:
        pass


def persist_session_cv_upload(
    db: OrmSession,
    session: SessionModel,
    file: UploadFile,
    public_base_url: str,
) -> dict:
    """Guarda el CV y lo registra en session.metrics."""
    if not file.filename:
        _close_upload_file(file)
        raise HTTPException(status_code=400, detail="Nombre de archivo vacío")

    ext = Path(file.filename).suffix.lower()
    if ext not in SESSION_CV_EXTENSIONS:
        _close_upload_file(file)
        raise HTTPException(
            status_code=400,
            detail=f"Extensión no permitida. Permitidas: {allowed_cv_extensions_message()}",
        )

    filename = f"cv_{session.id}_{uuid.uuid4().hex}{ext}"
    relative_key = f"cv/{filename}"
    storage = get_storage()

    try:
        url, size = storage.save_upload(
            file,
            relative_key=relative_key,
            max_bytes=SESSION_CV_MAX_BYTES,
            public_base_url=public_base_url,
            oversize_detail=f"Archivo demasiado grande. Máximo: {SESSION_CV_MAX_MB} MB",
        )
    finally:
        _close_upload_file(file)

    metrics = dict(session.metrics) if session.metrics else {}
    prev = metrics.get("cv") if isinstance(metrics.get("cv"), dict) else None
    if prev and prev.get("url"):
        try:
            storage.delete_public_url(prev.get("url"))
        except Exception:
            pass

    uploaded_at = datetime.now(UTC).isoformat()
    cv_payload = {
        "url": url,
        "filename": filename,
        "original_name": file.filename,
        "file_size_bytes": size,
        "uploaded_at": uploaded_at,
    }
    metrics["cv"] = cv_payload
    session.metrics = metrics
    db.commit()
    db.refresh(session)
    return cv_payload


def upload_session_cv_for_user(
    db: OrmSession,
    session_id: int,
    user: User,
    file: UploadFile,
    public_base_url: str,
) -> dict:
    """Valida acceso a la sesión y guarda el CV."""
    from app.services.session_access import require_session_access

    session = require_session_access(db, session_id, user)
    return persist_session_cv_upload(db, session, file, public_base_url)

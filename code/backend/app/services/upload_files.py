"""Subida de archivos genéricos (PDF/video) — capa de almacenamiento configurable."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.core.storage import get_storage

ALLOWED_EXTENSIONS = {".pdf", ".mp4", ".webm", ".mov", ".avi", ".mkv"}
MAX_SIZE_MB = 50
MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024


def allowed_upload_extensions_message() -> str:
    return ", ".join(sorted(ALLOWED_EXTENSIONS))


def _close_upload_file(file: UploadFile) -> None:
    try:
        file.file.close()
    except Exception:
        pass


def persist_public_upload(file: UploadFile, public_base_url: str) -> dict:
    """
    Guarda con nombre único. Devuelve url y filename.
    El caller debe validar rol; aquí solo validación de archivo.
    """
    if not file.filename:
        _close_upload_file(file)
        raise HTTPException(status_code=400, detail="Nombre de archivo vacío")
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        _close_upload_file(file)
        raise HTTPException(
            status_code=400,
            detail=f"Extensión no permitida. Permitidas: {allowed_upload_extensions_message()}",
        )
    unique_name = f"{uuid.uuid4().hex}{ext}"
    storage = get_storage()
    try:
        url, _n = storage.save_upload(
            file,
            relative_key=unique_name,
            max_bytes=MAX_SIZE_BYTES,
            public_base_url=public_base_url,
            oversize_detail=f"Archivo demasiado grande. Máximo: {MAX_SIZE_MB} MB",
        )
    finally:
        _close_upload_file(file)

    return {"url": url, "filename": unique_name}


def persist_staff_user_upload(file: UploadFile, public_base_url: str, user) -> dict:
    """Solo Admin o Profesional; delega en persist_public_upload."""
    if getattr(user, "role", None) not in ("ADMIN", "PROFESIONAL"):
        _close_upload_file(file)
        raise HTTPException(status_code=403, detail="Acceso denegado")
    return persist_public_upload(file, public_base_url)

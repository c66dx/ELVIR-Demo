"""Subida de archivos genéricos (PDF/video) a /uploads."""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

UPLOADS_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
ALLOWED_EXTENSIONS = {".pdf", ".mp4", ".webm", ".mov", ".avi", ".mkv"}
MAX_SIZE_MB = 50
CHUNK_SIZE = 1024 * 1024
MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024


def allowed_upload_extensions_message() -> str:
    return ", ".join(sorted(ALLOWED_EXTENSIONS))


def _ensure_uploads_dir() -> None:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def _save_upload_stream(file: UploadFile, destination: Path) -> None:
    total_written = 0
    with destination.open("wb") as out:
        while True:
            chunk = file.file.read(CHUNK_SIZE)
            if not chunk:
                break
            total_written += len(chunk)
            if total_written > MAX_SIZE_BYTES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Archivo demasiado grande. Máximo: {MAX_SIZE_MB} MB",
                )
            out.write(chunk)


def persist_public_upload(file: UploadFile, public_base_url: str) -> dict:
    """
    Guarda en uploads/ con nombre único. Devuelve url y filename.
    El caller debe validar rol; aquí solo validación de archivo.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo vacío")
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Extensión no permitida. Permitidas: {allowed_upload_extensions_message()}",
        )
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = UPLOADS_DIR / unique_name
    try:
        _ensure_uploads_dir()
        _save_upload_stream(file, file_path)
    except HTTPException:
        if file_path.exists():
            file_path.unlink(missing_ok=True)
        raise
    except OSError as e:
        if file_path.exists():
            file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Error al guardar archivo: {str(e)}") from e

    base = public_base_url.rstrip("/")
    url = f"{base}/uploads/{unique_name}"
    return {"url": url, "filename": unique_name}


def persist_staff_user_upload(file: UploadFile, public_base_url: str, user) -> dict:
    """Solo Admin o Profesional; delega en persist_public_upload."""
    if getattr(user, "role", None) not in ("ADMIN", "PROFESIONAL"):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    return persist_public_upload(file, public_base_url)

"""Persistencia de fotos de perfil de usuario."""
from __future__ import annotations

import uuid
from pathlib import Path
from urllib.parse import urlparse

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session as OrmSession

from app.models.user import User

PROFILE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
PROFILE_MAX_MB = 5
PROFILE_MAX_BYTES = PROFILE_MAX_MB * 1024 * 1024
PROFILE_CHUNK_SIZE = 1024 * 1024
PROFILE_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "profiles"


def allowed_profile_extensions_message() -> str:
    return ", ".join(sorted(PROFILE_EXTENSIONS))


def _ensure_profile_dir() -> None:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)


def _save_profile_stream(file: UploadFile, destination: Path) -> None:
    total_written = 0
    with destination.open("wb") as out:
        while True:
            chunk = file.file.read(PROFILE_CHUNK_SIZE)
            if not chunk:
                break
            total_written += len(chunk)
            if total_written > PROFILE_MAX_BYTES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Imagen demasiado grande. Máximo: {PROFILE_MAX_MB} MB",
                )
            out.write(chunk)


def persist_profile_photo_upload(
    db: OrmSession,
    user: User,
    file: UploadFile,
    public_base_url: str,
) -> str:
    """
    Guarda imagen en disco, elimina la anterior si estaba en /uploads/profiles/,
    actualiza user.profile_photo_url y hace commit. Devuelve la URL pública.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo vacío")
    ext = Path(file.filename).suffix.lower()
    if ext not in PROFILE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Extensión no permitida. Permitidas: {allowed_profile_extensions_message()}",
        )

    _ensure_profile_dir()
    unique_name = f"profile_{user.id}_{uuid.uuid4().hex}{ext}"
    file_path = PROFILE_DIR / unique_name
    try:
        _save_profile_stream(file, file_path)
    except HTTPException:
        if file_path.exists():
            file_path.unlink(missing_ok=True)
        raise
    except OSError as e:
        if file_path.exists():
            file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Error al guardar archivo: {str(e)}") from e
    finally:
        file.file.close()

    if user.profile_photo_url:
        try:
            parsed = urlparse(user.profile_photo_url)
            old_path = parsed.path or ""
            if old_path.startswith("/uploads/profiles/"):
                old_name = old_path.replace("/uploads/profiles/", "", 1)
                old_file = PROFILE_DIR / old_name
                if old_file.exists():
                    old_file.unlink(missing_ok=True)
        except Exception:
            pass

    base = public_base_url.rstrip("/")
    user.profile_photo_url = f"{base}/uploads/profiles/{unique_name}"
    db.commit()
    return user.profile_photo_url

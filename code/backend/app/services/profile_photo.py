"""Persistencia de fotos de perfil de usuario."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session as OrmSession

from app.core.storage import get_storage
from app.models.user import User

PROFILE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
PROFILE_MAX_MB = 5
PROFILE_MAX_BYTES = PROFILE_MAX_MB * 1024 * 1024


def allowed_profile_extensions_message() -> str:
    return ", ".join(sorted(PROFILE_EXTENSIONS))


def persist_profile_photo_upload(
    db: OrmSession,
    user: User,
    file: UploadFile,
    public_base_url: str,
) -> str:
    """
    Guarda imagen, elimina la anterior si estaba en nuestro almacenamiento,
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

    storage = get_storage()
    unique_name = f"profile_{user.id}_{uuid.uuid4().hex}{ext}"
    relative_key = f"profiles/{unique_name}"

    try:
        url, _n = storage.save_upload(
            file,
            relative_key=relative_key,
            max_bytes=PROFILE_MAX_BYTES,
            public_base_url=public_base_url,
            oversize_detail=f"Imagen demasiado grande. Máximo: {PROFILE_MAX_MB} MB",
        )
    finally:
        try:
            file.file.close()
        except Exception:
            pass

    if user.profile_photo_url:
        try:
            storage.delete_public_url(user.profile_photo_url)
        except Exception:
            pass

    user.profile_photo_url = url
    db.commit()
    return user.profile_photo_url

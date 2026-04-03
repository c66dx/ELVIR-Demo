"""Persistencia de fotos de perfil de jóvenes."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session as OrmSession

from app.core.storage import get_storage
from app.models.youth import Youth

YOUTH_PHOTO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
YOUTH_PHOTO_MAX_MB = 5
YOUTH_PHOTO_MAX_BYTES = YOUTH_PHOTO_MAX_MB * 1024 * 1024


def allowed_youth_photo_extensions_message() -> str:
    return ", ".join(sorted(YOUTH_PHOTO_EXTENSIONS))


def persist_youth_photo_upload(
    db: OrmSession,
    youth: Youth,
    file: UploadFile,
    public_base_url: str,
) -> str:
    """
    Guarda imagen, elimina la anterior si estaba en nuestro almacenamiento,
    actualiza youth.photo_url y hace commit + refresh. Devuelve la URL pública.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo vacío")
    ext = Path(file.filename).suffix.lower()
    if ext not in YOUTH_PHOTO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Extensión no permitida. Permitidas: {allowed_youth_photo_extensions_message()}",
        )

    storage = get_storage()
    unique_name = f"youth_{youth.id}_{uuid.uuid4().hex}{ext}"
    relative_key = f"youths/{unique_name}"

    try:
        url, _n = storage.save_upload(
            file,
            relative_key=relative_key,
            max_bytes=YOUTH_PHOTO_MAX_BYTES,
            public_base_url=public_base_url,
            oversize_detail=f"Imagen demasiado grande. Máximo: {YOUTH_PHOTO_MAX_MB} MB",
        )
    finally:
        try:
            file.file.close()
        except Exception:
            pass

    if youth.photo_url:
        try:
            storage.delete_public_url(youth.photo_url)
        except Exception:
            pass

    youth.photo_url = url
    db.commit()
    db.refresh(youth)
    return youth.photo_url

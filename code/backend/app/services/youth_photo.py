"""Persistencia de fotos de perfil de jóvenes (archivo en /uploads/youths)."""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session as OrmSession

from app.models.youth import Youth

YOUTH_PHOTO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
YOUTH_PHOTO_MAX_MB = 5
YOUTH_PHOTO_MAX_BYTES = YOUTH_PHOTO_MAX_MB * 1024 * 1024
YOUTH_PHOTO_CHUNK_SIZE = 1024 * 1024
YOUTH_PHOTO_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "youths"


def allowed_youth_photo_extensions_message() -> str:
    return ", ".join(sorted(YOUTH_PHOTO_EXTENSIONS))


def _ensure_youth_photo_dir() -> None:
    YOUTH_PHOTO_DIR.mkdir(parents=True, exist_ok=True)


def _save_youth_photo_stream(file: UploadFile, destination: Path) -> None:
    total_written = 0
    with destination.open("wb") as out:
        while True:
            chunk = file.file.read(YOUTH_PHOTO_CHUNK_SIZE)
            if not chunk:
                break
            total_written += len(chunk)
            if total_written > YOUTH_PHOTO_MAX_BYTES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Imagen demasiado grande. Máximo: {YOUTH_PHOTO_MAX_MB} MB",
                )
            out.write(chunk)


def persist_youth_photo_upload(
    db: OrmSession,
    youth: Youth,
    file: UploadFile,
    public_base_url: str,
) -> str:
    """
    Guarda imagen en disco, elimina la anterior si estaba en /uploads/youths/,
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

    _ensure_youth_photo_dir()
    unique_name = f"youth_{youth.id}_{uuid.uuid4().hex}{ext}"
    file_path = YOUTH_PHOTO_DIR / unique_name
    try:
        _save_youth_photo_stream(file, file_path)
    except HTTPException:
        if file_path.exists():
            file_path.unlink(missing_ok=True)
        raise
    except OSError as e:
        if file_path.exists():
            file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Error al guardar archivo: {str(e)}") from e
    finally:
        try:
            file.file.close()
        except Exception:
            pass

    if youth.photo_url and "/uploads/youths/" in youth.photo_url:
        try:
            old_name = youth.photo_url.split("/uploads/youths/")[-1]
            old_path = YOUTH_PHOTO_DIR / old_name
            if old_path.exists():
                old_path.unlink(missing_ok=True)
        except Exception:
            pass

    base = public_base_url.rstrip("/")
    youth.photo_url = f"{base}/uploads/youths/{unique_name}"
    db.commit()
    db.refresh(youth)
    return youth.photo_url

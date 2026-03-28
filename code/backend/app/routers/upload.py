"""Router para subida de archivos (material de apoyo)."""
from fastapi import APIRouter, Depends, UploadFile, File, Request

from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.upload_files import persist_staff_user_upload

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("")
def upload_file(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """
    Sube un archivo (PDF o video). Solo Admin y Profesional.
    Devuelve la URL para usar en material de apoyo.
    """
    try:
        base = f"{request.url.scheme}://{request.url.netloc}".rstrip("/")
        return persist_staff_user_upload(file, base, user)
    finally:
        try:
            file.file.close()
        except Exception:
            pass

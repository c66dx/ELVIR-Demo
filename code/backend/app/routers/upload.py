"""Router para subida de archivos (material de apoyo)."""

from fastapi import APIRouter, Depends, File, Request, UploadFile

from app.config import settings
from app.core.dependencies import get_current_user
from app.core.limiter import limiter
from app.models.user import User
from app.services.upload_files import persist_staff_user_upload

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("", summary="Subir archivo para material (PDF o video)")
@limiter.limit(settings.STAFF_UPLOAD_RATE_LIMIT)
def upload_file(
    request: Request,
    file: UploadFile = File(..., description="PDF o video; máximo 50 MB"),
    user: User = Depends(get_current_user),
):
    """
    Sube un archivo (PDF o video). Solo Admin y Profesional.
    Devuelve `url` absoluta bajo `/uploads/...` para usar en material de apoyo.
    """
    base = f"{request.url.scheme}://{request.url.netloc}".rstrip("/")
    return persist_staff_user_upload(file, base, user)

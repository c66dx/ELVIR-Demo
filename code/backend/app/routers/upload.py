"""Router para subida de archivos (material de apoyo)."""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request

from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/upload", tags=["upload"])

# Carpeta de uploads relativa al directorio del backend
UPLOADS_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
ALLOWED_EXTENSIONS = {".pdf", ".mp4", ".webm", ".mov", ".avi", ".mkv"}
MAX_SIZE_MB = 50


def _ensure_uploads_dir():
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


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
    if user.role not in ("ADMIN", "PROFESIONAL"):
        raise HTTPException(status_code=403, detail="Acceso denegado")

    if not file.filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo vacío")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Extensión no permitida. Permitidas: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    _ensure_uploads_dir()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = UPLOADS_DIR / unique_name

    try:
        content = file.file.read()
        if len(content) > MAX_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"Archivo demasiado grande. Máximo: {MAX_SIZE_MB} MB",
            )
        file_path.write_bytes(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar: {str(e)}")
    finally:
        file.file.close()

    # URL completa para que el frontend la use en material
    base = f"{request.url.scheme}://{request.url.netloc}".rstrip("/")
    url = f"{base}/uploads/{unique_name}"
    return {"url": url, "filename": unique_name}

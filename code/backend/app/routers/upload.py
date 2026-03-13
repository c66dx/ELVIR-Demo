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
CHUNK_SIZE = 1024 * 1024  # 1 MB
MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024


def _ensure_uploads_dir():
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def _save_upload_stream(file: UploadFile, destination: Path) -> None:
    """Guarda archivo por chunks para evitar cargar todo en memoria."""
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
        if user.role not in ("ADMIN", "PROFESIONAL"):
            raise HTTPException(status_code=403, detail="Acceso denegado")

        if not file.filename:
            raise HTTPException(status_code=400, detail="Nombre de archivo vacío")

        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Extensión no permitida. Permitidas: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
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
            raise HTTPException(status_code=500, detail=f"Error al guardar archivo: {str(e)}")

        # URL completa para que el frontend la use en material
        base = f"{request.url.scheme}://{request.url.netloc}".rstrip("/")
        url = f"{base}/uploads/{unique_name}"
        return {"url": url, "filename": unique_name}
    finally:
        file.file.close()


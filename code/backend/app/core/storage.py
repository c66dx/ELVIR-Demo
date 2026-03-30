"""Almacenamiento de ficheros: disco local (default) o S3-compatible (escala horizontal)."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from fastapi import HTTPException, UploadFile

from app.config import settings

CHUNK_SIZE = 1024 * 1024
UPLOADS_ROOT = Path(__file__).resolve().parent.parent.parent / "uploads"


def _safe_relative_key(relative_key: str) -> str:
    """Normaliza y valida la clave bajo uploads/ (sin .. ni absolutos)."""
    rel = relative_key.replace("\\", "/").strip("/")
    parts = tuple(p for p in rel.split("/") if p and p != ".")
    if not parts or ".." in parts:
        raise HTTPException(status_code=400, detail="Ruta de almacenamiento inválida")
    return "/".join(parts)


def _stream_upload_to_path(file: UploadFile, dest: Path, max_bytes: int, *, oversize_detail: str | None = None) -> int:
    total = 0
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as out:
        while True:
            chunk = file.file.read(CHUNK_SIZE)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise HTTPException(
                    status_code=400,
                    detail=oversize_detail or "Archivo demasiado grande",
                )
            out.write(chunk)
    return total


class LocalStorageBackend:
    """Ficheros bajo `uploads/`; URLs `{public_base}/uploads/{relative_key}`."""

    def __init__(self, root: Path = UPLOADS_ROOT) -> None:
        self.root = root.resolve()

    def save_upload(
        self,
        file: UploadFile,
        *,
        relative_key: str,
        max_bytes: int,
        public_base_url: str,
        oversize_detail: str | None = None,
    ) -> tuple[str, int]:
        key = _safe_relative_key(relative_key)
        dest = self.root.joinpath(*Path(key).parts)
        if not dest.resolve().is_relative_to(self.root):
            raise HTTPException(status_code=400, detail="Ruta de almacenamiento inválida")
        try:
            nbytes = _stream_upload_to_path(file, dest, max_bytes, oversize_detail=oversize_detail)
        except HTTPException:
            if dest.exists():
                dest.unlink(missing_ok=True)
            raise
        except OSError as e:
            if dest.exists():
                dest.unlink(missing_ok=True)
            raise HTTPException(status_code=500, detail=f"Error al guardar archivo: {e!s}") from e

        base = public_base_url.rstrip("/")
        return f"{base}/uploads/{key}", nbytes

    def delete_public_url(self, url: str | None) -> bool:
        if not url:
            return False
        try:
            path = urlparse(url).path or ""
            prefix = "/uploads/"
            if not path.startswith(prefix):
                return False
            rel = path[len(prefix) :].lstrip("/")
            if not rel or ".." in rel.split("/"):
                return False
            dest = self.root.joinpath(*Path(rel).parts)
            if not dest.resolve().is_relative_to(self.root):
                return False
            if dest.is_file():
                dest.unlink(missing_ok=True)
                return True
        except (OSError, ValueError):
            return False
        return False


class S3StorageBackend:
    """S3 / MinIO / R2: objeto `{S3_KEY_PREFIX}{relative_key}`; URL pública configurable."""

    def __init__(self) -> None:
        import boto3

        self._bucket = settings.S3_BUCKET
        self._public_base = settings.S3_PUBLIC_BASE_URL.rstrip("/")
        prefix = (settings.S3_KEY_PREFIX or "").strip().strip("/")
        self._key_prefix = f"{prefix}/" if prefix else ""

        self._client = boto3.client(
            "s3",
            region_name=settings.S3_REGION or "us-east-1",
            endpoint_url=settings.S3_ENDPOINT_URL or None,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID or None,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY or None,
        )

    def _object_key(self, relative_key: str) -> str:
        key = _safe_relative_key(relative_key)
        return f"{self._key_prefix}{key}"

    def save_upload(
        self,
        file: UploadFile,
        *,
        relative_key: str,
        max_bytes: int,
        public_base_url: str,
        oversize_detail: str | None = None,
    ) -> tuple[str, int]:
        _ = public_base_url  # S3 usa URL pública fija de settings
        object_key = self._object_key(relative_key)
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            nbytes = _stream_upload_to_path(file, tmp_path, max_bytes, oversize_detail=oversize_detail)
            self._client.upload_file(str(tmp_path), self._bucket, object_key)
        except HTTPException:
            raise
        except OSError as e:
            raise HTTPException(status_code=500, detail=f"Error al guardar archivo: {e!s}") from e
        finally:
            tmp_path.unlink(missing_ok=True)

        return f"{self._public_base}/{object_key}", nbytes

    def delete_public_url(self, url: str | None) -> bool:
        if not url:
            return False
        if not url.startswith(self._public_base):
            return False
        suffix = url[len(self._public_base) :].lstrip("/")
        if not suffix:
            return False
        try:
            self._client.delete_object(Bucket=self._bucket, Key=suffix)
            return True
        except Exception:
            return False


_backend: LocalStorageBackend | S3StorageBackend | None = None


def get_storage() -> LocalStorageBackend | S3StorageBackend:
    global _backend
    if _backend is None:
        kind: Literal["local", "s3"] = settings.STORAGE_BACKEND  # type: ignore[assignment]
        if kind == "s3":
            _backend = S3StorageBackend()
        else:
            _backend = LocalStorageBackend()
    return _backend


def reset_storage_cache_for_tests() -> None:
    """Solo tests: fuerza recreación tras cambiar settings."""
    global _backend
    _backend = None

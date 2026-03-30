#!/usr/bin/env python3
"""
Copia ficheros desde code/backend/uploads/ hacia un bucket S3-compatible.

Las claves de objeto coinciden con el backend cuando STORAGE_BACKEND=s3
(prefijo S3_KEY_PREFIX + ruta relativa bajo uploads/).

Uso (PowerShell, desde la raíz del repo):
  cd code/backend
  ..\\..\\scripts\\migrate_uploads_to_s3.py --dry-run

Linux/macOS:
  cd code/backend && ../../scripts/migrate_uploads_to_s3.py --dry-run

Variables de entorno (mismas que el backend para S3):
  S3_BUCKET, S3_REGION, S3_PUBLIC_BASE_URL, S3_KEY_PREFIX (opcional),
  S3_ENDPOINT_URL (opcional, MinIO), S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY

Opcional: cargar un .env antes de ejecutar, p. ej. `set -a; source .env; set +a` en bash.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from botocore.exceptions import ClientError


def _is_not_found_head(e: ClientError) -> bool:
    err = e.response.get("Error", {}) or {}
    code = err.get("Code", "")
    if code in ("404", "NotFound", "NoSuchKey"):
        return True
    status = e.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
    return status == 404


def _normalize_prefix(prefix: str) -> str:
    p = (prefix or "").strip().strip("/")
    return f"{p}/" if p else ""


def _object_key(relative_under_uploads: str, key_prefix: str) -> str:
    rel = relative_under_uploads.replace("\\", "/").strip("/")
    parts = tuple(p for p in rel.split("/") if p and p != ".")
    if not parts or ".." in parts:
        raise ValueError(f"Ruta inválida: {relative_under_uploads!r}")
    return f"{key_prefix}{'/'.join(parts)}"


def _s3_client():
    import boto3

    return boto3.client(
        "s3",
        region_name=os.environ.get("S3_REGION") or "us-east-1",
        endpoint_url=os.environ.get("S3_ENDPOINT_URL") or None,
        aws_access_key_id=os.environ.get("S3_ACCESS_KEY_ID") or None,
        aws_secret_access_key=os.environ.get("S3_SECRET_ACCESS_KEY") or None,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrar uploads/ locales a S3.")
    parser.add_argument(
        "--uploads-dir",
        type=Path,
        default=None,
        help="Carpeta uploads (default: code/backend/uploads junto al repo)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo listar acciones, sin subir",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="No sobrescribir si el objeto ya existe (comprueba con head_object)",
    )
    args = parser.parse_args()

    bucket = (os.environ.get("S3_BUCKET") or "").strip()
    if not bucket:
        print("Error: define S3_BUCKET", file=sys.stderr)
        return 1

    key_prefix = _normalize_prefix(os.environ.get("S3_KEY_PREFIX", ""))

    repo_root = Path(__file__).resolve().parent.parent
    uploads = args.uploads_dir
    if uploads is None:
        uploads = repo_root / "code" / "backend" / "uploads"
    uploads = uploads.resolve()

    if not uploads.is_dir():
        print(f"Error: no existe la carpeta {uploads}", file=sys.stderr)
        return 1

    files: list[Path] = []
    for path in uploads.rglob("*"):
        if path.is_file() and path.name != ".gitkeep":
            files.append(path)

    if not files:
        print(f"No hay ficheros en {uploads}")
        return 0

    client = None if args.dry_run else _s3_client()
    uploaded = 0
    skipped = 0
    errors = 0

    for local in sorted(files):
        try:
            rel = local.relative_to(uploads).as_posix()
            key = _object_key(rel, key_prefix)
        except ValueError as e:
            print(f"Omitido {local}: {e}", file=sys.stderr)
            errors += 1
            continue

        if args.dry_run:
            print(f"[dry-run] {local} -> s3://{bucket}/{key}")
            uploaded += 1
            continue

        assert client is not None
        if args.skip_existing:
            try:
                client.head_object(Bucket=bucket, Key=key)
                print(f"[skip exists] s3://{bucket}/{key}")
                skipped += 1
                continue
            except ClientError as e:
                if not _is_not_found_head(e):
                    print(f"Error head {key}: {e}", file=sys.stderr)
                    errors += 1
                    continue

        try:
            client.upload_file(str(local), bucket, key)
            print(f"OK s3://{bucket}/{key}")
            uploaded += 1
        except Exception as e:
            print(f"Error {local}: {e}", file=sys.stderr)
            errors += 1

    print(
        f"\nResumen: subidos={uploaded}, omitidos={skipped}, errores={errors}, total_ficheros={len(files)}"
    )
    public_base = (os.environ.get("S3_PUBLIC_BASE_URL") or "").rstrip("/")
    if public_base:
        print(
            "\nTras la migración, actualiza la app con STORAGE_BACKEND=s3 y las mismas variables."
        )
        print(
            "Las URLs en la BD deben pasar de http(s)://<api>/uploads/... a "
            f"{public_base}/<clave> (la clave incluye el prefijo si usas S3_KEY_PREFIX)."
        )
        print(
            "Puedes generar SQL de reemplazo según tu host antiguo, o un script que recorra tablas."
        )
    return 0 if errors == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

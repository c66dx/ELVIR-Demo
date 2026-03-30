import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException, UploadFile
from starlette.requests import Request

from app.core.storage import LocalStorageBackend, _stream_upload_to_path
from app.routers import upload
from app.services import upload_files

TEST_TMP_BASE = Path(__file__).resolve().parent / "_tmp"
TEST_TMP_BASE.mkdir(parents=True, exist_ok=True)


def _upload_router_request(*, scheme: str = "http", host: str = "api.local") -> Request:
    """Request ASGI mínimo (slowapi exige starlette.requests.Request en la vista)."""
    port = 443 if scheme == "https" else 80
    return Request(
        scope={
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": scheme,
            "path": "/api/v1/upload",
            "raw_path": b"/api/v1/upload",
            "root_path": "",
            "query_string": b"",
            "headers": [(b"host", host.encode("ascii"))],
            "client": ("127.0.0.1", 12345),
            "server": (host, port),
        }
    )


def _tempdir():
    return tempfile.TemporaryDirectory(dir=TEST_TMP_BASE)


class UploadStreamTestCase(unittest.TestCase):
    def test_stream_to_path_success(self):
        with _tempdir() as tmpdir:
            dest = Path(tmpdir) / "out.pdf"
            file = UploadFile(filename="test.pdf", file=BytesIO(b"hola" * 100))
            _stream_upload_to_path(file, dest, upload_files.MAX_SIZE_BYTES)
            self.assertTrue(dest.exists())
            self.assertGreater(dest.stat().st_size, 0)

    def test_upload_rejects_extension_with_sorted_detail(self):
        class DummyUser:
            role = "ADMIN"

        file = UploadFile(filename="archivo.exe", file=BytesIO(b"x"))
        with self.assertRaises(HTTPException) as ctx:
            upload.upload_file(request=_upload_router_request(), file=file, user=DummyUser())

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Extensión no permitida", ctx.exception.detail)
        expected = ", ".join(sorted(upload_files.ALLOWED_EXTENSIONS))
        self.assertIn(expected, ctx.exception.detail)
        self.assertTrue(file.file.closed)

    def test_upload_rejects_user_without_allowed_role(self):
        class DummyUser:
            role = "JOVEN"

        file = UploadFile(filename="archivo.pdf", file=BytesIO(b"x"))
        with self.assertRaises(HTTPException) as ctx:
            upload.upload_file(request=_upload_router_request(), file=file, user=DummyUser())

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.detail, "Acceso denegado")
        self.assertTrue(file.file.closed)

    def test_upload_rejects_empty_filename(self):
        class DummyUser:
            role = "ADMIN"

        file = UploadFile(filename="", file=BytesIO(b"x"))
        with self.assertRaises(HTTPException) as ctx:
            upload.upload_file(request=_upload_router_request(), file=file, user=DummyUser())

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail, "Nombre de archivo vacío")
        self.assertTrue(file.file.closed)

    def test_stream_accepts_exact_size_limit(self):
        with _tempdir() as tmpdir:
            dest = Path(tmpdir) / "out.webm"
            file = UploadFile(filename="test.webm", file=BytesIO(b"x" * upload_files.MAX_SIZE_BYTES))
            _stream_upload_to_path(file, dest, upload_files.MAX_SIZE_BYTES)
            self.assertTrue(dest.exists())
            self.assertEqual(dest.stat().st_size, upload_files.MAX_SIZE_BYTES)

    def test_stream_size_limit(self):
        with _tempdir() as tmpdir:
            dest = Path(tmpdir) / "out.mp4"
            file = UploadFile(filename="test.mp4", file=BytesIO(b"x" * (upload_files.MAX_SIZE_BYTES + 1)))
            with self.assertRaises(HTTPException):
                _stream_upload_to_path(file, dest, upload_files.MAX_SIZE_BYTES)

    def test_upload_maps_oserror_and_cleans_partial_file(self):
        class DummyUser:
            role = "ADMIN"

        class DummyUUID:
            hex = "fixedid"

        with _tempdir() as tmpdir:
            uploads_root = Path(tmpdir)

            def fake_stream(file: UploadFile, destination: Path, max_bytes: int, **kwargs):
                destination.write_bytes(b"partial")
                raise OSError("disk full")

            file = UploadFile(filename="archivo.pdf", file=BytesIO(b"x"))
            with (
                patch("app.services.upload_files.get_storage", return_value=LocalStorageBackend(root=uploads_root)),
                patch("app.core.storage._stream_upload_to_path", side_effect=fake_stream),
                patch("app.services.upload_files.uuid.uuid4", return_value=DummyUUID()),
            ):
                with self.assertRaises(HTTPException) as ctx:
                    upload.upload_file(request=_upload_router_request(), file=file, user=DummyUser())

            self.assertEqual(ctx.exception.status_code, 500)
            self.assertIn("Error al guardar archivo", ctx.exception.detail)
            self.assertFalse((uploads_root / "fixedid.pdf").exists())
            self.assertTrue(file.file.closed)

    def test_upload_success_returns_url_and_filename(self):
        class DummyUser:
            role = "ADMIN"

        class DummyUUID:
            hex = "fixedid"

        req = _upload_router_request()

        with _tempdir() as tmpdir:
            uploads_root = Path(tmpdir)
            file = UploadFile(filename="archivo.pdf", file=BytesIO(b"contenido"))

            with (
                patch("app.services.upload_files.get_storage", return_value=LocalStorageBackend(root=uploads_root)),
                patch("app.services.upload_files.uuid.uuid4", return_value=DummyUUID()),
            ):
                result = upload.upload_file(request=req, file=file, user=DummyUser())

            self.assertEqual(result["filename"], "fixedid.pdf")
            self.assertEqual(result["url"], "http://api.local/uploads/fixedid.pdf")
            self.assertTrue((uploads_root / "fixedid.pdf").exists())
            self.assertTrue(file.file.closed)

    def test_upload_accepts_uppercase_extension(self):
        class DummyUser:
            role = "ADMIN"

        class DummyUUID:
            hex = "fixedid"

        req = _upload_router_request(scheme="https")

        with _tempdir() as tmpdir:
            uploads_root = Path(tmpdir)
            file = UploadFile(filename="MATERIAL.PDF", file=BytesIO(b"contenido"))

            with (
                patch("app.services.upload_files.get_storage", return_value=LocalStorageBackend(root=uploads_root)),
                patch("app.services.upload_files.uuid.uuid4", return_value=DummyUUID()),
            ):
                result = upload.upload_file(request=req, file=file, user=DummyUser())

            self.assertEqual(result["filename"], "fixedid.pdf")
            self.assertEqual(result["url"], "https://api.local/uploads/fixedid.pdf")
            self.assertTrue((uploads_root / "fixedid.pdf").exists())
            self.assertTrue(file.file.closed)

    def test_upload_oversize_request_cleans_partial_file(self):
        class DummyUser:
            role = "ADMIN"

        class DummyUUID:
            hex = "fixedid"

        with _tempdir() as tmpdir:
            uploads_root = Path(tmpdir)
            file = UploadFile(
                filename="archivo.mp4",
                file=BytesIO(b"x" * (upload_files.MAX_SIZE_BYTES + 1)),
            )

            with (
                patch("app.services.upload_files.get_storage", return_value=LocalStorageBackend(root=uploads_root)),
                patch("app.services.upload_files.uuid.uuid4", return_value=DummyUUID()),
            ):
                with self.assertRaises(HTTPException) as ctx:
                    upload.upload_file(request=_upload_router_request(), file=file, user=DummyUser())

            self.assertEqual(ctx.exception.status_code, 400)
            self.assertIn("Archivo demasiado grande", ctx.exception.detail)
            self.assertFalse((uploads_root / "fixedid.mp4").exists())
            self.assertTrue(file.file.closed)

    def test_upload_propagates_http_exception_and_cleans_partial_file(self):
        class DummyUser:
            role = "ADMIN"

        class DummyUUID:
            hex = "fixedid"

        with _tempdir() as tmpdir:
            uploads_root = Path(tmpdir)

            def fake_stream(file: UploadFile, destination: Path, max_bytes: int, **kwargs):
                destination.write_bytes(b"partial")
                raise HTTPException(status_code=400, detail="Archivo demasiado grande")

            file = UploadFile(filename="archivo.pdf", file=BytesIO(b"x"))
            with (
                patch("app.services.upload_files.get_storage", return_value=LocalStorageBackend(root=uploads_root)),
                patch("app.core.storage._stream_upload_to_path", side_effect=fake_stream),
                patch("app.services.upload_files.uuid.uuid4", return_value=DummyUUID()),
            ):
                with self.assertRaises(HTTPException) as ctx:
                    upload.upload_file(request=_upload_router_request(), file=file, user=DummyUser())

            self.assertEqual(ctx.exception.status_code, 400)
            self.assertEqual(ctx.exception.detail, "Archivo demasiado grande")
            self.assertFalse((uploads_root / "fixedid.pdf").exists())
            self.assertTrue(file.file.closed)


if __name__ == "__main__":
    unittest.main()

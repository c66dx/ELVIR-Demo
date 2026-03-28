import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException, UploadFile

from app.routers import upload
from app.services import upload_files

TEST_TMP_BASE = Path(__file__).resolve().parent / "_tmp"
TEST_TMP_BASE.mkdir(parents=True, exist_ok=True)

_DUMMY_REQUEST = SimpleNamespace(url=SimpleNamespace(scheme="http", netloc="api.local"))


def _tempdir():
    return tempfile.TemporaryDirectory(dir=TEST_TMP_BASE)


class UploadStreamTestCase(unittest.TestCase):


    def test_save_upload_stream_success(self):
        with _tempdir() as tmpdir:
            dest = Path(tmpdir) / "out.pdf"
            file = UploadFile(filename="test.pdf", file=BytesIO(b"hola" * 100))
            upload_files._save_upload_stream(file, dest)
            self.assertTrue(dest.exists())
            self.assertGreater(dest.stat().st_size, 0)


    def test_upload_rejects_extension_with_sorted_detail(self):
        class DummyUser:
            role = "ADMIN"

        file = UploadFile(filename="archivo.exe", file=BytesIO(b"x"))
        with self.assertRaises(HTTPException) as ctx:
            upload.upload_file(request=_DUMMY_REQUEST, file=file, user=DummyUser())

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
            upload.upload_file(request=_DUMMY_REQUEST, file=file, user=DummyUser())

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.detail, "Acceso denegado")
        self.assertTrue(file.file.closed)


    def test_upload_rejects_empty_filename(self):
        class DummyUser:
            role = "ADMIN"

        file = UploadFile(filename="", file=BytesIO(b"x"))
        with self.assertRaises(HTTPException) as ctx:
            upload.upload_file(request=_DUMMY_REQUEST, file=file, user=DummyUser())

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail, "Nombre de archivo vacío")
        self.assertTrue(file.file.closed)


    def test_save_upload_stream_accepts_exact_size_limit(self):
        with _tempdir() as tmpdir:
            dest = Path(tmpdir) / "out.webm"
            file = UploadFile(filename="test.webm", file=BytesIO(b"x" * upload_files.MAX_SIZE_BYTES))
            upload_files._save_upload_stream(file, dest)
            self.assertTrue(dest.exists())
            self.assertEqual(dest.stat().st_size, upload_files.MAX_SIZE_BYTES)


    def test_save_upload_stream_size_limit(self):
        with _tempdir() as tmpdir:
            dest = Path(tmpdir) / "out.mp4"
            file = UploadFile(filename="test.mp4", file=BytesIO(b"x" * (upload_files.MAX_SIZE_BYTES + 1)))
            with self.assertRaises(HTTPException):
                upload_files._save_upload_stream(file, dest)


    def test_upload_maps_ensure_dir_oserror_and_closes_file(self):
        class DummyUser:
            role = "ADMIN"

        file = UploadFile(filename="archivo.pdf", file=BytesIO(b"x"))
        with patch.object(upload_files, "_ensure_uploads_dir", side_effect=OSError("mkdir fail")):
            with self.assertRaises(HTTPException) as ctx:
                upload.upload_file(request=_DUMMY_REQUEST, file=file, user=DummyUser())

        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("Error al guardar archivo", ctx.exception.detail)
        self.assertTrue(file.file.closed)


    def test_upload_maps_oserror_and_cleans_partial_file(self):
        class DummyUser:
            role = "ADMIN"

        class DummyUUID:
            hex = "fixedid"

        with _tempdir() as tmpdir:
            uploads_dir = Path(tmpdir)

            def fake_save(_file: UploadFile, destination: Path):
                destination.write_bytes(b"partial")
                raise OSError("disk full")

            file = UploadFile(filename="archivo.pdf", file=BytesIO(b"x"))
            with (
                patch.object(upload_files, "UPLOADS_DIR", uploads_dir),
                patch.object(upload_files, "_save_upload_stream", side_effect=fake_save),
                patch("app.services.upload_files.uuid.uuid4", return_value=DummyUUID()),
            ):
                with self.assertRaises(HTTPException) as ctx:
                    upload.upload_file(request=_DUMMY_REQUEST, file=file, user=DummyUser())

            self.assertEqual(ctx.exception.status_code, 500)
            self.assertIn("Error al guardar archivo", ctx.exception.detail)
            self.assertFalse((uploads_dir / "fixedid.pdf").exists())
            self.assertTrue(file.file.closed)


    def test_upload_success_returns_url_and_filename(self):
        class DummyUser:
            role = "ADMIN"

        class DummyUUID:
            hex = "fixedid"

        request = SimpleNamespace(url=SimpleNamespace(scheme="http", netloc="api.local"))

        with _tempdir() as tmpdir:
            uploads_dir = Path(tmpdir)
            file = UploadFile(filename="archivo.pdf", file=BytesIO(b"contenido"))

            with (
                patch.object(upload_files, "UPLOADS_DIR", uploads_dir),
                patch("app.services.upload_files.uuid.uuid4", return_value=DummyUUID()),
            ):
                result = upload.upload_file(request=request, file=file, user=DummyUser())

            self.assertEqual(result["filename"], "fixedid.pdf")
            self.assertEqual(result["url"], "http://api.local/uploads/fixedid.pdf")
            self.assertTrue((uploads_dir / "fixedid.pdf").exists())
            self.assertTrue(file.file.closed)


    def test_upload_accepts_uppercase_extension(self):
        class DummyUser:
            role = "ADMIN"

        class DummyUUID:
            hex = "fixedid"

        request = SimpleNamespace(url=SimpleNamespace(scheme="https", netloc="api.local"))

        with _tempdir() as tmpdir:
            uploads_dir = Path(tmpdir)
            file = UploadFile(filename="MATERIAL.PDF", file=BytesIO(b"contenido"))

            with (
                patch.object(upload_files, "UPLOADS_DIR", uploads_dir),
                patch("app.services.upload_files.uuid.uuid4", return_value=DummyUUID()),
            ):
                result = upload.upload_file(request=request, file=file, user=DummyUser())

            self.assertEqual(result["filename"], "fixedid.pdf")
            self.assertEqual(result["url"], "https://api.local/uploads/fixedid.pdf")
            self.assertTrue((uploads_dir / "fixedid.pdf").exists())
            self.assertTrue(file.file.closed)


    def test_upload_oversize_request_cleans_partial_file(self):
        class DummyUser:
            role = "ADMIN"

        class DummyUUID:
            hex = "fixedid"

        with _tempdir() as tmpdir:
            uploads_dir = Path(tmpdir)
            file = UploadFile(
                filename="archivo.mp4",
                file=BytesIO(b"x" * (upload_files.MAX_SIZE_BYTES + 1)),
            )

            with (
                patch.object(upload_files, "UPLOADS_DIR", uploads_dir),
                patch("app.services.upload_files.uuid.uuid4", return_value=DummyUUID()),
            ):
                with self.assertRaises(HTTPException) as ctx:
                    upload.upload_file(request=_DUMMY_REQUEST, file=file, user=DummyUser())

            self.assertEqual(ctx.exception.status_code, 400)
            self.assertIn("Archivo demasiado grande", ctx.exception.detail)
            self.assertFalse((uploads_dir / "fixedid.mp4").exists())
            self.assertTrue(file.file.closed)


    def test_upload_propagates_http_exception_and_cleans_partial_file(self):
        class DummyUser:
            role = "ADMIN"

        class DummyUUID:
            hex = "fixedid"

        with _tempdir() as tmpdir:
            uploads_dir = Path(tmpdir)

            def fake_save(_file: UploadFile, destination: Path):
                destination.write_bytes(b"partial")
                raise HTTPException(status_code=400, detail="Archivo demasiado grande")

            file = UploadFile(filename="archivo.pdf", file=BytesIO(b"x"))
            with (
                patch.object(upload_files, "UPLOADS_DIR", uploads_dir),
                patch.object(upload_files, "_save_upload_stream", side_effect=fake_save),
                patch("app.services.upload_files.uuid.uuid4", return_value=DummyUUID()),
            ):
                with self.assertRaises(HTTPException) as ctx:
                    upload.upload_file(request=_DUMMY_REQUEST, file=file, user=DummyUser())

            self.assertEqual(ctx.exception.status_code, 400)
            self.assertEqual(ctx.exception.detail, "Archivo demasiado grande")
            self.assertFalse((uploads_dir / "fixedid.pdf").exists())
            self.assertTrue(file.file.closed)


if __name__ == "__main__":
    unittest.main()

"""Tests de configuración de logging (JSON vs texto)."""
import json
import logging
import unittest
from types import SimpleNamespace

from app.core.logging_config import (
    ElvirTextFormatter,
    JsonLogFormatter,
    RequestIdContextFilter,
    emit_http_access_log,
)
from app.core.request_context import current_request_id


class JsonLogFormatterTestCase(unittest.TestCase):
    def test_includes_elvir_prefixed_extra(self):
        fmt = JsonLogFormatter()
        record = logging.LogRecord(
            name="elvir.api",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="http_request",
            args=(),
            exc_info=None,
        )
        record.elvir_request_id = "abc"
        record.elvir_method = "GET"
        record.elvir_path = "/health"
        record.elvir_status = 200
        record.elvir_duration_ms = 1.5
        record.elvir_event = "http_request"
        line = fmt.format(record)
        data = json.loads(line)
        self.assertEqual(data["request_id"], "abc")
        self.assertEqual(data["method"], "GET")
        self.assertEqual(data["path"], "/health")
        self.assertEqual(data["status"], 200)
        self.assertEqual(data["duration_ms"], 1.5)
        self.assertEqual(data["event"], "http_request")

    def test_request_id_filter_injects_from_context_json(self):
        fmt = JsonLogFormatter()
        flt = RequestIdContextFilter()
        token = current_request_id.set("ctx-rid-99")
        try:
            record = logging.LogRecord(
                name="elvir.api",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg="user_action",
                args=(),
                exc_info=None,
            )
            self.assertTrue(flt.filter(record))
            line = fmt.format(record)
            data = json.loads(line)
            self.assertEqual(data["request_id"], "ctx-rid-99")
            self.assertEqual(data["message"], "user_action")
        finally:
            current_request_id.reset(token)

    def test_elvir_text_formatter_prepends_request_id(self):
        fmt = ElvirTextFormatter(
            fmt="%(levelname)s [%(name)s] %(message)s",
        )
        record = logging.LogRecord(
            name="elvir.api",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="hello",
            args=(),
            exc_info=None,
        )
        record.elvir_request_id = "rid-1"
        line = fmt.format(record)
        self.assertTrue(line.startswith("request_id=rid-1 "))


class EmitHttpAccessLogTestCase(unittest.TestCase):
    def test_text_mode_uses_single_line_message(self):
        log = logging.getLogger("elvir.test.emit")
        log.handlers.clear()
        log.setLevel(logging.INFO)
        handler = logging.Handler()
        handler.level = logging.INFO
        captured: list[logging.LogRecord] = []

        def _emit(record: logging.LogRecord) -> None:
            captured.append(record)

        handler.emit = _emit  # type: ignore[method-assign]
        log.addHandler(handler)
        log.propagate = False

        settings = SimpleNamespace(use_json_logs=False)

        emit_http_access_log(
            log,
            settings,
            request_id="rid",
            method="GET",
            path="/x",
            status_code=200,
            duration_ms=3.0,
            error=False,
        )
        self.assertEqual(len(captured), 1)
        msg = captured[0].getMessage()
        self.assertIn("GET", msg)
        self.assertIn("/x", msg)
        self.assertIn("status=200", msg)

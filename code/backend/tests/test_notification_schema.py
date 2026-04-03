"""Esquema NotificationReadRequest."""
import unittest

from pydantic import ValidationError

from app.schemas.notification import NotificationReadRequest


class NotificationReadRequestTestCase(unittest.TestCase):
    def test_default_empty_ids(self):
        m = NotificationReadRequest()
        self.assertEqual(m.ids, [])

    def test_rejects_non_positive_id(self):
        with self.assertRaises(ValidationError):
            NotificationReadRequest(ids=[1, 0])


if __name__ == "__main__":
    unittest.main()

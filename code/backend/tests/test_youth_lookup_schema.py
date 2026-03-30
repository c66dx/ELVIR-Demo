"""Esquema POST /youths/lookup."""
import unittest

from pydantic import ValidationError

from app.schemas.youth import YouthLookupRequest


class YouthLookupRequestTestCase(unittest.TestCase):
    def test_dedupes_and_orders_first_seen(self):
        m = YouthLookupRequest(ids=[3, 1, 3, 2])
        self.assertEqual(m.ids, [3, 1, 2])

    def test_rejects_empty(self):
        with self.assertRaises(ValidationError):
            YouthLookupRequest(ids=[])

    def test_rejects_non_positive(self):
        with self.assertRaises(ValidationError):
            YouthLookupRequest(ids=[1, 0])


if __name__ == "__main__":
    unittest.main()

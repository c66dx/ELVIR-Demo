"""Tests de youth_to_response_with_contact."""
import unittest
from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.user import User
from app.models.youth import Youth
from app.models.youth_invitation import YouthInvitation
from app.services.youth_response import youth_to_response_with_contact


class YouthResponseServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()

        self.user = User(
            email="joven@test.cl",
            password_hash="x",
            role="JOVEN",
            is_active=True,
            profile_photo_url="https://example.com/p.jpg",
        )
        self.db.add(self.user)
        self.db.flush()

        self.youth_linked = Youth(
            user_id=self.user.id,
            display_name="J",
            identifier="JOV-1",
            login_enabled=True,
            is_active=True,
        )
        self.youth_pending = Youth(
            user_id=None,
            display_name="Pend",
            identifier="JOV-2",
            login_enabled=False,
            is_active=True,
        )
        self.db.add_all([self.youth_linked, self.youth_pending])
        self.db.flush()

        self.inv = YouthInvitation(
            youth_id=self.youth_pending.id,
            email="pending@test.cl",
            token="tok-pend",
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        self.db.add(self.inv)
        self.db.commit()
        self.db.refresh(self.youth_linked)
        self.db.refresh(self.youth_pending)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_with_user_resolves_email_and_photo(self):
        r = youth_to_response_with_contact(self.db, self.youth_linked)
        self.assertEqual(r.email, "joven@test.cl")
        self.assertEqual(r.profile_photo_url, "https://example.com/p.jpg")

    def test_pending_invitation_email_when_requested(self):
        r = youth_to_response_with_contact(
            self.db, self.youth_pending, include_pending_invitation_email=True
        )
        self.assertEqual(r.email, "pending@test.cl")

    def test_no_email_without_user_and_flag(self):
        r = youth_to_response_with_contact(
            self.db, self.youth_pending, include_pending_invitation_email=False
        )
        self.assertIsNone(r.email)


if __name__ == "__main__":
    unittest.main()

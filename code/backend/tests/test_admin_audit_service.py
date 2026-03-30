"""Tests de admin_audit_service (listado de audit logs)."""
import unittest
from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.audit_log import AuditLog
from app.models.user import User
from app.services.admin_audit_service import build_audit_log_list_response, fetch_audit_log_rows


class AdminAuditServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()

        self.actor = User(email="actor@test.cl", password_hash="x", role="ADMIN", is_active=True)
        self.db.add(self.actor)
        self.db.flush()

        now = datetime.now(UTC)
        self.db.add_all(
            [
                AuditLog(
                    request_id="req-a",
                    actor_user_id=self.actor.id,
                    actor_role="ADMIN",
                    action="LOGIN",
                    entity_type="session",
                    entity_id="1",
                    status_code=200,
                    method="POST",
                    path="/api/login",
                    ip_address="127.0.0.1",
                    user_agent="ua",
                    created_at=now,
                ),
                AuditLog(
                    request_id="req-b",
                    actor_user_id=None,
                    actor_role=None,
                    action="OTHER",
                    entity_type="x",
                    entity_id=None,
                    status_code=404,
                    method="GET",
                    path="/api/other",
                    created_at=now,
                ),
            ]
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_fetch_audit_log_rows_pagination_and_total(self):
        rows, total = fetch_audit_log_rows(
            self.db,
            page=1,
            page_size=1,
            search_term=None,
            action_term=None,
            entity_term=None,
            status_code=None,
            actor_user_id=None,
            method_term=None,
        )
        self.assertEqual(total, 2)
        self.assertEqual(len(rows), 1)

    def test_fetch_filter_by_action(self):
        rows, total = fetch_audit_log_rows(
            self.db,
            page=1,
            page_size=10,
            search_term=None,
            action_term="LOGIN",
            entity_term=None,
            status_code=None,
            actor_user_id=None,
            method_term=None,
        )
        self.assertEqual(total, 1)
        self.assertEqual(rows[0][0].action, "LOGIN")

    def test_fetch_search_matches_path(self):
        rows, total = fetch_audit_log_rows(
            self.db,
            page=1,
            page_size=10,
            search_term="login",
            action_term=None,
            entity_term=None,
            status_code=None,
            actor_user_id=None,
            method_term=None,
        )
        self.assertGreaterEqual(total, 1)

    def test_build_audit_log_list_response(self):
        out = build_audit_log_list_response(
            self.db,
            page=1,
            page_size=10,
            search_term=None,
            action_term=None,
            entity_term=None,
            status_code=None,
            actor_user_id=None,
            method_term=None,
        )
        self.assertEqual(out.meta.total, 2)
        self.assertEqual(len(out.items), 2)
        emails = {i.actor_email for i in out.items}
        self.assertIn("actor@test.cl", emails)


if __name__ == "__main__":
    unittest.main()

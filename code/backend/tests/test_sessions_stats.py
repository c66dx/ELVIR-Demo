import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.user import User
from app.models.youth import Youth
from app.models.job_role import JobRole
from app.models.case import Case
from app.models.simulation_template import SimulationTemplate
from app.models.session import Session as SessionModel
from app.routers.sessions import get_session_stats


class SessionsStatsTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()

        self.user = User(email="joven@test.cl", password_hash="x", role="JOVEN", is_active=True)
        self.db.add(self.user)
        self.db.flush()

        self.youth = Youth(
            user_id=self.user.id,
            display_name="Joven",
            identifier="JOV-001",
            login_enabled=True,
            is_active=True,
        )
        self.db.add(self.youth)
        self.db.flush()

        job_role = JobRole(
            slug="operario",
            name="Operario",
            description="Desc",
            objetivo="Obj",
            competencias="[]",
            is_active=True,
        )
        case = Case(
            slug="normal",
            name="Normal",
            difficulty="NORMAL",
            prompt_instructions="Instr",
            is_active=True,
        )
        self.db.add_all([job_role, case])
        self.db.flush()

        template = SimulationTemplate(
            job_role_id=job_role.id,
            case_id=case.id,
            liveavatar_context_id="ctx-1",
            liveavatar_avatar_id="avatar-1",
            liveavatar_voice_id="voice-1",
            is_active=True,
        )
        self.db.add(template)
        self.db.flush()

        now = datetime.now(timezone.utc)
        prev_month_anchor = (now.replace(day=1) - timedelta(days=1)).replace(day=15)

        s1 = SessionModel(
            youth_id=self.youth.id,
            professional_id=None,
            simulation_template_id=template.id,
            mode="AUTOGESTIONADA",
            status="COMPLETADA",
            started_at=now - timedelta(minutes=30),
            ended_at=now,
        )
        s2 = SessionModel(
            youth_id=self.youth.id,
            professional_id=None,
            simulation_template_id=template.id,
            mode="AUTOGESTIONADA",
            status="COMPLETADA",
            started_at=prev_month_anchor - timedelta(minutes=30),
            ended_at=prev_month_anchor,
        )
        s3 = SessionModel(
            youth_id=self.youth.id,
            professional_id=None,
            simulation_template_id=template.id,
            mode="AUTOGESTIONADA",
            status="CANCELADA",
            started_at=now - timedelta(days=2),
            ended_at=now - timedelta(days=2),
        )
        self.db.add_all([s1, s2, s3])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_stats_return_monthly_counts_in_sqlite(self):
        stats = get_session_stats(youth_id=None, months=2, user=self.user, db=self.db)
        self.assertEqual(stats.total, 3)
        self.assertEqual(stats.completed, 2)
        self.assertEqual(stats.cancelled, 1)

        month_map = {item.month: item.count for item in stats.monthly}
        self.assertEqual(sum(month_map.values()), 2)


if __name__ == "__main__":
    unittest.main()

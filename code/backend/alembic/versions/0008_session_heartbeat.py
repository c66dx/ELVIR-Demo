"""session heartbeat tracking

Revision ID: 0008_session_heartbeat
Revises: 0007_youth_notifications
"""
from alembic import op
import sqlalchemy as sa


revision = "0008_session_heartbeat"
down_revision = "0007_youth_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_sessions_last_heartbeat_at", "sessions", ["last_heartbeat_at"])
    op.execute("UPDATE sessions SET last_heartbeat_at = started_at WHERE last_heartbeat_at IS NULL")


def downgrade() -> None:
    op.drop_index("ix_sessions_last_heartbeat_at", table_name="sessions")
    op.drop_column("sessions", "last_heartbeat_at")

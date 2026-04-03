"""session heartbeat tracking

Revision ID: 0008_session_heartbeat
Revises: 0007_youth_notifications

0001 usa Base.metadata.create_all(), que ya refleja el modelo actual (incl. last_heartbeat_at).
Esta revisión debe ser idempotente para no duplicar columna/índice en installs desde cero.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0008_session_heartbeat"
down_revision = "0007_youth_notifications"
branch_labels = None
depends_on = None

_INDEX = "ix_sessions_last_heartbeat_at"
_COLUMN = "last_heartbeat_at"


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    col_names = {c["name"] for c in insp.get_columns("sessions")}
    if _COLUMN not in col_names:
        op.add_column(
            "sessions",
            sa.Column(_COLUMN, sa.DateTime(timezone=True), nullable=True),
        )
    idx_names = {i["name"] for i in insp.get_indexes("sessions") if i.get("name")}
    if _INDEX not in idx_names:
        op.create_index(_INDEX, "sessions", [_COLUMN])
    op.execute(
        f"UPDATE sessions SET {_COLUMN} = started_at WHERE {_COLUMN} IS NULL",
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    idx_names = {i["name"] for i in insp.get_indexes("sessions") if i.get("name")}
    if _INDEX in idx_names:
        op.drop_index(_INDEX, table_name="sessions")
    col_names = {c["name"] for c in insp.get_columns("sessions")}
    if _COLUMN in col_names:
        op.drop_column("sessions", _COLUMN)

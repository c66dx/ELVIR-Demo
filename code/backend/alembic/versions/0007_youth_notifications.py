"""agregar tabla youth_notifications

Revision ID: 0007_youth_notifications
Revises: 0006_youth_rut
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# identificadores de revision, usados por Alembic.
revision = "0007_youth_notifications"
down_revision = "0006_youth_rut"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if inspector.has_table("youth_notifications"):
        return
    if not inspector.has_table("youths"):
        return

    op.create_table(
        "youth_notifications",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("youth_id", sa.Integer(), sa.ForeignKey("youths.id"), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("link", sa.String(length=255), nullable=True),
        sa.Column("entity_type", sa.String(length=32), nullable=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("youth_id", "entity_type", "entity_id", name="uq_youth_notifications_entity"),
    )
    op.create_index("ix_youth_notifications_youth_id", "youth_notifications", ["youth_id"])
    op.create_index("ix_youth_notifications_entity_id", "youth_notifications", ["entity_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("youth_notifications"):
        return
    op.drop_index("ix_youth_notifications_entity_id", table_name="youth_notifications")
    op.drop_index("ix_youth_notifications_youth_id", table_name="youth_notifications")
    op.drop_table("youth_notifications")

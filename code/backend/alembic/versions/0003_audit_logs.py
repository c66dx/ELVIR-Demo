"""agregar tabla audit_logs

Revision ID: 0003_audit_logs
Revises: 0002_youth_identifier_unique
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# identificadores de revision, usados por Alembic.
revision = "0003_audit_logs"
down_revision = "0002_youth_identifier_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("audit_logs"):
        op.create_table(
            "audit_logs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("request_id", sa.String(length=64), nullable=True),
            sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("actor_role", sa.String(length=20), nullable=True),
            sa.Column("action", sa.String(length=50), nullable=False),
            sa.Column("entity_type", sa.String(length=50), nullable=True),
            sa.Column("entity_id", sa.String(length=64), nullable=True),
            sa.Column("status_code", sa.Integer(), nullable=False),
            sa.Column("method", sa.String(length=10), nullable=False),
            sa.Column("path", sa.String(length=255), nullable=False),
            sa.Column("ip_address", sa.String(length=64), nullable=True),
            sa.Column("user_agent", sa.String(length=255), nullable=True),
            sa.Column("payload", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
    index_names = {idx.get("name") for idx in inspector.get_indexes("audit_logs")} if inspector.has_table("audit_logs") else set()
    if "ix_audit_logs_request_id" not in index_names:
        op.create_index("ix_audit_logs_request_id", "audit_logs", ["request_id"])
    if "ix_audit_logs_actor_user_id" not in index_names:
        op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"])
    if "ix_audit_logs_entity" not in index_names:
        op.create_index("ix_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"])
    if "ix_audit_logs_created_at" not in index_names:
        op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("audit_logs"):
        return
    index_names = {idx.get("name") for idx in inspector.get_indexes("audit_logs")}
    if "ix_audit_logs_created_at" in index_names:
        op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    if "ix_audit_logs_entity" in index_names:
        op.drop_index("ix_audit_logs_entity", table_name="audit_logs")
    if "ix_audit_logs_actor_user_id" in index_names:
        op.drop_index("ix_audit_logs_actor_user_id", table_name="audit_logs")
    if "ix_audit_logs_request_id" in index_names:
        op.drop_index("ix_audit_logs_request_id", table_name="audit_logs")
    op.drop_table("audit_logs")


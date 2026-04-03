"""agregar profile_photo_url a users

Revision ID: 0004_user_profile_photo
Revises: 0003_audit_logs
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# identificadores de revision, usados por Alembic.
revision = "0004_user_profile_photo"
down_revision = "0003_audit_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("users"):
        return
    columns = {col["name"] for col in inspector.get_columns("users")}
    if "profile_photo_url" not in columns:
        op.add_column("users", sa.Column("profile_photo_url", sa.String(length=255), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("users"):
        return
    columns = {col["name"] for col in inspector.get_columns("users")}
    if "profile_photo_url" in columns:
        op.drop_column("users", "profile_photo_url")


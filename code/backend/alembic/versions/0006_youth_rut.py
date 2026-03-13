"""add rut and photo_url to youths

Revision ID: 0006_youth_rut
Revises: 0005_session_audio
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "0006_youth_rut"
down_revision = "0005_session_audio"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("youths"):
        return
    columns = {col["name"] for col in inspector.get_columns("youths")}
    indexes = inspector.get_indexes("youths")
    index_names = {idx.get("name") for idx in indexes}

    if "rut" not in columns:
        op.add_column("youths", sa.Column("rut", sa.String(length=20), nullable=True))
    if "photo_url" not in columns:
        op.add_column("youths", sa.Column("photo_url", sa.String(length=255), nullable=True))

    if "ix_youths_rut" not in index_names:
        op.create_index("ix_youths_rut", "youths", ["rut"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("youths"):
        return
    columns = {col["name"] for col in inspector.get_columns("youths")}
    indexes = inspector.get_indexes("youths")
    index_names = {idx.get("name") for idx in indexes}

    if "ix_youths_rut" in index_names:
        op.drop_index("ix_youths_rut", table_name="youths")
    if "photo_url" in columns:
        op.drop_column("youths", "photo_url")
    if "rut" in columns:
        op.drop_column("youths", "rut")

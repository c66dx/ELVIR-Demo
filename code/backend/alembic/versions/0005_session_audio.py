"""add session audio table

Revision ID: 0005_session_audio
Revises: 0004_user_profile_photo
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0005_session_audio"
down_revision = "0004_user_profile_photo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "session_audios",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
    )
    op.create_index("ix_session_audios_session_id", "session_audios", ["session_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_session_audios_session_id", table_name="session_audios")
    op.drop_table("session_audios")

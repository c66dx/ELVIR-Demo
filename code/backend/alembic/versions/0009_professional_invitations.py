"""professional invitations

Revision ID: 0009_professional_invitations
Revises: 0008_session_heartbeat
"""
from alembic import op
import sqlalchemy as sa


revision = "0009_professional_invitations"
down_revision = "0008_session_heartbeat"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "professional_invitations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("professional_id", sa.Integer(), sa.ForeignKey("professionals.id"), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("token", sa.String(length=255), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_professional_invitations_professional_id",
        "professional_invitations",
        ["professional_id"],
    )
    op.create_index(
        "ix_professional_invitations_token",
        "professional_invitations",
        ["token"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_professional_invitations_token", table_name="professional_invitations")
    op.drop_index("ix_professional_invitations_professional_id", table_name="professional_invitations")
    op.drop_table("professional_invitations")

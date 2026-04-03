"""professional invitations

Revision ID: 0009_professional_invitations
Revises: 0008_session_heartbeat

0001 usa Base.metadata.create_all(), que ya incluye professional_invitations.
Esta revisión es idempotente para installs desde cero.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0009_professional_invitations"
down_revision = "0008_session_heartbeat"
branch_labels = None
depends_on = None

_TABLE = "professional_invitations"
_IX_PRO = "ix_professional_invitations_professional_id"
_IX_TOKEN = "ix_professional_invitations_token"


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if _TABLE in insp.get_table_names():
        return
    op.create_table(
        _TABLE,
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("professional_id", sa.Integer(), sa.ForeignKey("professionals.id"), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("token", sa.String(length=255), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(_IX_PRO, _TABLE, ["professional_id"])
    op.create_index(_IX_TOKEN, _TABLE, ["token"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if _TABLE not in insp.get_table_names():
        return
    idx_names = {i["name"] for i in insp.get_indexes(_TABLE) if i.get("name")}
    if _IX_TOKEN in idx_names:
        op.drop_index(_IX_TOKEN, table_name=_TABLE)
    if _IX_PRO in idx_names:
        op.drop_index(_IX_PRO, table_name=_TABLE)
    op.drop_table(_TABLE)

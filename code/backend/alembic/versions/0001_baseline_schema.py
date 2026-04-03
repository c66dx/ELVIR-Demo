"""esquema base

Revision ID: 0001_baseline_schema
Revises:
"""
from __future__ import annotations

from alembic import op
from app.database import Base
import app.models  # noqa: F401 - asegurar modelos registrados

# identificadores de revision, usados por Alembic.
revision = "0001_baseline_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Base: crear esquema completo en base vacia.
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)


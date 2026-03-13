"""baseline schema

Revision ID: 0001_baseline_schema
Revises:
"""
from __future__ import annotations

# revision identifiers, used by Alembic.
revision = "0001_baseline_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Baseline inicial: esquema existente se considera estado base.
    # Próximas revisiones deben incluir cambios incrementales.
    pass


def downgrade() -> None:
    pass

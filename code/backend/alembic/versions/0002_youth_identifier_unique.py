"""add unique index for youths.identifier

Revision ID: 0002_youth_identifier_unique
Revises: 0001_baseline_schema
"""

from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "0002_youth_identifier_unique"
down_revision = "0001_baseline_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    indexes = inspector.get_indexes("youths")
    if not any(idx.get("name") == "ix_youths_identifier" for idx in indexes):
        op.create_index("ix_youths_identifier", "youths", ["identifier"], unique=True)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    indexes = inspector.get_indexes("youths")
    if any(idx.get("name") == "ix_youths_identifier" for idx in indexes):
        op.drop_index("ix_youths_identifier", table_name="youths")

"""campos contexto dinamico (roles/casos)

Revision ID: 0010_contexto_dinamico_fields
Revises: 0009_professional_invitations
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0010_contexto_dinamico_fields"
down_revision = "0009_professional_invitations"
branch_labels = None
depends_on = None

_JOB_ROLES = "job_roles"
_CASES = "cases"


def _has_column(insp, table: str, column: str) -> bool:
    return column in {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    if _JOB_ROLES in insp.get_table_names():
        if not _has_column(insp, _JOB_ROLES, "area"):
            op.add_column(_JOB_ROLES, sa.Column("area", sa.String(length=255), nullable=True))
        if not _has_column(insp, _JOB_ROLES, "nivel_experiencia"):
            op.add_column(_JOB_ROLES, sa.Column("nivel_experiencia", sa.String(length=255), nullable=True))
        if not _has_column(insp, _JOB_ROLES, "tecnologias"):
            op.add_column(_JOB_ROLES, sa.Column("tecnologias", sa.Text(), nullable=True))

    if _CASES in insp.get_table_names():
        if not _has_column(insp, _CASES, "description"):
            op.add_column(_CASES, sa.Column("description", sa.Text(), nullable=True))
        if not _has_column(insp, _CASES, "intervencion_regulacion_emocional"):
            op.add_column(_CASES, sa.Column("intervencion_regulacion_emocional", sa.Text(), nullable=True))
        if not _has_column(insp, _CASES, "intervencion_presentacion_personal"):
            op.add_column(_CASES, sa.Column("intervencion_presentacion_personal", sa.Text(), nullable=True))
        if not _has_column(insp, _CASES, "intervencion_expectativas_empresa"):
            op.add_column(_CASES, sa.Column("intervencion_expectativas_empresa", sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    if _CASES in insp.get_table_names():
        if _has_column(insp, _CASES, "intervencion_expectativas_empresa"):
            op.drop_column(_CASES, "intervencion_expectativas_empresa")
        if _has_column(insp, _CASES, "intervencion_presentacion_personal"):
            op.drop_column(_CASES, "intervencion_presentacion_personal")
        if _has_column(insp, _CASES, "intervencion_regulacion_emocional"):
            op.drop_column(_CASES, "intervencion_regulacion_emocional")
        if _has_column(insp, _CASES, "description"):
            op.drop_column(_CASES, "description")

    if _JOB_ROLES in insp.get_table_names():
        if _has_column(insp, _JOB_ROLES, "tecnologias"):
            op.drop_column(_JOB_ROLES, "tecnologias")
        if _has_column(insp, _JOB_ROLES, "nivel_experiencia"):
            op.drop_column(_JOB_ROLES, "nivel_experiencia")
        if _has_column(insp, _JOB_ROLES, "area"):
            op.drop_column(_JOB_ROLES, "area")

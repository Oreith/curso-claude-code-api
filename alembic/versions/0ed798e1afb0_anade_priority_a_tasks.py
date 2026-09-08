"""añade priority a tasks

Revision ID: 0ed798e1afb0
Revises: 7fe59d16aa51
Create Date: 2026-09-07 20:15:00.000000

Tareas v3: prioridad opcional (docs/contrato-api.md §Tareas v3). `VARCHAR`
nullable con CHECK que la limita al conjunto cerrado {BAJA, MEDIA, ALTA}.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0ed798e1afb0"
down_revision: str | Sequence[str] | None = "7fe59d16aa51"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CK = "ck_tasks_priority"
_VALORES = "'BAJA', 'MEDIA', 'ALTA'"


def upgrade() -> None:
    op.add_column("tasks", sa.Column("priority", sa.String, nullable=True))
    op.create_check_constraint(
        _CK, "tasks", f"priority IS NULL OR priority IN ({_VALORES})"
    )


def downgrade() -> None:
    op.drop_constraint(_CK, "tasks", type_="check")
    op.drop_column("tasks", "priority")

"""añade due_at a tasks

Revision ID: 7fe59d16aa51
Revises: 08b6d37b717e
Create Date: 2026-09-07 04:20:00.000000

Tareas v2: fecha límite opcional, con zona horaria, normalizada a UTC
(docs/contrato-api.md §Tareas v2). `TIMESTAMP WITH TIME ZONE` nullable.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7fe59d16aa51"
down_revision: str | Sequence[str] | None = "08b6d37b717e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tasks", "due_at")

"""crea la tabla tasks

Revision ID: 08b6d37b717e
Revises: fec3ded5126e
Create Date: 2026-09-06 22:45:00.000000

Solo esquema: la tabla `tasks` con sus columnas y claves foráneas. No hay
endpoints de tareas todavía (eso es "Tareas v1") ni el campo `due_at` ("Tareas
v2"). La tabla existe ya para que `DELETE /projects/{id}` pueda responder `409`
cuando un proyecto tiene tareas (docs/contrato-api.md §Proyectos).
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "08b6d37b717e"
down_revision: str | Sequence[str] | None = "fec3ded5126e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("description", sa.String, nullable=True),
        sa.Column(
            "project_id",
            sa.Integer,
            sa.ForeignKey("projects.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "state_id",
            sa.Integer,
            sa.ForeignKey("states.id", ondelete="RESTRICT"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("tasks")

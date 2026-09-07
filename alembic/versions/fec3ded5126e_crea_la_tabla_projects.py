"""crea la tabla projects

Revision ID: fec3ded5126e
Revises: 0b1b461bb5d6
Create Date: 2026-09-06 22:42:29.051858

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fec3ded5126e"
down_revision: str | Sequence[str] | None = "0b1b461bb5d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("description", sa.String, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("projects")

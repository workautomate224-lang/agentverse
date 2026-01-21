"""Fix run_outcomes foreign key to project_specs

The run_outcomes table was referencing the legacy 'projects' table,
but Blueprint V2 creates records in 'project_specs'. This migration
updates the foreign key constraint to reference project_specs.id.

Revision ID: 2026_01_21_0001
Revises: 2026_01_19_0001
Create Date: 2026-01-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = "2026_01_21_0001"
down_revision: Union[str, None] = "2026_01_19_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the old foreign key constraint referencing projects.id
    op.drop_constraint(
        "run_outcomes_project_id_fkey",
        "run_outcomes",
        type_="foreignkey"
    )

    # Create new foreign key constraint referencing project_specs.id
    op.create_foreign_key(
        "run_outcomes_project_id_fkey",
        "run_outcomes",
        "project_specs",
        ["project_id"],
        ["id"],
        ondelete="CASCADE"
    )


def downgrade() -> None:
    # Drop the new foreign key constraint
    op.drop_constraint(
        "run_outcomes_project_id_fkey",
        "run_outcomes",
        type_="foreignkey"
    )

    # Restore the old foreign key constraint referencing projects.id
    op.create_foreign_key(
        "run_outcomes_project_id_fkey",
        "run_outcomes",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE"
    )

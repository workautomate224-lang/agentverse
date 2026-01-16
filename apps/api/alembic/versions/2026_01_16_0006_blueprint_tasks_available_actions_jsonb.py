"""Convert blueprint_tasks.available_actions from VARCHAR[] to JSONB

Revision ID: blueprint_tasks_jsonb_001
Revises: blueprint_slots_jsonb_001
Create Date: 2026-01-16

The BlueprintTask model defines available_actions as JSONB,
but the database schema was never migrated from the original VARCHAR[] type.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = 'blueprint_tasks_jsonb_001'
down_revision = 'blueprint_slots_jsonb_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # First, drop the default constraint (it can't be cast automatically)
    op.execute("""
        ALTER TABLE blueprint_tasks
        ALTER COLUMN available_actions DROP DEFAULT
    """)

    # Convert available_actions from VARCHAR[] to JSONB
    op.execute("""
        ALTER TABLE blueprint_tasks
        ALTER COLUMN available_actions
        TYPE JSONB
        USING CASE
            WHEN available_actions IS NULL THEN NULL
            ELSE to_jsonb(available_actions)
        END
    """)

    # Set new default as NULL (column is nullable)
    # No default needed since nullable=True in the model


def downgrade() -> None:
    # Convert back to VARCHAR[] (may lose some data if JSONB has complex structures)
    op.execute("""
        ALTER TABLE blueprint_tasks
        ALTER COLUMN available_actions
        TYPE VARCHAR[]
        USING CASE
            WHEN available_actions IS NULL THEN NULL
            ELSE ARRAY(SELECT jsonb_array_elements_text(available_actions))
        END
    """)

"""Convert blueprint_slots.allowed_acquisition_methods from VARCHAR[] to JSONB

Revision ID: blueprint_slots_jsonb_001
Revises: blueprints_nullable_001
Create Date: 2026-01-16

The BlueprintSlot model defines allowed_acquisition_methods as JSONB,
but the database schema was never migrated from the original VARCHAR[] type.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = 'blueprint_slots_jsonb_001'
down_revision = 'blueprints_nullable_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Convert allowed_acquisition_methods from VARCHAR[] to JSONB
    op.execute("""
        ALTER TABLE blueprint_slots
        ALTER COLUMN allowed_acquisition_methods
        TYPE JSONB
        USING CASE
            WHEN allowed_acquisition_methods IS NULL THEN NULL
            ELSE to_jsonb(allowed_acquisition_methods)
        END
    """)


def downgrade() -> None:
    # Convert back to VARCHAR[] (may lose some data if JSONB has complex structures)
    op.execute("""
        ALTER TABLE blueprint_slots
        ALTER COLUMN allowed_acquisition_methods
        TYPE VARCHAR[]
        USING CASE
            WHEN allowed_acquisition_methods IS NULL THEN NULL
            ELSE ARRAY(SELECT jsonb_array_elements_text(allowed_acquisition_methods))
        END
    """)

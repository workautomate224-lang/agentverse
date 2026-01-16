"""Convert pil_jobs.artifact_ids from VARCHAR[] to JSONB

Revision ID: pil_jobs_jsonb_001
Revises: pil_artifacts_nullable_001
Create Date: 2026-01-16

The PILJob model defines artifact_ids as JSONB, but the database schema
was never migrated from the original VARCHAR[] type.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = 'pil_jobs_jsonb_001'
down_revision = 'pil_artifacts_nullable_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Convert artifact_ids from VARCHAR[] to JSONB
    # First, alter the column type with a USING clause to convert existing data
    op.execute("""
        ALTER TABLE pil_jobs
        ALTER COLUMN artifact_ids
        TYPE JSONB
        USING CASE
            WHEN artifact_ids IS NULL THEN NULL
            ELSE to_jsonb(artifact_ids)
        END
    """)


def downgrade() -> None:
    # Convert back to VARCHAR[] (may lose some data if JSONB has complex structures)
    op.execute("""
        ALTER TABLE pil_jobs
        ALTER COLUMN artifact_ids
        TYPE VARCHAR[]
        USING CASE
            WHEN artifact_ids IS NULL THEN NULL
            ELSE ARRAY(SELECT jsonb_array_elements_text(artifact_ids))
        END
    """)

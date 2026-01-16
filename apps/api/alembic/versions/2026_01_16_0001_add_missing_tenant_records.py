"""Add missing tenant records for existing users

Revision ID: missing_tenants_001
Revises: 2026_01_15_0004_add_more_pil_job_columns
Create Date: 2026-01-16

This migration ensures all existing users have corresponding tenant records.
The Blueprint table has a foreign key to tenants.id, so users without
tenant records cannot create blueprints.

This is a data-only migration (no schema changes).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "missing_tenants_001"
down_revision = "pil_jobs_columns_fix_002"
branch_labels = None
depends_on = None


def upgrade():
    """Create missing tenant records for users who don't have them."""
    conn = op.get_bind()

    # Find users without corresponding tenant records
    # For each user without a tenant, create a tenant with the same ID
    conn.execute(
        sa.text("""
            INSERT INTO tenants (id, name, slug, tier, is_active, settings, created_at, updated_at)
            SELECT
                u.id,
                COALESCE(u.full_name, split_part(u.email, '@', 1)),
                LOWER(REGEXP_REPLACE(
                    split_part(u.email, '@', 1) || '-' || LEFT(u.id::text, 8),
                    '[^a-z0-9-]', '-', 'g'
                )),
                COALESCE(u.tier, 'free'),
                u.is_active,
                '{}',
                u.created_at,
                NOW()
            FROM users u
            LEFT JOIN tenants t ON t.id = u.id
            WHERE t.id IS NULL
        """)
    )

    # Log how many were created
    result = conn.execute(
        sa.text("SELECT COUNT(*) FROM tenants t INNER JOIN users u ON t.id = u.id")
    )
    count = result.scalar()
    print(f"Ensured tenant records exist for {count} users")


def downgrade():
    """
    Do not delete tenant records on downgrade as they may have associated data.
    This migration is safe to keep.
    """
    pass

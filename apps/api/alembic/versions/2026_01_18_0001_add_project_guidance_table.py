"""Add project_guidance table for Slice 2C: Project Genesis

Revision ID: slice_2c_project_guidance_001
Revises: slice_1d_b_published_at_001
Create Date: 2026-01-18

This migration adds the project_guidance table for storing AI-generated,
project-specific guidance for each workspace section.

Reference: blueprint.md §7 - Section Guidance

The ProjectGuidance model stores:
- what_to_input: Description of required/recommended data per section
- recommended_sources: Suggested data sources for the project
- checklist: Actionable items to complete for each section
- suggested_actions: Available AI-assisted actions
- provenance: Audit trail linking to PIL job and LLM call
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'slice_2c_project_guidance_001'
down_revision: Union[str, None] = 'slice_1d_b_published_at_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists (for idempotency)."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = :table
            )
            """
        ),
        {"table": table_name},
    )
    return result.scalar()


def upgrade() -> None:
    # Skip if table already exists (idempotent)
    if table_exists('project_guidance'):
        return

    # Create project_guidance table
    op.create_table(
        'project_guidance',
        # Identity
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('blueprint_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Versioning for audit
        sa.Column('blueprint_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('guidance_version', sa.Integer(), nullable=False, server_default='1'),

        # Section identification
        sa.Column('section', sa.String(50), nullable=False),

        # Status
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),

        # Guidance content (AI-generated)
        sa.Column('section_title', sa.String(255), nullable=False, server_default=''),
        sa.Column('section_description', sa.Text(), nullable=True),
        sa.Column('what_to_input', postgresql.JSONB(), nullable=True),
        sa.Column('recommended_sources', postgresql.JSONB(), nullable=True),
        sa.Column('checklist', postgresql.JSONB(), nullable=True),
        sa.Column('suggested_actions', postgresql.JSONB(), nullable=True),
        sa.Column('tips', postgresql.JSONB(), nullable=True),

        # Provenance (audit trail)
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('artifact_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('llm_call_id', sa.String(100), nullable=True),

        # Active flag
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),

        # Foreign keys
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['project_specs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['blueprint_id'], ['blueprints.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['job_id'], ['pil_jobs.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['artifact_id'], ['pil_artifacts.id'], ondelete='SET NULL'),

        # Unique constraint for version tracking
        sa.UniqueConstraint('project_id', 'blueprint_version', 'section',
                           name='uq_project_guidance_version_section'),
    )

    # Create indexes for common queries
    op.create_index('ix_project_guidance_tenant_id', 'project_guidance', ['tenant_id'])
    op.create_index('ix_project_guidance_project_id', 'project_guidance', ['project_id'])
    op.create_index('ix_project_guidance_blueprint_id', 'project_guidance', ['blueprint_id'])
    op.create_index('ix_project_guidance_section', 'project_guidance', ['section'])

    # Composite index for common query pattern
    op.create_index(
        'ix_project_guidance_project_section_active',
        'project_guidance',
        ['project_id', 'section', 'is_active']
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_project_guidance_project_section_active', table_name='project_guidance')
    op.drop_index('ix_project_guidance_section', table_name='project_guidance')
    op.drop_index('ix_project_guidance_blueprint_id', table_name='project_guidance')
    op.drop_index('ix_project_guidance_project_id', table_name='project_guidance')
    op.drop_index('ix_project_guidance_tenant_id', table_name='project_guidance')

    # Drop table
    op.drop_table('project_guidance')

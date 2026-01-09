"""Add comprehensive persona tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-01-02

Adds tables for:
- persona_templates: Market/topic-specific persona configurations
- persona_records: Individual personas with 100+ traits
- persona_uploads: CSV/Excel upload tracking
- ai_research_jobs: AI research job tracking
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create persona_templates table
    op.create_table(
        'persona_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('region', sa.String(50), nullable=False),
        sa.Column('country', sa.String(100), nullable=True),
        sa.Column('sub_region', sa.String(100), nullable=True),
        sa.Column('industry', sa.String(100), nullable=True),
        sa.Column('topic', sa.String(255), nullable=True),
        sa.Column('keywords', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('data_sources', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('demographic_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('psychographic_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('behavioral_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('professional_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('cultural_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('distributions', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('data_completeness', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('confidence_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('validation_status', sa.String(50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_persona_templates_user_id', 'persona_templates', ['user_id'])
    op.create_index('ix_persona_templates_region', 'persona_templates', ['region'])
    op.create_index('ix_persona_templates_source_type', 'persona_templates', ['source_type'])

    # Create persona_records table
    op.create_table(
        'persona_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('demographics', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('professional', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('psychographics', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('behavioral', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('interests', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('topic_knowledge', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('cultural_context', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('data_sources', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=False, server_default='0.8'),
        sa.Column('generation_context', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('full_prompt', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['template_id'], ['persona_templates.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_persona_records_template_id', 'persona_records', ['template_id'])
    op.create_index('ix_persona_records_source_type', 'persona_records', ['source_type'])

    # Create persona_uploads table
    op.create_table(
        'persona_uploads',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('file_type', sa.String(20), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('records_total', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('records_processed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('records_failed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('column_mapping', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('errors', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['template_id'], ['persona_templates.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_persona_uploads_user_id', 'persona_uploads', ['user_id'])
    op.create_index('ix_persona_uploads_status', 'persona_uploads', ['status'])

    # Create ai_research_jobs table
    op.create_table(
        'ai_research_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('topic', sa.String(255), nullable=False),
        sa.Column('region', sa.String(50), nullable=False),
        sa.Column('country', sa.String(100), nullable=True),
        sa.Column('industry', sa.String(100), nullable=True),
        sa.Column('keywords', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('research_depth', sa.String(50), nullable=False, server_default='standard'),
        sa.Column('data_sources_to_use', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('target_persona_count', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('progress', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sources_found', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('demographics_discovered', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('insights', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('personas_generated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['template_id'], ['persona_templates.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ai_research_jobs_user_id', 'ai_research_jobs', ['user_id'])
    op.create_index('ix_ai_research_jobs_status', 'ai_research_jobs', ['status'])
    op.create_index('ix_ai_research_jobs_topic', 'ai_research_jobs', ['topic'])


def downgrade() -> None:
    op.drop_table('ai_research_jobs')
    op.drop_table('persona_uploads')
    op.drop_table('persona_records')
    op.drop_table('persona_templates')

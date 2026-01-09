"""Add product tables for 3-model system

Revision ID: 0004
Revises: 0003
Create Date: 2026-01-02

Adds tables for:
- products: Core product configuration (Predict, Insight, Simulate)
- product_runs: Individual execution runs
- agent_interactions: Agent interaction records
- product_results: Aggregated results
- benchmarks: Real-world validation data
- validation_records: Prediction accuracy tracking
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create products table
    op.create_table(
        'products',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('product_type', sa.String(50), nullable=False),
        sa.Column('sub_type', sa.String(100), nullable=True),
        sa.Column('target_market', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('persona_template_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('persona_count', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('persona_source', sa.String(50), nullable=False, server_default='ai_generated'),
        sa.Column('configuration', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('stimulus_materials', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('methodology', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('validation_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('confidence_target', sa.Float(), nullable=False, server_default='0.9'),
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['persona_template_id'], ['persona_templates.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_products_project_id', 'products', ['project_id'])
    op.create_index('ix_products_user_id', 'products', ['user_id'])
    op.create_index('ix_products_product_type', 'products', ['product_type'])
    op.create_index('ix_products_status', 'products', ['status'])

    # Create product_runs table
    op.create_table(
        'product_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('run_number', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('config_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('persona_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('progress', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('agents_total', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('agents_completed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('agents_failed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tokens_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('estimated_cost', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_product_runs_product_id', 'product_runs', ['product_id'])
    op.create_index('ix_product_runs_status', 'product_runs', ['status'])

    # Create agent_interactions table
    op.create_table(
        'agent_interactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('persona_record_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('agent_index', sa.Integer(), nullable=False),
        sa.Column('persona_summary', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('interaction_type', sa.String(50), nullable=False),
        sa.Column('conversation', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('responses', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('sentiment_overall', sa.Float(), nullable=True),
        sa.Column('key_themes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('behavioral_signals', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('coherence_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('authenticity_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('tokens_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['run_id'], ['product_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['persona_record_id'], ['persona_records.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_agent_interactions_run_id', 'agent_interactions', ['run_id'])
    op.create_index('ix_agent_interactions_status', 'agent_interactions', ['status'])

    # Create product_results table
    op.create_table(
        'product_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('result_type', sa.String(50), nullable=False),
        sa.Column('predictions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('insights', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('simulation_outcomes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('statistical_analysis', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('segment_analysis', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('validation_results', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('quality_metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('executive_summary', sa.Text(), nullable=True),
        sa.Column('key_takeaways', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('recommendations', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('visualizations', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['run_id'], ['product_runs.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_product_results_product_id', 'product_results', ['product_id'])
    op.create_index('ix_product_results_result_type', 'product_results', ['result_type'])

    # Create benchmarks table
    op.create_table(
        'benchmarks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('event_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('region', sa.String(50), nullable=False),
        sa.Column('country', sa.String(100), nullable=True),
        sa.Column('actual_outcome', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('source', sa.String(255), nullable=False),
        sa.Column('source_url', sa.String(500), nullable=True),
        sa.Column('verification_status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_benchmarks_category', 'benchmarks', ['category'])
    op.create_index('ix_benchmarks_region', 'benchmarks', ['region'])

    # Create validation_records table
    op.create_table(
        'validation_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('benchmark_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('predicted_outcome', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('actual_outcome', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('accuracy_score', sa.Float(), nullable=False),
        sa.Column('deviation', sa.Float(), nullable=False),
        sa.Column('within_confidence_interval', sa.Boolean(), nullable=False),
        sa.Column('analysis', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('validated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['benchmark_id'], ['benchmarks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_validation_records_product_id', 'validation_records', ['product_id'])
    op.create_index('ix_validation_records_benchmark_id', 'validation_records', ['benchmark_id'])


def downgrade() -> None:
    op.drop_table('validation_records')
    op.drop_table('benchmarks')
    op.drop_table('product_results')
    op.drop_table('agent_interactions')
    op.drop_table('product_runs')
    op.drop_table('products')

"""Add data source tables for real-world data integration

Revision ID: 0002
Revises: 0001
Create Date: 2024-01-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create data_sources table
    op.create_table(
        'data_sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('source_type', sa.String(50), nullable=False),  # census, research, web_scrape, survey, proprietary
        sa.Column('source_url', sa.String(500), nullable=True),
        sa.Column('api_endpoint', sa.String(500), nullable=True),
        sa.Column('coverage_region', sa.String(100), nullable=True),
        sa.Column('coverage_year', sa.Integer(), nullable=True),
        sa.Column('sample_size', sa.Integer(), nullable=True),
        sa.Column('accuracy_score', sa.Float(), nullable=True),
        sa.Column('validation_status', sa.String(50), nullable=True),
        sa.Column('last_validated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('credentials_encrypted', sa.Text(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_data_sources_source_type', 'data_sources', ['source_type'])
    op.create_index('ix_data_sources_status', 'data_sources', ['status'])

    # Create census_data table
    op.create_table(
        'census_data',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('data_source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('country', sa.String(10), nullable=False, server_default='US'),
        sa.Column('state', sa.String(50), nullable=True),
        sa.Column('county', sa.String(100), nullable=True),
        sa.Column('metro_area', sa.String(100), nullable=True),
        sa.Column('data_category', sa.String(50), nullable=False),  # age, gender, income, education, occupation
        sa.Column('distribution', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('survey_year', sa.Integer(), nullable=False),
        sa.Column('survey_name', sa.String(100), nullable=False),
        sa.Column('margin_of_error', sa.Float(), nullable=True),
        sa.Column('raw_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['data_source_id'], ['data_sources.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_census_data_data_source_id', 'census_data', ['data_source_id'])
    op.create_index('ix_census_data_category', 'census_data', ['data_category'])
    op.create_index('ix_census_data_country_state', 'census_data', ['country', 'state'])

    # Create regional_profiles table
    op.create_table(
        'regional_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('data_source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('region_code', sa.String(50), nullable=False),
        sa.Column('region_name', sa.String(255), nullable=False),
        sa.Column('region_type', sa.String(50), nullable=False),  # country, state, county, metro, custom
        sa.Column('parent_region_code', sa.String(50), nullable=True),
        sa.Column('demographics', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('psychographics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('behavioral_patterns', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('data_completeness', sa.Float(), nullable=False, server_default='0'),
        sa.Column('confidence_score', sa.Float(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['data_source_id'], ['data_sources.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('region_code')
    )
    op.create_index('ix_regional_profiles_data_source_id', 'regional_profiles', ['data_source_id'])
    op.create_index('ix_regional_profiles_region_type', 'regional_profiles', ['region_type'])

    # Create validation_results table
    op.create_table(
        'validation_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('simulation_run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('validation_type', sa.String(50), nullable=False),  # election, survey, product_launch, market_research
        sa.Column('predicted_result', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('actual_result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('correlation_score', sa.Float(), nullable=True),
        sa.Column('margin_of_error', sa.Float(), nullable=True),
        sa.Column('confidence_interval', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('analysis', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('validation_source', sa.String(255), nullable=True),
        sa.Column('validation_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['simulation_run_id'], ['simulation_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_validation_results_simulation_run_id', 'validation_results', ['simulation_run_id'])
    op.create_index('ix_validation_results_validation_type', 'validation_results', ['validation_type'])


def downgrade() -> None:
    op.drop_table('validation_results')
    op.drop_table('regional_profiles')
    op.drop_table('census_data')
    op.drop_table('data_sources')

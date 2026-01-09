"""Add LLM Router tables for centralized model management

Revision ID: llm_router_001
Revises: spec_compliant_001
Create Date: 2026-01-09 00:00:00.000000

This migration creates the LLM Router system tables:
- llm_profiles: Admin-managed model configurations per feature
- llm_calls: Call logging for cost tracking and debugging
- llm_cache: Deterministic cache for LLM response replay

Reference: GAPS.md GAP-P0-001 - No Centralized LLM Router
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'llm_router_001'
down_revision: Union[str, None] = 'spec_compliant_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # LLM Profiles Table - Admin-managed model configurations
    # =========================================================================
    op.create_table(
        'llm_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),  # NULL = global default

        # Profile identification
        sa.Column('profile_key', sa.String(100), nullable=False),  # e.g., EVENT_COMPILER_INTENT
        sa.Column('label', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),

        # Primary model configuration
        sa.Column('model', sa.String(100), nullable=False),  # e.g., openai/gpt-4o-mini
        sa.Column('temperature', sa.Float(), nullable=False, server_default='0.7'),
        sa.Column('max_tokens', sa.Integer(), nullable=False, server_default='1000'),
        sa.Column('top_p', sa.Float(), nullable=True),
        sa.Column('frequency_penalty', sa.Float(), nullable=True),
        sa.Column('presence_penalty', sa.Float(), nullable=True),

        # Cost tracking
        sa.Column('cost_per_1k_input_tokens', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('cost_per_1k_output_tokens', sa.Float(), nullable=False, server_default='0.0'),

        # Fallback chain (ordered list of model IDs to try on failure)
        sa.Column('fallback_models', postgresql.ARRAY(sa.String(100)), nullable=True),

        # Rate limiting per profile
        sa.Column('rate_limit_rpm', sa.Integer(), nullable=True),  # requests per minute
        sa.Column('rate_limit_tpm', sa.Integer(), nullable=True),  # tokens per minute

        # Caching configuration
        sa.Column('cache_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('cache_ttl_seconds', sa.Integer(), nullable=True),  # NULL = indefinite

        # System prompt template (can include {tenant_id}, {project_id} placeholders)
        sa.Column('system_prompt_template', sa.Text(), nullable=True),

        # Priority (lower = higher priority for selection)
        sa.Column('priority', sa.Integer(), nullable=False, server_default='100'),

        # Status
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_llm_profiles_tenant_id', 'llm_profiles', ['tenant_id'])
    op.create_index('ix_llm_profiles_profile_key', 'llm_profiles', ['profile_key'])
    op.create_index('ix_llm_profiles_is_active', 'llm_profiles', ['is_active'])
    # Unique constraint: one active profile per key per tenant (or global if tenant_id is NULL)
    op.create_index(
        'ix_llm_profiles_unique_active',
        'llm_profiles',
        ['profile_key', 'tenant_id'],
        unique=True,
        postgresql_where=sa.text('is_active = true')
    )

    # =========================================================================
    # LLM Calls Table - Call logging for cost tracking and debugging
    # =========================================================================
    op.create_table(
        'llm_calls',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Call identification
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('profile_key', sa.String(100), nullable=False),  # Denormalized for queries

        # Context
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('node_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Request details
        sa.Column('model_requested', sa.String(100), nullable=False),
        sa.Column('model_used', sa.String(100), nullable=False),  # May differ if fallback
        sa.Column('messages_hash', sa.String(64), nullable=False),  # SHA-256 of messages
        sa.Column('input_tokens', sa.Integer(), nullable=False),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('max_tokens', sa.Integer(), nullable=True),

        # Response details
        sa.Column('output_tokens', sa.Integer(), nullable=False),
        sa.Column('total_tokens', sa.Integer(), nullable=False),
        sa.Column('response_time_ms', sa.Integer(), nullable=False),

        # Cost
        sa.Column('cost_usd', sa.Float(), nullable=False),

        # Status
        sa.Column('status', sa.String(20), nullable=False),  # success, error, cached, fallback
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('fallback_attempts', sa.Integer(), nullable=False, server_default='0'),

        # Cache
        sa.Column('cache_hit', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('cache_key', sa.String(64), nullable=True),

        # User context
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['profile_id'], ['llm_profiles.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['project_id'], ['project_specs.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_llm_calls_tenant_id', 'llm_calls', ['tenant_id'])
    op.create_index('ix_llm_calls_profile_key', 'llm_calls', ['profile_key'])
    op.create_index('ix_llm_calls_project_id', 'llm_calls', ['project_id'])
    op.create_index('ix_llm_calls_created_at', 'llm_calls', ['created_at'])
    op.create_index('ix_llm_calls_status', 'llm_calls', ['status'])
    # Composite index for cost aggregation queries
    op.create_index(
        'ix_llm_calls_cost_agg',
        'llm_calls',
        ['tenant_id', 'project_id', 'created_at']
    )

    # =========================================================================
    # LLM Cache Table - Deterministic cache for LLM response replay
    # =========================================================================
    op.create_table(
        'llm_cache',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),

        # Cache key (SHA-256 hash of: profile_key + model + messages + temperature + seed)
        sa.Column('cache_key', sa.String(64), nullable=False),

        # Request fingerprint
        sa.Column('profile_key', sa.String(100), nullable=False),
        sa.Column('model', sa.String(100), nullable=False),
        sa.Column('messages_hash', sa.String(64), nullable=False),
        sa.Column('temperature', sa.Float(), nullable=False),
        sa.Column('seed', sa.BigInteger(), nullable=True),  # For deterministic replay

        # Response content
        sa.Column('response_content', sa.Text(), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=False),
        sa.Column('output_tokens', sa.Integer(), nullable=False),

        # Usage stats
        sa.Column('hit_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_hit_at', sa.DateTime(timezone=True), nullable=True),

        # TTL management
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),  # NULL = never

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),

        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_llm_cache_cache_key', 'llm_cache', ['cache_key'], unique=True)
    op.create_index('ix_llm_cache_profile_key', 'llm_cache', ['profile_key'])
    op.create_index('ix_llm_cache_expires_at', 'llm_cache', ['expires_at'])

    # =========================================================================
    # Insert default LLM profiles (global defaults)
    # =========================================================================
    op.execute("""
        INSERT INTO llm_profiles (
            id, profile_key, label, description, model,
            temperature, max_tokens, cost_per_1k_input_tokens, cost_per_1k_output_tokens,
            fallback_models, cache_enabled, is_active, is_default, priority
        ) VALUES
        -- Event Compiler profiles
        (gen_random_uuid(), 'EVENT_COMPILER_INTENT', 'Event Compiler - Intent Analysis',
         'Classifies user prompts as event/variable/query/comparison/explanation',
         'openai/gpt-4o-mini', 0.3, 500, 0.00015, 0.0006,
         ARRAY['anthropic/claude-3-haiku-20240307'], true, true, true, 10),

        (gen_random_uuid(), 'EVENT_COMPILER_DECOMPOSE', 'Event Compiler - Decomposition',
         'Breaks prompts into granular sub-effects',
         'openai/gpt-4o-mini', 0.5, 1000, 0.00015, 0.0006,
         ARRAY['anthropic/claude-3-haiku-20240307'], true, true, true, 10),

        (gen_random_uuid(), 'EVENT_COMPILER_VARIABLE_MAP', 'Event Compiler - Variable Mapping',
         'Maps sub-effects to concrete variable deltas',
         'openai/gpt-4o-mini', 0.3, 1500, 0.00015, 0.0006,
         ARRAY['anthropic/claude-3-haiku-20240307'], true, true, true, 10),

        -- Scenario generation
        (gen_random_uuid(), 'SCENARIO_GENERATOR', 'Scenario Generator',
         'Generates candidate scenarios from variable deltas',
         'anthropic/claude-3-haiku-20240307', 0.7, 2000, 0.00025, 0.00125,
         ARRAY['openai/gpt-4o-mini'], true, true, true, 20),

        -- Explanation generation
        (gen_random_uuid(), 'EXPLANATION_GENERATOR', 'Explanation Generator',
         'Creates causal chain summaries for simulation outcomes',
         'anthropic/claude-3-haiku-20240307', 0.5, 1500, 0.00025, 0.00125,
         ARRAY['openai/gpt-4o-mini'], true, true, true, 20),

        -- Persona enrichment
        (gen_random_uuid(), 'PERSONA_ENRICHMENT', 'Persona Enrichment',
         'Enriches persona attributes from demographics',
         'openai/gpt-4o-mini', 0.7, 1000, 0.00015, 0.0006,
         ARRAY['anthropic/claude-3-haiku-20240307'], true, true, true, 30),

        -- Deep search / AI research
        (gen_random_uuid(), 'DEEP_SEARCH', 'Deep Search / AI Research',
         'AI-powered persona research and validation',
         'anthropic/claude-3-haiku-20240307', 0.5, 2000, 0.00025, 0.00125,
         ARRAY['openai/gpt-4o-mini'], true, true, true, 30),

        -- Focus group dialogue
        (gen_random_uuid(), 'FOCUS_GROUP_DIALOGUE', 'Focus Group Dialogue',
         'Simulates focus group conversations',
         'anthropic/claude-3-5-sonnet-20241022', 0.8, 2000, 0.003, 0.015,
         ARRAY['anthropic/claude-3-haiku-20240307', 'openai/gpt-4o-mini'], false, true, true, 40);
    """)


def downgrade() -> None:
    op.drop_table('llm_cache')
    op.drop_table('llm_calls')
    op.drop_table('llm_profiles')

"""Add marketplace tables for scenario template sharing

Revision ID: 0007
Revises: 0006
Create Date: 2026-01-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0007'
down_revision: Union[str, None] = '0006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create marketplace_categories table
    op.create_table(
        'marketplace_categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('icon', sa.String(50), nullable=True),
        sa.Column('color', sa.String(20), nullable=True),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('template_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['parent_id'], ['marketplace_categories.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )

    # Create indexes for marketplace_categories
    op.create_index('ix_marketplace_categories_slug', 'marketplace_categories', ['slug'])
    op.create_index('ix_marketplace_categories_parent_order', 'marketplace_categories', ['parent_id', 'display_order'])

    # Create marketplace_templates table
    op.create_table(
        'marketplace_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        # Basic info
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('slug', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('short_description', sa.String(500), nullable=True),
        # Categorization
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('tags', postgresql.JSONB(), nullable=False, server_default='[]'),
        # Author/ownership
        sa.Column('author_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True),
        # Template content (from scenario)
        sa.Column('scenario_type', sa.String(50), nullable=False),
        sa.Column('context', sa.Text(), nullable=False),
        sa.Column('questions', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('variables', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('demographics', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('persona_template', postgresql.JSONB(), nullable=True),
        sa.Column('model_config', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('recommended_population_size', sa.Integer(), nullable=False, server_default='100'),
        # Stimulus materials and methodology
        sa.Column('stimulus_materials', postgresql.JSONB(), nullable=True),
        sa.Column('methodology', postgresql.JSONB(), nullable=True),
        # Preview/sample data
        sa.Column('preview_image_url', sa.String(500), nullable=True),
        sa.Column('sample_results', postgresql.JSONB(), nullable=True),
        # Status and visibility
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('is_featured', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_premium', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('price_usd', sa.Float(), nullable=True),
        # Metrics (denormalized for performance)
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rating_average', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('rating_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('like_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('view_count', sa.Integer(), nullable=False, server_default='0'),
        # Version tracking
        sa.Column('version', sa.String(20), nullable=False, server_default='1.0.0'),
        sa.Column('source_scenario_id', postgresql.UUID(as_uuid=True), nullable=True),
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        # Foreign keys and constraints
        sa.ForeignKeyConstraint(['category_id'], ['marketplace_categories.id']),
        sa.ForeignKeyConstraint(['author_id'], ['users.id']),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['source_scenario_id'], ['scenarios.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
        sa.CheckConstraint('rating_average >= 0 AND rating_average <= 5', name='check_rating_range'),
        sa.CheckConstraint('price_usd IS NULL OR price_usd >= 0', name='check_price_positive'),
    )

    # Create indexes for marketplace_templates
    op.create_index('ix_marketplace_templates_slug', 'marketplace_templates', ['slug'])
    op.create_index('ix_marketplace_templates_category', 'marketplace_templates', ['category_id'])
    op.create_index('ix_marketplace_templates_author', 'marketplace_templates', ['author_id'])
    op.create_index('ix_marketplace_templates_status', 'marketplace_templates', ['status'])
    op.create_index('ix_marketplace_templates_featured', 'marketplace_templates', ['is_featured', 'status'])
    op.create_index('ix_marketplace_templates_rating', 'marketplace_templates', ['rating_average', 'rating_count'])
    op.create_index('ix_marketplace_templates_usage', 'marketplace_templates', ['usage_count'])
    op.create_index('ix_marketplace_templates_search', 'marketplace_templates', ['name', 'status'])

    # Create template_reviews table
    op.create_table(
        'template_reviews',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        # Review content
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(200), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        # Review metadata
        sa.Column('is_verified_purchase', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_helpful_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_reported', sa.Boolean(), nullable=False, server_default='false'),
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        # Foreign keys and constraints
        sa.ForeignKeyConstraint(['template_id'], ['marketplace_templates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('template_id', 'user_id', name='uq_template_review_user'),
        sa.CheckConstraint('rating >= 1 AND rating <= 5', name='check_review_rating_range'),
    )

    # Create indexes for template_reviews
    op.create_index('ix_template_reviews_template', 'template_reviews', ['template_id'])
    op.create_index('ix_template_reviews_rating', 'template_reviews', ['template_id', 'rating'])

    # Create template_likes table
    op.create_table(
        'template_likes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        # Foreign keys and constraints
        sa.ForeignKeyConstraint(['template_id'], ['marketplace_templates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('template_id', 'user_id', name='uq_template_like_user'),
    )

    # Create indexes for template_likes
    op.create_index('ix_template_likes_template', 'template_likes', ['template_id'])
    op.create_index('ix_template_likes_user', 'template_likes', ['user_id'])

    # Create template_usages table
    op.create_table(
        'template_usages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        # What was created from the template
        sa.Column('created_scenario_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_product_id', postgresql.UUID(as_uuid=True), nullable=True),
        # Usage metadata
        sa.Column('customizations', postgresql.JSONB(), nullable=False, server_default='{}'),
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        # Foreign keys
        sa.ForeignKeyConstraint(['template_id'], ['marketplace_templates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['created_scenario_id'], ['scenarios.id']),
        sa.ForeignKeyConstraint(['created_product_id'], ['products.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create indexes for template_usages
    op.create_index('ix_template_usages_template', 'template_usages', ['template_id'])
    op.create_index('ix_template_usages_user', 'template_usages', ['user_id'])
    op.create_index('ix_template_usages_created_at', 'template_usages', ['created_at'])


def downgrade() -> None:
    # Drop template_usages table and indexes
    op.drop_index('ix_template_usages_created_at', table_name='template_usages')
    op.drop_index('ix_template_usages_user', table_name='template_usages')
    op.drop_index('ix_template_usages_template', table_name='template_usages')
    op.drop_table('template_usages')

    # Drop template_likes table and indexes
    op.drop_index('ix_template_likes_user', table_name='template_likes')
    op.drop_index('ix_template_likes_template', table_name='template_likes')
    op.drop_table('template_likes')

    # Drop template_reviews table and indexes
    op.drop_index('ix_template_reviews_rating', table_name='template_reviews')
    op.drop_index('ix_template_reviews_template', table_name='template_reviews')
    op.drop_table('template_reviews')

    # Drop marketplace_templates table and indexes
    op.drop_index('ix_marketplace_templates_search', table_name='marketplace_templates')
    op.drop_index('ix_marketplace_templates_usage', table_name='marketplace_templates')
    op.drop_index('ix_marketplace_templates_rating', table_name='marketplace_templates')
    op.drop_index('ix_marketplace_templates_featured', table_name='marketplace_templates')
    op.drop_index('ix_marketplace_templates_status', table_name='marketplace_templates')
    op.drop_index('ix_marketplace_templates_author', table_name='marketplace_templates')
    op.drop_index('ix_marketplace_templates_category', table_name='marketplace_templates')
    op.drop_index('ix_marketplace_templates_slug', table_name='marketplace_templates')
    op.drop_table('marketplace_templates')

    # Drop marketplace_categories table and indexes
    op.drop_index('ix_marketplace_categories_parent_order', table_name='marketplace_categories')
    op.drop_index('ix_marketplace_categories_slug', table_name='marketplace_categories')
    op.drop_table('marketplace_categories')

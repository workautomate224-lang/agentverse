"""Add organization tables for team collaboration

Revision ID: 0006
Revises: 0005
Create Date: 2026-01-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0006'
down_revision: Union[str, None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create organizations table
    op.create_table(
        'organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('logo_url', sa.String(500), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tier', sa.String(50), nullable=False, server_default='free'),
        sa.Column('max_members', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('max_projects', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('max_simulations_per_month', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('current_month_simulations', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('settings', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )

    # Create indexes for organizations
    op.create_index('ix_organizations_slug', 'organizations', ['slug'])
    op.create_index('ix_organizations_owner_id', 'organizations', ['owner_id'])
    op.create_index('ix_organizations_tier', 'organizations', ['tier'])

    # Create organization_memberships table
    op.create_table(
        'organization_memberships',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, server_default='member'),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'user_id', name='unique_org_user')
    )

    # Create indexes for organization_memberships
    op.create_index('ix_organization_memberships_org_id', 'organization_memberships', ['organization_id'])
    op.create_index('ix_organization_memberships_user_id', 'organization_memberships', ['user_id'])
    op.create_index('ix_organization_memberships_role', 'organization_memberships', ['role'])

    # Create organization_invitations table
    op.create_table(
        'organization_invitations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, server_default='member'),
        sa.Column('invited_by_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('token', sa.String(100), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invited_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token')
    )

    # Create indexes for organization_invitations
    op.create_index('ix_organization_invitations_org_id', 'organization_invitations', ['organization_id'])
    op.create_index('ix_organization_invitations_email', 'organization_invitations', ['email'])
    op.create_index('ix_organization_invitations_token', 'organization_invitations', ['token'])
    op.create_index('ix_organization_invitations_status', 'organization_invitations', ['status'])

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(100), nullable=True),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('details', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for audit_logs
    op.create_index('ix_audit_logs_org_id', 'audit_logs', ['organization_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])


def downgrade() -> None:
    # Drop audit_logs table and indexes
    op.drop_index('ix_audit_logs_user_id', table_name='audit_logs')
    op.drop_index('ix_audit_logs_created_at', table_name='audit_logs')
    op.drop_index('ix_audit_logs_action', table_name='audit_logs')
    op.drop_index('ix_audit_logs_org_id', table_name='audit_logs')
    op.drop_table('audit_logs')

    # Drop organization_invitations table and indexes
    op.drop_index('ix_organization_invitations_status', table_name='organization_invitations')
    op.drop_index('ix_organization_invitations_token', table_name='organization_invitations')
    op.drop_index('ix_organization_invitations_email', table_name='organization_invitations')
    op.drop_index('ix_organization_invitations_org_id', table_name='organization_invitations')
    op.drop_table('organization_invitations')

    # Drop organization_memberships table and indexes
    op.drop_index('ix_organization_memberships_role', table_name='organization_memberships')
    op.drop_index('ix_organization_memberships_user_id', table_name='organization_memberships')
    op.drop_index('ix_organization_memberships_org_id', table_name='organization_memberships')
    op.drop_table('organization_memberships')

    # Drop organizations table and indexes
    op.drop_index('ix_organizations_tier', table_name='organizations')
    op.drop_index('ix_organizations_owner_id', table_name='organizations')
    op.drop_index('ix_organizations_slug', table_name='organizations')
    op.drop_table('organizations')

"""add llm_config to marketplace_templates

Revision ID: dabd56adb2ca
Revises: 0008
Create Date: 2026-01-03 08:29:28.567191

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'dabd56adb2ca'
down_revision: Union[str, None] = '0008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add llm_config column to marketplace_templates
    op.add_column('marketplace_templates', sa.Column('llm_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    # Remove llm_config column from marketplace_templates
    op.drop_column('marketplace_templates', 'llm_config')

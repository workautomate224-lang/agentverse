"""Add PIL LLM profiles with gpt-5.2 as default model

Revision ID: pil_llm_profiles_001
Revises: 2026_01_16_0006_blueprint_tasks_available_actions_jsonb
Create Date: 2026-01-17 00:00:00.000000

This migration creates default LLM profiles for the PIL (Project Intelligence Layer) features:
- PIL_GOAL_ANALYSIS: Analyzes project goals and extracts domain/intent
- PIL_CLARIFYING_QUESTIONS: Generates clarifying questions for ambiguous goals
- PIL_RISK_ASSESSMENT: Assesses risks and generates warnings
- PIL_BLUEPRINT_GENERATION: Generates full blueprint drafts

All profiles use openai/gpt-5.2 as the primary model with gpt-4o as fallback.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'pil_llm_profiles_001'
down_revision: Union[str, None] = 'blueprint_tasks_jsonb_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Insert PIL LLM profiles with gpt-5.2 as the default model."""
    # Insert each profile only if it doesn't already exist (idempotent)
    pil_profiles = [
        {
            "key": "PIL_GOAL_ANALYSIS",
            "label": "PIL - Goal Analysis",
            "description": "Analyzes project goals to extract domain, intent, and summary",
            "model": "openai/gpt-5.2",
            "temperature": 0.3,
            "max_tokens": 1500,
        },
        {
            "key": "PIL_CLARIFYING_QUESTIONS",
            "label": "PIL - Clarifying Questions",
            "description": "Generates intelligent clarifying questions for ambiguous project goals",
            "model": "openai/gpt-5.2",
            "temperature": 0.5,
            "max_tokens": 2000,
        },
        {
            "key": "PIL_RISK_ASSESSMENT",
            "label": "PIL - Risk Assessment",
            "description": "Assesses potential risks, gaps, and generates warnings for projects",
            "model": "openai/gpt-5.2",
            "temperature": 0.3,
            "max_tokens": 1500,
        },
        {
            "key": "PIL_BLUEPRINT_GENERATION",
            "label": "PIL - Blueprint Generation",
            "description": "Generates complete project blueprints including slots, tasks, and strategy",
            "model": "openai/gpt-5.2",
            "temperature": 0.4,
            "max_tokens": 4000,
        },
    ]

    for profile in pil_profiles:
        op.execute(f"""
            INSERT INTO llm_profiles (
                id, profile_key, label, description, model,
                temperature, max_tokens, cost_per_1k_input_tokens, cost_per_1k_output_tokens,
                fallback_models, cache_enabled, is_active, is_default, priority
            )
            SELECT
                gen_random_uuid(),
                '{profile["key"]}',
                '{profile["label"]}',
                '{profile["description"]}',
                '{profile["model"]}',
                {profile["temperature"]},
                {profile["max_tokens"]},
                0.01,
                0.03,
                ARRAY['openai/gpt-4o', 'openai/gpt-4o-mini'],
                true,
                true,
                true,
                5
            WHERE NOT EXISTS (
                SELECT 1 FROM llm_profiles
                WHERE profile_key = '{profile["key"]}'
                AND tenant_id IS NULL
                AND is_active = true
            );
        """)


def downgrade() -> None:
    """Remove PIL LLM profiles."""
    op.execute("""
        DELETE FROM llm_profiles
        WHERE profile_key IN (
            'PIL_GOAL_ANALYSIS',
            'PIL_CLARIFYING_QUESTIONS',
            'PIL_RISK_ASSESSMENT',
            'PIL_BLUEPRINT_GENERATION'
        );
    """)

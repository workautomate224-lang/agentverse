"""STEP 6: Planning Models for Target Mode

Revision ID: step6_planning_001
Revises: step5_event_audit_001
Create Date: 2026-01-10

This migration adds infrastructure required for STEP 6 verification:
1. Create planning_specs table for PlanningSpec model
2. Create plan_candidates table for candidate plans
3. Create plan_evaluations table for simulation evaluations
4. Create plan_traces table for audit artifacts

STEP 6 Goal: Implement "Target Mode" as a real planning system that searches
action paths and evaluates them via simulation, NOT as an LLM-only advice feature.

Key Requirements:
- PlanningSpec must be stored in DB
- Planner must use Search + Simulation Evaluation
- PlanTrace artifact must record candidates, pruning, runs, scoring
- Explicit, non-black-box scoring function
- Ensemble evaluation (min 2 runs per plan)
- Reproducibility via stored seed
- Output with Top-K plans and evidence links to Runs
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'step6_planning_001'
down_revision = 'step5_event_audit_001'
branch_labels = None
depends_on = None


def upgrade():
    # ==========================================================================
    # 1. Create planning_specs table (STEP 6 Requirement 1)
    # ==========================================================================
    op.create_table(
        'planning_specs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('project_specs.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('parent_node_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('nodes.id', ondelete='SET NULL'),
                  nullable=True, index=True,
                  comment='STEP 6: parent_node_id - starting point'),
        sa.Column('target_snapshot_id', postgresql.UUID(as_uuid=True),
                  nullable=True,
                  comment='STEP 6: target_snapshot_id - goal state reference'),
        sa.Column('target_persona_id', sa.String(100), nullable=True, index=True,
                  comment='STEP 6: Target persona ID'),

        # Goal definition
        sa.Column('goal_definition', postgresql.JSONB, nullable=False, default=dict,
                  comment='STEP 6: Goal definition {goal_type, target_metrics, success_criteria}'),

        # Constraints
        sa.Column('constraints', postgresql.JSONB, nullable=False, default=dict,
                  comment='STEP 6: Constraints {hard_constraints, soft_constraints}'),

        # Action library version
        sa.Column('action_library_version', sa.String(50), nullable=False, default='1.0.0',
                  comment='STEP 6: action_library_version for reproducibility'),

        # Search configuration
        sa.Column('search_config', postgresql.JSONB, nullable=False, default=dict,
                  comment='STEP 6: search_config {algorithm, max_depth, beam_width, pruning_threshold}'),

        # Evaluation budget
        sa.Column('evaluation_budget', sa.Integer, nullable=False, default=10,
                  comment='STEP 6: evaluation_budget - max simulation runs'),
        sa.Column('min_runs_per_candidate', sa.Integer, nullable=False, default=2,
                  comment='STEP 6: Minimum runs per candidate (ensemble requirement)'),

        # Seed for reproducibility
        sa.Column('seed', sa.Integer, nullable=False,
                  comment='STEP 6: seed for reproducibility'),

        # Status
        sa.Column('status', sa.String(50), nullable=False, default='created', index=True,
                  comment='STEP 6: Planning status'),

        # Initial environment state
        sa.Column('initial_environment_state', postgresql.JSONB, nullable=True,
                  comment='STEP 6: Environment state snapshot at planning start'),

        # Label and description
        sa.Column('label', sa.String(255), nullable=True),
        sa.Column('description', sa.Text, nullable=True),

        # Provenance
        sa.Column('compiler_version', sa.String(50), nullable=False, default='1.0.0'),
        sa.Column('model_used', sa.String(100), nullable=True,
                  comment='LLM model used for NL compilation (if any)'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),

        # Error handling
        sa.Column('error_message', sa.Text, nullable=True),
    )

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_planning_specs_status
        ON planning_specs (tenant_id, status)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_planning_specs_project
        ON planning_specs (project_id, created_at)
    """)

    # ==========================================================================
    # 2. Create plan_candidates table (STEP 6 Requirement 2)
    # ==========================================================================
    op.create_table(
        'plan_candidates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('planning_spec_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('planning_specs.id', ondelete='CASCADE'),
                  nullable=False, index=True),

        # Candidate identification
        sa.Column('candidate_index', sa.Integer, nullable=False,
                  comment='STEP 6: Index of this candidate in search result'),

        # Label and description
        sa.Column('label', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),

        # Action sequence
        sa.Column('action_sequence', postgresql.JSONB, nullable=False, default=list,
                  comment='STEP 6: Sequence of actions'),

        # Predicted outcome
        sa.Column('predicted_outcome', postgresql.JSONB, nullable=False, default=dict,
                  comment='STEP 6: Predicted outcome from search'),

        # Search probability
        sa.Column('search_probability', sa.Float, nullable=False, default=0.0,
                  comment='STEP 6: Probability from search algorithm'),

        # Cluster info
        sa.Column('cluster_id', sa.String(100), nullable=True, index=True),
        sa.Column('is_cluster_representative', sa.Boolean, nullable=False, default=False),

        # Status
        sa.Column('status', sa.String(50), nullable=False, default='pending', index=True),

        # Simulation-derived scores (STEP 6 Requirement 4)
        sa.Column('success_probability', sa.Float, nullable=True,
                  comment='STEP 6: success_probability from simulation'),
        sa.Column('cost_score', sa.Float, nullable=True,
                  comment='STEP 6: cost from simulation runs'),
        sa.Column('risk_score', sa.Float, nullable=True,
                  comment='STEP 6: risk from simulation variance'),
        sa.Column('composite_score', sa.Float, nullable=True,
                  comment='STEP 6: Composite score'),
        sa.Column('score_confidence', sa.Float, nullable=True,
                  comment='STEP 6: Confidence in score'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_plan_candidates_spec
        ON plan_candidates (planning_spec_id, candidate_index)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_plan_candidates_score
        ON plan_candidates (planning_spec_id, composite_score)
    """)

    # ==========================================================================
    # 3. Create plan_evaluations table (STEP 6 Requirement 5)
    # ==========================================================================
    op.create_table(
        'plan_evaluations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('candidate_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('plan_candidates.id', ondelete='CASCADE'),
                  nullable=False, index=True),

        # Run reference (STEP 6 Requirement 7: Evidence links)
        sa.Column('run_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('runs.id', ondelete='SET NULL'),
                  nullable=True, index=True,
                  comment='STEP 6: FK to actual Run artifact for evidence'),
        sa.Column('node_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('nodes.id', ondelete='SET NULL'),
                  nullable=True, index=True,
                  comment='STEP 6: Node created for evaluation'),

        # Evaluation index
        sa.Column('evaluation_index', sa.Integer, nullable=False,
                  comment='STEP 6: Index in ensemble (0, 1, 2, ...)'),

        # Seed
        sa.Column('seed', sa.Integer, nullable=False,
                  comment='STEP 6: Seed for reproducibility'),

        # Simulation results
        sa.Column('simulation_outcome', postgresql.JSONB, nullable=True,
                  comment='STEP 6: Raw simulation outcome'),

        # Goal achievement
        sa.Column('goal_achieved', sa.Boolean, nullable=True,
                  comment='STEP 6: Did simulation reach goal state?'),
        sa.Column('goal_distance', sa.Float, nullable=True,
                  comment='STEP 6: Distance from goal at simulation end'),

        # Cost metrics
        sa.Column('execution_cost', sa.Float, nullable=True,
                  comment='STEP 6: Cost computed from simulation'),

        # Risk metrics
        sa.Column('outcome_variance', sa.Float, nullable=True,
                  comment='STEP 6: Variance in outcome metrics'),

        # Run status
        sa.Column('run_status', sa.String(50), nullable=False, default='pending',
                  comment='STEP 6: Status of the evaluation run'),

        # Timing
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Integer, nullable=True),

        # Error handling
        sa.Column('error_message', sa.Text, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
    )

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_plan_evaluations_candidate
        ON plan_evaluations (candidate_id, evaluation_index)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_plan_evaluations_run
        ON plan_evaluations (run_id)
    """)

    # ==========================================================================
    # 4. Create plan_traces table (STEP 6 Requirement 3)
    # ==========================================================================
    op.create_table(
        'plan_traces',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('planning_spec_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('planning_specs.id', ondelete='CASCADE'),
                  nullable=False, unique=True, index=True),

        # Search statistics
        sa.Column('total_candidates_generated', sa.Integer, nullable=False, default=0),
        sa.Column('candidates_pruned', sa.Integer, nullable=False, default=0),
        sa.Column('candidates_evaluated', sa.Integer, nullable=False, default=0),

        # Search algorithm details
        sa.Column('search_algorithm', sa.String(50), nullable=False, default='beam_search'),
        sa.Column('explored_states_count', sa.Integer, nullable=False, default=0,
                  comment='STEP 6: Number of unique states explored'),
        sa.Column('expanded_nodes_count', sa.Integer, nullable=False, default=0,
                  comment='STEP 6: Total node expansions in search'),

        # Pruning decisions (STEP 6: auditable)
        sa.Column('pruning_decisions', postgresql.JSONB, nullable=False, default=list,
                  comment='STEP 6: List of pruning decisions'),

        # Runs executed (STEP 6: auditable)
        sa.Column('runs_executed', postgresql.ARRAY(sa.String(50)),
                  nullable=False, server_default='{}',
                  comment='STEP 6: List of run_ids executed for evaluation'),
        sa.Column('total_runs_count', sa.Integer, nullable=False, default=0),

        # Scoring function (STEP 6 Requirement 4)
        sa.Column('scoring_function', postgresql.JSONB, nullable=False, default=dict,
                  comment='STEP 6: Explicit scoring function specification'),

        # Top-K results (STEP 6 Requirement 7)
        sa.Column('top_k_count', sa.Integer, nullable=False, default=5),
        sa.Column('top_k_results', postgresql.JSONB, nullable=False, default=list,
                  comment='STEP 6: Top-K plans with evidence links'),

        # Selected plan
        sa.Column('selected_candidate_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('plan_candidates.id', ondelete='SET NULL'),
                  nullable=True),

        # Timing
        sa.Column('search_time_ms', sa.Integer, nullable=False, default=0),
        sa.Column('evaluation_time_ms', sa.Integer, nullable=False, default=0),
        sa.Column('total_time_ms', sa.Integer, nullable=False, default=0),

        # Summary
        sa.Column('summary', sa.Text, nullable=True,
                  comment='STEP 6: Natural language summary'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
    )


def downgrade():
    # Drop tables in reverse order (respecting FK constraints)
    op.execute("DROP TABLE IF EXISTS plan_traces CASCADE")
    op.execute("DROP INDEX IF EXISTS ix_plan_evaluations_run")
    op.execute("DROP INDEX IF EXISTS ix_plan_evaluations_candidate")
    op.execute("DROP TABLE IF EXISTS plan_evaluations CASCADE")
    op.execute("DROP INDEX IF EXISTS ix_plan_candidates_score")
    op.execute("DROP INDEX IF EXISTS ix_plan_candidates_spec")
    op.execute("DROP TABLE IF EXISTS plan_candidates CASCADE")
    op.execute("DROP INDEX IF EXISTS ix_planning_specs_project")
    op.execute("DROP INDEX IF EXISTS ix_planning_specs_status")
    op.execute("DROP TABLE IF EXISTS planning_specs CASCADE")

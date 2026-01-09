"""Add predictive simulation tables

Revision ID: predictive_sim_001
Revises: dabd56adb2ca
Create Date: 2026-01-08 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'predictive_sim_001'
down_revision = 'dabd56adb2ca'
branch_labels = None
depends_on = None


def upgrade():
    # ============= SIMULATION ENVIRONMENTS =============
    op.create_table(
        'simulation_environments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('environment_type', sa.String(50), server_default='custom', nullable=False),
        sa.Column('country', sa.String(100), nullable=False),
        sa.Column('region_level', sa.String(50), server_default='country', nullable=False),
        sa.Column('regions', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('map_config', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('state_space', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('action_space', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_simulation_environments_user_id', 'simulation_environments', ['user_id'], unique=False)

    # ============= PREDICTION SCENARIOS =============
    op.create_table(
        'prediction_scenarios',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('environment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('target_event', sa.String(100), nullable=False),
        sa.Column('target_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('agent_count', sa.Integer(), server_default='1000', nullable=False),
        sa.Column('time_steps', sa.Integer(), server_default='100', nullable=False),
        sa.Column('step_duration_days', sa.Float(), server_default='1.0', nullable=False),
        sa.Column('agent_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('initial_state', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('event_ids', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('status', sa.String(50), server_default='draft', nullable=False),
        sa.Column('progress', sa.Integer(), server_default='0', nullable=False),
        sa.Column('current_step', sa.Integer(), server_default='0', nullable=False),
        sa.Column('prediction_results', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('calibration_metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('computation_time_seconds', sa.Float(), nullable=True),
        sa.Column('tokens_used', sa.Integer(), server_default='0', nullable=False),
        sa.Column('compute_credits_used', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['environment_id'], ['simulation_environments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_prediction_scenarios_environment_id', 'prediction_scenarios', ['environment_id'], unique=False)
    op.create_index('ix_prediction_scenarios_user_id', 'prediction_scenarios', ['user_id'], unique=False)
    op.create_index('ix_prediction_scenarios_status', 'prediction_scenarios', ['status'], unique=False)

    # ============= ENVIRONMENT STATES =============
    op.create_table(
        'environment_states',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('environment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('scenario_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('time_step', sa.Integer(), nullable=False),
        sa.Column('simulation_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('global_state', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('regional_states', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('aggregate_metrics', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['environment_id'], ['simulation_environments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['scenario_id'], ['prediction_scenarios.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_environment_states_environment_id', 'environment_states', ['environment_id'], unique=False)
    op.create_index('ix_environment_states_time_step', 'environment_states', ['time_step'], unique=False)

    # ============= EXTERNAL EVENTS =============
    op.create_table(
        'external_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('environment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('trigger_time_step', sa.Integer(), nullable=False),
        sa.Column('duration_steps', sa.Integer(), server_default='1', nullable=False),
        sa.Column('decay_rate', sa.Float(), server_default='0.1', nullable=False),
        sa.Column('impact', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_historical', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('historical_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('source_reference', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['environment_id'], ['simulation_environments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_external_events_environment_id', 'external_events', ['environment_id'], unique=False)

    # ============= GROUND TRUTHS =============
    op.create_table(
        'ground_truths',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('country', sa.String(100), nullable=False),
        sa.Column('region', sa.String(100), nullable=True),
        sa.Column('regions_covered', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('event_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('data_collection_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('outcomes', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('context_data', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('data_sources', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('data_quality_score', sa.Float(), server_default='0.95', nullable=False),
        sa.Column('is_verified', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('verified_by', sa.String(255), nullable=True),
        sa.Column('verification_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ground_truths_user_id', 'ground_truths', ['user_id'], unique=False)
    op.create_index('ix_ground_truths_event_type', 'ground_truths', ['event_type'], unique=False)
    op.create_index('ix_ground_truths_country', 'ground_truths', ['country'], unique=False)

    # ============= CALIBRATION RUNS =============
    op.create_table(
        'calibration_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ground_truth_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('calibration_method', sa.String(50), nullable=False),
        sa.Column('method_config', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('parameters_to_calibrate', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('initial_parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('status', sa.String(50), server_default='pending', nullable=False),
        sa.Column('progress', sa.Integer(), server_default='0', nullable=False),
        sa.Column('current_iteration', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_iterations', sa.Integer(), server_default='0', nullable=False),
        sa.Column('best_parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('best_metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('iteration_history', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('calibrated_predictions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('computation_time_seconds', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['ground_truth_id'], ['ground_truths.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_calibration_runs_ground_truth_id', 'calibration_runs', ['ground_truth_id'], unique=False)
    op.create_index('ix_calibration_runs_status', 'calibration_runs', ['status'], unique=False)

    # ============= PREDICTION RESULTS =============
    op.create_table(
        'prediction_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('scenario_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ground_truth_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('prediction_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('target_event_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('predictions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('confidence_intervals', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('monte_carlo_runs', sa.Integer(), server_default='1', nullable=False),
        sa.Column('distribution_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('scenario_comparisons', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('accuracy_metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('key_drivers', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('regional_predictions', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('demographic_predictions', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('overall_confidence', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('model_uncertainty', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['scenario_id'], ['prediction_scenarios.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['ground_truth_id'], ['ground_truths.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_prediction_results_scenario_id', 'prediction_results', ['scenario_id'], unique=False)

    # ============= ACCURACY BENCHMARKS =============
    op.create_table(
        'accuracy_benchmarks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('country', sa.String(100), nullable=False),
        sa.Column('total_predictions', sa.Integer(), server_default='0', nullable=False),
        sa.Column('predictions_within_ci', sa.Integer(), server_default='0', nullable=False),
        sa.Column('average_accuracy', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('average_rmse', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('average_mae', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('average_brier', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('best_accuracy', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('worst_accuracy', sa.Float(), server_default='1.0', nullable=False),
        sa.Column('prediction_history', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('accuracy_trend', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_accuracy_benchmarks_user_id', 'accuracy_benchmarks', ['user_id'], unique=False)

    # ============= SIMULATION AGENTS =============
    op.create_table(
        'simulation_agents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('scenario_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_index', sa.Integer(), nullable=False),
        sa.Column('agent_name', sa.String(100), nullable=True),
        sa.Column('region_id', sa.String(100), nullable=True),
        sa.Column('coordinates', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('state_vector', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('previous_state_vector', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('demographics', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('behavioral_params', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('psychographics', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('social_network', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('policy_type', sa.String(50), server_default='behavioral_economic', nullable=False),
        sa.Column('policy_config', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('memory', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('cumulative_reward', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('last_reward', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('reward_history', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('current_state', sa.String(50), server_default='idle', nullable=False),
        sa.Column('last_action', sa.String(100), nullable=True),
        sa.Column('last_action_step', sa.Integer(), server_default='0', nullable=False),
        sa.Column('committed_action', sa.String(100), nullable=True),
        sa.Column('commitment_strength', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('commitment_step', sa.Integer(), nullable=True),
        sa.Column('source_persona_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['scenario_id'], ['prediction_scenarios.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_simulation_agents_scenario_id', 'simulation_agents', ['scenario_id'], unique=False)
    op.create_index('ix_simulation_agents_agent_index', 'simulation_agents', ['agent_index'], unique=False)
    op.create_index('ix_simulation_agents_region_id', 'simulation_agents', ['region_id'], unique=False)

    # ============= AGENT ACTIONS =============
    op.create_table(
        'agent_actions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('time_step', sa.Integer(), nullable=False),
        sa.Column('state_before', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('action_probabilities', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('decision_context', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('reward', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('reward_components', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('state_after', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_terminal', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('advantage', sa.Float(), nullable=True),
        sa.Column('value_estimate', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['simulation_agents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_agent_actions_agent_id', 'agent_actions', ['agent_id'], unique=False)
    op.create_index('ix_agent_actions_time_step', 'agent_actions', ['time_step'], unique=False)

    # ============= AGENT INTERACTION LOGS =============
    op.create_table(
        'agent_interaction_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('time_step', sa.Integer(), nullable=False),
        sa.Column('interaction_type', sa.String(50), nullable=False),
        sa.Column('content', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('influence_magnitude', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('influence_direction', sa.String(100), nullable=True),
        sa.Column('state_change_vector', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['source_agent_id'], ['simulation_agents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_agent_id'], ['simulation_agents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_agent_interaction_logs_source_agent_id', 'agent_interaction_logs', ['source_agent_id'], unique=False)
    op.create_index('ix_agent_interaction_logs_time_step', 'agent_interaction_logs', ['time_step'], unique=False)

    # ============= POLICY MODELS =============
    op.create_table(
        'policy_models',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('environment_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('version', sa.String(50), server_default='1.0.0', nullable=False),
        sa.Column('architecture', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('training_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('training_status', sa.String(50), server_default='untrained', nullable=False),
        sa.Column('training_progress', sa.Integer(), server_default='0', nullable=False),
        sa.Column('training_episodes', sa.Integer(), server_default='0', nullable=False),
        sa.Column('performance_metrics', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('weights_path', sa.String(500), nullable=True),
        sa.Column('weights_checksum', sa.String(64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_trained_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['environment_id'], ['simulation_environments.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_policy_models_user_id', 'policy_models', ['user_id'], unique=False)
    op.create_index('ix_policy_models_training_status', 'policy_models', ['training_status'], unique=False)


def downgrade():
    # Drop tables in reverse order of creation
    op.drop_index('ix_policy_models_training_status', table_name='policy_models')
    op.drop_index('ix_policy_models_user_id', table_name='policy_models')
    op.drop_table('policy_models')

    op.drop_index('ix_agent_interaction_logs_time_step', table_name='agent_interaction_logs')
    op.drop_index('ix_agent_interaction_logs_source_agent_id', table_name='agent_interaction_logs')
    op.drop_table('agent_interaction_logs')

    op.drop_index('ix_agent_actions_time_step', table_name='agent_actions')
    op.drop_index('ix_agent_actions_agent_id', table_name='agent_actions')
    op.drop_table('agent_actions')

    op.drop_index('ix_simulation_agents_region_id', table_name='simulation_agents')
    op.drop_index('ix_simulation_agents_agent_index', table_name='simulation_agents')
    op.drop_index('ix_simulation_agents_scenario_id', table_name='simulation_agents')
    op.drop_table('simulation_agents')

    op.drop_index('ix_accuracy_benchmarks_user_id', table_name='accuracy_benchmarks')
    op.drop_table('accuracy_benchmarks')

    op.drop_index('ix_prediction_results_scenario_id', table_name='prediction_results')
    op.drop_table('prediction_results')

    op.drop_index('ix_calibration_runs_status', table_name='calibration_runs')
    op.drop_index('ix_calibration_runs_ground_truth_id', table_name='calibration_runs')
    op.drop_table('calibration_runs')

    op.drop_index('ix_ground_truths_country', table_name='ground_truths')
    op.drop_index('ix_ground_truths_event_type', table_name='ground_truths')
    op.drop_index('ix_ground_truths_user_id', table_name='ground_truths')
    op.drop_table('ground_truths')

    op.drop_index('ix_external_events_environment_id', table_name='external_events')
    op.drop_table('external_events')

    op.drop_index('ix_environment_states_time_step', table_name='environment_states')
    op.drop_index('ix_environment_states_environment_id', table_name='environment_states')
    op.drop_table('environment_states')

    op.drop_index('ix_prediction_scenarios_status', table_name='prediction_scenarios')
    op.drop_index('ix_prediction_scenarios_user_id', table_name='prediction_scenarios')
    op.drop_index('ix_prediction_scenarios_environment_id', table_name='prediction_scenarios')
    op.drop_table('prediction_scenarios')

    op.drop_index('ix_simulation_environments_user_id', table_name='simulation_environments')
    op.drop_table('simulation_environments')

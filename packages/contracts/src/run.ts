/**
 * RunConfig and Run Contracts
 * Reference: project.md §6.5, §6.6
 *
 * RunConfig defines execution parameters.
 * Run is the artifact produced by execution.
 */

import {
  ArtifactVersion,
  RunStatus,
  Timestamps,
  TenantScoped,
  ArtifactRef
} from './common';

// ============================================================================
// Seed Strategy
// ============================================================================

export type SeedStrategy =
  | 'single'      // One deterministic run
  | 'multi'       // Multiple runs with different seeds for variance analysis
  | 'adaptive';   // Adjust seed count based on variance

export interface SeedConfig {
  strategy: SeedStrategy;
  primary_seed: number;

  // For multi-seed runs
  additional_seeds?: number[];
  seed_count?: number;  // If not specifying explicit seeds

  // For adaptive strategy
  target_variance_threshold?: number;
  max_seeds?: number;
}

// ============================================================================
// Logging Profile
// ============================================================================

export interface LoggingProfile {
  // Keyframe frequency
  keyframe_interval_ticks: number;

  // What to include in keyframes
  include_full_world_state: boolean;
  include_agent_states: boolean;
  include_aggregated_only: boolean;

  // Delta stream sampling
  delta_sampling_rate: number;  // 0-1, what fraction of deltas to log

  // Key agent tracking
  track_key_agents: boolean;
  key_agent_ids?: string[];

  // Region-level aggregation
  aggregate_by_region: boolean;
  aggregate_by_segment: boolean;
}

// ============================================================================
// Scheduler Profile
// ============================================================================

export type SchedulerType =
  | 'synchronous'  // All agents act each tick
  | 'async_random' // Random subset acts each tick
  | 'event_driven' // Agents act in response to events
  | 'priority';    // Priority-based scheduling

export interface SchedulerProfile {
  scheduler_type: SchedulerType;

  // For async scheduling
  activation_probability?: number;

  // For priority scheduling
  priority_function?: string;  // Reference to priority function

  // Performance tuning
  batch_size?: number;
  parallelism_level?: number;
}

// ============================================================================
// Scenario Patch (variable changes for this run)
// ============================================================================

export interface ScenarioPatch {
  // Environment variable overrides
  environment_overrides: Record<string, unknown>;

  // Event bundle to apply
  event_bundle_ref?: string;

  // Inline events (if not using bundle)
  inline_events?: string[];  // event_ids

  // Constraints (for Target Mode)
  constraints?: {
    hard_constraints: Record<string, unknown>;
    soft_constraints: Record<string, { value: unknown; weight: number }>;
  };

  // Description of what this patch represents
  patch_description?: string;
}

// ============================================================================
// RunConfig (project.md §6.5)
// ============================================================================

export interface RunConfig extends TenantScoped, Timestamps {
  // Identity
  config_id: string;
  project_id: string;

  // Versioning (critical for reproducibility)
  versions: ArtifactVersion;

  // Randomness
  seed_config: SeedConfig;

  // Execution parameters
  horizon: number;  // Number of ticks to run
  tick_rate: number;  // Logical tick rate (ticks per time unit)

  // Scheduling
  scheduler_profile: SchedulerProfile;

  // Logging
  logging_profile: LoggingProfile;

  // Scenario modifications
  scenario_patch?: ScenarioPatch;

  // Resource limits
  max_execution_time_ms?: number;
  max_agents?: number;

  // Metadata
  label?: string;
  description?: string;

  // Whether this config is a template
  is_template: boolean;
}

// ============================================================================
// Run Timing
// ============================================================================

export interface RunTiming {
  queued_at: string;   // ISO 8601
  started_at?: string;
  ended_at?: string;

  // Tick progress
  current_tick: number;
  total_ticks: number;

  // Performance metrics
  ticks_per_second?: number;
  estimated_completion?: string;
}

// ============================================================================
// Run Outputs (references to artifacts)
// ============================================================================

export interface RunOutputs {
  // Primary results
  results_ref: ArtifactRef;

  // Telemetry for replay
  telemetry_ref: ArtifactRef;

  // Optional snapshots (world state at specific points)
  snapshot_refs?: ArtifactRef[];

  // Aggregated outcomes
  aggregated_outcome_ref?: ArtifactRef;

  // Reliability report
  reliability_ref?: ArtifactRef;
}

// ============================================================================
// Run Error
// ============================================================================

export interface RunError {
  error_code: string;
  error_message: string;
  tick_at_failure?: number;
  stack_trace?: string;
  recoverable: boolean;
}

// ============================================================================
// Run (project.md §6.6)
// ============================================================================

export interface Run extends TenantScoped, Timestamps {
  // Identity
  run_id: string;
  node_id: string;     // Parent node this run belongs to
  project_id: string;

  // Configuration reference
  run_config_ref: string;  // config_id

  // Status
  status: RunStatus;

  // Timing
  timing: RunTiming;

  // Outputs (populated when succeeded)
  outputs?: RunOutputs;

  // Error info (populated when failed)
  error?: RunError;

  // Seed used for this specific run (from SeedConfig)
  actual_seed: number;

  // Worker information
  worker_id?: string;

  // Metadata
  label?: string;
  triggered_by: 'user' | 'system' | 'schedule' | 'api';
  triggered_by_user_id?: string;
}

// ============================================================================
// Run Results (aggregated outcomes)
// ============================================================================

export interface RunResults {
  run_id: string;

  // Primary outcome metrics
  outcome_distribution: Record<string, number>;

  // Time series data
  metric_time_series: {
    metric_name: string;
    values: { tick: number; value: number }[];
  }[];

  // Key events that occurred
  key_events: {
    tick: number;
    event_type: string;
    description: string;
    impact_score: number;
  }[];

  // Turning points (significant changes)
  turning_points: {
    tick: number;
    metric: string;
    direction: 'increase' | 'decrease';
    magnitude: number;
  }[];

  // Final state summary
  final_state_summary: Record<string, unknown>;
}

// ============================================================================
// Create/Update DTOs
// ============================================================================

export interface CreateRunConfigInput {
  project_id: string;
  versions?: Partial<ArtifactVersion>;
  seed_config: SeedConfig;
  horizon: number;
  tick_rate?: number;
  scheduler_profile?: Partial<SchedulerProfile>;
  logging_profile?: Partial<LoggingProfile>;
  scenario_patch?: ScenarioPatch;
  label?: string;
  description?: string;
  is_template?: boolean;
}

export interface SubmitRunInput {
  node_id: string;
  config_id?: string;  // If not provided, use project defaults
  config_overrides?: Partial<CreateRunConfigInput>;
  label?: string;
}

export interface RunProgressUpdate {
  run_id: string;
  status: RunStatus;
  current_tick: number;
  ticks_per_second?: number;
  estimated_completion?: string;
}

// ============================================================================
// Run Summary (for lists)
// ============================================================================

export interface RunSummary {
  run_id: string;
  node_id: string;
  status: RunStatus;
  timing: Pick<RunTiming, 'started_at' | 'ended_at' | 'current_tick' | 'total_ticks'>;
  has_results: boolean;
  triggered_by: Run['triggered_by'];
  created_at: string;
}

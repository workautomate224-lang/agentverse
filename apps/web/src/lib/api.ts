/**
 * API Client for AgentVerse Backend
 */

// Use empty string for relative URLs (production), fallback to localhost only if undefined
const API_URL = process.env.NEXT_PUBLIC_API_URL !== undefined
  ? process.env.NEXT_PUBLIC_API_URL
  : 'http://localhost:8000';

export interface ApiError {
  detail: string;
  status: number;
}

// Auth Types
export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name?: string;
  company?: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserResponse {
  id: string;
  email: string;
  full_name: string | null;
  company: string | null;
  role: string;
  tier: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  updated_at: string;
  last_login_at: string | null;
}

// Project Types
export interface Project {
  id: string;
  name: string;
  description: string | null;
  domain: string;
  settings: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  name: string;
  description?: string;
  domain: string;
  settings?: Record<string, unknown>;
}

export interface ProjectUpdate {
  name?: string;
  description?: string;
  domain?: string;
  settings?: Record<string, unknown>;
}

export interface ProjectStats {
  project_id: string;
  scenario_count: number;
  simulation_count: number;
  total_cost_usd: number;
}

// Scenario Types
export interface Question {
  id: string;
  text: string;
  type: 'open_ended' | 'multiple_choice' | 'yes_no' | 'scale';
  options?: string[];
  scale_min?: number;
  scale_max?: number;
  required?: boolean;
}

export interface Demographics {
  age_distribution?: Record<string, number>;
  gender_distribution?: Record<string, number>;
  income_distribution?: Record<string, number>;
  education_distribution?: Record<string, number>;
  region_distribution?: Record<string, number>;
}

export interface Scenario {
  id: string;
  project_id: string;
  name: string;
  description: string | null;
  scenario_type: string;
  context: string;
  questions: Question[];
  variables: Record<string, unknown>;
  population_size: number;
  demographics: Demographics;
  persona_template: Record<string, unknown> | null;
  model_config_json: Record<string, unknown>;
  simulation_mode: string;
  status: 'draft' | 'ready' | 'running' | 'completed';
  created_at: string;
  updated_at: string;
}

export interface ScenarioCreate {
  project_id: string;
  name: string;
  description?: string;
  scenario_type: string;
  context: string;
  questions: Question[];
  variables?: Record<string, unknown>;
  population_size: number;
  demographics: Demographics;
  persona_template?: Record<string, unknown>;
  model_config_json?: Record<string, unknown>;
  simulation_mode?: string;
}

export interface ScenarioUpdate {
  name?: string;
  description?: string;
  context?: string;
  questions?: Question[];
  variables?: Record<string, unknown>;
  population_size?: number;
  demographics?: Demographics;
  persona_template?: Record<string, unknown>;
  model_config_json?: Record<string, unknown>;
  simulation_mode?: string;
  status?: string;
}

export interface ScenarioValidation {
  scenario_id: string;
  is_valid: boolean;
  status: string;
  errors: string[];
  warnings: string[];
}

// Simulation Types
export interface SimulationRun {
  id: string;
  scenario_id: string;
  user_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  agent_count: number;
  model_used: string;
  run_config: Record<string, unknown>;
  results_summary: ResultsSummary | null;
  confidence_score: number | null;
  tokens_used: number;
  cost_usd: number;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface SimulationRunCreate {
  scenario_id: string;
  agent_count: number;
  model_used?: string;
  run_config?: Record<string, unknown>;
}

export interface ResultsSummary {
  total_agents: number;
  response_distribution: Record<string, number>;
  response_percentages: Record<string, number>;
  demographics_breakdown: Record<string, Record<string, Record<string, number>>>;
  confidence_score: number;
  top_response: string | null;
}

export interface AgentResponse {
  id: string;
  run_id: string;
  agent_index: number;
  persona: {
    demographics: Record<string, unknown>;
    psychographics: Record<string, unknown>;
  };
  question_id: string | null;
  response: Record<string, unknown>;
  reasoning: string | null;
  tokens_used: number;
  response_time_ms: number;
  model_used: string;
}

export interface SimulationStats {
  total_runs: number;
  completed_runs: number;
  total_agents_simulated: number;
  total_cost_usd: number;
  total_tokens_used: number;
}

// =============================================================================
// Spec-Compliant Types (project.md §6.5-6.8)
// =============================================================================

// Run Status
export type SpecRunStatus = 'queued' | 'starting' | 'running' | 'succeeded' | 'failed' | 'cancelled';

// Seed Configuration
export type SeedStrategy = 'single' | 'multi' | 'adaptive';

export interface SeedConfig {
  strategy: SeedStrategy;
  primary_seed: number;
  additional_seeds?: number[];
  seed_count?: number;
  target_variance_threshold?: number;
  max_seeds?: number;
}

// Logging Profile
export interface LoggingProfile {
  keyframe_interval_ticks: number;
  include_full_world_state: boolean;
  include_agent_states: boolean;
  include_aggregated_only: boolean;
  delta_sampling_rate: number;
  track_key_agents: boolean;
  key_agent_ids?: string[];
  aggregate_by_region: boolean;
  aggregate_by_segment: boolean;
}

// Scheduler Profile
export type SchedulerType = 'synchronous' | 'async_random' | 'event_driven' | 'priority';

export interface SchedulerProfile {
  scheduler_type: SchedulerType;
  activation_probability?: number;
  priority_function?: string;
  batch_size?: number;
  parallelism_level?: number;
}

// Scenario Patch
export interface ScenarioPatch {
  environment_overrides: Record<string, unknown>;
  event_bundle_ref?: string;
  inline_events?: string[];
  constraints?: {
    hard_constraints: Record<string, unknown>;
    soft_constraints: Record<string, { value: unknown; weight: number }>;
  };
  patch_description?: string;
}

// Artifact Version
export interface ArtifactVersion {
  engine_version: string;
  ruleset_version: string;
  dataset_version: string;
  schema_version: string;
}

// Run Config (§6.5)
export interface SpecRunConfig {
  config_id: string;
  project_id: string;
  versions: ArtifactVersion;
  seed_config: SeedConfig;
  horizon: number;
  tick_rate: number;
  scheduler_profile: SchedulerProfile;
  logging_profile: LoggingProfile;
  scenario_patch?: ScenarioPatch;
  max_execution_time_ms?: number;
  max_agents?: number;
  label?: string;
  description?: string;
  is_template: boolean;
  created_at: string;
  updated_at: string;
}

// Run Timing
export interface RunTiming {
  queued_at: string;
  started_at?: string;
  ended_at?: string;
  current_tick: number;
  total_ticks: number;
  ticks_per_second?: number;
  estimated_completion?: string;
}

// Run Outputs
export interface RunOutputs {
  results_ref: { artifact_type: string; artifact_id: string; storage_path: string; storage_backend: string };
  telemetry_ref: { artifact_type: string; artifact_id: string; storage_path: string; storage_backend: string };
  snapshot_refs?: { artifact_type: string; artifact_id: string; storage_path: string; storage_backend: string }[];
  aggregated_outcome_ref?: { artifact_type: string; artifact_id: string; storage_path: string; storage_backend: string };
  reliability_ref?: { artifact_type: string; artifact_id: string; storage_path: string; storage_backend: string };
}

// Run Error
export interface RunError {
  error_code: string;
  error_message: string;
  tick_at_failure?: number;
  stack_trace?: string;
  recoverable: boolean;
}

// Run (§6.6)
export interface SpecRun {
  run_id: string;
  node_id: string;
  project_id: string;
  run_config_ref: string;
  status: SpecRunStatus;
  timing: RunTiming;
  outputs?: RunOutputs;
  error?: RunError;
  actual_seed: number;
  worker_id?: string;
  label?: string;
  triggered_by: 'user' | 'system' | 'schedule' | 'api';
  triggered_by_user_id?: string;
  created_at: string;
  updated_at: string;
}

// Run Summary
export interface RunSummary {
  run_id: string;
  node_id: string;
  status: SpecRunStatus;
  timing: Pick<RunTiming, 'started_at' | 'ended_at' | 'current_tick' | 'total_ticks'>;
  has_results: boolean;
  triggered_by: SpecRun['triggered_by'];
  created_at: string;
}

// Run Results
export interface SpecRunResults {
  run_id: string;
  outcome_distribution: Record<string, number>;
  metric_time_series: { metric_name: string; values: { tick: number; value: number }[] }[];
  key_events: { tick: number; event_type: string; description: string; impact_score: number }[];
  turning_points: { tick: number; metric: string; direction: 'increase' | 'decrease'; magnitude: number }[];
  final_state_summary: Record<string, unknown>;
}

// Run Progress Update
export interface RunProgressUpdate {
  run_id: string;
  status: SpecRunStatus;
  current_tick: number;
  ticks_per_second?: number;
  estimated_completion?: string;
}

// Create Run Config Input
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

// Submit Run Input
export interface SubmitRunInput {
  node_id: string;
  config_id?: string;
  config_overrides?: Partial<CreateRunConfigInput>;
  label?: string;
}

// =============================================================================
// Node/Edge Types (Universe Map - project.md §6.7)
// =============================================================================

export type ConfidenceLevel = 'very_low' | 'low' | 'medium' | 'high' | 'very_high';

// Aggregated Outcome
export interface AggregatedOutcome {
  primary_outcome: string;
  primary_outcome_probability: number;
  outcome_distribution: Record<string, number>;
  key_metrics: { metric_name: string; value: number; unit?: string; trend?: 'increasing' | 'stable' | 'decreasing' }[];
  variance_metrics?: Record<string, number>;
  summary_text?: string;
}

// Node Confidence
export interface NodeConfidence {
  confidence_level: ConfidenceLevel;
  confidence_score: number;
  factors: { factor_name: string; score: number; weight: number; notes?: string }[];
  reliability_ref?: { artifact_type: string; artifact_id: string; storage_path: string; storage_backend: string };
}

// Node (§6.7)
export interface SpecNode {
  node_id: string;
  project_id: string;
  parent_node_id?: string;
  depth: number;
  scenario_patch_ref?: { artifact_type: string; artifact_id: string; storage_path: string; storage_backend: string };
  run_refs: { artifact_type: string; artifact_id: string; storage_path: string; storage_backend: string }[];
  aggregated_outcome?: AggregatedOutcome;
  probability: number;
  cumulative_probability: number;
  confidence: NodeConfidence;
  telemetry_ref?: { artifact_type: string; artifact_id: string; storage_path: string; storage_backend: string };
  cluster_id?: string;
  is_cluster_representative: boolean;
  ui_position?: { x: number; y: number };
  is_collapsed: boolean;
  is_pinned: boolean;
  label?: string;
  description?: string;
  tags?: string[];
  is_baseline: boolean;
  is_explored: boolean;
  child_count: number;
  created_at: string;
  updated_at: string;
}

// Edge Intervention
export type InterventionType = 'event_script' | 'variable_delta' | 'nl_query' | 'expansion';

export interface EdgeIntervention {
  intervention_type: InterventionType;
  event_script_ref?: { artifact_type: string; artifact_id: string; storage_path: string; storage_backend: string };
  variable_deltas?: Record<string, unknown>;
  nl_query?: string;
  expansion_strategy?: 'user_ask' | 'auto_explore' | 'sensitivity';
}

// Edge Explanation
export interface EdgeExplanation {
  short_label: string;
  explanation_text: string;
  key_differentiators: string[];
  generated_by: 'compiler' | 'system' | 'user';
}

// Edge (§6.7)
export interface SpecEdge {
  edge_id: string;
  project_id: string;
  from_node_id: string;
  to_node_id: string;
  intervention: EdgeIntervention;
  explanation: EdgeExplanation;
  is_primary_path: boolean;
  weight?: number;
  created_at: string;
  updated_at: string;
}

// Node Summary
export interface NodeSummary {
  node_id: string;
  parent_node_id?: string;
  label?: string;
  probability: number;
  confidence_level: ConfidenceLevel;
  is_baseline: boolean;
  has_outcome: boolean;
  child_count: number;
  created_at: string;
}

// Edge Summary
export interface EdgeSummary {
  edge_id: string;
  from_node_id: string;
  to_node_id: string;
  short_label: string;
  intervention_type: InterventionType;
}

// Universe Map State
export interface UniverseMapState {
  project_id: string;
  root_node_id: string;
  visible_nodes: string[];
  visible_edges: string[];
  visible_clusters: string[];
  selected_node_id?: string;
  compared_node_ids?: string[];
  zoom_level: number;
  viewport_center: { x: number; y: number };
  probability_threshold: number;
  show_low_confidence: boolean;
}

// Path Analysis
export interface PathAnalysis {
  path_id: string;
  node_sequence: string[];
  path_probability: number;
  summary: string;
  key_events: string[];
  final_outcome: AggregatedOutcome;
}

// Node Cluster
export interface NodeCluster {
  cluster_id: string;
  project_id: string;
  label: string;
  description?: string;
  member_node_ids: string[];
  representative_node_id: string;
  cluster_outcome?: AggregatedOutcome;
  cluster_probability: number;
  is_expanded: boolean;
  expandable: boolean;
  ui_position?: { x: number; y: number };
}

// Fork Node Input
export interface ForkNodeInput {
  parent_node_id: string;
  label?: string;
  description?: string;
  scenario_patch?: ScenarioPatch;
  intervention_type?: InterventionType;
  nl_query?: string;
}

// Compare Nodes Response
export interface CompareNodesResponse {
  nodes: SpecNode[];
  outcome_comparison: Record<string, Record<string, number>>;
  key_differences: { metric: string; node_id: string; value: number; rank: number }[];
  recommendation?: string;
}

// =============================================================================
// Telemetry Types (project.md §6.8)
// =============================================================================

// World Keyframe
export interface WorldKeyframe {
  tick: number;
  timestamp: string;
  environment_state: Record<string, unknown>;
  global_metrics: Record<string, number>;
  active_events: string[];
  agent_counts: { total: number; active: number; by_segment: Record<string, number> };
}

// Region Keyframe
export interface RegionKeyframe {
  tick: number;
  region_id: string;
  aggregated_state: Record<string, number>;
  agent_distribution: Record<string, number>;
  metrics: Record<string, number>;
}

// Telemetry Delta
export type DeltaType = 'agent_state' | 'segment_aggregate' | 'environment' | 'event_trigger' | 'event_end' | 'agent_action' | 'metric_update';

export interface TelemetryDelta {
  delta_id: string;
  tick: number;
  delta_type: DeltaType;
  target_id?: string;
  field_path?: string;
  old_value?: unknown;
  new_value: unknown;
  caused_by?: string;
  region_id?: string;
  is_sampled: boolean;
  sample_weight?: number;
}

// Delta Stream
export interface DeltaStream {
  run_id: string;
  start_tick: number;
  end_tick: number;
  deltas: TelemetryDelta[];
  sampling_rate: number;
  total_deltas_original: number;
  total_deltas_sampled: number;
}

// Metric Time Series
export interface MetricTimeSeries {
  metric_name: string;
  unit?: string;
  data_points: { tick: number; value: number }[];
  aggregation_method?: 'sum' | 'mean' | 'max' | 'min' | 'last';
  region_id?: string;
  segment_id?: string;
}

// Event Occurrence
export interface EventOccurrence {
  event_id: string;
  start_tick: number;
  end_tick?: number;
  affected_agent_count: number;
  affected_regions: string[];
  peak_intensity: number;
  attributed_outcome_delta?: Record<string, number>;
}

// Telemetry Index
export interface TelemetryIndex {
  tick_index: { tick: number; keyframe_offset?: number; delta_range: [number, number] }[];
  region_index: Record<string, number[]>;
  segment_index: Record<string, number[]>;
  key_agent_index: Record<string, number[]>;
  available_metrics: string[];
}

// Telemetry Summary
export interface TelemetrySummary {
  telemetry_id: string;
  run_id: string;
  node_id: string;
  tick_count: number;
  keyframe_count: number;
  delta_count: number;
  size_bytes: number;
  created_at: string;
  available_metrics: string[];
  tracked_agents: number;
}

// Telemetry Slice (for replay)
export interface TelemetrySlice {
  tick: number;
  world_keyframe?: WorldKeyframe;
  deltas: TelemetryDelta[];
  is_interpolated: boolean;
}

// Telemetry Playback State
export interface TelemetryPlaybackState {
  telemetry_id: string;
  current_tick: number;
  total_ticks: number;
  current_world_state: WorldKeyframe;
  current_region_states: Record<string, RegionKeyframe>;
  active_events: string[];
  playback_speed: number;
  is_playing: boolean;
}

// =============================================================================
// Project Spec Types (project.md §6.1)
// =============================================================================

export interface ProjectSpecSettings {
  default_horizon: number;
  default_tick_rate: number;
  default_agent_count: number;
  allow_public_templates: boolean;
}

export interface ProjectSpec {
  id: string;
  name: string;
  description?: string;
  domain: string;
  settings: ProjectSpecSettings;
  default_run_config?: Partial<CreateRunConfigInput>;
  root_node_id?: string;
  node_count: number;
  run_count: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectSpecCreate {
  name: string;
  description?: string;
  domain: string;
  settings?: Partial<ProjectSpecSettings>;
  default_run_config?: Partial<CreateRunConfigInput>;
}

export interface ProjectSpecUpdate {
  name?: string;
  description?: string;
  domain?: string;
  settings?: Partial<ProjectSpecSettings>;
  default_run_config?: Partial<CreateRunConfigInput>;
}

export interface ProjectSpecStats {
  project_id: string;
  node_count: number;
  run_count: number;
  completed_runs: number;
  failed_runs: number;
  total_tokens_used: number;
  total_cost_usd: number;
  last_run_at?: string;
}

// =============================================================================
// Ask / Event Compiler Types (project.md §11 Phase 4)
// =============================================================================

export type AskIntentType = 'event' | 'variable' | 'query' | 'comparison' | 'explanation';
export type AskPromptScope = 'global' | 'regional' | 'segment' | 'individual' | 'temporal';

export interface AskExtractedIntent {
  intent_type: AskIntentType;
  confidence: number;
  original_prompt: string;
  normalized_prompt: string;
  scope: AskPromptScope;
  affected_regions: string[];
  affected_segments: string[];
  temporal_scope?: {
    start_tick?: number;
    end_tick?: number;
    duration?: number;
  };
  entities_mentioned: string[];
  keywords: string[];
}

export interface AskSubEffect {
  effect_id: string;
  description: string;
  target_variable: string;
  magnitude: number;
  duration_ticks?: number;
  delay_ticks?: number;
  confidence: number;
  dependencies: string[];
}

export interface AskVariableMapping {
  effect_id: string;
  source_concept: string;
  target_variable: string;
  transform_type: 'direct' | 'scaled' | 'inverted' | 'threshold' | 'composite';
  transform_params?: Record<string, unknown>;
  confidence: number;
  reasoning: string;
}

export interface AskCandidateScenario {
  scenario_id: string;
  label: string;
  description: string;
  variable_deltas: Record<string, number>;
  total_magnitude: number;
  confidence: number;
  event_script_preview?: {
    intensity_profile: string;
    scope: string;
    estimated_duration_ticks: number;
  };
  parent_cluster_id?: string;
  is_expanded?: boolean;
}

export interface AskScenarioCluster {
  cluster_id: string;
  label: string;
  description: string;
  scenario_count: number;
  magnitude_range: { min: number; max: number };
  representative_scenario: AskCandidateScenario;
  child_scenarios?: AskCandidateScenario[];
  is_expanded: boolean;
}

export interface AskCausalExplanation {
  summary: string;
  causal_chain: Array<{
    from_concept: string;
    to_concept: string;
    relationship: string;
    strength: number;
  }>;
  key_assumptions: string[];
  potential_side_effects: string[];
  confidence_factors: string[];
  uncertainty_sources: string[];
}

export interface AskCompilationResult {
  compilation_id: string;
  original_prompt: string;
  intent: AskExtractedIntent;
  sub_effects: AskSubEffect[];
  variable_mappings: AskVariableMapping[];
  candidate_scenarios: AskCandidateScenario[];
  clusters: AskScenarioCluster[];
  explanation: AskCausalExplanation;
  compiler_version: string;
  compiled_at: string;
  total_cost_usd: number;
  compilation_time_ms: number;
  warnings: string[];
}

export interface AskCompileRequest {
  project_id: string;
  prompt: string;
  max_scenarios?: number;
  clustering_enabled?: boolean;
}

export interface AskExpandClusterRequest {
  compilation_id: string;
  cluster_id: string;
  max_children?: number;
}

export interface AskCompilationListItem {
  compilation_id: string;
  prompt: string;
  intent_type: AskIntentType;
  scenario_count: number;
  compiled_at: string;
}

// =============================================================================
// Target Mode Types (project.md §11 Phase 5)
// =============================================================================

export type UtilityDimension =
  | 'wealth' | 'status' | 'security' | 'freedom' | 'relationships'
  | 'health' | 'achievement' | 'comfort' | 'power' | 'knowledge'
  | 'pleasure' | 'reputation' | 'custom';

export type ConstraintType = 'hard' | 'soft';
export type ActionCategory =
  | 'financial' | 'social' | 'professional' | 'personal'
  | 'consumption' | 'communication' | 'movement' | 'legal' | 'health' | 'custom';
export type PlanStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
export type PathStatus = 'valid' | 'pruned' | 'selected' | 'executed';

export interface UtilityWeight {
  dimension: UtilityDimension;
  weight: number;
  target_value?: number | null;
  threshold_min?: number | null;
  threshold_max?: number | null;
}

export interface UtilityFunction {
  weights: UtilityWeight[];
  risk_aversion: number;
  time_preference: number;
  loss_aversion: number;
  custom_objectives?: Record<string, number> | null;
}

export interface StateCondition {
  variable: string;
  operator: string;
  value: unknown;
}

export interface StateEffect {
  variable: string;
  operation: string;
  value: unknown;
  probability: number;
}

export interface ActionPrior {
  action_id: string;
  base_probability: number;
  context_modifiers?: Record<string, number> | null;
}

export interface ActionDefinition {
  action_id: string;
  name: string;
  description?: string | null;
  category: ActionCategory;
  preconditions: StateCondition[];
  effects: StateEffect[];
  monetary_cost: number;
  time_cost: number;
  effort_cost: number;
  social_cost: number;
  opportunity_cost: number;
  risk_level: number;
  failure_probability: number;
  reversibility: number;
  duration?: number | null;
  cooldown?: number | null;
  requires_actions?: string[] | null;
  blocks_actions?: string[] | null;
  tags?: string[] | null;
  domain_specific?: Record<string, unknown> | null;
}

export interface ActionCatalog {
  catalog_id: string;
  domain: string;
  version: string;
  actions: ActionDefinition[];
  created_at: string;
}

export interface TargetConstraint {
  constraint_id: string;
  name: string;
  description?: string | null;
  constraint_type: ConstraintType;
  condition: StateCondition;
  penalty_weight?: number | null;
  violation_explanation?: string | null;
  source?: string | null;
  priority: number;
}

export interface TargetPersona {
  target_id: string;
  persona_id?: string | null;
  name: string;
  description?: string | null;
  utility_function: UtilityFunction;
  action_priors: ActionPrior[];
  initial_state: Record<string, unknown>;
  action_catalog_id?: string | null;
  custom_actions?: ActionDefinition[] | null;
  personal_constraints?: TargetConstraint[] | null;
  planning_horizon: number;
  discount_factor: number;
  exploration_rate: number;
  domain?: string | null;
  tags?: string[] | null;
  created_at: string;
  updated_at: string;
}

export interface TargetPersonaCreate {
  name: string;
  description?: string | null;
  persona_id?: string | null;
  utility_function?: Partial<UtilityFunction> | null;
  action_priors?: ActionPrior[] | null;
  initial_state?: Record<string, unknown> | null;
  action_catalog_id?: string | null;
  custom_actions?: ActionDefinition[] | null;
  personal_constraints?: TargetConstraint[] | null;
  planning_horizon?: number;
  discount_factor?: number;
  exploration_rate?: number;
  domain?: string | null;
  tags?: string[] | null;
}

export interface PathStep {
  step_index: number;
  action: ActionDefinition;
  state_before: Record<string, unknown>;
  state_after: Record<string, unknown>;
  effects_applied: StateEffect[];
  utility_gained: number;
  cumulative_utility: number;
  probability: number;
  constraints_checked?: string[] | null;
  constraints_violated?: string[] | null;
}

export interface TargetPath {
  path_id: string;
  steps: PathStep[];
  path_probability: number;
  success_probability: number;
  total_utility: number;
  utility_variance?: number | null;
  total_cost: number;
  total_time: number;
  total_risk: number;
  status: PathStatus;
  pruning_reason?: string | null;
  cluster_id?: string | null;
  is_representative: boolean;
}

export interface PathCluster {
  cluster_id: string;
  label: string;
  description?: string | null;
  representative_path: TargetPath;
  child_paths: TargetPath[];
  aggregated_probability: number;
  avg_utility: number;
  utility_range: [number, number];
  is_expanded: boolean;
  expansion_depth: number;
  can_expand: boolean;
  common_actions?: string[] | null;
  distinguishing_features?: string[] | null;
}

export interface PlanResult {
  plan_id: string;
  target_id: string;
  project_id: string;
  status: PlanStatus;
  error_message?: string | null;
  total_paths_generated: number;
  total_paths_valid: number;
  total_paths_pruned: number;
  clusters: PathCluster[];
  top_paths: TargetPath[];
  hard_constraints_applied: string[];
  soft_constraints_applied: string[];
  paths_pruned_by_constraint: Record<string, number>;
  planning_summary?: string | null;
  key_decision_points?: string[] | null;
  planning_time_ms: number;
  created_at: string;
  completed_at?: string | null;
}

export interface TargetPlanRequest {
  project_id: string;
  target_id: string;
  max_paths?: number;
  max_depth?: number;
  pruning_threshold?: number;
  enable_clustering?: boolean;
  max_clusters?: number;
  additional_constraints?: TargetConstraint[] | null;
  disable_soft_constraints?: boolean;
  environment_state?: Record<string, unknown> | null;
  start_node_id?: string | null;
}

export interface ExpandClusterRequest {
  plan_id: string;
  cluster_id: string;
  max_paths?: number;
}

export interface BranchToNodeRequest {
  plan_id: string;
  path_id: string;
  parent_node_id: string;
  label?: string | null;
  auto_run?: boolean;
}

export interface TargetPlanListItem {
  plan_id: string;
  target_id: string;
  target_name: string;
  project_id: string;
  status: PlanStatus;
  total_paths: number;
  total_clusters: number;
  top_path_utility?: number | null;
  created_at: string;
  completed_at?: string | null;
}

export interface ActionCatalogListItem {
  catalog_id: string;
  domain: string;
  version: string;
  action_count: number;
  created_at: string;
}

// =============================================================================
// Hybrid Mode Types (project.md §11 Phase 6)
// =============================================================================

export type CouplingDirection = 'actor_to_society' | 'society_to_actor' | 'bidirectional';
export type CouplingStrength = 'none' | 'weak' | 'moderate' | 'strong' | 'dominant';
export type HybridRunStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface CouplingConfig {
  direction: CouplingDirection;
  actor_influence_strength: CouplingStrength;
  society_feedback_strength: CouplingStrength;
  influence_decay_rate: number;
  influence_radius_segments: string[];
  synchronization_interval: number;
  actor_action_amplification: number;
  society_pressure_weight: number;
}

export interface HybridAgentConfig {
  target_id: string;
  target_name: string;
  utility_function: UtilityFunction;
  action_priors: ActionPrior[];
  initial_state: Record<string, unknown>;
  personal_constraints?: TargetConstraint[] | null;
  planning_horizon: number;
}

export interface PopulationContext {
  persona_set_id?: string | null;
  segment_filter?: string[] | null;
  region_filter?: string[] | null;
  agent_count: number;
  segment_distribution?: Record<string, number> | null;
  region_distribution?: Record<string, number> | null;
  initial_stance_distribution?: Record<string, number> | null;
}

export interface HybridRunRequest {
  project_id: string;
  key_actors: string[];
  population_context: PopulationContext;
  coupling_config: CouplingConfig;
  num_ticks: number;
  seed?: number | null;
  parent_node_id?: string | null;
  label?: string | null;
  auto_create_node?: boolean;
}

export interface HybridActorOutcome {
  target_id: string;
  target_name: string;
  final_state: Record<string, unknown>;
  total_utility: number;
  actions_taken: string[];
  path_probability: number;
  influence_exerted: number;
  society_pressure_received: number;
}

export interface HybridSocietyOutcome {
  final_avg_stance: number;
  stance_shift: number;
  final_segment_distribution: Record<string, number>;
  influenced_agent_count: number;
  total_influence_received: number;
  key_events: string[];
}

export interface HybridCouplingEffect {
  tick: number;
  source_type: 'actor' | 'society';
  source_id: string;
  effect_type: string;
  magnitude: number;
  affected_count: number;
  variables_affected: string[];
}

export interface HybridRunProgress {
  run_id: string;
  status: HybridRunStatus;
  progress_pct: number;
  current_tick: number;
  total_ticks: number;
  actors_processed: number;
  society_agents_processed: number;
  coupling_effects_count: number;
  estimated_remaining_seconds?: number | null;
}

export interface HybridRunResult {
  run_id: string;
  project_id: string;
  status: HybridRunStatus;
  error_message?: string | null;
  key_actors: HybridAgentConfig[];
  population_context: PopulationContext;
  coupling_config: CouplingConfig;
  actor_outcomes: HybridActorOutcome[];
  society_outcome: HybridSocietyOutcome;
  coupling_effects: HybridCouplingEffect[];
  total_ticks: number;
  seed_used: number;
  execution_time_ms: number;
  telemetry_ref?: string | null;
  node_id?: string | null;
  created_at: string;
  completed_at?: string | null;
}

export interface HybridRunListItem {
  run_id: string;
  project_id: string;
  status: HybridRunStatus;
  key_actor_count: number;
  population_size: number;
  coupling_direction: CouplingDirection;
  actor_influence: CouplingStrength;
  total_ticks: number;
  avg_actor_utility?: number | null;
  society_stance_shift?: number | null;
  node_id?: string | null;
  created_at: string;
  completed_at?: string | null;
}

class ApiClient {
  private baseUrl: string;
  private accessToken: string | null = null;
  // Request deduplication map - prevents duplicate concurrent requests
  private pendingRequests: Map<string, Promise<unknown>> = new Map();
  // Request abort controllers for cancellation
  private abortControllers: Map<string, AbortController> = new Map();

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  setAccessToken(token: string | null) {
    this.accessToken = token;
  }

  getAccessToken(): string | null {
    return this.accessToken;
  }

  // Generate cache key for request deduplication
  private getRequestKey(endpoint: string, options: RequestInit = {}): string {
    return `${options.method || 'GET'}:${endpoint}:${options.body || ''}`;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    deduplicate = true
  ): Promise<T> {
    const requestKey = this.getRequestKey(endpoint, options);

    // For GET requests, check if there's already a pending request
    if (deduplicate && (!options.method || options.method === 'GET')) {
      const pendingRequest = this.pendingRequests.get(requestKey);
      if (pendingRequest) {
        return pendingRequest as Promise<T>;
      }
    }

    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.accessToken) {
      (headers as Record<string, string>)['Authorization'] = `Bearer ${this.accessToken}`;
    }

    // Create abort controller for this request
    const abortController = new AbortController();
    this.abortControllers.set(requestKey, abortController);

    const requestPromise = (async () => {
      try {
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
          ...options,
          headers,
          signal: abortController.signal,
        });

        if (!response.ok) {
          const error = await response.json().catch(() => ({ detail: 'An error occurred' }));
          throw {
            detail: error.detail || 'An error occurred',
            status: response.status,
          } as ApiError;
        }

        return response.json();
      } catch (error: unknown) {
        // Handle network errors (API unavailable, connection refused, etc.)
        if (error instanceof TypeError && error.message.includes('fetch')) {
          throw {
            detail: 'Unable to connect to server. Please check your connection and try again.',
            status: 0,
          } as ApiError;
        }
        // Handle abort errors
        if (error instanceof DOMException && error.name === 'AbortError') {
          throw {
            detail: 'Request was cancelled',
            status: 0,
          } as ApiError;
        }
        // Re-throw ApiError
        if (error && typeof error === 'object' && 'detail' in error) {
          throw error;
        }
        // Handle other network errors
        throw {
          detail: 'Network error. Please check your connection and try again.',
          status: 0,
        } as ApiError;
      } finally {
        // Clean up after request completes
        this.pendingRequests.delete(requestKey);
        this.abortControllers.delete(requestKey);
      }
    })();

    // Store pending request for deduplication
    if (deduplicate && (!options.method || options.method === 'GET')) {
      this.pendingRequests.set(requestKey, requestPromise);
    }

    return requestPromise;
  }

  // Cancel all pending requests (useful on logout or navigation)
  cancelAllRequests() {
    this.abortControllers.forEach(controller => controller.abort());
    this.pendingRequests.clear();
    this.abortControllers.clear();
  }

  // Health check - returns true if API is available
  // Always uses relative URL to go through Next.js rewrites (avoids Mixed Content on HTTPS)
  async checkHealth(): Promise<{ healthy: boolean; version?: string; error?: string }> {
    try {
      // Always use relative path to go through Next.js rewrites
      // This avoids Mixed Content errors when site is served over HTTPS
      const response = await fetch('/api/health', {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });
      if (response.ok) {
        const data = await response.json();
        return { healthy: true, version: data.version };
      }
      return { healthy: false, error: `Server returned ${response.status}` };
    } catch {
      return { healthy: false, error: 'Unable to connect to server' };
    }
  }

  // Auth endpoints
  async login(data: LoginRequest): Promise<TokenResponse> {
    return this.request<TokenResponse>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async register(data: RegisterRequest): Promise<UserResponse> {
    return this.request<UserResponse>('/api/v1/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getCurrentUser(): Promise<UserResponse> {
    return this.request<UserResponse>('/api/v1/auth/me');
  }

  async refreshToken(refreshToken: string): Promise<TokenResponse> {
    return this.request<TokenResponse>('/api/v1/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  }

  async logout(): Promise<void> {
    await this.request('/api/v1/auth/logout', {
      method: 'POST',
    });
  }

  // Project endpoints
  async listProjects(params?: {
    skip?: number;
    limit?: number;
    domain?: string;
    search?: string;
  }): Promise<Project[]> {
    const searchParams = new URLSearchParams();
    if (params?.skip) searchParams.set('skip', String(params.skip));
    if (params?.limit) searchParams.set('limit', String(params.limit));
    if (params?.domain) searchParams.set('domain', params.domain);
    if (params?.search) searchParams.set('search', params.search);

    const query = searchParams.toString();
    return this.request<Project[]>(`/api/v1/projects${query ? `?${query}` : ''}`);
  }

  async createProject(data: ProjectCreate): Promise<Project> {
    return this.request<Project>('/api/v1/projects/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getProject(projectId: string): Promise<Project> {
    return this.request<Project>(`/api/v1/projects/${projectId}`);
  }

  async updateProject(projectId: string, data: ProjectUpdate): Promise<Project> {
    return this.request<Project>(`/api/v1/projects/${projectId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteProject(projectId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/api/v1/projects/${projectId}`, {
      method: 'DELETE',
    });
  }

  async duplicateProject(projectId: string, newName?: string): Promise<Project> {
    const params = newName ? `?new_name=${encodeURIComponent(newName)}` : '';
    return this.request<Project>(`/api/v1/projects/${projectId}/duplicate${params}`, {
      method: 'POST',
    });
  }

  async getProjectStats(projectId: string): Promise<ProjectStats> {
    return this.request<ProjectStats>(`/api/v1/projects/${projectId}/stats`);
  }

  // Scenario endpoints
  async listScenarios(params?: {
    project_id?: string;
    skip?: number;
    limit?: number;
    status?: string;
    scenario_type?: string;
  }): Promise<Scenario[]> {
    const searchParams = new URLSearchParams();
    if (params?.project_id) searchParams.set('project_id', params.project_id);
    if (params?.skip) searchParams.set('skip', String(params.skip));
    if (params?.limit) searchParams.set('limit', String(params.limit));
    if (params?.status) searchParams.set('status_filter', params.status);
    if (params?.scenario_type) searchParams.set('scenario_type', params.scenario_type);

    const query = searchParams.toString();
    return this.request<Scenario[]>(`/api/v1/scenarios${query ? `?${query}` : ''}`);
  }

  async createScenario(data: ScenarioCreate): Promise<Scenario> {
    return this.request<Scenario>('/api/v1/scenarios/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getScenario(scenarioId: string): Promise<Scenario> {
    return this.request<Scenario>(`/api/v1/scenarios/${scenarioId}`);
  }

  async updateScenario(scenarioId: string, data: ScenarioUpdate): Promise<Scenario> {
    return this.request<Scenario>(`/api/v1/scenarios/${scenarioId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteScenario(scenarioId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/api/v1/scenarios/${scenarioId}`, {
      method: 'DELETE',
    });
  }

  async duplicateScenario(
    scenarioId: string,
    newName?: string,
    targetProjectId?: string
  ): Promise<Scenario> {
    const params = new URLSearchParams();
    if (newName) params.set('new_name', newName);
    if (targetProjectId) params.set('target_project_id', targetProjectId);
    const query = params.toString();

    return this.request<Scenario>(`/api/v1/scenarios/${scenarioId}/duplicate${query ? `?${query}` : ''}`, {
      method: 'POST',
    });
  }

  async validateScenario(scenarioId: string): Promise<ScenarioValidation> {
    return this.request<ScenarioValidation>(`/api/v1/scenarios/${scenarioId}/validate`, {
      method: 'POST',
    });
  }

  // Simulation endpoints
  async listSimulations(params?: {
    scenario_id?: string;
    status?: string;
    skip?: number;
    limit?: number;
  }): Promise<SimulationRun[]> {
    const searchParams = new URLSearchParams();
    if (params?.scenario_id) searchParams.set('scenario_id', params.scenario_id);
    if (params?.status) searchParams.set('status_filter', params.status);
    if (params?.skip) searchParams.set('skip', String(params.skip));
    if (params?.limit) searchParams.set('limit', String(params.limit));

    const query = searchParams.toString();
    return this.request<SimulationRun[]>(`/api/v1/simulations${query ? `?${query}` : ''}`);
  }

  async createSimulation(data: SimulationRunCreate): Promise<SimulationRun> {
    return this.request<SimulationRun>('/api/v1/simulations/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getSimulation(runId: string): Promise<SimulationRun> {
    return this.request<SimulationRun>(`/api/v1/simulations/${runId}`);
  }

  async runSimulation(runId: string): Promise<SimulationRun> {
    return this.request<SimulationRun>(`/api/v1/simulations/${runId}/run`, {
      method: 'POST',
    });
  }

  async cancelSimulation(runId: string): Promise<{ message: string; run_id: string }> {
    return this.request<{ message: string; run_id: string }>(`/api/v1/simulations/${runId}/cancel`, {
      method: 'POST',
    });
  }

  async getSimulationResults(runId: string): Promise<{
    run_id: string;
    scenario_id: string;
    status: string;
    agent_count: number;
    model_used: string;
    results_summary: ResultsSummary;
    confidence_score: number;
    tokens_used: number;
    cost_usd: number;
    started_at: string | null;
    completed_at: string | null;
    duration_seconds: number | null;
  }> {
    return this.request(`/api/v1/simulations/${runId}/results`);
  }

  async getAgentResponses(
    runId: string,
    params?: {
      skip?: number;
      limit?: number;
      question_id?: string;
    }
  ): Promise<AgentResponse[]> {
    const searchParams = new URLSearchParams();
    if (params?.skip) searchParams.set('skip', String(params.skip));
    if (params?.limit) searchParams.set('limit', String(params.limit));
    if (params?.question_id) searchParams.set('question_id', params.question_id);

    const query = searchParams.toString();
    return this.request<AgentResponse[]>(`/api/v1/simulations/${runId}/agents${query ? `?${query}` : ''}`);
  }

  async exportSimulation(
    runId: string,
    format: 'csv' | 'json' | 'xlsx' = 'csv'
  ): Promise<Blob> {
    const response = await fetch(`${this.baseUrl}/api/v1/simulations/${runId}/export?format=${format}`, {
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Export failed' }));
      throw { detail: error.detail || 'Export failed', status: response.status };
    }

    return response.blob();
  }

  getExportUrl(runId: string, format: 'csv' | 'json' | 'xlsx' = 'csv'): string {
    return `${this.baseUrl}/api/v1/simulations/${runId}/export?format=${format}`;
  }

  async getSimulationStats(): Promise<SimulationStats> {
    return this.request<SimulationStats>('/api/v1/simulations/stats/overview');
  }

  // Stream simulation progress (SSE)
  streamSimulation(runId: string, token: string): EventSource {
    const url = `${this.baseUrl}/api/v1/simulations/${runId}/stream`;
    const eventSource = new EventSource(url);
    return eventSource;
  }

  // Get authorization headers
  private getHeaders(): HeadersInit {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };
    if (this.accessToken) {
      (headers as Record<string, string>)['Authorization'] = `Bearer ${this.accessToken}`;
    }
    return headers;
  }

  // ========== Data Source Endpoints ==========

  async listDataSources(params?: {
    skip?: number;
    limit?: number;
    source_type?: string;
  }): Promise<DataSource[]> {
    const searchParams = new URLSearchParams();
    if (params?.skip) searchParams.set('skip', String(params.skip));
    if (params?.limit) searchParams.set('limit', String(params.limit));
    if (params?.source_type) searchParams.set('source_type', params.source_type);

    const query = searchParams.toString();
    return this.request<DataSource[]>(`/api/v1/data-sources${query ? `?${query}` : ''}`);
  }

  async getDataSource(dataSourceId: string): Promise<DataSource> {
    return this.request<DataSource>(`/api/v1/data-sources/${dataSourceId}`);
  }

  async createDataSource(data: DataSourceCreate): Promise<DataSource> {
    return this.request<DataSource>('/api/v1/data-sources/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateDataSource(dataSourceId: string, data: DataSourceUpdate): Promise<DataSource> {
    return this.request<DataSource>(`/api/v1/data-sources/${dataSourceId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteDataSource(dataSourceId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/api/v1/data-sources/${dataSourceId}`, {
      method: 'DELETE',
    });
  }

  // Census Data Endpoints
  async getUSStates(): Promise<Record<string, string>> {
    return this.request<Record<string, string>>('/api/v1/data-sources/census/states');
  }

  async getCensusDemographics(
    category: 'age' | 'gender' | 'income' | 'education' | 'occupation',
    params?: {
      state?: string;
      county?: string;
      year?: number;
    }
  ): Promise<DemographicDistribution> {
    const searchParams = new URLSearchParams();
    if (params?.state) searchParams.set('state', params.state);
    if (params?.county) searchParams.set('county', params.county);
    if (params?.year) searchParams.set('year', String(params.year));

    const query = searchParams.toString();
    return this.request<DemographicDistribution>(
      `/api/v1/data-sources/census/demographics/${category}${query ? `?${query}` : ''}`
    );
  }

  async getCensusProfile(params?: {
    state?: string;
    county?: string;
    year?: number;
  }): Promise<CensusProfile> {
    const searchParams = new URLSearchParams();
    if (params?.state) searchParams.set('state', params.state);
    if (params?.county) searchParams.set('county', params.county);
    if (params?.year) searchParams.set('year', String(params.year));

    const query = searchParams.toString();
    return this.request<CensusProfile>(
      `/api/v1/data-sources/census/profile${query ? `?${query}` : ''}`
    );
  }

  async syncCensusData(data: {
    state?: string;
    county?: string;
    year?: number;
  }): Promise<CensusSyncResult> {
    return this.request<CensusSyncResult>('/api/v1/data-sources/census/sync', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Regional Profile Endpoints
  async listRegionalProfiles(params?: {
    skip?: number;
    limit?: number;
    region_type?: string;
  }): Promise<RegionalProfile[]> {
    const searchParams = new URLSearchParams();
    if (params?.skip) searchParams.set('skip', String(params.skip));
    if (params?.limit) searchParams.set('limit', String(params.limit));
    if (params?.region_type) searchParams.set('region_type', params.region_type);

    const query = searchParams.toString();
    return this.request<RegionalProfile[]>(`/api/v1/data-sources/profiles/${query ? `?${query}` : ''}`);
  }

  async getRegionalProfile(regionCode: string): Promise<RegionalProfile> {
    return this.request<RegionalProfile>(`/api/v1/data-sources/profiles/${regionCode}`);
  }

  async buildRegionalProfile(params: {
    region_code: string;
    region_name: string;
    state?: string;
    county?: string;
  }): Promise<RegionalProfileBuildResult> {
    const searchParams = new URLSearchParams();
    searchParams.set('region_code', params.region_code);
    searchParams.set('region_name', params.region_name);
    if (params.state) searchParams.set('state', params.state);
    if (params.county) searchParams.set('county', params.county);

    return this.request<RegionalProfileBuildResult>(
      `/api/v1/data-sources/profiles/build?${searchParams.toString()}`,
      { method: 'POST' }
    );
  }

  // ========== Persona Endpoints ==========

  // Template Management
  async listPersonaTemplates(params?: {
    skip?: number;
    limit?: number;
    region?: string;
    source_type?: string;
  }): Promise<PersonaTemplate[]> {
    const searchParams = new URLSearchParams();
    if (params?.skip) searchParams.set('skip', String(params.skip));
    if (params?.limit) searchParams.set('limit', String(params.limit));
    if (params?.region) searchParams.set('region', params.region);
    if (params?.source_type) searchParams.set('source_type', params.source_type);

    const query = searchParams.toString();
    return this.request<PersonaTemplate[]>(`/api/v1/personas/templates${query ? `?${query}` : ''}`);
  }

  async createPersonaTemplate(data: PersonaTemplateCreate): Promise<PersonaTemplate> {
    return this.request<PersonaTemplate>('/api/v1/personas/templates', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getPersonaTemplate(templateId: string): Promise<PersonaTemplate> {
    return this.request<PersonaTemplate>(`/api/v1/personas/templates/${templateId}`);
  }

  async deletePersonaTemplate(templateId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/api/v1/personas/templates/${templateId}`, {
      method: 'DELETE',
    });
  }

  // Persona Generation
  async generatePersonas(data: GeneratePersonasRequest): Promise<GeneratePersonasResponse> {
    return this.request<GeneratePersonasResponse>('/api/v1/personas/generate', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async listPersonas(
    templateId: string,
    params?: { skip?: number; limit?: number }
  ): Promise<PersonaRecord[]> {
    const searchParams = new URLSearchParams();
    if (params?.skip) searchParams.set('skip', String(params.skip));
    if (params?.limit) searchParams.set('limit', String(params.limit));

    const query = searchParams.toString();
    return this.request<PersonaRecord[]>(
      `/api/v1/personas/templates/${templateId}/personas${query ? `?${query}` : ''}`
    );
  }

  // File Upload
  async analyzePersonaUpload(file: File): Promise<FileAnalysisResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${this.baseUrl}/api/v1/personas/upload/analyze`, {
      method: 'POST',
      headers: this.accessToken ? { Authorization: `Bearer ${this.accessToken}` } : {},
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Analysis failed' }));
      throw { detail: error.detail, status: response.status };
    }

    return response.json();
  }

  async processPersonaUpload(
    file: File,
    mapping: Record<string, string>,
    templateId?: string
  ): Promise<UploadResult> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('mapping', JSON.stringify(mapping));
    if (templateId) formData.append('template_id', templateId);

    const response = await fetch(`${this.baseUrl}/api/v1/personas/upload/process`, {
      method: 'POST',
      headers: this.accessToken ? { Authorization: `Bearer ${this.accessToken}` } : {},
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw { detail: error.detail, status: response.status };
    }

    return response.json();
  }

  getPersonaUploadTemplateUrl(): string {
    return `${this.baseUrl}/api/v1/personas/upload/template`;
  }

  async listPersonaUploads(params?: {
    skip?: number;
    limit?: number;
  }): Promise<Record<string, unknown>[]> {
    const searchParams = new URLSearchParams();
    if (params?.skip) searchParams.set('skip', String(params.skip));
    if (params?.limit) searchParams.set('limit', String(params.limit));

    const query = searchParams.toString();
    return this.request<Record<string, unknown>[]>(`/api/v1/personas/uploads${query ? `?${query}` : ''}`);
  }

  // AI Research
  async startAIResearch(data: AIResearchRequest): Promise<AIResearchJob> {
    return this.request<AIResearchJob>('/api/v1/personas/research', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getAIResearchJob(jobId: string): Promise<AIResearchJob> {
    return this.request<AIResearchJob>(`/api/v1/personas/research/${jobId}`);
  }

  async listAIResearchJobs(params?: {
    skip?: number;
    limit?: number;
  }): Promise<AIResearchJob[]> {
    const searchParams = new URLSearchParams();
    if (params?.skip) searchParams.set('skip', String(params.skip));
    if (params?.limit) searchParams.set('limit', String(params.limit));

    const query = searchParams.toString();
    return this.request<AIResearchJob[]>(`/api/v1/personas/research${query ? `?${query}` : ''}`);
  }

  // Region Information
  async listSupportedRegions(): Promise<RegionInfo[]> {
    return this.request<RegionInfo[]>('/api/v1/personas/regions');
  }

  async getRegionDemographics(
    regionCode: string,
    params?: {
      country?: string;
      sub_region?: string;
      year?: number;
    }
  ): Promise<Record<string, unknown>> {
    const searchParams = new URLSearchParams();
    if (params?.country) searchParams.set('country', params.country);
    if (params?.sub_region) searchParams.set('sub_region', params.sub_region);
    if (params?.year) searchParams.set('year', String(params.year));

    const query = searchParams.toString();
    return this.request<Record<string, unknown>>(
      `/api/v1/personas/regions/${regionCode}/demographics${query ? `?${query}` : ''}`
    );
  }

  // =============================================================================
  // Spec-Compliant Run Endpoints (project.md §6.5-6.6)
  // =============================================================================

  async listRuns(params?: {
    project_id?: string;
    node_id?: string;
    status?: SpecRunStatus;
    skip?: number;
    limit?: number;
  }): Promise<RunSummary[]> {
    const searchParams = new URLSearchParams();
    if (params?.project_id) searchParams.set('project_id', params.project_id);
    if (params?.node_id) searchParams.set('node_id', params.node_id);
    if (params?.status) searchParams.set('status', params.status);
    if (params?.skip) searchParams.set('skip', String(params.skip));
    if (params?.limit) searchParams.set('limit', String(params.limit));

    const query = searchParams.toString();
    return this.request<RunSummary[]>(`/api/v1/runs${query ? `?${query}` : ''}`);
  }

  async getRun(runId: string): Promise<SpecRun> {
    return this.request<SpecRun>(`/api/v1/runs/${runId}`);
  }

  async createRun(data: SubmitRunInput): Promise<SpecRun> {
    return this.request<SpecRun>('/api/v1/runs', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async startRun(runId: string): Promise<SpecRun> {
    return this.request<SpecRun>(`/api/v1/runs/${runId}/start`, {
      method: 'POST',
    });
  }

  async cancelRun(runId: string): Promise<{ message: string; run_id: string }> {
    return this.request<{ message: string; run_id: string }>(`/api/v1/runs/${runId}/cancel`, {
      method: 'POST',
    });
  }

  async getRunProgress(runId: string): Promise<RunProgressUpdate> {
    return this.request<RunProgressUpdate>(`/api/v1/runs/${runId}/progress`);
  }

  async getRunResults(runId: string): Promise<SpecRunResults> {
    return this.request<SpecRunResults>(`/api/v1/runs/${runId}/results`);
  }

  // Stream run progress (SSE)
  streamRunProgress(runId: string): EventSource {
    const url = `${this.baseUrl}/api/v1/runs/${runId}/stream`;
    return new EventSource(url);
  }

  // Batch run operations (multi-seed)
  async createBatchRuns(params: {
    node_id: string;
    config_id?: string;
    seed_count: number;
    label_prefix?: string;
  }): Promise<SpecRun[]> {
    return this.request<SpecRun[]>('/api/v1/runs/batch', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  }

  async listRunConfigs(params?: {
    project_id?: string;
    is_template?: boolean;
    skip?: number;
    limit?: number;
  }): Promise<SpecRunConfig[]> {
    const searchParams = new URLSearchParams();
    if (params?.project_id) searchParams.set('project_id', params.project_id);
    if (params?.is_template !== undefined) searchParams.set('is_template', String(params.is_template));
    if (params?.skip) searchParams.set('skip', String(params.skip));
    if (params?.limit) searchParams.set('limit', String(params.limit));

    const query = searchParams.toString();
    return this.request<SpecRunConfig[]>(`/api/v1/runs/configs${query ? `?${query}` : ''}`);
  }

  async createRunConfig(data: CreateRunConfigInput): Promise<SpecRunConfig> {
    return this.request<SpecRunConfig>('/api/v1/runs/configs', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // =============================================================================
  // Node/Universe Map Endpoints (project.md §6.7)
  // =============================================================================

  async listNodes(params?: {
    project_id?: string;
    parent_node_id?: string;
    skip?: number;
    limit?: number;
  }): Promise<NodeSummary[]> {
    const searchParams = new URLSearchParams();
    if (params?.project_id) searchParams.set('project_id', params.project_id);
    if (params?.parent_node_id) searchParams.set('parent_node_id', params.parent_node_id);
    if (params?.skip) searchParams.set('skip', String(params.skip));
    if (params?.limit) searchParams.set('limit', String(params.limit));

    const query = searchParams.toString();
    return this.request<NodeSummary[]>(`/api/v1/nodes${query ? `?${query}` : ''}`);
  }

  async getNode(nodeId: string): Promise<SpecNode> {
    return this.request<SpecNode>(`/api/v1/nodes/${nodeId}`);
  }

  async forkNode(data: ForkNodeInput): Promise<{ node: SpecNode; edge: SpecEdge }> {
    return this.request<{ node: SpecNode; edge: SpecEdge }>('/api/v1/nodes/fork', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getNodeChildren(nodeId: string): Promise<NodeSummary[]> {
    return this.request<NodeSummary[]>(`/api/v1/nodes/${nodeId}/children`);
  }

  async getNodeEdges(nodeId: string): Promise<EdgeSummary[]> {
    return this.request<EdgeSummary[]>(`/api/v1/nodes/${nodeId}/edges`);
  }

  async updateNodeUI(nodeId: string, data: {
    ui_position?: { x: number; y: number };
    is_collapsed?: boolean;
    is_pinned?: boolean;
  }): Promise<SpecNode> {
    return this.request<SpecNode>(`/api/v1/nodes/${nodeId}/ui`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async getUniverseMap(projectId: string): Promise<UniverseMapState> {
    return this.request<UniverseMapState>(`/api/v1/nodes/universe-map/${projectId}`);
  }

  async getUniverseMapFull(projectId: string): Promise<{
    state: UniverseMapState;
    nodes: SpecNode[];
    edges: SpecEdge[];
    clusters: NodeCluster[];
  }> {
    return this.request<{
      state: UniverseMapState;
      nodes: SpecNode[];
      edges: SpecEdge[];
      clusters: NodeCluster[];
    }>(`/api/v1/nodes/universe-map/${projectId}/full`);
  }

  async compareNodes(nodeIds: string[]): Promise<CompareNodesResponse> {
    return this.request<CompareNodesResponse>('/api/v1/nodes/compare', {
      method: 'POST',
      body: JSON.stringify({ node_ids: nodeIds }),
    });
  }

  async analyzeNodePath(params: {
    start_node_id: string;
    end_node_id: string;
  }): Promise<PathAnalysis> {
    return this.request<PathAnalysis>('/api/v1/nodes/path-analysis', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  }

  async getMostLikelyPaths(projectId: string, maxPaths?: number): Promise<PathAnalysis[]> {
    const params = maxPaths ? `?max_paths=${maxPaths}` : '';
    return this.request<PathAnalysis[]>(`/api/v1/nodes/universe-map/${projectId}/likely-paths${params}`);
  }

  // =============================================================================
  // Telemetry Endpoints (project.md §6.8) - READ-ONLY (C3 Compliant)
  // =============================================================================

  async getTelemetryIndex(runId: string): Promise<TelemetryIndex> {
    return this.request<TelemetryIndex>(`/api/v1/telemetry/${runId}`);
  }

  async getTelemetrySlice(runId: string, tick: number): Promise<TelemetrySlice> {
    return this.request<TelemetrySlice>(`/api/v1/telemetry/${runId}/slice?tick=${tick}`);
  }

  async getTelemetryRange(runId: string, params: {
    start_tick: number;
    end_tick: number;
    include_keyframes?: boolean;
    include_deltas?: boolean;
    max_deltas?: number;
  }): Promise<{
    keyframes: WorldKeyframe[];
    deltas: TelemetryDelta[];
  }> {
    const searchParams = new URLSearchParams();
    searchParams.set('start_tick', String(params.start_tick));
    searchParams.set('end_tick', String(params.end_tick));
    if (params.include_keyframes !== undefined) searchParams.set('include_keyframes', String(params.include_keyframes));
    if (params.include_deltas !== undefined) searchParams.set('include_deltas', String(params.include_deltas));
    if (params.max_deltas) searchParams.set('max_deltas', String(params.max_deltas));

    return this.request<{ keyframes: WorldKeyframe[]; deltas: TelemetryDelta[] }>(
      `/api/v1/telemetry/${runId}/range?${searchParams.toString()}`
    );
  }

  async getTelemetryKeyframe(runId: string, tick: number): Promise<WorldKeyframe> {
    return this.request<WorldKeyframe>(`/api/v1/telemetry/${runId}/keyframe/${tick}`);
  }

  async getTelemetryMetric(runId: string, metricName: string, params?: {
    start_tick?: number;
    end_tick?: number;
    downsample_factor?: number;
  }): Promise<MetricTimeSeries> {
    const searchParams = new URLSearchParams();
    if (params?.start_tick) searchParams.set('start_tick', String(params.start_tick));
    if (params?.end_tick) searchParams.set('end_tick', String(params.end_tick));
    if (params?.downsample_factor) searchParams.set('downsample_factor', String(params.downsample_factor));

    const query = searchParams.toString();
    return this.request<MetricTimeSeries>(
      `/api/v1/telemetry/${runId}/metrics/${metricName}${query ? `?${query}` : ''}`
    );
  }

  async getTelemetryAgentHistory(runId: string, agentId: string, params?: {
    start_tick?: number;
    end_tick?: number;
  }): Promise<TelemetryDelta[]> {
    const searchParams = new URLSearchParams();
    if (params?.start_tick) searchParams.set('start_tick', String(params.start_tick));
    if (params?.end_tick) searchParams.set('end_tick', String(params.end_tick));

    const query = searchParams.toString();
    return this.request<TelemetryDelta[]>(
      `/api/v1/telemetry/${runId}/agents/${agentId}${query ? `?${query}` : ''}`
    );
  }

  async getTelemetryEvents(runId: string): Promise<EventOccurrence[]> {
    return this.request<EventOccurrence[]>(`/api/v1/telemetry/${runId}/events`);
  }

  async getTelemetrySummary(runId: string): Promise<TelemetrySummary> {
    return this.request<TelemetrySummary>(`/api/v1/telemetry/${runId}/summary`);
  }

  // Stream telemetry for live replay (SSE)
  streamTelemetry(runId: string, params?: {
    start_tick?: number;
    speed?: number;
  }): EventSource {
    const searchParams = new URLSearchParams();
    if (params?.start_tick) searchParams.set('start_tick', String(params.start_tick));
    if (params?.speed) searchParams.set('speed', String(params.speed));

    const query = searchParams.toString();
    return new EventSource(`${this.baseUrl}/api/v1/telemetry/${runId}/stream${query ? `?${query}` : ''}`);
  }

  // Export telemetry data
  async exportTelemetry(runId: string, params?: {
    format?: 'json' | 'csv' | 'parquet';
    include_keyframes?: boolean;
    include_deltas?: boolean;
  }): Promise<{ download_url: string; size_bytes: number; expires_at: string }> {
    const searchParams = new URLSearchParams();
    if (params?.format) searchParams.set('format', params.format);
    if (params?.include_keyframes !== undefined) searchParams.set('include_keyframes', String(params.include_keyframes));
    if (params?.include_deltas !== undefined) searchParams.set('include_deltas', String(params.include_deltas));

    const query = searchParams.toString();
    return this.request<{ download_url: string; size_bytes: number; expires_at: string }>(
      `/api/v1/telemetry/${runId}/export${query ? `?${query}` : ''}`,
      { method: 'POST' }
    );
  }

  // =============================================================================
  // Project Spec Endpoints (project.md §6.1)
  // =============================================================================

  async listProjectSpecs(params?: {
    skip?: number;
    limit?: number;
    domain?: string;
    search?: string;
  }): Promise<ProjectSpec[]> {
    const searchParams = new URLSearchParams();
    if (params?.skip) searchParams.set('skip', String(params.skip));
    if (params?.limit) searchParams.set('limit', String(params.limit));
    if (params?.domain) searchParams.set('domain', params.domain);
    if (params?.search) searchParams.set('search', params.search);

    const query = searchParams.toString();
    return this.request<ProjectSpec[]>(`/api/v1/project-specs${query ? `?${query}` : ''}`);
  }

  async getProjectSpec(projectId: string): Promise<ProjectSpec> {
    return this.request<ProjectSpec>(`/api/v1/project-specs/${projectId}`);
  }

  async createProjectSpec(data: ProjectSpecCreate): Promise<ProjectSpec> {
    return this.request<ProjectSpec>('/api/v1/project-specs', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateProjectSpec(projectId: string, data: ProjectSpecUpdate): Promise<ProjectSpec> {
    return this.request<ProjectSpec>(`/api/v1/project-specs/${projectId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteProjectSpec(projectId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/api/v1/project-specs/${projectId}`, {
      method: 'DELETE',
    });
  }

  async getProjectSpecStats(projectId: string): Promise<ProjectSpecStats> {
    return this.request<ProjectSpecStats>(`/api/v1/project-specs/${projectId}/stats`);
  }

  async duplicateProjectSpec(projectId: string, newName?: string): Promise<ProjectSpec> {
    const params = newName ? `?new_name=${encodeURIComponent(newName)}` : '';
    return this.request<ProjectSpec>(`/api/v1/project-specs/${projectId}/duplicate${params}`, {
      method: 'POST',
    });
  }

  async createProjectSpecRun(projectId: string, data: {
    node_id?: string;
    config_overrides?: Partial<CreateRunConfigInput>;
  }): Promise<SpecRun> {
    return this.request<SpecRun>(`/api/v1/project-specs/${projectId}/runs`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // ========== Product Endpoints ==========

  async listProducts(params?: {
    project_id?: string;
    product_type?: string;
    status?: string;
    skip?: number;
    limit?: number;
  }): Promise<Product[]> {
    const searchParams = new URLSearchParams();
    if (params?.project_id) searchParams.set('project_id', params.project_id);
    if (params?.product_type) searchParams.set('product_type', params.product_type);
    if (params?.status) searchParams.set('status', params.status);
    if (params?.skip) searchParams.set('skip', String(params.skip));
    if (params?.limit) searchParams.set('limit', String(params.limit));

    const query = searchParams.toString();
    return this.request<Product[]>(`/api/v1/products${query ? `?${query}` : ''}`);
  }

  async createProduct(data: ProductCreate): Promise<Product> {
    return this.request<Product>('/api/v1/products/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getProduct(productId: string): Promise<Product> {
    return this.request<Product>(`/api/v1/products/${productId}`);
  }

  async updateProduct(productId: string, data: ProductUpdate): Promise<Product> {
    return this.request<Product>(`/api/v1/products/${productId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async deleteProduct(productId: string): Promise<void> {
    return this.request<void>(`/api/v1/products/${productId}`, {
      method: 'DELETE',
    });
  }

  async getProductStats(): Promise<ProductStats> {
    return this.request<ProductStats>('/api/v1/products/stats');
  }

  async getProductTypes(): Promise<ProductTypesResponse> {
    return this.request<ProductTypesResponse>('/api/v1/products/types');
  }

  // Product Runs
  async listProductRuns(productId: string): Promise<ProductRun[]> {
    return this.request<ProductRun[]>(`/api/v1/products/${productId}/runs`);
  }

  async createProductRun(productId: string, name?: string): Promise<ProductRun> {
    return this.request<ProductRun>(`/api/v1/products/${productId}/runs`, {
      method: 'POST',
      body: JSON.stringify({ name }),
    });
  }

  async startProductRun(productId: string, runId: string): Promise<ProductRun> {
    return this.request<ProductRun>(`/api/v1/products/${productId}/runs/${runId}/start`, {
      method: 'POST',
    });
  }

  async cancelProductRun(productId: string, runId: string): Promise<ProductRun> {
    return this.request<ProductRun>(`/api/v1/products/${productId}/runs/${runId}/cancel`, {
      method: 'POST',
    });
  }

  // Product Results
  async listProductResults(productId: string): Promise<ProductResult[]> {
    return this.request<ProductResult[]>(`/api/v1/products/${productId}/results`);
  }

  async getProductResult(productId: string, resultId: string): Promise<ProductResult> {
    return this.request<ProductResult>(`/api/v1/products/${productId}/results/${resultId}`);
  }

  // Product Comparison & Analytics
  async compareProducts(productIds: string[], metrics?: string[]): Promise<ComparisonResponse> {
    return this.request<ComparisonResponse>('/api/v1/products/compare', {
      method: 'POST',
      body: JSON.stringify({
        product_ids: productIds,
        metrics: metrics || ['sentiment', 'demographics', 'purchase_likelihood'],
      }),
    });
  }

  async getProductTrends(productId: string): Promise<ProductTrendsResponse> {
    return this.request<ProductTrendsResponse>(`/api/v1/products/${productId}/trends`);
  }

  // ========== Validation ==========

  // Benchmarks
  async listBenchmarks(params?: {
    category?: string;
    region?: string;
    is_public?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<Benchmark[]> {
    const queryParams = new URLSearchParams();
    if (params?.category) queryParams.append('category', params.category);
    if (params?.region) queryParams.append('region', params.region);
    if (params?.is_public !== undefined) queryParams.append('is_public', String(params.is_public));
    if (params?.limit) queryParams.append('limit', String(params.limit));
    if (params?.offset) queryParams.append('offset', String(params.offset));
    const query = queryParams.toString();
    return this.request<Benchmark[]>(`/api/v1/validation/benchmarks${query ? `?${query}` : ''}`);
  }

  async getBenchmark(benchmarkId: string): Promise<Benchmark> {
    return this.request<Benchmark>(`/api/v1/validation/benchmarks/${benchmarkId}`);
  }

  async createBenchmark(data: BenchmarkCreate): Promise<Benchmark> {
    return this.request<Benchmark>('/api/v1/validation/benchmarks', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deleteBenchmark(benchmarkId: string): Promise<void> {
    return this.request<void>(`/api/v1/validation/benchmarks/${benchmarkId}`, {
      method: 'DELETE',
    });
  }

  async seedElectionBenchmarks(): Promise<{ status: string; message: string; benchmarks: Array<{ id: string; name: string }> }> {
    return this.request('/api/v1/validation/benchmarks/seed-elections', {
      method: 'POST',
    });
  }

  async getBenchmarkCategories(): Promise<{ categories: BenchmarkCategory[] }> {
    return this.request('/api/v1/validation/categories');
  }

  // Validation Records
  async listValidations(params?: {
    product_id?: string;
    benchmark_id?: string;
    limit?: number;
    offset?: number;
  }): Promise<ValidationRecord[]> {
    const queryParams = new URLSearchParams();
    if (params?.product_id) queryParams.append('product_id', params.product_id);
    if (params?.benchmark_id) queryParams.append('benchmark_id', params.benchmark_id);
    if (params?.limit) queryParams.append('limit', String(params.limit));
    if (params?.offset) queryParams.append('offset', String(params.offset));
    const query = queryParams.toString();
    return this.request<ValidationRecord[]>(`/api/v1/validation/records${query ? `?${query}` : ''}`);
  }

  async getValidation(validationId: string): Promise<ValidationRecord> {
    return this.request<ValidationRecord>(`/api/v1/validation/records/${validationId}`);
  }

  async validatePrediction(data: ValidationCreate): Promise<ValidationRecord> {
    return this.request<ValidationRecord>('/api/v1/validation/validate', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Accuracy Stats
  async getAccuracyStats(category?: string): Promise<AccuracyStats> {
    const query = category ? `?category=${category}` : '';
    return this.request<AccuracyStats>(`/api/v1/validation/stats${query}`);
  }

  async getGlobalAccuracyStats(category?: string): Promise<AccuracyStats> {
    const query = category ? `?category=${category}` : '';
    return this.request<AccuracyStats>(`/api/v1/validation/stats/global${query}`);
  }

  // ========== AI Content Generation ==========

  async listAITemplates(category?: string): Promise<AITemplateListResponse> {
    const query = category ? `?category=${category}` : '';
    return this.request<AITemplateListResponse>(`/api/v1/ai/templates${query}`);
  }

  async getAITemplate(templateId: string): Promise<AIContentTemplate> {
    return this.request<AIContentTemplate>(`/api/v1/ai/templates/${templateId}`);
  }

  async generateAIContent(data: GenerateAIContentRequest): Promise<GenerateAIContentResponse> {
    return this.request<GenerateAIContentResponse>('/api/v1/ai/generate', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getAICategories(): Promise<{ categories: AICategory[] }> {
    return this.request<{ categories: AICategory[] }>('/api/v1/ai/categories');
  }

  // ========== Focus Group Endpoints ==========

  async listFocusGroupSessions(params?: {
    product_id?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<FocusGroupSession[]> {
    const searchParams = new URLSearchParams();
    if (params?.product_id) searchParams.set('product_id', params.product_id);
    if (params?.status) searchParams.set('status', params.status);
    if (params?.limit) searchParams.set('limit', String(params.limit));
    if (params?.offset) searchParams.set('offset', String(params.offset));

    const query = searchParams.toString();
    return this.request<FocusGroupSession[]>(`/api/v1/focus-groups/sessions${query ? `?${query}` : ''}`);
  }

  async createFocusGroupSession(data: FocusGroupSessionCreate): Promise<FocusGroupSession> {
    return this.request<FocusGroupSession>('/api/v1/focus-groups/sessions', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getFocusGroupSession(sessionId: string): Promise<FocusGroupSession> {
    return this.request<FocusGroupSession>(`/api/v1/focus-groups/sessions/${sessionId}`);
  }

  async updateFocusGroupSession(sessionId: string, data: FocusGroupSessionUpdate): Promise<FocusGroupSession> {
    return this.request<FocusGroupSession>(`/api/v1/focus-groups/sessions/${sessionId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async endFocusGroupSession(sessionId: string): Promise<FocusGroupSession> {
    return this.request<FocusGroupSession>(`/api/v1/focus-groups/sessions/${sessionId}/end`, {
      method: 'POST',
    });
  }

  async interviewAgent(sessionId: string, data: InterviewRequest): Promise<InterviewResponse> {
    return this.request<InterviewResponse>(`/api/v1/focus-groups/sessions/${sessionId}/interview`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  streamInterviewAgent(sessionId: string, data: InterviewRequest): EventSource | null {
    if (typeof window === 'undefined') return null;

    // For streaming, we need to use fetch with event source
    // This is a simplified version - in production you'd want proper SSE handling
    const url = `${this.baseUrl}/api/v1/focus-groups/sessions/${sessionId}/interview/stream`;
    return null; // Will be handled by custom hook
  }

  async groupDiscussion(sessionId: string, data: GroupDiscussionRequest): Promise<GroupDiscussionResponse> {
    return this.request<GroupDiscussionResponse>(`/api/v1/focus-groups/sessions/${sessionId}/discuss`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getFocusGroupMessages(sessionId: string, params?: {
    limit?: number;
    offset?: number;
  }): Promise<FocusGroupMessage[]> {
    const searchParams = new URLSearchParams();
    if (params?.limit) searchParams.set('limit', String(params.limit));
    if (params?.offset) searchParams.set('offset', String(params.offset));

    const query = searchParams.toString();
    return this.request<FocusGroupMessage[]>(`/api/v1/focus-groups/sessions/${sessionId}/messages${query ? `?${query}` : ''}`);
  }

  async getSessionSummary(sessionId: string): Promise<SessionSummaryResponse> {
    return this.request<SessionSummaryResponse>(`/api/v1/focus-groups/sessions/${sessionId}/summary`, {
      method: 'POST',
      body: JSON.stringify({ include_quotes: true, include_themes: true, include_sentiment: true }),
    });
  }

  async getAvailableAgents(productId: string, runId?: string): Promise<AvailableAgent[]> {
    const query = runId ? `?run_id=${runId}` : '';
    return this.request<AvailableAgent[]>(`/api/v1/focus-groups/products/${productId}/available-agents${query}`);
  }

  getStreamInterviewUrl(sessionId: string): string {
    return `${this.baseUrl}/api/v1/focus-groups/sessions/${sessionId}/interview/stream`;
  }

  // ========== Marketplace Endpoints ==========

  async listMarketplaceCategories(includeInactive?: boolean): Promise<MarketplaceCategory[]> {
    const query = includeInactive ? '?include_inactive=true' : '';
    return this.request<MarketplaceCategory[]>(`/api/v1/marketplace/categories${query}`);
  }

  async getMarketplaceCategoryTree(): Promise<MarketplaceCategoryWithChildren[]> {
    return this.request<MarketplaceCategoryWithChildren[]>('/api/v1/marketplace/categories/tree');
  }

  async createMarketplaceCategory(data: MarketplaceCategoryCreate): Promise<MarketplaceCategory> {
    return this.request<MarketplaceCategory>('/api/v1/marketplace/categories', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateMarketplaceCategory(categoryId: string, data: MarketplaceCategoryUpdate): Promise<MarketplaceCategory> {
    return this.request<MarketplaceCategory>(`/api/v1/marketplace/categories/${categoryId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async listMarketplaceTemplates(params?: {
    query?: string;
    category_id?: string;
    category_slug?: string;
    scenario_type?: string;
    tags?: string;
    author_id?: string;
    is_featured?: boolean;
    is_verified?: boolean;
    is_premium?: boolean;
    min_rating?: number;
    min_usage?: number;
    sort_by?: 'popular' | 'newest' | 'rating' | 'usage' | 'name';
    page?: number;
    page_size?: number;
  }): Promise<MarketplaceTemplateListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.query) searchParams.set('query', params.query);
    if (params?.category_id) searchParams.set('category_id', params.category_id);
    if (params?.category_slug) searchParams.set('category_slug', params.category_slug);
    if (params?.scenario_type) searchParams.set('scenario_type', params.scenario_type);
    if (params?.tags) searchParams.set('tags', params.tags);
    if (params?.author_id) searchParams.set('author_id', params.author_id);
    if (params?.is_featured !== undefined) searchParams.set('is_featured', String(params.is_featured));
    if (params?.is_verified !== undefined) searchParams.set('is_verified', String(params.is_verified));
    if (params?.is_premium !== undefined) searchParams.set('is_premium', String(params.is_premium));
    if (params?.min_rating) searchParams.set('min_rating', String(params.min_rating));
    if (params?.min_usage) searchParams.set('min_usage', String(params.min_usage));
    if (params?.sort_by) searchParams.set('sort_by', params.sort_by);
    if (params?.page) searchParams.set('page', String(params.page));
    if (params?.page_size) searchParams.set('page_size', String(params.page_size));

    const query = searchParams.toString();
    return this.request<MarketplaceTemplateListResponse>(`/api/v1/marketplace/templates${query ? `?${query}` : ''}`);
  }

  async getFeaturedTemplates(): Promise<FeaturedTemplatesResponse> {
    return this.request<FeaturedTemplatesResponse>('/api/v1/marketplace/templates/featured');
  }

  async getMarketplaceTemplate(slug: string): Promise<MarketplaceTemplateDetail> {
    return this.request<MarketplaceTemplateDetail>(`/api/v1/marketplace/templates/${slug}`);
  }

  async createMarketplaceTemplate(data: MarketplaceTemplateCreate): Promise<MarketplaceTemplateDetail> {
    return this.request<MarketplaceTemplateDetail>('/api/v1/marketplace/templates', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async createMarketplaceTemplateFromScenario(data: MarketplaceTemplateFromScenario): Promise<MarketplaceTemplateDetail> {
    return this.request<MarketplaceTemplateDetail>('/api/v1/marketplace/templates/from-scenario', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateMarketplaceTemplate(templateId: string, data: MarketplaceTemplateUpdate): Promise<MarketplaceTemplateDetail> {
    return this.request<MarketplaceTemplateDetail>(`/api/v1/marketplace/templates/${templateId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteMarketplaceTemplate(templateId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/api/v1/marketplace/templates/${templateId}`, {
      method: 'DELETE',
    });
  }

  async listMyTemplates(params?: {
    status?: string;
    page?: number;
    page_size?: number;
  }): Promise<MarketplaceTemplateListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.set('status_filter', params.status);
    if (params?.page) searchParams.set('page', String(params.page));
    if (params?.page_size) searchParams.set('page_size', String(params.page_size));

    const query = searchParams.toString();
    return this.request<MarketplaceTemplateListResponse>(`/api/v1/marketplace/my-templates${query ? `?${query}` : ''}`);
  }

  async useMarketplaceTemplate(templateId: string, data: UseTemplateRequest): Promise<UseTemplateResponse> {
    return this.request<UseTemplateResponse>(`/api/v1/marketplace/templates/${templateId}/use`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async toggleTemplateLike(templateId: string): Promise<{ liked: boolean; like_count: number }> {
    return this.request<{ liked: boolean; like_count: number }>(`/api/v1/marketplace/templates/${templateId}/like`, {
      method: 'POST',
    });
  }

  async listTemplateReviews(templateId: string, params?: {
    page?: number;
    page_size?: number;
  }): Promise<TemplateReviewListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set('page', String(params.page));
    if (params?.page_size) searchParams.set('page_size', String(params.page_size));

    const query = searchParams.toString();
    return this.request<TemplateReviewListResponse>(`/api/v1/marketplace/templates/${templateId}/reviews${query ? `?${query}` : ''}`);
  }

  async createTemplateReview(templateId: string, data: TemplateReviewCreate): Promise<TemplateReview> {
    return this.request<TemplateReview>(`/api/v1/marketplace/templates/${templateId}/reviews`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateTemplateReview(templateId: string, data: TemplateReviewUpdate): Promise<TemplateReview> {
    return this.request<TemplateReview>(`/api/v1/marketplace/templates/${templateId}/reviews`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteTemplateReview(templateId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/api/v1/marketplace/templates/${templateId}/reviews`, {
      method: 'DELETE',
    });
  }

  async getMarketplaceStats(): Promise<MarketplaceStats> {
    return this.request<MarketplaceStats>('/api/v1/marketplace/stats');
  }

  async getAuthorStats(authorId: string): Promise<AuthorStats> {
    return this.request<AuthorStats>(`/api/v1/marketplace/authors/${authorId}/stats`);
  }

  // ========== Vi World Endpoints ==========

  async getWorldByTemplate(templateId: string): Promise<WorldState> {
    return this.request<WorldState>(`/api/v1/world/by-template/${templateId}`);
  }

  async getWorld(worldId: string): Promise<WorldState> {
    return this.request<WorldState>(`/api/v1/world/${worldId}`);
  }

  async autoCreateWorld(templateId: string): Promise<WorldState> {
    return this.request<WorldState>(`/api/v1/world/auto-create/${templateId}`, {
      method: 'POST',
    });
  }

  async controlWorld(worldId: string, action: 'start' | 'pause' | 'resume' | 'stop' | 'reset', simulationSpeed?: number): Promise<WorldState> {
    return this.request<WorldState>(`/api/v1/world/${worldId}/control`, {
      method: 'POST',
      body: JSON.stringify({ action, simulation_speed: simulationSpeed }),
    });
  }

  async getWorldStats(worldId: string): Promise<WorldStats> {
    return this.request<WorldStats>(`/api/v1/world/${worldId}/stats`);
  }

  async getWorldChatHistory(worldId: string, page?: number, pageSize?: number): Promise<ChatHistoryResponse> {
    const params = new URLSearchParams();
    if (page) params.set('page', String(page));
    if (pageSize) params.set('page_size', String(pageSize));
    const query = params.toString();
    return this.request<ChatHistoryResponse>(`/api/v1/world/${worldId}/chat${query ? `?${query}` : ''}`);
  }

  async updateWorldNpcStates(worldId: string, npcStates: Record<string, NPCState>): Promise<WorldState> {
    return this.request<WorldState>(`/api/v1/world/${worldId}/npcs`, {
      method: 'PUT',
      body: JSON.stringify({ npc_states: npcStates }),
    });
  }

  // ========== Prediction Endpoints ==========

  async listPredictions(params?: {
    status?: string;
    scenario_type?: string;
    skip?: number;
    limit?: number;
  }): Promise<PredictionListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.set('status', params.status);
    if (params?.scenario_type) searchParams.set('scenario_type', params.scenario_type);
    if (params?.skip) searchParams.set('skip', String(params.skip));
    if (params?.limit) searchParams.set('limit', String(params.limit));

    const query = searchParams.toString();
    // Backend returns array directly, transform to expected format
    const predictions = await this.request<PredictionResponse[]>(`/api/v1/predictions${query ? `?${query}` : ''}`);
    return {
      predictions,
      total: predictions.length,
      skip: params?.skip || 0,
      limit: params?.limit || predictions.length,
    };
  }

  async createPrediction(data: PredictionCreate): Promise<PredictionResponse> {
    return this.request<PredictionResponse>('/api/v1/predictions', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getPrediction(predictionId: string): Promise<PredictionResponse> {
    return this.request<PredictionResponse>(`/api/v1/predictions/${predictionId}`);
  }

  async getPredictionResults(predictionId: string): Promise<PredictionResults> {
    return this.request<PredictionResults>(`/api/v1/predictions/${predictionId}/results`);
  }

  async cancelPrediction(predictionId: string): Promise<{ message: string; prediction_id: string }> {
    return this.request<{ message: string; prediction_id: string }>(`/api/v1/predictions/${predictionId}/cancel`, {
      method: 'POST',
    });
  }

  // SSE Stream for prediction progress
  streamPrediction(predictionId: string): EventSource {
    const url = `${this.baseUrl}/api/v1/predictions/${predictionId}/stream`;
    return new EventSource(url);
  }

  // Calibration endpoints
  async startCalibration(data: CalibrationRequest): Promise<CalibrationStatus> {
    return this.request<CalibrationStatus>('/api/v1/predictions/calibrate', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getCalibrationStatus(calibrationId: string): Promise<CalibrationStatus> {
    return this.request<CalibrationStatus>(`/api/v1/predictions/calibrate/${calibrationId}`);
  }

  // MARL Training
  async startMarlTraining(data: MarlTrainingRequest): Promise<{ message: string; training_id: string }> {
    return this.request<{ message: string; training_id: string }>('/api/v1/predictions/train', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Prediction Analytics
  async getPredictionAnalyticsOverview(): Promise<PredictionAnalyticsOverview> {
    return this.request<PredictionAnalyticsOverview>('/api/v1/predictions/analytics/overview');
  }

  async getAccuracyAnalytics(): Promise<AccuracyAnalytics> {
    return this.request<AccuracyAnalytics>('/api/v1/predictions/analytics/accuracy');
  }

  // ========== Ask / Event Compiler Endpoints (project.md §11 Phase 4) ==========

  async compileAskPrompt(data: AskCompileRequest): Promise<AskCompilationResult> {
    return this.request<AskCompilationResult>('/api/v1/ask/compile', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async expandAskCluster(data: AskExpandClusterRequest): Promise<AskScenarioCluster> {
    return this.request<AskScenarioCluster>('/api/v1/ask/expand', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async listAskCompilations(params?: {
    project_id?: string;
    skip?: number;
    limit?: number;
  }): Promise<AskCompilationListItem[]> {
    const searchParams = new URLSearchParams();
    if (params?.project_id) searchParams.set('project_id', params.project_id);
    if (params?.skip) searchParams.set('skip', String(params.skip));
    if (params?.limit) searchParams.set('limit', String(params.limit));

    const query = searchParams.toString();
    return this.request<AskCompilationListItem[]>(`/api/v1/ask/compilations${query ? `?${query}` : ''}`);
  }

  async getAskCompilation(compilationId: string): Promise<AskCompilationResult> {
    return this.request<AskCompilationResult>(`/api/v1/ask/compilations/${compilationId}`);
  }

  async deleteAskCompilation(compilationId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/api/v1/ask/compilations/${compilationId}`, {
      method: 'DELETE',
    });
  }

  async executeAskScenario(data: {
    compilation_id: string;
    scenario_id: string;
    node_id?: string;
    auto_fork?: boolean;
    run_config_overrides?: Partial<CreateRunConfigInput>;
  }): Promise<{ node_id: string; run_id?: string }> {
    return this.request<{ node_id: string; run_id?: string }>('/api/v1/ask/execute', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // ========== Target Mode Endpoints (project.md §11 Phase 5) ==========

  // Target Personas
  async createTargetPersona(data: TargetPersonaCreate): Promise<TargetPersona> {
    return this.request<TargetPersona>('/api/v1/target/personas', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getTargetPersona(targetId: string): Promise<TargetPersona> {
    return this.request<TargetPersona>(`/api/v1/target/personas/${targetId}`);
  }

  async listTargetPersonas(params?: {
    project_id?: string;
    domain?: string;
    skip?: number;
    limit?: number;
  }): Promise<TargetPersona[]> {
    const queryParams = new URLSearchParams();
    if (params?.project_id) queryParams.set('project_id', params.project_id);
    if (params?.domain) queryParams.set('domain', params.domain);
    if (params?.skip !== undefined) queryParams.set('skip', params.skip.toString());
    if (params?.limit !== undefined) queryParams.set('limit', params.limit.toString());
    const query = queryParams.toString();
    return this.request<TargetPersona[]>(`/api/v1/target/personas${query ? `?${query}` : ''}`);
  }

  async deleteTargetPersona(targetId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/api/v1/target/personas/${targetId}`, {
      method: 'DELETE',
    });
  }

  // Path Planning
  async runTargetPlanner(data: TargetPlanRequest): Promise<PlanResult> {
    return this.request<PlanResult>('/api/v1/target/plans', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getTargetPlan(planId: string): Promise<PlanResult> {
    return this.request<PlanResult>(`/api/v1/target/plans/${planId}`);
  }

  async listTargetPlans(params?: {
    project_id?: string;
    target_id?: string;
    status?: PlanStatus;
    skip?: number;
    limit?: number;
  }): Promise<TargetPlanListItem[]> {
    const queryParams = new URLSearchParams();
    if (params?.project_id) queryParams.set('project_id', params.project_id);
    if (params?.target_id) queryParams.set('target_id', params.target_id);
    if (params?.status) queryParams.set('status', params.status);
    if (params?.skip !== undefined) queryParams.set('skip', params.skip.toString());
    if (params?.limit !== undefined) queryParams.set('limit', params.limit.toString());
    const query = queryParams.toString();
    return this.request<TargetPlanListItem[]>(`/api/v1/target/plans${query ? `?${query}` : ''}`);
  }

  async getTargetPlanClusters(planId: string): Promise<PathCluster[]> {
    return this.request<PathCluster[]>(`/api/v1/target/plans/${planId}/clusters`);
  }

  async expandTargetCluster(data: ExpandClusterRequest): Promise<PathCluster> {
    return this.request<PathCluster>(`/api/v1/target/plans/${data.plan_id}/expand-cluster`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getTargetPlanPaths(planId: string, params?: {
    cluster_id?: string;
    status?: PathStatus;
    limit?: number;
  }): Promise<TargetPath[]> {
    const queryParams = new URLSearchParams();
    if (params?.cluster_id) queryParams.set('cluster_id', params.cluster_id);
    if (params?.status) queryParams.set('status', params.status);
    if (params?.limit !== undefined) queryParams.set('limit', params.limit.toString());
    const query = queryParams.toString();
    return this.request<TargetPath[]>(`/api/v1/target/plans/${planId}/paths${query ? `?${query}` : ''}`);
  }

  async branchPathToNode(data: BranchToNodeRequest): Promise<{ node_id: string; run_id?: string }> {
    return this.request<{ node_id: string; run_id?: string }>(`/api/v1/target/plans/${data.plan_id}/branch`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Action Catalogs
  async listActionCatalogs(params?: {
    domain?: string;
  }): Promise<ActionCatalogListItem[]> {
    const queryParams = new URLSearchParams();
    if (params?.domain) queryParams.set('domain', params.domain);
    const query = queryParams.toString();
    return this.request<ActionCatalogListItem[]>(`/api/v1/target/action-catalogs${query ? `?${query}` : ''}`);
  }

  async getActionCatalog(catalogId: string): Promise<ActionCatalog> {
    return this.request<ActionCatalog>(`/api/v1/target/action-catalogs/${catalogId}`);
  }

  // =============================================================================
  // Hybrid Mode Methods (project.md §11 Phase 6)
  // =============================================================================

  async runHybridSimulation(data: HybridRunRequest): Promise<HybridRunResult> {
    return this.request<HybridRunResult>('/api/v1/hybrid/runs', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getHybridRun(runId: string): Promise<HybridRunResult> {
    return this.request<HybridRunResult>(`/api/v1/hybrid/runs/${runId}`);
  }

  async listHybridRuns(params?: {
    project_id?: string;
    status?: HybridRunStatus;
    limit?: number;
    offset?: number;
  }): Promise<HybridRunListItem[]> {
    const queryParams = new URLSearchParams();
    if (params?.project_id) queryParams.set('project_id', params.project_id);
    if (params?.status) queryParams.set('status', params.status);
    if (params?.limit) queryParams.set('limit', params.limit.toString());
    if (params?.offset) queryParams.set('offset', params.offset.toString());
    const query = queryParams.toString();
    return this.request<HybridRunListItem[]>(`/api/v1/hybrid/runs${query ? `?${query}` : ''}`);
  }

  async getHybridRunProgress(runId: string): Promise<HybridRunProgress> {
    return this.request<HybridRunProgress>(`/api/v1/hybrid/runs/${runId}/progress`);
  }

  async cancelHybridRun(runId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/api/v1/hybrid/runs/${runId}/cancel`, {
      method: 'POST',
    });
  }

  async branchHybridToNode(
    runId: string,
    data: { parent_node_id: string; label?: string | null }
  ): Promise<{ node_id: string }> {
    return this.request<{ node_id: string }>(`/api/v1/hybrid/runs/${runId}/branch`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getHybridCouplingEffects(
    runId: string,
    params?: {
      tick_start?: number;
      tick_end?: number;
      source_type?: 'actor' | 'society';
    }
  ): Promise<HybridCouplingEffect[]> {
    const queryParams = new URLSearchParams();
    if (params?.tick_start !== undefined) queryParams.set('tick_start', params.tick_start.toString());
    if (params?.tick_end !== undefined) queryParams.set('tick_end', params.tick_end.toString());
    if (params?.source_type) queryParams.set('source_type', params.source_type);
    const query = queryParams.toString();
    return this.request<HybridCouplingEffect[]>(`/api/v1/hybrid/runs/${runId}/coupling-effects${query ? `?${query}` : ''}`);
  }

  // =============================================================================
  // 2D Replay Methods (project.md §11 Phase 8) - READ-ONLY (C3 Compliant)
  // =============================================================================

  async loadReplay(request: LoadReplayRequest): Promise<ReplayTimeline> {
    return this.request<ReplayTimeline>('/api/v1/replay/load', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async getReplayStateAtTick(tick: number, request: LoadReplayRequest): Promise<ReplayWorldState> {
    return this.request<ReplayWorldState>(`/api/v1/replay/state/${tick}`, {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async getReplayChunk(
    request: LoadReplayRequest,
    params?: { start_tick?: number; end_tick?: number; include_states?: boolean }
  ): Promise<ReplayChunk> {
    const searchParams = new URLSearchParams();
    if (params?.start_tick !== undefined) searchParams.set('start_tick', String(params.start_tick));
    if (params?.end_tick !== undefined) searchParams.set('end_tick', String(params.end_tick));
    if (params?.include_states !== undefined) searchParams.set('include_states', String(params.include_states));
    const query = searchParams.toString();
    return this.request<ReplayChunk>(`/api/v1/replay/chunk${query ? `?${query}` : ''}`, {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async getReplayAgentHistory(
    agentId: string,
    request: LoadReplayRequest,
    params?: { tick_start?: number; tick_end?: number }
  ): Promise<ReplayAgentHistory> {
    const searchParams = new URLSearchParams();
    if (params?.tick_start !== undefined) searchParams.set('tick_start', String(params.tick_start));
    if (params?.tick_end !== undefined) searchParams.set('tick_end', String(params.tick_end));
    const query = searchParams.toString();
    return this.request<ReplayAgentHistory>(
      `/api/v1/replay/agent/${agentId}/history${query ? `?${query}` : ''}`,
      {
        method: 'POST',
        body: JSON.stringify(request),
      }
    );
  }

  async getReplayEventsAtTick(tick: number, request: LoadReplayRequest): Promise<ReplayTickEvents> {
    return this.request<ReplayTickEvents>(`/api/v1/replay/events/${tick}`, {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async seekReplay(
    tick: number,
    request: LoadReplayRequest
  ): Promise<{ tick: number; world_state: ReplayWorldState }> {
    return this.request<{ tick: number; world_state: ReplayWorldState }>(`/api/v1/replay/seek/${tick}`, {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  // =============================================================================
  // Export Methods (Interaction_design.md §5.19)
  // =============================================================================

  async createExport(data: ExportRequest): Promise<ExportJob> {
    return this.request<ExportJob>('/api/v1/exports', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getExport(exportId: string): Promise<ExportJob> {
    return this.request<ExportJob>(`/api/v1/exports/${exportId}`);
  }

  async listExports(params?: {
    project_id?: string;
    export_type?: ExportType;
    status?: ExportStatus;
    limit?: number;
    offset?: number;
  }): Promise<ExportListItem[]> {
    const searchParams = new URLSearchParams();
    if (params?.project_id) searchParams.set('project_id', params.project_id);
    if (params?.export_type) searchParams.set('export_type', params.export_type);
    if (params?.status) searchParams.set('status', params.status);
    if (params?.limit) searchParams.set('limit', String(params.limit));
    if (params?.offset) searchParams.set('offset', String(params.offset));
    const query = searchParams.toString();
    return this.request<ExportListItem[]>(`/api/v1/exports${query ? `?${query}` : ''}`);
  }

  async deleteExport(exportId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/api/v1/exports/${exportId}`, {
      method: 'DELETE',
    });
  }

  async getExportDownloadUrl(exportId: string): Promise<ExportDownloadResponse> {
    return this.request<ExportDownloadResponse>(`/api/v1/exports/${exportId}/download`);
  }

  async getExportShareUrl(exportId: string, privacy?: ExportPrivacy): Promise<ExportShareResponse> {
    const query = privacy ? `?privacy=${privacy}` : '';
    return this.request<ExportShareResponse>(`/api/v1/exports/${exportId}/share${query}`, {
      method: 'POST',
    });
  }

  // =============================================================================
  // LLM Admin Methods (GAPS.md GAP-P0-001)
  // =============================================================================

  async listLLMProfiles(params?: {
    tenant_id?: string;
    is_active?: boolean;
    profile_key?: string;
  }): Promise<LLMProfileListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.tenant_id) searchParams.set('tenant_id', params.tenant_id);
    if (params?.is_active !== undefined) searchParams.set('is_active', String(params.is_active));
    if (params?.profile_key) searchParams.set('profile_key', params.profile_key);
    const query = searchParams.toString();
    return this.request<LLMProfileListResponse>(`/api/v1/admin/llm/profiles${query ? `?${query}` : ''}`);
  }

  async getLLMProfile(profileId: string): Promise<LLMProfile> {
    return this.request<LLMProfile>(`/api/v1/admin/llm/profiles/${profileId}`);
  }

  async createLLMProfile(data: LLMProfileCreate): Promise<LLMProfile> {
    return this.request<LLMProfile>('/api/v1/admin/llm/profiles', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateLLMProfile(profileId: string, data: LLMProfileUpdate): Promise<LLMProfile> {
    return this.request<LLMProfile>(`/api/v1/admin/llm/profiles/${profileId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async deleteLLMProfile(profileId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/api/v1/admin/llm/profiles/${profileId}`, {
      method: 'DELETE',
    });
  }

  async listLLMCalls(params?: {
    tenant_id?: string;
    profile_key?: string;
    project_id?: string;
    run_id?: string;
    status?: string;
    page?: number;
    page_size?: number;
    start_date?: string;
    end_date?: string;
  }): Promise<LLMCallListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.tenant_id) searchParams.set('tenant_id', params.tenant_id);
    if (params?.profile_key) searchParams.set('profile_key', params.profile_key);
    if (params?.project_id) searchParams.set('project_id', params.project_id);
    if (params?.run_id) searchParams.set('run_id', params.run_id);
    if (params?.status) searchParams.set('status', params.status);
    if (params?.page) searchParams.set('page', String(params.page));
    if (params?.page_size) searchParams.set('page_size', String(params.page_size));
    if (params?.start_date) searchParams.set('start_date', params.start_date);
    if (params?.end_date) searchParams.set('end_date', params.end_date);
    const query = searchParams.toString();
    return this.request<LLMCallListResponse>(`/api/v1/admin/llm/calls${query ? `?${query}` : ''}`);
  }

  async getLLMCostReport(params?: {
    tenant_id?: string;
    start_date?: string;
    end_date?: string;
  }): Promise<LLMCostReport> {
    const searchParams = new URLSearchParams();
    if (params?.tenant_id) searchParams.set('tenant_id', params.tenant_id);
    if (params?.start_date) searchParams.set('start_date', params.start_date);
    if (params?.end_date) searchParams.set('end_date', params.end_date);
    const query = searchParams.toString();
    return this.request<LLMCostReport>(`/api/v1/admin/llm/costs${query ? `?${query}` : ''}`);
  }

  async getAvailableLLMModels(): Promise<AvailableLLMModelsResponse> {
    return this.request<AvailableLLMModelsResponse>('/api/v1/admin/llm/models');
  }

  async getStandardProfileKeys(): Promise<ProfileKeysResponse> {
    return this.request<ProfileKeysResponse>('/api/v1/admin/llm/profile-keys');
  }

  async testLLMProfile(profileId: string, testPrompt?: string): Promise<LLMTestResponse> {
    return this.request<LLMTestResponse>(`/api/v1/admin/llm/profiles/${profileId}/test`, {
      method: 'POST',
      body: JSON.stringify({ test_prompt: testPrompt }),
    });
  }

  // =============================================================================
  // Audit Log Admin Methods (GAPS.md GAP-P0-006)
  // =============================================================================

  async listAuditLogs(params?: {
    action?: string;
    resource_type?: string;
    resource_id?: string;
    user_id?: string;
    tenant_id?: string;
    start_date?: string;
    end_date?: string;
    ip_address?: string;
    page?: number;
    page_size?: number;
    sort_by?: string;
    sort_order?: string;
  }): Promise<AuditLogListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.action) searchParams.set('action', params.action);
    if (params?.resource_type) searchParams.set('resource_type', params.resource_type);
    if (params?.resource_id) searchParams.set('resource_id', params.resource_id);
    if (params?.user_id) searchParams.set('user_id', params.user_id);
    if (params?.tenant_id) searchParams.set('tenant_id', params.tenant_id);
    if (params?.start_date) searchParams.set('start_date', params.start_date);
    if (params?.end_date) searchParams.set('end_date', params.end_date);
    if (params?.ip_address) searchParams.set('ip_address', params.ip_address);
    if (params?.page) searchParams.set('page', String(params.page));
    if (params?.page_size) searchParams.set('page_size', String(params.page_size));
    if (params?.sort_by) searchParams.set('sort_by', params.sort_by);
    if (params?.sort_order) searchParams.set('sort_order', params.sort_order);
    const query = searchParams.toString();
    return this.request<AuditLogListResponse>(`/api/v1/admin/audit-logs${query ? `?${query}` : ''}`);
  }

  async getAuditLog(logId: string): Promise<AuditLogEntry> {
    return this.request<AuditLogEntry>(`/api/v1/admin/audit-logs/${logId}`);
  }

  async getAuditStats(params?: {
    tenant_id?: string;
    days?: number;
  }): Promise<AuditLogStatsResponse> {
    const searchParams = new URLSearchParams();
    if (params?.tenant_id) searchParams.set('tenant_id', params.tenant_id);
    if (params?.days) searchParams.set('days', String(params.days));
    const query = searchParams.toString();
    return this.request<AuditLogStatsResponse>(`/api/v1/admin/audit-logs/stats${query ? `?${query}` : ''}`);
  }

  async exportAuditLogs(params?: {
    format?: 'json' | 'csv';
    action?: string;
    resource_type?: string;
    user_id?: string;
    tenant_id?: string;
    start_date?: string;
    end_date?: string;
    limit?: number;
  }): Promise<AuditLogExportResponse> {
    const searchParams = new URLSearchParams();
    if (params?.format) searchParams.set('format', params.format);
    if (params?.action) searchParams.set('action', params.action);
    if (params?.resource_type) searchParams.set('resource_type', params.resource_type);
    if (params?.user_id) searchParams.set('user_id', params.user_id);
    if (params?.tenant_id) searchParams.set('tenant_id', params.tenant_id);
    if (params?.start_date) searchParams.set('start_date', params.start_date);
    if (params?.end_date) searchParams.set('end_date', params.end_date);
    if (params?.limit) searchParams.set('limit', String(params.limit));
    const query = searchParams.toString();
    return this.request<AuditLogExportResponse>(`/api/v1/admin/audit-logs/export${query ? `?${query}` : ''}`);
  }

  async listAuditActions(): Promise<string[]> {
    return this.request<string[]>('/api/v1/admin/audit-logs/actions');
  }

  async listAuditResourceTypes(): Promise<string[]> {
    return this.request<string[]>('/api/v1/admin/audit-logs/resource-types');
  }
}

// Data Source Types
export interface DataSource {
  id: string;
  name: string;
  description: string | null;
  source_type: string;
  source_url: string | null;
  api_endpoint: string | null;
  coverage_region: string | null;
  coverage_year: number | null;
  status: string;
  is_enabled: boolean;
  accuracy_score: number | null;
  validation_status: string | null;
  last_synced_at: string | null;
  created_at: string;
  updated_at: string;
  config: Record<string, unknown>;
}

export interface DataSourceCreate {
  name: string;
  description?: string;
  source_type: string;
  source_url?: string;
  api_endpoint?: string;
  coverage_region?: string;
  coverage_year?: number;
  config?: Record<string, unknown>;
}

export interface DataSourceUpdate {
  name?: string;
  description?: string;
  source_url?: string;
  api_endpoint?: string;
  coverage_region?: string;
  coverage_year?: number;
  config?: Record<string, unknown>;
  is_enabled?: boolean;
}

export interface DemographicDistribution {
  category: string;
  distribution: Record<string, number>;
  total_population: number;
  source_year: number;
  source_survey: string;
  margin_of_error: number | null;
}

export interface CensusProfile {
  region: {
    state: string | null;
    county: string | null;
  };
  demographics: Record<string, {
    distribution: Record<string, number>;
    total_population: number;
    source_year: number;
    source_survey: string;
  }>;
  source: string;
  year: number;
}

export interface CensusSyncResult {
  message: string;
  records_created: number;
  data_source_id: string;
  region: {
    state: string | null;
    county: string | null;
  };
  year: number;
}

export interface RegionalProfile {
  id: string;
  data_source_id: string;
  region_code: string;
  region_name: string;
  region_type: string;
  demographics: Record<string, unknown>;
  psychographics: Record<string, unknown> | null;
  data_completeness: number;
  confidence_score: number;
  created_at: string;
}

export interface RegionalProfileBuildResult {
  message: string;
  profile_id: string;
  region_code: string;
  region_name: string;
  region_type: string;
  data_completeness: number;
  confidence_score: number;
}

// ========== Persona Types ==========

export interface PersonaTemplate {
  id: string;
  name: string;
  description: string | null;
  region: string;
  country: string | null;
  sub_region: string | null;
  industry: string | null;
  topic: string | null;
  keywords: string[] | null;
  source_type: string;
  data_completeness: number;
  confidence_score: number;
  is_active: boolean;
  is_public: boolean;
  persona_count: number;
  created_at: string;
  updated_at: string;
}

export interface PersonaTemplateCreate {
  name: string;
  description?: string;
  region: string;
  country?: string;
  sub_region?: string;
  industry?: string;
  topic?: string;
  keywords?: string[];
  source_type?: string;
}

export interface PersonaRecord {
  id: string;
  demographics: Record<string, unknown>;
  professional: Record<string, unknown>;
  psychographics: Record<string, unknown>;
  behavioral: Record<string, unknown>;
  interests: Record<string, unknown>;
  topic_knowledge: Record<string, unknown> | null;
  cultural_context: Record<string, unknown> | null;
  source_type: string;
  confidence_score: number;
  full_prompt: string | null;
  created_at: string;
}

export interface GeneratePersonasRequest {
  template_id?: string;
  region: string;
  country?: string;
  sub_region?: string;
  topic?: string;
  industry?: string;
  keywords?: string[];
  count?: number;
  include_psychographics?: boolean;
  include_behavioral?: boolean;
  include_cultural?: boolean;
  include_topic_knowledge?: boolean;
}

export interface GeneratePersonasResponse {
  count: number;
  template_id: string | null;
  sample_personas: Record<string, unknown>[];
  generation_config: Record<string, unknown>;
}

export interface FileAnalysisColumn {
  name: string;
  sample_values: string[];
  data_type: string;
  unique_count: number;
  null_count: number;
  suggested_mapping: string | null;
}

export interface FileAnalysisResponse {
  file_name: string;
  row_count: number;
  column_count: number;
  columns: FileAnalysisColumn[];
  suggested_mappings: Record<string, string>;
}

export interface UploadResult {
  upload_id: string;
  status: string;
  records_total: number;
  records_processed: number;
  records_failed: number;
  errors: Record<string, unknown>[];
  sample_records: Record<string, unknown>[];
}

export interface AIResearchRequest {
  topic: string;
  region: string;
  country?: string;
  industry?: string;
  keywords?: string[];
  research_depth?: 'quick' | 'standard' | 'comprehensive';
  target_persona_count?: number;
}

export interface AIResearchJob {
  id: string;
  topic: string;
  region: string;
  country: string | null;
  industry: string | null;
  status: string;
  progress: number;
  insights: Record<string, unknown> | null;
  personas_generated: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface RegionInfo {
  code: string;
  name: string;
  countries: string[];
  data_source: string;
}

// ========== Product Types ==========

export interface TargetMarket {
  regions: string[];
  countries: string[];
  demographics: Record<string, unknown>;
  sample_size: number;
}

export type ProductType = 'predict' | 'insight' | 'simulate' | 'oracle' | 'pulse' | 'prism';

export interface Product {
  id: string;
  project_id: string;
  name: string;
  description: string | null;
  product_type: ProductType;
  sub_type: string | null;
  target_market: TargetMarket;
  persona_template_id: string | null;
  persona_count: number;
  persona_source: string;
  configuration: Record<string, unknown>;
  stimulus_materials: Record<string, unknown> | null;
  methodology: Record<string, unknown> | null;
  confidence_target: number;
  status: string;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface ProductCreate {
  project_id: string;
  name: string;
  description?: string;
  product_type: ProductType;
  sub_type?: string;
  target_market: TargetMarket;
  persona_template_id?: string;
  persona_count?: number;
  persona_source?: string;
  configuration?: Record<string, unknown>;
  stimulus_materials?: Record<string, unknown>;
  methodology?: Record<string, unknown>;
  confidence_target?: number;
}

export interface ProductUpdate {
  name?: string;
  description?: string;
  target_market?: TargetMarket;
  persona_template_id?: string;
  persona_count?: number;
  configuration?: Record<string, unknown>;
  stimulus_materials?: Record<string, unknown>;
  methodology?: Record<string, unknown>;
  confidence_target?: number;
}

export interface ProductRun {
  id: string;
  product_id: string;
  run_number: number;
  name: string | null;
  status: string;
  progress: number;
  agents_total: number;
  agents_completed: number;
  agents_failed: number;
  tokens_used: number;
  estimated_cost: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface ProductResult {
  id: string;
  product_id: string;
  run_id: string | null;
  result_type: string;
  predictions: Record<string, unknown> | null;
  insights: Record<string, unknown> | null;
  simulation_outcomes: Record<string, unknown> | null;
  statistical_analysis: Record<string, unknown> | null;
  segment_analysis: Record<string, unknown> | null;
  // Advanced Model Analysis Fields
  oracle_analysis: Record<string, unknown> | null;  // ORACLE Market Intelligence
  pulse_analysis: Record<string, unknown> | null;   // PULSE Political Simulation
  prism_analysis: Record<string, unknown> | null;   // PRISM Public Sector Analytics
  confidence_score: number;
  executive_summary: string | null;
  key_takeaways: string[] | null;
  recommendations: string[] | null;
  visualizations: Record<string, unknown> | null;
  created_at: string;
}

export interface ProductStats {
  total_products: number;
  by_type: Record<string, number>;
  by_status: Record<string, number>;
  total_runs: number;
  active_runs: number;
  completed_runs: number;
  total_agents: number;
  avg_confidence: number;
}

export interface ProductSubType {
  value: string;
  name: string;
}

export interface ProductTypeInfo {
  type: string;
  name: string;
  description: string;
  sub_types: ProductSubType[];
}

export interface ProductTypesResponse {
  product_types: ProductTypeInfo[];
}

// Comparison Types
export interface ComparisonResultItem {
  product_id: string;
  product_name: string;
  result_id: string | null;
  data: Record<string, unknown>;
}

export interface ComparisonResponse {
  products: ComparisonResultItem[];
  comparison_metrics: Record<string, unknown[]>;
  statistical_significance: Record<string, {
    is_significant: boolean;
    p_value: number;
    description: string;
  }>;
}

export interface TrendDataPoint {
  name: string;
  value?: number;
  date?: string;
  positive_ratio?: number;
  likely_ratio?: number;
  distribution?: Record<string, number>;
}

export interface ProductTrendsResponse {
  product_id: string;
  product_name: string;
  total_runs: number;
  trends: {
    confidence_scores: TrendDataPoint[];
    sentiment_trends: TrendDataPoint[];
    purchase_likelihood_trends: TrendDataPoint[];
    run_dates: TrendDataPoint[];
  };
}

// Validation Types
export interface Benchmark {
  id: string;
  name: string;
  description: string | null;
  category: string;
  event_date: string | null;
  region: string;
  country: string | null;
  actual_outcome: Record<string, unknown>;
  source: string;
  source_url: string | null;
  verification_status: string;
  is_public: boolean;
  usage_count: number;
  created_at: string;
}

export interface BenchmarkCreate {
  name: string;
  description?: string;
  category: string;
  event_date?: string;
  region: string;
  country?: string;
  actual_outcome: Record<string, unknown>;
  source: string;
  source_url?: string;
  is_public?: boolean;
}

export interface ValidationRecord {
  id: string;
  product_id: string;
  benchmark_id: string;
  predicted_outcome: Record<string, unknown>;
  actual_outcome: Record<string, unknown>;
  accuracy_score: number;
  deviation: number;
  within_confidence_interval: boolean;
  analysis: Record<string, unknown> | null;
  validated_at: string;
}

export interface ValidationCreate {
  product_id: string;
  benchmark_id: string;
}

export interface AccuracyStats {
  total_validations: number;
  average_accuracy: number;
  median_accuracy: number;
  accuracy_by_category: Record<string, number>;
  accuracy_trend: Array<{ date: string; accuracy: number }>;
  within_ci_rate: number;
  best_performing_category: string | null;
  areas_for_improvement: string[];
}

export interface BenchmarkCategory {
  id: string;
  name: string;
  description: string;
}

// AI Content Generation Types
export interface AIContentTemplate {
  id: string;
  name: string;
  category: string;
  description: string;
  context: string;
  questions: Array<{
    type: string;
    text: string;
    options?: string[];
  }>;
}

export interface AITemplateListResponse {
  templates: AIContentTemplate[];
  total: number;
}

export interface GenerateAIContentRequest {
  title: string;
  product_type?: string;
  sub_type?: string;
  target_market?: Record<string, unknown>;
}

export interface GeneratedContent {
  context: string | null;
  description: string | null;
  questions: Array<{
    type: string;
    text: string;
    options?: string[];
  }> | null;
  recommendations: string[] | null;
}

export interface GenerateAIContentResponse {
  success: boolean;
  content: GeneratedContent;
}

export interface AICategory {
  id: string;
  name: string;
  description: string;
}

// ========== Focus Group Types ==========

export interface FocusGroupSession {
  id: string;
  product_id: string;
  run_id: string | null;
  user_id: string;
  name: string;
  session_type: 'individual_interview' | 'group_discussion' | 'panel_interview' | 'free_form';
  topic: string | null;
  objectives: string[] | null;
  agent_ids: string[];
  agent_contexts: Record<string, AgentContext>;
  discussion_guide: Array<{ topic: string; questions: string[] }> | null;
  model_preset: string;
  temperature: number;
  moderator_style: string;
  message_count: number;
  total_tokens: number;
  estimated_cost: number;
  sentiment_trajectory: Array<{ timestamp: string; sentiment: number; agent_id: string }> | null;
  key_themes: string[] | null;
  insights_summary: string | null;
  status: 'active' | 'paused' | 'completed' | 'archived';
  created_at: string;
  updated_at: string;
  ended_at: string | null;
}

export interface FocusGroupSessionCreate {
  product_id: string;
  run_id?: string;
  name: string;
  agent_ids: string[];
  session_type?: string;
  topic?: string;
  objectives?: string[];
  discussion_guide?: Array<{ topic: string; questions: string[] }>;
  model_preset?: string;
  temperature?: number;
  moderator_style?: string;
}

export interface FocusGroupSessionUpdate {
  name?: string;
  topic?: string;
  objectives?: string[];
  discussion_guide?: Array<{ topic: string; questions: string[] }>;
  model_preset?: string;
  temperature?: number;
  moderator_style?: string;
  status?: string;
  insights_summary?: string;
  key_themes?: string[];
}

export interface AgentContext {
  persona: Record<string, unknown>;
  previous_responses?: Record<string, unknown>;
  sentiment_baseline?: number;
  key_themes?: string[];
}

export interface FocusGroupMessage {
  id: string;
  session_id: string;
  sequence_number: number;
  role: 'moderator' | 'agent' | 'system';
  agent_id: string | null;
  agent_name: string | null;
  content: string;
  is_group_response: boolean;
  responding_agents: string[] | null;
  sentiment_score: number | null;
  emotion: string | null;
  confidence: number | null;
  key_points: string[] | null;
  themes: string[] | null;
  quotes: string[] | null;
  input_tokens: number;
  output_tokens: number;
  response_time_ms: number;
  created_at: string;
}

export interface InterviewRequest {
  question: string;
  target_agent_ids?: string[];
  context?: string;
  follow_up?: boolean;
}

export interface InterviewResponse {
  agent_id: string;
  agent_name: string;
  persona_summary: Record<string, unknown>;
  response: string;
  sentiment_score: number;
  emotion: string;
  confidence: number;
  key_points: string[];
  response_time_ms: number;
}

export interface StreamingInterviewChunk {
  agent_id: string;
  agent_name: string;
  chunk: string;
  is_final: boolean;
  sentiment_score?: number;
  emotion?: string;
}

export interface GroupDiscussionRequest {
  topic: string;
  initial_question: string;
  max_turns?: number;
  agent_ids?: string[];
}

export interface GroupDiscussionTurn {
  turn_number: number;
  agent_id: string;
  agent_name: string;
  response: string;
  responding_to: string | null;
  agreement_level: number | null;
  sentiment_score: number;
  emotion: string;
}

export interface GroupDiscussionResponse {
  topic: string;
  turns: GroupDiscussionTurn[];
  consensus_points: string[];
  disagreement_points: string[];
  key_themes: string[];
  sentiment_summary: {
    average: number;
    min: number;
    max: number;
  };
}

export interface SessionSummaryResponse {
  session_id: string;
  session_name: string;
  agent_count: number;
  message_count: number;
  duration_minutes: number | null;
  key_insights: string[];
  key_themes: string[];
  notable_quotes: Array<{ agent: string; quote: string }>;
  sentiment_trajectory: Array<{ timestamp: string; sentiment: number; agent_id: string }>;
  recommendations: string[];
  executive_summary: string;
}

export interface AvailableAgent {
  agent_id: string;
  agent_index: number;
  persona_summary: Record<string, unknown>;
  original_sentiment: number | null;
  key_themes: string[] | null;
}

// ========== Marketplace Types ==========

export interface MarketplaceCategory {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  icon: string | null;
  color: string | null;
  parent_id: string | null;
  display_order: number;
  is_active: boolean;
  template_count: number;
  created_at: string;
  updated_at: string;
}

export interface MarketplaceCategoryWithChildren extends MarketplaceCategory {
  children: MarketplaceCategoryWithChildren[];
}

export interface MarketplaceCategoryCreate {
  name: string;
  slug: string;
  description?: string;
  icon?: string;
  color?: string;
  parent_id?: string;
  display_order?: number;
}

export interface MarketplaceCategoryUpdate {
  name?: string;
  description?: string;
  icon?: string;
  color?: string;
  parent_id?: string;
  display_order?: number;
  is_active?: boolean;
}

export interface MarketplaceTemplateListItem {
  id: string;
  name: string;
  slug: string;
  short_description: string | null;
  category_id: string | null;
  category_name: string | null;
  author_id: string;
  author_name: string | null;
  scenario_type: string;
  tags: string[];
  status: string;
  is_featured: boolean;
  is_verified: boolean;
  is_premium: boolean;
  price_usd: number | null;
  usage_count: number;
  rating_average: number;
  rating_count: number;
  like_count: number;
  preview_image_url: string | null;
  created_at: string;
  published_at: string | null;
}

export interface MarketplaceTemplateDetail extends MarketplaceTemplateListItem {
  description: string | null;
  context: string;
  questions: Array<Record<string, unknown>>;
  variables: Record<string, unknown>;
  demographics: Record<string, unknown>;
  persona_template: Record<string, unknown> | null;
  model_config: Record<string, unknown>;
  recommended_population_size: number;
  stimulus_materials: Record<string, unknown> | null;
  methodology: Record<string, unknown> | null;
  sample_results: Record<string, unknown> | null;
  version: string;
  view_count: number;
  updated_at: string;
  is_liked_by_user: boolean;
  user_review: TemplateReview | null;
}

export interface MarketplaceTemplateCreate {
  name: string;
  description?: string;
  short_description?: string;
  category_id?: string;
  tags?: string[];
  scenario_type: string;
  context: string;
  questions?: Array<Record<string, unknown>>;
  variables?: Record<string, unknown>;
  demographics?: Record<string, unknown>;
  persona_template?: Record<string, unknown>;
  model_config?: Record<string, unknown>;
  recommended_population_size?: number;
  stimulus_materials?: Record<string, unknown>;
  methodology?: Record<string, unknown>;
  preview_image_url?: string;
  sample_results?: Record<string, unknown>;
  source_scenario_id?: string;
  is_premium?: boolean;
  price_usd?: number;
}

export interface MarketplaceTemplateFromScenario {
  scenario_id: string;
  name: string;
  description?: string;
  short_description?: string;
  category_id?: string;
  tags?: string[];
  is_premium?: boolean;
  price_usd?: number;
}

export interface MarketplaceTemplateUpdate {
  name?: string;
  description?: string;
  short_description?: string;
  category_id?: string;
  tags?: string[];
  context?: string;
  questions?: Array<Record<string, unknown>>;
  variables?: Record<string, unknown>;
  demographics?: Record<string, unknown>;
  persona_template?: Record<string, unknown>;
  model_config?: Record<string, unknown>;
  recommended_population_size?: number;
  stimulus_materials?: Record<string, unknown>;
  methodology?: Record<string, unknown>;
  preview_image_url?: string;
  sample_results?: Record<string, unknown>;
  is_premium?: boolean;
  price_usd?: number;
}

export interface MarketplaceTemplateListResponse {
  items: MarketplaceTemplateListItem[];
  total: number;
  page: number;
  page_size: number;
  categories?: MarketplaceCategory[];
}

export interface FeaturedTemplatesResponse {
  featured: MarketplaceTemplateListItem[];
  trending: MarketplaceTemplateListItem[];
  newest: MarketplaceTemplateListItem[];
  by_category: Record<string, MarketplaceTemplateListItem[]>;
}

export interface UseTemplateRequest {
  target_project_id?: string;
  create_type?: 'scenario' | 'product';
  customizations?: Record<string, unknown>;
  name?: string;
}

export interface UseTemplateResponse {
  usage_id: string;
  template_id: string;
  created_type: string;
  created_id: string;
  created_name: string;
  message: string;
}

export interface TemplateReview {
  id: string;
  template_id: string;
  user_id: string;
  user_name: string | null;
  rating: number;
  title: string | null;
  content: string | null;
  is_verified_purchase: boolean;
  is_helpful_count: number;
  created_at: string;
  updated_at: string;
}

export interface TemplateReviewCreate {
  rating: number;
  title?: string;
  content?: string;
}

export interface TemplateReviewUpdate {
  rating?: number;
  title?: string;
  content?: string;
}

export interface TemplateReviewListResponse {
  items: TemplateReview[];
  total: number;
  page: number;
  page_size: number;
  average_rating: number;
  rating_distribution: Record<number, number>;
}

export interface MarketplaceStats {
  total_templates: number;
  total_categories: number;
  total_usages: number;
  total_reviews: number;
  average_rating: number;
  top_categories: Array<{ name: string; slug: string; count: number }>;
  top_authors: Array<{ author_id: string; name: string; template_count: number; total_usage: number }>;
}

export interface AuthorStats {
  total_templates: number;
  total_usages: number;
  total_reviews: number;
  average_rating: number;
  total_likes: number;
  templates: MarketplaceTemplateListItem[];
}

// ========== Vi World Types ==========

export type WorldStatus = 'inactive' | 'running' | 'paused' | 'completed';

export interface NPCState {
  id: string;
  persona_id: string;
  name: string;
  position: { x: number; y: number };
  target_position?: { x: number; y: number } | null;
  direction: 'up' | 'down' | 'left' | 'right';
  state: 'idle' | 'walking' | 'chatting';
  speed: number;
  chat_cooldown?: number;
  current_chat_id?: string | null;
}

export interface WorldChatMessage {
  id: string;
  sender_id: string;
  sender_name: string;
  receiver_id?: string;
  message: string;
  timestamp: number;
}

export interface WorldState {
  id: string;
  template_id: string;
  user_id: string;
  name: string;
  status: WorldStatus;
  world_width: number;
  world_height: number;
  tile_size: number;
  npc_states: Record<string, NPCState>;
  chat_history: WorldChatMessage[];
  simulation_speed: number;
  started_at: string | null;
  last_tick_at: string | null;
  ticks_processed: number;
  total_messages: number;
  total_simulation_time: number;
  created_at: string;
  updated_at: string;
}

export interface WorldStats {
  world_id: string;
  status: WorldStatus;
  population: number;
  npcs_walking: number;
  npcs_chatting: number;
  npcs_idle: number;
  total_messages: number;
  ticks_processed: number;
  simulation_speed: number;
  uptime_seconds: number;
}

export interface ChatHistoryResponse {
  items: WorldChatMessage[];
  total: number;
  page: number;
  page_size: number;
}

// ========== Prediction Types ==========

export type PredictionStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
export type ScenarioType = 'election' | 'consumer' | 'market' | 'social';
export type NetworkType = 'small_world' | 'scale_free' | 'random' | 'complete';

export interface PredictionCategory {
  name: string;
  color?: string;
  metadata?: Record<string, unknown>;
}

export interface BehavioralParams {
  loss_aversion?: number;
  probability_weight_alpha?: number;
  probability_weight_beta?: number;
  status_quo_bias?: number;
  bandwagon_effect?: number;
  confirmation_bias?: number;
  social_influence_weight?: number;
  noise_temperature?: number;
}

export interface AgentConfig {
  count: number;
  demographics?: Record<string, Record<string, number>>;
  behavioral_params?: BehavioralParams;
}

export interface PredictionConfig {
  categories: PredictionCategory[];
  agent_config: AgentConfig;
  num_steps?: number;
  monte_carlo_runs?: number;
  confidence_level?: number;
  social_network_type?: NetworkType;
  enable_marl?: boolean;
  use_calibration?: boolean;
  regional_breakdown?: boolean;
  seed?: number;
}

export interface PredictionCreate {
  name: string;
  description?: string;
  scenario_type: ScenarioType;
  config: PredictionConfig;
}

export interface PredictionResponse {
  id: string;
  user_id: string;
  name: string;
  description: string | null;
  scenario_type: ScenarioType;
  config: PredictionConfig;
  status: PredictionStatus;
  progress: number;
  current_step: number;
  total_steps: number;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface PredictionListResponse {
  predictions: PredictionResponse[];
  total: number;
  skip: number;
  limit: number;
}

export interface CategoryDistribution {
  [category: string]: number;
}

export interface ConfidenceInterval {
  [category: string]: [number, number];
}

export interface PredictionResults {
  prediction_id: string;
  category_distributions: CategoryDistribution;
  confidence_intervals: ConfidenceInterval;
  regional_breakdown?: Record<string, CategoryDistribution>;
  temporal_evolution?: Array<{ step: number; distributions: CategoryDistribution }>;
  agent_statistics?: {
    total_agents: number;
    average_utility: number;
    action_counts: Record<string, number>;
  };
  monte_carlo_stats?: {
    runs: number;
    mean_distributions: CategoryDistribution;
    std_distributions: CategoryDistribution;
  };
  accuracy_metrics?: {
    kl_divergence?: number;
    brier_score?: number;
    coverage_probability?: number;
  };
}

export interface PredictionProgress {
  prediction_id: string;
  status: PredictionStatus;
  progress: number;
  current_step: number;
  total_steps: number;
  current_monte_carlo_run?: number;
  total_monte_carlo_runs?: number;
  message?: string;
  error?: string;
}

export interface CalibrationRequest {
  prediction_id: string;
  ground_truth: {
    category_distributions: CategoryDistribution;
    confidence_intervals?: ConfidenceInterval;
    regional_distributions?: Record<string, CategoryDistribution>;
    source?: string;
    date?: string;
    sample_size?: number;
  };
  config?: {
    method?: 'bayesian' | 'grid_search' | 'random_search' | 'ensemble' | 'adaptive';
    target_accuracy?: number;
    max_iterations?: number;
    patience?: number;
  };
}

export interface CalibrationStatus {
  id: string;
  prediction_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  current_accuracy: number | null;
  best_accuracy: number | null;
  target_accuracy: number;
  iterations_completed: number;
  max_iterations: number;
  best_params: BehavioralParams | null;
  improvement: Record<string, number> | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface MarlTrainingRequest {
  prediction_id: string;
  config?: {
    learning_rate?: number;
    gamma?: number;
    clip_epsilon?: number;
    entropy_coeff?: number;
    value_loss_coeff?: number;
    max_grad_norm?: number;
    n_epochs?: number;
    batch_size?: number;
    n_rollout_steps?: number;
    total_timesteps?: number;
  };
}

export interface PredictionAnalyticsOverview {
  total_predictions: number;
  completed_predictions: number;
  running_predictions: number;
  failed_predictions: number;
  total_agents_simulated: number;
  total_monte_carlo_runs: number;
  predictions_by_scenario: Record<ScenarioType, number>;
  predictions_by_status: Record<PredictionStatus, number>;
  recent_predictions: PredictionResponse[];
}

export interface AccuracyAnalytics {
  average_accuracy: number | null;
  median_accuracy: number | null;
  total_calibrations: number;
  successful_calibrations: number;
  accuracy_by_scenario: Record<ScenarioType, number>;
  accuracy_trend: Array<{ date: string; accuracy: number }>;
  best_performing_scenario: ScenarioType | null;
  history: Array<{ prediction_id: string; accuracy: number; date: string }>;
}

// ============================================================================
// Reliability Types (Phase 7)
// ============================================================================

export type ReliabilityConfidenceLevel = 'low' | 'moderate' | 'high';
export type DriftSeverity = 'none' | 'low' | 'moderate' | 'high' | 'critical';

export interface CalibrationScoreDetail {
  accuracy: number;
  historical_scenarios_run: number;
  best_scenario_accuracy: number;
  worst_scenario_accuracy: number;
  mean_error: number;
  bucket_scores?: Array<{
    predicted_probability_range: [number, number];
    actual_frequency: number;
    sample_size: number;
    calibration_error: number;
  }>;
  validation_runs?: Array<{
    run_id: string;
    predicted_outcome: string;
    actual_outcome: string;
    was_correct: boolean;
  }>;
}

export interface StabilityScoreDetail {
  score: number;
  seeds_tested: number;
  variance_coefficient: number;
  is_stable: boolean;
  most_stable_outcome: string;
  least_stable_outcome: string;
  metric_stability?: Array<{
    metric_name: string;
    mean_value: number;
    std_deviation: number;
    coefficient_of_variation: number;
    is_stable: boolean;
  }>;
}

export interface SensitivitySummaryDetail {
  n_high_impact_variables: number;
  top_impact_variables: string[];
  impact_scores: Record<string, number>;
  recommendations: string[];
  top_factors?: Array<{
    variable_path: string;
    variable_label: string;
    impact_direction: 'positive' | 'negative' | 'mixed';
    impact_magnitude: number;
    elasticity?: number;
  }>;
}

export interface DriftStatusDetail {
  drift_detected: boolean;
  severity: DriftSeverity;
  drifted_variables: string[];
  last_check: string;
  days_since_calibration: number;
  indicators?: Array<{
    indicator_name: string;
    baseline_value: number;
    current_value: number;
    drift_magnitude: number;
    is_significant: boolean;
  }>;
  recommendations?: string[];
}

export interface DataGapsSummaryDetail {
  total_variables: number;
  variables_with_gaps: number;
  gap_percentage: number;
  critical_gaps: string[];
  recommendations: string[];
  gaps?: Array<{
    gap_id: string;
    data_type: string;
    description: string;
    impact_severity: 'low' | 'medium' | 'high';
    was_mitigated: boolean;
  }>;
}

export interface ConfidenceBreakdownDetail {
  overall: number;
  level: ReliabilityConfidenceLevel;
  by_category: Record<string, number>;
  by_time_horizon: Record<string, number>;
  factors: Record<string, number>;
  improvement_suggestions?: string[];
}

export interface ReliabilityReport {
  report_id: string;
  project_id: string;
  node_id?: string;
  generated_at: string;
  valid_until: string;
  engine_version: string;
  report_version: string;
  calibration: CalibrationScoreDetail;
  stability: StabilityScoreDetail;
  sensitivity: SensitivitySummaryDetail;
  drift: DriftStatusDetail;
  data_gaps: DataGapsSummaryDetail;
  confidence: ConfidenceBreakdownDetail;
  overall_reliability_score: number;
  confidence_level: ReliabilityConfidenceLevel;
  is_reliable: boolean;
  reliability_threshold: number;
  recommendations: string[];
  warnings: string[];
}

export interface ReliabilitySummary {
  report_id: string;
  node_id?: string;
  run_id?: string;
  confidence_level: ReliabilityConfidenceLevel;
  confidence_score: number;
  calibration_score: number;
  stability_score: number;
  has_drift_warning: boolean;
  drift_severity: DriftSeverity;
  critical_data_gaps: number;
  computed_at: string;
}

export interface ComputeReliabilityRequest {
  node_id?: string;
  include_calibration?: boolean;
  include_stability?: boolean;
  include_sensitivity?: boolean;
  include_drift?: boolean;
  include_data_gaps?: boolean;
  historical_validation_cutoff?: string;
  stability_seed_count?: number;
  sensitivity_sample_size?: number;
}

export interface HistoricalScenario {
  scenario_id: string;
  name: string;
  description?: string;
  dataset_id?: string;
  time_cutoff: string;
  outcome_date?: string;
  ground_truth: Record<string, number | string>;
  leakage_validated?: boolean;
  accuracy?: number;
  metadata?: {
    region?: string;
    segment?: string;
    sample_size?: number;
    [key: string]: unknown;
  };
  created_at?: string;
}

export interface CalibrationLabConfig {
  project_id: string;
  selected_scenarios: string[];
  parameters: Record<string, number>;
  bounds: Record<string, { min: number; max: number; default: number }>;
  use_cross_validation: boolean;
  n_folds: number;
  target_accuracy: number;
}

export interface AutoTuneResult {
  final_parameters: Record<string, number>;
  initial_accuracy: number;
  final_accuracy: number;
  improvement: number;
  n_iterations: number;
  n_rollbacks: number;
  converged: boolean;
  convergence_reason: string;
  cross_validation_score?: number;
  duration_seconds: number;
}

// =============================================================================
// 2D Replay Types (project.md §11 Phase 8) - READ-ONLY (C3 Compliant)
// =============================================================================

export interface ReplayTimelineMarker {
  tick: number;
  type: string;
  label: string;
  event_types: string[];
}

export interface ReplayTimeline {
  run_id: string;
  node_id?: string;
  total_ticks: number;
  keyframe_ticks: number[];
  event_markers: ReplayTimelineMarker[];
  duration_seconds: number;
  tick_rate: number;
  seed_used: number;
  agent_count: number;
  segment_distribution: Record<string, number>;
  region_distribution: Record<string, number>;
  metrics_summary: Record<string, unknown>;
}

export interface ReplayAgentState {
  agent_id: string;
  tick: number;
  position: { x: number; y: number };
  segment: string;
  region?: string;
  stance: number;
  emotion: number;
  influence: number;
  exposure: number;
  last_action?: string;
  last_event?: string;
  beliefs?: Record<string, number>;
}

export interface ReplayEnvironmentState {
  tick: number;
  variables: Record<string, unknown>;
  active_events: string[];
  metrics: Record<string, number>;
}

export interface ReplayWorldState {
  tick: number;
  timestamp: string;
  agents: Record<string, ReplayAgentState>;
  environment: ReplayEnvironmentState;
  event_log: Array<Record<string, unknown>>;
}

export interface ReplayChunk {
  start_tick: number;
  end_tick: number;
  keyframe_count: number;
  delta_count: number;
  states?: ReplayWorldState[];
}

export interface ReplayAgentHistory {
  agent_id: string;
  states: ReplayAgentState[];
  total_states: number;
}

export interface ReplayTickEvents {
  tick: number;
  events: Array<Record<string, unknown>>;
}

export interface LoadReplayRequest {
  storage_ref: {
    artifact_type: string;
    artifact_id: string;
    storage_path: string;
    storage_backend: string;
  };
  preload_ticks?: number;
  node_id?: string;
}

// =============================================================================
// Export Types (Interaction_design.md §5.19)
// =============================================================================

export type ExportType = 'node_summary' | 'compare_pack' | 'reliability_report' | 'telemetry_snapshot';
export type ExportFormat = 'json' | 'csv' | 'parquet' | 'excel';
export type ExportPrivacy = 'private' | 'team' | 'public';
export type ExportStatus = 'pending' | 'processing' | 'completed' | 'failed';

// Sensitivity types for data redaction (project.md §11 Phase 9)
export type SensitivityType =
  | 'pii'
  | 'financial'
  | 'health'
  | 'behavioral'
  | 'demographic'
  | 'location'
  | 'contact'
  | 'prediction'
  | 'confidence'
  | 'internal';

export interface RedactionConfig {
  enabled: boolean;
  sensitivity_types?: SensitivityType[];
  include_redaction_summary?: boolean;
}

export interface ExportRequest {
  project_id: string;
  export_type: ExportType;
  format: ExportFormat;
  privacy: ExportPrivacy;
  node_ids?: string[];
  run_ids?: string[];
  include_telemetry?: boolean;
  include_agent_details?: boolean;
  date_range?: {
    start: string;
    end: string;
  };
  label?: string;
  // Redaction options (project.md §11 Phase 9)
  enable_redaction?: boolean;
  redact_types?: SensitivityType[];
  include_redaction_summary?: boolean;
  include_pii?: boolean;  // Requires admin role
  include_raw?: boolean;  // Requires telemetry:export permission
}

export interface ExportJob {
  export_id: string;
  project_id: string;
  export_type: ExportType;
  format: ExportFormat;
  privacy: ExportPrivacy;
  status: ExportStatus;
  progress_percent: number;
  file_size_bytes?: number;
  download_url?: string;
  share_url?: string;
  expires_at?: string;
  error_message?: string;
  created_at: string;
  completed_at?: string;
  label?: string;
  // Redaction info
  redacted_field_count?: number;
  redaction_summary?: Record<string, number>;
  metadata?: {
    node_count?: number;
    run_count?: number;
    agent_count?: number;
    tick_count?: number;
  };
}

export interface ExportListItem {
  export_id: string;
  export_type: ExportType;
  format: ExportFormat;
  status: ExportStatus;
  file_size_bytes?: number;
  created_at: string;
  completed_at?: string;
  label?: string;
  // Redaction info
  redacted_field_count?: number;
}

export interface ExportDownloadResponse {
  download_url: string;
  expires_at: string;
}

export interface ExportShareResponse {
  share_url: string;
  expires_at: string;
  privacy: ExportPrivacy;
}

// =============================================================================
// LLM Admin Types (GAPS.md GAP-P0-001)
// =============================================================================

export interface LLMProfile {
  id: string;
  tenant_id: string | null;
  profile_key: string;
  label: string;
  description: string | null;
  model: string;
  temperature: number;
  max_tokens: number;
  top_p: number | null;
  frequency_penalty: number | null;
  presence_penalty: number | null;
  cost_per_1k_input_tokens: number;
  cost_per_1k_output_tokens: number;
  fallback_models: string[] | null;
  rate_limit_rpm: number | null;
  rate_limit_tpm: number | null;
  cache_enabled: boolean;
  cache_ttl_seconds: number | null;
  system_prompt_template: string | null;
  priority: number;
  is_active: boolean;
  is_default: boolean;
  created_at: string;
  updated_at: string;
  created_by_id: string | null;
}

export interface LLMProfileCreate {
  profile_key: string;
  label: string;
  description?: string;
  model: string;
  temperature?: number;
  max_tokens?: number;
  top_p?: number;
  frequency_penalty?: number;
  presence_penalty?: number;
  cost_per_1k_input_tokens?: number;
  cost_per_1k_output_tokens?: number;
  fallback_models?: string[];
  rate_limit_rpm?: number;
  rate_limit_tpm?: number;
  cache_enabled?: boolean;
  cache_ttl_seconds?: number;
  system_prompt_template?: string;
  priority?: number;
  tenant_id?: string;
  is_default?: boolean;
}

export interface LLMProfileUpdate {
  label?: string;
  description?: string;
  model?: string;
  temperature?: number;
  max_tokens?: number;
  top_p?: number;
  frequency_penalty?: number;
  presence_penalty?: number;
  cost_per_1k_input_tokens?: number;
  cost_per_1k_output_tokens?: number;
  fallback_models?: string[];
  rate_limit_rpm?: number;
  rate_limit_tpm?: number;
  cache_enabled?: boolean;
  cache_ttl_seconds?: number;
  system_prompt_template?: string;
  priority?: number;
  is_active?: boolean;
  is_default?: boolean;
}

export interface LLMProfileListResponse {
  profiles: LLMProfile[];
  total: number;
}

export interface LLMCall {
  id: string;
  tenant_id: string | null;
  profile_key: string;
  project_id: string | null;
  run_id: string | null;
  model_requested: string;
  model_used: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  response_time_ms: number;
  cost_usd: number;
  status: string;
  cache_hit: boolean;
  fallback_attempts: number;
  created_at: string;
}

export interface LLMCallListResponse {
  calls: LLMCall[];
  total: number;
  page: number;
  page_size: number;
}

export interface LLMCostSummary {
  total_calls: number;
  total_cost_usd: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  avg_response_time_ms: number;
  cache_hits: number;
  cache_hit_rate: number;
}

export interface LLMCostByProfile {
  profile_key: string;
  call_count: number;
  total_cost_usd: number;
  total_tokens: number;
}

export interface LLMCostReport {
  summary: LLMCostSummary;
  by_profile: LLMCostByProfile[];
  period_start: string | null;
  period_end: string | null;
}

export interface AvailableLLMModel {
  model: string;
  provider: string;
  cost_per_1k_input_tokens: number;
  cost_per_1k_output_tokens: number;
  max_context_length: number;
  description: string;
}

export interface AvailableLLMModelsResponse {
  models: AvailableLLMModel[];
}

export interface ProfileKeyInfo {
  key: string;
  label: string;
  description: string;
  recommended_model: string;
}

export interface ProfileKeysResponse {
  keys: ProfileKeyInfo[];
}

export interface LLMTestResponse {
  success: boolean;
  response: string | null;
  model_used: string;
  input_tokens: number;
  output_tokens: number;
  response_time_ms: number;
  cost_usd: number;
  error: string | null;
}

// =============================================================================
// Audit Log Admin Types (GAPS.md GAP-P0-006)
// =============================================================================

export interface AuditLogEntry {
  id: string;
  organization_id: string | null;
  tenant_id: string | null;
  user_id: string | null;
  user_email: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  details: Record<string, unknown>;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
}

export interface AuditLogListResponse {
  logs: AuditLogEntry[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AuditLogStatsResponse {
  total_events: number;
  events_today: number;
  events_this_week: number;
  events_by_action: Record<string, number>;
  events_by_resource_type: Record<string, number>;
  top_users: Array<{
    user_id: string | null;
    email: string;
    event_count: number;
  }>;
  recent_activity_trend: Array<{
    date: string;
    count: number;
  }>;
}

export interface AuditLogExportResponse {
  filename: string;
  format: string;
  total_records: number;
  download_url: string | null;
  data: Array<Record<string, unknown>> | null;
}

export const api = new ApiClient(API_URL);

export default api;

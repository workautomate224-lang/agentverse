/**
 * Blueprint Contract
 * Reference: blueprint.md §3, §5, §6, §7
 *
 * Blueprint is the "single source of truth" for every project.
 * - Every project has a Blueprint (versioned)
 * - Every run references a specific blueprint version
 * - Any blueprint change creates a new version and is audit-tracked
 */

import { Timestamps, TenantScoped } from './common';

// ============================================================================
// Enums (blueprint.md §3.1)
// ============================================================================

/**
 * Domain classification for project goals (blueprint.md §3.1.A)
 */
export type DomainGuess =
  | 'election'
  | 'market_demand'
  | 'production_forecast'
  | 'policy_impact'
  | 'perception_risk'
  | 'crime_route'
  | 'personal_decision'
  | 'generic';

/**
 * Output types required (blueprint.md §3.1.A)
 */
export type TargetOutput =
  | 'distribution'
  | 'point_estimate'
  | 'ranked_outcomes'
  | 'paths'
  | 'recommendations';

/**
 * Primary drivers for prediction (blueprint.md §3.1.B)
 */
export type PrimaryDriver =
  | 'population'
  | 'timeseries'
  | 'network'
  | 'constraints'
  | 'events'
  | 'sentiment'
  | 'mixed';

/**
 * Input slot types (blueprint.md §3.1.C)
 */
export type SlotType =
  | 'TimeSeries'
  | 'Table'
  | 'EntitySet'
  | 'Graph'
  | 'TextCorpus'
  | 'Labels'
  | 'Ruleset'
  | 'AssumptionSet'
  | 'PersonaSet'
  | 'EventScriptSet';

/**
 * Requirement level for slots (blueprint.md §3.1.C)
 */
export type RequiredLevel = 'required' | 'recommended' | 'optional';

/**
 * How a slot can be fulfilled (blueprint.md §6.2)
 */
export type AcquisitionMethod =
  | 'manual_upload'
  | 'connect_api'
  | 'ai_research'
  | 'ai_generation'
  | 'snapshot_import';

/**
 * Checklist item alert states (blueprint.md §7.2)
 */
export type AlertState =
  | 'ready'           // ✅ Ready
  | 'needs_attention' // 🟡 Needs attention
  | 'blocked'         // 🔴 Blocked
  | 'not_started';    // ⚪ Not started

/**
 * Available actions for tasks (blueprint.md §3.1.D)
 */
export type TaskAction =
  | 'ai_generate'
  | 'ai_research'
  | 'manual_add'
  | 'connect_source';

// ============================================================================
// Blueprint Types (blueprint.md §3)
// ============================================================================

/**
 * Time horizon configuration
 */
export interface Horizon {
  range: string;       // e.g., "6 months", "2026-Q1"
  granularity: 'daily' | 'weekly' | 'monthly' | 'event_based';
}

/**
 * Scope configuration
 */
export interface Scope {
  geography?: string;  // e.g., "Malaysia", "Selangor"
  entity?: string;     // e.g., "Product X", "Voters"
}

/**
 * Success metrics configuration
 */
export interface SuccessMetrics {
  description: string;
  evaluation_metrics: string[];
}

/**
 * Schema requirements for a slot
 */
export interface SchemaRequirements {
  min_fields?: string[];
  types?: Record<string, string>;
  allowed_values?: Record<string, string[]>;
}

/**
 * Temporal requirements for a slot
 */
export interface TemporalRequirements {
  must_have_timestamps: boolean;
  must_be_before_cutoff: boolean;
  required_window?: string;
}

/**
 * Quality requirements for a slot
 */
export interface QualityRequirements {
  missing_threshold?: number;      // Max % missing values
  dedupe_rules?: string[];
  min_coverage?: number;           // Min % coverage required
}

/**
 * Validation plan for a slot
 */
export interface ValidationPlan {
  ai_checks: string[];
  programmatic_checks: string[];
}

/**
 * Input Slot definition (blueprint.md §3.1.C)
 */
export interface BlueprintSlot {
  slot_id: string;
  slot_name: string;
  slot_type: SlotType;
  required_level: RequiredLevel;
  description?: string;
  schema_requirements?: SchemaRequirements;
  temporal_requirements?: TemporalRequirements;
  quality_requirements?: QualityRequirements;
  allowed_acquisition_methods: AcquisitionMethod[];
  validation_plan?: ValidationPlan;
  derived_artifacts?: string[];
  // Status
  status: AlertState;
  status_reason?: string;
  fulfilled: boolean;
  fulfilled_by?: {
    type: string;
    id: string;
    name: string;
  };
  fulfillment_method?: AcquisitionMethod;
  // AI artifacts
  alignment_score?: number;
  alignment_reasons?: string[];
}

/**
 * Section Task definition (blueprint.md §3.1.D)
 */
export interface BlueprintTask {
  task_id: string;
  section_id: string;
  sort_order: number;
  title: string;
  description?: string;
  why_it_matters?: string;
  linked_slot_ids?: string[];
  available_actions: TaskAction[];
  completion_criteria?: {
    artifact_type: string;
    artifact_exists: boolean;
  };
  alert_config?: {
    warn_if_incomplete: boolean;
    warn_if_low_quality: boolean;
    quality_threshold?: number;
  };
  // Status
  status: AlertState;
  status_reason?: string;
  last_summary_ref?: string;
}

/**
 * Calibration plan (blueprint.md §3.1.E)
 */
export interface CalibrationPlan {
  required_historical_windows: string[];
  labels_needed: string[];
  evaluation_metrics: string[];
  min_test_suite_size: number;
}

/**
 * Branching plan for Universe Map (blueprint.md §3.1.F)
 */
export interface BranchingPlan {
  branchable_variables: string[];
  event_template_suggestions: string[];
  probability_aggregation_policy: 'mean' | 'median' | 'weighted';
  node_metadata_requirements: string[];
}

/**
 * Blueprint - the versioned, auditable "construction plan" for a project
 * Reference: blueprint.md §3
 */
export interface Blueprint extends TenantScoped, Timestamps {
  id: string;
  project_id: string;
  version: number;
  policy_version: string;
  is_active: boolean;

  // A) Project Profile (blueprint.md §3.1.A)
  goal_text: string;
  goal_summary?: string;
  domain_guess: DomainGuess;
  target_outputs?: TargetOutput[];
  horizon?: Horizon;
  scope?: Scope;
  success_metrics?: SuccessMetrics;

  // B) Strategy (blueprint.md §3.1.B)
  recommended_core: 'collective' | 'targeted' | 'hybrid';
  primary_drivers?: PrimaryDriver[];
  required_modules?: string[];

  // C) Input Slots (Contract)
  input_slots?: BlueprintSlot[];

  // D) Section Task Map
  section_task_map?: Record<string, BlueprintTask[]>;

  // E) Calibration + Backtest Plan
  calibration_plan?: CalibrationPlan;

  // F) Universe Map / Branching Plan
  branching_plan?: BranchingPlan;

  // G) Policy + Audit Metadata
  clarification_answers?: Record<string, string>;
  constraints_applied?: string[];
  risk_notes?: string[];
  created_by?: string;
  is_draft: boolean;
}

/**
 * Blueprint summary for lists
 */
export interface BlueprintSummary {
  id: string;
  project_id: string;
  version: number;
  is_active: boolean;
  goal_summary?: string;
  domain_guess: DomainGuess;
  is_draft: boolean;
  created_at: string;
  slots_ready: number;
  slots_total: number;
  tasks_ready: number;
  tasks_total: number;
}

// ============================================================================
// DTOs
// ============================================================================

/**
 * Input for creating a new blueprint
 */
export interface CreateBlueprintInput {
  project_id: string;
  goal_text: string;
  skip_clarification?: boolean;
}

/**
 * Input for updating blueprint from clarification
 */
export interface UpdateBlueprintFromClarificationInput {
  blueprint_id: string;
  clarification_answers: Record<string, string>;
}

/**
 * Clarifying question (blueprint.md §4.2.1)
 */
export interface ClarifyingQuestion {
  id: string;
  question: string;
  reason: string;
  type: 'single_select' | 'multi_select' | 'short_input';
  options?: string[];
  required: boolean;
}

/**
 * Goal analysis result
 */
export interface GoalAnalysisResult {
  goal_summary: string;
  domain_guess: DomainGuess;
  clarifying_questions: ClarifyingQuestion[];
  blueprint_preview: {
    required_slots: string[];
    recommended_slots: string[];
    section_tasks: Record<string, string[]>;
  };
  risk_notes: string[];
}

// ============================================================================
// Job Types (blueprint.md §5)
// ============================================================================

/**
 * Job status (blueprint.md §5.3)
 */
export type PILJobStatus =
  | 'queued'
  | 'running'
  | 'succeeded'
  | 'failed'
  | 'cancelled'
  | 'partial';

/**
 * Job types
 */
export type PILJobType =
  // Goal Analysis
  | 'goal_analysis'
  | 'clarification_generate'
  | 'blueprint_build'
  // Slot Processing
  | 'slot_validation'
  | 'slot_summarization'
  | 'slot_alignment_scoring'
  | 'slot_compilation'
  // Task Processing
  | 'task_validation'
  | 'task_guidance_generate'
  // Calibration & Quality
  | 'calibration_check'
  | 'backtest_validation'
  | 'reliability_analysis'
  // AI Research
  | 'ai_research'
  | 'ai_generation';

/**
 * Job priority levels
 */
export type PILJobPriority = 'low' | 'normal' | 'high' | 'critical';

/**
 * PIL Job (blueprint.md §5)
 */
export interface PILJob extends TenantScoped, Timestamps {
  id: string;
  project_id?: string;
  blueprint_id?: string;
  job_type: PILJobType;
  job_name: string;
  priority: PILJobPriority;
  celery_task_id?: string;
  status: PILJobStatus;
  // Progress (blueprint.md §5.4)
  progress_percent: number;
  stage_name?: string;
  eta_hint?: string;
  stages_completed: number;
  stages_total: number;
  // Input/Output
  input_params?: Record<string, unknown>;
  result?: Record<string, unknown>;
  error_message?: string;
  // Artifact references
  artifact_ids?: string[];
  slot_id?: string;
  task_id?: string;
  // Retry
  retry_count: number;
  max_retries: number;
  // Tracking
  created_by?: string;
  started_at?: string;
  completed_at?: string;
}

/**
 * Job progress update (blueprint.md §5.4)
 */
export interface JobProgressUpdate {
  job_id: string;
  progress_percent: number;
  stage_name?: string;
  eta_hint?: string;
}

/**
 * Job notification (blueprint.md §5.5)
 */
export interface JobNotification {
  job_id: string;
  job_type: PILJobType;
  job_name: string;
  status: PILJobStatus;
  message: string;
  artifact_ids?: string[];
  timestamp: string;
}

// ============================================================================
// Artifact Types (blueprint.md §5.6)
// ============================================================================

/**
 * Artifact types
 */
export type ArtifactType =
  // Goal Analysis
  | 'goal_summary'
  | 'clarification_questions'
  | 'blueprint_preview'
  // Slot Processing
  | 'slot_validation_report'
  | 'slot_summary'
  | 'slot_alignment_report'
  | 'slot_compiled_output'
  // Task Processing
  | 'task_guidance'
  | 'task_validation_report'
  // Calibration
  | 'calibration_report'
  | 'backtest_report'
  | 'reliability_report'
  // AI Research
  | 'research_result'
  | 'generated_data';

/**
 * PIL Artifact (blueprint.md §5.6)
 */
export interface PILArtifact extends TenantScoped {
  id: string;
  project_id: string;
  blueprint_id?: string;
  blueprint_version?: number;
  artifact_type: ArtifactType;
  artifact_name: string;
  job_id?: string;
  slot_id?: string;
  task_id?: string;
  content?: Record<string, unknown>;
  content_text?: string;
  alignment_score?: number;
  quality_score?: number;
  validation_passed?: boolean;
  created_at: string;
}

// ============================================================================
// Section IDs (blueprint.md §8.1)
// ============================================================================

export const PLATFORM_SECTIONS = [
  'overview',
  'inputs',
  'data',
  'personas',
  'rules',
  'run_params',
  'run_center',
  'event_lab',
  'universe_map',
  'society_simulation',
  'target_planner',
  'reliability',
  'telemetry_replay',
  'world_viewer_2d',
  'reports',
  'settings',
  'library',
  'calibration_lab',
] as const;

export type PlatformSection = typeof PLATFORM_SECTIONS[number];

// ============================================================================
// Guidance Panel (blueprint.md §8)
// ============================================================================

/**
 * Guidance Panel data for a section
 */
export interface GuidancePanel {
  section_id: PlatformSection;
  project_id: string;
  blueprint_version: number;
  tasks: BlueprintTask[];
  required_slots: BlueprintSlot[];
  recommended_slots: BlueprintSlot[];
  overall_status: AlertState;
  next_suggested_action?: {
    action: TaskAction;
    target_slot_id?: string;
    target_task_id?: string;
    reason: string;
  };
}

// ============================================================================
// Checklist (blueprint.md §7)
// ============================================================================

/**
 * Checklist item with alert state
 */
export interface ChecklistItem {
  id: string;
  title: string;
  section_id: PlatformSection;
  status: AlertState;
  status_reason?: string;
  why_it_matters?: string;
  missing_items?: string[];
  next_action?: {
    action: TaskAction;
    label: string;
  };
  latest_summary?: string;
  match_score?: number;
}

/**
 * Project checklist (blueprint.md §7)
 */
export interface ProjectChecklist {
  project_id: string;
  blueprint_id: string;
  blueprint_version: number;
  items: ChecklistItem[];
  ready_count: number;
  needs_attention_count: number;
  blocked_count: number;
  not_started_count: number;
  overall_readiness: 'ready' | 'needs_work' | 'blocked';
}

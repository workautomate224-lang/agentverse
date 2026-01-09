/**
 * Event Script Contract
 * Reference: project.md §6.4
 *
 * Events must be executable without LLM involvement at runtime.
 * They are compiled from natural language prompts into deterministic scripts.
 */

import { Timestamps, TenantScoped } from './common';

// ============================================================================
// Event Types
// ============================================================================

export type EventType =
  | 'policy'           // Government/regulatory policy change
  | 'media'            // News, social media, information events
  | 'shock'            // External shocks (economic, natural, etc.)
  | 'individual_action' // Specific individual action
  | 'environmental'    // Environmental/contextual changes
  | 'social'           // Social dynamics events
  | 'custom';          // User-defined event type

// ============================================================================
// Event Scope
// ============================================================================

export interface EventScope {
  // Geographic targeting
  affected_regions?: string[];
  region_filter?: Record<string, unknown>;

  // Demographic targeting
  affected_persona_segments?: string[];
  segment_filter?: Record<string, unknown>;

  // Time bounds
  start_tick: number;
  end_tick?: number;  // If undefined, instantaneous or permanent

  // Agent targeting (for individual actions)
  target_agent_ids?: string[];
}

// ============================================================================
// Intensity Profile
// ============================================================================

export type IntensityProfileType =
  | 'instantaneous'   // Full effect immediately
  | 'linear_decay'    // Effect decays linearly over time
  | 'exponential_decay' // Effect decays exponentially
  | 'lagged'          // Effect appears after delay
  | 'pulse'           // Effect oscillates
  | 'step'            // Step function (on/off)
  | 'custom';         // Custom profile

export interface IntensityProfile {
  profile_type: IntensityProfileType;
  initial_intensity: number;  // 0-1

  // Decay parameters (for decay profiles)
  decay_rate?: number;
  half_life_ticks?: number;

  // Lag parameters
  lag_ticks?: number;

  // Custom profile (tick -> intensity mapping)
  custom_profile?: Record<number, number>;
}

// ============================================================================
// Variable Deltas
// ============================================================================

export interface EnvironmentDelta {
  variable_path: string;  // e.g., "economy.inflation_rate"
  operation: 'set' | 'add' | 'multiply' | 'min' | 'max';
  value: number | string | boolean;
  duration_ticks?: number;
}

export interface PerceptionDelta {
  // Which perception weights to modify
  target_perception: string;  // e.g., "source_trust.mainstream_media"

  // Delta operation
  operation: 'set' | 'add' | 'multiply';
  value: number;

  // Targeting
  affected_segments?: string[];

  // Duration
  duration_ticks?: number;
}

export interface EventDeltas {
  environment_deltas: EnvironmentDelta[];
  perception_deltas: PerceptionDelta[];

  // Custom deltas for domain-specific effects
  custom_deltas?: Record<string, unknown>[];
}

// ============================================================================
// Event Uncertainty
// ============================================================================

export interface EventUncertainty {
  // Probability that the event occurs as specified
  occurrence_probability: number;

  // Uncertainty in the intensity
  intensity_variance: number;

  // Assumptions made during compilation
  assumptions: string[];

  // Confidence in the compiled script
  compilation_confidence: number;
}

// ============================================================================
// Event Provenance
// ============================================================================

export interface EventProvenance {
  // Original natural language prompt
  compiled_from: string;

  // Compiler version that generated this script
  compiler_version: string;

  // When compilation occurred
  compiled_at: string;  // ISO 8601

  // Model used for compilation
  compiler_model?: string;

  // Any manual edits after compilation
  manually_edited: boolean;
  edited_at?: string;
  edited_by?: string;
}

// ============================================================================
// Event Script (project.md §6.4)
// ============================================================================

export interface EventScript extends TenantScoped, Timestamps {
  // Identity
  event_id: string;
  project_id: string;

  // Classification
  event_type: EventType;
  label: string;
  description?: string;

  // Targeting
  scope: EventScope;

  // Effects
  deltas: EventDeltas;

  // Intensity over time
  intensity_profile: IntensityProfile;

  // Uncertainty quantification
  uncertainty: EventUncertainty;

  // Provenance (how was this created)
  provenance: EventProvenance;

  // Versioning
  event_version: string;
  schema_version: string;

  // Status
  is_active: boolean;
  is_validated: boolean;
}

// ============================================================================
// Event Bundle (multiple events as a scenario)
// ============================================================================

export interface EventBundle {
  bundle_id: string;
  label: string;
  description?: string;
  event_ids: string[];

  // Execution order (if events depend on each other)
  execution_order?: string[];

  // Bundle-level probability
  joint_probability?: number;
}

// ============================================================================
// Create/Update DTOs
// ============================================================================

export interface CreateEventScriptInput {
  event_type: EventType;
  label: string;
  description?: string;
  scope: EventScope;
  deltas: EventDeltas;
  intensity_profile: IntensityProfile;
  uncertainty?: Partial<EventUncertainty>;
  provenance?: Partial<EventProvenance>;
}

export interface CompileEventInput {
  project_id: string;
  natural_language_prompt: string;
  context?: {
    target_tick?: number;
    affected_regions?: string[];
    affected_segments?: string[];
  };
}

export interface CompileEventOutput {
  event_script: EventScript;
  alternative_interpretations?: EventScript[];
  compilation_notes: string[];
  confidence: number;
}

// ============================================================================
// Event Validation
// ============================================================================

export interface EventValidationResult {
  is_valid: boolean;
  errors: string[];
  warnings: string[];
  suggestions: string[];
}

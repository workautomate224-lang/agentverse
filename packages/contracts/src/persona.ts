/**
 * Persona Contract (Canonical Form)
 * Reference: project.md §6.2
 */

import { Timestamps, TenantScoped } from './common';

// ============================================================================
// Persona Source
// ============================================================================

export type PersonaSource = 'uploaded' | 'generated' | 'deep_search';

// ============================================================================
// Demographics (Structured, Normalized)
// ============================================================================

export interface Demographics {
  age?: number;
  age_range?: [number, number];
  gender?: string;
  income_bracket?: string;
  education_level?: string;
  occupation?: string;
  location_type?: string;  // urban/suburban/rural
  region?: string;
  country?: string;
  ethnicity?: string;
  marital_status?: string;
  household_size?: number;
  custom?: Record<string, unknown>;
}

// ============================================================================
// Preferences Vector
// ============================================================================

export interface PreferencesVector {
  // Media diet preferences (0-1 scale)
  media_consumption: {
    social_media?: number;
    traditional_news?: number;
    streaming?: number;
    print?: number;
    podcasts?: number;
    custom?: Record<string, number>;
  };

  // Consumption preferences
  consumption: {
    price_sensitivity?: number;
    quality_focus?: number;
    brand_consciousness?: number;
    sustainability_focus?: number;
    convenience_priority?: number;
    custom?: Record<string, number>;
  };

  // Risk attitude (-1 to 1: risk-averse to risk-seeking)
  risk_attitude?: number;

  // Custom preference dimensions
  custom?: Record<string, number>;
}

// ============================================================================
// Perception Weights
// ============================================================================

export interface PerceptionWeights {
  // Trust in sources (0-1)
  source_trust: {
    government?: number;
    mainstream_media?: number;
    social_media?: number;
    experts?: number;
    peers?: number;
    influencers?: number;
    custom?: Record<string, number>;
  };

  // Attention allocation (weights summing to ~1)
  attention_allocation: {
    local_news?: number;
    national_news?: number;
    international_news?: number;
    entertainment?: number;
    work_related?: number;
    custom?: Record<string, number>;
  };

  // Priors / baseline beliefs
  priors: Record<string, number>;
}

// ============================================================================
// Bias Parameters (Behavioral Economics)
// ============================================================================

export interface BiasParameters {
  // Loss aversion (1.0 = neutral, >1 = loss averse)
  loss_aversion?: number;

  // Confirmation bias strength (0-1)
  confirmation_bias?: number;

  // Conformity / social proof (0-1)
  conformity?: number;

  // Status quo bias (0-1)
  status_quo_bias?: number;

  // Anchoring susceptibility (0-1)
  anchoring?: number;

  // Availability heuristic strength (0-1)
  availability_heuristic?: number;

  // Optimism/pessimism bias (-1 to 1)
  optimism_bias?: number;

  // Custom bias parameters
  custom?: Record<string, number>;
}

// ============================================================================
// Action Priors
// ============================================================================

export interface ActionPriors {
  // Baseline propensity for action types (0-1)
  propensities: Record<string, number>;

  // Action frequency modifiers
  frequency_modifiers?: Record<string, number>;

  // Context-dependent adjustments
  context_adjustments?: Record<string, Record<string, number>>;
}

// ============================================================================
// Evidence References (for deep search)
// ============================================================================

export interface EvidenceRef {
  source_url?: string;
  source_type: string;
  retrieved_at: string;
  confidence: number;
  excerpt?: string;
}

// ============================================================================
// Persona (project.md §6.2)
// ============================================================================

export interface Persona extends TenantScoped, Timestamps {
  // Identity
  persona_id: string;
  label: string;
  source: PersonaSource;

  // Project association
  project_id: string;

  // Demographics
  demographics: Demographics;

  // Preferences
  preferences: PreferencesVector;

  // Perception
  perception_weights: PerceptionWeights;

  // Biases
  bias_parameters: BiasParameters;

  // Action priors
  action_priors: ActionPriors;

  // Uncertainty
  uncertainty_score: number;  // 0-1, higher = more uncertain
  evidence_refs?: EvidenceRef[];

  // Versioning
  persona_version: string;
  schema_version: string;

  // Segments
  segment_ids?: string[];

  // Active status
  is_active: boolean;
}

// ============================================================================
// Persona Segment
// ============================================================================

export interface PersonaSegment extends TenantScoped, Timestamps {
  segment_id: string;
  project_id: string;
  name: string;
  description?: string;
  filter_criteria: Record<string, unknown>;
  persona_count: number;
}

// ============================================================================
// Create/Update DTOs
// ============================================================================

export interface CreatePersonaInput {
  label: string;
  source: PersonaSource;
  project_id: string;
  demographics: Demographics;
  preferences?: Partial<PreferencesVector>;
  perception_weights?: Partial<PerceptionWeights>;
  bias_parameters?: Partial<BiasParameters>;
  action_priors?: Partial<ActionPriors>;
  uncertainty_score?: number;
  evidence_refs?: EvidenceRef[];
  segment_ids?: string[];
}

export interface ImportPersonasInput {
  project_id: string;
  personas: CreatePersonaInput[];
  source: PersonaSource;
}

export interface PersonaValidationResult {
  is_valid: boolean;
  coverage_issues: string[];
  conflict_issues: string[];
  missing_fields: string[];
  suggestions: string[];
}

// ============================================================================
// Persona Summary (for lists)
// ============================================================================

export interface PersonaSummary {
  persona_id: string;
  label: string;
  source: PersonaSource;
  uncertainty_score: number;
  segment_ids?: string[];
  created_at: string;
}

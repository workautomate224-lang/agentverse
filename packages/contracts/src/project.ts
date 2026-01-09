/**
 * ProjectSpec Contract
 * Reference: project.md §6.1
 */

import {
  PredictionCore,
  PrivacyLevel,
  Timestamps,
  TenantScoped,
} from './common';

// ============================================================================
// Domain Templates (project.md §3.1)
// ============================================================================

export type DomainTemplate =
  | 'election'
  | 'market_research'
  | 'policy_impact'
  | 'financial_forecast'
  | 'social_dynamics'
  | 'custom';

// ============================================================================
// Policy Flags (project.md §8.5)
// ============================================================================

export interface PolicyFlags {
  disallow_harm_guidance: boolean;
  require_explanation_layer: boolean;
  sensitive_domain: boolean;
  requires_ethics_review: boolean;
}

// ============================================================================
// Output Metrics Configuration
// ============================================================================

export type OutputMetricType =
  | 'outcome_distribution'
  | 'trend_over_time'
  | 'key_drivers'
  | 'reliability_report'
  | 'turning_points'
  | 'confidence_intervals';

export interface OutputMetricsConfig {
  enabled_metrics: OutputMetricType[];
  custom_metrics?: string[];
}

// ============================================================================
// ProjectSpec (project.md §6.1)
// ============================================================================

export interface ProjectSpec extends TenantScoped, Timestamps {
  // Identity
  project_id: string;

  // Core configuration
  title: string;
  goal_nl: string;  // Natural-language goal
  description?: string;

  // Prediction configuration
  prediction_core: PredictionCore;
  domain_template?: DomainTemplate;

  // Simulation defaults
  default_horizon: number;  // ticks/time window
  default_output_metrics: OutputMetricsConfig;

  // Access control
  privacy_level: PrivacyLevel;
  policy_flags: PolicyFlags;

  // Ownership
  owner_id: string;

  // Status
  has_baseline: boolean;
  root_node_id?: string;
}

// ============================================================================
// Create/Update DTOs
// ============================================================================

export interface CreateProjectInput {
  title: string;
  goal_nl: string;
  description?: string;
  prediction_core: PredictionCore;
  domain_template?: DomainTemplate;
  default_horizon?: number;
  default_output_metrics?: Partial<OutputMetricsConfig>;
  privacy_level?: PrivacyLevel;
  policy_flags?: Partial<PolicyFlags>;
}

export interface UpdateProjectInput {
  title?: string;
  goal_nl?: string;
  description?: string;
  prediction_core?: PredictionCore;
  domain_template?: DomainTemplate;
  default_horizon?: number;
  default_output_metrics?: Partial<OutputMetricsConfig>;
  privacy_level?: PrivacyLevel;
  policy_flags?: Partial<PolicyFlags>;
}

// ============================================================================
// Project Summary (for lists)
// ============================================================================

export interface ProjectSummary {
  project_id: string;
  title: string;
  prediction_core: PredictionCore;
  domain_template?: DomainTemplate;
  has_baseline: boolean;
  privacy_level: PrivacyLevel;
  created_at: string;
  updated_at: string;
  drift_warning?: boolean;
  last_run_status?: 'succeeded' | 'failed' | 'running';
}

/**
 * Reliability & Calibration Contracts
 * Reference: project.md §7.1
 *
 * Every prediction must ship with reliability metrics.
 */

import { ConfidenceLevel, Timestamps, TenantScoped, ArtifactRef } from './common';

// ============================================================================
// Calibration Score
// ============================================================================

export interface CalibrationScore {
  // Overall calibration (0-1, 1 is perfect)
  overall_score: number;

  // By prediction bucket
  bucket_scores: {
    predicted_probability_range: [number, number];
    actual_frequency: number;
    sample_size: number;
    calibration_error: number;
  }[];

  // Historical validation details
  validation_runs: {
    run_id: string;
    predicted_outcome: string;
    actual_outcome: string;
    prediction_date: string;
    outcome_date: string;
    was_correct: boolean;
  }[];

  // Calibration methodology
  methodology: string;
  validation_dataset_ref?: ArtifactRef;
}

// ============================================================================
// Stability Score
// ============================================================================

export interface StabilityScore {
  // Overall stability (0-1, 1 is perfectly stable)
  overall_score: number;

  // Variance across seeds
  seed_variance: number;

  // Per-metric stability
  metric_stability: {
    metric_name: string;
    mean_value: number;
    std_deviation: number;
    coefficient_of_variation: number;
    is_stable: boolean;
  }[];

  // Number of seeds used
  seed_count: number;

  // Outlier detection
  outlier_runs?: string[];  // run_ids that were outliers
}

// ============================================================================
// Sensitivity Summary
// ============================================================================

export interface SensitivityFactor {
  variable_path: string;
  variable_label: string;

  // Impact direction and magnitude
  impact_direction: 'positive' | 'negative' | 'nonlinear';
  impact_magnitude: number;  // Normalized 0-1

  // Elasticity (% change in outcome per % change in variable)
  elasticity?: number;

  // Confidence in this sensitivity estimate
  confidence: number;
}

export interface SensitivitySummary {
  // Top influential variables
  top_factors: SensitivityFactor[];

  // Interaction effects (if any)
  interaction_effects?: {
    variables: string[];
    interaction_type: 'amplifying' | 'dampening' | 'threshold';
    description: string;
  }[];

  // Sensitivity analysis methodology
  methodology: 'one_at_a_time' | 'global' | 'local';
  sample_size: number;
}

// ============================================================================
// Drift Status
// ============================================================================

export type DriftSeverity = 'none' | 'low' | 'medium' | 'high' | 'critical';

export interface DriftIndicator {
  indicator_name: string;

  // Current vs. baseline
  baseline_value: number;
  current_value: number;
  drift_magnitude: number;

  // Statistical test
  test_type: string;
  p_value: number;
  is_significant: boolean;

  // Impact assessment
  estimated_impact_on_predictions: 'low' | 'medium' | 'high';
}

export interface DriftStatus {
  // Overall drift assessment
  severity: DriftSeverity;
  has_drift: boolean;

  // Specific drift indicators
  indicators: DriftIndicator[];

  // When drift was detected
  detected_at?: string;

  // Recommendations
  recommendations: string[];

  // Comparison baseline
  baseline_date: string;
  baseline_dataset_ref?: ArtifactRef;
}

// ============================================================================
// Data Gaps
// ============================================================================

export interface DataGap {
  gap_id: string;

  // What's missing
  data_type: string;
  description: string;

  // Scope of the gap
  affected_regions?: string[];
  affected_segments?: string[];
  affected_time_range?: [string, string];

  // Impact assessment
  impact_severity: 'low' | 'medium' | 'high';
  impact_description: string;

  // Mitigation
  mitigation_strategy?: string;
  was_mitigated: boolean;
}

export interface DataGapsSummary {
  total_gaps: number;
  critical_gaps: number;

  gaps: DataGap[];

  // Overall data completeness
  completeness_score: number;  // 0-1

  // Recommendations
  recommendations: string[];
}

// ============================================================================
// Confidence Breakdown
// ============================================================================

export interface ConfidenceBreakdown {
  // Overall confidence
  level: ConfidenceLevel;
  score: number;  // 0-1

  // Factor contributions
  factors: {
    factor_name: string;
    contribution: number;  // -1 to 1 (negative = reduces confidence)
    weight: number;
    rationale: string;
  }[];

  // Primary reasons for confidence level
  primary_reasons: string[];

  // What would increase confidence
  improvement_suggestions: string[];
}

// ============================================================================
// Reliability Report (project.md §7.1)
// ============================================================================

export interface ReliabilityReport extends TenantScoped, Timestamps {
  // Identity
  report_id: string;

  // References (can be for a node OR a run)
  node_id?: string;
  run_id?: string;
  project_id: string;

  // Calibration
  calibration: CalibrationScore;

  // Stability
  stability: StabilityScore;

  // Sensitivity
  sensitivity: SensitivitySummary;

  // Drift
  drift: DriftStatus;

  // Data gaps
  data_gaps: DataGapsSummary;

  // Overall confidence
  confidence: ConfidenceBreakdown;

  // Versioning
  methodology_version: string;
  schema_version: string;

  // Computation metadata
  computed_at: string;
  computation_time_ms: number;
}

// ============================================================================
// Anti-Leakage Guardrails (project.md §7.2)
// ============================================================================

export interface TimeCutoffValidation {
  // The cutoff date for historical data
  cutoff_date: string;

  // Validation results
  validation_passed: boolean;

  // Any violations found
  violations: {
    data_source: string;
    data_date: string;
    violation_type: 'future_data' | 'timestamp_missing' | 'suspicious_pattern';
    description: string;
  }[];

  // Data sources checked
  sources_validated: string[];
}

export interface LeakageCheck {
  check_id: string;
  run_id: string;

  // Time cutoff validation
  time_cutoff: TimeCutoffValidation;

  // Deep research data validation
  deep_research_validated: boolean;
  untagged_sources: string[];

  // Overall result
  passed: boolean;
  warnings: string[];

  checked_at: string;
}

// ============================================================================
// Create/Update DTOs
// ============================================================================

export interface ComputeReliabilityInput {
  node_id?: string;
  run_id?: string;

  // What to compute
  include_calibration: boolean;
  include_stability: boolean;
  include_sensitivity: boolean;
  include_drift: boolean;
  include_data_gaps: boolean;

  // Computation parameters
  historical_validation_cutoff?: string;
  stability_seed_count?: number;
  sensitivity_sample_size?: number;
}

export interface UpdateCalibrationInput {
  report_id: string;
  new_validation_run: CalibrationScore['validation_runs'][0];
}

// ============================================================================
// Reliability Summary (for lists/badges)
// ============================================================================

export interface ReliabilitySummary {
  report_id: string;
  node_id?: string;
  run_id?: string;

  // Quick indicators
  confidence_level: ConfidenceLevel;
  confidence_score: number;

  calibration_score: number;
  stability_score: number;

  has_drift_warning: boolean;
  drift_severity: DriftSeverity;

  critical_data_gaps: number;

  computed_at: string;
}

// ============================================================================
// Reliability Comparison (for comparing nodes)
// ============================================================================

export interface ReliabilityComparison {
  base_node_id: string;
  compared_node_ids: string[];

  comparisons: {
    node_id: string;

    confidence_delta: number;
    calibration_delta: number;
    stability_delta: number;

    new_data_gaps: number;
    resolved_data_gaps: number;

    drift_change: 'improved' | 'worsened' | 'unchanged';
  }[];

  summary: string;
}

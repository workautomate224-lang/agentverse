/**
 * Telemetry Contract (Replay Data)
 * Reference: project.md §6.8
 *
 * Telemetry is "playback evidence," not full world state.
 * It enables read-only replay without re-running simulation.
 */

import { Timestamps, TenantScoped, ArtifactRef } from './common';
import { AgentStateVector, AgentLocation } from './agent';

// ============================================================================
// Keyframe Types
// ============================================================================

export interface WorldKeyframe {
  tick: number;
  timestamp: string;  // ISO 8601

  // Global environment state
  environment_state: Record<string, unknown>;

  // Aggregated metrics
  global_metrics: Record<string, number>;

  // Active events at this tick
  active_events: string[];  // event_ids

  // Agent count by status
  agent_counts: {
    total: number;
    active: number;
    by_segment: Record<string, number>;
  };
}

export interface RegionKeyframe {
  tick: number;
  region_id: string;

  // Region-level aggregated state
  aggregated_state: Record<string, number>;

  // Agent distribution
  agent_distribution: Record<string, number>;  // segment_id -> count

  // Regional metrics
  metrics: Record<string, number>;
}

export interface AgentKeyframe {
  tick: number;
  agent_id: string;

  // Full state snapshot
  state_vector: AgentStateVector;
  location: AgentLocation;

  // Is this a key agent we're tracking closely?
  is_key_agent: boolean;
}

// ============================================================================
// Delta Types
// ============================================================================

export type DeltaType =
  | 'agent_state'      // Individual agent state change
  | 'segment_aggregate' // Segment-level aggregated change
  | 'environment'      // Environment variable change
  | 'event_trigger'    // Event triggered
  | 'event_end'        // Event ended
  | 'agent_action'     // Agent took an action
  | 'metric_update';   // Metric value update

export interface TelemetryDelta {
  delta_id: string;
  tick: number;
  delta_type: DeltaType;

  // What changed
  target_id?: string;     // agent_id, segment_id, or variable path
  field_path?: string;    // Specific field that changed
  old_value?: unknown;
  new_value: unknown;

  // Context
  caused_by?: string;     // event_id or action_id that caused this
  region_id?: string;

  // Sampling info
  is_sampled: boolean;    // Was this delta sampled (vs. every delta logged)?
  sample_weight?: number; // For reconstruction
}

// ============================================================================
// Delta Stream
// ============================================================================

export interface DeltaStream {
  // Metadata
  run_id: string;
  start_tick: number;
  end_tick: number;

  // Deltas (ordered by tick)
  deltas: TelemetryDelta[];

  // Sampling info
  sampling_rate: number;
  total_deltas_original: number;
  total_deltas_sampled: number;
}

// ============================================================================
// Metric Time Series
// ============================================================================

export interface MetricTimeSeries {
  metric_name: string;
  unit?: string;

  // Data points (tick -> value)
  data_points: { tick: number; value: number }[];

  // Aggregation info
  aggregation_method?: 'sum' | 'mean' | 'max' | 'min' | 'last';
  region_id?: string;
  segment_id?: string;
}

// ============================================================================
// Event Occurrence Log
// ============================================================================

export interface EventOccurrence {
  event_id: string;
  start_tick: number;
  end_tick?: number;

  // Effect summary
  affected_agent_count: number;
  affected_regions: string[];
  peak_intensity: number;

  // Outcome attribution
  attributed_outcome_delta?: Record<string, number>;
}

// ============================================================================
// Telemetry Index (for efficient queries)
// ============================================================================

export interface TelemetryIndex {
  // By tick (for scrubbing)
  tick_index: {
    tick: number;
    keyframe_offset?: number;  // Offset to nearest keyframe
    delta_range: [number, number];  // Range of delta indices
  }[];

  // By region
  region_index: Record<string, number[]>;  // region_id -> tick indices with data

  // By segment
  segment_index: Record<string, number[]>;  // segment_id -> tick indices with data

  // By key agent
  key_agent_index: Record<string, number[]>;  // agent_id -> tick indices with data

  // Metric availability
  available_metrics: string[];
}

// ============================================================================
// Telemetry (project.md §6.8)
// ============================================================================

export interface Telemetry extends TenantScoped, Timestamps {
  // Identity
  telemetry_id: string;
  run_id: string;
  node_id: string;
  project_id: string;

  // Keyframes
  world_keyframes: WorldKeyframe[];
  region_keyframes: RegionKeyframe[];
  agent_keyframes: AgentKeyframe[];  // Only for key agents

  // Delta stream
  delta_stream: DeltaStream;

  // Metric time series (pre-computed for common metrics)
  metric_series: MetricTimeSeries[];

  // Event log
  event_occurrences: EventOccurrence[];

  // Index for efficient queries
  index: TelemetryIndex;

  // Storage info
  storage_ref: ArtifactRef;  // Reference to blob storage
  size_bytes: number;
  compression: 'none' | 'gzip' | 'zstd';

  // Versioning
  schema_version: string;
}

// ============================================================================
// Telemetry Query Interfaces
// ============================================================================

export interface TelemetryQueryByTick {
  telemetry_id: string;
  tick: number;
  include_keyframe: boolean;
  include_deltas: boolean;
}

export interface TelemetryQueryByRange {
  telemetry_id: string;
  start_tick: number;
  end_tick: number;
  include_keyframes: boolean;
  include_deltas: boolean;
  max_deltas?: number;
}

export interface TelemetryQueryByRegion {
  telemetry_id: string;
  region_id: string;
  start_tick?: number;
  end_tick?: number;
}

export interface TelemetryQueryByAgent {
  telemetry_id: string;
  agent_id: string;
  start_tick?: number;
  end_tick?: number;
}

export interface TelemetryQueryMetric {
  telemetry_id: string;
  metric_name: string;
  start_tick?: number;
  end_tick?: number;
  downsample_factor?: number;  // Return every Nth point
}

// ============================================================================
// Telemetry Response Types
// ============================================================================

export interface TelemetrySlice {
  tick: number;

  // World state at this tick
  world_keyframe?: WorldKeyframe;

  // Deltas that occurred at this tick
  deltas: TelemetryDelta[];

  // Interpolated values (if between keyframes)
  is_interpolated: boolean;
}

export interface TelemetryPlaybackState {
  telemetry_id: string;
  current_tick: number;
  total_ticks: number;

  // Current state (from keyframe + deltas)
  current_world_state: WorldKeyframe;
  current_region_states: Record<string, RegionKeyframe>;

  // Active events
  active_events: string[];

  // Playback metadata
  playback_speed: number;
  is_playing: boolean;
}

// ============================================================================
// Telemetry Summary (for lists)
// ============================================================================

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

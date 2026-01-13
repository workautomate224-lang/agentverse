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

// ============================================================================
// PHASE 5: Capabilities & Spatial Normalization (Telemetry Standardization)
// ============================================================================

/**
 * Telemetry capabilities flags.
 * Phase 5: Enables UI to conditionally render features based on available data.
 */
export interface TelemetryCapabilities {
  /** Whether telemetry contains spatial position data (x/y coordinates) */
  has_spatial: boolean;
  /** Whether telemetry contains event triggers */
  has_events: boolean;
  /** Whether telemetry contains metric data */
  has_metrics: boolean;
}

/**
 * Canonical normalized position format.
 * Phase 5: Standardizes position extraction across different field naming conventions.
 *
 * Supports detection from:
 * - x/y, position_x/position_y, pos_x/pos_y, coord_x/coord_y, loc_x/loc_y
 * - grid_cell, location_id as fallbacks
 */
export interface NormalizedPosition {
  agent_id: string;
  x: number;
  y: number;
  z?: number;
  rotation?: number;
  scale?: number;
  grid_cell?: string;
  location_id?: string;
}

/**
 * Telemetry Index API Response.
 * Phase 5: Enhanced with capabilities, telemetry_schema_version, and additional metadata.
 */
export interface TelemetryIndexResponse {
  run_id: string;
  total_ticks: number;
  keyframe_ticks: number[];
  event_types: string[];
  agent_ids: string[];
  storage_ref: Record<string, unknown>;
  // Phase 5 additions
  capabilities: TelemetryCapabilities;
  telemetry_schema_version: string;
  total_agents: number;
  total_events: number;
  metric_keys: string[];
}

/**
 * Telemetry Slice API Response.
 * Phase 5: Enhanced with normalized_positions and capabilities.
 */
export interface TelemetrySliceResponse {
  run_id: string;
  start_tick: number;
  end_tick: number;
  keyframes: KeyframeResponse[];
  deltas: DeltaResponse[];
  events: EventResponseItem[];
  total_events: number;
  // Phase 5 additions
  normalized_positions: NormalizedPosition[];
  capabilities: TelemetryCapabilities;
  telemetry_schema_version: string;
}

/**
 * Telemetry Summary API Response.
 * Phase 5: Enhanced with capabilities and telemetry_schema_version.
 */
export interface TelemetrySummaryResponse {
  run_id: string;
  total_ticks: number;
  total_events: number;
  total_agents: number;
  event_type_counts: Record<string, number>;
  key_metrics: Record<string, unknown>;
  duration_seconds: number;
  // Phase 5 additions
  capabilities: TelemetryCapabilities;
  telemetry_schema_version: string;
}

/**
 * Keyframe response item in slice.
 */
export interface KeyframeResponse {
  tick: number;
  timestamp: string;
  agent_states: Record<string, unknown>;
  environment_state?: Record<string, unknown>;
  metrics?: Record<string, number>;
  event_count: number;
  // Phase 5: Optional normalized positions for this keyframe
  normalized_positions?: NormalizedPosition[];
}

/**
 * Delta response item in slice.
 */
export interface DeltaResponse {
  tick: number;
  agent_updates: Record<string, unknown>[];
  events_triggered: string[];
  metrics: Record<string, number>;
}

/**
 * Event response item in slice.
 */
export interface EventResponseItem {
  event_id: string;
  tick: number;
  timestamp: string;
  event_type: string;
  agent_id?: string;
  data: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

// ============================================================================
// Spatial Field Aliases (for frontend/backend consistency)
// ============================================================================

/**
 * Spatial field aliases for X coordinate detection.
 * Phase 5: Used by both frontend and backend for consistent spatial extraction.
 */
export const SPATIAL_X_ALIASES = ['x', 'position_x', 'pos_x', 'coord_x', 'loc_x'] as const;

/**
 * Spatial field aliases for Y coordinate detection.
 */
export const SPATIAL_Y_ALIASES = ['y', 'position_y', 'pos_y', 'coord_y', 'loc_y'] as const;

/**
 * Spatial field aliases for Z coordinate detection.
 */
export const SPATIAL_Z_ALIASES = ['z', 'position_z', 'pos_z', 'coord_z', 'loc_z'] as const;

/**
 * Extract spatial position from agent state.
 * Phase 5: Utility function for frontend to extract positions consistently.
 *
 * @param agentId - The agent ID
 * @param state - The agent state object (may contain x/y at top-level or in 'variables')
 * @returns NormalizedPosition if spatial data found, null otherwise
 */
export function extractSpatialPosition(
  agentId: string,
  state: Record<string, unknown>
): NormalizedPosition | null {
  const variables = (state.variables as Record<string, unknown>) ?? {};
  const fieldsToCheck = { ...state, ...variables };

  // Find x value
  let x: number | null = null;
  for (const alias of SPATIAL_X_ALIASES) {
    const val = fieldsToCheck[alias];
    if (typeof val === 'number') {
      x = val;
      break;
    }
  }

  // Find y value
  let y: number | null = null;
  for (const alias of SPATIAL_Y_ALIASES) {
    const val = fieldsToCheck[alias];
    if (typeof val === 'number') {
      y = val;
      break;
    }
  }

  // Check for grid_cell or location_id fallback
  const gridCell = fieldsToCheck.grid_cell as string | undefined;
  const locationId = fieldsToCheck.location_id as string | undefined;

  if (x !== null && y !== null) {
    // Find optional z value
    let z: number | undefined;
    for (const alias of SPATIAL_Z_ALIASES) {
      const val = fieldsToCheck[alias];
      if (typeof val === 'number') {
        z = val;
        break;
      }
    }

    const rotation = typeof fieldsToCheck.rotation === 'number' ? fieldsToCheck.rotation : undefined;
    const scale = typeof fieldsToCheck.scale === 'number' ? fieldsToCheck.scale : undefined;

    return {
      agent_id: agentId,
      x,
      y,
      z,
      rotation,
      scale,
      grid_cell: gridCell,
      location_id: locationId,
    };
  } else if (gridCell || locationId) {
    // Fallback: position with 0,0 if we only have grid/location
    return {
      agent_id: agentId,
      x: 0,
      y: 0,
      grid_cell: gridCell,
      location_id: locationId,
    };
  }

  return null;
}

/**
 * Extract normalized positions from all agent states.
 * Phase 5: Batch extraction for keyframe data.
 *
 * @param agentStates - Map of agent_id to agent state
 * @returns Array of NormalizedPosition for agents with spatial data
 */
export function extractNormalizedPositions(
  agentStates: Record<string, unknown>
): NormalizedPosition[] {
  const positions: NormalizedPosition[] = [];
  for (const [agentId, state] of Object.entries(agentStates)) {
    if (state && typeof state === 'object') {
      const pos = extractSpatialPosition(agentId, state as Record<string, unknown>);
      if (pos) {
        positions.push(pos);
      }
    }
  }
  return positions;
}

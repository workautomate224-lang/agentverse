/**
 * Agent Contract (Runtime Instance)
 * Reference: project.md §6.3
 *
 * Agent is derived from Persona and not necessarily persisted in full.
 * It represents the runtime instance with current state.
 */

import { Timestamps, TenantScoped } from './common';

// ============================================================================
// Social Edge (connections between agents)
// ============================================================================

export interface SocialEdge {
  target_agent_id: string;
  relationship_type: string;  // friend, family, colleague, etc.
  weight: number;             // 0-1, strength of connection
  metadata?: Record<string, unknown>;
}

// ============================================================================
// Agent Location (for 2D placement & aggregation)
// ============================================================================

export interface AgentLocation {
  region_id?: string;
  coordinates?: {
    x: number;
    y: number;
  };
  location_type?: string;  // urban/suburban/rural
}

// ============================================================================
// Agent Memory State (bounded)
// ============================================================================

export interface MemoryState {
  // Recent events witnessed (bounded buffer)
  recent_events: {
    event_id: string;
    tick: number;
    impact: number;
  }[];

  // Belief updates from events
  belief_updates: Record<string, number>;

  // Social interactions memory
  social_interactions: {
    agent_id: string;
    tick: number;
    interaction_type: string;
  }[];

  // Memory capacity limit
  max_events: number;
  max_interactions: number;
}

// ============================================================================
// Agent State Vector (current state)
// ============================================================================

export interface AgentStateVector {
  // Core state variables
  opinion_state: Record<string, number>;      // -1 to 1 per topic
  emotional_state: Record<string, number>;    // 0 to 1 per emotion
  action_propensities: Record<string, number>; // 0 to 1 per action type

  // Behavioral state
  engagement_level: number;  // 0-1
  uncertainty: number;       // 0-1

  // Custom state variables
  custom?: Record<string, number>;
}

// ============================================================================
// Agent (project.md §6.3)
// ============================================================================

export interface Agent extends TenantScoped {
  // Identity
  agent_id: string;
  persona_ref: string;  // persona_id reference

  // Current state
  state_vector: AgentStateVector;

  // Memory (optional, bounded)
  memory_state?: MemoryState;

  // Social connections
  social_edges: SocialEdge[];

  // Location/region for 2D placement
  location: AgentLocation;

  // Run context
  run_id: string;
  current_tick: number;

  // Active status
  is_active: boolean;
}

// ============================================================================
// Agent Segment (for aggregated dynamics)
// ============================================================================

export interface AgentSegment {
  segment_id: string;
  name: string;
  filter_criteria: Record<string, unknown>;
  agent_count: number;
  aggregated_state?: AgentStateVector;  // Averaged state for segment
}

// ============================================================================
// Agent Action (recorded action)
// ============================================================================

export interface AgentAction {
  action_id: string;
  agent_id: string;
  tick: number;
  action_type: string;
  target_id?: string;     // If action targets another agent
  parameters: Record<string, unknown>;
  outcome?: Record<string, unknown>;
}

// ============================================================================
// Agent Snapshot (for telemetry)
// ============================================================================

export interface AgentSnapshot {
  agent_id: string;
  tick: number;
  state_vector: AgentStateVector;
  location: AgentLocation;
  is_key_agent: boolean;
}

// ============================================================================
// Target (for Target Mode - project.md §2)
// ============================================================================

export interface Target {
  target_id: string;
  agent_ref: string;  // References the underlying Agent

  // Decision process state machine
  decision_state: string;
  available_actions: string[];
  constraints: Record<string, unknown>;

  // Goal/objective modeling
  objectives: {
    objective_id: string;
    description: string;
    priority: number;
    progress: number;
  }[];

  // Planning context
  planning_horizon: number;
  risk_tolerance: number;
}

// ============================================================================
// Create/Update DTOs
// ============================================================================

export interface CreateAgentInput {
  persona_ref: string;
  run_id: string;
  location?: AgentLocation;
  initial_state_overrides?: Partial<AgentStateVector>;
}

export interface AgentStateUpdate {
  state_vector_deltas: Partial<AgentStateVector>;
  memory_updates?: {
    add_events?: MemoryState['recent_events'];
    add_interactions?: MemoryState['social_interactions'];
  };
  location_update?: AgentLocation;
}

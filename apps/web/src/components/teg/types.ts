/**
 * TEG (Thought Expansion Graph) Type Definitions
 *
 * Reference: docs/TEG_UNIVERSE_MAP_EXECUTION.md Section 3.2
 */

/**
 * TEG Node Types
 * - OUTCOME_VERIFIED: Verified result from actual runs (baseline/branch)
 * - SCENARIO_DRAFT: Draft scenario (estimated, not yet run)
 * - EVIDENCE: Evidence reference node
 */
export type TEGNodeType = 'OUTCOME_VERIFIED' | 'SCENARIO_DRAFT' | 'EVIDENCE';

/**
 * TEG Node Status
 */
export type TEGNodeStatus = 'DRAFT' | 'QUEUED' | 'RUNNING' | 'DONE' | 'FAILED';

/**
 * TEG Edge Relations
 */
export type TEGEdgeRelation =
  | 'EXPANDS_TO'    // parent -> draft scenario
  | 'RUNS_TO'       // draft scenario -> verified outcome
  | 'FORKS_FROM'    // baseline outcome -> branch outcome
  | 'SUPPORTS'      // evidence supports a claim
  | 'CONFLICTS';    // evidence conflicts with a claim

/**
 * Confidence Level
 */
export type ConfidenceLevel = 'low' | 'medium' | 'high';

/**
 * TEG View Mode
 */
export type TEGViewMode = 'graph' | 'table' | 'raw';

/**
 * Evidence Reference
 */
export interface TEGEvidenceRef {
  evidence_pack_id: string;
  source_url?: string;
  snapshot_time?: string;
  hash?: string;
  temporal_compliance: 'PASS' | 'WARN' | 'FAIL';
}

/**
 * Scenario Patch (for draft scenarios)
 */
export interface TEGScenarioPatch {
  patch_id: string;
  natural_language: string;
  structured_patch?: Record<string, unknown>;
  estimated_delta?: number;
  estimated_confidence?: number;
  rationale_bullets?: string[];
  evidence_refs?: TEGEvidenceRef[];
  cutoff_snapshot_id?: string;
}

/**
 * Verified Outcome Payload
 */
export interface TEGVerifiedPayload {
  primary_outcome_probability?: number;
  outcome_distribution?: Record<string, number>;
  actual_delta?: number;
  uncertainty?: number;
  top_drivers?: Array<{
    name: string;
    impact: number;
    direction: 'positive' | 'negative';
  }>;
  persona_segment_shifts?: Array<{
    segment: string;
    shift: number;
  }>;
  run_manifest_link?: string;
  run_id?: string;
  persona_set_version?: string;
  cutoff_snapshot?: string;
}

/**
 * Draft Scenario Payload
 */
export interface TEGDraftPayload {
  scenario_description: string;
  estimated_delta?: number;
  delta_direction?: 'positive' | 'negative' | 'neutral';
  estimated_confidence?: number;
  confidence_level?: ConfidenceLevel;
  rationale?: string[];
  evidence_refs?: TEGEvidenceRef[];
  scenario_patch?: TEGScenarioPatch;
}

/**
 * Failed Node Payload
 */
export interface TEGFailedPayload {
  stage: string;
  exception_class?: string;
  message: string;
  correlation_id?: string;
  retryable: boolean;
  guidance?: string;
}

/**
 * TEG Node
 */
export interface TEGNode {
  node_id: string;
  project_id: string;
  type: TEGNodeType;
  status: TEGNodeStatus;
  title: string;
  summary?: string;
  created_at: string;
  updated_at?: string;
  parent_node_id?: string | null;

  // Type-dependent payloads
  payload: TEGVerifiedPayload | TEGDraftPayload | TEGFailedPayload | Record<string, unknown>;

  // Links to external resources
  links?: {
    run_ids?: string[];
    manifest_hash?: string;
    persona_version?: string;
    evidence_ids?: string[];
  };

  // UI position (for graph layout)
  position?: { x: number; y: number };
}

/**
 * TEG Edge
 */
export interface TEGEdge {
  edge_id: string;
  project_id: string;
  from_node_id: string;
  to_node_id: string;
  relation: TEGEdgeRelation;
  weight?: number;
  confidence?: number;
}

/**
 * TEG Graph (full response)
 */
export interface TEGGraph {
  graph_id: string;
  project_id: string;
  created_at: string;
  updated_at?: string;
  active_baseline_node_id?: string;
  nodes: TEGNode[];
  edges: TEGEdge[];
}

/**
 * TEG Node Details (enriched for right panel)
 */
export interface TEGNodeDetails extends TEGNode {
  // Additional enriched data
  children_count?: number;
  parent_title?: string;
  evidence_count?: number;
  can_expand?: boolean;
  can_run?: boolean;
}

/**
 * Props for TEG components
 */
export interface TEGCanvasProps {
  nodes: TEGNode[];
  edges: TEGEdge[];
  selectedNodeId?: string | null;
  onNodeSelect: (nodeId: string | null) => void;
  onExpand?: (nodeId: string) => void;
  onRun?: (nodeId: string) => void;
  loading?: boolean;
}

export interface TEGTableProps {
  nodes: TEGNode[];
  selectedNodeId?: string | null;
  onNodeSelect: (nodeId: string | null) => void;
  sortBy?: 'impact' | 'confidence' | 'created' | 'title';
  sortOrder?: 'asc' | 'desc';
  onSortChange?: (sortBy: string, order: 'asc' | 'desc') => void;
  filters?: {
    type?: TEGNodeType[];
    status?: TEGNodeStatus[];
    confidence?: ConfidenceLevel[];
  };
  onFilterChange?: (filters: Record<string, unknown>) => void;
}

export interface TEGRawProps {
  node: TEGNode | null;
  edges?: TEGEdge[];
}

export interface TEGNodeDetailsProps {
  node: TEGNode | null;
  onExpand?: (nodeId: string) => void;
  onRun?: (nodeId: string) => void;
  onEdit?: (nodeId: string) => void;
  onRetry?: (nodeId: string) => void;
  loading?: boolean;
  baselineNode?: TEGNode | null;
}

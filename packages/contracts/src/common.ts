/**
 * Common types and enums shared across all contracts
 * Reference: project.md §6
 */

// ============================================================================
// Versioning (project.md §6.5, §12.1)
// ============================================================================

export interface ArtifactVersion {
  engine_version: string;      // e.g., "1.0.0"
  ruleset_version: string;     // e.g., "1.0.0"
  dataset_version: string;     // e.g., "2024-01-08"
  schema_version: string;      // e.g., "1.0.0"
}

// ============================================================================
// Timestamps
// ============================================================================

export interface Timestamps {
  created_at: string;  // ISO 8601
  updated_at: string;  // ISO 8601
}

// ============================================================================
// Tenant Scoping (project.md §8.1)
// ============================================================================

export interface TenantScoped {
  tenant_id: string;
}

// ============================================================================
// User Roles (project.md §8.2)
// ============================================================================

export type UserRole = 'owner' | 'admin' | 'analyst' | 'viewer';

export interface UserPermissions {
  can_run_simulations: boolean;
  can_edit_personas: boolean;
  can_export_artifacts: boolean;
  can_share_links: boolean;
  can_manage_project: boolean;
}

// ============================================================================
// Status Enums
// ============================================================================

export type RunStatus = 'queued' | 'running' | 'succeeded' | 'failed';

export type ConfidenceLevel = 'high' | 'medium' | 'low';

export type PrivacyLevel = 'private' | 'team' | 'public';

// ============================================================================
// Prediction Cores (project.md §3.1)
// ============================================================================

export type PredictionCore =
  | 'collective_dynamics'   // Society Mode
  | 'targeted_decision'     // Target Mode
  | 'hybrid_strategic';     // Hybrid Mode

// ============================================================================
// References (for linking artifacts)
// ============================================================================

export interface ArtifactRef {
  id: string;
  type: string;
  version?: string;
}

// ============================================================================
// Pagination
// ============================================================================

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  has_more: boolean;
}

// ============================================================================
// API Response Wrappers
// ============================================================================

export interface ApiResponse<T> {
  data: T;
  message?: string;
}

export interface ApiError {
  detail: string;
  code?: string;
  field?: string;
}

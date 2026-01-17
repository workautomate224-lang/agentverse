/**
 * Wizard State Persistence Utility
 *
 * Slice 1C: Dual persistence to localStorage (fallback) and server (source of truth).
 *
 * Provides:
 * - Schema versioning for future migrations
 * - TTL-based expiration (24 hours for localStorage)
 * - Namespaced storage keys
 * - Type-safe interfaces
 * - Server sync with optimistic concurrency control
 * - Debounced autosave (500ms)
 *
 * Key: agentverse:wizard:new_project:v1
 */

// Types
import type { BlueprintDraft } from '@/types/blueprint-v2';
import { api, type WizardState, type WizardStateResponse } from './api';

export interface WizardLLMProvenance {
  provider: string;
  model: string;
  cache_hit: boolean;
  fallback_used: boolean;
  fallback_attempts: number;
  call_id?: string;
  cost_usd?: number;
  timestamp?: string;
  profile_key?: string;
  input_tokens?: number;
  output_tokens?: number;
}

export interface WizardGoalAnalysisResult {
  domain_guess?: string;
  output_type?: string;
  horizon_guess?: string;
  scope_guess?: string;
  goal_summary?: string;
  clarifying_questions?: Array<{
    id: string;
    question: string;
    options: string[];
    rationale: string;
    required?: boolean;
  }>;
  llm_proof?: {
    goal_analysis?: WizardLLMProvenance;
    clarifying_questions?: WizardLLMProvenance;
    risk_assessment?: WizardLLMProvenance;
    blueprint_preview?: WizardLLMProvenance;
    blueprint_generation?: WizardLLMProvenance;
  };
}

export type WizardStage = 'idle' | 'analyzing' | 'clarifying' | 'generating' | 'preview';

export interface WizardPersistedState {
  // Schema metadata
  schemaVersion: number;
  updatedAt: string;  // ISO timestamp

  // Goal input
  goalText: string;

  // Goal analysis results
  goalAnalysisResult: WizardGoalAnalysisResult | null;
  goalAnalysisJobId: string | null;

  // Clarification state
  clarificationAnswers: Record<string, string>;

  // Blueprint state
  blueprintDraft: BlueprintDraft | null;
  blueprintJobId: string | null;

  // UI state
  stage: WizardStage;
  hasCompletedAnalysis: boolean;

  // Active job for resume
  activeJobId: string | null;
  activeJobType: 'goal_analysis' | 'blueprint_build' | null;
}

// Constants
const STORAGE_KEY = 'agentverse:wizard:new_project:v1';
const SCHEMA_VERSION = 1;
const TTL_MS = 24 * 60 * 60 * 1000; // 24 hours

/**
 * Check if we're in a browser environment with localStorage
 */
function isStorageAvailable(): boolean {
  try {
    if (typeof window === 'undefined') return false;
    const test = '__storage_test__';
    window.localStorage.setItem(test, test);
    window.localStorage.removeItem(test);
    return true;
  } catch {
    return false;
  }
}

/**
 * Create default empty state
 */
export function createDefaultWizardState(): WizardPersistedState {
  return {
    schemaVersion: SCHEMA_VERSION,
    updatedAt: new Date().toISOString(),
    goalText: '',
    goalAnalysisResult: null,
    goalAnalysisJobId: null,
    clarificationAnswers: {},
    blueprintDraft: null,
    blueprintJobId: null,
    stage: 'idle',
    hasCompletedAnalysis: false,
    activeJobId: null,
    activeJobType: null,
  };
}

/**
 * Save wizard state to localStorage
 */
export function saveWizardState(state: Partial<WizardPersistedState>): void {
  if (!isStorageAvailable()) return;

  try {
    // Load existing state and merge
    const existing = loadWizardState();
    const merged: WizardPersistedState = {
      ...(existing || createDefaultWizardState()),
      ...state,
      schemaVersion: SCHEMA_VERSION,
      updatedAt: new Date().toISOString(),
    };

    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(merged));
  } catch {
    // Silently fail - don't break the app if storage fails
  }
}

/**
 * Load wizard state from localStorage
 * Returns null if:
 * - No state exists
 * - State is expired (TTL exceeded)
 * - State has incompatible schema version
 */
export function loadWizardState(): WizardPersistedState | null {
  if (!isStorageAvailable()) return null;

  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (!stored) return null;

    const parsed = JSON.parse(stored) as WizardPersistedState;

    // Check schema version
    if (parsed.schemaVersion !== SCHEMA_VERSION) {
      // In future, could add migration logic here
      clearWizardState();
      return null;
    }

    // Check TTL
    const updatedAt = new Date(parsed.updatedAt).getTime();
    const now = Date.now();
    if (now - updatedAt > TTL_MS) {
      clearWizardState();
      return null;
    }

    return parsed;
  } catch {
    // Invalid JSON or other error
    clearWizardState();
    return null;
  }
}

/**
 * Clear wizard state from localStorage
 */
export function clearWizardState(): void {
  if (!isStorageAvailable()) return;

  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Silently fail
  }
}

/**
 * Check if there's a restorable wizard state
 */
export function hasRestorableState(): boolean {
  const state = loadWizardState();
  return state !== null && state.goalText.length > 0;
}

/**
 * Update just the active job tracking
 */
export function updateActiveJob(
  jobId: string | null,
  jobType: 'goal_analysis' | 'blueprint_build' | null
): void {
  saveWizardState({
    activeJobId: jobId,
    activeJobType: jobType,
  });
}

/**
 * Update clarification answers
 */
export function updateClarificationAnswer(questionId: string, answer: string): void {
  const state = loadWizardState();
  if (!state) return;

  saveWizardState({
    clarificationAnswers: {
      ...state.clarificationAnswers,
      [questionId]: answer,
    },
  });
}

/**
 * Get the storage key for debugging purposes
 */
export function getStorageKey(): string {
  return STORAGE_KEY;
}

// =============================================================================
// Slice 1C: Server Sync (Project-level Persistence)
// =============================================================================

/**
 * Track the current draft project ID (set when wizard creates a draft)
 */
let currentDraftProjectId: string | null = null;
let currentWizardStateVersion: number = 0;

// Debounce timer for autosave
let autosaveTimer: ReturnType<typeof setTimeout> | null = null;
const AUTOSAVE_DEBOUNCE_MS = 500;

/**
 * Set the current draft project ID for server sync
 */
export function setDraftProjectId(projectId: string | null, version: number = 0): void {
  currentDraftProjectId = projectId;
  currentWizardStateVersion = version;
}

/**
 * Get the current draft project ID
 */
export function getDraftProjectId(): string | null {
  return currentDraftProjectId;
}

/**
 * Get the current wizard state version
 */
export function getWizardStateVersion(): number {
  return currentWizardStateVersion;
}

/**
 * Convert local WizardPersistedState to server WizardState format
 */
export function toServerWizardState(local: WizardPersistedState): WizardState {
  // Map local stage to server step
  let step: WizardState['step'] = 'goal';
  switch (local.stage) {
    case 'idle':
      step = 'goal';
      break;
    case 'analyzing':
      step = 'analyzing';
      break;
    case 'clarifying':
      step = 'clarify';
      break;
    case 'generating':
      step = 'generating';
      break;
    case 'preview':
      step = 'blueprint_preview';
      break;
  }

  return {
    schema_version: local.schemaVersion,
    step,
    goal_text: local.goalText,
    goal_analysis_result: local.goalAnalysisResult ? {
      goal_summary: local.goalAnalysisResult.goal_summary || '',
      domain_guess: local.goalAnalysisResult.domain_guess || '',
      clarifying_questions: (local.goalAnalysisResult.clarifying_questions || []).map(q => ({
        id: q.id,
        question: q.question,
        options: q.options,
        required: q.required,
      })),
      llm_provenance: local.goalAnalysisResult.llm_proof?.goal_analysis || {
        provider: '',
        model: '',
        cache_hit: false,
        fallback_used: false,
        fallback_attempts: 0,
      },
    } : undefined,
    goal_analysis_job_id: local.goalAnalysisJobId,
    clarification_answers: local.clarificationAnswers,
    blueprint_draft: local.blueprintDraft as unknown as Record<string, unknown> | undefined,
    blueprint_job_id: local.blueprintJobId,
    last_saved_at: local.updatedAt,
  };
}

/**
 * Convert server WizardState to local WizardPersistedState format
 */
export function fromServerWizardState(server: WizardState): WizardPersistedState {
  // Map server step to local stage
  let stage: WizardStage = 'idle';
  switch (server.step) {
    case 'goal':
      stage = 'idle';
      break;
    case 'analyzing':
      stage = 'analyzing';
      break;
    case 'clarify':
      stage = 'clarifying';
      break;
    case 'generating':
      stage = 'generating';
      break;
    case 'blueprint_preview':
    case 'complete':
      stage = 'preview';
      break;
  }

  // Determine active job based on stage and job IDs
  const goalAnalysisJobId = server.goal_analysis_job_id || null;
  const blueprintJobId = server.blueprint_job_id || null;
  let activeJobId: string | null = null;
  let activeJobType: 'goal_analysis' | 'blueprint_build' | null = null;

  if (stage === 'analyzing' && goalAnalysisJobId) {
    activeJobId = goalAnalysisJobId;
    activeJobType = 'goal_analysis';
  } else if (stage === 'generating' && blueprintJobId) {
    activeJobId = blueprintJobId;
    activeJobType = 'blueprint_build';
  }

  return {
    schemaVersion: server.schema_version,
    updatedAt: server.last_saved_at || new Date().toISOString(),
    goalText: server.goal_text,
    goalAnalysisResult: server.goal_analysis_result ? {
      goal_summary: server.goal_analysis_result.goal_summary,
      domain_guess: server.goal_analysis_result.domain_guess,
      clarifying_questions: server.goal_analysis_result.clarifying_questions.map(q => ({
        id: q.id,
        question: q.question,
        options: q.options || [],
        rationale: '',
        required: q.required,
      })),
      llm_proof: {
        goal_analysis: server.goal_analysis_result.llm_provenance,
      },
    } : null,
    goalAnalysisJobId,
    clarificationAnswers: server.clarification_answers as Record<string, string>,
    blueprintDraft: server.blueprint_draft as unknown as BlueprintDraft | null,
    blueprintJobId,
    stage,
    hasCompletedAnalysis: !!server.goal_analysis_result,
    activeJobId,
    activeJobType,
  };
}

/**
 * Autosave wizard state to server with debouncing.
 * Uses optimistic concurrency control (409 on version mismatch).
 * Falls back to localStorage only if server is unavailable.
 */
export async function autosaveToServer(state: Partial<WizardPersistedState>): Promise<boolean> {
  // Always save to localStorage first (fallback)
  saveWizardState(state);

  // If no draft project, skip server sync
  if (!currentDraftProjectId) {
    return false;
  }

  // Clear any pending autosave
  if (autosaveTimer) {
    clearTimeout(autosaveTimer);
  }

  // Debounced server save
  return new Promise((resolve) => {
    autosaveTimer = setTimeout(async () => {
      try {
        const fullState = loadWizardState();
        if (!fullState) {
          resolve(false);
          return;
        }

        const serverState = toServerWizardState(fullState);
        const response = await api.patchWizardState(currentDraftProjectId!, {
          wizard_state: serverState,
          expected_version: currentWizardStateVersion,
        });

        // Update version for next save
        currentWizardStateVersion = response.wizard_state_version;
        resolve(true);
      } catch (error: unknown) {
        // Check for version conflict (409)
        if (error && typeof error === 'object' && 'status' in error && error.status === 409) {
          // Version conflict - someone else updated. Could trigger reload.
          resolve(false);
        }
        // Other errors - keep localStorage as fallback
        resolve(false);
      }
    }, AUTOSAVE_DEBOUNCE_MS);
  });
}

/**
 * Load wizard state from server (source of truth).
 * Falls back to localStorage if server is unavailable.
 */
export async function loadFromServer(projectId: string): Promise<WizardPersistedState | null> {
  try {
    const response: WizardStateResponse = await api.getWizardState(projectId);

    if (response.wizard_state) {
      // Update tracking
      setDraftProjectId(projectId, response.wizard_state_version);

      // Convert and cache to localStorage
      const localState = fromServerWizardState(response.wizard_state);
      saveWizardState(localState);

      return localState;
    }

    return null;
  } catch {
    // Server unavailable - fall back to localStorage
    return loadWizardState();
  }
}

/**
 * Promote draft to active and clear wizard state.
 */
export async function promoteDraftToActive(projectId: string): Promise<boolean> {
  try {
    await api.patchProjectStatus(projectId, 'ACTIVE');
    clearWizardState();
    setDraftProjectId(null, 0);
    return true;
  } catch {
    return false;
  }
}

/**
 * Clear all wizard state (localStorage and server tracking).
 */
export function clearAllWizardState(): void {
  clearWizardState();
  setDraftProjectId(null, 0);
  if (autosaveTimer) {
    clearTimeout(autosaveTimer);
    autosaveTimer = null;
  }
}

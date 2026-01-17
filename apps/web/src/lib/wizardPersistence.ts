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
  userDidSkipClarify: boolean;  // Slice 1D-A: Track if user skipped clarification

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

/**
 * Blueprint Input - canonical structure for LLM blueprint generation.
 * Slice 1D-A: This is what gets sent to the LLM for blueprint generation.
 */
export interface BlueprintInput {
  goal_text: string;
  goal_summary: string;
  domain_guess: string;
  clarifying_questions: Array<{
    id: string;
    question: string;
    answer: string | null;
  }>;
  user_skipped_clarify: boolean;
  generation_context: {
    schema_version: number;
    timestamp: string;
  };
}

/**
 * Build the canonical BlueprintInput from wizard state.
 * Slice 1D-A: Combines goal_text + answers (or empty answers if skipped),
 * strips fields not needed by LLM.
 *
 * @param state The current wizard persisted state
 * @returns BlueprintInput ready for LLM blueprint generation
 */
export function buildBlueprintInput(state: WizardPersistedState): BlueprintInput {
  const goalAnalysis = state.goalAnalysisResult;
  const questions = goalAnalysis?.clarifying_questions || [];

  // Build clarifying questions with answers
  // If user skipped clarification, answers will be null
  const clarifyingQuestionsWithAnswers = questions.map(q => ({
    id: q.id,
    question: q.question,
    answer: state.userDidSkipClarify ? null : (state.clarificationAnswers[q.id] || null),
  }));

  return {
    goal_text: state.goalText,
    goal_summary: goalAnalysis?.goal_summary || '',
    domain_guess: goalAnalysis?.domain_guess || '',
    clarifying_questions: clarifyingQuestionsWithAnswers,
    user_skipped_clarify: state.userDidSkipClarify,
    generation_context: {
      schema_version: state.schemaVersion,
      timestamp: new Date().toISOString(),
    },
  };
}

/**
 * Get the BlueprintInput for the current wizard state.
 * Convenience function that loads from localStorage and builds the input.
 */
export function getCurrentBlueprintInput(): BlueprintInput | null {
  const state = loadWizardState();
  if (!state) return null;
  return buildBlueprintInput(state);
}

// Constants
const STORAGE_KEY_PREFIX = 'agentverse:wizard:project:';
const STORAGE_KEY_SUFFIX = ':v1';
const LEGACY_STORAGE_KEY = 'agentverse:wizard:new_project:v1';
const SCHEMA_VERSION = 1;
const TTL_MS = 24 * 60 * 60 * 1000; // 24 hours

// Module-level state for tracking current draft project
// Moved up to be available for localStorage key functions
let currentDraftProjectId: string | null = null;
let currentWizardStateVersion: number = 0;

/**
 * Get the localStorage key for a specific project.
 * Slice 1D-A: Project-scoped localStorage keys.
 */
function getStorageKeyForProject(projectId: string | null): string {
  if (projectId) {
    return `${STORAGE_KEY_PREFIX}${projectId}${STORAGE_KEY_SUFFIX}`;
  }
  // Fallback to legacy key for backward compatibility during migration
  return LEGACY_STORAGE_KEY;
}

/**
 * Get the current storage key based on active draft project.
 */
function getCurrentStorageKey(): string {
  return getStorageKeyForProject(currentDraftProjectId);
}

/**
 * Clean up localStorage for a specific project.
 * Call this when a project becomes ACTIVE or is deleted.
 * Slice 1D-A requirement.
 */
export function cleanupProjectLocalStorage(projectId: string): void {
  if (!isStorageAvailable()) return;

  try {
    const key = getStorageKeyForProject(projectId);
    window.localStorage.removeItem(key);
  } catch {
    // Silently fail
  }
}

/**
 * Clean up all wizard localStorage entries (for development/testing).
 * Removes both legacy and project-scoped entries.
 */
export function cleanupAllWizardLocalStorage(): void {
  if (!isStorageAvailable()) return;

  try {
    // Remove legacy key
    window.localStorage.removeItem(LEGACY_STORAGE_KEY);

    // Find and remove all project-scoped keys
    const keysToRemove: string[] = [];
    for (let i = 0; i < window.localStorage.length; i++) {
      const key = window.localStorage.key(i);
      if (key && key.startsWith(STORAGE_KEY_PREFIX)) {
        keysToRemove.push(key);
      }
    }
    keysToRemove.forEach(key => window.localStorage.removeItem(key));
  } catch {
    // Silently fail
  }
}

/**
 * Migrate legacy localStorage to project-scoped storage.
 * Called when a draft project is first created.
 */
export function migrateToProjectStorage(projectId: string): void {
  if (!isStorageAvailable()) return;

  try {
    // Check if legacy key has data
    const legacyData = window.localStorage.getItem(LEGACY_STORAGE_KEY);
    if (legacyData) {
      // Copy to project-scoped key
      const projectKey = getStorageKeyForProject(projectId);
      window.localStorage.setItem(projectKey, legacyData);
      // Remove legacy key
      window.localStorage.removeItem(LEGACY_STORAGE_KEY);
    }
  } catch {
    // Silently fail
  }
}

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
    userDidSkipClarify: false,  // Slice 1D-A
    blueprintDraft: null,
    blueprintJobId: null,
    stage: 'idle',
    hasCompletedAnalysis: false,
    activeJobId: null,
    activeJobType: null,
  };
}

/**
 * Save wizard state to localStorage.
 * Slice 1D-A: Uses project-scoped key when draft project exists.
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

    const storageKey = getCurrentStorageKey();
    window.localStorage.setItem(storageKey, JSON.stringify(merged));
  } catch {
    // Silently fail - don't break the app if storage fails
  }
}

/**
 * Load wizard state from localStorage.
 * Slice 1D-A: Uses project-scoped key when draft project exists,
 * with fallback to legacy key for migration.
 *
 * Returns null if:
 * - No state exists
 * - State is expired (TTL exceeded)
 * - State has incompatible schema version
 */
export function loadWizardState(): WizardPersistedState | null {
  if (!isStorageAvailable()) return null;

  try {
    const storageKey = getCurrentStorageKey();
    let stored = window.localStorage.getItem(storageKey);

    // Slice 1D-A: If no project-scoped data, try legacy key as fallback
    if (!stored && currentDraftProjectId) {
      stored = window.localStorage.getItem(LEGACY_STORAGE_KEY);
    }

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
 * Clear wizard state from localStorage.
 * Slice 1D-A: Clears both project-scoped and legacy keys.
 */
export function clearWizardState(): void {
  if (!isStorageAvailable()) return;

  try {
    // Clear project-scoped key if exists
    const projectKey = getCurrentStorageKey();
    window.localStorage.removeItem(projectKey);

    // Also clear legacy key for cleanup
    window.localStorage.removeItem(LEGACY_STORAGE_KEY);
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
  return getCurrentStorageKey();
}

// =============================================================================
// Slice 1C: Server Sync (Project-level Persistence)
// =============================================================================

// Note: currentDraftProjectId and currentWizardStateVersion are now defined
// earlier in the file (after constants) to support localStorage key functions.

// Debounce timer for autosave
let autosaveTimer: ReturnType<typeof setTimeout> | null = null;
const AUTOSAVE_DEBOUNCE_MS = 500;

/**
 * Result of an autosave operation.
 * Slice 1D-A: Enhanced with conflict detection.
 */
export type AutosaveResult = {
  success: boolean;
  status: 'saved' | 'conflict' | 'error' | 'offline' | 'no_project';
  message?: string;
};

// Callback for notifying consumers of autosave results
type AutosaveCallback = (result: AutosaveResult) => void;
let autosaveCallback: AutosaveCallback | null = null;

/**
 * Register a callback to be notified of autosave results.
 * Used by components to update save status indicators.
 */
export function onAutosaveResult(callback: AutosaveCallback | null): void {
  autosaveCallback = callback;
}

/**
 * Set the current draft project ID for server sync.
 * Slice 1D-A: Migrates legacy localStorage to project-scoped storage.
 */
export function setDraftProjectId(projectId: string | null, version: number = 0): void {
  const previousProjectId = currentDraftProjectId;

  currentDraftProjectId = projectId;
  currentWizardStateVersion = version;

  // Slice 1D-A: Migrate legacy localStorage to project-scoped storage
  // when a project ID is first set
  if (projectId && !previousProjectId) {
    migrateToProjectStorage(projectId);
  }
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
    userDidSkipClarify: false,  // Slice 1D-A: Default to false; server doesn't track this yet
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
 *
 * Slice 1D-A: Enhanced to return detailed result and notify via callback.
 */
export async function autosaveToServer(state: Partial<WizardPersistedState>): Promise<AutosaveResult> {
  // Always save to localStorage first (fallback)
  saveWizardState(state);

  // If no draft project, skip server sync
  if (!currentDraftProjectId) {
    const result: AutosaveResult = { success: false, status: 'no_project' };
    autosaveCallback?.(result);
    return result;
  }

  // Clear any pending autosave
  if (autosaveTimer) {
    clearTimeout(autosaveTimer);
  }

  // Debounced server save
  return new Promise((resolve) => {
    autosaveTimer = setTimeout(async () => {
      let result: AutosaveResult;

      try {
        const fullState = loadWizardState();
        if (!fullState) {
          result = { success: false, status: 'error', message: 'No state to save' };
          autosaveCallback?.(result);
          resolve(result);
          return;
        }

        const serverState = toServerWizardState(fullState);
        const response = await api.patchWizardState(currentDraftProjectId!, {
          wizard_state: serverState,
          expected_version: currentWizardStateVersion,
        });

        // Update version for next save
        currentWizardStateVersion = response.wizard_state_version;
        result = { success: true, status: 'saved' };
        autosaveCallback?.(result);
        resolve(result);
      } catch (error: unknown) {
        // Check for version conflict (409)
        if (error && typeof error === 'object' && 'status' in error && error.status === 409) {
          result = {
            success: false,
            status: 'conflict',
            message: 'This draft was updated elsewhere. Reload to continue.',
          };
          autosaveCallback?.(result);
          resolve(result);
          return;
        }

        // Check if offline/network error
        if (error instanceof TypeError && error.message.includes('fetch')) {
          result = { success: false, status: 'offline', message: 'Network unavailable' };
          autosaveCallback?.(result);
          resolve(result);
          return;
        }

        // Other errors
        const message = error instanceof Error ? error.message : 'Save failed';
        result = { success: false, status: 'error', message };
        autosaveCallback?.(result);
        resolve(result);
      }
    }, AUTOSAVE_DEBOUNCE_MS);
  });
}

/**
 * Force an immediate save without debouncing.
 * Used for retry functionality after errors.
 */
export async function forceSaveToServer(): Promise<AutosaveResult> {
  // Cancel any pending debounced save
  if (autosaveTimer) {
    clearTimeout(autosaveTimer);
    autosaveTimer = null;
  }

  if (!currentDraftProjectId) {
    const result: AutosaveResult = { success: false, status: 'no_project' };
    autosaveCallback?.(result);
    return result;
  }

  let result: AutosaveResult;

  try {
    const fullState = loadWizardState();
    if (!fullState) {
      result = { success: false, status: 'error', message: 'No state to save' };
      autosaveCallback?.(result);
      return result;
    }

    const serverState = toServerWizardState(fullState);
    const response = await api.patchWizardState(currentDraftProjectId, {
      wizard_state: serverState,
      expected_version: currentWizardStateVersion,
    });

    currentWizardStateVersion = response.wizard_state_version;
    result = { success: true, status: 'saved' };
    autosaveCallback?.(result);
    return result;
  } catch (error: unknown) {
    if (error && typeof error === 'object' && 'status' in error && error.status === 409) {
      result = {
        success: false,
        status: 'conflict',
        message: 'This draft was updated elsewhere. Reload to continue.',
      };
    } else if (error instanceof TypeError && error.message.includes('fetch')) {
      result = { success: false, status: 'offline', message: 'Network unavailable' };
    } else {
      const message = error instanceof Error ? error.message : 'Save failed';
      result = { success: false, status: 'error', message };
    }
    autosaveCallback?.(result);
    return result;
  }
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
 * Reload wizard state from server after a conflict.
 * Used when a 409 conflict is detected.
 * Returns the fresh state and notifies callback.
 */
export async function reloadAfterConflict(): Promise<WizardPersistedState | null> {
  if (!currentDraftProjectId) {
    return null;
  }

  try {
    const response: WizardStateResponse = await api.getWizardState(currentDraftProjectId);

    if (response.wizard_state) {
      // Update version tracking to latest
      setDraftProjectId(currentDraftProjectId, response.wizard_state_version);

      // Convert and cache to localStorage
      const localState = fromServerWizardState(response.wizard_state);
      saveWizardState(localState);

      // Notify that we're now in sync
      autosaveCallback?.({ success: true, status: 'saved' });

      return localState;
    }

    return null;
  } catch {
    autosaveCallback?.({ success: false, status: 'error', message: 'Failed to reload' });
    return null;
  }
}

/**
 * Promote draft to active and clear wizard state.
 * Slice 1D-A: Explicitly cleans up project-scoped localStorage.
 */
export async function promoteDraftToActive(projectId: string): Promise<boolean> {
  try {
    await api.patchProjectStatus(projectId, 'ACTIVE');

    // Slice 1D-A: Clean up localStorage for this specific project
    cleanupProjectLocalStorage(projectId);

    // Reset tracking state
    setDraftProjectId(null, 0);
    return true;
  } catch {
    return false;
  }
}

/**
 * Clear all wizard state (localStorage and server tracking).
 * Slice 1D-A: Cleans up project-scoped localStorage before resetting.
 */
export function clearAllWizardState(): void {
  // Clean up current project's localStorage before resetting ID
  if (currentDraftProjectId) {
    cleanupProjectLocalStorage(currentDraftProjectId);
  }

  // Also clear any legacy entries
  clearWizardState();

  // Reset tracking state
  setDraftProjectId(null, 0);

  // Cancel pending autosave
  if (autosaveTimer) {
    clearTimeout(autosaveTimer);
    autosaveTimer = null;
  }
}

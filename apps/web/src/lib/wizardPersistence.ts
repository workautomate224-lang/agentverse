/**
 * Wizard State Persistence Utility
 *
 * Provides localStorage persistence for the New Project Wizard with:
 * - Schema versioning for future migrations
 * - TTL-based expiration (24 hours)
 * - Namespaced storage keys
 * - Type-safe interfaces
 *
 * Key: agentverse:wizard:new_project:v1
 */

// Types
import type { BlueprintDraft } from '@/types/blueprint-v2';

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

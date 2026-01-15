/**
 * Blueprint v2 Types
 *
 * Shared type definitions for the Blueprint v2 wizard flow.
 * Reference: blueprint_v2.md §4
 */

// Clarifying question structure (per blueprint_v2.md §2.1.1)
export interface ClarifyingQuestion {
  id: string;
  question: string;
  why_we_ask: string;
  answer_type: 'single_select' | 'multi_select' | 'short_text';
  options?: { value: string; label: string }[];
  required: boolean;
}

// Goal analysis result from /api/goal-analysis
export interface GoalAnalysisResult {
  goal_summary: string;
  domain_guess: 'marketing' | 'political' | 'finance' | 'social' | 'technology' | 'custom';
  output_type: 'distribution' | 'point' | 'ranked' | 'paths';
  horizon_guess: string;
  scope_guess: string;
  primary_drivers: string[];
  clarifying_questions: ClarifyingQuestion[];
  risk_notes: string[];
  processing_time_ms: number;
}

// Input slot definition (per blueprint_v2.md §4.3)
export interface InputSlot {
  slot_id: string;
  name: string;
  description: string;
  required_level: 'required' | 'recommended' | 'optional';
  data_type?: string;
  example_sources?: string[];
}

// Section task definition (per blueprint_v2.md §4.4)
export interface SectionTask {
  task_id: string;
  title: string;
  why_it_matters: string;
  linked_slots?: string[];
  completion_criteria?: string;
}

// Blueprint draft structure (per blueprint_v2.md §4)
export interface BlueprintDraft {
  // Project Profile (§4.1)
  project_profile: {
    goal_text: string;
    goal_summary: string;
    domain_guess: string;
    output_type: string;
    horizon: string;
    scope: string;
    success_metrics: string[];
  };
  // Strategy (§4.2)
  strategy: {
    chosen_core: 'collective' | 'target' | 'hybrid';
    primary_drivers: string[];
    required_modules: string[];
  };
  // Input Slots Contract (§4.3)
  input_slots: InputSlot[];
  // Section Task Map (§4.4)
  section_tasks: Record<string, SectionTask[]>;
  // Clarification data
  clarification_answers: Record<string, string | string[]>;
  // Metadata
  generated_at?: string;
  processing_time_ms?: number;
  warnings: string[];
}

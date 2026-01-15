'use client';

/**
 * GoalAssistantPanel - Blueprint v2/v3
 *
 * This component handles the goal analysis flow in Step 1 of the Create Project wizard.
 * It manages: Analyze Goal → Clarifying Questions → Blueprint Preview
 *
 * Reference: blueprint_v3.md §2.1.1
 *
 * PHASE 2 (blueprint_v3): Job deduplication
 * - Uses useRef to track request-in-progress and prevent duplicate clicks
 * - AbortController for cleanup on unmount or new request
 * - Buttons disabled while processing
 */

import { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import {
  Sparkles,
  Loader2,
  ChevronRight,
  ChevronDown,
  CheckCircle,
  AlertCircle,
  Info,
  Brain,
  FileText,
  Save,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { ExitConfirmationModal, useExitConfirmation } from '@/components/pil/ExitConfirmationModal';
import { SaveDraftIndicator, SaveStatus } from '@/components/pil/SaveDraftIndicator';
import type {
  ClarifyingQuestion,
  GoalAnalysisResult,
  BlueprintDraft,
} from '@/types/blueprint-v2';

// PHASE 3 (blueprint_v3): Local storage key for wizard state persistence
const WIZARD_STATE_KEY = 'agentverse_wizard_state';

// PHASE 3: Interface for persisted wizard state
interface PersistedWizardState {
  goalText: string;
  stage: Stage;
  analysisResult: GoalAnalysisResult | null;
  answers: Record<string, string | string[]>;
  blueprintDraft: BlueprintDraft | null;
  savedAt: string;
}

// PHASE 3: Helper to save wizard state to localStorage
function saveWizardState(state: PersistedWizardState): void {
  try {
    localStorage.setItem(WIZARD_STATE_KEY, JSON.stringify(state));
  } catch {
    // Ignore localStorage errors (private browsing, quota exceeded, etc.)
  }
}

// PHASE 3: Helper to load wizard state from localStorage
function loadWizardState(): PersistedWizardState | null {
  try {
    const saved = localStorage.getItem(WIZARD_STATE_KEY);
    if (!saved) return null;
    return JSON.parse(saved);
  } catch {
    return null;
  }
}

// PHASE 3: Helper to clear wizard state from localStorage
function clearWizardState(): void {
  try {
    localStorage.removeItem(WIZARD_STATE_KEY);
  } catch {
    // Ignore localStorage errors
  }
}

interface GoalAssistantPanelProps {
  goalText: string;
  onBlueprintReady: (blueprint: BlueprintDraft) => void;
  onAnalysisStart?: () => void;
  className?: string;
}

type Stage =
  | 'idle'
  | 'analyzing'
  | 'clarifying'
  | 'generating_blueprint'
  | 'preview';

export function GoalAssistantPanel({
  goalText,
  onBlueprintReady,
  onAnalysisStart,
  className,
}: GoalAssistantPanelProps) {
  // State
  const [stage, setStage] = useState<Stage>('idle');
  const [analysisResult, setAnalysisResult] = useState<GoalAnalysisResult | null>(null);
  const [answers, setAnswers] = useState<Record<string, string | string[]>>({});
  const [blueprintDraft, setBlueprintDraft] = useState<BlueprintDraft | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedQuestion, setExpandedQuestion] = useState<string | null>(null);

  // PHASE 3 (blueprint_v3): State persistence
  const [saveStatus, setSaveStatus] = useState<SaveStatus>('idle');
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null);
  const [showExitModal, setShowExitModal] = useState(false);
  const [hasRestoredState, setHasRestoredState] = useState(false);

  // PHASE 2 (blueprint_v3): Job deduplication refs
  // Track if a request is in progress to prevent duplicate clicks
  const requestInProgressRef = useRef<boolean>(false);
  // AbortController for cleanup on unmount or when starting a new request
  const abortControllerRef = useRef<AbortController | null>(null);

  // PHASE 3: Determine if there are unsaved changes (analysis in progress or clarifying)
  const hasUnsavedChanges = useMemo(() => {
    return stage === 'analyzing' || stage === 'clarifying' || stage === 'generating_blueprint';
  }, [stage]);

  // PHASE 3: Use exit confirmation hook for browser navigation
  useExitConfirmation({ hasUnsavedChanges });

  // PHASE 3: Restore state from localStorage on mount
  useEffect(() => {
    if (hasRestoredState) return;

    const saved = loadWizardState();
    if (saved && saved.goalText === goalText) {
      // Restore only if the goal text matches (same session)
      // Don't restore 'analyzing' or 'generating_blueprint' stages - restart those
      if (saved.stage === 'clarifying' || saved.stage === 'preview') {
        setStage(saved.stage);
        setAnalysisResult(saved.analysisResult);
        setAnswers(saved.answers);
        setBlueprintDraft(saved.blueprintDraft);
        setLastSavedAt(new Date(saved.savedAt));
        setSaveStatus('saved');

        // If we restored a completed blueprint, notify parent
        if (saved.blueprintDraft && saved.stage === 'preview') {
          onBlueprintReady(saved.blueprintDraft);
        }
      }
    }
    setHasRestoredState(true);
  }, [goalText, hasRestoredState, onBlueprintReady]);

  // PHASE 3: Auto-save state when it changes
  useEffect(() => {
    // Don't save during transitions (analyzing, generating)
    if (stage === 'idle' || stage === 'analyzing' || stage === 'generating_blueprint') {
      return;
    }

    // Debounce save by 500ms
    const timer = setTimeout(() => {
      setSaveStatus('saving');
      const state: PersistedWizardState = {
        goalText,
        stage,
        analysisResult,
        answers,
        blueprintDraft,
        savedAt: new Date().toISOString(),
      };
      saveWizardState(state);
      setLastSavedAt(new Date());
      setSaveStatus('saved');
    }, 500);

    return () => clearTimeout(timer);
  }, [goalText, stage, analysisResult, answers, blueprintDraft]);

  // PHASE 3: Clear state when blueprint is finalized (preview stage)
  useEffect(() => {
    if (stage === 'preview' && blueprintDraft) {
      // Clear saved state since blueprint is ready
      clearWizardState();
    }
  }, [stage, blueprintDraft]);

  // Cleanup abort controller on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  // Analyze goal
  // PHASE 2 (blueprint_v3): Added deduplication to prevent duplicate clicks
  const handleAnalyzeGoal = useCallback(async () => {
    if (!goalText || goalText.trim().length < 10) {
      setError('Please enter at least 10 characters for your goal');
      return;
    }

    // PHASE 2: Prevent duplicate requests
    if (requestInProgressRef.current) {
      return; // Already processing, ignore click
    }

    // Abort any previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Create new abort controller for this request
    const abortController = new AbortController();
    abortControllerRef.current = abortController;
    requestInProgressRef.current = true;

    setStage('analyzing');
    setError(null);
    onAnalysisStart?.();

    try {
      const response = await fetch('/api/goal-analysis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal_text: goalText }),
        signal: abortController.signal,
      });

      if (!response.ok) {
        throw new Error('Failed to analyze goal');
      }

      const result: GoalAnalysisResult = await response.json();
      setAnalysisResult(result);

      if (result.clarifying_questions.length > 0) {
        setStage('clarifying');
      } else {
        // No questions, go directly to blueprint generation
        await generateBlueprint(result, {});
      }
    } catch (err) {
      // Don't show error if request was aborted
      if (err instanceof Error && err.name === 'AbortError') {
        return;
      }
      setError(err instanceof Error ? err.message : 'Analysis failed');
      setStage('idle');
    } finally {
      requestInProgressRef.current = false;
    }
  }, [goalText, onAnalysisStart]);

  // Skip clarification and generate blueprint directly
  // PHASE 2 (blueprint_v3): Added deduplication to prevent duplicate clicks
  const handleSkipClarify = useCallback(async () => {
    // PHASE 2: Prevent duplicate requests
    if (requestInProgressRef.current) {
      return; // Already processing, ignore click
    }

    // Abort any previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Create new abort controller for this request
    const abortController = new AbortController();
    abortControllerRef.current = abortController;
    requestInProgressRef.current = true;

    setStage('generating_blueprint');
    setError(null);

    try {
      const response = await fetch('/api/goal-analysis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal_text: goalText, skip_clarification: true }),
        signal: abortController.signal,
      });

      if (!response.ok) {
        throw new Error('Failed to analyze goal');
      }

      const result: GoalAnalysisResult = await response.json();
      await generateBlueprint(result, {});
    } catch (err) {
      // Don't show error if request was aborted
      if (err instanceof Error && err.name === 'AbortError') {
        return;
      }
      setError(err instanceof Error ? err.message : 'Failed to generate blueprint');
      setStage('idle');
    } finally {
      requestInProgressRef.current = false;
    }
  }, [goalText]);

  // Generate blueprint from analysis + answers
  // PHASE 2 (blueprint_v3): Uses shared abort controller for request cleanup
  const generateBlueprint = useCallback(async (
    analysis: GoalAnalysisResult,
    clarificationAnswers: Record<string, string | string[]>
  ) => {
    setStage('generating_blueprint');

    // Use existing abort controller if set (from outer function)
    // or create a new one if called directly
    const abortController = abortControllerRef.current || new AbortController();
    if (!abortControllerRef.current) {
      abortControllerRef.current = abortController;
    }

    try {
      const response = await fetch('/api/blueprint-draft', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          goal_text: goalText,
          goal_summary: analysis.goal_summary,
          domain_guess: analysis.domain_guess,
          clarification_answers: clarificationAnswers,
        }),
        signal: abortController.signal,
      });

      if (!response.ok) {
        throw new Error('Failed to generate blueprint');
      }

      const blueprint: BlueprintDraft = await response.json();
      setBlueprintDraft(blueprint);
      setStage('preview');
      onBlueprintReady(blueprint);
    } catch (err) {
      // Don't show error if request was aborted
      if (err instanceof Error && err.name === 'AbortError') {
        return;
      }
      setError(err instanceof Error ? err.message : 'Blueprint generation failed');
      setStage('clarifying');
    }
  }, [goalText, onBlueprintReady]);

  // Handle answer change
  const handleAnswerChange = useCallback((questionId: string, value: string | string[]) => {
    setAnswers(prev => ({ ...prev, [questionId]: value }));
  }, []);

  // Submit clarification answers
  // PHASE 2 (blueprint_v3): Added deduplication to prevent duplicate submissions
  const handleSubmitAnswers = useCallback(async () => {
    if (!analysisResult) return;

    // PHASE 2: Prevent duplicate requests
    if (requestInProgressRef.current) {
      return; // Already processing, ignore click
    }

    // Abort any previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Create new abort controller for this request
    const abortController = new AbortController();
    abortControllerRef.current = abortController;
    requestInProgressRef.current = true;

    try {
      await generateBlueprint(analysisResult, answers);
    } finally {
      requestInProgressRef.current = false;
    }
  }, [analysisResult, answers, generateBlueprint]);

  // Check if all required questions are answered
  const allRequiredAnswered = analysisResult?.clarifying_questions
    .filter(q => q.required)
    .every(q => {
      const answer = answers[q.id];
      return answer && (Array.isArray(answer) ? answer.length > 0 : answer.trim().length > 0);
    }) ?? false;

  return (
    <div className={cn('border border-white/10 bg-white/5', className)}>
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/10 flex items-center gap-2">
        <Brain className="w-4 h-4 text-cyan-400" />
        <span className="text-sm font-mono font-bold text-white">Goal Assistant</span>

        {/* PHASE 3: Save status indicator */}
        {stage === 'clarifying' && (
          <SaveDraftIndicator
            status={saveStatus}
            lastSavedAt={lastSavedAt}
            compact
            className="ml-2"
          />
        )}

        {stage !== 'idle' && (
          <span className="ml-auto text-[10px] font-mono text-white/40 uppercase">
            {stage === 'analyzing' && 'Analyzing...'}
            {stage === 'clarifying' && 'Clarification'}
            {stage === 'generating_blueprint' && 'Generating...'}
            {stage === 'preview' && 'Blueprint Ready'}
          </span>
        )}
      </div>

      {/* PHASE 3: Exit confirmation modal */}
      <ExitConfirmationModal
        open={showExitModal}
        onOpenChange={setShowExitModal}
        onConfirmExit={() => {
          clearWizardState();
          setShowExitModal(false);
        }}
        onSaveAndExit={() => {
          // Save is auto-done, just close
          setShowExitModal(false);
        }}
        title="Analysis in Progress"
        description="You have an analysis in progress. Your answers have been auto-saved and will be restored when you return."
      />

      {/* Content */}
      <div className="p-4">
        {/* Idle State - Action Buttons */}
        {stage === 'idle' && (
          <div className="space-y-4">
            <p className="text-xs font-mono text-white/60">
              Analyze your goal to get personalized clarifying questions and generate an optimal blueprint.
            </p>
            <div className="flex flex-col sm:flex-row gap-2">
              <Button
                onClick={handleAnalyzeGoal}
                disabled={goalText.trim().length < 10}
                className="bg-cyan-500 hover:bg-cyan-600 text-black font-mono text-xs flex-1"
              >
                <Sparkles className="w-3 h-3 mr-2" />
                Analyze Goal
              </Button>
              <Button
                onClick={handleSkipClarify}
                disabled={goalText.trim().length < 10}
                variant="outline"
                className="border-white/20 text-white/70 hover:bg-white/10 font-mono text-xs"
              >
                Skip & Generate Blueprint
              </Button>
            </div>
            {error && (
              <div className="flex items-center gap-2 text-red-400 text-xs font-mono">
                <AlertCircle className="w-3 h-3" />
                {error}
              </div>
            )}
          </div>
        )}

        {/* Analyzing State */}
        {stage === 'analyzing' && (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <Loader2 className="w-5 h-5 text-cyan-400 animate-spin" />
              <div>
                <p className="text-sm font-mono text-white">Analyzing your goal...</p>
                <p className="text-xs font-mono text-white/40">Understanding context and generating questions</p>
              </div>
            </div>
            <div className="h-2 bg-white/10 overflow-hidden">
              <div className="h-full bg-cyan-500 animate-pulse" style={{ width: '60%' }} />
            </div>
          </div>
        )}

        {/* Clarifying Questions */}
        {stage === 'clarifying' && analysisResult && (
          <div className="space-y-4">
            {/* Analysis Summary */}
            <div className="p-3 bg-cyan-500/10 border border-cyan-500/30">
              <div className="flex items-center gap-2 mb-2">
                <CheckCircle className="w-4 h-4 text-cyan-400" />
                <span className="text-xs font-mono font-bold text-cyan-400">ANALYSIS COMPLETE</span>
              </div>
              <p className="text-xs font-mono text-white/80">{analysisResult.goal_summary}</p>
              <div className="flex flex-wrap gap-2 mt-2">
                <span className="px-2 py-0.5 bg-white/10 text-[10px] font-mono text-white/60">
                  {analysisResult.domain_guess.toUpperCase()}
                </span>
                <span className="px-2 py-0.5 bg-white/10 text-[10px] font-mono text-white/60">
                  {analysisResult.horizon_guess}
                </span>
                <span className="px-2 py-0.5 bg-white/10 text-[10px] font-mono text-white/60">
                  {analysisResult.scope_guess}
                </span>
              </div>
            </div>

            {/* Questions */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono text-white/40 uppercase">
                  Clarifying Questions ({analysisResult.clarifying_questions.length})
                </span>
                <span className="text-[10px] font-mono text-white/30">
                  * Required
                </span>
              </div>

              {analysisResult.clarifying_questions.map((q) => (
                <div key={q.id} className="border border-white/10 bg-black/30">
                  {/* Question Header */}
                  <button
                    onClick={() => setExpandedQuestion(expandedQuestion === q.id ? null : q.id)}
                    className="w-full px-3 py-2 flex items-center gap-2 text-left hover:bg-white/5"
                  >
                    <span className="text-xs font-mono text-white flex-1">
                      {q.question}
                      {q.required && <span className="text-cyan-400 ml-1">*</span>}
                    </span>
                    {answers[q.id] && (
                      <CheckCircle className="w-3 h-3 text-green-400 flex-shrink-0" />
                    )}
                    {expandedQuestion === q.id ? (
                      <ChevronDown className="w-4 h-4 text-white/40 flex-shrink-0" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-white/40 flex-shrink-0" />
                    )}
                  </button>

                  {/* Expanded Content */}
                  {expandedQuestion === q.id && (
                    <div className="px-3 pb-3 space-y-2">
                      {/* Why we ask */}
                      <div className="flex items-start gap-2 p-2 bg-white/5">
                        <Info className="w-3 h-3 text-cyan-400 flex-shrink-0 mt-0.5" />
                        <p className="text-[10px] font-mono text-white/50">{q.why_we_ask}</p>
                      </div>

                      {/* Answer Input */}
                      {q.answer_type === 'single_select' && q.options && (
                        <div className="space-y-1">
                          {q.options.map((opt) => (
                            <button
                              key={opt.value}
                              onClick={() => handleAnswerChange(q.id, opt.value)}
                              className={cn(
                                'w-full px-3 py-2 text-left text-xs font-mono border transition-all',
                                answers[q.id] === opt.value
                                  ? 'bg-cyan-500/20 border-cyan-500/50 text-cyan-400'
                                  : 'bg-white/5 border-white/10 text-white/70 hover:bg-white/10'
                              )}
                            >
                              {opt.label}
                            </button>
                          ))}
                        </div>
                      )}

                      {q.answer_type === 'multi_select' && q.options && (
                        <div className="space-y-1">
                          {q.options.map((opt) => {
                            const selected = (answers[q.id] as string[] || []).includes(opt.value);
                            return (
                              <button
                                key={opt.value}
                                onClick={() => {
                                  const current = (answers[q.id] as string[]) || [];
                                  const updated = selected
                                    ? current.filter(v => v !== opt.value)
                                    : [...current, opt.value];
                                  handleAnswerChange(q.id, updated);
                                }}
                                className={cn(
                                  'w-full px-3 py-2 text-left text-xs font-mono border transition-all',
                                  selected
                                    ? 'bg-cyan-500/20 border-cyan-500/50 text-cyan-400'
                                    : 'bg-white/5 border-white/10 text-white/70 hover:bg-white/10'
                                )}
                              >
                                <span className="mr-2">{selected ? '☑' : '☐'}</span>
                                {opt.label}
                              </button>
                            );
                          })}
                        </div>
                      )}

                      {q.answer_type === 'short_text' && (
                        <input
                          type="text"
                          value={(answers[q.id] as string) || ''}
                          onChange={(e) => handleAnswerChange(q.id, e.target.value)}
                          placeholder="Enter your answer..."
                          className="w-full px-3 py-2 bg-black border border-white/10 text-xs font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-cyan-500/50"
                        />
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Submit Button */}
            <div className="flex gap-2 pt-2">
              <Button
                onClick={handleSubmitAnswers}
                disabled={!allRequiredAnswered}
                className="flex-1 bg-cyan-500 hover:bg-cyan-600 text-black font-mono text-xs"
              >
                <FileText className="w-3 h-3 mr-2" />
                Generate Blueprint Preview
              </Button>
            </div>

            {error && (
              <div className="flex items-center gap-2 text-red-400 text-xs font-mono">
                <AlertCircle className="w-3 h-3" />
                {error}
              </div>
            )}
          </div>
        )}

        {/* Generating Blueprint */}
        {stage === 'generating_blueprint' && (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <Loader2 className="w-5 h-5 text-cyan-400 animate-spin" />
              <div>
                <p className="text-sm font-mono text-white">Building blueprint...</p>
                <p className="text-xs font-mono text-white/40">Creating project structure and tasks</p>
              </div>
            </div>
            <div className="h-2 bg-white/10 overflow-hidden">
              <div className="h-full bg-cyan-500 animate-pulse" style={{ width: '80%' }} />
            </div>
          </div>
        )}

        {/* Blueprint Preview */}
        {stage === 'preview' && blueprintDraft && (
          <BlueprintPreview blueprint={blueprintDraft} />
        )}
      </div>
    </div>
  );
}

// Blueprint Preview Sub-component
function BlueprintPreview({ blueprint }: { blueprint: BlueprintDraft }) {
  const [expanded, setExpanded] = useState<string | null>('profile');

  const requiredSlots = blueprint.input_slots.filter(s => s.required_level === 'required');
  const recommendedSlots = blueprint.input_slots.filter(s => s.required_level === 'recommended');

  return (
    <div className="space-y-3">
      {/* Success Header */}
      <div className="p-3 bg-green-500/10 border border-green-500/30">
        <div className="flex items-center gap-2">
          <CheckCircle className="w-4 h-4 text-green-400" />
          <span className="text-xs font-mono font-bold text-green-400">BLUEPRINT READY</span>
        </div>
        <p className="text-xs font-mono text-white/60 mt-1">
          Your project blueprint has been generated. Continue to the next step.
        </p>
      </div>

      {/* Warnings */}
      {blueprint.warnings.length > 0 && (
        <div className="p-2 bg-amber-500/10 border border-amber-500/30">
          {blueprint.warnings.map((w, i) => (
            <p key={i} className="text-[10px] font-mono text-amber-400 flex items-center gap-1">
              <AlertCircle className="w-3 h-3" />
              {w}
            </p>
          ))}
        </div>
      )}

      {/* Collapsible Sections */}
      <div className="space-y-2">
        {/* Project Profile */}
        <div className="border border-white/10">
          <button
            onClick={() => setExpanded(expanded === 'profile' ? null : 'profile')}
            className="w-full px-3 py-2 flex items-center gap-2 hover:bg-white/5"
          >
            <span className="text-xs font-mono font-bold text-white flex-1 text-left">
              Project Profile
            </span>
            {expanded === 'profile' ? (
              <ChevronDown className="w-4 h-4 text-white/40" />
            ) : (
              <ChevronRight className="w-4 h-4 text-white/40" />
            )}
          </button>
          {expanded === 'profile' && (
            <div className="px-3 pb-3 space-y-2">
              <div className="grid grid-cols-2 gap-2 text-[10px] font-mono">
                <div>
                  <span className="text-white/40">Domain:</span>
                  <span className="text-white ml-1">{blueprint.project_profile.domain_guess}</span>
                </div>
                <div>
                  <span className="text-white/40">Output:</span>
                  <span className="text-white ml-1">{blueprint.project_profile.output_type}</span>
                </div>
                <div>
                  <span className="text-white/40">Horizon:</span>
                  <span className="text-white ml-1">{blueprint.project_profile.horizon}</span>
                </div>
                <div>
                  <span className="text-white/40">Scope:</span>
                  <span className="text-white ml-1">{blueprint.project_profile.scope}</span>
                </div>
              </div>
              <p className="text-[10px] font-mono text-white/60">
                {blueprint.project_profile.goal_summary}
              </p>
            </div>
          )}
        </div>

        {/* Strategy */}
        <div className="border border-white/10">
          <button
            onClick={() => setExpanded(expanded === 'strategy' ? null : 'strategy')}
            className="w-full px-3 py-2 flex items-center gap-2 hover:bg-white/5"
          >
            <span className="text-xs font-mono font-bold text-white flex-1 text-left">
              Strategy
            </span>
            <span className="px-2 py-0.5 bg-cyan-500/20 text-[10px] font-mono text-cyan-400 uppercase">
              {blueprint.strategy.chosen_core}
            </span>
            {expanded === 'strategy' ? (
              <ChevronDown className="w-4 h-4 text-white/40" />
            ) : (
              <ChevronRight className="w-4 h-4 text-white/40" />
            )}
          </button>
          {expanded === 'strategy' && (
            <div className="px-3 pb-3 space-y-2">
              <div>
                <span className="text-[10px] font-mono text-white/40">Primary Drivers:</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {blueprint.strategy.primary_drivers.map((d, i) => (
                    <span key={i} className="px-2 py-0.5 bg-white/10 text-[10px] font-mono text-white/70">
                      {d}
                    </span>
                  ))}
                </div>
              </div>
              <div>
                <span className="text-[10px] font-mono text-white/40">Required Modules:</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {blueprint.strategy.required_modules.map((m, i) => (
                    <span key={i} className="px-2 py-0.5 bg-purple-500/20 text-[10px] font-mono text-purple-400">
                      {m}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Required Inputs */}
        <div className="border border-white/10">
          <button
            onClick={() => setExpanded(expanded === 'inputs' ? null : 'inputs')}
            className="w-full px-3 py-2 flex items-center gap-2 hover:bg-white/5"
          >
            <span className="text-xs font-mono font-bold text-white flex-1 text-left">
              Required Inputs
            </span>
            <span className="text-[10px] font-mono text-white/40">
              {requiredSlots.length} required, {recommendedSlots.length} recommended
            </span>
            {expanded === 'inputs' ? (
              <ChevronDown className="w-4 h-4 text-white/40" />
            ) : (
              <ChevronRight className="w-4 h-4 text-white/40" />
            )}
          </button>
          {expanded === 'inputs' && (
            <div className="px-3 pb-3 space-y-2">
              {requiredSlots.map((slot) => (
                <div key={slot.slot_id} className="flex items-start gap-2">
                  <span className="w-1.5 h-1.5 mt-1.5 bg-red-400" />
                  <div>
                    <span className="text-xs font-mono text-white">{slot.name}</span>
                    <p className="text-[10px] font-mono text-white/40">{slot.description}</p>
                  </div>
                </div>
              ))}
              {recommendedSlots.length > 0 && (
                <>
                  <div className="border-t border-white/10 my-2" />
                  {recommendedSlots.map((slot) => (
                    <div key={slot.slot_id} className="flex items-start gap-2">
                      <span className="w-1.5 h-1.5 mt-1.5 bg-amber-400" />
                      <div>
                        <span className="text-xs font-mono text-white/70">{slot.name}</span>
                        <p className="text-[10px] font-mono text-white/30">{slot.description}</p>
                      </div>
                    </div>
                  ))}
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

'use client';

/**
 * GoalAssistantPanel - Blueprint v2/v3
 *
 * This component handles the goal analysis flow in Step 1 of the Create Project wizard.
 * It manages: Analyze Goal → Clarifying Questions → Blueprint Preview
 *
 * Reference: blueprint_v3.md §2.1.1
 *
 * VERTICAL SLICE #1: Background Job Integration
 * - Uses PIL job hooks for background processing
 * - Job appears in both Step 1 inline AND global Active Jobs widget
 * - Resume behavior: job ID persisted to localStorage, recovered on return/refresh
 * - Deduplication via job state (prevents duplicate job creation)
 */

import { useState, useCallback, useEffect, useMemo } from 'react';
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
  XCircle,
  Clock,
  RefreshCw,
  Zap,
  Database,
  Shield,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { ExitConfirmationModal, useExitConfirmation } from '@/components/pil/ExitConfirmationModal';
import { SaveDraftIndicator, SaveStatus } from '@/components/pil/SaveDraftIndicator';
import { useCreatePILJob, usePILJob, useCancelPILJob, useRetryPILJob } from '@/hooks/useApi';
import type { PILJobStatus } from '@/lib/api';
import type {
  ClarifyingQuestion,
  GoalAnalysisResult,
  BlueprintDraft,
  LLMProof,
} from '@/types/blueprint-v2';

// VERTICAL SLICE #1: Local storage key for wizard state persistence
const WIZARD_STATE_KEY = 'agentverse_wizard_state';

// VERTICAL SLICE #1: Interface for persisted wizard state with job IDs
interface PersistedWizardState {
  goalText: string;
  stage: Stage;
  // Job IDs for resume behavior
  goalAnalysisJobId: string | null;
  blueprintJobId: string | null;
  // Results
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
  // VERTICAL SLICE #1: Core state
  const [stage, setStage] = useState<Stage>('idle');
  const [analysisResult, setAnalysisResult] = useState<GoalAnalysisResult | null>(null);
  const [answers, setAnswers] = useState<Record<string, string | string[]>>({});
  const [blueprintDraft, setBlueprintDraft] = useState<BlueprintDraft | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedQuestion, setExpandedQuestion] = useState<string | null>(null);

  // VERTICAL SLICE #1: Job IDs for background processing
  const [goalAnalysisJobId, setGoalAnalysisJobId] = useState<string | null>(null);
  const [blueprintJobId, setBlueprintJobId] = useState<string | null>(null);

  // VERTICAL SLICE #1: State persistence
  const [saveStatus, setSaveStatus] = useState<SaveStatus>('idle');
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null);
  const [showExitModal, setShowExitModal] = useState(false);
  const [hasRestoredState, setHasRestoredState] = useState(false);

  // VERTICAL SLICE #1: PIL Job hooks for background processing
  const createJobMutation = useCreatePILJob();
  const cancelJobMutation = useCancelPILJob();
  const retryJobMutation = useRetryPILJob();

  // Poll goal analysis job status (auto-refreshes while active)
  const { data: goalAnalysisJob } = usePILJob(goalAnalysisJobId || '');
  // Poll blueprint job status (auto-refreshes while active)
  const { data: blueprintJob } = usePILJob(blueprintJobId || '');

  // VERTICAL SLICE #1: Determine if there are unsaved changes
  const hasUnsavedChanges = useMemo(() => {
    return stage === 'analyzing' || stage === 'clarifying' || stage === 'generating_blueprint';
  }, [stage]);

  // VERTICAL SLICE #1: Use exit confirmation hook for browser navigation
  useExitConfirmation({ hasUnsavedChanges });

  // VERTICAL SLICE #1: Compute current job status for display
  const currentJobStatus: PILJobStatus | null = useMemo(() => {
    if (stage === 'analyzing' && goalAnalysisJob) {
      return goalAnalysisJob.status;
    }
    if (stage === 'generating_blueprint' && blueprintJob) {
      return blueprintJob.status;
    }
    return null;
  }, [stage, goalAnalysisJob, blueprintJob]);

  // VERTICAL SLICE #1: Compute current job for display
  const currentJob = useMemo(() => {
    if (stage === 'analyzing' && goalAnalysisJob) return goalAnalysisJob;
    if (stage === 'generating_blueprint' && blueprintJob) return blueprintJob;
    return null;
  }, [stage, goalAnalysisJob, blueprintJob]);

  // VERTICAL SLICE #1: Restore state from localStorage on mount (includes job IDs for resume)
  useEffect(() => {
    if (hasRestoredState) return;

    const saved = loadWizardState();
    if (saved && saved.goalText === goalText) {
      // Restore state including job IDs for resume behavior
      setStage(saved.stage);
      setAnalysisResult(saved.analysisResult);
      setAnswers(saved.answers);
      setBlueprintDraft(saved.blueprintDraft);
      setGoalAnalysisJobId(saved.goalAnalysisJobId);
      setBlueprintJobId(saved.blueprintJobId);
      setLastSavedAt(new Date(saved.savedAt));
      setSaveStatus('saved');

      // If we restored a completed blueprint, notify parent
      if (saved.blueprintDraft && saved.stage === 'preview') {
        onBlueprintReady(saved.blueprintDraft);
      }
    }
    setHasRestoredState(true);
  }, [goalText, hasRestoredState, onBlueprintReady]);

  // VERTICAL SLICE #1: Handle goal analysis job completion
  useEffect(() => {
    if (!goalAnalysisJob || stage !== 'analyzing') return;

    if (goalAnalysisJob.status === 'succeeded') {
      // Extract analysis result from job output
      const output = goalAnalysisJob.result as unknown as GoalAnalysisResult | undefined;
      if (output) {
        setAnalysisResult(output);
        if (output.clarifying_questions && output.clarifying_questions.length > 0) {
          setStage('clarifying');
        } else {
          // No questions, generate blueprint directly
          handleGenerateBlueprint(output, {});
        }
      } else {
        setError('Job completed but no analysis result found');
        setStage('idle');
      }
    } else if (goalAnalysisJob.status === 'failed') {
      setError(goalAnalysisJob.error_message || 'Goal analysis failed');
      // Stay in analyzing stage to show retry option
    }
  }, [goalAnalysisJob, stage]);

  // VERTICAL SLICE #1: Handle blueprint job completion
  useEffect(() => {
    if (!blueprintJob || stage !== 'generating_blueprint') return;

    if (blueprintJob.status === 'succeeded') {
      // Extract blueprint from job output
      const output = blueprintJob.result as unknown as BlueprintDraft | undefined;
      if (output) {
        setBlueprintDraft(output);
        setStage('preview');
        onBlueprintReady(output);
      } else {
        setError('Job completed but no blueprint found');
        setStage('clarifying');
      }
    } else if (blueprintJob.status === 'failed') {
      setError(blueprintJob.error_message || 'Blueprint generation failed');
      // Stay in generating_blueprint stage to show retry option
    }
  }, [blueprintJob, stage, onBlueprintReady]);

  // VERTICAL SLICE #1: Auto-save state when it changes (including job IDs)
  useEffect(() => {
    // Don't save if in idle state with no data
    if (stage === 'idle' && !goalAnalysisJobId && !blueprintJobId) {
      return;
    }

    // Debounce save by 500ms
    const timer = setTimeout(() => {
      setSaveStatus('saving');
      const state: PersistedWizardState = {
        goalText,
        stage,
        goalAnalysisJobId,
        blueprintJobId,
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
  }, [goalText, stage, goalAnalysisJobId, blueprintJobId, analysisResult, answers, blueprintDraft]);

  // VERTICAL SLICE #1: Clear state when blueprint is finalized (preview stage)
  useEffect(() => {
    if (stage === 'preview' && blueprintDraft) {
      // Clear saved state since blueprint is ready
      clearWizardState();
    }
  }, [stage, blueprintDraft]);

  // VERTICAL SLICE #1: Analyze goal using background job
  const handleAnalyzeGoal = useCallback(async () => {
    if (!goalText || goalText.trim().length < 10) {
      setError('Please enter at least 10 characters for your goal');
      return;
    }

    // Prevent duplicate job creation
    if (createJobMutation.isPending || (goalAnalysisJob && (goalAnalysisJob.status === 'queued' || goalAnalysisJob.status === 'running'))) {
      return;
    }

    setStage('analyzing');
    setError(null);
    onAnalysisStart?.();

    try {
      // Create goal_analysis job via PIL job system
      const job = await createJobMutation.mutateAsync({
        job_type: 'goal_analysis',
        job_name: 'Goal Analysis',
        input_params: {
          goal_text: goalText,
          skip_clarification: false,
        },
      });

      // Store job ID for polling and resume
      setGoalAnalysisJobId(job.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start analysis');
      setStage('idle');
    }
  }, [goalText, onAnalysisStart, createJobMutation, goalAnalysisJob]);

  // VERTICAL SLICE #1: Skip clarification and generate blueprint directly using background job
  const handleSkipClarify = useCallback(async () => {
    // Prevent duplicate job creation
    if (createJobMutation.isPending || (blueprintJob && (blueprintJob.status === 'queued' || blueprintJob.status === 'running'))) {
      return;
    }

    setStage('generating_blueprint');
    setError(null);

    try {
      // Create blueprint_build job directly (skip clarification)
      const job = await createJobMutation.mutateAsync({
        job_type: 'blueprint_build',
        job_name: 'Blueprint Generation (Skip Clarify)',
        input_params: {
          goal_text: goalText,
          skip_clarification: true,
          clarification_answers: {},
        },
      });

      // Store job ID for polling and resume
      setBlueprintJobId(job.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start blueprint generation');
      setStage('idle');
    }
  }, [goalText, createJobMutation, blueprintJob]);

  // VERTICAL SLICE #1: Generate blueprint from analysis + answers using background job
  const handleGenerateBlueprint = useCallback(async (
    analysis: GoalAnalysisResult,
    clarificationAnswers: Record<string, string | string[]>
  ) => {
    // Prevent duplicate job creation
    if (createJobMutation.isPending || (blueprintJob && (blueprintJob.status === 'queued' || blueprintJob.status === 'running'))) {
      return;
    }

    setStage('generating_blueprint');
    setError(null);

    try {
      // Create blueprint_build job via PIL job system
      const job = await createJobMutation.mutateAsync({
        job_type: 'blueprint_build',
        job_name: 'Blueprint Generation',
        input_params: {
          goal_text: goalText,
          goal_summary: analysis.goal_summary,
          domain_guess: analysis.domain_guess,
          clarification_answers: clarificationAnswers,
        },
      });

      // Store job ID for polling and resume
      setBlueprintJobId(job.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start blueprint generation');
      setStage('clarifying');
    }
  }, [goalText, createJobMutation, blueprintJob]);

  // VERTICAL SLICE #1: Cancel current job
  const handleCancelJob = useCallback(async () => {
    const jobId = stage === 'analyzing' ? goalAnalysisJobId : blueprintJobId;
    if (!jobId) return;

    try {
      await cancelJobMutation.mutateAsync(jobId);
      setStage('idle');
      setGoalAnalysisJobId(null);
      setBlueprintJobId(null);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to cancel job');
    }
  }, [stage, goalAnalysisJobId, blueprintJobId, cancelJobMutation]);

  // VERTICAL SLICE #1: Retry failed job
  const handleRetryJob = useCallback(async () => {
    const jobId = stage === 'analyzing' ? goalAnalysisJobId : blueprintJobId;
    if (!jobId) return;

    try {
      setError(null);
      await retryJobMutation.mutateAsync(jobId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to retry job');
    }
  }, [stage, goalAnalysisJobId, blueprintJobId, retryJobMutation]);

  // Handle answer change
  const handleAnswerChange = useCallback((questionId: string, value: string | string[]) => {
    setAnswers(prev => ({ ...prev, [questionId]: value }));
  }, []);

  // VERTICAL SLICE #1: Submit clarification answers using background job
  const handleSubmitAnswers = useCallback(async () => {
    if (!analysisResult) return;
    await handleGenerateBlueprint(analysisResult, answers);
  }, [analysisResult, answers, handleGenerateBlueprint]);

  // Check if all required questions are answered
  const allRequiredAnswered = (analysisResult?.clarifying_questions || [])
    .filter(q => q.required)
    .every(q => {
      const answer = answers[q.id];
      return answer && (Array.isArray(answer) ? answer.length > 0 : answer.trim().length > 0);
    });

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

        {/* VERTICAL SLICE #1: Job status badge in header */}
        {stage !== 'idle' && (
          <span className={cn(
            "ml-auto text-[10px] font-mono uppercase px-2 py-0.5",
            currentJobStatus === 'queued' && 'bg-amber-500/20 text-amber-400',
            currentJobStatus === 'running' && 'bg-cyan-500/20 text-cyan-400',
            currentJobStatus === 'succeeded' && 'bg-green-500/20 text-green-400',
            currentJobStatus === 'failed' && 'bg-red-500/20 text-red-400',
            !currentJobStatus && 'text-white/40'
          )}>
            {stage === 'analyzing' && (currentJobStatus || 'Analyzing')}
            {stage === 'clarifying' && 'Clarification'}
            {stage === 'generating_blueprint' && (currentJobStatus || 'Generating')}
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

        {/* VERTICAL SLICE #1: Analyzing State with Job Status */}
        {stage === 'analyzing' && (
          <div className="space-y-4">
            {/* Job Status Display */}
            <JobStatusDisplay
              job={goalAnalysisJob}
              jobType="Goal Analysis"
              onCancel={handleCancelJob}
              onRetry={handleRetryJob}
              isRetrying={retryJobMutation.isPending}
              isCancelling={cancelJobMutation.isPending}
            />
            {error && (
              <div className="flex items-center gap-2 text-red-400 text-xs font-mono">
                <AlertCircle className="w-3 h-3" />
                {error}
              </div>
            )}
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

              {/* Slice 1A: LLM Provenance Display */}
              {analysisResult.llm_proof?.goal_analysis && (
                <div className="mt-3 pt-3 border-t border-white/10">
                  <div className="flex items-center gap-1.5 mb-2">
                    <Shield className="w-3 h-3 text-green-400" />
                    <span className="text-[10px] font-mono font-bold text-green-400 uppercase">LLM Provenance</span>
                  </div>
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[10px] font-mono">
                    <div className="flex items-center gap-1.5">
                      <Zap className="w-2.5 h-2.5 text-cyan-400" />
                      <span className="text-white/50">Provider:</span>
                      <span className="text-cyan-400">{analysisResult.llm_proof.goal_analysis.provider || 'openrouter'}</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Database className="w-2.5 h-2.5 text-cyan-400" />
                      <span className="text-white/50">Model:</span>
                      <span className="text-cyan-400">{analysisResult.llm_proof.goal_analysis.model}</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-white/50">Cache:</span>
                      <span className={analysisResult.llm_proof.goal_analysis.cache_hit ? 'text-yellow-400' : 'text-green-400'}>
                        {analysisResult.llm_proof.goal_analysis.cache_hit ? 'Hit' : 'Bypassed'}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-white/50">Fallback:</span>
                      <span className={analysisResult.llm_proof.goal_analysis.fallback_used ? 'text-red-400' : 'text-green-400'}>
                        {analysisResult.llm_proof.goal_analysis.fallback_used ? 'Yes' : 'No'}
                      </span>
                    </div>
                  </div>
                </div>
              )}
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

                      {/* Support both 'short_text' and 'short_input' for compatibility */}
                      {(q.answer_type === 'short_text' || q.answer_type === 'short_input') && (
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

        {/* VERTICAL SLICE #1: Generating Blueprint with Job Status */}
        {stage === 'generating_blueprint' && (
          <div className="space-y-4">
            {/* Job Status Display */}
            <JobStatusDisplay
              job={blueprintJob}
              jobType="Blueprint Generation"
              onCancel={handleCancelJob}
              onRetry={handleRetryJob}
              isRetrying={retryJobMutation.isPending}
              isCancelling={cancelJobMutation.isPending}
            />
            {error && (
              <div className="flex items-center gap-2 text-red-400 text-xs font-mono">
                <AlertCircle className="w-3 h-3" />
                {error}
              </div>
            )}
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

// VERTICAL SLICE #1: Job Status Display Sub-component
interface JobStatusDisplayProps {
  job: {
    id: string;
    status: PILJobStatus;
    progress_percent: number;
    stage_name: string | null;
    stage_message: string | null;
    error_message: string | null;
  } | undefined;
  jobType: string;
  onCancel: () => void;
  onRetry: () => void;
  isRetrying: boolean;
  isCancelling: boolean;
}

function JobStatusDisplay({
  job,
  jobType,
  onCancel,
  onRetry,
  isRetrying,
  isCancelling,
}: JobStatusDisplayProps) {
  // Status configuration
  const statusConfig: Record<PILJobStatus, { icon: React.ReactNode; color: string; bgColor: string; label: string }> = {
    queued: {
      icon: <Clock className="w-4 h-4" />,
      color: 'text-amber-400',
      bgColor: 'bg-amber-500/10 border-amber-500/30',
      label: 'QUEUED',
    },
    running: {
      icon: <Loader2 className="w-4 h-4 animate-spin" />,
      color: 'text-cyan-400',
      bgColor: 'bg-cyan-500/10 border-cyan-500/30',
      label: 'RUNNING',
    },
    succeeded: {
      icon: <CheckCircle className="w-4 h-4" />,
      color: 'text-green-400',
      bgColor: 'bg-green-500/10 border-green-500/30',
      label: 'SUCCEEDED',
    },
    failed: {
      icon: <XCircle className="w-4 h-4" />,
      color: 'text-red-400',
      bgColor: 'bg-red-500/10 border-red-500/30',
      label: 'FAILED',
    },
    cancelled: {
      icon: <XCircle className="w-4 h-4" />,
      color: 'text-gray-400',
      bgColor: 'bg-gray-500/10 border-gray-500/30',
      label: 'CANCELLED',
    },
  };

  // If no job yet, show loading state
  if (!job) {
    return (
      <div className="p-3 bg-white/5 border border-white/10">
        <div className="flex items-center gap-3">
          <Loader2 className="w-4 h-4 text-white/40 animate-spin" />
          <div>
            <p className="text-xs font-mono text-white/60">Starting {jobType}...</p>
            <p className="text-[10px] font-mono text-white/30">Creating job...</p>
          </div>
        </div>
      </div>
    );
  }

  const config = statusConfig[job.status];
  const isActive = job.status === 'queued' || job.status === 'running';
  const isFailed = job.status === 'failed';

  return (
    <div className={cn('p-3 border', config.bgColor)}>
      {/* Header with status */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className={config.color}>{config.icon}</span>
          <span className={cn('text-xs font-mono font-bold', config.color)}>
            {config.label}
          </span>
        </div>
        <span className="text-[10px] font-mono text-white/40">
          Job: {job.id.slice(0, 8)}...
        </span>
      </div>

      {/* Job info */}
      <div className="space-y-2">
        <p className="text-sm font-mono text-white">{jobType}</p>
        {job.stage_message && (
          <p className="text-xs font-mono text-white/60">{job.stage_message}</p>
        )}
        {job.stage_name && (
          <p className="text-[10px] font-mono text-white/40">Stage: {job.stage_name}</p>
        )}
      </div>

      {/* Progress bar for active jobs */}
      {isActive && (
        <div className="mt-3">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] font-mono text-white/40">Progress</span>
            <span className="text-[10px] font-mono text-white/60">{job.progress_percent}%</span>
          </div>
          <div className="h-2 bg-white/10 overflow-hidden">
            <div
              className={cn('h-full transition-all duration-500', config.color.replace('text-', 'bg-'))}
              style={{ width: `${Math.max(job.progress_percent, 10)}%` }}
            />
          </div>
        </div>
      )}

      {/* Error message for failed jobs */}
      {isFailed && job.error_message && (
        <div className="mt-2 p-2 bg-red-500/10 border border-red-500/20">
          <p className="text-[10px] font-mono text-red-400">{job.error_message}</p>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-2 mt-3">
        {isActive && (
          <Button
            onClick={onCancel}
            disabled={isCancelling}
            variant="outline"
            size="sm"
            className="border-white/20 text-white/70 hover:bg-white/10 font-mono text-[10px]"
          >
            {isCancelling ? (
              <>
                <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                Cancelling...
              </>
            ) : (
              <>
                <XCircle className="w-3 h-3 mr-1" />
                Cancel
              </>
            )}
          </Button>
        )}
        {isFailed && (
          <Button
            onClick={onRetry}
            disabled={isRetrying}
            className="bg-cyan-500 hover:bg-cyan-600 text-black font-mono text-[10px]"
            size="sm"
          >
            {isRetrying ? (
              <>
                <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                Retrying...
              </>
            ) : (
              <>
                <RefreshCw className="w-3 h-3 mr-1" />
                Retry
              </>
            )}
          </Button>
        )}
      </div>
    </div>
  );
}

// Blueprint Preview Sub-component
function BlueprintPreview({ blueprint }: { blueprint: BlueprintDraft }) {
  const [expanded, setExpanded] = useState<string | null>('profile');

  // Safe defaults for all potentially undefined fields
  const inputSlots = blueprint.input_slots || [];
  const requiredSlots = inputSlots.filter(s => s.required_level === 'required');
  const recommendedSlots = inputSlots.filter(s => s.required_level === 'recommended');
  const warnings = blueprint.warnings || [];
  const projectProfile = blueprint.project_profile || {
    domain_guess: 'generic',
    output_type: 'prediction',
    horizon: 'medium',
    scope: 'standard',
    goal_summary: 'No summary available',
    goal_text: '',
    success_metrics: [],
  };
  const strategy = blueprint.strategy || {
    chosen_core: 'ensemble',
    primary_drivers: [],
    required_modules: [],
  };

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
      {warnings.length > 0 && (
        <div className="p-2 bg-amber-500/10 border border-amber-500/30">
          {warnings.map((w, i) => (
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
                  <span className="text-white ml-1">{projectProfile.domain_guess}</span>
                </div>
                <div>
                  <span className="text-white/40">Output:</span>
                  <span className="text-white ml-1">{projectProfile.output_type}</span>
                </div>
                <div>
                  <span className="text-white/40">Horizon:</span>
                  <span className="text-white ml-1">{projectProfile.horizon}</span>
                </div>
                <div>
                  <span className="text-white/40">Scope:</span>
                  <span className="text-white ml-1">{projectProfile.scope}</span>
                </div>
              </div>
              <p className="text-[10px] font-mono text-white/60">
                {projectProfile.goal_summary}
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
              {strategy.chosen_core}
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
                  {strategy.primary_drivers.map((d, i) => (
                    <span key={i} className="px-2 py-0.5 bg-white/10 text-[10px] font-mono text-white/70">
                      {d}
                    </span>
                  ))}
                </div>
              </div>
              <div>
                <span className="text-[10px] font-mono text-white/40">Required Modules:</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {strategy.required_modules.map((m, i) => (
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

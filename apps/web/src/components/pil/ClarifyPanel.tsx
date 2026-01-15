'use client';

/**
 * Clarify Panel Component
 * Reference: blueprint.md §4.2
 *
 * Displays clarifying questions from goal analysis and collects user answers.
 * Submits answers to trigger blueprint build job.
 */

import { useState, useCallback, useMemo, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  MessageSquare,
  ChevronRight,
  ChevronLeft,
  Check,
  AlertCircle,
  Sparkles,
  Send,
  Loader2,
  HelpCircle,
  Info,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import {
  useActiveBlueprint,
  useGoalAnalysisResult,
  useSubmitClarificationAnswers,
  useActivePILJobs,
} from '@/hooks/useApi';
import type {
  ClarifyingQuestion,
  GoalAnalysisResult,
  Blueprint,
} from '@/lib/api';
import { PILJobProgress } from './PILJobProgress';

// Question type configurations
const QUESTION_TYPE_CONFIG = {
  single_select: {
    label: 'Choose one',
    icon: Check,
  },
  multi_select: {
    label: 'Choose multiple',
    icon: Check,
  },
  short_input: {
    label: 'Short answer',
    icon: MessageSquare,
  },
  long_input: {
    label: 'Detailed answer',
    icon: MessageSquare,
  },
};

interface ClarifyPanelProps {
  /** Project ID */
  projectId: string;
  /** Callback when clarification is complete */
  onComplete?: (blueprint: Blueprint) => void;
  /** Callback when user skips clarification */
  onSkip?: () => void;
  /** Additional CSS classes */
  className?: string;
}

export function ClarifyPanel({
  projectId,
  onComplete,
  onSkip,
  className,
}: ClarifyPanelProps) {
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [multiSelectAnswers, setMultiSelectAnswers] = useState<Record<string, string[]>>({});
  const [submitting, setSubmitting] = useState(false);
  const [buildJobId, setBuildJobId] = useState<string | null>(null);

  // Fetch blueprint and goal analysis data
  const { data: blueprint, isLoading: blueprintLoading } = useActiveBlueprint(projectId);
  const { data: goalAnalysis, isLoading: analysisLoading } = useGoalAnalysisResult(projectId);
  const { data: activeJobs } = useActivePILJobs(projectId);
  const submitMutation = useSubmitClarificationAnswers();

  // Check if there's an active goal_analysis job
  const activeGoalAnalysisJob = useMemo(() => {
    return activeJobs?.find(
      (job) => job.job_type === 'goal_analysis' && ['queued', 'running'].includes(job.status)
    );
  }, [activeJobs]);

  // Check if there's an active blueprint_build job
  const activeBlueprintBuildJob = useMemo(() => {
    return activeJobs?.find(
      (job) => job.job_type === 'blueprint_build' && ['queued', 'running'].includes(job.status)
    );
  }, [activeJobs]);

  // Get questions from goal analysis
  const questions = useMemo(() => {
    return goalAnalysis?.clarifying_questions || [];
  }, [goalAnalysis]);

  const currentQuestion = questions[currentQuestionIndex];
  const totalQuestions = questions.length;
  const isFirstQuestion = currentQuestionIndex === 0;
  const isLastQuestion = currentQuestionIndex === totalQuestions - 1;

  // Calculate completion percentage
  const completedCount = useMemo(() => {
    return questions.filter((q) => {
      if (q.type === 'multi_select') {
        return multiSelectAnswers[q.id]?.length > 0;
      }
      return answers[q.id]?.trim();
    }).length;
  }, [questions, answers, multiSelectAnswers]);

  const completionPercent = totalQuestions > 0 ? Math.round((completedCount / totalQuestions) * 100) : 0;

  // Check if current question is answered
  const isCurrentAnswered = useMemo(() => {
    if (!currentQuestion) return false;
    if (currentQuestion.type === 'multi_select') {
      return multiSelectAnswers[currentQuestion.id]?.length > 0;
    }
    return !!answers[currentQuestion.id]?.trim();
  }, [currentQuestion, answers, multiSelectAnswers]);

  // Check if all required questions are answered
  const allRequiredAnswered = useMemo(() => {
    return questions.every((q) => {
      if (!q.required) return true;
      if (q.type === 'multi_select') {
        return multiSelectAnswers[q.id]?.length > 0;
      }
      return !!answers[q.id]?.trim();
    });
  }, [questions, answers, multiSelectAnswers]);

  // Handle single select answer
  const handleSingleSelect = useCallback((questionId: string, value: string) => {
    setAnswers((prev) => ({ ...prev, [questionId]: value }));
  }, []);

  // Handle multi select answer
  const handleMultiSelect = useCallback((questionId: string, value: string) => {
    setMultiSelectAnswers((prev) => {
      const current = prev[questionId] || [];
      const isSelected = current.includes(value);
      const updated = isSelected
        ? current.filter((v) => v !== value)
        : [...current, value];
      return { ...prev, [questionId]: updated };
    });
  }, []);

  // Handle text input
  const handleTextInput = useCallback((questionId: string, value: string) => {
    setAnswers((prev) => ({ ...prev, [questionId]: value }));
  }, []);

  // Navigate questions
  const goToNext = useCallback(() => {
    if (!isLastQuestion) {
      setCurrentQuestionIndex((i) => i + 1);
    }
  }, [isLastQuestion]);

  const goToPrevious = useCallback(() => {
    if (!isFirstQuestion) {
      setCurrentQuestionIndex((i) => i - 1);
    }
  }, [isFirstQuestion]);

  // Submit all answers
  const handleSubmit = useCallback(async () => {
    if (!blueprint) return;

    setSubmitting(true);
    try {
      // Merge answers and multi-select answers
      const mergedAnswers: Record<string, string> = { ...answers };
      Object.entries(multiSelectAnswers).forEach(([key, values]) => {
        if (values.length > 0) {
          mergedAnswers[key] = values.join(', ');
        }
      });

      const result = await submitMutation.mutateAsync({
        blueprintId: blueprint.id,
        data: { clarification_answers: mergedAnswers },
      });

      if (result.job_id) {
        setBuildJobId(result.job_id);
      }
    } catch (error) {
      // Error handled by mutation
    } finally {
      setSubmitting(false);
    }
  }, [blueprint, answers, multiSelectAnswers, submitMutation]);

  // Handle blueprint build job completion
  const handleBuildComplete = useCallback(
    (job: { status: string }) => {
      if (onComplete && blueprint) {
        onComplete(blueprint);
      }
    },
    [onComplete, blueprint]
  );

  // Loading states
  if (blueprintLoading || analysisLoading) {
    return (
      <div className={cn('flex items-center justify-center p-8', className)}>
        <Loader2 className="h-6 w-6 animate-spin text-cyan-400" />
        <span className="ml-3 text-sm text-gray-400 font-mono">Loading...</span>
      </div>
    );
  }

  // Show active goal analysis job progress
  if (activeGoalAnalysisJob) {
    return (
      <div className={cn('space-y-4', className)}>
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 rounded bg-cyan-400/10 border border-cyan-400/30">
            <Sparkles className="h-5 w-5 text-cyan-400" />
          </div>
          <div>
            <h3 className="text-sm font-mono font-medium text-white">
              Analyzing Your Goals
            </h3>
            <p className="text-xs text-gray-400 font-mono">
              AI is processing your project goals to generate clarifying questions
            </p>
          </div>
        </div>
        <PILJobProgress
          jobId={activeGoalAnalysisJob.id}
          mode="full"
          showCancel={false}
        />
      </div>
    );
  }

  // Show blueprint build progress
  if (buildJobId || activeBlueprintBuildJob) {
    const jobId = buildJobId || activeBlueprintBuildJob?.id;
    return (
      <div className={cn('space-y-4', className)}>
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 rounded bg-green-400/10 border border-green-400/30">
            <Check className="h-5 w-5 text-green-400" />
          </div>
          <div>
            <h3 className="text-sm font-mono font-medium text-white">
              Building Your Blueprint
            </h3>
            <p className="text-xs text-gray-400 font-mono">
              Creating data slots and tasks based on your answers
            </p>
          </div>
        </div>
        {jobId && (
          <PILJobProgress
            jobId={jobId}
            mode="full"
            showCancel={false}
            onComplete={handleBuildComplete}
          />
        )}
      </div>
    );
  }

  // No questions available
  if (!goalAnalysis || questions.length === 0) {
    return (
      <div className={cn('p-6 rounded border border-white/10 bg-white/5', className)}>
        <div className="flex items-start gap-3">
          <Info className="h-5 w-5 text-cyan-400 mt-0.5" />
          <div>
            <h3 className="text-sm font-mono font-medium text-white mb-1">
              No Clarification Needed
            </h3>
            <p className="text-xs text-gray-400 font-mono">
              Your project goals are clear enough to generate a blueprint.
              You can proceed to set up your data and scenarios.
            </p>
            {onSkip && (
              <Button
                variant="outline"
                size="sm"
                className="mt-3 text-xs font-mono border-cyan-400/30 text-cyan-400 hover:bg-cyan-400/10"
                onClick={onSkip}
              >
                Continue to Overview
              </Button>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={cn('space-y-6', className)}>
      {/* Header with progress */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded bg-purple-400/10 border border-purple-400/30">
            <HelpCircle className="h-5 w-5 text-purple-400" />
          </div>
          <div>
            <h3 className="text-sm font-mono font-medium text-white">
              Clarify Your Goals
            </h3>
            <p className="text-xs text-gray-400 font-mono">
              Answer a few questions to help us understand your project better
            </p>
          </div>
        </div>
        <div className="text-right">
          <div className="text-xs text-gray-400 font-mono mb-1">
            {completedCount} of {totalQuestions} answered
          </div>
          <Progress value={completionPercent} className="w-24 h-1.5" />
        </div>
      </div>

      {/* Goal summary from analysis */}
      {goalAnalysis?.goal_summary && (
        <div className="p-4 rounded border border-cyan-400/30 bg-cyan-400/5">
          <div className="flex items-start gap-2">
            <Sparkles className="h-4 w-4 text-cyan-400 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-xs text-cyan-400 font-mono font-medium mb-1">
                AI Understanding
              </p>
              <p className="text-sm text-gray-300 font-mono">
                {goalAnalysis.goal_summary}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Question navigation dots */}
      <div className="flex items-center justify-center gap-2">
        {questions.map((q, index) => {
          const isAnswered =
            q.type === 'multi_select'
              ? multiSelectAnswers[q.id]?.length > 0
              : !!answers[q.id]?.trim();
          const isCurrent = index === currentQuestionIndex;

          return (
            <button
              key={q.id}
              className={cn(
                'w-2.5 h-2.5 rounded-full transition-all',
                isCurrent
                  ? 'bg-cyan-400 scale-125'
                  : isAnswered
                  ? 'bg-green-400'
                  : 'bg-white/20 hover:bg-white/40'
              )}
              onClick={() => setCurrentQuestionIndex(index)}
              title={`Question ${index + 1}: ${q.question.slice(0, 50)}...`}
            />
          );
        })}
      </div>

      {/* Current question */}
      <AnimatePresence mode="wait">
        {currentQuestion && (
          <motion.div
            key={currentQuestion.id}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.2 }}
            className="p-6 rounded border border-white/10 bg-white/5"
          >
            {/* Question header */}
            <div className="flex items-start gap-3 mb-4">
              <div className="flex items-center justify-center w-6 h-6 rounded-full bg-cyan-400/20 text-cyan-400 text-xs font-mono font-bold">
                {currentQuestionIndex + 1}
              </div>
              <div className="flex-1">
                <p className="text-sm text-white font-mono leading-relaxed">
                  {currentQuestion.question}
                </p>
                {currentQuestion.reason && (
                  <p className="mt-2 text-xs text-gray-500 font-mono">
                    <span className="text-gray-400">Why we ask:</span>{' '}
                    {currentQuestion.reason}
                  </p>
                )}
              </div>
              {currentQuestion.required && (
                <span className="text-xs text-red-400 font-mono">Required</span>
              )}
            </div>

            {/* Answer input based on type */}
            <div className="ml-9">
              {/* Single select */}
              {currentQuestion.type === 'single_select' && currentQuestion.options && (
                <div className="space-y-2">
                  {currentQuestion.options.map((option) => (
                    <button
                      key={option}
                      className={cn(
                        'w-full text-left px-4 py-3 rounded border transition-all font-mono text-sm',
                        answers[currentQuestion.id] === option
                          ? 'border-cyan-400 bg-cyan-400/10 text-white'
                          : 'border-white/10 bg-white/5 text-gray-300 hover:border-white/30 hover:bg-white/10'
                      )}
                      onClick={() => handleSingleSelect(currentQuestion.id, option)}
                    >
                      <div className="flex items-center gap-3">
                        <div
                          className={cn(
                            'w-4 h-4 rounded-full border-2 flex items-center justify-center',
                            answers[currentQuestion.id] === option
                              ? 'border-cyan-400 bg-cyan-400'
                              : 'border-white/30'
                          )}
                        >
                          {answers[currentQuestion.id] === option && (
                            <Check className="h-2.5 w-2.5 text-black" />
                          )}
                        </div>
                        {option}
                      </div>
                    </button>
                  ))}
                </div>
              )}

              {/* Multi select */}
              {currentQuestion.type === 'multi_select' && currentQuestion.options && (
                <div className="space-y-2">
                  {currentQuestion.options.map((option) => {
                    const isSelected = multiSelectAnswers[currentQuestion.id]?.includes(option);
                    return (
                      <button
                        key={option}
                        className={cn(
                          'w-full text-left px-4 py-3 rounded border transition-all font-mono text-sm',
                          isSelected
                            ? 'border-cyan-400 bg-cyan-400/10 text-white'
                            : 'border-white/10 bg-white/5 text-gray-300 hover:border-white/30 hover:bg-white/10'
                        )}
                        onClick={() => handleMultiSelect(currentQuestion.id, option)}
                      >
                        <div className="flex items-center gap-3">
                          <div
                            className={cn(
                              'w-4 h-4 rounded border-2 flex items-center justify-center',
                              isSelected
                                ? 'border-cyan-400 bg-cyan-400'
                                : 'border-white/30'
                            )}
                          >
                            {isSelected && <Check className="h-2.5 w-2.5 text-black" />}
                          </div>
                          {option}
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}

              {/* Short input */}
              {currentQuestion.type === 'short_input' && (
                <input
                  type="text"
                  value={answers[currentQuestion.id] || ''}
                  onChange={(e) => handleTextInput(currentQuestion.id, e.target.value)}
                  placeholder="Type your answer..."
                  className="w-full px-4 py-3 rounded border border-white/10 bg-white/5 text-white font-mono text-sm placeholder:text-gray-500 focus:outline-none focus:border-cyan-400/50"
                />
              )}

              {/* Long input */}
              {currentQuestion.type === 'long_input' && (
                <textarea
                  value={answers[currentQuestion.id] || ''}
                  onChange={(e) => handleTextInput(currentQuestion.id, e.target.value)}
                  placeholder="Type your detailed answer..."
                  rows={4}
                  className="w-full px-4 py-3 rounded border border-white/10 bg-white/5 text-white font-mono text-sm placeholder:text-gray-500 focus:outline-none focus:border-cyan-400/50 resize-none"
                />
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Navigation and submit */}
      <div className="flex items-center justify-between">
        <Button
          variant="outline"
          size="sm"
          className="text-xs font-mono border-white/20 text-gray-400 hover:bg-white/5"
          onClick={goToPrevious}
          disabled={isFirstQuestion}
        >
          <ChevronLeft className="h-4 w-4 mr-1" />
          Previous
        </Button>

        <div className="flex items-center gap-2">
          {onSkip && (
            <Button
              variant="ghost"
              size="sm"
              className="text-xs font-mono text-gray-500 hover:text-gray-300"
              onClick={onSkip}
            >
              Skip for now
            </Button>
          )}

          {isLastQuestion ? (
            <Button
              size="sm"
              className="text-xs font-mono bg-cyan-500 hover:bg-cyan-400 text-black"
              onClick={handleSubmit}
              disabled={!allRequiredAnswered || submitting}
            >
              {submitting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                  Submitting...
                </>
              ) : (
                <>
                  <Send className="h-4 w-4 mr-1" />
                  Submit Answers
                </>
              )}
            </Button>
          ) : (
            <Button
              size="sm"
              className="text-xs font-mono bg-white/10 hover:bg-white/20 text-white"
              onClick={goToNext}
            >
              Next
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          )}
        </div>
      </div>

      {/* Risk notes warning */}
      {goalAnalysis?.risk_notes && goalAnalysis.risk_notes.length > 0 && (
        <div className="p-4 rounded border border-yellow-400/30 bg-yellow-400/5">
          <div className="flex items-start gap-2">
            <AlertCircle className="h-4 w-4 text-yellow-400 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-xs text-yellow-400 font-mono font-medium mb-1">
                Things to Consider
              </p>
              <ul className="space-y-1">
                {goalAnalysis.risk_notes.map((note, index) => (
                  <li key={index} className="text-xs text-gray-400 font-mono">
                    • {note}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ClarifyPanel;

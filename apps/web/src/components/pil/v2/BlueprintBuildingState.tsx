'use client';

/**
 * Blueprint Building State Component
 * Reference: Slice 2A - Blueprint v2
 *
 * Shows "Generating Blueprint..." state with progress polling.
 * Displays while the final_blueprint_build PIL job is running.
 */

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Loader2,
  CheckCircle2,
  XCircle,
  FileText,
  Sparkles,
  Brain,
  Target,
  Clock,
  AlertTriangle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import { useBlueprintV2JobStatus } from '@/hooks/useApi';

// Stage configuration for visual feedback
const STAGE_CONFIG: Record<string, {
  icon: typeof Loader2;
  label: string;
  description: string;
}> = {
  gathering_context: {
    icon: FileText,
    label: 'Gathering Context',
    description: 'Collecting Q/A responses and project data...',
  },
  analyzing_intent: {
    icon: Brain,
    label: 'Analyzing Intent',
    description: 'Understanding your business goals and requirements...',
  },
  building_blueprint: {
    icon: Sparkles,
    label: 'Building Blueprint',
    description: 'Generating structured blueprint with AI...',
  },
  validating_structure: {
    icon: Target,
    label: 'Validating Structure',
    description: 'Ensuring blueprint meets all requirements...',
  },
};

interface BlueprintBuildingStateProps {
  /** Job ID to track */
  jobId: string;
  /** Callback when build completes successfully */
  onComplete?: (blueprintId: string) => void;
  /** Callback when build fails */
  onError?: (error: string) => void;
  /** Additional CSS classes */
  className?: string;
}

export function BlueprintBuildingState({
  jobId,
  onComplete,
  onError,
  className,
}: BlueprintBuildingStateProps) {
  const [hasCompleted, setHasCompleted] = useState(false);
  const [hasFailed, setHasFailed] = useState(false);

  const { data: jobStatus, isLoading, error } = useBlueprintV2JobStatus(jobId, {
    enabled: !hasCompleted && !hasFailed,
  });

  // Handle status changes
  useEffect(() => {
    if (!jobStatus) return;

    if (jobStatus.status === 'succeeded' && !hasCompleted) {
      setHasCompleted(true);
      if (onComplete && jobStatus.blueprint_id) {
        onComplete(jobStatus.blueprint_id);
      }
    }

    if (jobStatus.status === 'failed' && !hasFailed) {
      setHasFailed(true);
      if (onError) {
        onError(jobStatus.error || 'Blueprint build failed');
      }
    }
  }, [jobStatus, hasCompleted, hasFailed, onComplete, onError]);

  // Loading state
  if (isLoading) {
    return (
      <div className={cn('flex items-center justify-center p-8', className)}>
        <Loader2 className="h-8 w-8 animate-spin text-cyan-400" />
      </div>
    );
  }

  // Error fetching status
  if (error) {
    return (
      <div className={cn('p-6 text-center', className)}>
        <AlertTriangle className="h-12 w-12 text-yellow-400 mx-auto mb-4" />
        <h3 className="text-lg font-mono text-white mb-2">
          Unable to Track Progress
        </h3>
        <p className="text-sm text-gray-400 font-mono">
          Blueprint generation may still be in progress.
        </p>
      </div>
    );
  }

  // Completed state
  if (hasCompleted || jobStatus?.status === 'succeeded') {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className={cn(
          'p-6 rounded border border-green-500/30 bg-green-500/10',
          className
        )}
      >
        <div className="flex items-center gap-4">
          <div className="p-3 rounded-full bg-green-500/20">
            <CheckCircle2 className="h-8 w-8 text-green-400" />
          </div>
          <div>
            <h3 className="text-lg font-mono text-white">
              Blueprint Generated Successfully
            </h3>
            <p className="text-sm text-gray-400 font-mono mt-1">
              Your Blueprint v2 is ready for review.
            </p>
          </div>
        </div>
      </motion.div>
    );
  }

  // Failed state
  if (hasFailed || jobStatus?.status === 'failed') {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className={cn(
          'p-6 rounded border border-red-500/30 bg-red-500/10',
          className
        )}
      >
        <div className="flex items-start gap-4">
          <div className="p-3 rounded-full bg-red-500/20">
            <XCircle className="h-8 w-8 text-red-400" />
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-mono text-white">
              Blueprint Generation Failed
            </h3>
            <p className="text-sm text-red-400 font-mono mt-1">
              {jobStatus?.error || 'An unexpected error occurred'}
            </p>
            {jobStatus?.error_code && (
              <p className="text-xs text-gray-500 font-mono mt-2">
                Error code: {jobStatus.error_code}
              </p>
            )}
          </div>
        </div>
      </motion.div>
    );
  }

  // Active/building state
  const progress = jobStatus?.progress || 0;
  const isQueued = jobStatus?.status === 'queued';

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        'p-6 rounded border border-cyan-500/30 bg-cyan-500/5',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <div className="relative">
          <div className="p-3 rounded-full bg-cyan-500/20">
            <Sparkles className="h-8 w-8 text-cyan-400" />
          </div>
          {/* Pulse animation */}
          <motion.div
            className="absolute inset-0 rounded-full border-2 border-cyan-400/50"
            animate={{ scale: [1, 1.3, 1], opacity: [0.5, 0, 0.5] }}
            transition={{ duration: 2, repeat: Infinity }}
          />
        </div>
        <div>
          <h3 className="text-lg font-mono text-white">
            {isQueued ? 'Preparing to Generate Blueprint...' : 'Generating Blueprint...'}
          </h3>
          <p className="text-sm text-gray-400 font-mono mt-1">
            AI is building your structured simulation blueprint
          </p>
        </div>
      </div>

      {/* Progress bar */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-gray-400 font-mono">
            {isQueued ? 'Queued' : 'Processing'}
          </span>
          <span className="text-xs font-mono text-cyan-400 tabular-nums">
            {progress}%
          </span>
        </div>
        <Progress value={progress} className="h-2" />
      </div>

      {/* Stage indicators */}
      <div className="grid grid-cols-2 gap-3">
        {Object.entries(STAGE_CONFIG).map(([key, config], index) => {
          const StageIcon = config.icon;
          const stageProgress = (index + 1) * 25;
          const isActive = progress >= stageProgress - 25 && progress < stageProgress;
          const isComplete = progress >= stageProgress;

          return (
            <div
              key={key}
              className={cn(
                'p-3 rounded border transition-all duration-300',
                isComplete
                  ? 'border-green-500/30 bg-green-500/10'
                  : isActive
                  ? 'border-cyan-500/50 bg-cyan-500/10'
                  : 'border-white/10 bg-white/5'
              )}
            >
              <div className="flex items-center gap-2 mb-1">
                {isComplete ? (
                  <CheckCircle2 className="h-4 w-4 text-green-400" />
                ) : isActive ? (
                  <Loader2 className="h-4 w-4 text-cyan-400 animate-spin" />
                ) : (
                  <StageIcon className="h-4 w-4 text-gray-500" />
                )}
                <span
                  className={cn(
                    'text-xs font-mono',
                    isComplete
                      ? 'text-green-400'
                      : isActive
                      ? 'text-cyan-400'
                      : 'text-gray-500'
                  )}
                >
                  {config.label}
                </span>
              </div>
              <p className="text-xs text-gray-500 font-mono line-clamp-1">
                {config.description}
              </p>
            </div>
          );
        })}
      </div>

      {/* Time estimate */}
      <div className="mt-4 flex items-center gap-2 text-xs text-gray-500 font-mono">
        <Clock className="h-3 w-3" />
        <span>This usually takes 30-60 seconds</span>
      </div>
    </motion.div>
  );
}

export default BlueprintBuildingState;

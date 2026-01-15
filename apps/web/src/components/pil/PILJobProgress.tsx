'use client';

/**
 * PIL Job Progress Component
 * Reference: blueprint.md §5
 *
 * Inline loading widget that shows progress for PIL background jobs.
 * Supports compact mode for inline display and full mode for detailed view.
 */

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Loader2,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Clock,
  RefreshCw,
  X,
  ChevronDown,
  ChevronUp,
  Sparkles,
  FileText,
  Target,
  Zap,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import {
  usePILJob,
  useCancelPILJob,
  useRetryPILJob,
  usePILJobArtifacts,
} from '@/hooks/useApi';
import type { PILJob, PILJobStatus, PILJobType } from '@/lib/api';

// Status colors and icons
const STATUS_CONFIG: Record<PILJobStatus, {
  color: string;
  bgColor: string;
  borderColor: string;
  icon: typeof Loader2;
  label: string;
}> = {
  queued: {
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-400/10',
    borderColor: 'border-yellow-400/30',
    icon: Clock,
    label: 'Queued',
  },
  running: {
    color: 'text-cyan-400',
    bgColor: 'bg-cyan-400/10',
    borderColor: 'border-cyan-400/30',
    icon: Loader2,
    label: 'Processing',
  },
  succeeded: {
    color: 'text-green-400',
    bgColor: 'bg-green-400/10',
    borderColor: 'border-green-400/30',
    icon: CheckCircle2,
    label: 'Complete',
  },
  failed: {
    color: 'text-red-400',
    bgColor: 'bg-red-400/10',
    borderColor: 'border-red-400/30',
    icon: XCircle,
    label: 'Failed',
  },
  cancelled: {
    color: 'text-gray-400',
    bgColor: 'bg-gray-400/10',
    borderColor: 'border-gray-400/30',
    icon: X,
    label: 'Cancelled',
  },
};

// Job type icons and labels
const JOB_TYPE_CONFIG: Record<PILJobType, {
  icon: typeof Sparkles;
  label: string;
  description: string;
}> = {
  goal_analysis: {
    icon: Target,
    label: 'Goal Analysis',
    description: 'Analyzing project goals and generating clarifying questions',
  },
  blueprint_build: {
    icon: FileText,
    label: 'Blueprint Build',
    description: 'Generating project blueprint with slots and tasks',
  },
  slot_validation: {
    icon: CheckCircle2,
    label: 'Slot Validation',
    description: 'Validating data against slot requirements',
  },
  summarization: {
    icon: Sparkles,
    label: 'Summarization',
    description: 'Creating AI summary of content',
  },
  alignment_scoring: {
    icon: Zap,
    label: 'Alignment Scoring',
    description: 'Computing alignment with project goals',
  },
};

interface PILJobProgressProps {
  /** Job ID to display progress for */
  jobId: string;
  /** Display mode - compact for inline, full for detailed view */
  mode?: 'compact' | 'full';
  /** Show cancel button */
  showCancel?: boolean;
  /** Show retry button for failed jobs */
  showRetry?: boolean;
  /** Callback when job completes */
  onComplete?: (job: PILJob) => void;
  /** Callback when job fails */
  onError?: (job: PILJob, error: string) => void;
  /** Additional CSS classes */
  className?: string;
}

export function PILJobProgress({
  jobId,
  mode = 'compact',
  showCancel = true,
  showRetry = true,
  onComplete,
  onError,
  className,
}: PILJobProgressProps) {
  const [expanded, setExpanded] = useState(mode === 'full');
  const [previousStatus, setPreviousStatus] = useState<PILJobStatus | null>(null);

  const { data: job, isLoading, error } = usePILJob(jobId);
  const { data: artifacts } = usePILJobArtifacts(jobId);
  const cancelMutation = useCancelPILJob();
  const retryMutation = useRetryPILJob();

  // Track status changes for callbacks
  useEffect(() => {
    if (job && previousStatus !== job.status) {
      if (job.status === 'succeeded' && onComplete) {
        onComplete(job);
      }
      if (job.status === 'failed' && onError) {
        onError(job, job.error_message || 'Job failed');
      }
      setPreviousStatus(job.status);
    }
  }, [job, previousStatus, onComplete, onError]);

  if (isLoading) {
    return (
      <div className={cn('flex items-center gap-2 p-2', className)}>
        <Loader2 className="h-4 w-4 animate-spin text-cyan-400" />
        <span className="text-xs text-gray-400 font-mono">Loading job...</span>
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className={cn('flex items-center gap-2 p-2 text-red-400', className)}>
        <AlertCircle className="h-4 w-4" />
        <span className="text-xs font-mono">Failed to load job</span>
      </div>
    );
  }

  const statusConfig = STATUS_CONFIG[job.status];
  const typeConfig = JOB_TYPE_CONFIG[job.job_type];
  const StatusIcon = statusConfig.icon;
  const TypeIcon = typeConfig.icon;
  const isActive = job.status === 'queued' || job.status === 'running';

  const handleCancel = async () => {
    try {
      await cancelMutation.mutateAsync(jobId);
    } catch (err) {
      // Handle error silently - toast will show from mutation
    }
  };

  const handleRetry = async () => {
    try {
      await retryMutation.mutateAsync(jobId);
    } catch (err) {
      // Handle error silently - toast will show from mutation
    }
  };

  // Compact mode - minimal inline display
  if (mode === 'compact' && !expanded) {
    return (
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className={cn(
          'flex items-center gap-3 px-3 py-2 rounded border',
          statusConfig.bgColor,
          statusConfig.borderColor,
          className
        )}
      >
        {/* Status icon with animation */}
        <div className="relative">
          <StatusIcon
            className={cn(
              'h-4 w-4',
              statusConfig.color,
              isActive && 'animate-spin'
            )}
          />
          {isActive && (
            <motion.div
              className="absolute inset-0 rounded-full border border-cyan-400/50"
              animate={{ scale: [1, 1.5, 1], opacity: [0.5, 0, 0.5] }}
              transition={{ duration: 1.5, repeat: Infinity }}
            />
          )}
        </div>

        {/* Job info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-white truncate">
              {job.job_name || typeConfig.label}
            </span>
            <span className={cn('text-xs font-mono', statusConfig.color)}>
              {statusConfig.label}
            </span>
          </div>
          {job.stage_name && (
            <div className="text-xs text-gray-500 font-mono truncate">
              {job.stage_name}
              {job.stage_message && `: ${job.stage_message}`}
            </div>
          )}
        </div>

        {/* Progress bar for active jobs */}
        {isActive && (
          <div className="w-20">
            <Progress value={job.progress_percent} className="h-1" />
          </div>
        )}

        {/* Progress percentage */}
        {isActive && (
          <span className="text-xs font-mono text-cyan-400 tabular-nums">
            {job.progress_percent}%
          </span>
        )}

        {/* Expand button */}
        <Button
          variant="ghost"
          size="sm"
          className="h-6 w-6 p-0 hover:bg-white/10"
          onClick={() => setExpanded(true)}
        >
          <ChevronDown className="h-3 w-3 text-gray-400" />
        </Button>

        {/* Cancel button */}
        {showCancel && isActive && (
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0 hover:bg-red-500/20"
            onClick={handleCancel}
            disabled={cancelMutation.isPending}
          >
            <X className="h-3 w-3 text-red-400" />
          </Button>
        )}
      </motion.div>
    );
  }

  // Full/expanded mode - detailed view
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className={cn(
        'rounded border p-4',
        statusConfig.bgColor,
        statusConfig.borderColor,
        className
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div
            className={cn(
              'p-2 rounded',
              statusConfig.bgColor,
              'border',
              statusConfig.borderColor
            )}
          >
            <TypeIcon className={cn('h-5 w-5', statusConfig.color)} />
          </div>
          <div>
            <h4 className="text-sm font-mono font-medium text-white">
              {job.job_name || typeConfig.label}
            </h4>
            <p className="text-xs text-gray-400 font-mono">
              {typeConfig.description}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Status badge */}
          <div
            className={cn(
              'flex items-center gap-1.5 px-2 py-1 rounded text-xs font-mono',
              statusConfig.bgColor,
              statusConfig.color
            )}
          >
            <StatusIcon
              className={cn('h-3 w-3', isActive && 'animate-spin')}
            />
            {statusConfig.label}
          </div>

          {/* Collapse button (only in expanded compact mode) */}
          {mode === 'compact' && expanded && (
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0 hover:bg-white/10"
              onClick={() => setExpanded(false)}
            >
              <ChevronUp className="h-3 w-3 text-gray-400" />
            </Button>
          )}
        </div>
      </div>

      {/* Progress section */}
      {isActive && (
        <div className="mb-4">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs text-gray-400 font-mono">
              {job.stage_name || 'Processing...'}
            </span>
            <span className="text-xs font-mono text-cyan-400 tabular-nums">
              {job.progress_percent}%
            </span>
          </div>
          <Progress value={job.progress_percent} className="h-2" />
          {job.stage_message && (
            <p className="mt-1.5 text-xs text-gray-500 font-mono">
              {job.stage_message}
            </p>
          )}
        </div>
      )}

      {/* Error message */}
      {job.status === 'failed' && job.error_message && (
        <div className="mb-4 p-3 rounded bg-red-500/10 border border-red-500/30">
          <div className="flex items-start gap-2">
            <XCircle className="h-4 w-4 text-red-400 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-red-400 font-mono">{job.error_message}</p>
          </div>
        </div>
      )}

      {/* Artifacts preview */}
      {artifacts && artifacts.length > 0 && (
        <div className="mb-4">
          <h5 className="text-xs text-gray-400 font-mono mb-2">
            Artifacts ({artifacts.length})
          </h5>
          <div className="space-y-1">
            {artifacts.slice(0, 3).map((artifact) => (
              <div
                key={artifact.id}
                className="flex items-center gap-2 px-2 py-1.5 rounded bg-white/5 border border-white/10"
              >
                <FileText className="h-3 w-3 text-cyan-400" />
                <span className="text-xs font-mono text-gray-300 truncate">
                  {artifact.artifact_name}
                </span>
                {artifact.alignment_score !== null && (
                  <span className="text-xs font-mono text-green-400 ml-auto">
                    {Math.round(artifact.alignment_score * 100)}% match
                  </span>
                )}
              </div>
            ))}
            {artifacts.length > 3 && (
              <p className="text-xs text-gray-500 font-mono pl-2">
                +{artifacts.length - 3} more
              </p>
            )}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-between pt-3 border-t border-white/10">
        <div className="text-xs text-gray-500 font-mono">
          {job.created_at && (
            <span>
              Started {new Date(job.created_at).toLocaleTimeString()}
            </span>
          )}
          {job.retry_count > 0 && (
            <span className="ml-2 text-yellow-400">
              (Retry {job.retry_count}/{job.max_retries})
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Retry button for failed jobs */}
          {showRetry && job.status === 'failed' && job.retry_count < job.max_retries && (
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs font-mono border-yellow-400/30 text-yellow-400 hover:bg-yellow-400/10"
              onClick={handleRetry}
              disabled={retryMutation.isPending}
            >
              <RefreshCw
                className={cn(
                  'h-3 w-3 mr-1',
                  retryMutation.isPending && 'animate-spin'
                )}
              />
              Retry
            </Button>
          )}

          {/* Cancel button for active jobs */}
          {showCancel && isActive && (
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs font-mono border-red-400/30 text-red-400 hover:bg-red-400/10"
              onClick={handleCancel}
              disabled={cancelMutation.isPending}
            >
              <X className="h-3 w-3 mr-1" />
              Cancel
            </Button>
          )}
        </div>
      </div>
    </motion.div>
  );
}

// Convenience component for showing multiple active jobs
interface ActiveJobsIndicatorProps {
  projectId?: string;
  className?: string;
}

export function ActiveJobsIndicator({ projectId, className }: ActiveJobsIndicatorProps) {
  const { data: jobs, isLoading } = usePILJobArtifacts(projectId || '');

  // This will be implemented with useActivePILJobs when we have proper polling
  // For now, just show a placeholder

  return null; // Will be implemented in next iteration
}

export default PILJobProgress;

'use client';

/**
 * SpecRunProgress Component
 * Real-time progress monitoring for spec-compliant simulation runs.
 * Reference: project.md §6.6 (Run progress), C3 (read-only telemetry)
 */

import { memo, useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  Play,
  Pause,
  StopCircle,
  CheckCircle,
  XCircle,
  Clock,
  Users,
  Cpu,
  Activity,
  GitBranch,
  AlertTriangle,
  ExternalLink,
  RefreshCw,
  TrendingUp,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { RunStatusBadge } from './RunStatusBadge';
import { useRunProgress, useStartRun, useCancelRun } from '@/hooks/useApi';
import type { SpecRun, RunProgressUpdate } from '@/lib/api';

interface SpecRunProgressProps {
  runId: string;
  initialRun?: SpecRun;
  onComplete?: (runId: string) => void;
  onFailed?: (runId: string, error: string) => void;
  showControls?: boolean;
  showDetails?: boolean;
  compact?: boolean;
  autoRefresh?: boolean;
  refreshInterval?: number;
  className?: string;
}

export const SpecRunProgress = memo(function SpecRunProgress({
  runId,
  initialRun,
  onComplete,
  onFailed,
  showControls = true,
  showDetails = true,
  compact = false,
  autoRefresh = true,
  refreshInterval = 2000,
  className,
}: SpecRunProgressProps) {
  const router = useRouter();

  // State
  const [elapsedTime, setElapsedTime] = useState(0);
  const [progressData, setProgressData] = useState<RunProgressUpdate | null>(null);

  // Queries and mutations
  const { data: runProgress, refetch } = useRunProgress(runId);
  const startRun = useStartRun();
  const cancelRun = useCancelRun();

  // Combine initial run with progress data
  const run = {
    ...initialRun,
    ...runProgress,
    ...progressData,
  } as SpecRun & RunProgressUpdate;

  // Determine run state
  const isQueued = run.status === 'queued';
  const isStarting = run.status === 'starting';
  const isRunning = run.status === 'running';
  const isActive = isStarting || isRunning;
  const isSucceeded = run.status === 'succeeded';
  const isFailed = run.status === 'failed';
  const isCancelled = run.status === 'cancelled';
  const isComplete = isSucceeded || isFailed || isCancelled;

  // Get total ticks from run config or timing
  const totalTicks = run.timing?.total_ticks ?? 100;
  const currentTick = runProgress?.current_tick ?? run.timing?.current_tick ?? 0;

  // Progress percentage (calculated from ticks)
  const progress = totalTicks > 0 ? Math.round((currentTick / totalTicks) * 100) : 0;

  // Timer for elapsed time
  useEffect(() => {
    if (!isActive) return;

    const interval = setInterval(() => {
      const startedAt = run.timing?.started_at;
      if (startedAt) {
        const start = new Date(startedAt).getTime();
        setElapsedTime(Date.now() - start);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [isActive, run.timing?.started_at]);

  // Handle completion callbacks
  useEffect(() => {
    if (isSucceeded && onComplete) {
      onComplete(runId);
    }
    if (isFailed && onFailed) {
      const errorMessage = run.error?.error_message ?? 'Unknown error';
      onFailed(runId, errorMessage);
    }
  }, [isSucceeded, isFailed, runId, run.error?.error_message, onComplete, onFailed]);

  // Format time
  const formatTime = (ms: number) => {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    if (hours > 0) {
      return `${hours}:${(minutes % 60).toString().padStart(2, '0')}:${(seconds % 60).toString().padStart(2, '0')}`;
    }
    return `${minutes}:${(seconds % 60).toString().padStart(2, '0')}`;
  };

  // Estimate remaining time
  const estimatedRemaining = progress > 0 && progress < 100
    ? Math.round((elapsedTime / progress) * (100 - progress))
    : null;

  // Handle actions
  const handleStart = useCallback(() => {
    startRun.mutate(runId);
  }, [runId, startRun]);

  const handleCancel = useCallback(() => {
    cancelRun.mutate(runId);
  }, [runId, cancelRun]);

  // Compact version
  if (compact) {
    return (
      <div
        className={cn(
          'flex items-center gap-4 p-3 bg-black border border-white/10',
          isActive && 'border-cyan-500/30',
          className
        )}
      >
        <RunStatusBadge status={run.status} size="sm" />

        <div className="flex-1 min-w-0">
          <div className="h-1.5 bg-white/10 overflow-hidden">
            <div
              className={cn(
                'h-full transition-all duration-300',
                isActive && 'bg-gradient-to-r from-cyan-500 to-blue-500',
                isSucceeded && 'bg-green-500',
                isFailed && 'bg-red-500'
              )}
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        <span className="text-xs font-mono text-white/60">
          {progress}%
        </span>

        {showControls && isQueued && (
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={handleStart}
            disabled={startRun.isPending}
          >
            <Play className="w-3 h-3" />
          </Button>
        )}

        {showControls && isActive && (
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={handleCancel}
            disabled={cancelRun.isPending}
          >
            <StopCircle className="w-3 h-3" />
          </Button>
        )}
      </div>
    );
  }

  // Full version
  return (
    <div
      className={cn(
        'bg-black border',
        isActive ? 'border-cyan-500/30' : 'border-white/10',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className={cn(
            'p-2',
            isActive ? 'bg-cyan-500/10' : 'bg-white/5'
          )}>
            <Activity className={cn(
              'w-4 h-4',
              isActive ? 'text-cyan-400' : 'text-white/40'
            )} />
          </div>
          <div>
            <h3 className="text-sm font-mono font-bold text-white">
              Simulation Progress
            </h3>
            <p className="text-[10px] font-mono text-white/40">
              Run ID: {runId.slice(0, 12)}...
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {isActive && (
            <div className="flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 bg-cyan-500 rounded-full animate-pulse" />
              <span className="text-[10px] font-mono text-cyan-400">LIVE</span>
            </div>
          )}
          <RunStatusBadge status={run.status} />
        </div>
      </div>

      {/* Progress Section */}
      <div className="px-4 py-4">
        {/* Progress Bar */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-mono text-white/40 uppercase tracking-wider">
              Overall Progress
            </span>
            <span className="text-sm font-mono font-bold text-white">
              {progress}%
            </span>
          </div>
          <div className="h-2 bg-white/10 overflow-hidden">
            <div
              className={cn(
                'h-full transition-all duration-500 ease-out',
                isActive && 'bg-gradient-to-r from-cyan-500 via-blue-500 to-purple-500 animate-shimmer',
                isSucceeded && 'bg-green-500',
                isFailed && 'bg-red-500',
                isCancelled && 'bg-white/20'
              )}
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Stats Grid */}
        {showDetails && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            {/* Current Tick */}
            <div className="p-3 bg-white/5 border border-white/10">
              <div className="flex items-center gap-2 mb-1">
                <CheckCircle className="w-3 h-3 text-green-400" />
                <span className="text-[10px] font-mono text-white/40 uppercase">
                  Current Tick
                </span>
              </div>
              <p className="text-lg font-mono font-bold text-green-400">
                {currentTick}
              </p>
            </div>

            {/* Total Ticks */}
            <div className="p-3 bg-white/5 border border-white/10">
              <div className="flex items-center gap-2 mb-1">
                <Users className="w-3 h-3 text-white/40" />
                <span className="text-[10px] font-mono text-white/40 uppercase">
                  Total Ticks
                </span>
              </div>
              <p className="text-lg font-mono font-bold text-white">
                {totalTicks}
              </p>
            </div>

            {/* Elapsed Time */}
            <div className="p-3 bg-white/5 border border-white/10">
              <div className="flex items-center gap-2 mb-1">
                <Clock className="w-3 h-3 text-white/40" />
                <span className="text-[10px] font-mono text-white/40 uppercase">
                  Elapsed
                </span>
              </div>
              <p className="text-lg font-mono font-bold text-white">
                {formatTime(elapsedTime)}
              </p>
            </div>

            {/* Estimated Remaining */}
            <div className="p-3 bg-white/5 border border-white/10">
              <div className="flex items-center gap-2 mb-1">
                <TrendingUp className="w-3 h-3 text-white/40" />
                <span className="text-[10px] font-mono text-white/40 uppercase">
                  Remaining
                </span>
              </div>
              <p className="text-lg font-mono font-bold text-white">
                {estimatedRemaining ? formatTime(estimatedRemaining) : '--:--'}
              </p>
            </div>
          </div>
        )}

        {/* Current Tick Info */}
        {runProgress?.current_tick !== undefined && (
          <div className="flex items-center gap-4 p-3 bg-white/5 border border-white/10 mb-4">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-cyan-400" />
              <span className="text-xs font-mono text-white/40">Tick:</span>
              <span className="text-sm font-mono font-bold text-white">
                {runProgress.current_tick}
              </span>
            </div>
            {totalTicks > 0 && (
              <>
                <span className="text-white/20">/</span>
                <span className="text-sm font-mono text-white/60">
                  {totalTicks}
                </span>
              </>
            )}
          </div>
        )}

        {/* Error Message */}
        {run.error && (
          <div className="flex items-start gap-3 p-3 bg-red-500/10 border border-red-500/30 mb-4">
            <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-xs font-mono font-bold text-red-400 mb-1">
                {run.error.error_code}
              </p>
              <p className="text-xs font-mono text-red-300">
                {run.error.error_message}
              </p>
            </div>
          </div>
        )}

        {/* Completion Message */}
        {isSucceeded && (
          <div className="flex items-center justify-between p-3 bg-green-500/10 border border-green-500/30">
            <div className="flex items-center gap-3">
              <CheckCircle className="w-5 h-5 text-green-400" />
              <div>
                <p className="text-sm font-mono font-bold text-green-400">
                  Simulation Complete
                </p>
                <p className="text-[10px] font-mono text-green-400/60">
                  Results are ready for analysis
                </p>
              </div>
            </div>
            <Button
              variant="success"
              size="sm"
              onClick={() => router.push(`/dashboard/runs/${runId}/results`)}
            >
              <ExternalLink className="w-3 h-3 mr-1" />
              View Results
            </Button>
          </div>
        )}
      </div>

      {/* Controls */}
      {showControls && (
        <div className="flex items-center justify-between px-4 py-3 border-t border-white/10">
          <div className="flex items-center gap-2">
            {isQueued && (
              <Button
                variant="primary"
                size="sm"
                onClick={handleStart}
                disabled={startRun.isPending}
              >
                {startRun.isPending ? (
                  <RefreshCw className="w-3 h-3 mr-1 animate-spin" />
                ) : (
                  <Play className="w-3 h-3 mr-1" />
                )}
                Start Run
              </Button>
            )}
            {isActive && (
              <Button
                variant="destructive"
                size="sm"
                onClick={handleCancel}
                disabled={cancelRun.isPending}
              >
                {cancelRun.isPending ? (
                  <RefreshCw className="w-3 h-3 mr-1 animate-spin" />
                ) : (
                  <StopCircle className="w-3 h-3 mr-1" />
                )}
                Cancel
              </Button>
            )}
          </div>

          {run.node_id && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => router.push(`/dashboard/nodes/${run.node_id}`)}
            >
              <GitBranch className="w-3 h-3 mr-1" />
              View Node
            </Button>
          )}
        </div>
      )}

      {/* Shimmer animation styles */}
      <style jsx>{`
        @keyframes shimmer {
          0% { background-position: -200% 0; }
          100% { background-position: 200% 0; }
        }
        .animate-shimmer {
          background-size: 200% 100%;
          animation: shimmer 2s linear infinite;
        }
      `}</style>
    </div>
  );
});

export default SpecRunProgress;

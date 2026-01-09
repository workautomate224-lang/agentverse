'use client';

/**
 * RunCard Component
 * Displays a single run with status, progress, and actions.
 * Reference: project.md §6.6 (Run entity)
 */

import { memo, useMemo } from 'react';
import Link from 'next/link';
import {
  Play,
  StopCircle,
  Clock,
  Users,
  GitBranch,
  ExternalLink,
  MoreVertical,
  Copy,
  Trash2,
  RefreshCw,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { RunStatusBadge } from './RunStatusBadge';
import type { SpecRun, RunSummary } from '@/lib/api';

interface RunCardProps {
  run: SpecRun | RunSummary;
  projectId?: string;
  onStart?: (runId: string) => void;
  onCancel?: (runId: string) => void;
  onDuplicate?: (runId: string) => void;
  onDelete?: (runId: string) => void;
  showActions?: boolean;
  compact?: boolean;
  className?: string;
}

export const RunCard = memo(function RunCard({
  run,
  projectId,
  onStart,
  onCancel,
  onDuplicate,
  onDelete,
  showActions = true,
  compact = false,
  className,
}: RunCardProps) {
  // Determine if run is in progress
  const isActive = run.status === 'running' || run.status === 'starting';
  const isQueued = run.status === 'queued';
  const isComplete = run.status === 'succeeded' || run.status === 'failed' || run.status === 'cancelled';

  // Calculate progress percentage from timing
  const progress = useMemo(() => {
    if (run.status === 'succeeded') return 100;
    if (run.status === 'queued') return 0;

    const currentTick = run.timing?.current_tick ?? 0;
    const totalTicks = run.timing?.total_ticks ?? 0;

    if (totalTicks > 0) {
      return Math.round((currentTick / totalTicks) * 100);
    }
    return 0;
  }, [run.status, run.timing?.current_tick, run.timing?.total_ticks]);

  // Format elapsed time
  const formatDuration = (ms: number) => {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    if (hours > 0) return `${hours}h ${minutes % 60}m`;
    if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
    return `${seconds}s`;
  };

  // Calculate duration
  const duration = useMemo(() => {
    const startedAt = run.timing?.started_at;
    if (!startedAt) return null;
    const start = new Date(startedAt).getTime();
    const endedAt = run.timing?.ended_at;
    const end = endedAt
      ? new Date(endedAt).getTime()
      : Date.now();
    return formatDuration(end - start);
  }, [run.timing?.started_at, run.timing?.ended_at]);

  // Get run ID (both SpecRun and RunSummary use run_id)
  const runId = run.run_id;

  // Get agent count - not available in current API types, would come from config
  const agentCount = 0;

  // Compact version
  if (compact) {
    return (
      <div
        className={cn(
          'flex items-center gap-4 p-3 bg-black border border-white/10 hover:border-white/20 transition-colors',
          className
        )}
      >
        <RunStatusBadge status={run.status} size="sm" />

        <div className="flex-1 min-w-0">
          <Link
            href={`/dashboard/runs/${runId}`}
            className="text-sm font-mono text-white hover:text-cyan-400 transition-colors truncate block"
          >
            {runId.slice(0, 8)}...
          </Link>
        </div>

        {isActive && (
          <div className="w-24">
            <div className="h-1 bg-white/10 overflow-hidden">
              <div
                className="h-full bg-cyan-500 transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        {duration && (
          <span className="text-xs font-mono text-white/40">
            {duration}
          </span>
        )}

        {showActions && isQueued && onStart && (
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => onStart(runId)}
          >
            <Play className="w-3 h-3" />
          </Button>
        )}

        {showActions && isActive && onCancel && (
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => onCancel(runId)}
          >
            <StopCircle className="w-3 h-3" />
          </Button>
        )}
      </div>
    );
  }

  // Full card version
  return (
    <div
      className={cn(
        'bg-black border border-white/10 hover:border-white/20 transition-colors',
        isActive && 'border-cyan-500/30',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
        <div className="flex items-center gap-3">
          <RunStatusBadge status={run.status} />
          <Link
            href={`/dashboard/runs/${runId}`}
            className="text-sm font-mono text-white hover:text-cyan-400 transition-colors"
          >
            Run {runId.slice(0, 8)}
          </Link>
        </div>

        {showActions && (
          <div className="flex items-center gap-1">
            {isQueued && onStart && (
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => onStart(runId)}
                title="Start Run"
              >
                <Play className="w-3.5 h-3.5" />
              </Button>
            )}
            {isActive && onCancel && (
              <Button
                variant="destructive"
                size="icon-sm"
                onClick={() => onCancel(runId)}
                title="Cancel Run"
              >
                <StopCircle className="w-3.5 h-3.5" />
              </Button>
            )}
            {isComplete && onDuplicate && (
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => onDuplicate(runId)}
                title="Duplicate Run"
              >
                <Copy className="w-3.5 h-3.5" />
              </Button>
            )}
            <Link href={`/dashboard/runs/${runId}`}>
              <Button variant="ghost" size="icon-sm" title="View Details">
                <ExternalLink className="w-3.5 h-3.5" />
              </Button>
            </Link>
          </div>
        )}
      </div>

      {/* Progress Bar (for active runs) */}
      {isActive && (
        <div className="px-4 py-3 border-b border-white/10">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-mono text-white/40 uppercase tracking-wider">
              Progress
            </span>
            <span className="text-xs font-mono text-cyan-400">
              {progress}%
            </span>
          </div>
          <div className="h-1.5 bg-white/10 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Stats */}
      <div className="px-4 py-3 grid grid-cols-3 gap-4">
        {/* Agents */}
        <div className="flex items-center gap-2">
          <Users className="w-3.5 h-3.5 text-white/40" />
          <div>
            <p className="text-[10px] font-mono text-white/40 uppercase">Agents</p>
            <p className="text-sm font-mono text-white">{agentCount}</p>
          </div>
        </div>

        {/* Duration */}
        <div className="flex items-center gap-2">
          <Clock className="w-3.5 h-3.5 text-white/40" />
          <div>
            <p className="text-[10px] font-mono text-white/40 uppercase">Duration</p>
            <p className="text-sm font-mono text-white">{duration || '--:--'}</p>
          </div>
        </div>

        {/* Node */}
        {'node_id' in run && run.node_id && (
          <div className="flex items-center gap-2">
            <GitBranch className="w-3.5 h-3.5 text-white/40" />
            <div>
              <p className="text-[10px] font-mono text-white/40 uppercase">Node</p>
              <p className="text-sm font-mono text-white truncate">
                {run.node_id.slice(0, 8)}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Error Message */}
      {'error' in run && run.error && (
        <div className="px-4 py-3 border-t border-red-500/20 bg-red-500/5">
          <p className="text-xs font-mono text-red-400">
            {run.error.error_message}
          </p>
        </div>
      )}

      {/* Footer */}
      <div className="px-4 py-2 border-t border-white/5 flex items-center justify-between">
        <span className="text-[10px] font-mono text-white/30">
          Created {new Date(run.created_at).toLocaleDateString()}
        </span>
        {'actual_seed' in run && run.actual_seed && (
          <span className="text-[10px] font-mono text-white/30">
            Seed: {run.actual_seed}
          </span>
        )}
      </div>
    </div>
  );
});

export default RunCard;

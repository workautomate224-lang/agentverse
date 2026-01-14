'use client';

/**
 * Run Detail Page
 * Spec-compliant run monitoring with progress and telemetry links
 * Reference: project.md §6.5-6.6, C3 (replay read-only)
 */

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import {
  Play,
  Loader2,
  XCircle,
  CheckCircle,
  Clock,
  Activity,
  ArrowLeft,
  GitBranch,
  BarChart3,
  Terminal,
  RefreshCw,
  Pause,
  AlertTriangle,
  FileText,
  Settings,
  Layers,
  Shield,
} from 'lucide-react';
import { useRun, useRunProgress, useCancelRun, useStartRun } from '@/hooks/useApi';
import { cn } from '@/lib/utils';

import type { SpecRunStatus } from '@/lib/api';

const statusConfig: Record<SpecRunStatus, { className: string; icon: React.ReactNode; label: string; bgColor: string }> = {
  queued: {
    className: 'text-orange-400',
    bgColor: 'bg-orange-500/10 border-orange-500/30',
    icon: <Clock className="w-5 h-5" />,
    label: 'Queued',
  },
  starting: {
    className: 'text-yellow-400',
    bgColor: 'bg-yellow-500/10 border-yellow-500/30',
    icon: <Activity className="w-5 h-5" />,
    label: 'Starting',
  },
  running: {
    className: 'text-blue-400',
    bgColor: 'bg-blue-500/10 border-blue-500/30',
    icon: <Activity className="w-5 h-5 animate-pulse" />,
    label: 'Running',
  },
  succeeded: {
    className: 'text-green-400',
    bgColor: 'bg-green-500/10 border-green-500/30',
    icon: <CheckCircle className="w-5 h-5" />,
    label: 'Succeeded',
  },
  failed: {
    className: 'text-red-400',
    bgColor: 'bg-red-500/10 border-red-500/30',
    icon: <XCircle className="w-5 h-5" />,
    label: 'Failed',
  },
  cancelled: {
    className: 'text-white/50',
    bgColor: 'bg-white/5 border-white/20',
    icon: <Pause className="w-5 h-5" />,
    label: 'Cancelled',
  },
};

export default function RunDetailPage() {
  const params = useParams();
  const router = useRouter();
  const runId = params.id as string;

  const { data: run, isLoading, error, refetch } = useRun(runId);
  const { data: progress } = useRunProgress(runId);
  const cancelRun = useCancelRun();
  const startRun = useStartRun();

  // Auto-refresh while running
  useEffect(() => {
    if (run?.status === 'running') {
      const interval = setInterval(() => refetch(), 3000);
      return () => clearInterval(interval);
    }
  }, [run?.status, refetch]);

  const handleCancel = async () => {
    if (confirm('Cancel this run?')) {
      try {
        await cancelRun.mutateAsync(runId);
        refetch();
      } catch {
        // Error handled by mutation
      }
    }
  };

  const handleStart = async () => {
    try {
      await startRun.mutateAsync(runId);
      refetch();
    } catch {
      // Error handled by mutation
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-cyan-400" />
      </div>
    );
  }

  if (error || !run) {
    return (
      <div className="min-h-screen bg-black p-6">
        <div className="bg-red-500/10 border border-red-500/30 p-6 max-w-md mx-auto mt-12">
          <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-4" />
          <p className="text-sm font-mono text-red-400 text-center mb-4">
            Failed to load run details
          </p>
          <div className="flex justify-center gap-2">
            <Button variant="secondary" size="sm" onClick={() => refetch()}>
              RETRY
            </Button>
            <Button variant="secondary" size="sm" onClick={() => router.push('/dashboard/runs')}>
              BACK TO RUNS
            </Button>
          </div>
        </div>
      </div>
    );
  }

  const status = statusConfig[run.status] || statusConfig.queued;
  const currentTick = progress?.current_tick || run.timing?.current_tick || 0;
  const totalTicks = run.timing?.total_ticks || 0;
  const progressPercent = totalTicks > 0 ? (currentTick / totalTicks) * 100 : 0;

  return (
    <div className="min-h-screen bg-black p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <Link
            href="/dashboard/runs"
            className="flex items-center gap-1 text-xs font-mono text-white/40 hover:text-white mb-2"
          >
            <ArrowLeft className="w-3 h-3" />
            Back to Runs
          </Link>
          <div className="flex items-center gap-3">
            <div className={cn('p-2 border', status.bgColor)}>
              {status.icon}
            </div>
            <div>
              <h1 className="text-xl font-mono font-bold text-white">
                Run Detail
              </h1>
              <p className="text-xs font-mono text-white/40">
                {run.run_id}
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" onClick={() => refetch()}>
            <RefreshCw className="w-3 h-3 mr-2" />
            REFRESH
          </Button>
          {run.status === 'queued' && (
            <Button size="sm" onClick={handleStart} disabled={startRun.isPending}>
              <Play className="w-3 h-3 mr-2" />
              START RUN
            </Button>
          )}
          {run.status === 'running' && (
            <Button variant="destructive" size="sm" onClick={handleCancel} disabled={cancelRun.isPending}>
              <XCircle className="w-3 h-3 mr-2" />
              CANCEL
            </Button>
          )}
        </div>
      </div>

      {/* Status Banner */}
      <div className={cn('border p-4 mb-6', status.bgColor)}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className={cn('text-lg font-mono font-bold', status.className)}>
              {status.label}
            </span>
            {run.label && (
              <span className="text-sm font-mono text-white/60">
                {run.label}
              </span>
            )}
          </div>
          {run.status === 'running' && (
            <span className="text-xs font-mono text-white/40">
              Auto-refreshing every 3s
            </span>
          )}
        </div>
      </div>

      {/* Progress Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {/* Progress Bar */}
        <div className="lg:col-span-2 bg-white/5 border border-white/10 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Activity className="w-4 h-4 text-cyan-400" />
            <span className="text-sm font-mono text-white/60 uppercase">Progress</span>
          </div>

          <div className="mb-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-3xl font-mono font-bold text-white">
                {progressPercent.toFixed(1)}%
              </span>
              <span className="text-sm font-mono text-white/40">
                Tick {currentTick} / {totalTicks}
              </span>
            </div>
            <div className="w-full bg-white/10 h-3">
              <div
                className={cn(
                  'h-3 transition-all duration-500',
                  progressPercent === 100 ? 'bg-green-500' : 'bg-cyan-500'
                )}
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>

          {progress?.estimated_completion && (
            <p className="text-xs font-mono text-white/40">
              Estimated completion: {new Date(progress.estimated_completion).toLocaleTimeString()}
            </p>
          )}
        </div>

        {/* Quick Stats */}
        <div className="bg-white/5 border border-white/10 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Layers className="w-4 h-4 text-purple-400" />
            <span className="text-sm font-mono text-white/60 uppercase">Timing</span>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-white/40">Total Ticks</span>
              <span className="text-sm font-mono text-white">{totalTicks}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-white/40">Actual Seed</span>
              <span className="text-sm font-mono text-white">
                {run.actual_seed || '-'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-white/40">Triggered By</span>
              <span className="text-sm font-mono text-white capitalize">
                {run.triggered_by}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Info Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {/* Node Link */}
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-2">
            <GitBranch className="w-4 h-4 text-white/40" />
            <span className="text-xs font-mono text-white/40">Node</span>
          </div>
          {run.node_id ? (
            <Link
              href={`/dashboard/nodes/${run.node_id}`}
              className="text-sm font-mono text-cyan-400 hover:text-cyan-300 hover:underline"
            >
              {run.node_id.slice(0, 16)}...
            </Link>
          ) : (
            <span className="text-sm font-mono text-white/30">Not assigned</span>
          )}
        </div>

        {/* Project Link */}
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-2">
            <FileText className="w-4 h-4 text-white/40" />
            <span className="text-xs font-mono text-white/40">Project</span>
          </div>
          {run.project_id ? (
            <Link
              href={`/dashboard/projects/${run.project_id}`}
              className="text-sm font-mono text-cyan-400 hover:text-cyan-300 hover:underline"
            >
              {run.project_id.slice(0, 16)}...
            </Link>
          ) : (
            <span className="text-sm font-mono text-white/30">Unknown</span>
          )}
        </div>

        {/* Created */}
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-2">
            <Clock className="w-4 h-4 text-white/40" />
            <span className="text-xs font-mono text-white/40">Created</span>
          </div>
          <span className="text-sm font-mono text-white">
            {new Date(run.created_at).toLocaleString()}
          </span>
        </div>

        {/* Updated */}
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-2">
            <RefreshCw className="w-4 h-4 text-white/40" />
            <span className="text-xs font-mono text-white/40">Updated</span>
          </div>
          <span className="text-sm font-mono text-white">
            {new Date(run.updated_at).toLocaleString()}
          </span>
        </div>
      </div>

      {/* Actions for Succeeded Runs */}
      {run.status === 'succeeded' && (
        <div className="bg-green-500/10 border border-green-500/30 p-6 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-mono font-bold text-green-400 mb-1">
                Run Succeeded
              </h3>
              <p className="text-xs font-mono text-white/40">
                View telemetry data, audit report, and replay the simulation (read-only)
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Link href={`/dashboard/runs/${run.run_id}/telemetry`}>
                <Button size="sm">
                  <BarChart3 className="w-3 h-3 mr-2" />
                  TELEMETRY
                </Button>
              </Link>
              <Link href={`/dashboard/runs/${run.run_id}/audit`}>
                <Button variant="secondary" size="sm">
                  <Shield className="w-3 h-3 mr-2" />
                  AUDIT REPORT
                </Button>
              </Link>
              {run.node_id && (
                <Link href={`/dashboard/nodes/${run.node_id}`}>
                  <Button variant="secondary" size="sm">
                    <GitBranch className="w-3 h-3 mr-2" />
                    NODE
                  </Button>
                </Link>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Error Display for Failed Runs */}
      {run.status === 'failed' && run.error && (
        <div className="bg-red-500/10 border border-red-500/30 p-6 mb-6">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="w-4 h-4 text-red-400" />
            <span className="text-sm font-mono font-bold text-red-400">
              Run Failed
            </span>
          </div>
          <pre className="text-xs font-mono text-red-300 bg-black/30 p-3 overflow-x-auto">
            {typeof run.error === 'string' ? run.error : JSON.stringify(run.error, null, 2)}
          </pre>
        </div>
      )}

      {/* Run Details */}
      <div className="bg-white/5 border border-white/10 p-6">
        <div className="flex items-center gap-2 mb-4">
          <Settings className="w-4 h-4 text-white/40" />
          <span className="text-sm font-mono text-white/60 uppercase">Run Details</span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs font-mono">
          <div>
            <span className="text-white/40">Config Ref</span>
            <p className="text-white/60 truncate">{run.run_config_ref || '-'}</p>
          </div>
          <div>
            <span className="text-white/40">Worker ID</span>
            <p className="text-white/60 truncate">{run.worker_id || '-'}</p>
          </div>
          <div>
            <span className="text-white/40">Started</span>
            <p className="text-white/60">{run.timing?.started_at ? new Date(run.timing.started_at).toLocaleString() : '-'}</p>
          </div>
          <div>
            <span className="text-white/40">Ended</span>
            <p className="text-white/60">{run.timing?.ended_at ? new Date(run.timing.ended_at).toLocaleString() : '-'}</p>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-8 pt-4 border-t border-white/5">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1">
              <Terminal className="w-3 h-3" />
              <span>SPEC-COMPLIANT RUN</span>
            </div>
            <div className="flex items-center gap-1">
              <GitBranch className="w-3 h-3" />
              <span>C3: REPLAY READ-ONLY</span>
            </div>
          </div>
          <span>project.md §6.5-6.6</span>
        </div>
      </div>
    </div>
  );
}

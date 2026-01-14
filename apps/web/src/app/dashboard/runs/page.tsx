'use client';

/**
 * Runs List Page
 * Spec-compliant run management using project.md §6.5-6.6
 * Reference: C1 (fork-not-mutate), C3 (replay read-only)
 */

import { useState } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  Plus,
  Play,
  MoreVertical,
  Loader2,
  Search,
  XCircle,
  CheckCircle,
  Clock,
  Activity,
  Eye,
  Terminal,
  GitBranch,
  RefreshCw,
  Pause,
  BarChart3,
  Zap,
  Shield,
  ShieldCheck,
  ShieldX,
} from 'lucide-react';
import { useRuns, useCancelRun, useStartRun } from '@/hooks/useApi';
import type { RunSummary, SpecRunStatus } from '@/lib/api';
import { cn } from '@/lib/utils';

const statusColors: Record<string, { className: string; icon: React.ReactNode; label: string }> = {
  queued: {
    className: 'bg-orange-500/20 text-orange-400',
    icon: <Clock className="w-2.5 h-2.5" />,
    label: 'QUEUED',
  },
  starting: {
    className: 'bg-yellow-500/20 text-yellow-400',
    icon: <Zap className="w-2.5 h-2.5" />,
    label: 'STARTING',
  },
  running: {
    className: 'bg-blue-500/20 text-blue-400 animate-pulse',
    icon: <Activity className="w-2.5 h-2.5" />,
    label: 'RUNNING',
  },
  succeeded: {
    className: 'bg-green-500/20 text-green-400',
    icon: <CheckCircle className="w-2.5 h-2.5" />,
    label: 'SUCCEEDED',
  },
  failed: {
    className: 'bg-red-500/20 text-red-400',
    icon: <XCircle className="w-2.5 h-2.5" />,
    label: 'FAILED',
  },
  cancelled: {
    className: 'bg-white/10 text-white/50',
    icon: <Pause className="w-2.5 h-2.5" />,
    label: 'CANCELLED',
  },
};

export default function RunsPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<SpecRunStatus | ''>('');
  const { data: runs, isLoading, error, refetch } = useRuns(
    statusFilter ? { status: statusFilter } : undefined
  );

  const filteredRuns = runs?.filter(run =>
    !searchQuery ||
    run.run_id.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-black p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Play className="w-4 h-4 text-cyan-400" />
            <span className="text-xs font-mono text-white/40 uppercase tracking-wider">Simulation Engine</span>
          </div>
          <h1 className="text-xl font-mono font-bold text-white">Simulation Runs</h1>
          <p className="text-sm font-mono text-white/50 mt-1">
            Execute and monitor spec-compliant simulations
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" onClick={() => refetch()}>
            <RefreshCw className="w-3 h-3 mr-2" />
            REFRESH
          </Button>
          <Link href="/dashboard/projects">
            <Button size="sm">
              <Plus className="w-3 h-3 mr-2" />
              NEW RUN
            </Button>
          </Link>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="w-4 h-4 text-blue-400" />
            <span className="text-xs font-mono text-white/40">RUNNING</span>
          </div>
          <span className="text-2xl font-mono font-bold text-white">
            {runs?.filter(r => r.status === 'running' || r.status === 'starting').length || 0}
          </span>
        </div>
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-2">
            <Clock className="w-4 h-4 text-yellow-400" />
            <span className="text-xs font-mono text-white/40">QUEUED</span>
          </div>
          <span className="text-2xl font-mono font-bold text-white">
            {runs?.filter(r => r.status === 'queued').length || 0}
          </span>
        </div>
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle className="w-4 h-4 text-green-400" />
            <span className="text-xs font-mono text-white/40">SUCCEEDED</span>
          </div>
          <span className="text-2xl font-mono font-bold text-white">
            {runs?.filter(r => r.status === 'succeeded').length || 0}
          </span>
        </div>
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-2">
            <BarChart3 className="w-4 h-4 text-purple-400" />
            <span className="text-xs font-mono text-white/40">TOTAL</span>
          </div>
          <span className="text-2xl font-mono font-bold text-white">
            {runs?.length || 0}
          </span>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-6">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-white/30" />
          <input
            type="text"
            placeholder="Search runs..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-7 pr-3 py-1.5 bg-white/5 border border-white/10 text-xs font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-cyan-500/50"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as SpecRunStatus | '')}
          className="px-3 py-1.5 bg-white/5 border border-white/10 text-xs font-mono text-white appearance-none focus:outline-none focus:border-cyan-500/50"
        >
          <option value="">All Status</option>
          <option value="queued">Queued</option>
          <option value="starting">Starting</option>
          <option value="running">Running</option>
          <option value="succeeded">Succeeded</option>
          <option value="failed">Failed</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-4 h-4 animate-spin text-cyan-400" />
          <span className="ml-2 text-sm font-mono text-white/40">Loading runs...</span>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 p-4">
          <p className="text-sm font-mono text-red-400">Failed to load runs</p>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => refetch()}
            className="mt-2"
          >
            RETRY
          </Button>
        </div>
      )}

      {/* Runs List */}
      {!isLoading && !error && (
        <>
          {(!filteredRuns || filteredRuns.length === 0) ? (
            <div className="bg-white/5 border border-white/10">
              <div className="p-12 text-center">
                <div className="w-12 h-12 bg-cyan-500/10 flex items-center justify-center mx-auto mb-4">
                  <Play className="w-5 h-5 text-cyan-400" />
                </div>
                <p className="text-sm font-mono text-white/60 mb-1">No simulation runs</p>
                <p className="text-xs font-mono text-white/30 mb-4">
                  Create a project and start your first simulation run
                </p>
                <Link href="/dashboard/projects">
                  <Button size="sm">
                    <Plus className="w-3 h-3 mr-2" />
                    CREATE PROJECT
                  </Button>
                </Link>
              </div>
            </div>
          ) : (
            <div className="bg-white/5 border border-white/10">
              <table className="w-full">
                <thead className="border-b border-white/10">
                  <tr>
                    <th className="text-left px-4 py-3 text-[10px] font-mono text-white/40 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="text-left px-4 py-3 text-[10px] font-mono text-white/40 uppercase tracking-wider">
                      Isolation
                    </th>
                    <th className="text-left px-4 py-3 text-[10px] font-mono text-white/40 uppercase tracking-wider">
                      Run ID
                    </th>
                    <th className="text-left px-4 py-3 text-[10px] font-mono text-white/40 uppercase tracking-wider">
                      Node
                    </th>
                    <th className="text-left px-4 py-3 text-[10px] font-mono text-white/40 uppercase tracking-wider">
                      Progress
                    </th>
                    <th className="text-left px-4 py-3 text-[10px] font-mono text-white/40 uppercase tracking-wider">
                      Ticks
                    </th>
                    <th className="text-left px-4 py-3 text-[10px] font-mono text-white/40 uppercase tracking-wider">
                      Created
                    </th>
                    <th className="text-right px-4 py-3 text-[10px] font-mono text-white/40 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {filteredRuns.map((run) => (
                    <RunRow
                      key={run.run_id}
                      run={run}
                      onUpdate={() => refetch()}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {/* Footer Status */}
      <div className="mt-8 pt-4 border-t border-white/5">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1">
              <Terminal className="w-3 h-3" />
              <span>SPEC-COMPLIANT RUN ENGINE</span>
            </div>
            <div className="flex items-center gap-1">
              <GitBranch className="w-3 h-3" />
              <span>C1: FORK-NOT-MUTATE</span>
            </div>
          </div>
          <span>project.md §6.5-6.6</span>
        </div>
      </div>
    </div>
  );
}

function RunRow({ run, onUpdate }: { run: RunSummary; onUpdate: () => void }) {
  const [showMenu, setShowMenu] = useState(false);
  const cancelRun = useCancelRun();
  const startRun = useStartRun();

  const status = statusColors[run.status] || statusColors.queued;
  const currentTick = run.timing?.current_tick || 0;
  const totalTicks = run.timing?.total_ticks || 0;
  const progress = totalTicks > 0 ? (currentTick / totalTicks) * 100 : 0;

  const handleCancel = async () => {
    if (confirm('Cancel this run?')) {
      try {
        await cancelRun.mutateAsync(run.run_id);
        onUpdate();
      } catch {
        // Error handled by mutation
      }
    }
    setShowMenu(false);
  };

  const handleStart = async () => {
    try {
      await startRun.mutateAsync(run.run_id);
      onUpdate();
    } catch {
      // Error handled by mutation
    }
    setShowMenu(false);
  };

  // Isolation status badge helper
  const renderIsolationBadge = () => {
    if (!run.isolation_status) {
      return (
        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-white/5 text-white/30 text-[10px] font-mono">
          <Shield className="w-2.5 h-2.5" />
          N/A
        </span>
      );
    }
    if (run.isolation_status === 'PASS') {
      return (
        <Link
          href={`/dashboard/runs/${run.run_id}/audit`}
          className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-green-500/20 text-green-400 text-[10px] font-mono hover:bg-green-500/30 transition-colors"
        >
          <ShieldCheck className="w-2.5 h-2.5" />
          PASS
        </Link>
      );
    }
    return (
      <Link
        href={`/dashboard/runs/${run.run_id}/audit`}
        className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-red-500/20 text-red-400 text-[10px] font-mono hover:bg-red-500/30 transition-colors"
      >
        <ShieldX className="w-2.5 h-2.5" />
        FAIL
      </Link>
    );
  };

  return (
    <tr className="hover:bg-white/5 transition-colors">
      <td className="px-4 py-3">
        <span className={cn('inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-mono uppercase', status.className)}>
          {status.icon}
          {status.label}
        </span>
      </td>
      <td className="px-4 py-3">
        {renderIsolationBadge()}
      </td>
      <td className="px-4 py-3">
        <Link
          href={`/dashboard/runs/${run.run_id}`}
          className="text-xs font-mono text-cyan-400 hover:text-cyan-300 hover:underline"
        >
          {run.run_id.slice(0, 12)}...
        </Link>
      </td>
      <td className="px-4 py-3">
        {run.node_id ? (
          <Link
            href={`/dashboard/nodes/${run.node_id}`}
            className="flex items-center gap-1 text-xs font-mono text-white/60 hover:text-white"
          >
            <GitBranch className="w-3 h-3" />
            {run.node_id.slice(0, 8)}
          </Link>
        ) : (
          <span className="text-xs font-mono text-white/30">-</span>
        )}
      </td>
      <td className="px-4 py-3">
        <div className="w-full max-w-[100px]">
          <div className="flex items-center gap-2">
            <div className="flex-1 bg-white/10 h-1">
              <div
                className={cn(
                  'h-1 transition-all',
                  progress >= 100 ? 'bg-green-500' : 'bg-cyan-500'
                )}
                style={{ width: `${Math.min(progress, 100)}%` }}
              />
            </div>
            <span className="text-[10px] font-mono text-white/40 w-8">
              {progress.toFixed(0)}%
            </span>
          </div>
        </div>
      </td>
      <td className="px-4 py-3 text-xs font-mono text-white/60">
        {currentTick}/{totalTicks}
      </td>
      <td className="px-4 py-3 text-[10px] font-mono text-white/30">
        {new Date(run.created_at).toLocaleDateString()}
      </td>
      <td className="px-4 py-3 text-right">
        <div className="relative inline-block">
          <button
            onClick={() => setShowMenu(!showMenu)}
            className="p-1.5 hover:bg-white/10 transition-colors"
          >
            <MoreVertical className="w-3 h-3 text-white/40" />
          </button>
          {showMenu && (
            <>
              <div
                className="fixed inset-0 z-10"
                onClick={() => setShowMenu(false)}
              />
              <div className="absolute right-0 mt-1 w-36 bg-black border border-white/20 py-1 z-20">
                <Link
                  href={`/dashboard/runs/${run.run_id}`}
                  className="flex items-center gap-2 px-3 py-1.5 text-xs font-mono text-white/60 hover:bg-white/10"
                  onClick={() => setShowMenu(false)}
                >
                  <Eye className="w-3 h-3" />
                  View Details
                </Link>
                {run.status === 'succeeded' && (
                  <>
                    <Link
                      href={`/dashboard/runs/${run.run_id}/telemetry`}
                      className="flex items-center gap-2 px-3 py-1.5 text-xs font-mono text-white/60 hover:bg-white/10"
                      onClick={() => setShowMenu(false)}
                    >
                      <BarChart3 className="w-3 h-3" />
                      Telemetry
                    </Link>
                    <Link
                      href={`/dashboard/runs/${run.run_id}/audit`}
                      className="flex items-center gap-2 px-3 py-1.5 text-xs font-mono text-white/60 hover:bg-white/10"
                      onClick={() => setShowMenu(false)}
                    >
                      <Shield className="w-3 h-3" />
                      Audit Report
                    </Link>
                  </>
                )}
                {run.status === 'queued' && (
                  <button
                    onClick={handleStart}
                    disabled={startRun.isPending}
                    className="flex items-center gap-2 w-full px-3 py-1.5 text-xs font-mono text-green-400 hover:bg-white/10 disabled:opacity-50"
                  >
                    <Play className="w-3 h-3" />
                    Start
                  </button>
                )}
                {run.status === 'running' && (
                  <button
                    onClick={handleCancel}
                    disabled={cancelRun.isPending}
                    className="flex items-center gap-2 w-full px-3 py-1.5 text-xs font-mono text-red-400 hover:bg-white/10 disabled:opacity-50"
                  >
                    <XCircle className="w-3 h-3" />
                    Cancel
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      </td>
    </tr>
  );
}

'use client';

/**
 * Backtests Page (PHASE 8)
 * End-to-End Backtest Loop with deterministic multi-run testing.
 * Route: /p/{projectId}/backtests
 *
 * Features:
 * - List all backtests for a project
 * - Create new backtests with configuration
 * - View backtest detail with progress tracking
 * - View individual runs and their status
 * - Generate and view report snapshots
 */

import { useState, useCallback, useMemo } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  FlaskConical,
  Plus,
  Play,
  RotateCcw,
  ChevronRight,
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
  AlertTriangle,
  FileBarChart,
  Settings,
  Hash,
  Calendar,
  GitBranch,
  Target,
  ArrowLeft,
  RefreshCw,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  useBacktests,
  useBacktest,
  useBacktestRuns,
  useCreateBacktest,
  useStartBacktest,
  useResetBacktest,
  useNodes,
} from '@/hooks/useApi';
import type {
  BacktestStatus,
  BacktestResponse,
  BacktestRunResponse,
  BacktestRunStatus,
} from '@/lib/api';

// ============================================================================
// Status Components
// ============================================================================

const statusConfig: Record<BacktestStatus, { icon: React.ElementType; color: string; bg: string }> = {
  created: { icon: Clock, color: 'text-gray-400', bg: 'bg-gray-500/10' },
  running: { icon: Loader2, color: 'text-cyan-400', bg: 'bg-cyan-500/10' },
  succeeded: { icon: CheckCircle2, color: 'text-green-400', bg: 'bg-green-500/10' },
  failed: { icon: XCircle, color: 'text-red-400', bg: 'bg-red-500/10' },
  canceled: { icon: AlertTriangle, color: 'text-amber-400', bg: 'bg-amber-500/10' },
};

const runStatusConfig: Record<BacktestRunStatus, { icon: React.ElementType; color: string }> = {
  pending: { icon: Clock, color: 'text-gray-400' },
  running: { icon: Loader2, color: 'text-cyan-400' },
  succeeded: { icon: CheckCircle2, color: 'text-green-400' },
  failed: { icon: XCircle, color: 'text-red-400' },
  skipped: { icon: AlertTriangle, color: 'text-amber-400' },
};

function BacktestStatusBadge({ status }: { status: BacktestStatus }) {
  const config = statusConfig[status];
  const Icon = config.icon;
  return (
    <div className={cn(
      'inline-flex items-center gap-1.5 px-2 py-0.5 text-xs font-mono',
      config.bg, config.color
    )}>
      <Icon className={cn('w-3 h-3', status === 'running' && 'animate-spin')} />
      {status.toUpperCase()}
    </div>
  );
}

function RunStatusBadge({ status }: { status: BacktestRunStatus }) {
  const config = runStatusConfig[status];
  const Icon = config.icon;
  return (
    <div className={cn('inline-flex items-center gap-1', config.color)}>
      <Icon className={cn('w-3 h-3', status === 'running' && 'animate-spin')} />
      <span className="text-xs font-mono">{status}</span>
    </div>
  );
}

// ============================================================================
// Progress Bar
// ============================================================================

function ProgressBar({ percent }: { percent: number }) {
  return (
    <div className="w-full h-1.5 bg-white/5">
      <div
        className={cn(
          'h-full transition-all duration-300',
          percent >= 100 ? 'bg-green-500' : 'bg-cyan-500'
        )}
        style={{ width: `${Math.min(100, percent)}%` }}
      />
    </div>
  );
}

// ============================================================================
// Create Backtest Form
// ============================================================================

interface CreateBacktestFormProps {
  projectId: string;
  onSuccess: () => void;
  onCancel: () => void;
}

function CreateBacktestForm({ projectId, onSuccess, onCancel }: CreateBacktestFormProps) {
  const [name, setName] = useState('');
  const [topic, setTopic] = useState('');
  const [seed, setSeed] = useState(42);
  const [runsPerNode, setRunsPerNode] = useState(3);
  const [maxTicks, setMaxTicks] = useState(100);
  const [notes, setNotes] = useState('');

  const createBacktest = useCreateBacktest();

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    await createBacktest.mutateAsync({
      projectId,
      data: {
        name,
        topic,
        seed,
        config: {
          runs_per_node: runsPerNode,
          node_ids: [],
          agent_config: {
            max_agents: 100,
            sampling_policy: 'all',
            sampling_ratio: 1.0,
          },
          scenario_config: {
            max_ticks: maxTicks,
            tick_rate: 1,
          },
        },
        notes: notes || undefined,
      },
    });
    onSuccess();
  }, [projectId, name, topic, seed, runsPerNode, maxTicks, notes, createBacktest, onSuccess]);

  return (
    <form onSubmit={handleSubmit} className="border border-white/10 bg-black/50 p-6 space-y-6">
      <div className="flex items-center justify-between border-b border-white/10 pb-4">
        <h3 className="text-lg font-mono text-white flex items-center gap-2">
          <FlaskConical className="w-5 h-5 text-cyan-400" />
          CREATE BACKTEST
        </h3>
        <button
          type="button"
          onClick={onCancel}
          className="text-white/40 hover:text-white text-sm font-mono"
        >
          CANCEL
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Name */}
        <div className="space-y-2">
          <label className="block text-xs font-mono text-white/60 uppercase">Name *</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full bg-white/5 border border-white/10 px-3 py-2 text-sm font-mono text-white placeholder-white/30 focus:border-cyan-500 focus:outline-none"
            placeholder="e.g., US Election 2024 Backtest"
            required
          />
        </div>

        {/* Seed */}
        <div className="space-y-2">
          <label className="block text-xs font-mono text-white/60 uppercase">Base Seed</label>
          <input
            type="number"
            value={seed}
            onChange={(e) => setSeed(parseInt(e.target.value) || 42)}
            className="w-full bg-white/5 border border-white/10 px-3 py-2 text-sm font-mono text-white focus:border-cyan-500 focus:outline-none"
          />
        </div>

        {/* Topic */}
        <div className="md:col-span-2 space-y-2">
          <label className="block text-xs font-mono text-white/60 uppercase">Topic / Description *</label>
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            className="w-full bg-white/5 border border-white/10 px-3 py-2 text-sm font-mono text-white placeholder-white/30 focus:border-cyan-500 focus:outline-none"
            placeholder="e.g., Testing prediction accuracy for November 6, 2024"
            required
          />
        </div>

        {/* Runs Per Node */}
        <div className="space-y-2">
          <label className="block text-xs font-mono text-white/60 uppercase">Runs Per Node</label>
          <input
            type="number"
            value={runsPerNode}
            onChange={(e) => setRunsPerNode(Math.max(1, parseInt(e.target.value) || 3))}
            min={1}
            max={100}
            className="w-full bg-white/5 border border-white/10 px-3 py-2 text-sm font-mono text-white focus:border-cyan-500 focus:outline-none"
          />
          <p className="text-[10px] font-mono text-white/30">
            Number of simulation runs to execute per node (default: 3)
          </p>
        </div>

        {/* Max Ticks */}
        <div className="space-y-2">
          <label className="block text-xs font-mono text-white/60 uppercase">Max Ticks</label>
          <input
            type="number"
            value={maxTicks}
            onChange={(e) => setMaxTicks(Math.max(1, parseInt(e.target.value) || 100))}
            min={1}
            max={10000}
            className="w-full bg-white/5 border border-white/10 px-3 py-2 text-sm font-mono text-white focus:border-cyan-500 focus:outline-none"
          />
          <p className="text-[10px] font-mono text-white/30">
            Maximum simulation ticks per run (default: 100)
          </p>
        </div>

        {/* Notes */}
        <div className="md:col-span-2 space-y-2">
          <label className="block text-xs font-mono text-white/60 uppercase">Notes (Optional)</label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={3}
            className="w-full bg-white/5 border border-white/10 px-3 py-2 text-sm font-mono text-white placeholder-white/30 focus:border-cyan-500 focus:outline-none resize-none"
            placeholder="Additional notes about this backtest..."
          />
        </div>
      </div>

      <div className="flex items-center gap-3 pt-4 border-t border-white/10">
        <Button
          type="submit"
          disabled={!name || !topic || createBacktest.isPending}
          className="bg-cyan-500 hover:bg-cyan-600 text-black font-mono"
        >
          {createBacktest.isPending ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              CREATING...
            </>
          ) : (
            <>
              <Plus className="w-4 h-4 mr-2" />
              CREATE BACKTEST
            </>
          )}
        </Button>
        <p className="text-[10px] font-mono text-white/30">
          This will plan runs for all nodes in the project
        </p>
      </div>
    </form>
  );
}

// ============================================================================
// Backtest Card
// ============================================================================

interface BacktestCardProps {
  backtest: BacktestResponse;
  onClick: () => void;
}

function BacktestCard({ backtest, onClick }: BacktestCardProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full text-left border border-white/10 bg-black/50 hover:bg-white/5 transition-colors p-4"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0 pr-4">
          <h3 className="text-sm font-mono text-white truncate">{backtest.name}</h3>
          <p className="text-xs font-mono text-white/40 mt-0.5 truncate">{backtest.topic}</p>
        </div>
        <BacktestStatusBadge status={backtest.status} />
      </div>

      <ProgressBar percent={backtest.progress_percent} />

      <div className="flex items-center justify-between mt-3">
        <div className="flex items-center gap-4 text-[10px] font-mono text-white/40">
          <span className="flex items-center gap-1">
            <Hash className="w-3 h-3" />
            {backtest.completed_runs}/{backtest.total_planned_runs} runs
          </span>
          {backtest.failed_runs > 0 && (
            <span className="flex items-center gap-1 text-red-400">
              <XCircle className="w-3 h-3" />
              {backtest.failed_runs} failed
            </span>
          )}
          <span className="flex items-center gap-1">
            <Calendar className="w-3 h-3" />
            {new Date(backtest.created_at).toLocaleDateString()}
          </span>
        </div>
        <ChevronRight className="w-4 h-4 text-white/20" />
      </div>
    </button>
  );
}

// ============================================================================
// Backtest Detail View
// ============================================================================

interface BacktestDetailProps {
  projectId: string;
  backtestId: string;
  onBack: () => void;
}

function BacktestDetail({ projectId, backtestId, onBack }: BacktestDetailProps) {
  const { data: backtest, isLoading, refetch } = useBacktest(projectId, backtestId);
  const { data: runsData, isLoading: runsLoading } = useBacktestRuns(projectId, backtestId);
  const startBacktest = useStartBacktest();
  const resetBacktest = useResetBacktest();

  const handleStart = useCallback(async () => {
    await startBacktest.mutateAsync({ projectId, backtestId, sequential: true });
  }, [projectId, backtestId, startBacktest]);

  const handleReset = useCallback(async () => {
    if (window.confirm('Are you sure you want to reset this backtest? This will delete all run data for this backtest only (not global data).')) {
      await resetBacktest.mutateAsync({ projectId, backtestId });
    }
  }, [projectId, backtestId, resetBacktest]);

  if (isLoading || !backtest) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="w-6 h-6 text-cyan-500 animate-spin" />
      </div>
    );
  }

  const canStart = backtest.status === 'created';
  const canReset = backtest.status !== 'running';
  const isRunning = backtest.status === 'running';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <button
            onClick={onBack}
            className="flex items-center gap-1.5 text-xs font-mono text-white/40 hover:text-white mb-2"
          >
            <ArrowLeft className="w-3 h-3" />
            BACK TO LIST
          </button>
          <h2 className="text-xl font-mono text-white">{backtest.name}</h2>
          <p className="text-sm font-mono text-white/40 mt-1">{backtest.topic}</p>
        </div>
        <div className="flex items-center gap-2">
          <BacktestStatusBadge status={backtest.status} />
          {isRunning && (
            <button
              onClick={() => refetch()}
              className="p-1.5 text-white/40 hover:text-white hover:bg-white/5"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Progress */}
      <div className="border border-white/10 bg-black/50 p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-mono text-white/60">PROGRESS</span>
          <span className="text-sm font-mono text-white">
            {backtest.progress_percent.toFixed(1)}%
          </span>
        </div>
        <ProgressBar percent={backtest.progress_percent} />
        <div className="flex items-center gap-6 mt-3 text-xs font-mono text-white/40">
          <span className="flex items-center gap-1.5">
            <CheckCircle2 className="w-3 h-3 text-green-400" />
            {backtest.completed_runs} completed
          </span>
          <span className="flex items-center gap-1.5">
            <XCircle className="w-3 h-3 text-red-400" />
            {backtest.failed_runs} failed
          </span>
          <span className="flex items-center gap-1.5">
            <Clock className="w-3 h-3" />
            {backtest.total_planned_runs - backtest.completed_runs - backtest.failed_runs} pending
          </span>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3">
        {canStart && (
          <Button
            onClick={handleStart}
            disabled={startBacktest.isPending}
            className="bg-cyan-500 hover:bg-cyan-600 text-black font-mono"
          >
            {startBacktest.isPending ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Play className="w-4 h-4 mr-2" />
            )}
            START BACKTEST
          </Button>
        )}
        {canReset && (
          <Button
            onClick={handleReset}
            disabled={resetBacktest.isPending}
            variant="outline"
            className="border-white/20 text-white/60 hover:text-white font-mono"
          >
            {resetBacktest.isPending ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <RotateCcw className="w-4 h-4 mr-2" />
            )}
            RESET
          </Button>
        )}
        <Link
          href={`/p/${projectId}/reports`}
          className="inline-flex items-center gap-2 px-4 py-2 border border-white/20 text-white/60 hover:text-white text-sm font-mono"
        >
          <FileBarChart className="w-4 h-4" />
          VIEW REPORTS
        </Link>
      </div>

      {/* Config */}
      <div className="border border-white/10 bg-black/50 p-4">
        <h3 className="text-xs font-mono text-white/60 uppercase mb-3 flex items-center gap-2">
          <Settings className="w-3 h-3" />
          CONFIGURATION
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm font-mono">
          <div>
            <span className="text-white/40 text-xs">BASE SEED</span>
            <p className="text-white">{backtest.seed}</p>
          </div>
          <div>
            <span className="text-white/40 text-xs">TOTAL RUNS</span>
            <p className="text-white">{backtest.total_planned_runs}</p>
          </div>
          <div>
            <span className="text-white/40 text-xs">CREATED</span>
            <p className="text-white">{new Date(backtest.created_at).toLocaleDateString()}</p>
          </div>
          {backtest.started_at && (
            <div>
              <span className="text-white/40 text-xs">STARTED</span>
              <p className="text-white">{new Date(backtest.started_at).toLocaleString()}</p>
            </div>
          )}
        </div>
        {backtest.notes && (
          <div className="mt-4 pt-4 border-t border-white/10">
            <span className="text-white/40 text-xs font-mono">NOTES</span>
            <p className="text-white/60 text-sm mt-1">{backtest.notes}</p>
          </div>
        )}
      </div>

      {/* Runs */}
      <div className="border border-white/10 bg-black/50">
        <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between">
          <h3 className="text-xs font-mono text-white/60 uppercase flex items-center gap-2">
            <GitBranch className="w-3 h-3" />
            RUNS ({runsData?.total || 0})
          </h3>
          {runsData?.by_status && (
            <div className="flex items-center gap-3 text-xs font-mono">
              {Object.entries(runsData.by_status).map(([status, count]) => (
                count > 0 && (
                  <span key={status} className="flex items-center gap-1 text-white/40">
                    <span className={runStatusConfig[status as BacktestRunStatus]?.color}>
                      {count}
                    </span>
                    {status}
                  </span>
                )
              ))}
            </div>
          )}
        </div>
        <div className="max-h-80 overflow-y-auto">
          {runsLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-5 h-5 text-cyan-500 animate-spin" />
            </div>
          ) : runsData?.items.length === 0 ? (
            <div className="px-4 py-8 text-center text-sm font-mono text-white/40">
              No runs yet. Start the backtest to create runs.
            </div>
          ) : (
            <div className="divide-y divide-white/5">
              {runsData?.items.map((run) => (
                <div key={run.id} className="px-4 py-3 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <RunStatusBadge status={run.status} />
                    <span className="text-xs font-mono text-white/60">
                      Run #{run.run_index + 1}
                    </span>
                    <span className="text-xs font-mono text-white/30">
                      Seed: {run.derived_seed}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    {run.run_id && (
                      <Link
                        href={`/p/${projectId}/run-center?run=${run.run_id}`}
                        className="text-xs font-mono text-cyan-400 hover:text-cyan-300"
                      >
                        View Run
                      </Link>
                    )}
                    {run.error && (
                      <span className="text-xs font-mono text-red-400 truncate max-w-48" title={run.error}>
                        {run.error}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Main Page Component
// ============================================================================

export default function BacktestsPage() {
  const params = useParams();
  const projectId = params.projectId as string;

  const [showCreateForm, setShowCreateForm] = useState(false);
  const [selectedBacktestId, setSelectedBacktestId] = useState<string | null>(null);

  const { data: backtestsData, isLoading, refetch } = useBacktests(projectId);

  const handleCreateSuccess = useCallback(() => {
    setShowCreateForm(false);
    refetch();
  }, [refetch]);

  // If viewing a specific backtest
  if (selectedBacktestId) {
    return (
      <div className="min-h-screen bg-black p-6">
        <div className="max-w-5xl mx-auto">
          <BacktestDetail
            projectId={projectId}
            backtestId={selectedBacktestId}
            onBack={() => setSelectedBacktestId(null)}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black p-6">
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-mono text-white flex items-center gap-3">
              <FlaskConical className="w-6 h-6 text-cyan-400" />
              BACKTESTS
            </h1>
            <p className="text-sm font-mono text-white/40 mt-1">
              End-to-end backtest loop with deterministic multi-run testing
            </p>
          </div>
          {!showCreateForm && (
            <Button
              onClick={() => setShowCreateForm(true)}
              className="bg-cyan-500 hover:bg-cyan-600 text-black font-mono"
            >
              <Plus className="w-4 h-4 mr-2" />
              NEW BACKTEST
            </Button>
          )}
        </div>

        {/* Create Form */}
        {showCreateForm && (
          <CreateBacktestForm
            projectId={projectId}
            onSuccess={handleCreateSuccess}
            onCancel={() => setShowCreateForm(false)}
          />
        )}

        {/* Backtests List */}
        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-6 h-6 text-cyan-500 animate-spin" />
          </div>
        ) : backtestsData?.items.length === 0 ? (
          <div className="border border-white/10 bg-black/50 p-12 text-center">
            <FlaskConical className="w-12 h-12 text-white/20 mx-auto mb-4" />
            <h3 className="text-lg font-mono text-white mb-2">No Backtests Yet</h3>
            <p className="text-sm font-mono text-white/40 mb-6">
              Create your first backtest to start testing prediction accuracy.
            </p>
            {!showCreateForm && (
              <Button
                onClick={() => setShowCreateForm(true)}
                className="bg-cyan-500 hover:bg-cyan-600 text-black font-mono"
              >
                <Plus className="w-4 h-4 mr-2" />
                CREATE FIRST BACKTEST
              </Button>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {backtestsData?.items.map((backtest) => (
              <BacktestCard
                key={backtest.id}
                backtest={backtest}
                onClick={() => setSelectedBacktestId(backtest.id)}
              />
            ))}
          </div>
        )}

        {/* Info Box */}
        <div className="border border-white/10 bg-black/50 p-4">
          <h3 className="text-xs font-mono text-white/60 uppercase mb-2 flex items-center gap-2">
            <Target className="w-3 h-3" />
            ABOUT BACKTESTS
          </h3>
          <div className="text-xs font-mono text-white/40 space-y-1">
            <p>Backtests execute multiple deterministic simulation runs across all nodes.</p>
            <p>Each run uses a derived seed (hash of base seed + node ID + run index) for reproducibility.</p>
            <p>Reset operations are SCOPED-SAFE - they only delete data for that specific backtest.</p>
          </div>
        </div>
      </div>
    </div>
  );
}

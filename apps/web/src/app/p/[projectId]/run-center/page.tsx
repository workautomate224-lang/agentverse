'use client';

/**
 * Run Center Page
 * Configure and execute simulation runs with node-aware targeting
 */

import { useState, useEffect } from 'react';
import { useParams, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  Play,
  ArrowLeft,
  ArrowRight,
  Terminal,
  Clock,
  Settings,
  History,
  Gauge,
  Zap,
  X,
  Loader2,
  CheckCircle,
  AlertCircle,
  ExternalLink,
  Users,
  FileText,
  RefreshCw,
  StopCircle,
  GitBranch,
  Target,
  Circle,
  ChevronRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  useRuns,
  useRun,
  useCreateRun,
  useStartRun,
  useCancelRun,
  useRunProgress,
  useProjectPersonas,
  useNodes,
} from '@/hooks/useApi';
import type { RunSummary, SubmitRunInput, NodeSummary, SpecRun } from '@/lib/api';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from '@/hooks/use-toast';

// Run configuration options
const runOptions = [
  {
    id: 'baseline',
    name: 'Baseline Run',
    description: 'Standard simulation with default parameters',
    icon: Play,
    color: 'green',
    config: {
      run_mode: 'baseline',
      max_ticks: 100,
      agent_batch_size: 10,
    },
  },
  {
    id: 'quick',
    name: 'Quick Test',
    description: 'Faster run with reduced agent count',
    icon: Zap,
    color: 'yellow',
    config: {
      run_mode: 'quick_test',
      max_ticks: 25,
      agent_batch_size: 5,
    },
  },
  {
    id: 'custom',
    name: 'Custom Run',
    description: 'Configure all parameters manually',
    icon: Settings,
    color: 'purple',
    config: {},
  },
];

// Format date for display
function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

// Format duration
function formatDuration(startedAt?: string, endedAt?: string): string {
  if (!startedAt) return '--';
  const start = new Date(startedAt);
  const end = endedAt ? new Date(endedAt) : new Date();
  const diffMs = end.getTime() - start.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  if (diffSec < 60) return `${diffSec}s`;
  const diffMin = Math.floor(diffSec / 60);
  return `${diffMin}m ${diffSec % 60}s`;
}

// Status badge component
function StatusBadge({ status }: { status: string }) {
  const statusConfig: Record<string, { color: string; icon: React.ReactNode }> = {
    queued: { color: 'text-blue-400 bg-blue-400/10', icon: <Clock className="w-3 h-3" /> },
    starting: { color: 'text-yellow-400 bg-yellow-400/10', icon: <Loader2 className="w-3 h-3 animate-spin" /> },
    running: { color: 'text-cyan-400 bg-cyan-400/10', icon: <Loader2 className="w-3 h-3 animate-spin" /> },
    succeeded: { color: 'text-green-400 bg-green-400/10', icon: <CheckCircle className="w-3 h-3" /> },
    failed: { color: 'text-red-400 bg-red-400/10', icon: <AlertCircle className="w-3 h-3" /> },
    cancelled: { color: 'text-white/40 bg-white/10', icon: <StopCircle className="w-3 h-3" /> },
  };

  const config = statusConfig[status] || statusConfig.queued;

  return (
    <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-mono uppercase', config.color)}>
      {config.icon}
      {status}
    </span>
  );
}

// Pre-flight Validation Modal - shown when personas/rules are missing
function PreFlightValidationModal({
  open,
  onClose,
  projectId,
  personaCount,
}: {
  open: boolean;
  onClose: () => void;
  projectId: string;
  personaCount: number;
}) {
  const hasPersonas = personaCount > 0;

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="bg-black border border-red-500/30 max-w-md">
        <DialogHeader>
          <DialogTitle className="text-white font-mono flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-red-400" />
            Cannot Start Simulation
          </DialogTitle>
          <DialogDescription className="text-white/50 font-mono text-xs">
            Your project is missing required configuration
          </DialogDescription>
        </DialogHeader>

        <div className="py-4 space-y-4">
          <div className="p-4 bg-red-500/10 border border-red-500/30">
            <p className="text-sm font-mono text-red-400 mb-3">
              You need Personas and Rules configured before running a simulation.
            </p>
            <ul className="space-y-2 text-sm font-mono">
              <li className={cn(
                'flex items-center gap-2',
                hasPersonas ? 'text-green-400' : 'text-red-400'
              )}>
                {hasPersonas ? (
                  <CheckCircle className="w-4 h-4" />
                ) : (
                  <X className="w-4 h-4" />
                )}
                <span>Personas: {personaCount} configured</span>
              </li>
              <li className="flex items-center gap-2 text-yellow-400">
                <AlertCircle className="w-4 h-4" />
                <span>Rules: Configure in Rules page</span>
              </li>
            </ul>
          </div>
        </div>

        <DialogFooter className="flex flex-col sm:flex-row gap-2">
          <Link href={`/p/${projectId}/data-personas`} className="w-full sm:w-auto">
            <Button
              size="sm"
              className={cn(
                'w-full text-xs font-mono',
                hasPersonas
                  ? 'bg-white/10 text-white/60'
                  : 'bg-cyan-500 hover:bg-cyan-600 text-black'
              )}
            >
              <Users className="w-3 h-3 mr-2" />
              {hasPersonas ? 'View Personas' : 'Add Personas'}
            </Button>
          </Link>
          <Link href={`/p/${projectId}/rules`} className="w-full sm:w-auto">
            <Button
              size="sm"
              className="w-full text-xs font-mono bg-purple-500 hover:bg-purple-600"
            >
              <FileText className="w-3 h-3 mr-2" />
              Configure Rules
            </Button>
          </Link>
          <Button variant="ghost" size="sm" onClick={onClose} className="w-full sm:w-auto">
            Cancel
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Custom Run Modal
function CustomRunModal({
  open,
  onClose,
  onSubmit,
  isSubmitting,
}: {
  open: boolean;
  onClose: () => void;
  onSubmit: (config: SubmitRunInput['config']) => void;
  isSubmitting: boolean;
}) {
  const [maxTicks, setMaxTicks] = useState(100);
  const [agentBatchSize, setAgentBatchSize] = useState(10);
  const [label, setLabel] = useState('');

  const handleSubmit = () => {
    onSubmit({
      run_mode: 'custom',
      max_ticks: maxTicks,
      agent_batch_size: agentBatchSize,
    });
  };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="bg-black border border-white/10 max-w-md">
        <DialogHeader>
          <DialogTitle className="text-white font-mono flex items-center gap-2">
            <Settings className="w-5 h-5 text-purple-400" />
            Custom Run Configuration
          </DialogTitle>
          <DialogDescription className="text-white/50 font-mono text-xs">
            Configure simulation parameters for your custom run
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div>
            <label className="block text-xs font-mono text-white/60 mb-2">Label (optional)</label>
            <input
              type="text"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="e.g., Market Analysis v2"
              className="w-full px-3 py-2 bg-white/5 border border-white/10 text-sm font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-cyan-500/50"
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-white/60 mb-2">
              Simulation Horizon (max ticks)
            </label>
            <input
              type="number"
              min={10}
              max={1000}
              value={maxTicks}
              onChange={(e) => setMaxTicks(Number(e.target.value))}
              className="w-full px-3 py-2 bg-white/5 border border-white/10 text-sm font-mono text-white focus:outline-none focus:border-cyan-500/50"
            />
            <p className="text-[10px] font-mono text-white/40 mt-1">
              Number of simulation ticks to run (10-1000)
            </p>
          </div>

          <div>
            <label className="block text-xs font-mono text-white/60 mb-2">Agent Batch Size</label>
            <input
              type="number"
              min={1}
              max={50}
              value={agentBatchSize}
              onChange={(e) => setAgentBatchSize(Number(e.target.value))}
              className="w-full px-3 py-2 bg-white/5 border border-white/10 text-sm font-mono text-white focus:outline-none focus:border-cyan-500/50"
            />
            <p className="text-[10px] font-mono text-white/40 mt-1">
              Number of agents to process per batch (1-50)
            </p>
          </div>
        </div>

        <DialogFooter className="flex justify-end gap-2">
          <Button variant="ghost" size="sm" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="bg-purple-500 hover:bg-purple-600"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-3 h-3 mr-2 animate-spin" />
                Starting...
              </>
            ) : (
              <>
                <Play className="w-3 h-3 mr-2" />
                Start Custom Run
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Run Details Modal
function RunDetailsModal({
  run,
  open,
  onClose,
  projectId,
}: {
  run: RunSummary | null;
  open: boolean;
  onClose: () => void;
  projectId: string;
}) {
  const { data: progress } = useRunProgress(
    run && ['running', 'starting', 'queued'].includes(run.status) ? run.run_id : undefined
  );
  // Fetch full run details to get error info for failed runs
  const { data: fullRun } = useRun(
    run?.status === 'failed' ? run.run_id : undefined
  );
  const cancelRun = useCancelRun();

  if (!run) return null;

  const isRunning = ['running', 'starting', 'queued'].includes(run.status);
  const isCompleted = run.status === 'succeeded';
  const isFailed = run.status === 'failed';
  const runError = (fullRun as SpecRun | undefined)?.error;

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className={cn(
        "bg-black max-w-lg",
        isFailed ? "border border-red-500/30" : "border border-white/10"
      )}>
        <DialogHeader>
          <DialogTitle className="text-white font-mono flex items-center gap-2">
            {isFailed ? (
              <AlertCircle className="w-5 h-5 text-red-400" />
            ) : (
              <History className="w-5 h-5 text-cyan-400" />
            )}
            Run Details
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-white/60">Status</span>
            <StatusBadge status={progress?.status || run.status} />
          </div>

          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-white/60">Run ID</span>
            <span className="text-xs font-mono text-white/80">{run.run_id.slice(0, 12)}...</span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-white/60">Created</span>
            <span className="text-xs font-mono text-white/80">{formatDate(run.created_at)}</span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-white/60">Duration</span>
            <span className="text-xs font-mono text-white/80">
              {formatDuration(run.timing?.started_at, run.timing?.ended_at)}
            </span>
          </div>

          {(progress || run.timing) && (
            <div className="bg-white/5 border border-white/10 p-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-mono text-white/60">Progress</span>
                <span className="text-xs font-mono text-white/80">
                  Tick {progress?.current_tick || run.timing?.current_tick || 0} /{' '}
                  {run.timing?.total_ticks || '?'}
                </span>
              </div>
              <div className="h-1 bg-white/10 rounded-full overflow-hidden">
                <div
                  className={cn(
                    "h-full transition-all",
                    isFailed ? "bg-red-500" : "bg-cyan-500"
                  )}
                  style={{
                    width: `${
                      run.timing?.total_ticks
                        ? ((progress?.current_tick || run.timing?.current_tick || 0) /
                            run.timing.total_ticks) *
                          100
                        : 0
                    }%`,
                  }}
                />
              </div>
            </div>
          )}

          {/* Error Details Section for Failed Runs */}
          {isFailed && (
            <div className="bg-red-500/10 border border-red-500/30 p-4 space-y-3">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-red-400" />
                <span className="text-sm font-mono font-bold text-red-400">Run Failed</span>
              </div>
              {runError ? (
                <>
                  <div>
                    <span className="text-[10px] font-mono text-white/40 uppercase">Error Code</span>
                    <p className="text-xs font-mono text-red-400">{runError.error_code}</p>
                  </div>
                  <div>
                    <span className="text-[10px] font-mono text-white/40 uppercase">Error Message</span>
                    <p className="text-xs font-mono text-white/80">{runError.error_message}</p>
                  </div>
                  {runError.tick_at_failure !== undefined && (
                    <div>
                      <span className="text-[10px] font-mono text-white/40 uppercase">Failed At Tick</span>
                      <p className="text-xs font-mono text-white/80">{runError.tick_at_failure}</p>
                    </div>
                  )}
                  {runError.stack_trace && (
                    <div>
                      <span className="text-[10px] font-mono text-white/40 uppercase">Stack Trace</span>
                      <pre className="text-[10px] font-mono text-white/60 bg-black/50 p-2 mt-1 overflow-x-auto max-h-32">
                        {runError.stack_trace}
                      </pre>
                    </div>
                  )}
                </>
              ) : fullRun ? (
                // Run data loaded but no error field - show available info
                <div className="space-y-2">
                  <p className="text-xs font-mono text-white/60">
                    The simulation ended with status &quot;failed&quot;.
                  </p>
                  {(fullRun as SpecRun)?.ticks_completed !== undefined && (
                    <div>
                      <span className="text-[10px] font-mono text-white/40 uppercase">Ticks Completed</span>
                      <p className="text-xs font-mono text-white/80">{(fullRun as SpecRun).ticks_completed}</p>
                    </div>
                  )}
                  {(fullRun as SpecRun)?.duration_seconds !== undefined && (
                    <div>
                      <span className="text-[10px] font-mono text-white/40 uppercase">Duration</span>
                      <p className="text-xs font-mono text-white/80">{(fullRun as SpecRun).duration_seconds?.toFixed(2)}s</p>
                    </div>
                  )}
                  <p className="text-[10px] font-mono text-white/40 mt-2">
                    No detailed error information available from backend.
                  </p>
                </div>
              ) : (
                <p className="text-xs font-mono text-white/60">
                  Loading run details...
                </p>
              )}
            </div>
          )}
        </div>

        <DialogFooter className="flex justify-end gap-2">
          {isRunning && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => cancelRun.mutate(run.run_id)}
              disabled={cancelRun.isPending}
              className="border-red-500/30 text-red-400 hover:bg-red-500/10"
            >
              {cancelRun.isPending ? (
                <Loader2 className="w-3 h-3 mr-2 animate-spin" />
              ) : (
                <StopCircle className="w-3 h-3 mr-2" />
              )}
              Cancel Run
            </Button>
          )}

          {isCompleted && run.has_results && (
            <Link href={`/p/${projectId}/results?run=${run.run_id}`}>
              <Button size="sm" className="bg-cyan-500 hover:bg-cyan-600">
                <ExternalLink className="w-3 h-3 mr-2" />
                View Results
              </Button>
            </Link>
          )}

          {isCompleted && (
            <Link href={`/p/${projectId}/replay?run=${run.run_id}`}>
              <Button size="sm" variant="outline">
                <Play className="w-3 h-3 mr-2" />
                Open Replay
              </Button>
            </Link>
          )}

          <Button variant="ghost" size="sm" onClick={onClose}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Node Selector Modal
function NodeSelectorModal({
  open,
  onClose,
  onSelect,
  nodes,
  isLoading,
  currentNodeId,
}: {
  open: boolean;
  onClose: () => void;
  onSelect: (node: NodeSummary | null) => void;
  nodes: NodeSummary[] | undefined;
  isLoading: boolean;
  currentNodeId: string | null;
}) {
  // Separate baseline and fork nodes
  const baselineNode = nodes?.find((n) => n.is_baseline);
  const forkNodes = nodes?.filter((n) => !n.is_baseline) || [];

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="bg-black border border-white/10 max-w-md">
        <DialogHeader>
          <DialogTitle className="text-white font-mono flex items-center gap-2">
            <GitBranch className="w-5 h-5 text-cyan-400" />
            Select Target Node
          </DialogTitle>
          <DialogDescription className="text-white/50 font-mono text-xs">
            Choose which node to run the simulation on
          </DialogDescription>
        </DialogHeader>

        <div className="py-4 space-y-2 max-h-[400px] overflow-y-auto">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 text-white/40 animate-spin" />
            </div>
          ) : (
            <>
              {/* Baseline Node */}
              <button
                onClick={() => onSelect(baselineNode || null)}
                className={cn(
                  'w-full p-3 flex items-center gap-3 border transition-colors text-left',
                  currentNodeId === null || currentNodeId === baselineNode?.node_id
                    ? 'bg-cyan-500/10 border-cyan-500/50'
                    : 'bg-white/5 border-white/10 hover:border-white/30'
                )}
              >
                <div className="w-8 h-8 bg-green-500/20 flex items-center justify-center">
                  <Circle className="w-4 h-4 text-green-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-mono text-white">Baseline (Root Node)</p>
                  <p className="text-[10px] font-mono text-white/40">Original simulation starting point</p>
                </div>
                {(currentNodeId === null || currentNodeId === baselineNode?.node_id) && (
                  <CheckCircle className="w-4 h-4 text-cyan-400 flex-shrink-0" />
                )}
              </button>

              {/* Fork Nodes */}
              {forkNodes.length > 0 && (
                <div className="mt-4">
                  <p className="text-[10px] font-mono text-white/40 uppercase tracking-wider mb-2 px-1">
                    Fork Nodes ({forkNodes.length})
                  </p>
                  <div className="space-y-1">
                    {forkNodes.map((node) => (
                      <button
                        key={node.node_id}
                        onClick={() => onSelect(node)}
                        className={cn(
                          'w-full p-3 flex items-center gap-3 border transition-colors text-left',
                          currentNodeId === node.node_id
                            ? 'bg-cyan-500/10 border-cyan-500/50'
                            : 'bg-white/5 border-white/10 hover:border-white/30'
                        )}
                      >
                        <div className="w-8 h-8 bg-purple-500/20 flex items-center justify-center">
                          <GitBranch className="w-4 h-4 text-purple-400" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-mono text-white truncate">
                            {node.label || `Fork ${node.node_id.slice(0, 8)}`}
                          </p>
                          <div className="flex items-center gap-2 text-[10px] font-mono text-white/40">
                            <span>{Math.round(node.probability * 100)}% probability</span>
                            <span>•</span>
                            <span className={cn(
                              node.confidence_level === 'high' ? 'text-green-400' :
                              node.confidence_level === 'medium' ? 'text-yellow-400' : 'text-red-400'
                            )}>
                              {node.confidence_level} confidence
                            </span>
                          </div>
                        </div>
                        {currentNodeId === node.node_id && (
                          <CheckCircle className="w-4 h-4 text-cyan-400 flex-shrink-0" />
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {forkNodes.length === 0 && (
                <div className="py-4 text-center">
                  <p className="text-xs font-mono text-white/40">
                    No fork nodes yet. Create forks in the Event Lab.
                  </p>
                </div>
              )}
            </>
          )}
        </div>

        <DialogFooter>
          <Button variant="ghost" size="sm" onClick={onClose}>
            Cancel
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function RunCenterPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const projectId = params.projectId as string;
  const queryClient = useQueryClient();

  // Node selection state - read initial value from URL
  const initialNodeId = searchParams.get('node');
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(initialNodeId);
  const [showNodeSelector, setShowNodeSelector] = useState(false);

  // Node filter for run history
  const [nodeFilter, setNodeFilter] = useState<'all' | 'baseline' | 'selected'>('all');

  // Modal states
  const [customRunModalOpen, setCustomRunModalOpen] = useState(false);
  const [selectedRun, setSelectedRun] = useState<RunSummary | null>(null);
  const [runDetailsModalOpen, setRunDetailsModalOpen] = useState(false);
  const [preFlightModalOpen, setPreFlightModalOpen] = useState(false);

  // Track active run for progress polling
  const [activeRunId, setActiveRunId] = useState<string | null>(null);

  // API hooks
  const { data: nodes, isLoading: nodesLoading } = useNodes({ project_id: projectId });
  const { data: runs, isLoading: runsLoading, refetch: refetchRuns } = useRuns({ project_id: projectId, limit: 20 });
  const { data: projectPersonas } = useProjectPersonas(projectId);
  const createRun = useCreateRun();
  const startRun = useStartRun();
  const { data: activeRunProgress } = useRunProgress(activeRunId || undefined);

  // Count DB-persisted personas for this project
  const personaCount = projectPersonas?.length || 0;

  // Get selected node data
  const baselineNode = nodes?.find((n) => n.is_baseline);
  const selectedNode = selectedNodeId
    ? nodes?.find((n) => n.node_id === selectedNodeId)
    : baselineNode;
  const isBaseline = !selectedNodeId || selectedNodeId === baselineNode?.node_id;

  // Filter runs based on node filter
  const filteredRuns = runs?.filter((run) => {
    if (nodeFilter === 'all') return true;
    if (nodeFilter === 'baseline') return !run.node_id || run.node_id === baselineNode?.node_id;
    if (nodeFilter === 'selected' && selectedNodeId) return run.node_id === selectedNodeId;
    return true;
  });

  // Count completed runs
  const completedRuns = runs?.filter((r) => r.status === 'succeeded').length || 0;

  // Find any running runs and track them
  useEffect(() => {
    const runningRun = runs?.find((r) => ['running', 'starting', 'queued'].includes(r.status));
    if (runningRun) {
      setActiveRunId(runningRun.run_id);
    } else {
      setActiveRunId(null);
    }
  }, [runs]);

  // Refetch runs when active run completes
  useEffect(() => {
    if (activeRunProgress && ['succeeded', 'failed', 'cancelled'].includes(activeRunProgress.status)) {
      refetchRuns();
      setActiveRunId(null);
    }
  }, [activeRunProgress, refetchRuns]);

  // Handle starting a run with pre-flight validation
  const handleStartRun = async (runType: string, config?: SubmitRunInput['config']) => {
    // Pre-flight validation: check if personas exist
    if (personaCount === 0) {
      setPreFlightModalOpen(true);
      return;
    }

    const runConfig = runOptions.find((o) => o.id === runType)?.config || config || {};

    // Build label with node context
    const nodeLabel = isBaseline
      ? 'Baseline'
      : selectedNode?.label || `Fork ${selectedNodeId?.slice(0, 8)}`;
    const runLabel = `${runType.charAt(0).toUpperCase() + runType.slice(1)} Run - ${nodeLabel}`;

    const runInput: SubmitRunInput = {
      project_id: projectId,
      label: runLabel,
      config: runConfig,
      auto_start: true,
      // Pass the selected node_id (null for baseline uses project default)
      node_id: isBaseline ? undefined : selectedNodeId || undefined,
    };

    try {
      const newRun = await createRun.mutateAsync(runInput);
      setActiveRunId(newRun.run_id);

      // Show success toast
      toast({
        title: 'Simulation Started',
        description: `${runLabel} is now running.`,
      });

      refetchRuns();

      // If not auto-started, start it manually
      if (newRun.status === 'queued') {
        await startRun.mutateAsync(newRun.run_id);
      }
    } catch (error) {
      // Extract error message from the error
      const errorMessage = error instanceof Error
        ? error.message
        : 'An unknown error occurred';

      // Show error toast with real error message
      toast({
        title: 'Failed to Start Run',
        description: errorMessage,
        variant: 'destructive',
      });

      // Refetch to show any partially created run
      refetchRuns();
    }
  };

  // Handle node selection
  const handleNodeSelect = (node: NodeSummary | null) => {
    setSelectedNodeId(node?.is_baseline ? null : node?.node_id || null);
    setShowNodeSelector(false);
  };

  // Invalidate related queries when run completes
  useEffect(() => {
    if (activeRunProgress && ['succeeded', 'failed', 'cancelled'].includes(activeRunProgress.status)) {
      // Invalidate universe map and nodes to reflect new status
      queryClient.invalidateQueries({ queryKey: ['nodes'] });
      queryClient.invalidateQueries({ queryKey: ['universe-map'] });
    }
  }, [activeRunProgress, queryClient]);

  // Check if run endpoints are available
  const isRunEndpointAvailable =
    !createRun.error || (createRun.error as Error)?.message !== 'Network Error';

  return (
    <div className="min-h-screen bg-black p-4 md:p-6">
      {/* Header */}
      <div className="mb-6 md:mb-8">
        <div className="flex items-center gap-2 mb-3">
          <Link href={`/p/${projectId}/rules`}>
            <Button variant="ghost" size="sm" className="text-[10px] md:text-xs">
              <ArrowLeft className="w-3 h-3 mr-1 md:mr-2" />
              BACK TO RULES
            </Button>
          </Link>
        </div>
        <div className="flex items-center gap-2 mb-1">
          <Play className="w-3.5 h-3.5 md:w-4 md:h-4 text-green-400" />
          <span className="text-[10px] md:text-xs font-mono text-white/40 uppercase tracking-wider">
            Run Center
          </span>
        </div>
        <h1 className="text-lg md:text-xl font-mono font-bold text-white">Simulation Runs</h1>
        <p className="text-xs md:text-sm font-mono text-white/50 mt-1">
          Configure and execute simulation runs for your project
        </p>
      </div>

      {/* Run Context - Node Selection */}
      <div className="max-w-3xl mb-6">
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Target className="w-4 h-4 text-cyan-400" />
                <span className="text-xs font-mono text-white/60 uppercase tracking-wider">
                  Run Target
                </span>
              </div>
              <div className="flex items-center gap-3">
                {isBaseline ? (
                  <>
                    <div className="w-8 h-8 bg-green-500/20 flex items-center justify-center">
                      <Circle className="w-4 h-4 text-green-400" />
                    </div>
                    <div>
                      <p className="text-sm font-mono text-white font-bold">Baseline (Root Node)</p>
                      <p className="text-[10px] font-mono text-white/40">Original simulation</p>
                    </div>
                  </>
                ) : selectedNode ? (
                  <>
                    <div className="w-8 h-8 bg-purple-500/20 flex items-center justify-center">
                      <GitBranch className="w-4 h-4 text-purple-400" />
                    </div>
                    <div>
                      <p className="text-sm font-mono text-white font-bold truncate max-w-[200px]">
                        {selectedNode.label || `Fork ${selectedNode.node_id.slice(0, 8)}`}
                      </p>
                      <div className="flex items-center gap-2 text-[10px] font-mono text-white/40">
                        <span>{Math.round(selectedNode.probability * 100)}% probability</span>
                        <span>•</span>
                        <span className={cn(
                          selectedNode.confidence_level === 'high' ? 'text-green-400' :
                          selectedNode.confidence_level === 'medium' ? 'text-yellow-400' : 'text-red-400'
                        )}>
                          {selectedNode.confidence_level}
                        </span>
                      </div>
                    </div>
                  </>
                ) : (
                  <span className="text-sm font-mono text-white/40">Loading...</span>
                )}
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowNodeSelector(true)}
              className="text-xs font-mono"
            >
              <GitBranch className="w-3 h-3 mr-2" />
              Change Target
            </Button>
          </div>
        </div>
      </div>

      {/* Run Options */}
      <div className="max-w-3xl mb-8">
        <h2 className="text-xs font-mono text-white/40 uppercase tracking-wider mb-4">Start New Run</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {runOptions.map((option) => {
            const Icon = option.icon;
            const colorClasses = {
              green: 'hover:bg-green-500/10 hover:border-green-500/30',
              yellow: 'hover:bg-yellow-500/10 hover:border-yellow-500/30',
              purple: 'hover:bg-purple-500/10 hover:border-purple-500/30',
            }[option.color];

            const iconColor = {
              green: 'text-green-400',
              yellow: 'text-yellow-400',
              purple: 'text-purple-400',
            }[option.color];

            const isDisabled = createRun.isPending || startRun.isPending || !!activeRunId;

            return (
              <button
                key={option.id}
                onClick={() => {
                  if (option.id === 'custom') {
                    setCustomRunModalOpen(true);
                  } else {
                    handleStartRun(option.id);
                  }
                }}
                disabled={isDisabled}
                className={cn(
                  'flex flex-col items-center gap-3 p-4 bg-white/5 border border-white/10 transition-all text-center',
                  isDisabled ? 'opacity-50 cursor-not-allowed' : colorClasses
                )}
              >
                <div className="w-12 h-12 bg-white/5 flex items-center justify-center">
                  {(createRun.isPending || startRun.isPending) && option.id !== 'custom' ? (
                    <Loader2 className={cn('w-6 h-6 animate-spin', iconColor)} />
                  ) : (
                    <Icon className={cn('w-6 h-6', iconColor)} />
                  )}
                </div>
                <div>
                  <h3 className="text-sm font-mono font-bold text-white">{option.name}</h3>
                  <p className="text-[10px] font-mono text-white/50 mt-1">{option.description}</p>
                </div>
              </button>
            );
          })}
        </div>

        {activeRunId && (
          <div className="mt-4 p-3 bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Loader2 className="w-4 h-4 text-cyan-400 animate-spin" />
              <span className="text-xs font-mono text-cyan-400">
                Run in progress - Tick {activeRunProgress?.current_tick || 0}
              </span>
            </div>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                const run = runs?.find((r) => r.run_id === activeRunId);
                if (run) {
                  setSelectedRun(run);
                  setRunDetailsModalOpen(true);
                }
              }}
            >
              View Details
            </Button>
          </div>
        )}

        {!isRunEndpointAvailable && (
          <div className="mt-4 p-3 bg-yellow-500/10 border border-yellow-500/30 text-yellow-400 text-xs font-mono">
            <AlertCircle className="w-4 h-4 inline mr-2" />
            Run endpoints not available. Backend integration coming soon.
          </div>
        )}
      </div>

      {/* Quick Stats */}
      <div className="max-w-3xl mb-8">
        <h2 className="text-xs font-mono text-white/40 uppercase tracking-wider mb-4">
          Configuration Summary
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="bg-white/5 border border-white/10 p-4">
            <div className="flex items-center gap-2 text-white/40 mb-2">
              <Clock className="w-3.5 h-3.5" />
              <span className="text-[10px] font-mono uppercase">Horizon</span>
            </div>
            <p className="text-lg font-mono font-bold text-white">100</p>
            <p className="text-[10px] font-mono text-white/40">ticks</p>
          </div>
          <div className={cn(
            "p-4 border",
            personaCount === 0
              ? "bg-red-500/10 border-red-500/30"
              : "bg-white/5 border-white/10"
          )}>
            <div className={cn(
              "flex items-center gap-2 mb-2",
              personaCount === 0 ? "text-red-400" : "text-white/40"
            )}>
              <Users className="w-3.5 h-3.5" />
              <span className="text-[10px] font-mono uppercase">Personas</span>
            </div>
            <p className={cn(
              "text-lg font-mono font-bold",
              personaCount === 0 ? "text-red-400" : "text-white"
            )}>{personaCount}</p>
            <p className={cn(
              "text-[10px] font-mono",
              personaCount === 0 ? "text-red-400/60" : "text-white/40"
            )}>
              {personaCount === 0 ? "required" : "configured"}
            </p>
          </div>
          <div className="bg-white/5 border border-white/10 p-4">
            <div className="flex items-center gap-2 text-white/40 mb-2">
              <FileText className="w-3.5 h-3.5" />
              <span className="text-[10px] font-mono uppercase">Rules</span>
            </div>
            <p className="text-lg font-mono font-bold text-white">--</p>
            <p className="text-[10px] font-mono text-white/40">defined</p>
          </div>
          <div className="bg-white/5 border border-white/10 p-4">
            <div className="flex items-center gap-2 text-white/40 mb-2">
              <History className="w-3.5 h-3.5" />
              <span className="text-[10px] font-mono uppercase">Runs</span>
            </div>
            <p className="text-lg font-mono font-bold text-white">{completedRuns}</p>
            <p className="text-[10px] font-mono text-white/40">completed</p>
          </div>
        </div>
      </div>

      {/* Run History */}
      <div className="max-w-3xl mb-8">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-4">
            <h2 className="text-xs font-mono text-white/40 uppercase tracking-wider">Run History</h2>
            {/* Node Filter */}
            <select
              value={nodeFilter}
              onChange={(e) => setNodeFilter(e.target.value as 'all' | 'baseline' | 'selected')}
              className="bg-white/5 border border-white/10 text-xs font-mono text-white/80 px-2 py-1 focus:outline-none focus:border-cyan-500/50"
            >
              <option value="all">All Nodes</option>
              <option value="baseline">Baseline Only</option>
              {selectedNodeId && <option value="selected">Selected Node</option>}
            </select>
          </div>
          <Button variant="ghost" size="sm" onClick={() => refetchRuns()} disabled={runsLoading}>
            <RefreshCw className={cn('w-3 h-3 mr-1', runsLoading && 'animate-spin')} />
            Refresh
          </Button>
        </div>

        {runsLoading ? (
          <div className="bg-white/5 border border-white/10 p-8 text-center">
            <Loader2 className="w-8 h-8 text-white/40 animate-spin mx-auto mb-4" />
            <p className="text-xs font-mono text-white/40">Loading run history...</p>
          </div>
        ) : filteredRuns && filteredRuns.length > 0 ? (
          <div className="bg-white/5 border border-white/10 divide-y divide-white/5">
            {filteredRuns.map((run) => (
              <button
                key={run.run_id}
                onClick={() => {
                  setSelectedRun(run);
                  setRunDetailsModalOpen(true);
                }}
                className="w-full p-4 flex items-center justify-between hover:bg-white/5 transition-colors text-left"
              >
                <div className="flex items-center gap-4">
                  <StatusBadge status={run.status} />
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-mono text-white">
                        {run.run_id.slice(0, 8)}...
                      </p>
                      {/* Node indicator */}
                      {run.node_id && run.node_id !== baselineNode?.node_id && (
                        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-purple-500/20 text-[9px] font-mono text-purple-400">
                          <GitBranch className="w-2.5 h-2.5" />
                          Fork
                        </span>
                      )}
                    </div>
                    <p className="text-[10px] font-mono text-white/40">{formatDate(run.created_at)}</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <p className="text-xs font-mono text-white/60">
                      Tick {run.timing?.current_tick || 0} / {run.timing?.total_ticks || '?'}
                    </p>
                    <p className="text-[10px] font-mono text-white/40">
                      {formatDuration(run.timing?.started_at, run.timing?.ended_at)}
                    </p>
                  </div>
                  {/* Quick Replay button for succeeded runs */}
                  {run.status === 'succeeded' && (
                    <Link
                      href={`/p/${projectId}/replay?run=${run.run_id}`}
                      onClick={(e) => e.stopPropagation()}
                      className="flex items-center gap-1 px-2 py-1 bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-[10px] font-mono hover:bg-cyan-500/20 transition-colors"
                    >
                      <Play className="w-3 h-3" />
                      Replay
                    </Link>
                  )}
                  {/* View Error button for failed runs */}
                  {run.status === 'failed' && (
                    <span className="flex items-center gap-1 px-2 py-1 bg-red-500/10 border border-red-500/30 text-red-400 text-[10px] font-mono">
                      <AlertCircle className="w-3 h-3" />
                      View Error
                    </span>
                  )}
                  <ChevronRight className="w-4 h-4 text-white/40" />
                </div>
              </button>
            ))}
          </div>
        ) : (
          <div className="bg-white/5 border border-white/10 p-8 text-center">
            <div className="w-16 h-16 bg-white/5 flex items-center justify-center mx-auto mb-4">
              <History className="w-8 h-8 text-white/20" />
            </div>
            <h3 className="text-sm font-mono text-white/60 mb-2">No runs yet</h3>
            <p className="text-xs font-mono text-white/40 mb-4">
              Configure your project and start your first simulation run
            </p>
            <Button
              size="sm"
              className="text-xs font-mono bg-green-500 hover:bg-green-600"
              onClick={() => handleStartRun('baseline')}
              disabled={createRun.isPending || startRun.isPending}
            >
              {createRun.isPending || startRun.isPending ? (
                <Loader2 className="w-3 h-3 mr-2 animate-spin" />
              ) : (
                <Play className="w-3 h-3 mr-2" />
              )}
              START BASELINE RUN
            </Button>
          </div>
        )}
      </div>

      {/* Navigation */}
      <div className="max-w-3xl mb-8">
        <div className="flex items-center justify-between gap-4">
          <Link href={`/p/${projectId}/rules`}>
            <Button variant="outline" size="sm" className="text-xs font-mono">
              <ArrowLeft className="w-3 h-3 mr-2" />
              Back to Rules
            </Button>
          </Link>
          <Link href={`/p/${projectId}/universe-map`}>
            <Button size="sm" className="text-xs font-mono bg-cyan-500 hover:bg-cyan-600">
              Next: Universe Map
              <ArrowRight className="w-3 h-3 ml-2" />
            </Button>
          </Link>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-8 pt-4 border-t border-white/5 max-w-3xl">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-1">
            <Terminal className="w-3 h-3" />
            <span>RUN CENTER</span>
          </div>
          <span>AGENTVERSE v1.0</span>
        </div>
      </div>

      {/* Modals */}
      <CustomRunModal
        open={customRunModalOpen}
        onClose={() => setCustomRunModalOpen(false)}
        onSubmit={(config) => {
          handleStartRun('custom', config);
          setCustomRunModalOpen(false);
        }}
        isSubmitting={createRun.isPending || startRun.isPending}
      />

      <RunDetailsModal
        run={selectedRun}
        open={runDetailsModalOpen}
        onClose={() => {
          setRunDetailsModalOpen(false);
          setSelectedRun(null);
        }}
        projectId={projectId}
      />

      <NodeSelectorModal
        open={showNodeSelector}
        onClose={() => setShowNodeSelector(false)}
        onSelect={handleNodeSelect}
        nodes={nodes}
        isLoading={nodesLoading}
        currentNodeId={selectedNodeId}
      />

      <PreFlightValidationModal
        open={preFlightModalOpen}
        onClose={() => setPreFlightModalOpen(false)}
        projectId={projectId}
        personaCount={personaCount}
      />
    </div>
  );
}

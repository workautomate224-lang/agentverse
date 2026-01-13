'use client';

/**
 * Calibration Lab Page
 * MVP for calibrating simulation predictions against ground truth data
 * Allows selecting nodes/runs and comparing predictions to actual outcomes
 */

import { useState, useCallback, useEffect } from 'react';
import { useParams, useSearchParams, useRouter } from 'next/navigation';
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
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  ArrowLeft,
  ArrowRight,
  Terminal,
  Loader2,
  AlertCircle,
  CheckCircle,
  Target,
  Play,
  RefreshCw,
  TrendingUp,
  Layers,
  GitBranch,
  Activity,
  Clock,
  Sparkles,
  Download,
  Upload,
  Settings,
  BarChart3,
  XCircle,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  useNodes,
  useRuns,
  useStartCalibration,
  useCalibrationStatus,
} from '@/hooks/useApi';
import type { NodeSummary, RunSummary } from '@/lib/api';
import { toast } from '@/hooks/use-toast';

// ============ Empty State ============

function EmptyState({
  type,
  projectId,
}: {
  type: 'no-nodes' | 'no-runs' | 'select-node';
  projectId: string;
}) {
  const config = {
    'no-nodes': {
      icon: GitBranch,
      title: 'No Nodes Available',
      description: 'Create your first simulation node to start calibrating.',
      action: (
        <Link href={`/p/${projectId}/universe-map`}>
          <Button size="sm" className="bg-purple-500 hover:bg-purple-600">
            <GitBranch className="w-3 h-3 mr-2" />
            Open Universe Map
          </Button>
        </Link>
      ),
    },
    'no-runs': {
      icon: Play,
      title: 'No Completed Runs',
      description: 'Run simulations to generate predictions for calibration.',
      action: (
        <Link href={`/p/${projectId}/run-center`}>
          <Button size="sm" className="bg-cyan-500 hover:bg-cyan-600">
            <Play className="w-3 h-3 mr-2" />
            Open Run Center
          </Button>
        </Link>
      ),
    },
    'select-node': {
      icon: Target,
      title: 'Select a Node',
      description: 'Choose a simulation node from the list to begin calibration.',
      action: null,
    },
  };

  const c = config[type];
  const Icon = c.icon;

  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="w-16 h-16 bg-white/5 border border-white/10 flex items-center justify-center mb-4">
        <Icon className="w-8 h-8 text-white/30" />
      </div>
      <h3 className="text-sm font-mono text-white/60 mb-1">{c.title}</h3>
      <p className="text-xs font-mono text-white/40 mb-4 max-w-xs">{c.description}</p>
      {c.action}
    </div>
  );
}

// ============ Node Selector ============

function NodeSelector({
  nodes,
  selectedNodeId,
  onSelectNode,
  runs,
}: {
  nodes: NodeSummary[];
  selectedNodeId: string | null;
  onSelectNode: (nodeId: string) => void;
  runs: RunSummary[];
}) {
  // Group runs by node
  const runsByNode = runs.reduce((acc, run) => {
    const nodeId = run.node_id || 'baseline';
    if (!acc[nodeId]) acc[nodeId] = [];
    acc[nodeId].push(run);
    return acc;
  }, {} as Record<string, RunSummary[]>);

  return (
    <div className="space-y-2">
      {/* Baseline node */}
      <button
        onClick={() => onSelectNode('baseline')}
        className={cn(
          'w-full p-3 border text-left transition-colors',
          selectedNodeId === 'baseline'
            ? 'bg-cyan-500/10 border-cyan-500/50'
            : 'bg-white/5 border-white/10 hover:border-white/20'
        )}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <GitBranch className="w-4 h-4 text-cyan-400" />
            <span className="font-mono text-sm text-white">Baseline</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono text-white/40">
              {runsByNode['baseline']?.filter(r => r.status === 'succeeded').length || 0} runs
            </span>
            {selectedNodeId === 'baseline' && (
              <CheckCircle className="w-4 h-4 text-cyan-400" />
            )}
          </div>
        </div>
      </button>

      {/* Other nodes */}
      {nodes.map((node) => {
        const nodeRuns = runsByNode[node.node_id] || [];
        const succeededRuns = nodeRuns.filter(r => r.status === 'succeeded');

        return (
          <button
            key={node.node_id}
            onClick={() => onSelectNode(node.node_id)}
            className={cn(
              'w-full p-3 border text-left transition-colors',
              selectedNodeId === node.node_id
                ? 'bg-purple-500/10 border-purple-500/50'
                : 'bg-white/5 border-white/10 hover:border-white/20'
            )}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <GitBranch className="w-4 h-4 text-purple-400" />
                <span className="font-mono text-sm text-white truncate max-w-[200px]">
                  {node.label || node.node_id.slice(0, 8)}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono text-white/40">
                  {succeededRuns.length} runs
                </span>
                {selectedNodeId === node.node_id && (
                  <CheckCircle className="w-4 h-4 text-purple-400" />
                )}
              </div>
            </div>
            <div className="mt-1 text-[10px] font-mono text-white/40">
              Prob: {(node.probability * 100).toFixed(1)}%
            </div>
          </button>
        );
      })}
    </div>
  );
}

// ============ Run Selector ============

function RunSelector({
  runs,
  selectedRunIds,
  onToggleRun,
}: {
  runs: RunSummary[];
  selectedRunIds: string[];
  onToggleRun: (runId: string) => void;
}) {
  const succeededRuns = runs.filter(r => r.status === 'succeeded');

  if (succeededRuns.length === 0) {
    return (
      <div className="p-4 bg-white/5 border border-white/10 text-center">
        <p className="text-xs font-mono text-white/40">No completed runs for this node</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {succeededRuns.map((run) => {
        const isSelected = selectedRunIds.includes(run.run_id);
        const created = run.created_at ? new Date(run.created_at) : null;

        return (
          <button
            key={run.run_id}
            onClick={() => onToggleRun(run.run_id)}
            className={cn(
              'w-full p-3 border text-left transition-colors',
              isSelected
                ? 'bg-emerald-500/10 border-emerald-500/50'
                : 'bg-white/5 border-white/10 hover:border-white/20'
            )}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {isSelected ? (
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                ) : (
                  <div className="w-4 h-4 border border-white/30" />
                )}
                <span className="font-mono text-sm text-white">
                  {run.run_id.slice(0, 8)}...
                </span>
              </div>
              <span className="text-[10px] font-mono text-white/40">
                {created?.toLocaleDateString() || 'N/A'}
              </span>
            </div>
            {run.timing && (
              <div className="mt-1 flex items-center gap-4 text-[10px] font-mono text-white/40">
                <span>{run.timing.current_tick || 0} / {run.timing.total_ticks || 0} ticks</span>
              </div>
            )}
          </button>
        );
      })}
    </div>
  );
}

// ============ Ground Truth Input ============

function GroundTruthInput({
  groundTruth,
  onChange,
}: {
  groundTruth: string;
  onChange: (value: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);

  const sampleGroundTruth = JSON.stringify({
    category_distributions: {
      "option_a": 0.45,
      "option_b": 0.35,
      "option_c": 0.20,
    },
    source: "Survey Q4 2025",
    sample_size: 1000,
  }, null, 2);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-xs font-mono text-white/60">Ground Truth Data (JSON)</label>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-[10px] font-mono text-cyan-400 hover:text-cyan-300"
        >
          {expanded ? 'Hide' : 'Show'} format
        </button>
      </div>

      {expanded && (
        <div className="p-3 bg-white/5 border border-white/10 text-[10px] font-mono text-white/40">
          <pre>{sampleGroundTruth}</pre>
        </div>
      )}

      <Textarea
        value={groundTruth}
        onChange={(e) => onChange(e.target.value)}
        placeholder='{"category_distributions": {"option_a": 0.45, ...}}'
        className="font-mono text-xs min-h-[120px] bg-black border-white/20"
      />
    </div>
  );
}

// ============ Calibration Status Card ============

function CalibrationStatusCard({
  calibrationId,
}: {
  calibrationId: string;
}) {
  const { data: status, isLoading, refetch } = useCalibrationStatus(calibrationId);

  useEffect(() => {
    if (status?.status === 'running' || status?.status === 'pending') {
      const interval = setInterval(() => {
        refetch();
      }, 2000);
      return () => clearInterval(interval);
    }
  }, [status?.status, refetch]);

  if (isLoading) {
    return (
      <div className="p-4 bg-white/5 border border-white/10 flex items-center justify-center">
        <Loader2 className="w-4 h-4 text-cyan-400 animate-spin" />
      </div>
    );
  }

  if (!status) {
    return (
      <div className="p-4 bg-red-500/10 border border-red-500/30 text-xs font-mono text-red-400">
        <AlertCircle className="w-3 h-3 inline mr-1" />
        Failed to load calibration status
      </div>
    );
  }

  const statusConfig = {
    pending: { icon: Clock, color: 'text-yellow-400', bg: 'bg-yellow-500/10 border-yellow-500/30' },
    running: { icon: Activity, color: 'text-cyan-400 animate-pulse', bg: 'bg-cyan-500/10 border-cyan-500/30' },
    completed: { icon: CheckCircle, color: 'text-green-400', bg: 'bg-green-500/10 border-green-500/30' },
    failed: { icon: XCircle, color: 'text-red-400', bg: 'bg-red-500/10 border-red-500/30' },
  };

  const s = statusConfig[status.status];
  const Icon = s.icon;

  return (
    <div className={cn('p-4 border', s.bg)}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Icon className={cn('w-4 h-4', s.color)} />
          <span className="font-mono text-sm text-white capitalize">{status.status}</span>
        </div>
        <span className="text-[10px] font-mono text-white/40">
          {status.iterations_completed} / {status.max_iterations} iterations
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-2 bg-white/10 mb-3">
        <div
          className="h-full bg-cyan-500 transition-all"
          style={{ width: `${status.progress * 100}%` }}
        />
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-3 gap-3">
        <div>
          <div className="text-[10px] font-mono text-white/40 uppercase mb-1">Current</div>
          <div className="font-mono text-sm text-white">
            {status.current_accuracy !== null ? `${(status.current_accuracy * 100).toFixed(1)}%` : '—'}
          </div>
        </div>
        <div>
          <div className="text-[10px] font-mono text-white/40 uppercase mb-1">Best</div>
          <div className="font-mono text-sm text-emerald-400">
            {status.best_accuracy !== null ? `${(status.best_accuracy * 100).toFixed(1)}%` : '—'}
          </div>
        </div>
        <div>
          <div className="text-[10px] font-mono text-white/40 uppercase mb-1">Target</div>
          <div className="font-mono text-sm text-white/60">
            {(status.target_accuracy * 100).toFixed(1)}%
          </div>
        </div>
      </div>

      {/* Best params preview */}
      {status.best_params && status.status === 'completed' && (
        <div className="mt-3 pt-3 border-t border-white/10">
          <div className="text-[10px] font-mono text-white/40 uppercase mb-1">Optimized Parameters</div>
          <pre className="text-[10px] font-mono text-white/60 overflow-x-auto">
            {JSON.stringify(status.best_params, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

// ============ Main Page Component ============

export default function CalibrationLabPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const projectId = params.projectId as string;

  // URL params
  const initialNodeId = searchParams.get('node');

  // State
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(initialNodeId || null);
  const [selectedRunIds, setSelectedRunIds] = useState<string[]>([]);
  const [groundTruth, setGroundTruth] = useState('');
  const [calibrationIds, setCalibrationIds] = useState<string[]>([]);
  const [isStarting, setIsStarting] = useState(false);
  const [configModalOpen, setConfigModalOpen] = useState(false);
  const [targetAccuracy, setTargetAccuracy] = useState(0.85);
  const [maxIterations, setMaxIterations] = useState(100);

  // API hooks
  const { data: nodes, isLoading: nodesLoading, refetch: refetchNodes } = useNodes({
    project_id: projectId,
    limit: 50,
  });
  const { data: runs, isLoading: runsLoading, refetch: refetchRuns } = useRuns({
    project_id: projectId,
    limit: 100,
  });
  const startCalibration = useStartCalibration();

  const isLoading = nodesLoading || runsLoading;

  // Update URL when node changes
  useEffect(() => {
    if (selectedNodeId) {
      const url = new URL(window.location.href);
      url.searchParams.set('node', selectedNodeId);
      router.replace(url.pathname + url.search, { scroll: false });
    }
  }, [selectedNodeId, router]);

  // Filter runs for selected node
  const filteredRuns = (runs || []).filter(run => {
    if (selectedNodeId === 'baseline') {
      return !run.node_id;
    }
    return run.node_id === selectedNodeId;
  });

  // Handle node selection
  const handleSelectNode = useCallback((nodeId: string) => {
    setSelectedNodeId(nodeId);
    setSelectedRunIds([]); // Reset run selection
  }, []);

  // Handle run toggle
  const handleToggleRun = useCallback((runId: string) => {
    setSelectedRunIds(prev =>
      prev.includes(runId)
        ? prev.filter(id => id !== runId)
        : [...prev, runId]
    );
  }, []);

  // Handle start calibration
  const handleStartCalibration = useCallback(async () => {
    if (selectedRunIds.length === 0) {
      toast({
        title: 'No Runs Selected',
        description: 'Please select at least one run to calibrate.',
        variant: 'destructive',
      });
      return;
    }

    let parsedGroundTruth;
    try {
      parsedGroundTruth = groundTruth ? JSON.parse(groundTruth) : {
        category_distributions: { default: 1.0 },
        source: 'Manual input',
      };
    } catch {
      toast({
        title: 'Invalid JSON',
        description: 'Ground truth data must be valid JSON.',
        variant: 'destructive',
      });
      return;
    }

    setIsStarting(true);
    try {
      // Start calibration for each selected run
      const newCalibrationIds: string[] = [];
      for (const runId of selectedRunIds) {
        const result = await startCalibration.mutateAsync({
          prediction_id: runId, // Using run_id as prediction_id
          ground_truth: parsedGroundTruth,
          config: {
            target_accuracy: targetAccuracy,
            max_iterations: maxIterations,
          },
        });
        newCalibrationIds.push(result.id);
      }
      setCalibrationIds(prev => [...prev, ...newCalibrationIds]);
      toast({
        title: 'Calibration Started',
        description: `Started ${newCalibrationIds.length} calibration job(s).`,
      });
    } catch (error) {
      toast({
        title: 'Calibration Failed',
        description: error instanceof Error ? error.message : 'Failed to start calibration.',
        variant: 'destructive',
      });
    } finally {
      setIsStarting(false);
    }
  }, [selectedRunIds, groundTruth, targetAccuracy, maxIterations, startCalibration]);

  // Handle refresh
  const handleRefresh = useCallback(() => {
    refetchNodes();
    refetchRuns();
  }, [refetchNodes, refetchRuns]);

  return (
    <div className="min-h-screen bg-black">
      {/* Header */}
      <div className="p-4 border-b border-white/10">
        <div className="flex items-center gap-2 mb-2">
          <Link href={`/p/${projectId}/run-center`}>
            <Button variant="ghost" size="sm" className="text-[10px]">
              <ArrowLeft className="w-3 h-3 mr-1" />
              RUN CENTER
            </Button>
          </Link>
        </div>
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <Target className="w-4 h-4 text-emerald-400" />
              <span className="text-xs font-mono text-white/40 uppercase">Calibration Lab</span>
            </div>
            <h1 className="text-xl font-mono font-bold text-white">Prediction Calibration</h1>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="text-xs"
              onClick={() => setConfigModalOpen(true)}
            >
              <Settings className="w-3 h-3 mr-1" />
              CONFIG
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="text-xs"
              onClick={handleRefresh}
              disabled={isLoading}
            >
              <RefreshCw className={cn('w-3 h-3 mr-1', isLoading && 'animate-spin')} />
              REFRESH
            </Button>
          </div>
        </div>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-6 h-6 text-cyan-400 animate-spin" />
        </div>
      )}

      {/* Main content */}
      {!isLoading && (
        <div className="p-4">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Column 1: Node Selection */}
            <div className="space-y-4">
              <div className="p-3 bg-white/5 border border-white/10">
                <div className="flex items-center gap-2 mb-3">
                  <GitBranch className="w-4 h-4 text-purple-400" />
                  <span className="font-mono text-sm text-white">1. Select Node</span>
                </div>
                {(!nodes || nodes.length === 0) && !runs?.length ? (
                  <EmptyState type="no-nodes" projectId={projectId} />
                ) : (
                  <NodeSelector
                    nodes={nodes || []}
                    selectedNodeId={selectedNodeId}
                    onSelectNode={handleSelectNode}
                    runs={runs || []}
                  />
                )}
              </div>
            </div>

            {/* Column 2: Run Selection */}
            <div className="space-y-4">
              <div className="p-3 bg-white/5 border border-white/10">
                <div className="flex items-center gap-2 mb-3">
                  <Layers className="w-4 h-4 text-cyan-400" />
                  <span className="font-mono text-sm text-white">2. Select Runs</span>
                  {selectedRunIds.length > 0 && (
                    <span className="text-[10px] font-mono text-emerald-400">
                      ({selectedRunIds.length} selected)
                    </span>
                  )}
                </div>
                {!selectedNodeId ? (
                  <EmptyState type="select-node" projectId={projectId} />
                ) : filteredRuns.filter(r => r.status === 'succeeded').length === 0 ? (
                  <EmptyState type="no-runs" projectId={projectId} />
                ) : (
                  <RunSelector
                    runs={filteredRuns}
                    selectedRunIds={selectedRunIds}
                    onToggleRun={handleToggleRun}
                  />
                )}
              </div>
            </div>

            {/* Column 3: Ground Truth & Actions */}
            <div className="space-y-4">
              <div className="p-3 bg-white/5 border border-white/10">
                <div className="flex items-center gap-2 mb-3">
                  <Target className="w-4 h-4 text-emerald-400" />
                  <span className="font-mono text-sm text-white">3. Ground Truth</span>
                </div>
                <GroundTruthInput
                  groundTruth={groundTruth}
                  onChange={setGroundTruth}
                />

                <div className="mt-4 pt-4 border-t border-white/10">
                  <Button
                    onClick={handleStartCalibration}
                    disabled={selectedRunIds.length === 0 || isStarting}
                    className="w-full bg-emerald-500 hover:bg-emerald-600 text-white"
                  >
                    {isStarting ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Starting...
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-4 h-4 mr-2" />
                        Start Calibration
                      </>
                    )}
                  </Button>
                </div>

                {/* Config summary */}
                <div className="mt-3 p-2 bg-black border border-white/10 text-[10px] font-mono text-white/40">
                  <div className="flex justify-between">
                    <span>Target Accuracy</span>
                    <span>{(targetAccuracy * 100).toFixed(0)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Max Iterations</span>
                    <span>{maxIterations}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Calibration Status Section */}
          {calibrationIds.length > 0 && (
            <div className="mt-6 p-4 bg-white/5 border border-white/10">
              <div className="flex items-center gap-2 mb-4">
                <Activity className="w-4 h-4 text-cyan-400" />
                <span className="font-mono text-sm text-white">Active Calibrations</span>
                <span className="text-[10px] font-mono text-white/40">
                  ({calibrationIds.length})
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {calibrationIds.map((id) => (
                  <CalibrationStatusCard key={id} calibrationId={id} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Footer nav */}
      <div className="p-4 border-t border-white/10 flex items-center justify-between">
        <Link href={`/p/${projectId}/results`}>
          <Button variant="outline" size="sm" className="text-xs font-mono">
            <ArrowLeft className="w-3 h-3 mr-2" />
            Results
          </Button>
        </Link>
        <div className="flex items-center gap-1">
          <Terminal className="w-3 h-3 text-white/30" />
          <span className="text-[10px] font-mono text-white/30">CALIBRATION LAB v1.0</span>
        </div>
        <Link href={`/p/${projectId}/universe-map`}>
          <Button size="sm" className="text-xs font-mono bg-purple-500 hover:bg-purple-600">
            Universe Map
            <ArrowRight className="w-3 h-3 ml-2" />
          </Button>
        </Link>
      </div>

      {/* Config Modal */}
      <Dialog open={configModalOpen} onOpenChange={setConfigModalOpen}>
        <DialogContent className="bg-black border border-white/10 max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-white font-mono flex items-center gap-2">
              <Settings className="w-5 h-5 text-cyan-400" />
              Calibration Config
            </DialogTitle>
            <DialogDescription className="text-white/50 font-mono text-xs">
              Configure calibration parameters
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div>
              <label className="block text-xs font-mono text-white/60 mb-2">
                Target Accuracy ({(targetAccuracy * 100).toFixed(0)}%)
              </label>
              <input
                type="range"
                min="0.5"
                max="0.99"
                step="0.01"
                value={targetAccuracy}
                onChange={(e) => setTargetAccuracy(parseFloat(e.target.value))}
                className="w-full"
              />
            </div>

            <div>
              <label className="block text-xs font-mono text-white/60 mb-2">
                Max Iterations
              </label>
              <Input
                type="number"
                value={maxIterations}
                onChange={(e) => setMaxIterations(parseInt(e.target.value) || 100)}
                min={10}
                max={1000}
                className="font-mono text-sm"
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              size="sm"
              onClick={() => setConfigModalOpen(false)}
              className="bg-cyan-500 hover:bg-cyan-600"
            >
              Apply
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

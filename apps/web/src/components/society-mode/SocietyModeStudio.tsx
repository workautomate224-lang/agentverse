'use client';

/**
 * Society Mode Studio
 * Reference: Interaction_design.md §5.12
 *
 * Run and inspect multi-agent emergent simulations directly (expert view).
 * Most users won't need it - prefer Ask/Universe Map for typical workflows.
 */

import { useState, useMemo } from 'react';
import {
  Users2,
  Play,
  Loader2,
  AlertCircle,
  GitBranch,
  PlayCircle,
  Download,
  Save,
  BarChart3,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  useNodes,
  useRuns,
  useCreateRun,
  useRunProgress,
  useRunResults,
  useRunConfigs,
  useProjectSpecStats,
} from '@/hooks/useApi';
import {
  SpecRun,
  SpecRunConfig,
  SpecRunResults,
  CreateRunConfigInput,
  SchedulerProfile,
} from '@/lib/api';
import { cn } from '@/lib/utils';
import { RunControlsPanel } from './RunControlsPanel';
import { SocietyPopulationPanel } from './SocietyPopulationPanel';
import { SocietyOutputPanel } from './SocietyOutputPanel';

interface SocietyModeStudioProps {
  projectId: string;
}

export interface SocietyRunConfig {
  horizon: number;
  tick_rate: number;
  scheduler_profile: Partial<SchedulerProfile>;
  rule_pack: string;
  max_agents: number;
  seed?: number | null;
}

const DEFAULT_CONFIG: SocietyRunConfig = {
  horizon: 100,
  tick_rate: 10,
  scheduler_profile: {
    scheduler_type: 'synchronous',
    activation_probability: 1.0,
    batch_size: 1000,
    parallelism_level: 4,
  },
  rule_pack: 'default',
  max_agents: 1000,
  seed: null,
};

export function SocietyModeStudio({ projectId }: SocietyModeStudioProps) {
  // State
  const [runConfig, setRunConfig] = useState<SocietyRunConfig>(DEFAULT_CONFIG);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // API hooks
  const { data: nodes } = useNodes({ project_id: projectId });
  const { data: runs } = useRuns({ project_id: projectId });
  const { data: stats } = useProjectSpecStats(projectId);
  const { data: runConfigs } = useRunConfigs({ project_id: projectId, is_template: true });
  const { data: runProgress, isLoading: loadingProgress } = useRunProgress(activeRunId ?? undefined);
  const { data: runResults, isLoading: loadingResults } = useRunResults(
    runProgress?.status === 'succeeded' ? activeRunId ?? undefined : undefined
  );
  const createRun = useCreateRun();

  // Get root node for running baseline
  const rootNode = useMemo(() => {
    if (!nodes?.length) return null;
    return nodes.find((n) => !n.parent_node_id) ?? nodes[0];
  }, [nodes]);

  // Active run
  const activeRun = useMemo(() => {
    if (!activeRunId || !runs) return null;
    return runs.find((r) => r.run_id === activeRunId) ?? null;
  }, [activeRunId, runs]);

  // Recent completed runs
  const completedRuns = useMemo(() => {
    if (!runs) return [];
    return runs
      .filter((r) => r.status === 'succeeded')
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      .slice(0, 5);
  }, [runs]);

  // Handle running society simulation
  const handleRunSimulation = async () => {
    if (!rootNode) return;

    const configOverrides: Partial<CreateRunConfigInput> = {
      project_id: projectId,
      horizon: runConfig.horizon,
      tick_rate: runConfig.tick_rate,
      scheduler_profile: runConfig.scheduler_profile as SchedulerProfile,
      seed_config: {
        strategy: 'single',
        primary_seed: runConfig.seed ?? Math.floor(Math.random() * 1000000),
      },
    };

    try {
      const run = await createRun.mutateAsync({
        node_id: rootNode.node_id,
        config_overrides: configOverrides,
        label: `Society Mode Run - ${new Date().toISOString()}`,
      });
      setActiveRunId(run.run_id);
    } catch {
      // Error handled by mutation
    }
  };

  // Handle saving run as baseline node
  const handleSaveAsNode = () => {
    // This would create a new node from the run results
    // Implementation depends on backend API
  };

  // Handle opening 2D replay
  const handleOpenReplay = () => {
    if (!activeRunId) return;
    window.location.href = `/dashboard/projects/${projectId}/replay?run_id=${activeRunId}`;
  };

  // Handle export
  const handleExport = () => {
    if (!runResults) return;
    const data = JSON.stringify(runResults, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `society-run-${activeRunId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Loading states
  const isRunning = createRun.isPending || runProgress?.status === 'running';
  const canRun = !!rootNode && !isRunning;

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex-none border-b border-white/10 bg-black/40 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Users2 className="h-5 w-5 text-cyan-400" />
            <h1 className="text-lg font-semibold">Society Mode Studio</h1>
            <span className="text-sm text-white/60">
              Multi-agent emergent simulation (expert view)
            </span>
          </div>
          <div className="flex items-center gap-2">
            {runProgress && (
              <div
                className={cn(
                  'flex items-center gap-2 px-3 py-1.5 text-sm border',
                  runProgress.status === 'succeeded'
                    ? 'bg-green-500/10 border-green-500/30 text-green-300'
                    : runProgress.status === 'running'
                    ? 'bg-yellow-500/10 border-yellow-500/30 text-yellow-300'
                    : runProgress.status === 'failed'
                    ? 'bg-red-500/10 border-red-500/30 text-red-300'
                    : 'bg-white/5 border-white/20 text-white/60'
                )}
              >
                {runProgress.status === 'running' && (
                  <Loader2 className="h-4 w-4 animate-spin" />
                )}
                <span className="capitalize">{runProgress.status}</span>
                {runProgress.status === 'running' && (
                  <span className="text-white/60">
                    ({runProgress.current_tick}/{runConfig.horizon})
                  </span>
                )}
              </div>
            )}
            {stats && (
              <div className="flex items-center gap-2 px-3 py-1.5 bg-white/5 border border-white/10 text-sm">
                <span className="text-white/40">Nodes:</span>
                <span className="text-white/90">{stats.node_count}</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Content - 3 Panel Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Column - Run Controls */}
        <div className="w-80 flex-none border-r border-white/10 flex flex-col overflow-hidden">
          <RunControlsPanel
            config={runConfig}
            onConfigChange={setRunConfig}
            showAdvanced={showAdvanced}
            onToggleAdvanced={() => setShowAdvanced(!showAdvanced)}
            runConfigs={runConfigs ?? []}
          />

          {/* Run Buttons */}
          <div className="flex-none p-4 border-t border-white/10 space-y-2">
            <Button
              className="w-full"
              onClick={handleRunSimulation}
              disabled={!canRun}
            >
              {isRunning ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Running...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Run Society Simulation
                </>
              )}
            </Button>

            {runProgress?.status === 'succeeded' && (
              <>
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={handleSaveAsNode}
                >
                  <Save className="h-4 w-4 mr-2" />
                  Save as Baseline Node
                </Button>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    onClick={handleOpenReplay}
                  >
                    <PlayCircle className="h-3 w-3 mr-1" />
                    2D Replay
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    onClick={handleExport}
                  >
                    <Download className="h-3 w-3 mr-1" />
                    Export
                  </Button>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Center Column - Population */}
        <div className="w-80 flex-none border-r border-white/10 overflow-y-auto">
          <SocietyPopulationPanel
            projectId={projectId}
            stats={stats}
            config={runConfig}
          />
        </div>

        {/* Right Column - Output */}
        <div className="flex-1 overflow-hidden">
          <SocietyOutputPanel
            runProgress={runProgress ?? null}
            runResults={runResults ?? null}
            isLoading={loadingProgress || loadingResults}
            completedRuns={completedRuns}
            onSelectRun={setActiveRunId}
          />
        </div>
      </div>

      {/* Footer Error */}
      {createRun.isError && (
        <div className="flex-none border-t border-red-500/30 bg-red-500/10 p-3">
          <div className="flex items-center gap-2 text-red-400 text-sm">
            <AlertCircle className="h-4 w-4" />
            <span>{createRun.error?.message ?? 'Failed to start simulation'}</span>
          </div>
        </div>
      )}
    </div>
  );
}

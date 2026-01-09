'use client';

/**
 * Hybrid Mode Studio Component
 * Reference: project.md §11 Phase 6, Interaction_design.md §5.14
 *
 * Main container for Hybrid Mode: Key actors in a population context.
 * Combines Target Mode (individual paths) with Society Mode (collective dynamics).
 */

import { useState, useMemo, useCallback } from 'react';
import {
  Combine,
  User,
  Users,
  Settings2,
  Play,
  GitBranch,
  PlayCircle,
  AlertCircle,
  Loader2,
  CheckCircle,
  XCircle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  useTargetPersonas,
  useRunHybridSimulation,
  useHybridRun,
  useBranchHybridToNode,
  useNodes,
} from '@/hooks/useApi';
import {
  TargetPersona,
  CouplingConfig,
  PopulationContext,
  HybridRunRequest,
  HybridRunResult,
  CouplingDirection,
  CouplingStrength,
} from '@/lib/api';
import { cn } from '@/lib/utils';
import { KeyActorPanel } from './KeyActorPanel';
import { PopulationPanel } from './PopulationPanel';
import { CouplingPanel } from './CouplingPanel';
import { HybridResultsPanel } from './HybridResultsPanel';

interface HybridModeStudioProps {
  projectId: string;
}

const DEFAULT_COUPLING_CONFIG: CouplingConfig = {
  direction: 'bidirectional',
  actor_influence_strength: 'moderate',
  society_feedback_strength: 'moderate',
  influence_decay_rate: 0.1,
  influence_radius_segments: [],
  synchronization_interval: 5,
  actor_action_amplification: 1.5,
  society_pressure_weight: 0.3,
};

const DEFAULT_POPULATION_CONTEXT: PopulationContext = {
  agent_count: 100,
  segment_distribution: null,
  region_distribution: null,
  initial_stance_distribution: null,
};

export function HybridModeStudio({ projectId }: HybridModeStudioProps) {
  // Selected key actors (target persona IDs)
  const [selectedActorIds, setSelectedActorIds] = useState<string[]>([]);

  // Coupling configuration
  const [couplingConfig, setCouplingConfig] = useState<CouplingConfig>(DEFAULT_COUPLING_CONFIG);

  // Population context
  const [populationContext, setPopulationContext] = useState<PopulationContext>(DEFAULT_POPULATION_CONTEXT);

  // Simulation settings
  const [numTicks, setNumTicks] = useState(100);
  const [autoCreateNode, setAutoCreateNode] = useState(true);

  // Active run
  const [activeRunId, setActiveRunId] = useState<string | null>(null);

  // API hooks
  const { data: personas, isLoading: loadingPersonas } = useTargetPersonas({
    project_id: projectId,
  });
  const { data: runResult, isLoading: loadingRun } = useHybridRun(activeRunId ?? undefined);
  const { data: nodes } = useNodes({ project_id: projectId });
  const runHybrid = useRunHybridSimulation();
  const branchToNode = useBranchHybridToNode();

  // Get root node for branching
  const rootNode = useMemo(() => {
    if (!nodes?.length) return null;
    return nodes.find((n) => !n.parent_node_id) ?? nodes[0];
  }, [nodes]);

  // Selected personas
  const selectedActors = useMemo(() => {
    if (!personas) return [];
    return personas.filter((p) => selectedActorIds.includes(p.target_id));
  }, [personas, selectedActorIds]);

  // Handle running hybrid simulation
  const handleRunHybrid = useCallback(async () => {
    if (selectedActorIds.length === 0) return;

    const request: HybridRunRequest = {
      project_id: projectId,
      key_actors: selectedActorIds,
      population_context: populationContext,
      coupling_config: couplingConfig,
      num_ticks: numTicks,
      parent_node_id: rootNode?.node_id ?? null,
      auto_create_node: autoCreateNode,
    };

    try {
      const result = await runHybrid.mutateAsync(request);
      setActiveRunId(result.run_id);
    } catch {
      // Error handled by mutation
    }
  }, [selectedActorIds, projectId, populationContext, couplingConfig, numTicks, rootNode, autoCreateNode, runHybrid]);

  // Handle branching to Universe Map
  const handleBranchToNode = useCallback(async () => {
    if (!activeRunId || !rootNode) return;

    await branchToNode.mutateAsync({
      runId: activeRunId,
      data: {
        parent_node_id: rootNode.node_id,
        label: `Hybrid: ${selectedActors.map(a => a.name).join(', ')}`,
      },
    });
  }, [activeRunId, rootNode, selectedActors, branchToNode]);

  // Toggle actor selection
  const handleToggleActor = useCallback((targetId: string) => {
    setSelectedActorIds(prev =>
      prev.includes(targetId)
        ? prev.filter(id => id !== targetId)
        : [...prev, targetId]
    );
  }, []);

  // Run status
  const isRunning = runHybrid.isPending || runResult?.status === 'running' || runResult?.status === 'pending';
  const isCompleted = runResult?.status === 'completed';
  const isFailed = runResult?.status === 'failed';
  const canRun = selectedActorIds.length > 0 && !isRunning;

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex-none border-b border-white/10 bg-black/40 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Combine className="h-5 w-5 text-purple-400" />
            <h1 className="text-lg font-semibold">Hybrid Mode Studio</h1>
            <span className="text-sm text-white/60">
              Key actors in a population context
            </span>
          </div>
          <div className="flex items-center gap-2">
            {/* Selected actors badge */}
            {selectedActorIds.length > 0 && (
              <div className="flex items-center gap-2 px-3 py-1.5 bg-purple-500/10 border border-purple-500/30 text-sm">
                <User className="h-4 w-4 text-purple-400" />
                <span className="text-purple-300">
                  {selectedActorIds.length} actor{selectedActorIds.length > 1 ? 's' : ''} selected
                </span>
              </div>
            )}

            {/* Population badge */}
            <div className="flex items-center gap-2 px-3 py-1.5 bg-cyan-500/10 border border-cyan-500/30 text-sm">
              <Users className="h-4 w-4 text-cyan-400" />
              <span className="text-cyan-300">
                {populationContext.agent_count} agents
              </span>
            </div>

            {/* Run status */}
            {runResult && (
              <div
                className={cn(
                  'flex items-center gap-2 px-3 py-1.5 text-sm border',
                  runResult.status === 'completed'
                    ? 'bg-green-500/10 border-green-500/30 text-green-300'
                    : runResult.status === 'running' || runResult.status === 'pending'
                    ? 'bg-yellow-500/10 border-yellow-500/30 text-yellow-300'
                    : runResult.status === 'failed'
                    ? 'bg-red-500/10 border-red-500/30 text-red-300'
                    : 'bg-white/5 border-white/20 text-white/60'
                )}
              >
                {isRunning && <Loader2 className="h-4 w-4 animate-spin" />}
                {isCompleted && <CheckCircle className="h-4 w-4" />}
                {isFailed && <XCircle className="h-4 w-4" />}
                <span className="capitalize">{runResult.status}</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Content - 4 Panel Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Column - Key Actors */}
        <div className="w-72 flex-none border-r border-white/10 overflow-y-auto">
          <KeyActorPanel
            personas={personas ?? []}
            selectedIds={selectedActorIds}
            onToggleActor={handleToggleActor}
            isLoading={loadingPersonas}
          />
        </div>

        {/* Center Column - Population & Coupling */}
        <div className="w-80 flex-none border-r border-white/10 flex flex-col overflow-hidden">
          {/* Population Panel */}
          <div className="flex-none border-b border-white/10">
            <PopulationPanel
              context={populationContext}
              onChange={setPopulationContext}
            />
          </div>

          {/* Coupling Panel */}
          <div className="flex-1 overflow-y-auto">
            <CouplingPanel
              config={couplingConfig}
              onChange={setCouplingConfig}
              numTicks={numTicks}
              onNumTicksChange={setNumTicks}
            />
          </div>

          {/* Run Button */}
          <div className="flex-none border-t border-white/10 p-4">
            <Button
              onClick={handleRunHybrid}
              disabled={!canRun}
              className={cn(
                'w-full h-10',
                canRun
                  ? 'bg-gradient-to-r from-purple-500 to-cyan-500 hover:from-purple-400 hover:to-cyan-400 text-white'
                  : ''
              )}
            >
              {isRunning ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Running Hybrid...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Run Hybrid Simulation
                </>
              )}
            </Button>

            <div className="flex items-center gap-2 mt-2">
              <label className="flex items-center gap-2 text-xs text-white/60 cursor-pointer">
                <input
                  type="checkbox"
                  checked={autoCreateNode}
                  onChange={(e) => setAutoCreateNode(e.target.checked)}
                  className="rounded border-white/20 bg-white/5 text-purple-500 focus:ring-purple-500"
                />
                Auto-create node in Universe Map
              </label>
            </div>
          </div>
        </div>

        {/* Right Column - Results */}
        <div className="flex-1 overflow-hidden">
          <HybridResultsPanel
            runResult={runResult ?? null}
            isLoading={loadingRun}
            selectedActors={selectedActors}
            onBranchToNode={handleBranchToNode}
            isBranching={branchToNode.isPending}
          />
        </div>
      </div>

      {/* Footer Error */}
      {(runHybrid.isError || branchToNode.isError) && (
        <div className="flex-none border-t border-red-500/30 bg-red-500/10 p-3">
          <div className="flex items-center gap-2 text-red-400 text-sm">
            <AlertCircle className="h-4 w-4" />
            <span>
              {runHybrid.error?.message ??
                branchToNode.error?.message ??
                'An error occurred'}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

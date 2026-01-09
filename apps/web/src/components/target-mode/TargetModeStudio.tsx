'use client';

import { useState, useMemo } from 'react';
import {
  Target,
  User,
  Settings,
  Play,
  Plus,
  ChevronRight,
  AlertCircle,
  Loader2,
  GitBranch,
  Sparkles,
  Filter,
  RefreshCw,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  useTargetPersonas,
  useTargetPlan,
  useRunTargetPlanner,
  useExpandTargetCluster,
  useBranchPathToNode,
  useNodes,
  useCreateTargetPersona,
} from '@/hooks/useApi';
import {
  TargetPersona,
  PlanResult,
  PathCluster,
  TargetPath,
  TargetPlanRequest,
} from '@/lib/api';
import { cn } from '@/lib/utils';
import { TargetPersonaPanel } from './TargetPersonaPanel';
import { ContextPanel } from './ContextPanel';
import { ActionSetPanel } from './ActionSetPanel';
import { PlannerPanel } from './PlannerPanel';
import { ResultsPanel } from './ResultsPanel';

interface TargetModeStudioProps {
  projectId: string;
}

export function TargetModeStudio({ projectId }: TargetModeStudioProps) {
  // State
  const [selectedTargetId, setSelectedTargetId] = useState<string | null>(null);
  const [activePlanId, setActivePlanId] = useState<string | null>(null);
  const [selectedPathId, setSelectedPathId] = useState<string | null>(null);
  const [parentNodeId, setParentNodeId] = useState<string | null>(null);
  const [showCreateTarget, setShowCreateTarget] = useState(false);
  const [newTargetName, setNewTargetName] = useState('');
  const [newTargetGoal, setNewTargetGoal] = useState('');

  // Planner config
  const [plannerConfig, setPlannerConfig] = useState({
    max_paths: 100,
    max_depth: 10,
    pruning_threshold: 0.01,
    enable_clustering: true,
    max_clusters: 5,
  });

  // API hooks
  const { data: personas, isLoading: loadingPersonas, refetch: refetchPersonas } = useTargetPersonas({
    project_id: projectId,
  });
  const { data: plan, isLoading: loadingPlan } = useTargetPlan(activePlanId ?? undefined);
  const { data: nodes } = useNodes({ project_id: projectId });
  const runPlanner = useRunTargetPlanner();
  const expandCluster = useExpandTargetCluster();
  const branchToNode = useBranchPathToNode();
  const createTargetPersona = useCreateTargetPersona();

  // Get root node for branching
  const rootNode = useMemo(() => {
    if (!nodes?.length) return null;
    return nodes.find((n) => !n.parent_node_id) ?? nodes[0];
  }, [nodes]);

  // Selected target
  const selectedTarget = useMemo(() => {
    if (!selectedTargetId || !personas) return null;
    return personas.find((p) => p.target_id === selectedTargetId) ?? null;
  }, [selectedTargetId, personas]);

  // Handle running the planner
  const handleRunPlanner = async () => {
    if (!selectedTargetId) return;

    const request: TargetPlanRequest = {
      project_id: projectId,
      target_id: selectedTargetId,
      ...plannerConfig,
      start_node_id: parentNodeId ?? rootNode?.node_id ?? undefined,
    };

    try {
      const result = await runPlanner.mutateAsync(request);
      setActivePlanId(result.plan_id);
    } catch {
      // Error handled by mutation
    }
  };

  // Handle expanding a cluster
  const handleExpandCluster = async (clusterId: string) => {
    if (!activePlanId) return;
    await expandCluster.mutateAsync({
      plan_id: activePlanId,
      cluster_id: clusterId,
      max_paths: 10,
    });
  };

  // Handle branching selected path to Universe Map
  const handleBranchToNode = async () => {
    if (!activePlanId || !selectedPathId) return;

    const nodeId = parentNodeId ?? rootNode?.node_id;
    if (!nodeId) return;

    await branchToNode.mutateAsync({
      plan_id: activePlanId,
      path_id: selectedPathId,
      parent_node_id: nodeId,
      auto_run: false,
    });
  };

  // Loading states
  const isPlanning = runPlanner.isPending;
  const isBranching = branchToNode.isPending;

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex-none border-b border-white/10 bg-black/40 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Target className="h-5 w-5 text-cyan-400" />
            <h1 className="text-lg font-semibold">Target Mode Studio</h1>
            <span className="text-sm text-white/60">
              Single-target, many possible futures
            </span>
          </div>
          <div className="flex items-center gap-2">
            {selectedTarget && (
              <div className="flex items-center gap-2 px-3 py-1.5 bg-cyan-500/10 border border-cyan-500/30 text-sm">
                <User className="h-4 w-4 text-cyan-400" />
                <span className="text-cyan-300">{selectedTarget.name}</span>
              </div>
            )}
            {plan && (
              <div
                className={cn(
                  'flex items-center gap-2 px-3 py-1.5 text-sm border',
                  plan.status === 'completed'
                    ? 'bg-green-500/10 border-green-500/30 text-green-300'
                    : plan.status === 'running'
                    ? 'bg-yellow-500/10 border-yellow-500/30 text-yellow-300'
                    : plan.status === 'failed'
                    ? 'bg-red-500/10 border-red-500/30 text-red-300'
                    : 'bg-white/5 border-white/20 text-white/60'
                )}
              >
                {plan.status === 'running' && (
                  <Loader2 className="h-4 w-4 animate-spin" />
                )}
                <span className="capitalize">{plan.status}</span>
                {plan.status === 'completed' && (
                  <span className="text-white/60">
                    ({plan.total_paths_valid} paths)
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Content - 4 Panel Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Column - Target & Context */}
        <div className="w-80 flex-none border-r border-white/10 flex flex-col overflow-hidden">
          {/* Target Persona Panel */}
          <div className="flex-none border-b border-white/10">
            <TargetPersonaPanel
              projectId={projectId}
              personas={personas ?? []}
              selectedTargetId={selectedTargetId}
              onSelectTarget={setSelectedTargetId}
              onCreateTarget={() => setShowCreateTarget(true)}
              isLoading={loadingPersonas}
            />
          </div>

          {/* Context Panel */}
          <div className="flex-1 overflow-y-auto">
            <ContextPanel
              target={selectedTarget}
              parentNodeId={parentNodeId}
              onSelectParentNode={setParentNodeId}
              nodes={nodes ?? []}
            />
          </div>
        </div>

        {/* Center Column - Actions & Planner */}
        <div className="w-80 flex-none border-r border-white/10 flex flex-col overflow-hidden">
          {/* Action Set Panel */}
          <div className="flex-none border-b border-white/10">
            <ActionSetPanel target={selectedTarget} />
          </div>

          {/* Planner Panel */}
          <div className="flex-1 overflow-y-auto">
            <PlannerPanel
              config={plannerConfig}
              onConfigChange={setPlannerConfig}
              onRunPlanner={handleRunPlanner}
              isPlanning={isPlanning}
              canRun={!!selectedTargetId}
            />
          </div>
        </div>

        {/* Right Column - Results */}
        <div className="flex-1 overflow-hidden">
          <ResultsPanel
            plan={plan ?? null}
            isLoading={loadingPlan}
            selectedPathId={selectedPathId}
            onSelectPath={setSelectedPathId}
            onExpandCluster={handleExpandCluster}
            onBranchToNode={handleBranchToNode}
            isExpanding={expandCluster.isPending}
            isBranching={isBranching}
          />
        </div>
      </div>

      {/* Footer Status */}
      {(runPlanner.isError || branchToNode.isError) && (
        <div className="flex-none border-t border-red-500/30 bg-red-500/10 p-3">
          <div className="flex items-center gap-2 text-red-400 text-sm">
            <AlertCircle className="h-4 w-4" />
            <span>
              {runPlanner.error?.message ??
                branchToNode.error?.message ??
                'An error occurred'}
            </span>
          </div>
        </div>
      )}

      {/* Create Target Dialog */}
      <Dialog open={showCreateTarget} onOpenChange={setShowCreateTarget}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Target Persona</DialogTitle>
            <DialogDescription>
              Define a target persona for goal-driven simulation. The planner will find optimal paths to achieve this persona&apos;s objectives.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <label htmlFor="target-name" className="text-sm font-medium text-white/80">
                Target Name
              </label>
              <Input
                id="target-name"
                placeholder="e.g., Early Adopter, Price Sensitive Consumer"
                value={newTargetName}
                onChange={(e) => setNewTargetName(e.target.value)}
                className="bg-white/5 border-white/20 text-white placeholder:text-white/40"
              />
            </div>
            <div className="grid gap-2">
              <label htmlFor="target-goal" className="text-sm font-medium text-white/80">
                Goal / Desired Outcome
              </label>
              <Input
                id="target-goal"
                placeholder="e.g., Achieve 80% purchase intent for EV"
                value={newTargetGoal}
                onChange={(e) => setNewTargetGoal(e.target.value)}
                className="bg-white/5 border-white/20 text-white placeholder:text-white/40"
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setShowCreateTarget(false);
                setNewTargetName('');
                setNewTargetGoal('');
              }}
              className="border-white/20 hover:bg-white/10"
            >
              CANCEL
            </Button>
            <Button
              onClick={async () => {
                try {
                  const result = await createTargetPersona.mutateAsync({
                    name: newTargetName,
                    project_id: projectId,
                    description: newTargetGoal,
                    domain: 'general',
                  });
                  setSelectedTargetId(result.target_id);
                  refetchPersonas();
                  setShowCreateTarget(false);
                  setNewTargetName('');
                  setNewTargetGoal('');
                } catch {
                  // Error handled by mutation
                }
              }}
              disabled={!newTargetName || !newTargetGoal || createTargetPersona.isPending}
              className="bg-cyan-500 hover:bg-cyan-600 text-black"
            >
              {createTargetPersona.isPending ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Plus className="h-4 w-4 mr-2" />
              )}
              {createTargetPersona.isPending ? 'CREATING...' : 'CREATE TARGET'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

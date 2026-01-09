'use client';

import { useState } from 'react';
import {
  GitBranch,
  ChevronDown,
  ChevronRight,
  Loader2,
  TrendingUp,
  Clock,
  AlertTriangle,
  Check,
  ArrowRight,
  Zap,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { PlanResult, PathCluster, TargetPath, PathStep } from '@/lib/api';
import { cn } from '@/lib/utils';

interface ResultsPanelProps {
  plan: PlanResult | null;
  isLoading: boolean;
  selectedPathId: string | null;
  onSelectPath: (pathId: string | null) => void;
  onExpandCluster: (clusterId: string) => void;
  onBranchToNode: () => void;
  isExpanding: boolean;
  isBranching: boolean;
}

interface ClusterCardProps {
  cluster: PathCluster;
  isExpanded: boolean;
  onToggle: () => void;
  onExpand: () => void;
  selectedPathId: string | null;
  onSelectPath: (pathId: string) => void;
  isExpanding: boolean;
}

function ClusterCard({
  cluster,
  isExpanded,
  onToggle,
  onExpand,
  selectedPathId,
  onSelectPath,
  isExpanding,
}: ClusterCardProps) {
  const probability = Math.round(cluster.aggregated_probability * 100);
  const utilityRange = cluster.utility_range;

  return (
    <div className="border border-white/10 bg-white/5">
      {/* Cluster Header */}
      <button
        onClick={onToggle}
        className="w-full p-3 flex items-center gap-3 text-left hover:bg-white/5"
      >
        {isExpanded ? (
          <ChevronDown className="h-4 w-4 text-white/40" />
        ) : (
          <ChevronRight className="h-4 w-4 text-white/40" />
        )}
        <div className="flex-1 min-w-0">
          <div className="font-medium truncate">{cluster.label}</div>
          {cluster.description && (
            <div className="text-xs text-white/50 truncate">
              {cluster.description}
            </div>
          )}
        </div>
        <div className="flex items-center gap-3 text-xs">
          <div
            className={cn(
              'px-2 py-1 font-medium',
              probability >= 50
                ? 'bg-green-500/10 text-green-400'
                : probability >= 20
                ? 'bg-yellow-500/10 text-yellow-400'
                : 'bg-white/5 text-white/60'
            )}
          >
            {probability}%
          </div>
          <div className="text-white/40">
            {cluster.child_paths.length + 1} paths
          </div>
        </div>
      </button>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="border-t border-white/10">
          {/* Cluster Stats */}
          <div className="p-3 grid grid-cols-3 gap-2 text-xs border-b border-white/10">
            <div className="p-2 bg-black/20">
              <div className="text-white/40">Avg Utility</div>
              <div className="font-medium text-green-400">
                {cluster.avg_utility.toFixed(2)}
              </div>
            </div>
            <div className="p-2 bg-black/20">
              <div className="text-white/40">Utility Range</div>
              <div className="font-medium">
                {utilityRange[0].toFixed(1)} - {utilityRange[1].toFixed(1)}
              </div>
            </div>
            <div className="p-2 bg-black/20">
              <div className="text-white/40">Depth</div>
              <div className="font-medium">{cluster.expansion_depth}</div>
            </div>
          </div>

          {/* Common Actions */}
          {cluster.common_actions && cluster.common_actions.length > 0 && (
            <div className="p-3 border-b border-white/10 text-xs">
              <span className="text-white/40">Common actions: </span>
              <span className="text-white/70">
                {cluster.common_actions.join(' -> ')}
              </span>
            </div>
          )}

          {/* Representative Path */}
          <PathCard
            path={cluster.representative_path}
            isSelected={selectedPathId === cluster.representative_path.path_id}
            onSelect={() => onSelectPath(cluster.representative_path.path_id)}
            isRepresentative
          />

          {/* Child Paths */}
          {cluster.child_paths.length > 0 && (
            <div className="border-t border-white/10">
              {cluster.child_paths.map((path) => (
                <PathCard
                  key={path.path_id}
                  path={path}
                  isSelected={selectedPathId === path.path_id}
                  onSelect={() => onSelectPath(path.path_id)}
                />
              ))}
            </div>
          )}

          {/* Expand Button */}
          {cluster.can_expand && (
            <div className="p-2 border-t border-white/10">
              <Button
                variant="outline"
                size="sm"
                onClick={onExpand}
                disabled={isExpanding}
                className="w-full text-xs"
              >
                {isExpanding ? (
                  <>
                    <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                    Expanding...
                  </>
                ) : (
                  <>
                    <ChevronDown className="h-3 w-3 mr-1" />
                    Expand Cluster
                  </>
                )}
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

interface PathCardProps {
  path: TargetPath;
  isSelected: boolean;
  onSelect: () => void;
  isRepresentative?: boolean;
}

function PathCard({ path, isSelected, onSelect, isRepresentative }: PathCardProps) {
  const [showSteps, setShowSteps] = useState(false);
  const probability = Math.round(path.path_probability * 100);

  return (
    <div
      className={cn(
        'border-l-2 transition-colors',
        isSelected
          ? 'border-l-cyan-500 bg-cyan-500/10'
          : isRepresentative
          ? 'border-l-purple-500 bg-purple-500/5'
          : 'border-l-transparent hover:bg-white/5'
      )}
    >
      <button
        onClick={onSelect}
        className="w-full p-3 text-left flex items-start gap-2"
      >
        <input
          type="radio"
          checked={isSelected}
          onChange={() => onSelect()}
          className="mt-1 w-3 h-3"
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 text-sm">
            {isRepresentative && (
              <span className="px-1.5 py-0.5 text-xs bg-purple-500/20 text-purple-300 border border-purple-500/30">
                Representative
              </span>
            )}
            <span className="text-white/60">{path.steps.length} steps</span>
          </div>
          <div className="text-xs text-white/40 mt-1">
            {path.steps.slice(0, 3).map((s) => s.action.name).join(' -> ')}
            {path.steps.length > 3 && '...'}
          </div>
        </div>
        <div className="flex flex-col items-end gap-1 text-xs">
          <div
            className={cn(
              'px-2 py-0.5',
              probability >= 50
                ? 'bg-green-500/10 text-green-400'
                : probability >= 20
                ? 'bg-yellow-500/10 text-yellow-400'
                : 'bg-white/5 text-white/60'
            )}
          >
            {probability}%
          </div>
          <div className="text-green-400">+{path.total_utility.toFixed(2)}</div>
        </div>
      </button>

      {/* Path Steps */}
      {isSelected && (
        <div className="px-3 pb-3">
          <button
            onClick={() => setShowSteps(!showSteps)}
            className="flex items-center gap-1 text-xs text-white/50 hover:text-white/70"
          >
            {showSteps ? (
              <ChevronDown className="h-3 w-3" />
            ) : (
              <ChevronRight className="h-3 w-3" />
            )}
            {showSteps ? 'Hide' : 'Show'} steps
          </button>
          {showSteps && (
            <div className="mt-2 space-y-1">
              {path.steps.map((step, i) => (
                <div
                  key={i}
                  className="flex items-center gap-2 p-2 bg-black/20 text-xs"
                >
                  <span className="w-5 h-5 flex items-center justify-center bg-white/10 text-white/60 font-mono text-xs">
                    {i + 1}
                  </span>
                  <Zap className="h-3 w-3 text-cyan-400" />
                  <span className="flex-1 font-medium">{step.action.name}</span>
                  <span className="text-green-400">
                    +{step.utility_gained.toFixed(2)}
                  </span>
                  <span
                    className={cn(
                      step.probability >= 0.8
                        ? 'text-green-400'
                        : step.probability >= 0.5
                        ? 'text-yellow-400'
                        : 'text-red-400'
                    )}
                  >
                    {Math.round(step.probability * 100)}%
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function ResultsPanel({
  plan,
  isLoading,
  selectedPathId,
  onSelectPath,
  onExpandCluster,
  onBranchToNode,
  isExpanding,
  isBranching,
}: ResultsPanelProps) {
  const [expandedClusters, setExpandedClusters] = useState<Set<string>>(
    new Set()
  );

  const toggleCluster = (clusterId: string) => {
    setExpandedClusters((prev) => {
      const next = new Set(prev);
      if (next.has(clusterId)) {
        next.delete(clusterId);
      } else {
        next.add(clusterId);
      }
      return next;
    });
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex-none p-4 border-b border-white/10 bg-black/40">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <GitBranch className="h-4 w-4 text-cyan-400" />
            <span className="font-medium">Results</span>
            {plan?.status === 'completed' && (
              <span className="text-sm text-white/40">
                {plan.clusters.length} clusters, {plan.total_paths_valid} paths
              </span>
            )}
          </div>
          {selectedPathId && (
            <Button
              onClick={onBranchToNode}
              disabled={isBranching}
              className="bg-cyan-500 hover:bg-cyan-600 text-black"
            >
              {isBranching ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Branching...
                </>
              ) : (
                <>
                  <GitBranch className="h-4 w-4 mr-2" />
                  Branch to Universe Map
                </>
              )}
            </Button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-cyan-400" />
          </div>
        ) : !plan ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <GitBranch className="h-12 w-12 text-white/20 mb-4" />
            <div className="text-white/40">No planning results yet</div>
            <div className="text-sm text-white/30 mt-1">
              Select a target and run the planner
            </div>
          </div>
        ) : plan.status === 'failed' ? (
          <div className="p-4 bg-red-500/10 border border-red-500/30 text-center">
            <AlertTriangle className="h-8 w-8 text-red-400 mx-auto mb-2" />
            <div className="text-red-300 font-medium">Planning Failed</div>
            {plan.error_message && (
              <div className="text-sm text-red-400/70 mt-1">
                {plan.error_message}
              </div>
            )}
          </div>
        ) : plan.status === 'running' ? (
          <div className="flex flex-col items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-cyan-400 mb-4" />
            <div className="text-white/60">Planning in progress...</div>
          </div>
        ) : plan.total_paths_valid === 0 ? (
          <div className="p-4 bg-yellow-500/10 border border-yellow-500/30 text-center">
            <AlertTriangle className="h-8 w-8 text-yellow-400 mx-auto mb-2" />
            <div className="text-yellow-300 font-medium">No Feasible Paths</div>
            <div className="text-sm text-yellow-400/70 mt-1">
              All paths were pruned by constraints.
              <br />
              Try relaxing constraints or adding more actions.
            </div>
          </div>
        ) : (
          <>
            {/* Summary */}
            <div className="grid grid-cols-4 gap-2 text-xs">
              <div className="p-3 bg-white/5 border border-white/10">
                <div className="text-white/40">Generated</div>
                <div className="text-lg font-medium">
                  {plan.total_paths_generated}
                </div>
              </div>
              <div className="p-3 bg-green-500/10 border border-green-500/30">
                <div className="text-green-400/70">Valid</div>
                <div className="text-lg font-medium text-green-400">
                  {plan.total_paths_valid}
                </div>
              </div>
              <div className="p-3 bg-red-500/10 border border-red-500/30">
                <div className="text-red-400/70">Pruned</div>
                <div className="text-lg font-medium text-red-400">
                  {plan.total_paths_pruned}
                </div>
              </div>
              <div className="p-3 bg-white/5 border border-white/10">
                <div className="text-white/40">Time</div>
                <div className="text-lg font-medium">
                  {plan.planning_time_ms}ms
                </div>
              </div>
            </div>

            {/* Planning Summary */}
            {plan.planning_summary && (
              <div className="p-3 bg-cyan-500/10 border border-cyan-500/30 text-sm">
                <div className="text-cyan-300 font-medium mb-1">Summary</div>
                <div className="text-white/70">{plan.planning_summary}</div>
              </div>
            )}

            {/* Key Decision Points */}
            {plan.key_decision_points && plan.key_decision_points.length > 0 && (
              <div className="text-xs">
                <span className="text-white/40">Key decisions: </span>
                <span className="text-white/70">
                  {plan.key_decision_points.join(' | ')}
                </span>
              </div>
            )}

            {/* Clusters */}
            <div className="space-y-2">
              {plan.clusters.map((cluster) => (
                <ClusterCard
                  key={cluster.cluster_id}
                  cluster={cluster}
                  isExpanded={expandedClusters.has(cluster.cluster_id)}
                  onToggle={() => toggleCluster(cluster.cluster_id)}
                  onExpand={() => onExpandCluster(cluster.cluster_id)}
                  selectedPathId={selectedPathId}
                  onSelectPath={onSelectPath}
                  isExpanding={isExpanding}
                />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

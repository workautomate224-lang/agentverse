'use client';

/**
 * CompareView Component
 * Side-by-side comparison of 2-4 nodes showing outcomes, drivers, and reliability.
 * Reference: Interaction_design.md §5.11
 */

import { memo, useState, useCallback, useMemo } from 'react';
import {
  X,
  Pin,
  PinOff,
  Download,
  Plus,
  Trash2,
  TrendingUp,
  TrendingDown,
  Minus,
  AlertCircle,
  Loader2,
  GitBranch,
  Target,
  BarChart3,
  Shield,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { useCompareNodes } from '@/hooks/useApi';
import type { NodeSummary, CompareNodesResponse } from '@/lib/api';

interface CompareViewProps {
  selectedNodes: NodeSummary[];
  onAddNode?: () => void;
  onRemoveNode?: (nodeId: string) => void;
  onClose?: () => void;
  pinnedNodeId?: string;
  onPinNode?: (nodeId: string | null) => void;
  className?: string;
}

// Trend indicator component
function TrendIndicator({ value, baseline }: { value: number; baseline: number }) {
  const diff = value - baseline;
  const percentDiff = baseline !== 0 ? (diff / baseline) * 100 : 0;

  if (Math.abs(percentDiff) < 1) {
    return (
      <span className="flex items-center gap-1 text-white/40">
        <Minus className="w-3 h-3" />
        <span className="text-[10px]">0%</span>
      </span>
    );
  }

  if (diff > 0) {
    return (
      <span className="flex items-center gap-1 text-green-400">
        <TrendingUp className="w-3 h-3" />
        <span className="text-[10px]">+{percentDiff.toFixed(1)}%</span>
      </span>
    );
  }

  return (
    <span className="flex items-center gap-1 text-red-400">
      <TrendingDown className="w-3 h-3" />
      <span className="text-[10px]">{percentDiff.toFixed(1)}%</span>
    </span>
  );
}

export const CompareView = memo(function CompareView({
  selectedNodes,
  onAddNode,
  onRemoveNode,
  onClose,
  pinnedNodeId,
  onPinNode,
  className,
}: CompareViewProps) {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(['outcomes', 'drivers'])
  );

  // Fetch comparison data
  const compareNodes = useCompareNodes();

  // Fetch comparison when nodes change
  const nodeIds = useMemo(() => selectedNodes.map((n) => n.node_id), [selectedNodes]);

  // Trigger comparison
  const handleCompare = useCallback(() => {
    if (nodeIds.length >= 2) {
      compareNodes.mutate(nodeIds);
    }
  }, [nodeIds, compareNodes]);

  // Auto-compare when we have 2+ nodes
  useMemo(() => {
    if (nodeIds.length >= 2 && !compareNodes.data && !compareNodes.isPending) {
      compareNodes.mutate(nodeIds);
    }
  }, [nodeIds, compareNodes]);

  const comparisonData = compareNodes.data;
  const pinnedNode = selectedNodes.find((n) => n.node_id === pinnedNodeId);
  const baselineNode = pinnedNode || selectedNodes[0];

  // Toggle section
  const toggleSection = useCallback((section: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(section)) {
        next.delete(section);
      } else {
        next.add(section);
      }
      return next;
    });
  }, []);

  // Export handler
  const handleExport = useCallback(() => {
    if (!comparisonData) return;

    const exportData = {
      nodes: selectedNodes.map((n) => ({
        node_id: n.node_id,
        label: n.label,
        probability: n.probability,
      })),
      comparison: comparisonData,
      exported_at: new Date().toISOString(),
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `compare-${nodeIds.slice(0, 2).join('-')}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [comparisonData, selectedNodes, nodeIds]);

  // Not enough nodes
  if (selectedNodes.length < 2) {
    return (
      <div className={cn('bg-black border-t border-white/10 p-4', className)}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-cyan-400" />
            <span className="text-sm font-mono font-bold text-white">Compare Nodes</span>
          </div>
          {onClose && (
            <Button variant="ghost" size="icon-sm" onClick={onClose}>
              <X className="w-4 h-4" />
            </Button>
          )}
        </div>
        <div className="flex items-center justify-center py-8">
          <div className="text-center">
            <GitBranch className="w-6 h-6 text-white/20 mx-auto mb-2" />
            <p className="text-sm font-mono text-white/40">
              Select at least 2 nodes to compare
            </p>
            <p className="text-xs font-mono text-white/30 mt-1">
              Shift+click nodes in the Universe Map
            </p>
            {onAddNode && (
              <Button variant="secondary" size="sm" className="mt-4" onClick={onAddNode}>
                <Plus className="w-3 h-3 mr-1" />
                Add Node
              </Button>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={cn('bg-black border-t border-white/10', className)}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className="p-1.5 bg-cyan-500/10">
            <BarChart3 className="w-4 h-4 text-cyan-400" />
          </div>
          <div>
            <span className="text-sm font-mono font-bold text-white">
              Compare Nodes
            </span>
            <span className="text-xs font-mono text-white/40 ml-2">
              {selectedNodes.length} selected
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {selectedNodes.length < 4 && onAddNode && (
            <Button variant="ghost" size="sm" onClick={onAddNode}>
              <Plus className="w-3 h-3 mr-1" />
              Add
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleExport}
            disabled={!comparisonData}
          >
            <Download className="w-3 h-3 mr-1" />
            Export
          </Button>
          {onClose && (
            <Button variant="ghost" size="icon-sm" onClick={onClose}>
              <X className="w-4 h-4" />
            </Button>
          )}
        </div>
      </div>

      {/* Node Headers */}
      <div className="flex border-b border-white/10">
        <div className="w-32 shrink-0 px-4 py-2 bg-white/5 border-r border-white/10">
          <span className="text-[10px] font-mono text-white/40 uppercase tracking-wider">
            Metric
          </span>
        </div>
        {selectedNodes.map((node) => {
          const isBaseline = node.node_id === baselineNode?.node_id;
          const isPinned = node.node_id === pinnedNodeId;

          return (
            <div
              key={node.node_id}
              className={cn(
                'flex-1 px-4 py-2 border-r border-white/10 last:border-r-0',
                isBaseline && 'bg-cyan-500/5'
              )}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {isBaseline ? (
                    <Target className="w-3 h-3 text-cyan-400" />
                  ) : (
                    <GitBranch className="w-3 h-3 text-white/40" />
                  )}
                  <span className="text-xs font-mono text-white truncate max-w-[80px]">
                    {node.label || node.node_id.slice(0, 8)}
                  </span>
                </div>
                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => onPinNode?.(isPinned ? null : node.node_id)}
                    title={isPinned ? 'Unpin baseline' : 'Pin as baseline'}
                  >
                    {isPinned ? (
                      <PinOff className="w-3 h-3 text-cyan-400" />
                    ) : (
                      <Pin className="w-3 h-3" />
                    )}
                  </Button>
                  {onRemoveNode && (
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => onRemoveNode(node.node_id)}
                      title="Remove from comparison"
                    >
                      <Trash2 className="w-3 h-3" />
                    </Button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Loading State */}
      {compareNodes.isPending && (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-5 h-5 text-cyan-400 animate-spin" />
          <span className="ml-2 text-sm font-mono text-white/40">Comparing nodes...</span>
        </div>
      )}

      {/* Error State */}
      {compareNodes.isError && (
        <div className="flex items-center justify-center py-8">
          <AlertCircle className="w-5 h-5 text-red-400" />
          <span className="ml-2 text-sm font-mono text-red-400">
            Failed to compare nodes
          </span>
          <Button variant="secondary" size="sm" className="ml-4" onClick={handleCompare}>
            Retry
          </Button>
        </div>
      )}

      {/* Comparison Data */}
      {comparisonData && (
        <div className="max-h-80 overflow-y-auto">
          {/* Outcomes Section */}
          <div className="border-b border-white/10">
            <button
              onClick={() => toggleSection('outcomes')}
              className="w-full flex items-center justify-between px-4 py-2 bg-white/5 hover:bg-white/10 transition-colors"
            >
              <div className="flex items-center gap-2">
                <Target className="w-3.5 h-3.5 text-white/40" />
                <span className="text-xs font-mono text-white/60 uppercase tracking-wider">
                  Outcomes
                </span>
              </div>
              {expandedSections.has('outcomes') ? (
                <ChevronUp className="w-3 h-3 text-white/40" />
              ) : (
                <ChevronDown className="w-3 h-3 text-white/40" />
              )}
            </button>

            {expandedSections.has('outcomes') && (
              <div>
                {/* Probability Row */}
                <div className="flex border-b border-white/5">
                  <div className="w-32 shrink-0 px-4 py-2 border-r border-white/10">
                    <span className="text-xs font-mono text-white/60">Probability</span>
                  </div>
                  {selectedNodes.map((node) => {
                    const prob = node.probability ?? 1;
                    const baselineProb = baselineNode?.probability ?? 1;

                    return (
                      <div
                        key={node.node_id}
                        className="flex-1 px-4 py-2 border-r border-white/10 last:border-r-0"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-mono text-white">
                            {(prob * 100).toFixed(1)}%
                          </span>
                          {node.node_id !== baselineNode?.node_id && (
                            <TrendIndicator value={prob} baseline={baselineProb} />
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Outcome Distribution */}
                {comparisonData.outcome_comparison &&
                  Object.entries(comparisonData.outcome_comparison).map(([metric, values]) => (
                    <div key={metric} className="flex border-b border-white/5">
                      <div className="w-32 shrink-0 px-4 py-2 border-r border-white/10">
                        <span className="text-xs font-mono text-white/60 capitalize">
                          {metric.replace(/_/g, ' ')}
                        </span>
                      </div>
                      {selectedNodes.map((node) => {
                        const value = values[node.node_id] ?? 0;
                        const baselineValue = values[baselineNode?.node_id ?? ''] ?? 0;

                        return (
                          <div
                            key={node.node_id}
                            className="flex-1 px-4 py-2 border-r border-white/10 last:border-r-0"
                          >
                            <div className="flex items-center justify-between">
                              <span className="text-sm font-mono text-white">
                                {typeof value === 'number' ? value.toFixed(2) : value}
                              </span>
                              {node.node_id !== baselineNode?.node_id && (
                                <TrendIndicator value={value} baseline={baselineValue} />
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ))}
              </div>
            )}
          </div>

          {/* Drivers Section */}
          <div className="border-b border-white/10">
            <button
              onClick={() => toggleSection('drivers')}
              className="w-full flex items-center justify-between px-4 py-2 bg-white/5 hover:bg-white/10 transition-colors"
            >
              <div className="flex items-center gap-2">
                <TrendingUp className="w-3.5 h-3.5 text-white/40" />
                <span className="text-xs font-mono text-white/60 uppercase tracking-wider">
                  Key Differences
                </span>
              </div>
              {expandedSections.has('drivers') ? (
                <ChevronUp className="w-3 h-3 text-white/40" />
              ) : (
                <ChevronDown className="w-3 h-3 text-white/40" />
              )}
            </button>

            {expandedSections.has('drivers') && comparisonData.key_differences && (
              <div className="p-4 space-y-2">
                {comparisonData.key_differences.length === 0 ? (
                  <p className="text-xs font-mono text-white/40">No significant differences</p>
                ) : (
                  comparisonData.key_differences.slice(0, 5).map((diff, index) => {
                    const node = selectedNodes.find((n) => n.node_id === diff.node_id);
                    return (
                      <div
                        key={index}
                        className="flex items-center justify-between p-2 bg-white/5 border border-white/10"
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-mono text-white/40">
                            #{diff.rank}
                          </span>
                          <span className="text-xs font-mono text-white">
                            {diff.metric.replace(/_/g, ' ')}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono text-white/60">
                            {node?.label || diff.node_id.slice(0, 6)}:
                          </span>
                          <span className="text-xs font-mono text-cyan-400">
                            {diff.value.toFixed(2)}
                          </span>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            )}
          </div>

          {/* Reliability Section */}
          <div className="border-b border-white/10">
            <button
              onClick={() => toggleSection('reliability')}
              className="w-full flex items-center justify-between px-4 py-2 bg-white/5 hover:bg-white/10 transition-colors"
            >
              <div className="flex items-center gap-2">
                <Shield className="w-3.5 h-3.5 text-white/40" />
                <span className="text-xs font-mono text-white/60 uppercase tracking-wider">
                  Reliability
                </span>
              </div>
              {expandedSections.has('reliability') ? (
                <ChevronUp className="w-3 h-3 text-white/40" />
              ) : (
                <ChevronDown className="w-3 h-3 text-white/40" />
              )}
            </button>

            {expandedSections.has('reliability') && (
              <div className="flex border-b border-white/5">
                <div className="w-32 shrink-0 px-4 py-2 border-r border-white/10">
                  <span className="text-xs font-mono text-white/60">Confidence</span>
                </div>
                {selectedNodes.map((node) => {
                  const conf = node.confidence_level ?? 'medium';
                  const colors: Record<string, string> = {
                    high: 'text-green-400',
                    medium: 'text-yellow-400',
                    low: 'text-red-400',
                  };

                  return (
                    <div
                      key={node.node_id}
                      className="flex-1 px-4 py-2 border-r border-white/10 last:border-r-0"
                    >
                      <span className={cn('text-sm font-mono capitalize', colors[conf])}>
                        {conf}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Recommendation */}
          {comparisonData.recommendation && (
            <div className="p-4 bg-cyan-500/5 border-b border-cyan-500/20">
              <div className="flex items-start gap-2">
                <Target className="w-4 h-4 text-cyan-400 mt-0.5" />
                <div>
                  <p className="text-xs font-mono text-cyan-400 uppercase tracking-wider mb-1">
                    Recommendation
                  </p>
                  <p className="text-sm font-mono text-white/80">
                    {comparisonData.recommendation}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
});

export default CompareView;

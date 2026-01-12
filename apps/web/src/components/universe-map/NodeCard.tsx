'use client';

/**
 * NodeCard Component
 * Displays a single Universe Map node with outcome and fork info.
 * Reference: project.md §6.7 (Node entity), C1 (fork-not-mutate)
 */

import { memo, useMemo } from 'react';
import Link from 'next/link';
import {
  GitBranch,
  GitMerge,
  Play,
  CheckCircle,
  Clock,
  AlertTriangle,
  ExternalLink,
  ChevronRight,
  Target,
  Percent,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import type { SpecNode, NodeSummary } from '@/lib/api';

// Type guard to check if node is SpecNode (has run_refs)
function isSpecNode(node: SpecNode | NodeSummary): node is SpecNode {
  return 'run_refs' in node && Array.isArray((node as SpecNode).run_refs);
}

// Helper to get run ID from run_refs (handles both string and object formats)
function getRunId(runRef: string | { artifact_id: string }): string {
  return typeof runRef === 'string' ? runRef : runRef.artifact_id;
}

interface NodeCardProps {
  node: SpecNode | NodeSummary;
  isSelected?: boolean;
  isHighlighted?: boolean;
  onSelect?: (nodeId: string) => void;
  onFork?: (nodeId: string) => void;
  onViewRun?: (runId: string) => void;
  showOutcome?: boolean;
  showActions?: boolean;
  compact?: boolean;
  className?: string;
}

// Color for outcome visualization
const outcomeColors: Record<string, string> = {
  positive: 'border-green-500/50 bg-green-500/10',
  negative: 'border-red-500/50 bg-red-500/10',
  neutral: 'border-white/20 bg-white/5',
  mixed: 'border-yellow-500/50 bg-yellow-500/10',
};

export const NodeCard = memo(function NodeCard({
  node,
  isSelected,
  isHighlighted,
  onSelect,
  onFork,
  onViewRun,
  showOutcome = true,
  showActions = true,
  compact = false,
  className,
}: NodeCardProps) {
  // Get outcome data (different structure between SpecNode and NodeSummary)
  const hasOutcome = 'has_outcome' in node ? node.has_outcome : 'aggregated_outcome' in node && node.aggregated_outcome !== undefined;
  const outcomeData = 'aggregated_outcome' in node ? node.aggregated_outcome : undefined;

  // Determine dominant outcome color
  const outcomeColor = useMemo(() => {
    if (!outcomeData) return outcomeColors.neutral;
    const summary = outcomeData.outcome_distribution;
    if (!summary) return outcomeColors.neutral;
    const entries = Object.entries(summary);
    if (entries.length === 0) return outcomeColors.neutral;
    // Use first entry to determine color (simplified)
    return outcomeColors.neutral;
  }, [outcomeData]);

  // Check if node is root (no parent)
  const isRoot = !node.parent_node_id;

  // Get child count (safely handle undefined)
  const childCount = 'child_count' in node ? (node.child_count ?? 0) : 0;

  // Compact version (for tree display)
  if (compact) {
    return (
      <div
        onClick={() => onSelect?.(node.node_id)}
        className={cn(
          'flex items-center gap-2 px-3 py-2 cursor-pointer transition-all',
          'border',
          isSelected
            ? 'bg-cyan-500/20 border-cyan-500/50'
            : isHighlighted
            ? 'bg-white/10 border-white/30'
            : 'bg-black border-white/10 hover:border-white/20',
          className
        )}
      >
        {isRoot ? (
          <Target className="w-3.5 h-3.5 text-cyan-400" />
        ) : (
          <GitBranch className="w-3.5 h-3.5 text-white/40" />
        )}
        <span className="text-xs font-mono text-white truncate flex-1">
          {node.node_id.slice(0, 8)}
        </span>
        {childCount > 0 && (
          <span className="text-[10px] font-mono text-white/40">
            +{childCount}
          </span>
        )}
      </div>
    );
  }

  // Full card version
  return (
    <div
      onClick={() => onSelect?.(node.node_id)}
      className={cn(
        'bg-black border cursor-pointer transition-all',
        isSelected
          ? 'border-cyan-500/50 ring-1 ring-cyan-500/30'
          : isHighlighted
          ? 'border-white/30'
          : 'border-white/10 hover:border-white/20',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
        <div className="flex items-center gap-2">
          {isRoot ? (
            <div className="p-1.5 bg-cyan-500/10">
              <Target className="w-3.5 h-3.5 text-cyan-400" />
            </div>
          ) : (
            <div className="p-1.5 bg-white/5">
              <GitBranch className="w-3.5 h-3.5 text-white/40" />
            </div>
          )}
          <div>
            <span className="text-xs font-mono font-bold text-white">
              {isRoot ? 'Root Node' : 'Node'}
            </span>
            <span className="text-[10px] font-mono text-white/40 ml-2">
              {node.node_id.slice(0, 12)}
            </span>
          </div>
        </div>

        {childCount > 0 && (
          <div className="flex items-center gap-1 px-2 py-0.5 bg-white/5 border border-white/10">
            <GitMerge className="w-3 h-3 text-white/40" />
            <span className="text-[10px] font-mono text-white/60">
              {childCount} forks
            </span>
          </div>
        )}
      </div>

      {/* Outcome Summary */}
      {showOutcome && hasOutcome && outcomeData?.outcome_distribution && (
        <div className="px-4 py-3 border-b border-white/10">
          <div className="flex items-center gap-2 mb-2">
            <Percent className="w-3.5 h-3.5 text-white/40" />
            <span className="text-[10px] font-mono text-white/40 uppercase tracking-wider">
              Outcome Distribution
            </span>
          </div>
          <div className="flex gap-1 h-4 overflow-hidden">
            {Object.entries(outcomeData.outcome_distribution).map(([label, count], index) => {
              const total = Object.values(outcomeData.outcome_distribution || {}).reduce(
                (a: number, b) => a + (b as number),
                0
              );
              const percent = total > 0 ? ((count as number) / total) * 100 : 0;
              const colors = [
                'bg-cyan-500',
                'bg-blue-500',
                'bg-purple-500',
                'bg-pink-500',
                'bg-orange-500',
              ];
              return (
                <div
                  key={label}
                  className={cn('h-full', colors[index % colors.length])}
                  style={{ width: `${percent}%` }}
                  title={`${label}: ${percent.toFixed(1)}%`}
                />
              );
            })}
          </div>
        </div>
      )}

      {/* Meta Info */}
      <div className="px-4 py-3 grid grid-cols-2 gap-3">
        {/* Run Reference */}
        {isSpecNode(node) && node.run_refs && node.run_refs.length > 0 && (
          <div className="flex items-center gap-2">
            <Play className="w-3 h-3 text-white/40" />
            <div>
              <p className="text-[10px] font-mono text-white/40">Run</p>
              <p className="text-xs font-mono text-white truncate">
                {getRunId(node.run_refs[0]).slice(0, 8)}
              </p>
            </div>
          </div>
        )}

        {/* Probability */}
        {'probability' in node && node.probability !== undefined && (
          <div className="flex items-center gap-2">
            <Target className="w-3 h-3 text-white/40" />
            <div>
              <p className="text-[10px] font-mono text-white/40">Probability</p>
              <p className="text-xs font-mono text-white">
                {(node.probability * 100).toFixed(1)}%
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Actions */}
      {showActions && (
        <div className="flex items-center justify-between px-4 py-2 border-t border-white/10">
          <span className="text-[10px] font-mono text-white/30">
            {new Date(node.created_at).toLocaleDateString()}
          </span>

          <div className="flex items-center gap-1">
            {onFork && (
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={(e) => {
                  e.stopPropagation();
                  onFork(node.node_id);
                }}
                title="Fork Node"
              >
                <GitBranch className="w-3 h-3" />
              </Button>
            )}
            {isSpecNode(node) && node.run_refs && node.run_refs.length > 0 && onViewRun && (
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={(e) => {
                  e.stopPropagation();
                  onViewRun(getRunId(node.run_refs![0]));
                }}
                title="View Run"
              >
                <ExternalLink className="w-3 h-3" />
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  );
});

export default NodeCard;

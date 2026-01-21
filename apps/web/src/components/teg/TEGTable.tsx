'use client';

/**
 * TEG Table Component
 *
 * Sorted list of nodes with filters.
 * Reference: docs/TEG_UNIVERSE_MAP_EXECUTION.md Section 2.2.B
 */

import { useState, useMemo } from 'react';
import {
  CheckCircle,
  Clock,
  Activity,
  XCircle,
  Edit3,
  FileText,
  Sparkles,
  ArrowUp,
  ArrowDown,
  Filter,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { TEGTableProps, TEGNode, TEGNodeType, TEGNodeStatus, ConfidenceLevel } from './types';

const statusConfig: Record<TEGNodeStatus, { icon: typeof CheckCircle; color: string; label: string }> = {
  DRAFT: { icon: Edit3, color: 'text-gray-400 bg-gray-500/10', label: 'Draft' },
  QUEUED: { icon: Clock, color: 'text-blue-400 bg-blue-500/10', label: 'Queued' },
  RUNNING: { icon: Activity, color: 'text-cyan-400 bg-cyan-500/10', label: 'Running' },
  DONE: { icon: CheckCircle, color: 'text-green-400 bg-green-500/10', label: 'Done' },
  FAILED: { icon: XCircle, color: 'text-red-400 bg-red-500/10', label: 'Failed' },
};

const typeConfig: Record<TEGNodeType, { icon: typeof FileText; color: string; label: string }> = {
  OUTCOME_VERIFIED: { icon: CheckCircle, color: 'text-cyan-400 bg-cyan-500/10', label: 'Verified' },
  SCENARIO_DRAFT: { icon: Sparkles, color: 'text-purple-400 bg-purple-500/10', label: 'Draft' },
  EVIDENCE: { icon: FileText, color: 'text-amber-400 bg-amber-500/10', label: 'Evidence' },
};

const confidenceColors: Record<ConfidenceLevel, string> = {
  high: 'text-green-400 bg-green-500/10',
  medium: 'text-yellow-400 bg-yellow-500/10',
  low: 'text-red-400 bg-red-500/10',
};

function getProbability(node: TEGNode): number | null {
  if (node.type === 'OUTCOME_VERIFIED') {
    return (node.payload as { primary_outcome_probability?: number })?.primary_outcome_probability ?? null;
  }
  return null;
}

function getDelta(node: TEGNode): number | null {
  if (node.type === 'SCENARIO_DRAFT') {
    return (node.payload as { estimated_delta?: number })?.estimated_delta ?? null;
  }
  if (node.type === 'OUTCOME_VERIFIED') {
    return (node.payload as { actual_delta?: number })?.actual_delta ?? null;
  }
  return null;
}

function getConfidence(node: TEGNode): ConfidenceLevel | null {
  if (node.type === 'SCENARIO_DRAFT') {
    return (node.payload as { confidence_level?: ConfidenceLevel })?.confidence_level ?? null;
  }
  return null;
}

type SortKey = 'impact' | 'confidence' | 'created' | 'title';

export function TEGTable({
  nodes,
  selectedNodeId,
  onNodeSelect,
  sortBy: initialSortBy = 'impact',
  sortOrder: initialSortOrder = 'desc',
  onSortChange,
  filters,
  onFilterChange,
}: TEGTableProps) {
  const [sortBy, setSortBy] = useState<SortKey>(initialSortBy);
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>(initialSortOrder);
  const [showFilters, setShowFilters] = useState(false);

  const handleSort = (key: SortKey) => {
    if (sortBy === key) {
      const newOrder = sortOrder === 'asc' ? 'desc' : 'asc';
      setSortOrder(newOrder);
      onSortChange?.(key, newOrder);
    } else {
      setSortBy(key);
      setSortOrder('desc');
      onSortChange?.(key, 'desc');
    }
  };

  const sortedNodes = useMemo(() => {
    let filtered = [...nodes];

    // Apply filters
    if (filters?.type?.length) {
      filtered = filtered.filter((n) => filters.type!.includes(n.type));
    }
    if (filters?.status?.length) {
      filtered = filtered.filter((n) => filters.status!.includes(n.status));
    }

    // Sort
    filtered.sort((a, b) => {
      let comparison = 0;

      switch (sortBy) {
        case 'impact': {
          const deltaA = Math.abs(getDelta(a) ?? 0);
          const deltaB = Math.abs(getDelta(b) ?? 0);
          comparison = deltaA - deltaB;
          break;
        }
        case 'confidence': {
          const confOrder: Record<ConfidenceLevel, number> = { high: 3, medium: 2, low: 1 };
          const confA = confOrder[getConfidence(a) ?? 'low'];
          const confB = confOrder[getConfidence(b) ?? 'low'];
          comparison = confA - confB;
          break;
        }
        case 'created': {
          comparison = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
          break;
        }
        case 'title': {
          comparison = a.title.localeCompare(b.title);
          break;
        }
      }

      return sortOrder === 'asc' ? comparison : -comparison;
    });

    return filtered;
  }, [nodes, sortBy, sortOrder, filters]);

  const SortIcon = ({ column }: { column: SortKey }) => {
    if (sortBy !== column) return null;
    return sortOrder === 'asc' ? (
      <ArrowUp className="w-3 h-3 inline ml-1" />
    ) : (
      <ArrowDown className="w-3 h-3 inline ml-1" />
    );
  };

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center justify-between p-3 border-b border-white/10">
        <div className="text-xs font-mono text-white/50">
          {sortedNodes.length} node{sortedNodes.length !== 1 ? 's' : ''}
        </div>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className={cn(
            'flex items-center gap-1.5 px-2 py-1 text-xs font-mono transition-colors',
            showFilters ? 'text-cyan-400 bg-cyan-500/10' : 'text-white/60 hover:text-white'
          )}
        >
          <Filter className="w-3 h-3" />
          Filters
        </button>
      </div>

      {/* Filter panel (placeholder for Task 3) */}
      {showFilters && (
        <div className="p-3 border-b border-white/10 bg-white/5">
          <div className="text-xs text-white/50 font-mono">
            Filter controls coming in Task 3...
          </div>
        </div>
      )}

      {/* Table */}
      <div className="flex-1 overflow-auto">
        <table className="w-full">
          <thead className="sticky top-0 bg-black/90 backdrop-blur-sm">
            <tr className="text-left text-[10px] font-mono uppercase text-white/50 border-b border-white/10">
              <th
                className="px-4 py-2 cursor-pointer hover:text-white"
                onClick={() => handleSort('title')}
              >
                Title <SortIcon column="title" />
              </th>
              <th className="px-4 py-2">Type</th>
              <th
                className="px-4 py-2 cursor-pointer hover:text-white"
                onClick={() => handleSort('impact')}
              >
                Probability / Delta <SortIcon column="impact" />
              </th>
              <th
                className="px-4 py-2 cursor-pointer hover:text-white"
                onClick={() => handleSort('confidence')}
              >
                Confidence <SortIcon column="confidence" />
              </th>
              <th className="px-4 py-2">Status</th>
              <th
                className="px-4 py-2 cursor-pointer hover:text-white"
                onClick={() => handleSort('created')}
              >
                Created <SortIcon column="created" />
              </th>
            </tr>
          </thead>
          <tbody>
            {sortedNodes.map((node) => {
              const status = statusConfig[node.status];
              const type = typeConfig[node.type];
              const StatusIcon = status.icon;
              const TypeIcon = type.icon;
              const probability = getProbability(node);
              const delta = getDelta(node);
              const confidence = getConfidence(node);

              return (
                <tr
                  key={node.node_id}
                  onClick={() => onNodeSelect(node.node_id)}
                  className={cn(
                    'border-b border-white/5 cursor-pointer transition-colors',
                    selectedNodeId === node.node_id
                      ? 'bg-cyan-500/10'
                      : 'hover:bg-white/5'
                  )}
                >
                  <td className="px-4 py-3">
                    <div className="text-sm text-white/90 font-medium line-clamp-1">
                      {node.title}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className={cn('inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-mono', type.color)}>
                      <TypeIcon className="w-3 h-3" />
                      {type.label}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    {probability !== null && (
                      <span className="text-cyan-400 font-mono">
                        {(probability * 100).toFixed(1)}%
                      </span>
                    )}
                    {delta !== null && (
                      <span className={cn('font-mono', delta > 0 ? 'text-green-400' : delta < 0 ? 'text-red-400' : 'text-white/50')}>
                        {delta > 0 ? '+' : ''}{(delta * 100).toFixed(0)}%
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {confidence && (
                      <span className={cn('px-2 py-0.5 text-[10px] font-mono uppercase', confidenceColors[confidence])}>
                        {confidence}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className={cn('inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-mono', status.color)}>
                      <StatusIcon className="w-3 h-3" />
                      {status.label}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-xs text-white/50 font-mono">
                      {new Date(node.created_at).toLocaleDateString()}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {sortedNodes.length === 0 && (
          <div className="flex items-center justify-center h-40 text-white/50 text-sm">
            No nodes to display
          </div>
        )}
      </div>
    </div>
  );
}

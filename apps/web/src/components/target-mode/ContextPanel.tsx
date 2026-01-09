'use client';

import { Settings, AlertTriangle, MapPin, Clock, DollarSign } from 'lucide-react';
import { TargetPersona, NodeSummary } from '@/lib/api';
import { cn } from '@/lib/utils';

interface ContextPanelProps {
  target: TargetPersona | null;
  parentNodeId: string | null;
  onSelectParentNode: (nodeId: string | null) => void;
  nodes: NodeSummary[];
}

export function ContextPanel({
  target,
  parentNodeId,
  onSelectParentNode,
  nodes,
}: ContextPanelProps) {
  // Get hard and soft constraints
  const hardConstraints = target?.personal_constraints?.filter(
    (c) => c.constraint_type === 'hard'
  ) ?? [];
  const softConstraints = target?.personal_constraints?.filter(
    (c) => c.constraint_type === 'soft'
  ) ?? [];

  // Initial state summary
  const stateEntries = Object.entries(target?.initial_state ?? {}).slice(0, 6);

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Settings className="h-4 w-4 text-cyan-400" />
        <span className="text-sm font-medium">Context & Constraints</span>
      </div>

      {!target ? (
        <div className="text-sm text-white/40 text-center py-8 border border-dashed border-white/20 rounded">
          Select a target persona to view context
        </div>
      ) : (
        <>
          {/* Starting Node */}
          <div className="space-y-2">
            <div className="text-xs text-white/60 uppercase tracking-wider">
              Starting Point
            </div>
            <select
              value={parentNodeId ?? ''}
              onChange={(e) => onSelectParentNode(e.target.value || null)}
              className="w-full p-2 bg-white/5 border border-white/20 text-sm focus:border-cyan-500/50 focus:outline-none"
            >
              <option value="">Root Node (baseline)</option>
              {nodes.map((node) => (
                <option key={node.node_id} value={node.node_id}>
                  {node.label ?? `Node ${node.node_id.slice(0, 8)}`}
                  {node.probability != null && ` (${Math.round(node.probability * 100)}%)`}
                </option>
              ))}
            </select>
          </div>

          {/* Initial State */}
          <div className="space-y-2">
            <div className="text-xs text-white/60 uppercase tracking-wider">
              Initial State
            </div>
            {stateEntries.length === 0 ? (
              <div className="text-xs text-white/40 text-center py-2">
                No state variables defined
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                {stateEntries.map(([key, value]) => (
                  <div
                    key={key}
                    className="p-2 bg-white/5 border border-white/10 text-xs"
                  >
                    <div className="text-white/40 truncate">{key}</div>
                    <div className="font-medium truncate">
                      {typeof value === 'number'
                        ? value.toLocaleString()
                        : String(value)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Hard Constraints */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs text-white/60 uppercase tracking-wider">
              <AlertTriangle className="h-3 w-3 text-red-400" />
              Hard Constraints ({hardConstraints.length})
            </div>
            {hardConstraints.length === 0 ? (
              <div className="text-xs text-white/40 text-center py-2">
                No hard constraints
              </div>
            ) : (
              <div className="space-y-1">
                {hardConstraints.map((c) => (
                  <div
                    key={c.constraint_id}
                    className="p-2 bg-red-500/10 border border-red-500/30 text-xs"
                  >
                    <div className="font-medium text-red-300">{c.name}</div>
                    {c.description && (
                      <div className="text-white/50 mt-0.5">{c.description}</div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Soft Constraints */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs text-white/60 uppercase tracking-wider">
              <AlertTriangle className="h-3 w-3 text-yellow-400" />
              Soft Constraints ({softConstraints.length})
            </div>
            {softConstraints.length === 0 ? (
              <div className="text-xs text-white/40 text-center py-2">
                No soft constraints
              </div>
            ) : (
              <div className="space-y-1">
                {softConstraints.map((c) => (
                  <div
                    key={c.constraint_id}
                    className="p-2 bg-yellow-500/10 border border-yellow-500/30 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-yellow-300">{c.name}</span>
                      {c.penalty_weight != null && (
                        <span className="text-white/40">
                          -{Math.round(c.penalty_weight * 100)}%
                        </span>
                      )}
                    </div>
                    {c.description && (
                      <div className="text-white/50 mt-0.5">{c.description}</div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Planning Horizon */}
          <div className="pt-2 border-t border-white/10 space-y-2">
            <div className="text-xs text-white/60 uppercase tracking-wider">
              Planning Parameters
            </div>
            <div className="grid grid-cols-3 gap-2 text-xs">
              <div className="p-2 bg-white/5 border border-white/10">
                <div className="text-white/40">Horizon</div>
                <div className="font-medium">{target.planning_horizon} steps</div>
              </div>
              <div className="p-2 bg-white/5 border border-white/10">
                <div className="text-white/40">Discount</div>
                <div className="font-medium">{target.discount_factor}</div>
              </div>
              <div className="p-2 bg-white/5 border border-white/10">
                <div className="text-white/40">Explore</div>
                <div className="font-medium">
                  {Math.round(target.exploration_rate * 100)}%
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

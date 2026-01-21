'use client';

/**
 * TEG Canvas Component - Graph View
 *
 * Force-directed/graph layout for TEG nodes using React Flow.
 * Reference: docs/TEG_UNIVERSE_MAP_EXECUTION.md Section 2.2.A
 */

import { useCallback, useMemo, useEffect } from 'react';
import {
  ReactFlow,
  type Node as FlowNode,
  type Edge as FlowEdge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
  MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import {
  CheckCircle,
  Clock,
  Activity,
  XCircle,
  Edit3,
  FileText,
  Sparkles,
  GitBranch,
  Zap,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { TEGCanvasProps, TEGNode, TEGNodeType, TEGNodeStatus } from './types';

// ============ Custom TEG Node Component ============

interface TEGFlowNodeData {
  tegNode: TEGNode;
  selected?: boolean;
  onSelect: () => void;
  // Index signature for React Flow compatibility
  [key: string]: unknown;
}

const statusConfig: Record<TEGNodeStatus, { icon: typeof CheckCircle; color: string; label: string }> = {
  DRAFT: { icon: Edit3, color: 'text-gray-400', label: 'DRAFT' },
  QUEUED: { icon: Clock, color: 'text-blue-400', label: 'QUEUED' },
  RUNNING: { icon: Activity, color: 'text-cyan-400 animate-pulse', label: 'RUNNING' },
  DONE: { icon: CheckCircle, color: 'text-green-400', label: 'DONE' },
  FAILED: { icon: XCircle, color: 'text-red-400', label: 'FAILED' },
};

const typeConfig: Record<TEGNodeType, { icon: typeof FileText; color: string; label: string; borderColor: string }> = {
  OUTCOME_VERIFIED: {
    icon: CheckCircle,
    color: 'text-cyan-400',
    label: 'VERIFIED',
    borderColor: 'border-cyan-500/60',
  },
  SCENARIO_DRAFT: {
    icon: Sparkles,
    color: 'text-purple-400',
    label: 'ESTIMATED',
    borderColor: 'border-purple-500/50 border-dashed',
  },
  EVIDENCE: {
    icon: FileText,
    color: 'text-amber-400',
    label: 'EVIDENCE',
    borderColor: 'border-amber-500/50',
  },
};

function TEGFlowNode({ data, selected }: { data: TEGFlowNodeData; selected?: boolean }) {
  const { tegNode, onSelect } = data;
  const status = statusConfig[tegNode.status];
  const type = typeConfig[tegNode.type];
  const StatusIcon = status.icon;
  const TypeIcon = type.icon;

  // Get probability for verified nodes
  const probability =
    tegNode.type === 'OUTCOME_VERIFIED'
      ? (tegNode.payload as { primary_outcome_probability?: number })?.primary_outcome_probability
      : tegNode.type === 'SCENARIO_DRAFT'
        ? (tegNode.payload as { estimated_delta?: number })?.estimated_delta
        : undefined;

  const isVerified = tegNode.type === 'OUTCOME_VERIFIED';
  const isDraft = tegNode.type === 'SCENARIO_DRAFT';

  return (
    <div
      onClick={onSelect}
      className={cn(
        'relative group cursor-pointer transition-all duration-200',
        selected && 'scale-105'
      )}
    >
      {/* Glow effect for verified nodes */}
      {isVerified && tegNode.status === 'DONE' && (
        <div className="absolute -inset-2 bg-cyan-500/20 blur-xl rounded-lg opacity-50" />
      )}

      {/* Main node card */}
      <div
        className={cn(
          'relative w-56 border-2 backdrop-blur-sm transition-all duration-200',
          type.borderColor,
          isVerified
            ? 'bg-gradient-to-br from-cyan-950/90 to-blue-950/90 shadow-cyan-500/20 shadow-lg'
            : isDraft
              ? 'bg-gradient-to-br from-purple-950/90 to-violet-950/90 shadow-purple-500/10 shadow-lg'
              : 'bg-gradient-to-br from-amber-950/90 to-orange-950/90 shadow-amber-500/10 shadow-lg',
          selected && 'ring-2 ring-white/50'
        )}
      >
        {/* Header strip */}
        <div
          className={cn(
            'px-3 py-1.5 flex items-center justify-between border-b',
            isVerified
              ? 'bg-cyan-500/10 border-cyan-500/30'
              : isDraft
                ? 'bg-purple-500/10 border-purple-500/30'
                : 'bg-amber-500/10 border-amber-500/30'
          )}
        >
          <div className="flex items-center gap-1.5">
            <TypeIcon className={cn('w-3 h-3', type.color)} />
            <span className={cn('text-[9px] font-mono uppercase font-semibold', type.color)}>
              {type.label}
            </span>
          </div>
          <div className="flex items-center gap-1">
            <StatusIcon className={cn('w-3 h-3', status.color)} />
            <span className={cn('text-[8px] font-mono', status.color)}>{status.label}</span>
          </div>
        </div>

        {/* Content */}
        <div className="p-3 space-y-2">
          <h3 className="text-sm font-medium text-white/90 line-clamp-2">{tegNode.title}</h3>

          {probability !== undefined && (
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono text-white/50">
                {isVerified ? 'Probability' : 'Est. Delta'}
              </span>
              <span
                className={cn(
                  'text-lg font-bold font-mono',
                  isVerified ? 'text-cyan-400' : 'text-purple-400'
                )}
              >
                {isVerified
                  ? `${(probability * 100).toFixed(1)}%`
                  : `${probability > 0 ? '+' : ''}${(probability * 100).toFixed(0)}%`}
              </span>
            </div>
          )}

          {tegNode.summary && (
            <p className="text-[10px] text-white/50 line-clamp-2">{tegNode.summary}</p>
          )}
        </div>

        {/* Connection handles */}
        <Handle type="target" position={Position.Top} className="w-2 h-2 !bg-cyan-500" />
        <Handle type="source" position={Position.Bottom} className="w-2 h-2 !bg-purple-500" />
      </div>
    </div>
  );
}

// Define custom node type for React Flow
type TEGFlowNodeType = FlowNode<TEGFlowNodeData>;

const nodeTypes = {
  tegNode: TEGFlowNode,
};

// ============ Main Canvas Component ============

export function TEGCanvas({
  nodes,
  edges,
  selectedNodeId,
  onNodeSelect,
  loading,
}: TEGCanvasProps) {
  // Convert TEG nodes to React Flow nodes
  const flowNodes = useMemo((): FlowNode[] => {
    return nodes.map((tegNode, index) => ({
      id: tegNode.node_id,
      type: 'tegNode',
      position: tegNode.position || { x: 200 + (index % 3) * 280, y: 100 + Math.floor(index / 3) * 200 },
      data: {
        tegNode,
        selected: tegNode.node_id === selectedNodeId,
        onSelect: () => onNodeSelect(tegNode.node_id),
      } satisfies TEGFlowNodeData,
      selected: tegNode.node_id === selectedNodeId,
    }));
  }, [nodes, selectedNodeId, onNodeSelect]);

  // Convert TEG edges to React Flow edges
  const flowEdges = useMemo((): FlowEdge[] => {
    return edges.map((edge) => {
      const edgeStyles: Record<string, { stroke: string; strokeDasharray?: string }> = {
        EXPANDS_TO: { stroke: '#a855f7', strokeDasharray: '5,5' }, // Purple dashed
        RUNS_TO: { stroke: '#22c55e' }, // Green solid
        FORKS_FROM: { stroke: '#06b6d4' }, // Cyan solid
        SUPPORTS: { stroke: '#f59e0b', strokeDasharray: '3,3' }, // Amber dashed
        CONFLICTS: { stroke: '#ef4444', strokeDasharray: '3,3' }, // Red dashed
      };

      const style = edgeStyles[edge.relation] || { stroke: '#666' };

      return {
        id: edge.edge_id,
        source: edge.from_node_id,
        target: edge.to_node_id,
        type: 'smoothstep',
        animated: edge.relation === 'RUNS_TO',
        style,
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: style.stroke,
        },
        label: edge.relation,
        labelStyle: { fill: style.stroke, fontSize: 8 },
        labelBgStyle: { fill: '#000', fillOpacity: 0.8 },
      };
    });
  }, [edges]);

  const [rfNodes, setNodes, onNodesChange] = useNodesState(flowNodes);
  const [rfEdges, setEdges, onEdgesChange] = useEdgesState(flowEdges);

  // Sync with external nodes/edges
  useEffect(() => {
    setNodes(flowNodes);
    setEdges(flowEdges);
  }, [flowNodes, flowEdges, setNodes, setEdges]);

  const onPaneClick = useCallback(() => {
    onNodeSelect(null);
  }, [onNodeSelect]);

  if (loading) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-black/50">
        <div className="text-center">
          <Activity className="w-8 h-8 text-cyan-500 animate-spin mx-auto mb-2" />
          <p className="text-white/60 font-mono text-sm">Loading TEG...</p>
        </div>
      </div>
    );
  }

  if (nodes.length === 0) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-black/50">
        <div className="text-center max-w-md">
          <GitBranch className="w-12 h-12 text-cyan-500/40 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-white/80 mb-2">No Scenarios Yet</h3>
          <p className="text-sm text-white/50">
            Run a baseline simulation first, then expand to explore what-if scenarios.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full">
      <ReactFlow
        nodes={rfNodes}
        edges={rfEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onPaneClick={onPaneClick}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        className="bg-black"
      >
        <Background color="#1e293b" gap={32} size={1} />
        <Controls className="bg-black/80 border border-white/10" />
        <MiniMap
          nodeColor={(node) => {
            const data = node.data as TEGFlowNodeData | undefined;
            if (data?.tegNode?.type === 'OUTCOME_VERIFIED') return '#06b6d4';
            if (data?.tegNode?.type === 'SCENARIO_DRAFT') return '#a855f7';
            return '#f59e0b';
          }}
          maskColor="rgba(0, 0, 0, 0.8)"
          className="bg-black/80 border border-white/10"
        />
      </ReactFlow>
    </div>
  );
}

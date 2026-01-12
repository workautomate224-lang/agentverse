'use client';

/**
 * Universe Map Page
 * Infinite canvas with draggable nodes, fork actions, and sci-fi UI
 * Uses React Flow for professional graph editing experience
 */

import { useState, useCallback, useMemo, useEffect } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import {
  ReactFlow,
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  NodeTypes,
  Panel,
  useReactFlow,
  ReactFlowProvider,
  Handle,
  Position,
  MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

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
  Globe,
  ArrowLeft,
  ArrowRight,
  Terminal,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Filter,
  Download,
  RefreshCw,
  Loader2,
  AlertCircle,
  GitBranch,
  GitFork,
  Play,
  Pause,
  CheckCircle,
  Clock,
  XCircle,
  Activity,
  Layers,
  Eye,
  Edit3,
  Copy,
  TrendingUp,
  BarChart3,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  useUniverseMapFull,
  useNodes,
  useRuns,
  useCreateRun,
  useStartRun,
} from '@/hooks/useApi';
import type { SpecNode, NodeSummary, RunSummary } from '@/lib/api';

// ============ Types ============

interface UniverseNode {
  id: string;
  label: string;
  probability: number;
  confidence: 'high' | 'medium' | 'low';
  status: 'draft' | 'queued' | 'running' | 'completed' | 'failed';
  isBaseline: boolean;
  runCount: number;
  parentId: string | null;
  createdAt: string;
  outcome?: string;
}

interface NodePosition {
  x: number;
  y: number;
}

// Storage key for node positions
const getStorageKey = (projectId: string) => `universe-map-positions-${projectId}`;

// ============ Custom Node Component ============

interface SciFiNodeData {
  label: string;
  probability: number;
  confidence: 'high' | 'medium' | 'low';
  status: 'draft' | 'queued' | 'running' | 'completed' | 'failed';
  isBaseline: boolean;
  runCount: number;
  outcome?: string;
  onFork: () => void;
  onInspect: () => void;
  selected?: boolean;
}

function SciFiNode({ data, selected }: { data: SciFiNodeData; selected?: boolean }) {
  const confidenceColors = {
    high: { bg: 'bg-green-500/20', border: 'border-green-500/60', text: 'text-green-400' },
    medium: { bg: 'bg-yellow-500/20', border: 'border-yellow-500/60', text: 'text-yellow-400' },
    low: { bg: 'bg-red-500/20', border: 'border-red-500/60', text: 'text-red-400' },
  };

  const statusConfig = {
    draft: { icon: Edit3, color: 'text-gray-400', label: 'DRAFT' },
    queued: { icon: Clock, color: 'text-blue-400', label: 'QUEUED' },
    running: { icon: Activity, color: 'text-cyan-400 animate-pulse', label: 'RUNNING' },
    completed: { icon: CheckCircle, color: 'text-green-400', label: 'COMPLETED' },
    failed: { icon: XCircle, color: 'text-red-400', label: 'FAILED' },
  };

  const conf = confidenceColors[data.confidence];
  const stat = statusConfig[data.status];
  const StatusIcon = stat.icon;

  return (
    <div
      className={cn(
        'relative group transition-all duration-200',
        selected && 'scale-105'
      )}
    >
      {/* Glow effect for baseline */}
      {data.isBaseline && (
        <div className="absolute -inset-2 bg-cyan-500/20 blur-xl rounded-lg opacity-50" />
      )}

      {/* Main node card */}
      <div
        className={cn(
          'relative w-56 border-2 backdrop-blur-sm transition-all duration-200',
          data.isBaseline
            ? 'bg-gradient-to-br from-cyan-950/90 to-blue-950/90 border-cyan-500/70 shadow-cyan-500/20 shadow-lg'
            : 'bg-gradient-to-br from-purple-950/90 to-violet-950/90 border-purple-500/50 shadow-purple-500/10 shadow-lg',
          selected && 'ring-2 ring-white/50'
        )}
      >
        {/* Header strip */}
        <div
          className={cn(
            'px-3 py-1.5 flex items-center justify-between border-b',
            data.isBaseline ? 'bg-cyan-500/10 border-cyan-500/30' : 'bg-purple-500/10 border-purple-500/30'
          )}
        >
          <div className="flex items-center gap-1.5">
            <GitBranch className={cn('w-3 h-3', data.isBaseline ? 'text-cyan-400' : 'text-purple-400')} />
            <span className={cn('text-[9px] font-mono uppercase font-semibold', data.isBaseline ? 'text-cyan-400' : 'text-purple-400')}>
              {data.isBaseline ? 'BASELINE' : 'FORK'}
            </span>
          </div>
          <div className="flex items-center gap-1">
            <StatusIcon className={cn('w-3 h-3', stat.color)} />
            <span className={cn('text-[8px] font-mono', stat.color)}>{stat.label}</span>
          </div>
        </div>

        {/* Content */}
        <div className="p-3 space-y-2.5">
          {/* Title */}
          <div className="font-mono text-sm text-white font-medium leading-tight truncate">
            {data.label}
          </div>

          {/* Metrics row */}
          <div className="flex items-center justify-between gap-2">
            {/* Probability */}
            <div className="flex-1">
              <div className="text-[8px] font-mono text-white/40 uppercase mb-0.5">Probability</div>
              <div className="flex items-center gap-1">
                <div className="flex-1 h-1.5 bg-white/10 overflow-hidden">
                  <div
                    className={cn(
                      'h-full transition-all',
                      data.probability >= 0.7 ? 'bg-green-500' :
                      data.probability >= 0.4 ? 'bg-yellow-500' : 'bg-red-500'
                    )}
                    style={{ width: `${data.probability * 100}%` }}
                  />
                </div>
                <span className="text-xs font-mono text-white/80 font-semibold w-12 text-right">
                  {data.status === 'draft' ? '—' : `${(data.probability * 100).toFixed(1)}%`}
                </span>
              </div>
            </div>
          </div>

          {/* Confidence + Run count */}
          <div className="flex items-center justify-between">
            <div className={cn('px-1.5 py-0.5 text-[8px] font-mono uppercase font-semibold', conf.bg, conf.text)}>
              {data.confidence.toUpperCase()} CONF
            </div>
            <div className="flex items-center gap-1 text-[10px] font-mono text-white/50">
              <Layers className="w-3 h-3" />
              <span>{data.runCount} runs</span>
            </div>
          </div>

          {/* Outcome preview */}
          {data.outcome && data.status === 'completed' && (
            <div className="text-[10px] font-mono text-white/50 truncate border-t border-white/10 pt-2 mt-2">
              {data.outcome}
            </div>
          )}
        </div>

        {/* Hover actions */}
        <div className={cn(
          'absolute -bottom-10 left-0 right-0 flex items-center justify-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity',
        )}>
          <button
            onClick={(e) => { e.stopPropagation(); data.onFork(); }}
            className="px-2 py-1 bg-purple-500/80 hover:bg-purple-500 text-white text-[10px] font-mono flex items-center gap-1 transition-colors"
          >
            <GitFork className="w-3 h-3" />
            FORK
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); data.onInspect(); }}
            className="px-2 py-1 bg-white/10 hover:bg-white/20 text-white/80 text-[10px] font-mono flex items-center gap-1 transition-colors"
          >
            <Eye className="w-3 h-3" />
            INSPECT
          </button>
        </div>
      </div>

      {/* Connection handles */}
      <Handle
        type="target"
        position={Position.Top}
        className={cn(
          'w-3 h-3 border-2 !bg-black',
          data.isBaseline ? '!border-cyan-500' : '!border-purple-500'
        )}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        className={cn(
          'w-3 h-3 border-2 !bg-black',
          data.isBaseline ? '!border-cyan-500' : '!border-purple-500'
        )}
      />
    </div>
  );
}

const nodeTypes: NodeTypes = {
  sciFiNode: SciFiNode,
};

// ============ Fork Modal ============

function ForkModal({
  open,
  onClose,
  parentNode,
  onFork,
}: {
  open: boolean;
  onClose: () => void;
  parentNode: UniverseNode | null;
  onFork: (name: string, description: string, variables: string) => void;
}) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [variables, setVariables] = useState('');

  const handleSubmit = () => {
    onFork(name || `Fork of ${parentNode?.label || 'Node'}`, description, variables);
    setName('');
    setDescription('');
    setVariables('');
  };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="bg-black border border-purple-500/30 max-w-md">
        <DialogHeader>
          <DialogTitle className="text-white font-mono flex items-center gap-2">
            <GitFork className="w-5 h-5 text-purple-400" />
            Fork Universe
          </DialogTitle>
          <DialogDescription className="text-white/50 font-mono text-xs">
            Create a divergent simulation branch from "{parentNode?.label}"
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div>
            <label className="block text-xs font-mono text-white/60 mb-2">Fork Name</label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Tariff Increase Scenario"
              className="font-mono text-sm"
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-white/60 mb-2">Description</label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What changes in this fork?"
              className="font-mono text-sm min-h-[80px]"
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-white/60 mb-2">
              Variable Overrides <span className="text-white/30">(JSON)</span>
            </label>
            <Textarea
              value={variables}
              onChange={(e) => setVariables(e.target.value)}
              placeholder='{"tariff_rate": 0.25, "inflation": 0.05}'
              className="font-mono text-xs min-h-[60px]"
            />
          </div>

          <div className="p-3 bg-yellow-500/10 border border-yellow-500/30 text-yellow-400 text-xs font-mono">
            <AlertCircle className="w-3 h-3 inline mr-1" />
            Fork API endpoint coming soon. Node will be created as Draft.
          </div>
        </div>

        <DialogFooter className="flex justify-end gap-2">
          <Button variant="ghost" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={handleSubmit}
            className="bg-purple-500 hover:bg-purple-600 text-white"
          >
            <GitFork className="w-3 h-3 mr-2" />
            Create Fork
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ============ Inspector Panel ============

function InspectorPanel({
  node,
  onClose,
  projectId,
  onFork,
}: {
  node: UniverseNode | null;
  onClose: () => void;
  projectId: string;
  onFork: (node: UniverseNode) => void;
}) {
  if (!node) return null;

  const statusConfig = {
    draft: { color: 'text-gray-400 bg-gray-400/10', label: 'Draft' },
    queued: { color: 'text-blue-400 bg-blue-400/10', label: 'Queued' },
    running: { color: 'text-cyan-400 bg-cyan-400/10', label: 'Running' },
    completed: { color: 'text-green-400 bg-green-400/10', label: 'Completed' },
    failed: { color: 'text-red-400 bg-red-400/10', label: 'Failed' },
  };

  const stat = statusConfig[node.status];

  return (
    <div className="absolute right-0 top-0 bottom-0 w-80 bg-black/95 border-l border-white/10 z-50 overflow-y-auto">
      {/* Header */}
      <div className="p-4 border-b border-white/10 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <GitBranch className={cn('w-4 h-4', node.isBaseline ? 'text-cyan-400' : 'text-purple-400')} />
          <span className="font-mono text-sm text-white font-semibold">Node Inspector</span>
        </div>
        <button onClick={onClose} className="text-white/40 hover:text-white/80 transition-colors">
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Content */}
      <div className="p-4 space-y-4">
        {/* Title */}
        <div>
          <div className="text-[10px] font-mono text-white/40 uppercase mb-1">Name</div>
          <div className="font-mono text-white text-sm">{node.label}</div>
        </div>

        {/* Type */}
        <div>
          <div className="text-[10px] font-mono text-white/40 uppercase mb-1">Type</div>
          <span className={cn(
            'inline-flex items-center px-2 py-0.5 text-xs font-mono',
            node.isBaseline ? 'bg-cyan-500/20 text-cyan-400' : 'bg-purple-500/20 text-purple-400'
          )}>
            {node.isBaseline ? 'BASELINE ROOT' : 'FORK'}
          </span>
        </div>

        {/* Status */}
        <div>
          <div className="text-[10px] font-mono text-white/40 uppercase mb-1">Status</div>
          <span className={cn('inline-flex items-center px-2 py-0.5 text-xs font-mono', stat.color)}>
            {stat.label}
          </span>
        </div>

        {/* Probability */}
        <div>
          <div className="text-[10px] font-mono text-white/40 uppercase mb-1">Probability</div>
          <div className="flex items-center gap-2">
            <div className="flex-1 h-2 bg-white/10">
              <div
                className={cn(
                  'h-full',
                  node.probability >= 0.7 ? 'bg-green-500' :
                  node.probability >= 0.4 ? 'bg-yellow-500' : 'bg-red-500'
                )}
                style={{ width: `${node.probability * 100}%` }}
              />
            </div>
            <span className="text-sm font-mono text-white font-semibold">
              {node.status === 'draft' ? 'Pending' : `${(node.probability * 100).toFixed(1)}%`}
            </span>
          </div>
        </div>

        {/* Confidence */}
        <div>
          <div className="text-[10px] font-mono text-white/40 uppercase mb-1">Confidence</div>
          <span className={cn(
            'inline-flex items-center px-2 py-0.5 text-xs font-mono uppercase',
            node.confidence === 'high' ? 'bg-green-500/20 text-green-400' :
            node.confidence === 'medium' ? 'bg-yellow-500/20 text-yellow-400' :
            'bg-red-500/20 text-red-400'
          )}>
            {node.confidence}
          </span>
        </div>

        {/* Run count */}
        <div>
          <div className="text-[10px] font-mono text-white/40 uppercase mb-1">Simulation Runs</div>
          <div className="font-mono text-white text-sm">{node.runCount}</div>
        </div>

        {/* Created */}
        <div>
          <div className="text-[10px] font-mono text-white/40 uppercase mb-1">Created</div>
          <div className="font-mono text-white/60 text-xs">
            {new Date(node.createdAt).toLocaleString()}
          </div>
        </div>

        {/* Node ID */}
        <div>
          <div className="text-[10px] font-mono text-white/40 uppercase mb-1">Node ID</div>
          <div className="font-mono text-white/40 text-[10px] break-all">{node.id}</div>
        </div>

        {/* Outcome */}
        {node.outcome && (
          <div>
            <div className="text-[10px] font-mono text-white/40 uppercase mb-1">Outcome</div>
            <div className="p-2 bg-white/5 border border-white/10 text-xs font-mono text-white/60">
              {node.outcome}
            </div>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="p-4 border-t border-white/10 space-y-2">
        <Button
          size="sm"
          onClick={() => onFork(node)}
          className="w-full bg-purple-500 hover:bg-purple-600 text-white text-xs font-mono"
        >
          <GitFork className="w-3 h-3 mr-2" />
          Fork This Universe
        </Button>

        {node.status === 'draft' && (
          <Button
            size="sm"
            variant="outline"
            className="w-full text-xs font-mono"
            disabled
          >
            <Play className="w-3 h-3 mr-2" />
            Run Simulation (Coming Soon)
          </Button>
        )}

        {node.status === 'completed' && (
          <>
            <Link href={`/p/${projectId}/results?node=${node.id}`} className="block">
              <Button size="sm" variant="outline" className="w-full text-xs font-mono">
                <TrendingUp className="w-3 h-3 mr-2" />
                View Results
              </Button>
            </Link>
            <Link href={`/p/${projectId}/replay?node=${node.id}`} className="block">
              <Button size="sm" variant="outline" className="w-full text-xs font-mono">
                <Eye className="w-3 h-3 mr-2" />
                Open in Replay
              </Button>
            </Link>
          </>
        )}
      </div>
    </div>
  );
}

// ============ Main Component ============

function UniverseMapCanvas() {
  const params = useParams();
  const projectId = params.projectId as string;
  const { fitView, zoomIn, zoomOut } = useReactFlow();

  // State
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [universeNodes, setUniverseNodes] = useState<Map<string, UniverseNode>>(new Map());
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [forkModalOpen, setForkModalOpen] = useState(false);
  const [forkingNode, setForkingNode] = useState<UniverseNode | null>(null);
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [filterOpen, setFilterOpen] = useState(false);
  const [exportModalOpen, setExportModalOpen] = useState(false);

  // API hooks
  const { data: mapData, isLoading: mapLoading, error: mapError, refetch: refetchMap } = useUniverseMapFull(projectId);
  const { data: nodesList, isLoading: nodesLoading, refetch: refetchNodes } = useNodes({ project_id: projectId, limit: 100 });
  const { data: runs, refetch: refetchRuns } = useRuns({ project_id: projectId });

  const isLoading = mapLoading || nodesLoading;

  // Load saved positions from localStorage
  const loadPositions = useCallback((): Record<string, NodePosition> => {
    try {
      const saved = localStorage.getItem(getStorageKey(projectId));
      return saved ? JSON.parse(saved) : {};
    } catch {
      return {};
    }
  }, [projectId]);

  // Save positions to localStorage
  const savePositions = useCallback((positions: Record<string, NodePosition>) => {
    try {
      localStorage.setItem(getStorageKey(projectId), JSON.stringify(positions));
    } catch {
      // Ignore storage errors
    }
  }, [projectId]);

  // Build universe nodes from API data
  const buildUniverseFromData = useCallback(() => {
    const savedPositions = loadPositions();
    const newUniverseNodes = new Map<string, UniverseNode>();
    const flowNodes: Node[] = [];
    const flowEdges: Edge[] = [];

    // Get all runs - they will be associated with nodes via node_id
    // We'll use nodesList/mapData to determine baseline vs fork hierarchy
    const allRuns: RunSummary[] = runs || [];

    // Create one baseline root node (consolidate all runs into summary)
    const baselineId = 'baseline-root';
    const calcProgress = (r: RunSummary) => {
      const current = r.timing?.current_tick || 0;
      const total = r.timing?.total_ticks || 100;
      return total > 0 ? (current / total) : 0;
    };
    const baselineNode: UniverseNode = {
      id: baselineId,
      label: 'Baseline Universe',
      probability: allRuns.length > 0 ?
        allRuns.reduce((sum, r) => sum + calcProgress(r), 0) / allRuns.length : 0.5,
      confidence: allRuns.some(r => r.status === 'succeeded') ? 'high' : 'medium',
      status: allRuns.some(r => r.status === 'running') ? 'running' :
              allRuns.some(r => r.status === 'succeeded') ? 'completed' :
              allRuns.some(r => r.status === 'queued') ? 'queued' :
              allRuns.length === 0 ? 'draft' : 'completed',
      isBaseline: true,
      runCount: allRuns.length,
      parentId: null,
      createdAt: allRuns[0]?.created_at || new Date().toISOString(),
      outcome: allRuns.find(r => r.status === 'succeeded')?.status,
    };
    newUniverseNodes.set(baselineId, baselineNode);

    // Position for baseline
    const baselinePos = savedPositions[baselineId] || { x: 400, y: 50 };
    flowNodes.push({
      id: baselineId,
      type: 'sciFiNode',
      position: baselinePos,
      data: {
        ...baselineNode,
        onFork: () => {
          setForkingNode(baselineNode);
          setForkModalOpen(true);
        },
        onInspect: () => {
          setSelectedNodeId(baselineId);
          setInspectorOpen(true);
        },
      },
    });

    // Process API nodes if available
    const apiNodes = mapData?.nodes || nodesList || [];
    let yOffset = 200;

    apiNodes.forEach((apiNode, index) => {
      // Skip if it looks like a baseline (depth 0 or is_baseline)
      const isBaseline = ('depth' in apiNode && (apiNode as SpecNode).depth === 0) ||
                        ('is_baseline' in apiNode && (apiNode as NodeSummary).is_baseline);

      if (isBaseline) {
        // Update baseline with API data
        const existing = newUniverseNodes.get(baselineId)!;
        existing.probability = apiNode.probability;
        if ('confidence' in apiNode && (apiNode as SpecNode).confidence) {
          existing.confidence = ((apiNode as SpecNode).confidence?.level as 'high' | 'medium' | 'low') || 'medium';
        }
        if ('confidence_level' in apiNode) {
          existing.confidence = ((apiNode as NodeSummary).confidence_level as 'high' | 'medium' | 'low') || 'medium';
        }
        if (apiNode.label) {
          existing.label = apiNode.label;
        }
        return;
      }

      // It's a fork node
      const nodeId = apiNode.node_id;
      const forkNode: UniverseNode = {
        id: nodeId,
        label: apiNode.label || `Fork ${index + 1}`,
        probability: apiNode.probability,
        confidence: ('confidence_level' in apiNode ? (apiNode as NodeSummary).confidence_level :
                    'confidence' in apiNode ? (apiNode as SpecNode).confidence?.level : 'medium') as 'high' | 'medium' | 'low',
        status: ('has_outcome' in apiNode && (apiNode as NodeSummary).has_outcome) ? 'completed' : 'draft',
        isBaseline: false,
        runCount: ('child_count' in apiNode ? (apiNode as NodeSummary).child_count : 0) || 1,
        parentId: apiNode.parent_node_id || baselineId,
        createdAt: ('created_at' in apiNode ? (apiNode as NodeSummary).created_at : new Date().toISOString()),
        outcome: ('aggregated_outcome' in apiNode ? (apiNode as SpecNode).aggregated_outcome?.primary_outcome : undefined),
      };

      newUniverseNodes.set(nodeId, forkNode);

      // Calculate position
      const savedPos = savedPositions[nodeId];
      const xOffset = (index % 3) * 280 + 100;
      const pos = savedPos || { x: xOffset, y: yOffset };
      if (!savedPos && index > 0 && index % 3 === 0) {
        yOffset += 200;
      }

      flowNodes.push({
        id: nodeId,
        type: 'sciFiNode',
        position: pos,
        data: {
          ...forkNode,
          onFork: () => {
            setForkingNode(forkNode);
            setForkModalOpen(true);
          },
          onInspect: () => {
            setSelectedNodeId(nodeId);
            setInspectorOpen(true);
          },
        },
      });

      // Create edge to parent
      const parentId = forkNode.parentId || baselineId;
      flowEdges.push({
        id: `${parentId}-${nodeId}`,
        source: parentId,
        target: nodeId,
        type: 'smoothstep',
        animated: forkNode.status === 'running',
        style: { stroke: forkNode.isBaseline ? '#06b6d4' : '#a855f7', strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#a855f7' },
      });
    });

    setUniverseNodes(newUniverseNodes);
    setNodes(flowNodes);
    setEdges(flowEdges);
  }, [mapData, nodesList, runs, loadPositions, setNodes, setEdges]);

  // Rebuild nodes when data changes
  useEffect(() => {
    if (!isLoading) {
      buildUniverseFromData();
    }
  }, [isLoading, buildUniverseFromData]);

  // Save positions on node drag
  const handleNodesChange = useCallback((changes: Parameters<typeof onNodesChange>[0]) => {
    onNodesChange(changes);

    // Save positions after drag
    const positionChanges = changes.filter(
      (c) => c.type === 'position' && 'position' in c && c.position
    );
    if (positionChanges.length > 0) {
      const currentPositions = loadPositions();
      positionChanges.forEach((change) => {
        if (change.type === 'position' && 'position' in change && change.position) {
          currentPositions[change.id] = change.position;
        }
      });
      savePositions(currentPositions);
    }
  }, [onNodesChange, loadPositions, savePositions]);

  // Handle fork creation
  const handleFork = useCallback((name: string, description: string, variables: string) => {
    if (!forkingNode) return;

    // Create new fork node locally (Draft status since API may not be available)
    const newId = `fork-${Date.now()}`;
    const newNode: UniverseNode = {
      id: newId,
      label: name,
      probability: 0.5,
      confidence: 'low',
      status: 'draft',
      isBaseline: false,
      runCount: 0,
      parentId: forkingNode.id,
      createdAt: new Date().toISOString(),
    };

    // Calculate position relative to parent
    const parentFlowNode = nodes.find((n) => n.id === forkingNode.id);
    const childCount = edges.filter((e) => e.source === forkingNode.id).length;
    const xOffset = (childCount % 3 - 1) * 280;
    const yOffset = 200;

    const newFlowNode: Node = {
      id: newId,
      type: 'sciFiNode',
      position: {
        x: (parentFlowNode?.position.x || 400) + xOffset,
        y: (parentFlowNode?.position.y || 50) + yOffset,
      },
      data: {
        ...newNode,
        onFork: () => {
          setForkingNode(newNode);
          setForkModalOpen(true);
        },
        onInspect: () => {
          setSelectedNodeId(newId);
          setInspectorOpen(true);
        },
      },
    };

    const newEdge: Edge = {
      id: `${forkingNode.id}-${newId}`,
      source: forkingNode.id,
      target: newId,
      type: 'smoothstep',
      animated: false,
      style: { stroke: '#a855f7', strokeWidth: 2 },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#a855f7' },
    };

    setNodes((nds) => [...nds, newFlowNode]);
    setEdges((eds) => [...eds, newEdge]);
    setUniverseNodes((prev) => new Map(prev).set(newId, newNode));

    // Save new position
    const positions = loadPositions();
    positions[newId] = newFlowNode.position;
    savePositions(positions);

    setForkModalOpen(false);
    setForkingNode(null);
  }, [forkingNode, nodes, edges, setNodes, setEdges, loadPositions, savePositions]);

  // Refresh data
  const handleRefresh = useCallback(() => {
    refetchMap();
    refetchNodes();
    refetchRuns();
  }, [refetchMap, refetchNodes, refetchRuns]);

  // Export
  const handleExport = useCallback((format: 'json' | 'csv') => {
    const data = Array.from(universeNodes.values());
    let content: string;
    let filename: string;
    let mimeType: string;

    if (format === 'json') {
      content = JSON.stringify({ project_id: projectId, nodes: data, exported_at: new Date().toISOString() }, null, 2);
      filename = `universe-map-${projectId}-${Date.now()}.json`;
      mimeType = 'application/json';
    } else {
      const headers = ['id', 'label', 'probability', 'confidence', 'status', 'isBaseline', 'runCount', 'parentId'];
      const rows = data.map((n) => [
        n.id, n.label, n.probability.toString(), n.confidence, n.status,
        n.isBaseline.toString(), n.runCount.toString(), n.parentId || '',
      ]);
      content = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
      filename = `universe-map-${projectId}-${Date.now()}.csv`;
      mimeType = 'text/csv';
    }

    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
    setExportModalOpen(false);
  }, [universeNodes, projectId]);

  const selectedNode = selectedNodeId ? universeNodes.get(selectedNodeId) : null;

  return (
    <div className="h-screen bg-black flex flex-col">
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
              <Globe className="w-4 h-4 text-blue-400" />
              <span className="text-xs font-mono text-white/40 uppercase">Universe Map</span>
            </div>
            <h1 className="text-xl font-mono font-bold text-white">Simulation Universe</h1>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="secondary" size="sm" className="text-xs" onClick={() => zoomIn()}>
              <ZoomIn className="w-3 h-3 mr-1" />
              ZOOM
            </Button>
            <Button variant="secondary" size="sm" className="text-xs" onClick={() => zoomOut()}>
              <ZoomOut className="w-3 h-3 mr-1" />
              ZOOM
            </Button>
            <Button variant="secondary" size="sm" className="text-xs" onClick={() => fitView({ padding: 0.3 })}>
              <Maximize2 className="w-3 h-3 mr-1" />
              FIT
            </Button>
            <Button variant="outline" size="sm" className="text-xs" onClick={handleRefresh} disabled={isLoading}>
              <RefreshCw className={cn('w-3 h-3 mr-1', isLoading && 'animate-spin')} />
              REFRESH
            </Button>
            <Button variant="outline" size="sm" className="text-xs" onClick={() => setExportModalOpen(true)}>
              <Download className="w-3 h-3 mr-1" />
              EXPORT
            </Button>
          </div>
        </div>
      </div>

      {/* Canvas */}
      <div className="flex-1 relative">
        {/* Loading overlay */}
        {isLoading && (
          <div className="absolute inset-0 bg-black/80 z-50 flex items-center justify-center">
            <div className="text-center">
              <Loader2 className="w-8 h-8 text-cyan-400 animate-spin mx-auto mb-2" />
              <p className="text-sm font-mono text-white/60">Loading universe...</p>
            </div>
          </div>
        )}

        {/* Warning banner if API error */}
        {mapError && (
          <div className="absolute top-4 left-4 right-4 z-40 p-3 bg-yellow-500/10 border border-yellow-500/30 text-yellow-400 text-xs font-mono flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>Universe Map endpoint unavailable. Showing derived graph from runs.</span>
          </div>
        )}

        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={handleNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.3 }}
          minZoom={0.1}
          maxZoom={2}
          className="bg-black"
          defaultEdgeOptions={{
            type: 'smoothstep',
            style: { stroke: '#a855f7', strokeWidth: 2 },
          }}
        >
          <Background
            gap={40}
            size={1}
            color="#ffffff10"
          />
          <Controls
            showInteractive={false}
            className="!bg-black/80 !border-white/20"
          />
          <MiniMap
            nodeColor={(node) => {
              const data = node.data as Record<string, unknown>;
              return data?.isBaseline ? '#06b6d4' : '#a855f7';
            }}
            maskColor="#00000080"
            className="!bg-black/80 !border-white/20"
          />

          {/* Legend panel */}
          <Panel position="bottom-left" className="m-4">
            <div className="bg-black/90 border border-white/10 p-3 space-y-2">
              <div className="text-[10px] font-mono text-white/40 uppercase">Legend</div>
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-cyan-500" />
                  <span className="text-xs font-mono text-white/60">Baseline Root</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-purple-500" />
                  <span className="text-xs font-mono text-white/60">Fork</span>
                </div>
                <div className="flex items-center gap-2">
                  <Activity className="w-3 h-3 text-cyan-400 animate-pulse" />
                  <span className="text-xs font-mono text-white/60">Running</span>
                </div>
              </div>
            </div>
          </Panel>

          {/* Stats panel */}
          <Panel position="top-right" className="m-4">
            <div className="bg-black/90 border border-white/10 p-3">
              <div className="text-[10px] font-mono text-white/40 uppercase mb-2">Universe Stats</div>
              <div className="space-y-1 text-xs font-mono text-white/60">
                <div className="flex justify-between gap-4">
                  <span>Total Nodes</span>
                  <span className="text-white">{universeNodes.size}</span>
                </div>
                <div className="flex justify-between gap-4">
                  <span>Forks</span>
                  <span className="text-white">{Array.from(universeNodes.values()).filter(n => !n.isBaseline).length}</span>
                </div>
                <div className="flex justify-between gap-4">
                  <span>Completed</span>
                  <span className="text-green-400">
                    {Array.from(universeNodes.values()).filter(n => n.status === 'completed').length}
                  </span>
                </div>
              </div>
            </div>
          </Panel>
        </ReactFlow>

        {/* Inspector Panel */}
        {inspectorOpen && (
          <InspectorPanel
            node={selectedNode || null}
            onClose={() => {
              setInspectorOpen(false);
              setSelectedNodeId(null);
            }}
            projectId={projectId}
            onFork={(node) => {
              setForkingNode(node);
              setForkModalOpen(true);
            }}
          />
        )}
      </div>

      {/* Footer nav */}
      <div className="p-4 border-t border-white/10 flex items-center justify-between">
        <Link href={`/p/${projectId}/run-center`}>
          <Button variant="outline" size="sm" className="text-xs font-mono">
            <ArrowLeft className="w-3 h-3 mr-2" />
            Run Center
          </Button>
        </Link>
        <div className="flex items-center gap-1">
          <Terminal className="w-3 h-3 text-white/30" />
          <span className="text-[10px] font-mono text-white/30">UNIVERSE MAP v2.0</span>
        </div>
        <Link href={`/p/${projectId}/replay`}>
          <Button size="sm" className="text-xs font-mono bg-cyan-500 hover:bg-cyan-600">
            Replay
            <ArrowRight className="w-3 h-3 ml-2" />
          </Button>
        </Link>
      </div>

      {/* Fork Modal */}
      <ForkModal
        open={forkModalOpen}
        onClose={() => {
          setForkModalOpen(false);
          setForkingNode(null);
        }}
        parentNode={forkingNode}
        onFork={handleFork}
      />

      {/* Export Modal */}
      <Dialog open={exportModalOpen} onOpenChange={setExportModalOpen}>
        <DialogContent className="bg-black border border-white/10 max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-white font-mono flex items-center gap-2">
              <Download className="w-5 h-5 text-cyan-400" />
              Export Universe
            </DialogTitle>
            <DialogDescription className="text-white/50 font-mono text-xs">
              Export {universeNodes.size} nodes
            </DialogDescription>
          </DialogHeader>
          <div className="flex gap-2 py-4">
            <Button
              onClick={() => handleExport('json')}
              className="flex-1 bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/20"
            >
              JSON
            </Button>
            <Button
              onClick={() => handleExport('csv')}
              className="flex-1 bg-white/5 border border-white/10 text-white/60 hover:bg-white/10"
            >
              CSV
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// Wrap with provider
export default function UniverseMapPage() {
  return (
    <ReactFlowProvider>
      <UniverseMapCanvas />
    </ReactFlowProvider>
  );
}

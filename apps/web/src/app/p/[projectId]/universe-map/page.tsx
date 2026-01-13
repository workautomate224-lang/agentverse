'use client';

/**
 * Universe Map Page
 * Infinite canvas with draggable nodes, fork actions, and sci-fi UI
 * Uses React Flow for professional graph editing experience
 */

import { useState, useCallback, useMemo, useEffect, useRef, Suspense } from 'react';
import { useParams, useSearchParams } from 'next/navigation';
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
  Trash2,
  Sparkles,
  Zap,
  FileText,
  Map as MapIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  useUniverseMap,
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
  depth: number; // Tree depth for hierarchical layout
  forkType: 'ai' | 'manual' | 'baseline'; // Type of fork
  childCount: number; // Number of direct children
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
  depth: number;
  forkType: 'ai' | 'manual' | 'baseline';
  childCount: number;
  onFork: () => void;
  onAiFork: () => void;
  onDelete: () => void;
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
              {data.isBaseline ? 'BASELINE' : data.forkType === 'ai' ? 'AI FORK' : 'MANUAL'}
            </span>
            {/* Fork type indicator */}
            {!data.isBaseline && data.forkType === 'ai' && (
              <div className="px-1 py-0.5 bg-emerald-500/20 text-[7px] font-mono text-emerald-400 uppercase">
                AUTO
              </div>
            )}
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

          {/* Confidence + Run/Child count */}
          <div className="flex items-center justify-between">
            <div className={cn('px-1.5 py-0.5 text-[8px] font-mono uppercase font-semibold', conf.bg, conf.text)}>
              {data.confidence.toUpperCase()} CONF
            </div>
            <div className="flex items-center gap-2 text-[10px] font-mono text-white/50">
              <div className="flex items-center gap-1">
                <Layers className="w-3 h-3" />
                <span>{data.runCount}</span>
              </div>
              {data.childCount > 0 && (
                <div className="flex items-center gap-1 text-purple-400">
                  <GitFork className="w-3 h-3" />
                  <span>{data.childCount}</span>
                </div>
              )}
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
            title="Create manual fork"
          >
            <GitFork className="w-3 h-3" />
            FORK
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); data.onAiFork(); }}
            className="px-2 py-1 bg-emerald-500/80 hover:bg-emerald-500 text-white text-[10px] font-mono flex items-center gap-1 transition-colors"
            title="Generate AI forks"
          >
            <Sparkles className="w-3 h-3" />
            AI
          </button>
          {/* Delete button - only for non-baseline nodes */}
          {!data.isBaseline && (
            <button
              onClick={(e) => { e.stopPropagation(); data.onDelete(); }}
              className="px-2 py-1 bg-red-500/60 hover:bg-red-500 text-white text-[10px] font-mono flex items-center gap-1 transition-colors"
              title="Delete this fork"
            >
              <Trash2 className="w-3 h-3" />
            </button>
          )}
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

        {/* Run on this Node - always available */}
        <Link href={`/p/${projectId}/run-center?node=${node.id}`} className="block">
          <Button
            size="sm"
            variant="outline"
            className="w-full text-xs font-mono border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/10"
          >
            <Play className="w-3 h-3 mr-2" />
            Run on this Node
          </Button>
        </Link>

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
            <Link href={`/p/${projectId}/world-viewer?node=${node.id}`} className="block">
              <Button size="sm" variant="outline" className="w-full text-xs font-mono">
                <MapIcon className="w-3 h-3 mr-2" />
                View in 2D World
              </Button>
            </Link>
            <Link href={`/p/${projectId}/reports?type=node&node=${node.id}`} className="block">
              <Button size="sm" variant="outline" className="w-full text-xs font-mono">
                <FileText className="w-3 h-3 mr-2" />
                View Report
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
  const searchParams = useSearchParams();
  const projectId = params.projectId as string;
  const { fitView, zoomIn, zoomOut } = useReactFlow();

  // Track if we've processed URL params to avoid re-processing
  const urlParamsProcessed = useRef(false);

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

  // Delete confirmation state
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deletingNode, setDeletingNode] = useState<UniverseNode | null>(null);

  // AI Fork modal state
  const [aiForkModalOpen, setAiForkModalOpen] = useState(false);
  const [aiForkingNode, setAiForkingNode] = useState<UniverseNode | null>(null);
  const [aiForkCount, setAiForkCount] = useState(3);
  const [aiForkGenerating, setAiForkGenerating] = useState(false);

  // API hooks - using useUniverseMap (not useUniverseMapFull which calls a non-existent endpoint)
  const { data: mapData, isLoading: mapLoading, error: mapError, refetch: refetchMap } = useUniverseMap(projectId);
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

  // Build universe nodes from API data with hierarchical DAG layout
  const buildUniverseFromData = useCallback(() => {
    const savedPositions = loadPositions();
    const newUniverseNodes = new Map<string, UniverseNode>();
    const flowNodes: Node[] = [];
    const flowEdges: Edge[] = [];

    // Get all runs for status aggregation
    const allRuns: RunSummary[] = runs || [];
    const calcProgress = (r: RunSummary) => {
      const current = r.timing?.current_tick || 0;
      const total = r.timing?.total_ticks || 100;
      return total > 0 ? (current / total) : 0;
    };

    // === PHASE 1: Build node tree structure ===
    const baselineId = 'baseline-root';
    // Use nodesList from useNodes hook (mapData only contains state/ids, not actual node data)
    const apiNodes = nodesList || [];

    // Track parent-child relationships for layout
    const childrenMap = new Map<string, string[]>(); // parentId -> [childIds]
    childrenMap.set(baselineId, []);

    // First, create all nodes and track relationships
    const tempNodes = new Map<string, {
      node: UniverseNode;
      apiDepth: number;
      parentId: string;
    }>();

    // Create baseline root node
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
      depth: 0,
      forkType: 'baseline',
      childCount: 0,
    };
    newUniverseNodes.set(baselineId, baselineNode);

    // Process API nodes - determine which are baseline updates vs forks
    apiNodes.forEach((apiNode, index) => {
      const isBaselineNode = ('depth' in apiNode && (apiNode as unknown as SpecNode).depth === 0) ||
                            ('is_baseline' in apiNode && (apiNode as unknown as NodeSummary).is_baseline);

      if (isBaselineNode) {
        // Update baseline with API data
        const existing = newUniverseNodes.get(baselineId)!;
        existing.probability = apiNode.probability;
        if ('confidence' in apiNode && (apiNode as unknown as SpecNode).confidence) {
          existing.confidence = ((apiNode as unknown as SpecNode).confidence?.level as 'high' | 'medium' | 'low') || 'medium';
        }
        if ('confidence_level' in apiNode) {
          existing.confidence = ((apiNode as NodeSummary).confidence_level as 'high' | 'medium' | 'low') || 'medium';
        }
        if (apiNode.label) {
          existing.label = apiNode.label;
        }
        return;
      }

      // It's a fork node - determine fork type based on label/description patterns
      const nodeId = apiNode.node_id;
      const nodeLabel = apiNode.label || '';
      const nodeDesc = ('description' in apiNode ? (apiNode as unknown as SpecNode).description : '') || '';
      const apiDepth = ('depth' in apiNode ? (apiNode as unknown as SpecNode).depth : 1) || 1;

      // AI forks typically have generated labels like "Scenario: X wins" or outcomes
      const isAIFork = nodeLabel.includes('Scenario') ||
                      nodeLabel.includes('Outcome') ||
                      nodeLabel.includes('Prediction') ||
                      nodeDesc.includes('AI generated') ||
                      nodeDesc.includes('auto-generated') ||
                      !nodeLabel.includes('Manual') && apiDepth > 1;

      const parentId = apiNode.parent_node_id || baselineId;

      // Track child relationships
      if (!childrenMap.has(parentId)) {
        childrenMap.set(parentId, []);
      }
      childrenMap.get(parentId)!.push(nodeId);
      childrenMap.set(nodeId, []); // Initialize children array for this node

      const forkNode: UniverseNode = {
        id: nodeId,
        label: apiNode.label || `Fork ${index + 1}`,
        probability: apiNode.probability,
        confidence: (
          // First check for nested confidence.confidence_level (fork nodes from API)
          ('confidence' in apiNode && typeof (apiNode as Record<string, unknown>).confidence === 'object' &&
           (apiNode as Record<string, unknown>).confidence !== null &&
           'confidence_level' in ((apiNode as Record<string, unknown>).confidence as Record<string, unknown>))
            ? (((apiNode as Record<string, unknown>).confidence as Record<string, unknown>).confidence_level as string)
          // Then check for nested confidence.level (spec nodes)
          : ('confidence' in apiNode && typeof (apiNode as Record<string, unknown>).confidence === 'object' &&
             (apiNode as Record<string, unknown>).confidence !== null &&
             'level' in ((apiNode as Record<string, unknown>).confidence as Record<string, unknown>))
            ? (((apiNode as Record<string, unknown>).confidence as Record<string, unknown>).level as string)
          // Then check for direct confidence_level property (NodeSummary)
          : ('confidence_level' in apiNode)
            ? ((apiNode as unknown as NodeSummary).confidence_level)
          // Default fallback
          : 'medium'
        ) as 'high' | 'medium' | 'low',
        status: ('has_outcome' in apiNode && (apiNode as unknown as NodeSummary).has_outcome) ? 'completed' : 'draft',
        isBaseline: false,
        runCount: 1,
        parentId,
        createdAt: ('created_at' in apiNode ? (apiNode as NodeSummary).created_at : new Date().toISOString()),
        outcome: ('aggregated_outcome' in apiNode ? (apiNode as unknown as SpecNode).aggregated_outcome?.primary_outcome : undefined),
        depth: apiDepth,
        forkType: isAIFork ? 'ai' : 'manual',
        childCount: 0,
      };

      tempNodes.set(nodeId, { node: forkNode, apiDepth, parentId });
      newUniverseNodes.set(nodeId, forkNode);
    });

    // === PHASE 2: Calculate child counts ===
    childrenMap.forEach((children, parentId) => {
      const parentNode = newUniverseNodes.get(parentId);
      if (parentNode) {
        parentNode.childCount = children.length;
      }
    });

    // === PHASE 3: Calculate hierarchical positions (Sugiyama-style) ===
    // Group nodes by depth level
    const levelMap = new Map<number, string[]>();
    newUniverseNodes.forEach((node, id) => {
      if (!levelMap.has(node.depth)) {
        levelMap.set(node.depth, []);
      }
      levelMap.get(node.depth)!.push(id);
    });

    // Layout constants
    const LEVEL_HEIGHT = 200; // Vertical spacing between levels
    const NODE_WIDTH = 280; // Horizontal spacing between nodes
    const CANVAS_CENTER_X = 500; // Center X position

    // Calculate positions level by level
    const nodePositions = new Map<string, { x: number; y: number }>();

    // Sort levels
    const sortedLevels = Array.from(levelMap.keys()).sort((a, b) => a - b);

    sortedLevels.forEach((level) => {
      const nodesAtLevel = levelMap.get(level)!;
      const numNodes = nodesAtLevel.length;
      const totalWidth = (numNodes - 1) * NODE_WIDTH;
      const startX = CANVAS_CENTER_X - totalWidth / 2;

      // Sort nodes by parent position for better edge layout
      nodesAtLevel.sort((a, b) => {
        const nodeA = newUniverseNodes.get(a)!;
        const nodeB = newUniverseNodes.get(b)!;
        const parentPosA = nodePositions.get(nodeA.parentId || '') || { x: CANVAS_CENTER_X };
        const parentPosB = nodePositions.get(nodeB.parentId || '') || { x: CANVAS_CENTER_X };
        return parentPosA.x - parentPosB.x;
      });

      nodesAtLevel.forEach((nodeId, index) => {
        const savedPos = savedPositions[nodeId];
        if (savedPos) {
          nodePositions.set(nodeId, savedPos);
        } else {
          nodePositions.set(nodeId, {
            x: startX + index * NODE_WIDTH,
            y: level * LEVEL_HEIGHT + 50,
          });
        }
      });
    });

    // === PHASE 4: Create React Flow nodes and edges ===
    newUniverseNodes.forEach((node, nodeId) => {
      const pos = nodePositions.get(nodeId) || { x: CANVAS_CENTER_X, y: node.depth * LEVEL_HEIGHT + 50 };

      flowNodes.push({
        id: nodeId,
        type: 'sciFiNode',
        position: pos,
        data: {
          ...node,
          onFork: () => {
            setForkingNode(node);
            setForkModalOpen(true);
          },
          onAiFork: () => {
            setAiForkingNode(node);
            setAiForkModalOpen(true);
          },
          onDelete: () => {
            setDeletingNode(node);
            setDeleteModalOpen(true);
          },
        },
      });

      // Create edge to parent (skip baseline which has no parent)
      if (node.parentId) {
        const edgeColor = node.forkType === 'ai' ? '#10b981' : '#a855f7'; // Green for AI, purple for manual
        flowEdges.push({
          id: `${node.parentId}-${nodeId}`,
          source: node.parentId,
          target: nodeId,
          type: 'smoothstep',
          animated: node.status === 'running',
          style: {
            stroke: edgeColor,
            strokeWidth: 2,
            strokeDasharray: node.forkType === 'ai' ? undefined : '5,5', // Dashed for manual
          },
          markerEnd: { type: MarkerType.ArrowClosed, color: edgeColor },
        });
      }
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

  // Handle URL params for auto-selecting node and opening inspector
  // This is used when navigating from Event Lab after creating a branch
  useEffect(() => {
    if (urlParamsProcessed.current) return;
    if (isLoading || universeNodes.size === 0) return;

    const selectNodeId = searchParams.get('select');
    const shouldOpenInspector = searchParams.get('inspect') === 'true';

    if (selectNodeId) {
      // Find the node to select
      const nodeExists = universeNodes.has(selectNodeId) || nodes.some(n => n.id === selectNodeId);

      if (nodeExists) {
        setSelectedNodeId(selectNodeId);
        if (shouldOpenInspector) {
          setInspectorOpen(true);
        }
        urlParamsProcessed.current = true;

        // Clean up URL params after processing (optional - removes params from URL bar)
        if (typeof window !== 'undefined') {
          const url = new URL(window.location.href);
          url.searchParams.delete('select');
          url.searchParams.delete('inspect');
          window.history.replaceState({}, '', url.pathname);
        }
      }
    }
  }, [isLoading, universeNodes, nodes, searchParams]);

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

    // Get parent's depth from the existing flow nodes
    const parentFlowNode = nodes.find((n) => n.id === forkingNode.id);
    const parentData = parentFlowNode?.data as SciFiNodeData | undefined;
    const parentDepth = parentData?.depth ?? 0;

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
      depth: parentDepth + 1,
      forkType: 'manual', // User-created fork
      childCount: 0,
    };

    // Calculate position relative to parent (parentFlowNode already defined above)
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
        onAiFork: () => {
          setAiForkingNode(newNode);
          setAiForkModalOpen(true);
        },
        onDelete: () => {
          setDeletingNode(newNode);
          setDeleteModalOpen(true);
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

  // Handle node double-click to open inspector
  const handleNodeDoubleClick = useCallback((_event: React.MouseEvent, node: Node) => {
    setSelectedNodeId(node.id);
    setInspectorOpen(true);
  }, []);

  // Handle delete confirmation
  const handleDeleteConfirm = useCallback(() => {
    if (!deletingNode || deletingNode.isBaseline) return;

    // Remove the node and its children recursively
    const nodeIdsToRemove = new Set<string>();
    const collectChildIds = (nodeId: string) => {
      nodeIdsToRemove.add(nodeId);
      // Find children of this node
      edges.forEach((edge) => {
        if (edge.source === nodeId) {
          collectChildIds(edge.target);
        }
      });
    };
    collectChildIds(deletingNode.id);

    // Remove nodes
    setNodes((nds) => nds.filter((n) => !nodeIdsToRemove.has(n.id)));

    // Remove edges connected to deleted nodes
    setEdges((eds) => eds.filter((e) => !nodeIdsToRemove.has(e.source) && !nodeIdsToRemove.has(e.target)));

    // Remove from universeNodes
    setUniverseNodes((prev) => {
      const newMap = new Map(prev);
      nodeIdsToRemove.forEach((id) => newMap.delete(id));
      return newMap;
    });

    // Remove saved positions
    const positions = loadPositions();
    nodeIdsToRemove.forEach((id) => delete positions[id]);
    savePositions(positions);

    setDeleteModalOpen(false);
    setDeletingNode(null);
  }, [deletingNode, edges, setNodes, setEdges, loadPositions, savePositions]);

  // Handle AI Fork generation
  const handleAiForkGenerate = useCallback(() => {
    if (!aiForkingNode) return;

    setAiForkGenerating(true);

    // Get parent's depth
    const parentFlowNode = nodes.find((n) => n.id === aiForkingNode.id);
    const parentData = parentFlowNode?.data as SciFiNodeData | undefined;
    const parentDepth = parentData?.depth ?? 0;

    // Simulate AI-generated scenarios (in real implementation, this would call the backend AI)
    const aiScenarios = [
      { name: 'Optimistic Scenario', probability: 0.65 },
      { name: 'Conservative Scenario', probability: 0.45 },
      { name: 'Alternative Path', probability: 0.55 },
      { name: 'High Growth Variant', probability: 0.70 },
      { name: 'Risk-Adjusted Outcome', probability: 0.40 },
    ].slice(0, aiForkCount);

    const existingChildCount = edges.filter((e) => e.source === aiForkingNode.id).length;
    const newNodes: Node[] = [];
    const newEdges: Edge[] = [];
    const newUniverseNodeEntries: Array<[string, UniverseNode]> = [];
    const newPositions: Record<string, { x: number; y: number }> = {};

    aiScenarios.forEach((scenario, index) => {
      const newId = `ai-fork-${Date.now()}-${index}`;
      const totalIndex = existingChildCount + index;
      const xOffset = (totalIndex - Math.floor((existingChildCount + aiScenarios.length) / 2)) * 280;

      const newNode: UniverseNode = {
        id: newId,
        label: scenario.name,
        probability: scenario.probability,
        confidence: scenario.probability >= 0.6 ? 'high' : scenario.probability >= 0.4 ? 'medium' : 'low',
        status: 'draft',
        isBaseline: false,
        runCount: 0,
        parentId: aiForkingNode.id,
        createdAt: new Date().toISOString(),
        depth: parentDepth + 1,
        forkType: 'ai',
        childCount: 0,
      };

      const position = {
        x: (parentFlowNode?.position.x || 400) + xOffset,
        y: (parentFlowNode?.position.y || 50) + 200,
      };

      newNodes.push({
        id: newId,
        type: 'sciFiNode',
        position,
        data: {
          ...newNode,
          onFork: () => {
            setForkingNode(newNode);
            setForkModalOpen(true);
          },
          onAiFork: () => {
            setAiForkingNode(newNode);
            setAiForkModalOpen(true);
          },
          onDelete: () => {
            setDeletingNode(newNode);
            setDeleteModalOpen(true);
          },
        },
      });

      newEdges.push({
        id: `${aiForkingNode.id}-${newId}`,
        source: aiForkingNode.id,
        target: newId,
        type: 'smoothstep',
        animated: false,
        style: { stroke: '#10b981', strokeWidth: 2 }, // Green for AI forks
        markerEnd: { type: MarkerType.ArrowClosed, color: '#10b981' },
      });

      newUniverseNodeEntries.push([newId, newNode]);
      newPositions[newId] = position;
    });

    // Add all new nodes and edges
    setNodes((nds) => [...nds, ...newNodes]);
    setEdges((eds) => [...eds, ...newEdges]);
    setUniverseNodes((prev) => {
      const newMap = new Map(prev);
      newUniverseNodeEntries.forEach(([id, node]) => newMap.set(id, node));
      return newMap;
    });

    // Save positions
    const positions = loadPositions();
    Object.assign(positions, newPositions);
    savePositions(positions);

    setAiForkGenerating(false);
    setAiForkModalOpen(false);
    setAiForkingNode(null);
  }, [aiForkingNode, aiForkCount, nodes, edges, setNodes, setEdges, loadPositions, savePositions]);

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
          onNodeDoubleClick={handleNodeDoubleClick}
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

          {/* Legend panel - positioned to avoid blocking Controls */}
          <Panel position="bottom-center" className="mb-4">
            <div className="bg-black/90 border border-white/10 px-4 py-2">
              <div className="flex items-center gap-6">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-cyan-500" />
                  <span className="text-[10px] font-mono text-white/60">Baseline</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-emerald-500" />
                  <span className="text-[10px] font-mono text-white/60">AI Fork</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-purple-500 border border-dashed border-purple-400" />
                  <span className="text-[10px] font-mono text-white/60">Manual Fork</span>
                </div>
                <div className="flex items-center gap-2">
                  <Activity className="w-3 h-3 text-cyan-400 animate-pulse" />
                  <span className="text-[10px] font-mono text-white/60">Running</span>
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
                  <span>AI Forks</span>
                  <span className="text-emerald-400">{Array.from(universeNodes.values()).filter(n => n.forkType === 'ai').length}</span>
                </div>
                <div className="flex justify-between gap-4">
                  <span>Manual Forks</span>
                  <span className="text-purple-400">{Array.from(universeNodes.values()).filter(n => n.forkType === 'manual').length}</span>
                </div>
                <div className="flex justify-between gap-4">
                  <span>Completed</span>
                  <span className="text-green-400">
                    {Array.from(universeNodes.values()).filter(n => n.status === 'completed').length}
                  </span>
                </div>
                <div className="flex justify-between gap-4">
                  <span>Max Depth</span>
                  <span className="text-white">
                    {Math.max(0, ...Array.from(universeNodes.values()).map(n => n.depth))}
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

      {/* Delete Confirmation Modal */}
      <Dialog open={deleteModalOpen} onOpenChange={(open) => { setDeleteModalOpen(open); if (!open) setDeletingNode(null); }}>
        <DialogContent className="bg-black border border-red-500/30 max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-white font-mono flex items-center gap-2">
              <Trash2 className="w-5 h-5 text-red-400" />
              Delete Fork
            </DialogTitle>
            <DialogDescription className="text-white/50 font-mono text-xs">
              Are you sure you want to delete this fork?
            </DialogDescription>
          </DialogHeader>
          {deletingNode && (
            <div className="py-4 space-y-3">
              <div className="p-3 bg-red-500/5 border border-red-500/20">
                <div className="text-sm font-mono text-white font-medium">{deletingNode.label}</div>
                <div className="text-xs font-mono text-white/40 mt-1">
                  {deletingNode.forkType === 'ai' ? 'AI-generated fork' : 'Manual fork'}
                </div>
              </div>
              <div className="text-xs font-mono text-red-400/80">
                <AlertCircle className="w-3 h-3 inline mr-1" />
                This will also delete all child forks. This action cannot be undone.
              </div>
            </div>
          )}
          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              onClick={() => { setDeleteModalOpen(false); setDeletingNode(null); }}
              className="border-white/20 text-white/60"
            >
              Cancel
            </Button>
            <Button
              onClick={handleDeleteConfirm}
              className="bg-red-500/80 hover:bg-red-500 text-white"
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* AI Fork Modal */}
      <Dialog open={aiForkModalOpen} onOpenChange={(open) => { setAiForkModalOpen(open); if (!open) setAiForkingNode(null); }}>
        <DialogContent className="bg-black border border-emerald-500/30 max-w-md">
          <DialogHeader>
            <DialogTitle className="text-white font-mono flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-emerald-400" />
              Generate AI Forks
            </DialogTitle>
            <DialogDescription className="text-white/50 font-mono text-xs">
              Let AI generate alternative scenario branches
            </DialogDescription>
          </DialogHeader>
          {aiForkingNode && (
            <div className="py-4 space-y-4">
              <div className="p-3 bg-emerald-500/5 border border-emerald-500/20">
                <div className="text-[10px] font-mono text-white/40 uppercase mb-1">Parent Node</div>
                <div className="text-sm font-mono text-white font-medium">{aiForkingNode.label}</div>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-mono text-white/60">Number of scenarios to generate</label>
                <div className="flex items-center gap-3">
                  {[2, 3, 4, 5].map((num) => (
                    <button
                      key={num}
                      onClick={() => setAiForkCount(num)}
                      className={cn(
                        'w-10 h-10 border font-mono text-sm transition-colors',
                        aiForkCount === num
                          ? 'bg-emerald-500/20 border-emerald-500 text-emerald-400'
                          : 'bg-white/5 border-white/20 text-white/60 hover:border-white/40'
                      )}
                    >
                      {num}
                    </button>
                  ))}
                </div>
              </div>

              <div className="p-3 bg-white/5 border border-white/10 space-y-1.5">
                <div className="text-[10px] font-mono text-white/40 uppercase">AI will generate</div>
                <ul className="text-xs font-mono text-white/60 space-y-1">
                  <li className="flex items-center gap-2">
                    <Zap className="w-3 h-3 text-emerald-400" />
                    Alternative outcome scenarios
                  </li>
                  <li className="flex items-center gap-2">
                    <Zap className="w-3 h-3 text-emerald-400" />
                    Probability estimates
                  </li>
                  <li className="flex items-center gap-2">
                    <Zap className="w-3 h-3 text-emerald-400" />
                    Confidence levels
                  </li>
                </ul>
              </div>
            </div>
          )}
          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              onClick={() => { setAiForkModalOpen(false); setAiForkingNode(null); }}
              className="border-white/20 text-white/60"
            >
              Cancel
            </Button>
            <Button
              onClick={handleAiForkGenerate}
              disabled={aiForkGenerating}
              className="bg-emerald-500/80 hover:bg-emerald-500 text-white"
            >
              {aiForkGenerating ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 mr-2" />
                  Generate {aiForkCount} Forks
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// Loading fallback for Suspense
function UniverseMapLoading() {
  return (
    <div className="min-h-screen bg-black flex items-center justify-center">
      <div className="text-center">
        <Loader2 className="w-8 h-8 text-cyan-500 animate-spin mx-auto mb-4" />
        <p className="text-white/60 font-mono text-sm">Loading Universe Map...</p>
      </div>
    </div>
  );
}

// Wrap with provider and Suspense for useSearchParams
export default function UniverseMapPage() {
  return (
    <Suspense fallback={<UniverseMapLoading />}>
      <ReactFlowProvider>
        <UniverseMapCanvas />
      </ReactFlowProvider>
    </Suspense>
  );
}

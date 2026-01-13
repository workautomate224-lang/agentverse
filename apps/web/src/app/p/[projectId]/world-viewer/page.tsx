'use client';

/**
 * 2D World Viewer Page
 * Spatial/visual replay of simulation runs with agent visualization
 * Integrated with Telemetry Replay, Universe Map, and Run Center
 */

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useParams, useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  Map,
  ArrowLeft,
  Terminal,
  Play,
  Pause,
  SkipBack,
  SkipForward,
  ZoomIn,
  ZoomOut,
  Maximize2,
  ChevronDown,
  CheckCircle,
  Loader2,
  AlertCircle,
  Activity,
  GitBranch,
  BarChart3,
  FileText,
  Users,
  X,
  ExternalLink,
  Crosshair,
  Info,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  useRuns,
  useNodes,
  useTelemetryIndex,
  useTelemetrySummary,
  useTelemetrySlice,
  useNode,
} from '@/hooks/useApi';
import type { RunSummary, TelemetryIndex, TelemetrySummary, TelemetrySlice, TelemetryKeyframe } from '@/lib/api';

// =============================================================================
// Types
// =============================================================================

interface AgentPosition {
  agentId: string;
  x: number;
  y: number;
  state?: string;
  personaId?: string;
  variables?: Record<string, number>;
  memorySummary?: { belief_count: number; episode_count: number };
  socialEdgeCount?: number;
}

interface SpatialBounds {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

// =============================================================================
// Utilities
// =============================================================================

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

// Detect spatial fields in agent variables
// Returns { x, y } if found, null otherwise
function extractSpatialPosition(variables: Record<string, number> | undefined): { x: number; y: number } | null {
  if (!variables) return null;

  // Check for common spatial field patterns
  const xFields = ['x', 'position_x', 'pos_x', 'coord_x', 'loc_x'];
  const yFields = ['y', 'position_y', 'pos_y', 'coord_y', 'loc_y'];

  let x: number | null = null;
  let y: number | null = null;

  for (const field of xFields) {
    if (field in variables && typeof variables[field] === 'number') {
      x = variables[field];
      break;
    }
  }

  for (const field of yFields) {
    if (field in variables && typeof variables[field] === 'number') {
      y = variables[field];
      break;
    }
  }

  // Also check for location_id or grid_cell as fallback (map to positions)
  if (x === null && y === null) {
    if ('location_id' in variables) {
      // Generate pseudo-positions from location_id
      const locId = variables.location_id;
      x = (locId % 10) * 50;
      y = Math.floor(locId / 10) * 50;
    } else if ('grid_cell' in variables) {
      const cell = variables.grid_cell;
      x = (cell % 10) * 50;
      y = Math.floor(cell / 10) * 50;
    }
  }

  if (x !== null && y !== null) {
    return { x, y };
  }

  return null;
}

// Extract agent positions from telemetry slice
function extractAgentPositions(slice: TelemetrySlice | undefined): AgentPosition[] {
  if (!slice) return [];

  const positions: AgentPosition[] = [];

  // Try keyframes first
  const keyframe = slice.keyframes?.[0];
  if (keyframe?.agent_states) {
    for (const [agentId, agentState] of Object.entries(keyframe.agent_states)) {
      const pos = extractSpatialPosition(agentState.variables);
      if (pos) {
        positions.push({
          agentId,
          x: pos.x,
          y: pos.y,
          state: agentState.state,
          personaId: agentState.persona_id,
          variables: agentState.variables,
          memorySummary: agentState.memory_summary,
          socialEdgeCount: agentState.social_edge_count,
        });
      }
    }
  }

  return positions;
}

// Check if spatial telemetry exists in slice
function hasSpatialTelemetry(slice: TelemetrySlice | undefined): boolean {
  if (!slice) return false;

  const keyframe = slice.keyframes?.[0];
  if (keyframe?.agent_states) {
    for (const agentState of Object.values(keyframe.agent_states)) {
      if (extractSpatialPosition(agentState.variables)) {
        return true;
      }
    }
  }

  return false;
}

// Calculate bounds for all agent positions
function calculateBounds(positions: AgentPosition[]): SpatialBounds {
  if (positions.length === 0) {
    return { minX: -100, maxX: 100, minY: -100, maxY: 100 };
  }

  let minX = Infinity, maxX = -Infinity;
  let minY = Infinity, maxY = -Infinity;

  for (const pos of positions) {
    minX = Math.min(minX, pos.x);
    maxX = Math.max(maxX, pos.x);
    minY = Math.min(minY, pos.y);
    maxY = Math.max(maxY, pos.y);
  }

  // Add padding
  const padX = Math.max((maxX - minX) * 0.1, 50);
  const padY = Math.max((maxY - minY) * 0.1, 50);

  return {
    minX: minX - padX,
    maxX: maxX + padX,
    minY: minY - padY,
    maxY: maxY + padY,
  };
}

// =============================================================================
// Components
// =============================================================================

// Run selector dropdown component
function RunSelector({
  runs,
  selectedRunId,
  onSelectRun,
  isLoading,
  nodeLabel,
}: {
  runs: RunSummary[] | undefined;
  selectedRunId: string | null;
  onSelectRun: (runId: string) => void;
  isLoading: boolean;
  nodeLabel?: string;
}) {
  const [isOpen, setIsOpen] = useState(false);

  // Filter to only runs with status=succeeded
  const completedRuns = runs?.filter((r) => r.status === 'succeeded') || [];
  const selectedRun = completedRuns.find((r) => r.run_id === selectedRunId);

  return (
    <div className="relative">
      <div className="text-[10px] font-mono text-white/40 uppercase mb-1">
        Run {nodeLabel && <span className="text-cyan-400">({nodeLabel})</span>}
      </div>
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={isLoading || completedRuns.length === 0}
        className={cn(
          'w-full px-3 py-2 bg-black border border-white/10 text-left flex items-center justify-between transition-colors',
          'hover:border-white/30 focus:outline-none focus:border-cyan-500/50',
          (isLoading || completedRuns.length === 0) && 'opacity-50 cursor-not-allowed'
        )}
      >
        <span className="text-xs font-mono text-white/60 truncate">
          {isLoading ? (
            'Loading runs...'
          ) : selectedRun ? (
            <span className="text-white">
              {selectedRun.run_id.slice(0, 8)}... - {formatDate(selectedRun.created_at)}
            </span>
          ) : completedRuns.length === 0 ? (
            'No completed runs'
          ) : (
            'Select a run'
          )}
        </span>
        <ChevronDown className={cn('w-4 h-4 text-white/40 transition-transform', isOpen && 'rotate-180')} />
      </button>

      {isOpen && completedRuns.length > 0 && (
        <div className="absolute z-50 top-full left-0 right-0 mt-1 bg-black border border-white/10 max-h-48 overflow-y-auto">
          {completedRuns.map((run) => (
            <button
              key={run.run_id}
              onClick={() => {
                onSelectRun(run.run_id);
                setIsOpen(false);
              }}
              className={cn(
                'w-full px-3 py-2 text-left flex items-center justify-between hover:bg-white/5 transition-colors',
                selectedRunId === run.run_id && 'bg-cyan-500/10'
              )}
            >
              <div>
                <p className="text-xs font-mono text-white">{run.run_id.slice(0, 12)}...</p>
                <p className="text-[10px] font-mono text-white/40">{formatDate(run.created_at)}</p>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono text-white/40">
                  {run.timing?.total_ticks || '?'} ticks
                </span>
                {run.has_results && <CheckCircle className="w-3 h-3 text-green-400" />}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// Keyframe list component
function KeyframeList({
  keyframeTicks,
  currentTick,
  onSeek,
}: {
  keyframeTicks: number[];
  currentTick: number;
  onSeek: (tick: number) => void;
}) {
  if (keyframeTicks.length === 0) {
    return (
      <div className="text-xs font-mono text-white/40 text-center py-2">
        No keyframes
      </div>
    );
  }

  return (
    <div className="space-y-1 max-h-32 overflow-y-auto">
      {keyframeTicks.map((tick) => (
        <button
          key={tick}
          onClick={() => onSeek(tick)}
          className={cn(
            'w-full px-2 py-1 text-left text-xs font-mono transition-colors',
            currentTick === tick
              ? 'bg-cyan-500/20 text-cyan-400 border-l-2 border-cyan-500'
              : 'text-white/60 hover:bg-white/5'
          )}
        >
          Tick {tick}
        </button>
      ))}
    </div>
  );
}

// Agent Inspector Drawer
function AgentInspector({
  agent,
  currentTick,
  runId,
  projectId,
  onClose,
}: {
  agent: AgentPosition;
  currentTick: number;
  runId: string;
  projectId: string;
  onClose: () => void;
}) {
  return (
    <div className="w-72 bg-black/95 border-l border-white/10 p-4 h-full overflow-y-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-mono font-bold text-white">Agent Inspector</h3>
        <button onClick={onClose} className="p-1 hover:bg-white/10 transition-colors">
          <X className="w-4 h-4 text-white/60" />
        </button>
      </div>

      {/* Agent ID */}
      <div className="mb-4">
        <div className="text-[10px] font-mono text-white/40 uppercase mb-1">Agent ID</div>
        <div className="text-xs font-mono text-cyan-400 break-all">{agent.agentId}</div>
      </div>

      {/* Persona */}
      {agent.personaId && (
        <div className="mb-4">
          <div className="text-[10px] font-mono text-white/40 uppercase mb-1">Persona</div>
          <div className="text-xs font-mono text-white">{agent.personaId}</div>
        </div>
      )}

      {/* State */}
      {agent.state && (
        <div className="mb-4">
          <div className="text-[10px] font-mono text-white/40 uppercase mb-1">State</div>
          <div className="text-xs font-mono text-white">{agent.state}</div>
        </div>
      )}

      {/* Position */}
      <div className="mb-4">
        <div className="text-[10px] font-mono text-white/40 uppercase mb-1">Position</div>
        <div className="text-xs font-mono text-white">
          X: {agent.x.toFixed(2)}, Y: {agent.y.toFixed(2)}
        </div>
      </div>

      {/* Memory Summary */}
      {agent.memorySummary && (
        <div className="mb-4">
          <div className="text-[10px] font-mono text-white/40 uppercase mb-1">Memory</div>
          <div className="text-xs font-mono text-white">
            {agent.memorySummary.belief_count} beliefs, {agent.memorySummary.episode_count} episodes
          </div>
        </div>
      )}

      {/* Social Edges */}
      {agent.socialEdgeCount !== undefined && (
        <div className="mb-4">
          <div className="text-[10px] font-mono text-white/40 uppercase mb-1">Social Connections</div>
          <div className="text-xs font-mono text-white">{agent.socialEdgeCount} edges</div>
        </div>
      )}

      {/* Variables */}
      {agent.variables && Object.keys(agent.variables).length > 0 && (
        <div className="mb-4">
          <div className="text-[10px] font-mono text-white/40 uppercase mb-1">Variables</div>
          <div className="space-y-1 max-h-40 overflow-y-auto">
            {Object.entries(agent.variables).map(([key, value]) => (
              <div key={key} className="flex justify-between text-xs font-mono">
                <span className="text-white/60">{key}</span>
                <span className="text-white">{typeof value === 'number' ? value.toFixed(2) : String(value)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Jump to Telemetry Replay */}
      <div className="mt-6 pt-4 border-t border-white/10">
        <Link
          href={`/p/${projectId}/replay?run=${runId}&tick=${currentTick}&agent=${agent.agentId}`}
        >
          <Button variant="secondary" size="sm" className="w-full text-xs">
            <ExternalLink className="w-3 h-3 mr-2" />
            Jump to Telemetry Replay
          </Button>
        </Link>
      </div>
    </div>
  );
}

// 2D Canvas Component
function WorldCanvas({
  positions,
  bounds,
  selectedAgentId,
  onSelectAgent,
  zoom,
  pan,
  onZoom,
  onPan,
}: {
  positions: AgentPosition[];
  bounds: SpatialBounds;
  selectedAgentId: string | null;
  onSelectAgent: (agentId: string | null) => void;
  zoom: number;
  pan: { x: number; y: number };
  onZoom: (delta: number) => void;
  onPan: (delta: { x: number; y: number }) => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [hoveredAgent, setHoveredAgent] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  // Calculate viewport dimensions
  const viewWidth = bounds.maxX - bounds.minX;
  const viewHeight = bounds.maxY - bounds.minY;

  // Transform world coordinates to screen coordinates
  const worldToScreen = useCallback((worldX: number, worldY: number) => {
    const container = containerRef.current;
    if (!container) return { x: 0, y: 0 };

    const rect = container.getBoundingClientRect();
    const scaleX = (rect.width / viewWidth) * zoom;
    const scaleY = (rect.height / viewHeight) * zoom;
    const scale = Math.min(scaleX, scaleY);

    const centerX = rect.width / 2 + pan.x;
    const centerY = rect.height / 2 + pan.y;

    const worldCenterX = (bounds.minX + bounds.maxX) / 2;
    const worldCenterY = (bounds.minY + bounds.maxY) / 2;

    return {
      x: centerX + (worldX - worldCenterX) * scale,
      y: centerY + (worldY - worldCenterY) * scale,
    };
  }, [bounds, viewWidth, viewHeight, zoom, pan]);

  // Handle wheel zoom
  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    onZoom(delta);
  }, [onZoom]);

  // Handle pan
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button === 0) {
      setIsDragging(true);
      setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
    }
  }, [pan]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (isDragging) {
      onPan({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
    }
  }, [isDragging, dragStart, onPan]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  return (
    <div
      ref={containerRef}
      className="w-full h-full relative overflow-hidden cursor-grab active:cursor-grabbing"
      onWheel={handleWheel}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      {/* Grid Background */}
      <div
        className="absolute inset-0 opacity-20"
        style={{
          backgroundImage: `
            linear-gradient(to right, rgba(0,255,255,0.1) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(0,255,255,0.1) 1px, transparent 1px)
          `,
          backgroundSize: `${40 * zoom}px ${40 * zoom}px`,
          backgroundPosition: `${pan.x}px ${pan.y}px`,
        }}
      />

      {/* Agents */}
      {positions.map((agent) => {
        const screenPos = worldToScreen(agent.x, agent.y);
        const isSelected = selectedAgentId === agent.agentId;
        const isHovered = hoveredAgent === agent.agentId;

        return (
          <div
            key={agent.agentId}
            className="absolute transition-all duration-100"
            style={{
              left: screenPos.x,
              top: screenPos.y,
              transform: 'translate(-50%, -50%)',
            }}
          >
            {/* Agent dot */}
            <button
              onClick={() => onSelectAgent(isSelected ? null : agent.agentId)}
              onMouseEnter={() => setHoveredAgent(agent.agentId)}
              onMouseLeave={() => setHoveredAgent(null)}
              className={cn(
                'w-4 h-4 rounded-full transition-all duration-200',
                'hover:scale-150 hover:shadow-[0_0_12px_rgba(0,255,255,0.8)]',
                isSelected
                  ? 'bg-cyan-400 shadow-[0_0_16px_rgba(0,255,255,1)] scale-150'
                  : 'bg-cyan-500/80 shadow-[0_0_8px_rgba(0,255,255,0.5)]'
              )}
            />

            {/* Hover tooltip */}
            {isHovered && !isSelected && (
              <div className="absolute left-6 top-0 z-10 px-2 py-1 bg-black/90 border border-white/20 whitespace-nowrap">
                <div className="text-[10px] font-mono text-white">{agent.agentId.slice(0, 12)}...</div>
                {agent.state && (
                  <div className="text-[10px] font-mono text-white/60">{agent.state}</div>
                )}
              </div>
            )}
          </div>
        );
      })}

      {/* Center crosshair */}
      <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 pointer-events-none opacity-20">
        <Crosshair className="w-8 h-8 text-white/20" />
      </div>
    </div>
  );
}

// =============================================================================
// Main Page Component
// =============================================================================

export default function WorldViewerPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const projectId = params.projectId as string;

  // URL params
  const urlRunId = searchParams.get('run');
  const urlTick = searchParams.get('tick');
  const urlNodeId = searchParams.get('node');
  const urlAgentId = searchParams.get('agent');

  // State
  const [selectedRunId, setSelectedRunId] = useState<string | null>(urlRunId);
  const [currentTick, setCurrentTick] = useState(urlTick ? parseInt(urlTick, 10) : 0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(urlAgentId);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });

  // API hooks
  const { data: runs, isLoading: runsLoading } = useRuns({ project_id: projectId, status: 'succeeded', limit: 50 });
  const { data: nodes } = useNodes({ project_id: projectId });
  const { data: telemetryIndex, isLoading: indexLoading, error: indexError } = useTelemetryIndex(selectedRunId || undefined);
  const { data: telemetrySummary } = useTelemetrySummary(selectedRunId || undefined);
  const { data: currentSlice, isLoading: sliceLoading } = useTelemetrySlice(selectedRunId || undefined, currentTick);

  // Get run's node for label
  const selectedRun = runs?.find(r => r.run_id === selectedRunId);
  const { data: runNode } = useNode(selectedRun?.node_id);

  // Derived state
  const totalTicks = telemetrySummary?.total_ticks || telemetryIndex?.total_ticks || 0;
  const keyframeTicks = telemetryIndex?.keyframe_ticks || [];
  const isLoading = indexLoading || sliceLoading;

  // Extract agent positions and check for spatial data
  const agentPositions = useMemo(() => extractAgentPositions(currentSlice), [currentSlice]);
  const hasSpatialData = useMemo(() => hasSpatialTelemetry(currentSlice), [currentSlice]);
  const bounds = useMemo(() => calculateBounds(agentPositions), [agentPositions]);

  // Get selected agent for inspector
  const selectedAgent = useMemo(
    () => agentPositions.find(a => a.agentId === selectedAgentId),
    [agentPositions, selectedAgentId]
  );

  // Handle node preselection - find latest succeeded run for node
  useEffect(() => {
    if (urlNodeId && runs && !selectedRunId) {
      const nodeRuns = runs.filter(r => r.node_id === urlNodeId && r.status === 'succeeded');
      if (nodeRuns.length > 0) {
        // Sort by created_at descending and pick first
        const latestRun = nodeRuns.sort((a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        )[0];
        setSelectedRunId(latestRun.run_id);
      }
    }
  }, [urlNodeId, runs, selectedRunId]);

  // Update URL when state changes
  useEffect(() => {
    const params = new URLSearchParams();
    if (selectedRunId) params.set('run', selectedRunId);
    if (currentTick > 0) params.set('tick', currentTick.toString());
    if (selectedAgentId) params.set('agent', selectedAgentId);

    const newUrl = `/p/${projectId}/world-viewer${params.toString() ? `?${params.toString()}` : ''}`;
    window.history.replaceState({}, '', newUrl);
  }, [projectId, selectedRunId, currentTick, selectedAgentId]);

  // Playback logic
  useEffect(() => {
    if (!isPlaying || !selectedRunId || totalTicks === 0) return;

    const interval = setInterval(() => {
      setCurrentTick((tick) => {
        if (tick >= totalTicks - 1) {
          setIsPlaying(false);
          return tick;
        }
        return tick + 1;
      });
    }, 1000 / playbackSpeed);

    return () => clearInterval(interval);
  }, [isPlaying, selectedRunId, totalTicks, playbackSpeed]);

  // Playback controls
  const handlePlay = useCallback(() => {
    if (currentTick >= totalTicks - 1) {
      setCurrentTick(0);
    }
    setIsPlaying(true);
  }, [currentTick, totalTicks]);

  const handlePause = useCallback(() => setIsPlaying(false), []);
  const handleSkipBack = useCallback(() => { setCurrentTick(0); setIsPlaying(false); }, []);
  const handleSkipForward = useCallback(() => { setCurrentTick(Math.max(0, totalTicks - 1)); setIsPlaying(false); }, [totalTicks]);

  const handleSeek = useCallback((tick: number) => {
    setCurrentTick(Math.max(0, Math.min(tick, totalTicks - 1)));
  }, [totalTicks]);

  // Zoom controls
  const handleZoom = useCallback((delta: number) => {
    setZoom(z => Math.max(0.25, Math.min(4, z + delta)));
  }, []);

  const handleFitView = useCallback(() => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }, []);

  // Check states
  const hasTelemetry = selectedRunId && !indexError && (telemetryIndex || telemetrySummary);
  const showEmptyState = !selectedRunId;
  const showNoSpatialState = selectedRunId && hasTelemetry && !sliceLoading && !hasSpatialData;

  return (
    <div className="min-h-screen bg-black flex">
      {/* Left Panel */}
      <div className="w-72 border-r border-white/10 p-4 flex flex-col">
        {/* Header */}
        <div className="mb-6">
          <Link href={`/p/${projectId}/overview`}>
            <Button variant="ghost" size="sm" className="mb-3 text-[10px]">
              <ArrowLeft className="w-3 h-3 mr-1" />
              BACK TO OVERVIEW
            </Button>
          </Link>
          <div className="flex items-center gap-2 mb-1">
            <Map className="w-4 h-4 text-green-400" />
            <span className="text-[10px] font-mono text-white/40 uppercase tracking-wider">World Viewer</span>
          </div>
          <h1 className="text-lg font-mono font-bold text-white">2D World Viewer</h1>
        </div>

        {/* Run Selector */}
        <div className="mb-4">
          <RunSelector
            runs={runs}
            selectedRunId={selectedRunId}
            onSelectRun={setSelectedRunId}
            isLoading={runsLoading}
            nodeLabel={runNode?.label}
          />
        </div>

        {/* Tick Scrubber */}
        {hasTelemetry && (
          <>
            <div className="mb-4">
              <div className="text-[10px] font-mono text-white/40 uppercase mb-2">
                Tick: {currentTick} / {totalTicks}
              </div>
              <input
                type="range"
                min={0}
                max={Math.max(0, totalTicks - 1)}
                value={currentTick}
                onChange={(e) => handleSeek(parseInt(e.target.value, 10))}
                className="w-full accent-cyan-500"
                disabled={!hasTelemetry}
              />
            </div>

            {/* Playback Controls */}
            <div className="flex items-center justify-center gap-2 mb-4">
              <button
                onClick={handleSkipBack}
                className="p-2 hover:bg-white/10 transition-colors"
                disabled={!hasTelemetry}
              >
                <SkipBack className="w-4 h-4 text-white/60" />
              </button>
              <button
                onClick={isPlaying ? handlePause : handlePlay}
                className="p-2 bg-cyan-500/20 hover:bg-cyan-500/30 transition-colors"
                disabled={!hasTelemetry}
              >
                {isPlaying ? (
                  <Pause className="w-5 h-5 text-cyan-400" />
                ) : (
                  <Play className="w-5 h-5 text-cyan-400" />
                )}
              </button>
              <button
                onClick={handleSkipForward}
                className="p-2 hover:bg-white/10 transition-colors"
                disabled={!hasTelemetry}
              >
                <SkipForward className="w-4 h-4 text-white/60" />
              </button>

              {/* Speed selector */}
              <select
                value={playbackSpeed}
                onChange={(e) => setPlaybackSpeed(parseFloat(e.target.value))}
                className="ml-2 px-2 py-1 bg-black border border-white/10 text-xs font-mono text-white"
              >
                <option value={0.5}>0.5x</option>
                <option value={1}>1x</option>
                <option value={2}>2x</option>
                <option value={4}>4x</option>
              </select>
            </div>

            {/* Keyframes */}
            <div className="mb-4">
              <div className="text-[10px] font-mono text-white/40 uppercase mb-2">Keyframes</div>
              <KeyframeList
                keyframeTicks={keyframeTicks}
                currentTick={currentTick}
                onSeek={handleSeek}
              />
            </div>
          </>
        )}

        {/* Spacer */}
        <div className="flex-1" />

        {/* Quick Actions */}
        <div className="border-t border-white/10 pt-4 mt-4">
          <div className="text-[10px] font-mono text-white/40 uppercase mb-2">Quick Actions</div>
          <div className="space-y-2">
            <Link href={`/p/${projectId}/universe-map${selectedRun?.node_id ? `?node=${selectedRun.node_id}` : ''}`}>
              <Button variant="ghost" size="sm" className="w-full justify-start text-xs">
                <GitBranch className="w-3 h-3 mr-2" />
                Universe Map
              </Button>
            </Link>
            <Link href={`/p/${projectId}/run-center${selectedRun?.node_id ? `?node=${selectedRun.node_id}` : ''}`}>
              <Button variant="ghost" size="sm" className="w-full justify-start text-xs">
                <Activity className="w-3 h-3 mr-2" />
                Run Center
              </Button>
            </Link>
            <Link href={`/p/${projectId}/reliability${selectedRunId ? `?run=${selectedRunId}` : ''}`}>
              <Button variant="ghost" size="sm" className="w-full justify-start text-xs">
                <BarChart3 className="w-3 h-3 mr-2" />
                Reliability
              </Button>
            </Link>
            <Link href={`/p/${projectId}/reports${selectedRunId ? `?type=run&run=${selectedRunId}` : ''}`}>
              <Button variant="ghost" size="sm" className="w-full justify-start text-xs">
                <FileText className="w-3 h-3 mr-2" />
                Reports
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Main Canvas Area */}
      <div className="flex-1 flex flex-col">
        {/* Toolbar */}
        <div className="h-12 border-b border-white/10 flex items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <button
              onClick={() => handleZoom(0.2)}
              className="p-2 hover:bg-white/10 transition-colors"
              title="Zoom In"
            >
              <ZoomIn className="w-4 h-4 text-white/60" />
            </button>
            <button
              onClick={() => handleZoom(-0.2)}
              className="p-2 hover:bg-white/10 transition-colors"
              title="Zoom Out"
            >
              <ZoomOut className="w-4 h-4 text-white/60" />
            </button>
            <button
              onClick={handleFitView}
              className="p-2 hover:bg-white/10 transition-colors"
              title="Fit to View"
            >
              <Maximize2 className="w-4 h-4 text-white/60" />
            </button>
            <span className="text-xs font-mono text-white/40 ml-2">
              Zoom: {Math.round(zoom * 100)}%
            </span>
          </div>
          <div className="flex items-center gap-2 text-xs font-mono text-white/40">
            <Users className="w-4 h-4" />
            <span>{agentPositions.length} agents</span>
          </div>
        </div>

        {/* Canvas */}
        <div className="flex-1 relative">
          {/* Loading State */}
          {isLoading && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/50 z-10">
              <div className="text-center">
                <Loader2 className="w-8 h-8 text-cyan-400 animate-spin mx-auto mb-2" />
                <p className="text-xs font-mono text-white/60">Loading telemetry data...</p>
              </div>
            </div>
          )}

          {/* Empty State - No Run Selected */}
          {showEmptyState && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center max-w-md">
                <div className="w-20 h-20 bg-white/5 flex items-center justify-center mx-auto mb-4 rounded-full">
                  <Map className="w-10 h-10 text-white/20" />
                </div>
                <h3 className="text-sm font-mono text-white/60 mb-2">Select a Run to Visualize</h3>
                <p className="text-xs font-mono text-white/40 mb-4">
                  Choose a completed simulation run from the selector to view the 2D world replay.
                </p>
                <Link href={`/p/${projectId}/run-center`}>
                  <Button size="sm" variant="secondary" className="text-xs">
                    GO TO RUN CENTER
                  </Button>
                </Link>
              </div>
            </div>
          )}

          {/* No Spatial Telemetry State */}
          {showNoSpatialState && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center max-w-md">
                <div className="w-20 h-20 bg-yellow-500/10 flex items-center justify-center mx-auto mb-4 rounded-full">
                  <Info className="w-10 h-10 text-yellow-400/60" />
                </div>
                <h3 className="text-sm font-mono text-white/60 mb-2">Spatial Replay Not Available</h3>
                <p className="text-xs font-mono text-white/40 mb-4">
                  This run does not contain spatial telemetry data (x, y positions).
                  The simulation may not have included spatial tracking.
                </p>
                <div className="flex gap-3 justify-center">
                  <Link href={`/p/${projectId}/replay?run=${selectedRunId}&tick=${currentTick}`}>
                    <Button size="sm" variant="secondary" className="text-xs">
                      <Activity className="w-3 h-3 mr-2" />
                      View Telemetry Replay
                    </Button>
                  </Link>
                  <Link href={`/p/${projectId}/run-center`}>
                    <Button size="sm" variant="outline" className="text-xs">
                      Run New Simulation
                    </Button>
                  </Link>
                </div>
              </div>
            </div>
          )}

          {/* World Canvas */}
          {hasTelemetry && hasSpatialData && !sliceLoading && (
            <WorldCanvas
              positions={agentPositions}
              bounds={bounds}
              selectedAgentId={selectedAgentId}
              onSelectAgent={setSelectedAgentId}
              zoom={zoom}
              pan={pan}
              onZoom={handleZoom}
              onPan={setPan}
            />
          )}

          {/* Coordinate Display */}
          <div className="absolute bottom-3 left-3 px-2 py-1 bg-black/80 text-[10px] font-mono text-white/40">
            Pan: ({pan.x.toFixed(0)}, {pan.y.toFixed(0)})
          </div>
        </div>

        {/* Footer */}
        <div className="h-8 border-t border-white/10 flex items-center justify-between px-4 text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-1">
            <Terminal className="w-3 h-3" />
            <span>2D WORLD VIEWER</span>
          </div>
          <span>AGENTVERSE v1.0</span>
        </div>
      </div>

      {/* Agent Inspector Drawer */}
      {selectedAgent && selectedRunId && (
        <AgentInspector
          agent={selectedAgent}
          currentTick={currentTick}
          runId={selectedRunId}
          projectId={projectId}
          onClose={() => setSelectedAgentId(null)}
        />
      )}
    </div>
  );
}

'use client';

/**
 * 2D Replay Player Component
 * Reference: project.md §11 Phase 8, Interaction_design.md §5.17
 *
 * Main container component for the 2D Replay UI.
 * Orchestrates all replay panels: controls, canvas, layers, inspector, timeline.
 *
 * READ-ONLY (C3 Compliant) - Never triggers simulations.
 */

import React, { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import {
  ExternalLink,
  FileText,
  Camera,
  Share2,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useReplayAgentHistory, useReplayEventsAtTick } from '@/hooks/useApi';
import type { LoadReplayRequest } from '@/lib/api';

import { ReplayCanvas, type WorldState, type ZoneDefinition, type LayerVisibility } from './ReplayCanvas';
import { ReplayControls, type TimelineMarker } from './ReplayControls';
import { ReplayLayerPanel } from './ReplayLayerPanel';
import { ReplayInspector } from './ReplayInspector';
import { ReplayTimeline } from './ReplayTimeline';

// Replay timeline data from API
export interface ReplayTimelineData {
  run_id: string;
  node_id?: string;
  total_ticks: number;
  keyframe_ticks: number[];
  event_markers: TimelineMarker[];
  duration_seconds: number;
  tick_rate: number;
  seed_used: number;
  agent_count: number;
  segment_distribution: Record<string, number>;
  region_distribution: Record<string, number>;
  metrics_summary: Record<string, unknown>;
}

interface ReplayPlayerProps {
  // Data props
  timeline: ReplayTimelineData | null;
  worldState: WorldState | null;
  isLoading: boolean;
  error: string | null;
  storageRef: LoadReplayRequest | null; // For fetching agent history and events

  // Callbacks for data fetching
  onLoadReplay?: () => void;
  onSeekToTick?: (tick: number) => void;
  onRetry?: () => void;

  // Navigation callbacks
  onOpenNode?: (nodeId: string) => void;
  onOpenReliability?: (nodeId: string) => void;

  // Optional initial state
  initialTick?: number;

  className?: string;
}

// Default zones for visualization
const DEFAULT_ZONES: ZoneDefinition[] = [
  {
    zone_id: 'supporters',
    name: 'Supporters',
    bounds: { x: 50, y: 50, width: 200, height: 200 },
    segments: ['early_adopter', 'loyal', 'advocate'],
    color: '#22c55e',
  },
  {
    zone_id: 'neutral',
    name: 'Neutral',
    bounds: { x: 300, y: 50, width: 200, height: 200 },
    segments: ['mainstream', 'curious', 'undecided'],
    color: '#64748b',
  },
  {
    zone_id: 'skeptics',
    name: 'Skeptics',
    bounds: { x: 550, y: 50, width: 200, height: 200 },
    segments: ['skeptic', 'resistant', 'antagonist'],
    color: '#ef4444',
  },
  {
    zone_id: 'observers',
    name: 'Observers',
    bounds: { x: 175, y: 300, width: 450, height: 150 },
    segments: ['passive', 'observer', 'default'],
    color: '#3b82f6',
  },
];

export function ReplayPlayer({
  timeline,
  worldState,
  isLoading,
  error,
  storageRef,
  onLoadReplay,
  onSeekToTick,
  onRetry,
  onOpenNode,
  onOpenReliability,
  initialTick = 0,
  className,
}: ReplayPlayerProps) {
  // Playback state
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTick, setCurrentTick] = useState(initialTick);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const playbackRef = useRef<NodeJS.Timeout | null>(null);

  // UI state
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);

  // P8-006: Fetch agent history when an agent is selected
  const { data: agentHistoryData } = useReplayAgentHistory(
    selectedAgentId ?? undefined,
    storageRef,
    { tick_start: 0, tick_end: currentTick }
  );

  // P8-006: Fetch events at current tick
  const { data: tickEventsData } = useReplayEventsAtTick(currentTick, storageRef);

  // Layer visibility
  const [layerVisibility, setLayerVisibility] = useState<LayerVisibility>({
    stance: true,
    emotion: true,
    influence: true,
    exposure: false,
    events: true,
    trails: false,
  });

  // Filters
  const [selectedSegments, setSelectedSegments] = useState<string[]>([]);
  const [selectedRegions, setSelectedRegions] = useState<string[]>([]);

  // Get total ticks
  const totalTicks = timeline?.total_ticks ?? 0;
  const keyframeTicks = timeline?.keyframe_ticks ?? [];
  const eventMarkers = timeline?.event_markers ?? [];

  // Calculate segment stats from world state
  const segmentStats = React.useMemo(() => {
    if (!worldState?.agents) return [];

    const stats: Record<string, { count: number; totalStance: number }> = {};
    Object.values(worldState.agents).forEach(agent => {
      if (!stats[agent.segment]) {
        stats[agent.segment] = { count: 0, totalStance: 0 };
      }
      stats[agent.segment].count += 1;
      stats[agent.segment].totalStance += agent.stance;
    });

    return Object.entries(stats).map(([segment, data]) => ({
      segment,
      count: data.count,
      avgStance: data.totalStance / data.count,
    }));
  }, [worldState?.agents]);

  // Calculate region stats from world state
  const regionStats = React.useMemo(() => {
    if (!worldState?.agents) return [];

    const stats: Record<string, number> = {};
    Object.values(worldState.agents).forEach(agent => {
      const region = agent.region || 'unknown';
      stats[region] = (stats[region] || 0) + 1;
    });

    return Object.entries(stats).map(([region, count]) => ({ region, count }));
  }, [worldState?.agents]);

  // Get selected agent data
  const selectedAgent = selectedAgentId && worldState?.agents
    ? worldState.agents[selectedAgentId]
    : null;

  // P8-006: Transform agent history for ReplayInspector
  const agentHistory = useMemo(() => {
    if (!agentHistoryData?.states) return [];
    return agentHistoryData.states.map(state => ({
      tick: state.tick,
      stance: state.stance,
      emotion: state.emotion,
      influence: state.influence,
    }));
  }, [agentHistoryData]);

  // P8-006: Filter events affecting the selected agent
  const agentEvents = useMemo(() => {
    if (!tickEventsData?.events || !selectedAgentId) return [];

    // Filter events that affect the selected agent
    return tickEventsData.events
      .filter(event => {
        const affectedAgents = event.affected_agents as string[] | undefined;
        // Include events that:
        // 1. Explicitly target this agent
        // 2. Are global events (no specific agents)
        return !affectedAgents || affectedAgents.length === 0 || affectedAgents.includes(selectedAgentId);
      })
      .map(event => ({
        tick: tickEventsData.tick,
        event_type: (event.event_type as string) || 'unknown',
        event_name: (event.event_name as string) || (event.name as string) || 'Event',
        intensity: (event.intensity as number) || 0,
        variables_affected: (event.variables_affected as string[]) || [],
      }));
  }, [tickEventsData, selectedAgentId]);

  // Playback logic
  useEffect(() => {
    if (isPlaying && totalTicks > 0) {
      const interval = 1000 / (10 * playbackSpeed); // Base: 10 ticks per second

      playbackRef.current = setInterval(() => {
        setCurrentTick(prev => {
          const next = prev + 1;
          if (next >= totalTicks) {
            setIsPlaying(false);
            return totalTicks;
          }
          // Trigger seek to fetch new state
          if (onSeekToTick) {
            onSeekToTick(next);
          }
          return next;
        });
      }, interval);

      return () => {
        if (playbackRef.current) {
          clearInterval(playbackRef.current);
        }
      };
    }
  }, [isPlaying, playbackSpeed, totalTicks, onSeekToTick]);

  // Handlers
  const handlePlayPause = useCallback(() => {
    setIsPlaying(prev => !prev);
  }, []);

  const handleSeek = useCallback((tick: number) => {
    const clampedTick = Math.max(0, Math.min(tick, totalTicks));
    setCurrentTick(clampedTick);
    setIsPlaying(false);
    if (onSeekToTick) {
      onSeekToTick(clampedTick);
    }
  }, [totalTicks, onSeekToTick]);

  const handleJumpToKeyframe = useCallback((direction: 'prev' | 'next') => {
    const currentIndex = keyframeTicks.findIndex(t => t >= currentTick);
    let targetTick: number;

    if (direction === 'prev') {
      // Find the keyframe before current
      const prevKeyframes = keyframeTicks.filter(t => t < currentTick);
      targetTick = prevKeyframes.length > 0 ? prevKeyframes[prevKeyframes.length - 1] : 0;
    } else {
      // Find the keyframe after current
      const nextKeyframes = keyframeTicks.filter(t => t > currentTick);
      targetTick = nextKeyframes.length > 0 ? nextKeyframes[0] : totalTicks;
    }

    handleSeek(targetTick);
  }, [currentTick, keyframeTicks, totalTicks, handleSeek]);

  const handleAgentClick = useCallback((agentId: string) => {
    setSelectedAgentId(prev => prev === agentId ? null : agentId);
  }, []);

  const handleToggleFullscreen = useCallback(() => {
    setIsFullscreen(prev => !prev);
  }, []);

  const handleExportSnapshot = useCallback(() => {
    // TODO: Implement canvas export to PNG
    console.log('Export snapshot at tick', currentTick);
  }, [currentTick]);

  // Render loading state
  if (isLoading && !timeline) {
    return (
      <div className={cn('flex items-center justify-center h-full bg-black', className)}>
        <div className="text-center">
          <RefreshCw className="h-8 w-8 mx-auto mb-3 text-cyan-400 animate-spin" />
          <p className="text-white/60 text-sm">Loading replay data...</p>
        </div>
      </div>
    );
  }

  // Render error state
  if (error) {
    return (
      <div className={cn('flex items-center justify-center h-full bg-black', className)}>
        <div className="text-center max-w-md">
          <AlertCircle className="h-8 w-8 mx-auto mb-3 text-red-400" />
          <p className="text-white/80 text-sm mb-2">Replay Unavailable</p>
          <p className="text-white/50 text-xs mb-4">{error}</p>
          {onRetry && (
            <Button variant="outline" size="sm" onClick={onRetry}>
              <RefreshCw className="h-3 w-3 mr-1" />
              Retry
            </Button>
          )}
        </div>
      </div>
    );
  }

  // Render empty state
  if (!timeline) {
    return (
      <div className={cn('flex items-center justify-center h-full bg-black', className)}>
        <div className="text-center max-w-md">
          <AlertCircle className="h-8 w-8 mx-auto mb-3 text-yellow-400" />
          <p className="text-white/80 text-sm mb-2">No Replay Data</p>
          <p className="text-white/50 text-xs mb-4">
            This node does not have telemetry data for replay.
            Re-run the simulation with logging enabled.
          </p>
          {onLoadReplay && (
            <Button variant="outline" size="sm" onClick={onLoadReplay}>
              Load Replay
            </Button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className={cn(
      'flex flex-col h-full bg-black',
      isFullscreen && 'fixed inset-0 z-50',
      className
    )}>
      {/* Top action bar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-white/10 bg-black/90">
        <div className="flex items-center gap-2">
          <span className="text-sm text-white/60">2D Replay</span>
          {timeline.node_id && (
            <span className="text-xs text-cyan-400 font-mono">
              Node: {timeline.node_id.slice(0, 8)}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {timeline.node_id && onOpenNode && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onOpenNode(timeline.node_id!)}
              className="h-7 text-xs text-white/60 hover:text-cyan-400"
            >
              <ExternalLink className="h-3 w-3 mr-1" />
              Open Node
            </Button>
          )}

          {timeline.node_id && onOpenReliability && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onOpenReliability(timeline.node_id!)}
              className="h-7 text-xs text-white/60 hover:text-cyan-400"
            >
              <FileText className="h-3 w-3 mr-1" />
              Reliability
            </Button>
          )}

          <Button
            variant="ghost"
            size="sm"
            onClick={handleExportSnapshot}
            className="h-7 text-xs text-white/60 hover:text-cyan-400"
          >
            <Camera className="h-3 w-3 mr-1" />
            Snapshot
          </Button>

          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs text-white/40"
            disabled
            title="Coming soon"
          >
            <Share2 className="h-3 w-3 mr-1" />
            Share
          </Button>
        </div>
      </div>

      {/* Playback controls */}
      <ReplayControls
        currentTick={currentTick}
        totalTicks={totalTicks}
        isPlaying={isPlaying}
        playbackSpeed={playbackSpeed}
        keyframeTicks={keyframeTicks}
        eventMarkers={eventMarkers}
        onPlayPause={handlePlayPause}
        onSeek={handleSeek}
        onSpeedChange={setPlaybackSpeed}
        onJumpToKeyframe={handleJumpToKeyframe}
        isFullscreen={isFullscreen}
        onToggleFullscreen={handleToggleFullscreen}
      />

      {/* Main content area */}
      <div className="flex-1 flex min-h-0">
        {/* Left layer panel */}
        <ReplayLayerPanel
          visibility={layerVisibility}
          onVisibilityChange={setLayerVisibility}
          segments={segmentStats}
          regions={regionStats}
          selectedSegments={selectedSegments}
          selectedRegions={selectedRegions}
          onSegmentFilter={setSelectedSegments}
          onRegionFilter={setSelectedRegions}
        />

        {/* Center canvas */}
        <div className="flex-1 relative">
          <ReplayCanvas
            worldState={worldState}
            zones={DEFAULT_ZONES}
            layerVisibility={layerVisibility}
            selectedAgentId={selectedAgentId}
            onAgentClick={handleAgentClick}
            zoom={zoom}
            pan={pan}
            onPanChange={setPan}
            className="h-full"
          />

          {/* Zoom controls */}
          <div className="absolute bottom-4 right-4 flex items-center gap-1 bg-black/80 border border-white/10 rounded px-2 py-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setZoom(z => Math.max(0.25, z - 0.25))}
              className="h-6 w-6 p-0 text-white/60"
            >
              -
            </Button>
            <span className="text-xs text-white/60 min-w-[40px] text-center">
              {Math.round(zoom * 100)}%
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setZoom(z => Math.min(4, z + 0.25))}
              className="h-6 w-6 p-0 text-white/60"
            >
              +
            </Button>
          </div>
        </div>

        {/* Right inspector - P8-006: Pass actual agent history and events */}
        <ReplayInspector
          selectedAgent={selectedAgent}
          agentHistory={agentHistory}
          agentEvents={agentEvents}
          onClose={() => setSelectedAgentId(null)}
          currentTick={currentTick}
        />
      </div>

      {/* Bottom timeline */}
      <ReplayTimeline
        currentTick={currentTick}
        totalTicks={totalTicks}
        metrics={[]}
        onSeek={handleSeek}
        height={80}
      />
    </div>
  );
}

'use client';

/**
 * TelemetryReplay Component
 * Main container for simulation telemetry replay.
 * Reference: project.md §6.8 (Telemetry), C3 (read-only replay)
 *
 * IMPORTANT: This is READ-ONLY. It must NEVER trigger new simulations.
 * All data displayed is historical - no mutations allowed.
 */

import { memo, useState, useCallback, useEffect, useMemo } from 'react';
import {
  Activity,
  MessageSquare,
  Play,
  Pause,
  SkipBack,
  Clock,
  Database,
  AlertCircle,
  Loader2,
  RefreshCw,
  Maximize2,
  Minimize2,
  Download,
  Share2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { TelemetryTimeline } from './TelemetryTimeline';
import { TelemetryMetrics } from './TelemetryMetrics';
import { TelemetryEvents } from './TelemetryEvents';
import { useTelemetrySummary, useTelemetryEvents, useExportTelemetry } from '@/hooks/useApi';
import type { EventOccurrence } from '@/lib/api';

interface TelemetryReplayProps {
  runId: string;
  initialTick?: number;
  autoPlay?: boolean;
  className?: string;
}

// Generate tick markers from EventOccurrence events
function generateMarkers(
  events: EventOccurrence[]
): Array<{ tick: number; label: string; color?: string }> {
  // Create markers from events based on intensity
  return events.slice(0, 20).map((e) => ({
    tick: e.start_tick,
    label: `Event ${e.event_id.slice(0, 8)}`,
    color: e.peak_intensity > 0.7
      ? 'rgba(239,68,68,0.6)'
      : e.peak_intensity > 0.4
      ? 'rgba(168,85,247,0.6)'
      : 'rgba(249,115,22,0.6)',
  }));
}

// Convert EventOccurrence to TelemetryEvent format expected by TelemetryEvents component
type EventType = 'info' | 'warning' | 'error' | 'success' | 'action' | 'decision' | 'state_change';

function convertEvents(
  events: EventOccurrence[]
): Array<{ id: string; tick: number; type: EventType; source: string; message: string }> {
  return events.map((e) => ({
    id: e.event_id,
    tick: e.start_tick,
    type: (e.peak_intensity > 0.7 ? 'error' : e.peak_intensity > 0.4 ? 'decision' : 'state_change') as EventType,
    source: 'system',
    message: `Event affecting ${e.affected_agent_count} agents in ${e.affected_regions.join(', ') || 'all regions'}`,
  }));
}

export const TelemetryReplay = memo(function TelemetryReplay({
  runId,
  initialTick = 0,
  autoPlay = false,
  className,
}: TelemetryReplayProps) {
  // State
  const [currentTick, setCurrentTick] = useState(initialTick);
  const [isPlaying, setIsPlaying] = useState(autoPlay);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [activeTab, setActiveTab] = useState<'metrics' | 'events' | 'both'>('both');

  // Fetch telemetry summary
  const {
    data: telemetrySummary,
    isLoading: summaryLoading,
    error: summaryError,
    refetch: refetchSummary,
  } = useTelemetrySummary(runId);

  // Fetch telemetry events
  const {
    data: telemetryEvents = [],
    isLoading: eventsLoading,
    error: eventsError,
  } = useTelemetryEvents(runId);

  // Export mutation
  const exportTelemetry = useExportTelemetry();

  // Combined loading/error state
  const isLoading = summaryLoading || eventsLoading;
  const error = summaryError || eventsError;
  const refetch = refetchSummary;

  // Calculate total ticks from telemetry summary
  const totalTicks = useMemo(() => {
    if (!telemetrySummary) return 0;
    // Use total_ticks from summary, or calculate from events
    const maxEventTick = telemetryEvents.length > 0
      ? Math.max(...telemetryEvents.map((e) => e.end_tick ?? e.start_tick), 0)
      : 0;
    return Math.max(telemetrySummary.total_ticks, maxEventTick);
  }, [telemetrySummary, telemetryEvents]);

  // Convert events to component format
  const convertedEvents = useMemo(() => convertEvents(telemetryEvents), [telemetryEvents]);

  // Generate placeholder metrics from key_metrics
  // In production, this would fetch actual metric data using useTelemetryMetric
  const metrics = useMemo(() => {
    if (!telemetrySummary) return [];
    const metricKeys = Object.keys(telemetrySummary.key_metrics || {});
    return metricKeys.map((metricName, index) => ({
      id: metricName,
      name: metricName.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
      color: ['#06b6d4', '#22c55e', '#eab308', '#ef4444', '#a855f7'][index % 5],
      data: [], // Would be populated by useTelemetryMetric
      visible: true,
    }));
  }, [telemetrySummary]);

  // Generate markers from events
  const markers = useMemo(() => {
    if (telemetryEvents.length === 0) return [];
    return generateMarkers(telemetryEvents);
  }, [telemetryEvents]);

  // Playback timer
  useEffect(() => {
    if (!isPlaying || currentTick >= totalTicks) {
      setIsPlaying(false);
      return;
    }

    const interval = setInterval(() => {
      setCurrentTick((t) => Math.min(t + 1, totalTicks));
    }, 100 / playbackSpeed);

    return () => clearInterval(interval);
  }, [isPlaying, currentTick, totalTicks, playbackSpeed]);

  // Handle tick change from timeline
  const handleTickChange = useCallback((tick: number) => {
    setCurrentTick(tick);
  }, []);

  // Handle play/pause
  const handlePlayPause = useCallback(() => {
    if (currentTick >= totalTicks) {
      setCurrentTick(0);
    }
    setIsPlaying(!isPlaying);
  }, [isPlaying, currentTick, totalTicks]);

  // Handle speed change
  const handleSpeedChange = useCallback((speed: number) => {
    setPlaybackSpeed(speed);
  }, []);

  // Handle jump to tick from event
  const handleJumpToTick = useCallback((tick: number) => {
    setCurrentTick(tick);
    setIsPlaying(false);
  }, []);

  // Handle export
  const handleExport = useCallback(async () => {
    try {
      await exportTelemetry.mutateAsync({
        runId,
        format: 'json',
      });
    } catch {
      // Error handled by mutation
    }
  }, [runId, exportTelemetry]);

  // Handle metric toggle
  const handleMetricToggle = useCallback((metricId: string, visible: boolean) => {
    // This would update local state or call API to save preference
    console.log(`Toggle metric ${metricId}: ${visible}`);
  }, []);

  // Error state
  if (error) {
    return (
      <div className={cn('flex items-center justify-center p-12 bg-black border border-white/10', className)}>
        <div className="text-center">
          <AlertCircle className="w-8 h-8 text-red-400 mx-auto mb-3" />
          <p className="text-sm font-mono text-red-400 mb-2">
            Failed to load telemetry data
          </p>
          <Button variant="secondary" size="sm" onClick={() => refetch()}>
            <RefreshCw className="w-3 h-3 mr-1" />
            Retry
          </Button>
        </div>
      </div>
    );
  }

  // Loading state
  if (isLoading) {
    return (
      <div className={cn('flex items-center justify-center p-12 bg-black border border-white/10', className)}>
        <div className="flex items-center gap-3 text-white/40">
          <Loader2 className="w-5 h-5 animate-spin" />
          <span className="text-sm font-mono">Loading telemetry...</span>
        </div>
      </div>
    );
  }

  // Empty state
  if (!telemetrySummary) {
    return (
      <div className={cn('flex items-center justify-center p-12 bg-black border border-white/10', className)}>
        <div className="text-center">
          <Database className="w-8 h-8 text-white/20 mx-auto mb-3" />
          <p className="text-sm font-mono text-white/40">No telemetry data available</p>
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'flex flex-col bg-black',
        isFullscreen && 'fixed inset-0 z-50',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-cyan-500/10">
            <Activity className="w-5 h-5 text-cyan-400" />
          </div>
          <div>
            <h2 className="text-lg font-mono font-bold text-white">
              Telemetry Replay
            </h2>
            <div className="flex items-center gap-3 text-xs font-mono text-white/40">
              <span>Run: {runId.slice(0, 12)}...</span>
              <span>|</span>
              <span>{totalTicks} ticks</span>
              <span>|</span>
              <span>{metrics.length} metrics</span>
              <span>|</span>
              <span>{telemetryEvents.length} events</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Tab selector */}
          <div className="flex items-center bg-white/5 border border-white/10">
            <button
              onClick={() => setActiveTab('metrics')}
              className={cn(
                'px-3 py-1.5 text-xs font-mono transition-colors',
                activeTab === 'metrics'
                  ? 'bg-white text-black'
                  : 'text-white/60 hover:text-white'
              )}
            >
              <Activity className="w-3 h-3 inline mr-1" />
              Metrics
            </button>
            <button
              onClick={() => setActiveTab('events')}
              className={cn(
                'px-3 py-1.5 text-xs font-mono transition-colors',
                activeTab === 'events'
                  ? 'bg-white text-black'
                  : 'text-white/60 hover:text-white'
              )}
            >
              <MessageSquare className="w-3 h-3 inline mr-1" />
              Events
            </button>
            <button
              onClick={() => setActiveTab('both')}
              className={cn(
                'px-3 py-1.5 text-xs font-mono transition-colors',
                activeTab === 'both'
                  ? 'bg-white text-black'
                  : 'text-white/60 hover:text-white'
              )}
            >
              Both
            </button>
          </div>

          <Button
            variant="ghost"
            size="icon-sm"
            onClick={handleExport}
            disabled={exportTelemetry.isPending}
            title="Export telemetry"
          >
            <Download className="w-3.5 h-3.5" />
          </Button>

          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => setIsFullscreen(!isFullscreen)}
            title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
          >
            {isFullscreen ? (
              <Minimize2 className="w-3.5 h-3.5" />
            ) : (
              <Maximize2 className="w-3.5 h-3.5" />
            )}
          </Button>
        </div>
      </div>

      {/* Timeline */}
      <div className="px-4 py-3 border-b border-white/10">
        <TelemetryTimeline
          currentTick={currentTick}
          totalTicks={totalTicks}
          onTickChange={handleTickChange}
          isPlaying={isPlaying}
          onPlayPause={handlePlayPause}
          playbackSpeed={playbackSpeed}
          onSpeedChange={handleSpeedChange}
          markers={markers}
        />
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'both' ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 h-full divide-y lg:divide-y-0 lg:divide-x divide-white/10">
            {/* Metrics Panel */}
            <div className="p-4 overflow-y-auto">
              <TelemetryMetrics
                metrics={metrics}
                currentTick={currentTick}
                totalTicks={totalTicks}
                onMetricToggle={handleMetricToggle}
                height={250}
              />
            </div>

            {/* Events Panel */}
            <div className="p-4 overflow-hidden flex flex-col">
              <TelemetryEvents
                events={convertedEvents}
                currentTick={currentTick}
                onJumpToTick={handleJumpToTick}
                className="flex-1"
              />
            </div>
          </div>
        ) : activeTab === 'metrics' ? (
          <div className="p-4 h-full overflow-y-auto">
            <TelemetryMetrics
              metrics={metrics}
              currentTick={currentTick}
              totalTicks={totalTicks}
              onMetricToggle={handleMetricToggle}
              height={400}
            />
          </div>
        ) : (
          <div className="p-4 h-full overflow-hidden flex flex-col">
            <TelemetryEvents
              events={convertedEvents}
              currentTick={currentTick}
              onJumpToTick={handleJumpToTick}
              className="flex-1"
            />
          </div>
        )}
      </div>

      {/* Footer Status Bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-black/50 border-t border-white/10">
        <div className="flex items-center gap-4 text-[10px] font-mono text-white/40">
          <div className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            <span>
              Tick {currentTick} / {totalTicks}
            </span>
          </div>
          <div className="flex items-center gap-1">
            {isPlaying ? (
              <>
                <Play className="w-3 h-3 text-green-400" />
                <span className="text-green-400">Playing {playbackSpeed}x</span>
              </>
            ) : (
              <>
                <Pause className="w-3 h-3" />
                <span>Paused</span>
              </>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="px-2 py-1 bg-blue-500/10 border border-blue-500/20">
            <span className="text-[10px] font-mono text-blue-400">
              READ-ONLY REPLAY MODE
            </span>
          </div>
        </div>
      </div>
    </div>
  );
});

export default TelemetryReplay;

'use client';

/**
 * Telemetry Viewer Page
 * Spec-compliant read-only telemetry replay and analysis
 * Reference: project.md §6.8 (Telemetry), C3 (replay read-only)
 */

import { useState, useEffect, useMemo, useCallback } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import {
  BarChart3,
  Play,
  Pause,
  SkipBack,
  SkipForward,
  FastForward,
  Loader2,
  ArrowLeft,
  Activity,
  Users,
  Clock,
  Terminal,
  RefreshCw,
  AlertTriangle,
  Layers,
  GitBranch,
  Zap,
  Target,
  TrendingUp,
  TrendingDown,
  Minus,
  ChevronDown,
  ChevronUp,
  Eye,
  Database,
} from 'lucide-react';
import {
  useRun,
  useTelemetryIndex,
  useTelemetrySummary,
  useTelemetrySlice,
  useTelemetryMetric,
  useTelemetryEvents,
} from '@/hooks/useApi';
import { cn } from '@/lib/utils';
import type { TelemetrySummary, TelemetrySlice, TelemetryKeyframe, TelemetryDeltaItem, TelemetryIndex, EventOccurrence } from '@/lib/api';

// Playback speeds
const PLAYBACK_SPEEDS = [0.5, 1, 2, 4, 8];

export default function TelemetryPage() {
  const params = useParams();
  const router = useRouter();
  const runId = params.id as string;

  // State
  const [currentTick, setCurrentTick] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [selectedMetric, setSelectedMetric] = useState<string>('');
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    metrics: true,
    agents: true,
    events: true,
    deltas: false,
  });

  // Fetch run details
  const { data: run, isLoading: runLoading, error: runError } = useRun(runId);

  // Fetch telemetry data
  const { data: summary, isLoading: summaryLoading } = useTelemetrySummary(runId);
  const { data: index } = useTelemetryIndex(runId);
  const { data: slice } = useTelemetrySlice(runId, currentTick);
  const { data: events } = useTelemetryEvents(runId);

  // Fetch selected metric
  const { data: metricData } = useTelemetryMetric(
    runId,
    selectedMetric || (index?.metric_keys?.[0] || ''),
    { start_tick: 0, end_tick: summary?.total_ticks || 100 }
  );

  // Set default metric when index loads
  useEffect(() => {
    if (index?.metric_keys && index.metric_keys.length > 0 && !selectedMetric) {
      setSelectedMetric(index.metric_keys[0]);
    }
  }, [index, selectedMetric]);

  // Playback timer
  useEffect(() => {
    if (!isPlaying || !summary) return;

    const interval = setInterval(() => {
      setCurrentTick((prev) => {
        if (prev >= summary.total_ticks - 1) {
          setIsPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, 1000 / playbackSpeed);

    return () => clearInterval(interval);
  }, [isPlaying, playbackSpeed, summary]);

  // Handlers
  const handlePlayPause = useCallback(() => setIsPlaying(!isPlaying), [isPlaying]);
  const handleSkipStart = useCallback(() => { setCurrentTick(0); setIsPlaying(false); }, []);
  const handleSkipEnd = useCallback(() => {
    if (summary) {
      setCurrentTick(summary.total_ticks - 1);
      setIsPlaying(false);
    }
  }, [summary]);
  const handleSpeedChange = useCallback(() => {
    setPlaybackSpeed((prev) => {
      const idx = PLAYBACK_SPEEDS.indexOf(prev);
      return PLAYBACK_SPEEDS[(idx + 1) % PLAYBACK_SPEEDS.length];
    });
  }, []);

  const toggleSection = useCallback((section: string) => {
    setExpandedSections((prev) => ({ ...prev, [section]: !prev[section] }));
  }, []);

  // Calculate progress
  const progress = summary ? (currentTick / (summary.total_ticks - 1)) * 100 : 0;

  // Loading state
  const isLoading = runLoading || summaryLoading;

  if (isLoading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-cyan-400" />
      </div>
    );
  }

  if (runError || !run) {
    return (
      <div className="min-h-screen bg-black p-6">
        <div className="bg-red-500/10 border border-red-500/30 p-6 max-w-md mx-auto mt-12">
          <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-4" />
          <p className="text-sm font-mono text-red-400 text-center mb-4">
            Failed to load telemetry data
          </p>
          <div className="flex justify-center gap-2">
            <Button variant="secondary" size="sm" onClick={() => router.back()}>
              GO BACK
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <Link
            href={`/dashboard/runs/${runId}`}
            className="flex items-center gap-1 text-xs font-mono text-white/40 hover:text-white mb-2"
          >
            <ArrowLeft className="w-3 h-3" />
            Back to Run
          </Link>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-cyan-500/10 border border-cyan-500/30">
              <BarChart3 className="w-5 h-5 text-cyan-400" />
            </div>
            <div>
              <h1 className="text-xl font-mono font-bold text-white">
                Telemetry Viewer
              </h1>
              <p className="text-xs font-mono text-white/40">
                Run: {runId.slice(0, 16)}...
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {run.node_id && (
            <Link href={`/dashboard/nodes/${run.node_id}`}>
              <Button variant="secondary" size="sm">
                <GitBranch className="w-3 h-3 mr-2" />
                VIEW NODE
              </Button>
            </Link>
          )}
        </div>
      </div>

      {/* Read-Only Notice */}
      <div className="bg-blue-500/10 border border-blue-500/30 p-4 mb-6">
        <div className="flex items-center gap-2">
          <Eye className="w-4 h-4 text-blue-400" />
          <span className="text-sm font-mono text-blue-400">
            READ-ONLY MODE: Telemetry replay does not trigger simulations (C3 compliant)
          </span>
        </div>
      </div>

      {/* Summary Stats */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-6">
          <div className="bg-white/5 border border-white/10 p-4">
            <div className="flex items-center gap-2 mb-2">
              <Clock className="w-4 h-4 text-cyan-400" />
              <span className="text-xs font-mono text-white/40">Ticks</span>
            </div>
            <span className="text-xl font-mono font-bold text-white">
              {summary.total_ticks}
            </span>
          </div>

          <div className="bg-white/5 border border-white/10 p-4">
            <div className="flex items-center gap-2 mb-2">
              <Layers className="w-4 h-4 text-purple-400" />
              <span className="text-xs font-mono text-white/40">Keyframes</span>
            </div>
            <span className="text-xl font-mono font-bold text-white">
              {index?.keyframe_ticks?.length || 0}
            </span>
          </div>

          <div className="bg-white/5 border border-white/10 p-4">
            <div className="flex items-center gap-2 mb-2">
              <Zap className="w-4 h-4 text-yellow-400" />
              <span className="text-xs font-mono text-white/40">Events</span>
            </div>
            <span className="text-xl font-mono font-bold text-white">
              {summary.total_events}
            </span>
          </div>

          <div className="bg-white/5 border border-white/10 p-4">
            <div className="flex items-center gap-2 mb-2">
              <Users className="w-4 h-4 text-green-400" />
              <span className="text-xs font-mono text-white/40">Agents</span>
            </div>
            <span className="text-xl font-mono font-bold text-white">
              {summary.total_agents}
            </span>
          </div>

          <div className="bg-white/5 border border-white/10 p-4">
            <div className="flex items-center gap-2 mb-2">
              <Activity className="w-4 h-4 text-orange-400" />
              <span className="text-xs font-mono text-white/40">Metrics</span>
            </div>
            <span className="text-xl font-mono font-bold text-white">
              {index?.metric_keys?.length || 0}
            </span>
          </div>

          <div className="bg-white/5 border border-white/10 p-4">
            <div className="flex items-center gap-2 mb-2">
              <Database className="w-4 h-4 text-blue-400" />
              <span className="text-xs font-mono text-white/40">Size</span>
            </div>
            <span className="text-xl font-mono font-bold text-white">
              {((index?.storage_ref?.size_bytes || 0) / 1024).toFixed(1)} KB
            </span>
          </div>
        </div>
      )}

      {/* Playback Controls */}
      <div className="bg-white/5 border border-white/10 p-4 mb-6">
        <div className="flex items-center gap-4 mb-4">
          <div className="flex items-center gap-1">
            <Button
              variant="secondary"
              size="icon-sm"
              onClick={handleSkipStart}
              disabled={currentTick === 0}
            >
              <SkipBack className="w-4 h-4" />
            </Button>
            <Button
              variant={isPlaying ? 'secondary' : 'primary'}
              size="icon-sm"
              onClick={handlePlayPause}
            >
              {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            </Button>
            <Button
              variant="secondary"
              size="icon-sm"
              onClick={handleSkipEnd}
              disabled={currentTick >= (summary?.total_ticks || 1) - 1}
            >
              <SkipForward className="w-4 h-4" />
            </Button>
          </div>

          <Button
            variant="secondary"
            size="sm"
            onClick={handleSpeedChange}
            className="min-w-[60px]"
          >
            <FastForward className="w-3 h-3 mr-1" />
            {playbackSpeed}x
          </Button>

          <div className="flex-1">
            <input
              type="range"
              min={0}
              max={(summary?.total_ticks || 1) - 1}
              value={currentTick}
              onChange={(e) => setCurrentTick(parseInt(e.target.value))}
              className="w-full h-2 bg-white/10 appearance-none cursor-pointer"
            />
          </div>

          <div className="text-sm font-mono text-white/60 min-w-[100px] text-right">
            Tick {currentTick} / {(summary?.total_ticks || 1) - 1}
          </div>
        </div>

        {/* Progress Bar */}
        <div className="w-full bg-white/10 h-1">
          <div
            className="h-1 bg-cyan-500 transition-all duration-100"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Slice Data */}
        <div className="lg:col-span-2 space-y-6">
          {/* Current Keyframe State */}
          {slice?.keyframes && slice.keyframes.length > 0 && (
            <div className="bg-white/5 border border-white/10 p-6">
              <div className="flex items-center gap-2 mb-4">
                <Target className="w-5 h-5 text-cyan-400" />
                <span className="text-lg font-mono font-bold text-white">
                  State @ Tick {slice.keyframes[0].tick}
                </span>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {/* Agent Count */}
                <div className="bg-black/30 p-4">
                  <span className="text-xs font-mono text-white/40 block mb-2">Agents in Frame</span>
                  <span className="text-2xl font-mono font-bold text-white">
                    {Object.keys(slice.keyframes[0].agent_states || {}).length}
                  </span>
                </div>

                {/* Event Count */}
                <div className="bg-black/30 p-4">
                  <span className="text-xs font-mono text-white/40 block mb-2">Events</span>
                  <span className="text-2xl font-mono font-bold text-white">
                    {slice.keyframes[0].event_count || 0}
                  </span>
                </div>

                {/* Metrics if available */}
                {slice.keyframes[0].metrics && Object.entries(slice.keyframes[0].metrics).slice(0, 4).map(([key, value]) => (
                  <div key={key} className="bg-black/30 p-4">
                    <span className="text-xs font-mono text-white/40 block mb-2 truncate">
                      {key}
                    </span>
                    <span className="text-2xl font-mono font-bold text-white">
                      {typeof value === 'number' ? value.toFixed(2) : String(value)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Deltas Section */}
          <div className="bg-white/5 border border-white/10">
            <button
              onClick={() => toggleSection('deltas')}
              className="w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors"
            >
              <div className="flex items-center gap-2">
                <Zap className="w-5 h-5 text-yellow-400" />
                <span className="text-lg font-mono font-bold text-white">
                  Deltas ({slice?.deltas?.length || 0})
                </span>
              </div>
              {expandedSections.deltas ? (
                <ChevronUp className="w-5 h-5 text-white/40" />
              ) : (
                <ChevronDown className="w-5 h-5 text-white/40" />
              )}
            </button>

            {expandedSections.deltas && slice?.deltas && slice.deltas.length > 0 && (
              <div className="border-t border-white/10 max-h-80 overflow-y-auto">
                {slice.deltas.map((delta, index) => (
                  <div
                    key={index}
                    className="px-4 py-3 border-b border-white/5 hover:bg-white/5"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-mono text-cyan-400">
                        Tick {delta.tick}
                      </span>
                      <span className="text-[10px] font-mono text-white/30">
                        {delta.agent_updates?.length || 0} updates
                      </span>
                    </div>
                    {delta.events_triggered && delta.events_triggered.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {delta.events_triggered.map((evt, i) => (
                          <span key={i} className="px-1.5 py-0.5 bg-orange-500/20 text-orange-400 text-[10px] font-mono">
                            {evt}
                          </span>
                        ))}
                      </div>
                    )}
                    {delta.metrics && (
                      <p className="text-xs font-mono text-white/60 mt-1">
                        Active: {delta.metrics.active_agents} / {delta.metrics.total_agents}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Metrics Chart Placeholder */}
          {metricData && (
            <div className="bg-white/5 border border-white/10 p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Activity className="w-5 h-5 text-purple-400" />
                  <span className="text-lg font-mono font-bold text-white">
                    Metric: {selectedMetric}
                  </span>
                </div>
                {index?.metric_keys && (
                  <select
                    value={selectedMetric}
                    onChange={(e) => setSelectedMetric(e.target.value)}
                    className="px-3 py-1.5 bg-black border border-white/10 text-xs font-mono text-white appearance-none focus:outline-none focus:border-cyan-500/50"
                  >
                    {index.metric_keys.map((metric) => (
                      <option key={metric} value={metric}>
                        {metric}
                      </option>
                    ))}
                  </select>
                )}
              </div>

              {/* Simple metric visualization */}
              <div className="h-40 flex items-end gap-px">
                {metricData.data_points.slice(-50).map((point, index) => {
                  const max = Math.max(...metricData.data_points.map(p => p.value));
                  const height = max > 0 ? (point.value / max) * 100 : 0;
                  const isCurrentTick = point.tick === currentTick;
                  return (
                    <div
                      key={index}
                      className={cn(
                        'flex-1 transition-all',
                        isCurrentTick ? 'bg-cyan-400' : 'bg-purple-500/60'
                      )}
                      style={{ height: `${height}%` }}
                      title={`Tick ${point.tick}: ${point.value.toFixed(2)}`}
                    />
                  );
                })}
              </div>

              <div className="flex justify-between mt-2 text-[10px] font-mono text-white/30">
                <span>Recent 50 ticks</span>
                <span>Current: {metricData.data_points.find(p => p.tick === currentTick)?.value?.toFixed(2) || '-'}</span>
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Events & Info */}
        <div className="space-y-6">
          {/* Events Section */}
          <div className="bg-white/5 border border-white/10">
            <button
              onClick={() => toggleSection('events')}
              className="w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors"
            >
              <div className="flex items-center gap-2">
                <Zap className="w-5 h-5 text-orange-400" />
                <span className="text-sm font-mono font-bold text-white">
                  Events ({events?.length || 0})
                </span>
              </div>
              {expandedSections.events ? (
                <ChevronUp className="w-4 h-4 text-white/40" />
              ) : (
                <ChevronDown className="w-4 h-4 text-white/40" />
              )}
            </button>

            {expandedSections.events && events && events.length > 0 && (
              <div className="border-t border-white/10 max-h-60 overflow-y-auto">
                {events.map((event: EventOccurrence, idx: number) => {
                  const isActive = event.start_tick <= currentTick &&
                    (!event.end_tick || event.end_tick >= currentTick);
                  return (
                    <div
                      key={event.event_id || idx}
                      className={cn(
                        'px-4 py-3 border-b border-white/5',
                        isActive && 'bg-orange-500/10'
                      )}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className={cn(
                          'text-xs font-mono',
                          isActive ? 'text-orange-400' : 'text-white/60'
                        )}>
                          {event.event_id}
                        </span>
                        {isActive && (
                          <span className="px-1.5 py-0.5 bg-orange-500/20 text-orange-400 text-[10px] font-mono">
                            ACTIVE
                          </span>
                        )}
                      </div>
                      <p className="text-[10px] font-mono text-white/40">
                        Ticks: {event.start_tick} - {event.end_tick || 'ongoing'}
                      </p>
                      <p className="text-[10px] font-mono text-white/30">
                        Affected: {event.affected_agent_count || 0} agents | Intensity: {event.peak_intensity?.toFixed(2) || '-'}
                      </p>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Available Metrics */}
          {index?.metric_keys && (
            <div className="bg-white/5 border border-white/10 p-4">
              <div className="flex items-center gap-2 mb-3">
                <Activity className="w-4 h-4 text-white/40" />
                <span className="text-xs font-mono text-white/40 uppercase">
                  Available Metrics
                </span>
              </div>
              <div className="space-y-1 max-h-40 overflow-y-auto">
                {index.metric_keys.map((metric) => (
                  <button
                    key={metric}
                    onClick={() => setSelectedMetric(metric)}
                    className={cn(
                      'w-full text-left px-2 py-1.5 text-xs font-mono transition-colors',
                      selectedMetric === metric
                        ? 'bg-cyan-500/20 text-cyan-400'
                        : 'text-white/60 hover:bg-white/5'
                    )}
                  >
                    {metric}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Agent IDs */}
          {index?.agent_ids && index.agent_ids.length > 0 && (
            <div className="bg-white/5 border border-white/10 p-4">
              <div className="flex items-center gap-2 mb-3">
                <Users className="w-4 h-4 text-white/40" />
                <span className="text-xs font-mono text-white/40 uppercase">
                  Tracked Agents ({index.agent_ids.length})
                </span>
              </div>
              <div className="space-y-1 max-h-40 overflow-y-auto">
                {index.agent_ids.slice(0, 20).map((agentId) => (
                  <div
                    key={agentId}
                    className="text-xs font-mono text-white/60 px-2 py-1 hover:bg-white/5"
                  >
                    {agentId.slice(0, 24)}...
                  </div>
                ))}
                {index.agent_ids.length > 20 && (
                  <div className="text-xs font-mono text-white/30 px-2 py-1">
                    +{index.agent_ids.length - 20} more
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="mt-8 pt-4 border-t border-white/5">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1">
              <Terminal className="w-3 h-3" />
              <span>TELEMETRY VIEWER</span>
            </div>
            <div className="flex items-center gap-1">
              <Eye className="w-3 h-3" />
              <span>C3: REPLAY READ-ONLY</span>
            </div>
          </div>
          <span>project.md §6.8</span>
        </div>
      </div>
    </div>
  );
}

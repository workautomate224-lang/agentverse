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
import type { TelemetrySummary, TelemetrySlice, MetricTimeSeries, EventOccurrence } from '@/lib/api';

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
    selectedMetric || (index?.available_metrics?.[0] || ''),
    { start_tick: 0, end_tick: summary?.tick_count || 100 }
  );

  // Set default metric when index loads
  useEffect(() => {
    if (index?.available_metrics && index.available_metrics.length > 0 && !selectedMetric) {
      setSelectedMetric(index.available_metrics[0]);
    }
  }, [index, selectedMetric]);

  // Playback timer
  useEffect(() => {
    if (!isPlaying || !summary) return;

    const interval = setInterval(() => {
      setCurrentTick((prev) => {
        if (prev >= summary.tick_count - 1) {
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
      setCurrentTick(summary.tick_count - 1);
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
  const progress = summary ? (currentTick / (summary.tick_count - 1)) * 100 : 0;

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
              {summary.tick_count}
            </span>
          </div>

          <div className="bg-white/5 border border-white/10 p-4">
            <div className="flex items-center gap-2 mb-2">
              <Layers className="w-4 h-4 text-purple-400" />
              <span className="text-xs font-mono text-white/40">Keyframes</span>
            </div>
            <span className="text-xl font-mono font-bold text-white">
              {summary.keyframe_count}
            </span>
          </div>

          <div className="bg-white/5 border border-white/10 p-4">
            <div className="flex items-center gap-2 mb-2">
              <Zap className="w-4 h-4 text-yellow-400" />
              <span className="text-xs font-mono text-white/40">Deltas</span>
            </div>
            <span className="text-xl font-mono font-bold text-white">
              {summary.delta_count}
            </span>
          </div>

          <div className="bg-white/5 border border-white/10 p-4">
            <div className="flex items-center gap-2 mb-2">
              <Users className="w-4 h-4 text-green-400" />
              <span className="text-xs font-mono text-white/40">Agents</span>
            </div>
            <span className="text-xl font-mono font-bold text-white">
              {summary.tracked_agents}
            </span>
          </div>

          <div className="bg-white/5 border border-white/10 p-4">
            <div className="flex items-center gap-2 mb-2">
              <Activity className="w-4 h-4 text-orange-400" />
              <span className="text-xs font-mono text-white/40">Metrics</span>
            </div>
            <span className="text-xl font-mono font-bold text-white">
              {summary.available_metrics?.length || 0}
            </span>
          </div>

          <div className="bg-white/5 border border-white/10 p-4">
            <div className="flex items-center gap-2 mb-2">
              <Database className="w-4 h-4 text-blue-400" />
              <span className="text-xs font-mono text-white/40">Size</span>
            </div>
            <span className="text-xl font-mono font-bold text-white">
              {(summary.size_bytes / 1024).toFixed(1)} KB
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
              disabled={currentTick >= (summary?.tick_count || 1) - 1}
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
              max={(summary?.tick_count || 1) - 1}
              value={currentTick}
              onChange={(e) => setCurrentTick(parseInt(e.target.value))}
              className="w-full h-2 bg-white/10 appearance-none cursor-pointer"
            />
          </div>

          <div className="text-sm font-mono text-white/60 min-w-[100px] text-right">
            Tick {currentTick} / {(summary?.tick_count || 1) - 1}
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
          {/* World State */}
          {slice?.world_keyframe && (
            <div className="bg-white/5 border border-white/10 p-6">
              <div className="flex items-center gap-2 mb-4">
                <Target className="w-5 h-5 text-cyan-400" />
                <span className="text-lg font-mono font-bold text-white">
                  World State @ Tick {slice.tick}
                </span>
                {slice.is_interpolated && (
                  <span className="px-2 py-0.5 bg-yellow-500/20 text-yellow-400 text-[10px] font-mono uppercase">
                    Interpolated
                  </span>
                )}
              </div>

              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {/* Agent Counts */}
                <div className="bg-black/30 p-4">
                  <span className="text-xs font-mono text-white/40 block mb-2">Total Agents</span>
                  <span className="text-2xl font-mono font-bold text-white">
                    {slice.world_keyframe.agent_counts.total}
                  </span>
                  <span className="text-xs font-mono text-green-400 ml-2">
                    ({slice.world_keyframe.agent_counts.active} active)
                  </span>
                </div>

                {/* Global Metrics */}
                {Object.entries(slice.world_keyframe.global_metrics).slice(0, 5).map(([key, value]) => (
                  <div key={key} className="bg-black/30 p-4">
                    <span className="text-xs font-mono text-white/40 block mb-2 truncate">
                      {key}
                    </span>
                    <span className="text-2xl font-mono font-bold text-white">
                      {typeof value === 'number' ? value.toFixed(2) : value}
                    </span>
                  </div>
                ))}
              </div>

              {/* Active Events */}
              {slice.world_keyframe.active_events.length > 0 && (
                <div className="mt-4 pt-4 border-t border-white/10">
                  <span className="text-xs font-mono text-white/40 block mb-2">Active Events</span>
                  <div className="flex flex-wrap gap-2">
                    {slice.world_keyframe.active_events.map((event, index) => (
                      <span
                        key={index}
                        className="px-2 py-1 bg-orange-500/20 text-orange-400 text-xs font-mono"
                      >
                        {event}
                      </span>
                    ))}
                  </div>
                </div>
              )}
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
                    key={delta.delta_id || index}
                    className="px-4 py-3 border-b border-white/5 hover:bg-white/5"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-mono text-cyan-400">
                        {delta.delta_type}
                      </span>
                      {delta.target_id && (
                        <span className="text-[10px] font-mono text-white/30">
                          Target: {delta.target_id.slice(0, 8)}
                        </span>
                      )}
                    </div>
                    {delta.field_path && (
                      <p className="text-xs font-mono text-white/60">
                        {delta.field_path}: {JSON.stringify(delta.old_value)} → {JSON.stringify(delta.new_value)}
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
                {index?.available_metrics && (
                  <select
                    value={selectedMetric}
                    onChange={(e) => setSelectedMetric(e.target.value)}
                    className="px-3 py-1.5 bg-black border border-white/10 text-xs font-mono text-white appearance-none focus:outline-none focus:border-cyan-500/50"
                  >
                    {index.available_metrics.map((metric) => (
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
                {events.map((event: EventOccurrence, index) => {
                  const isActive = event.start_tick <= currentTick &&
                    (!event.end_tick || event.end_tick >= currentTick);
                  return (
                    <div
                      key={event.event_id || index}
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
                        {event.affected_agent_count} agents affected
                      </p>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Available Metrics */}
          {index?.available_metrics && (
            <div className="bg-white/5 border border-white/10 p-4">
              <div className="flex items-center gap-2 mb-3">
                <Activity className="w-4 h-4 text-white/40" />
                <span className="text-xs font-mono text-white/40 uppercase">
                  Available Metrics
                </span>
              </div>
              <div className="space-y-1 max-h-40 overflow-y-auto">
                {index.available_metrics.map((metric) => (
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

          {/* Segment Breakdown */}
          {slice?.world_keyframe?.agent_counts?.by_segment && (
            <div className="bg-white/5 border border-white/10 p-4">
              <div className="flex items-center gap-2 mb-3">
                <Users className="w-4 h-4 text-white/40" />
                <span className="text-xs font-mono text-white/40 uppercase">
                  Agents by Segment
                </span>
              </div>
              <div className="space-y-2">
                {Object.entries(slice.world_keyframe.agent_counts.by_segment).map(([segment, count]) => {
                  const total = slice.world_keyframe?.agent_counts?.total || 1;
                  const percent = ((count as number) / total) * 100;
                  return (
                    <div key={segment}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-mono text-white/60">{segment}</span>
                        <span className="text-xs font-mono text-white">{count as number}</span>
                      </div>
                      <div className="w-full bg-white/10 h-1">
                        <div
                          className="h-1 bg-green-500"
                          style={{ width: `${percent}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
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

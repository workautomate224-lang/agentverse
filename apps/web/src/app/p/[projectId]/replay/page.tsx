'use client';

/**
 * Telemetry & Replay Page
 * Watch simulation replays and explore telemetry data (read-only per C3)
 */

import { useState, useEffect, useCallback } from 'react';
import { useParams, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  Activity,
  ArrowLeft,
  ArrowRight,
  Terminal,
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Clock,
  Users,
  TrendingUp,
  Settings,
  Loader2,
  AlertCircle,
  RefreshCw,
  ChevronDown,
  CheckCircle,
  Zap,
  FileText,
  Map,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  useRuns,
  useTelemetryIndex,
  useTelemetrySummary,
  useTelemetrySlice,
} from '@/hooks/useApi';
import type { RunSummary, TelemetryIndex, TelemetrySummary, TelemetrySlice } from '@/lib/api';
import { GuidancePanel } from '@/components/pil';

// Format date for display
function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

// Run selector dropdown component
function RunSelector({
  runs,
  selectedRunId,
  onSelectRun,
  isLoading,
}: {
  runs: RunSummary[] | undefined;
  selectedRunId: string | null;
  onSelectRun: (runId: string) => void;
  isLoading: boolean;
}) {
  const [isOpen, setIsOpen] = useState(false);

  // Filter to only runs with status=succeeded (telemetry available for succeeded runs)
  const completedRuns = runs?.filter((r) => r.status === 'succeeded') || [];
  const selectedRun = completedRuns.find((r) => r.run_id === selectedRunId);

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={isLoading || completedRuns.length === 0}
        className={cn(
          'w-full px-3 py-2 bg-black border border-white/10 text-left flex items-center justify-between transition-colors',
          'hover:border-white/30 focus:outline-none focus:border-cyan-500/50',
          (isLoading || completedRuns.length === 0) && 'opacity-50 cursor-not-allowed'
        )}
      >
        <span className="text-sm font-mono text-white/60 truncate">
          {isLoading ? (
            'Loading runs...'
          ) : selectedRun ? (
            <span className="text-white">
              Run {selectedRun.run_id.slice(0, 8)}... - {formatDate(selectedRun.created_at)}
            </span>
          ) : completedRuns.length === 0 ? (
            'No completed runs available'
          ) : (
            'Select a run to replay'
          )}
        </span>
        <ChevronDown className={cn('w-4 h-4 text-white/40 transition-transform', isOpen && 'rotate-180')} />
      </button>

      {isOpen && completedRuns.length > 0 && (
        <div className="absolute z-50 top-full left-0 right-0 mt-1 bg-black border border-white/10 max-h-60 overflow-y-auto">
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

// Playback speed options
const PLAYBACK_SPEEDS = [0.5, 1, 2, 4];

export default function TelemetryReplayPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const projectId = params.projectId as string;

  // Get run ID from URL if provided
  const urlRunId = searchParams.get('run');

  // Playback state
  const [selectedRunId, setSelectedRunId] = useState<string | null>(urlRunId);
  const [currentTick, setCurrentTick] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);

  // API hooks
  const { data: runs, isLoading: runsLoading } = useRuns({ project_id: projectId, status: 'succeeded', limit: 50 });
  const { data: telemetryIndex, isLoading: indexLoading, error: indexError } = useTelemetryIndex(selectedRunId || undefined);
  const { data: telemetrySummary, isLoading: summaryLoading } = useTelemetrySummary(selectedRunId || undefined);
  const { data: currentSlice, isLoading: sliceLoading } = useTelemetrySlice(selectedRunId || undefined, currentTick);

  // Total ticks from telemetry data
  const totalTicks = telemetrySummary?.total_ticks || telemetryIndex?.total_ticks || 0;

  // Update selected run from URL
  useEffect(() => {
    if (urlRunId && urlRunId !== selectedRunId) {
      setSelectedRunId(urlRunId);
    }
  }, [urlRunId, selectedRunId]);

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

  const handlePause = useCallback(() => {
    setIsPlaying(false);
  }, []);

  const handleSkipBack = useCallback(() => {
    setCurrentTick(0);
    setIsPlaying(false);
  }, []);

  const handleSkipForward = useCallback(() => {
    setCurrentTick(Math.max(0, totalTicks - 1));
    setIsPlaying(false);
  }, [totalTicks]);

  const handleSeek = useCallback((tick: number) => {
    setCurrentTick(Math.max(0, Math.min(tick, totalTicks - 1)));
  }, [totalTicks]);

  // Check if telemetry is available
  const hasTelemetry = selectedRunId && !indexError && (telemetryIndex || telemetrySummary);
  const isLoading = indexLoading || summaryLoading;

  // Extract metrics from current slice
  const currentDelta = currentSlice?.deltas?.[0];
  const currentKeyframe = currentSlice?.keyframes?.[0];
  const activeAgents = currentDelta?.metrics?.active_agents || Object.keys(currentKeyframe?.agent_states || {}).length || 0;
  const totalAgents = currentDelta?.metrics?.total_agents || Object.keys(currentKeyframe?.agent_states || {}).length || 0;
  const eventsThisTick = currentSlice?.events?.length || 0;

  return (
    <div className="min-h-screen bg-black p-4 md:p-6">
      {/* Header */}
      <div className="mb-6 md:mb-8">
        <div className="flex items-center gap-2 mb-3">
          <Link href={`/p/${projectId}/universe-map`}>
            <Button variant="ghost" size="sm" className="text-[10px] md:text-xs">
              <ArrowLeft className="w-3 h-3 mr-1 md:mr-2" />
              BACK TO UNIVERSE MAP
            </Button>
          </Link>
        </div>
        <div className="flex items-center gap-2 mb-1">
          <Activity className="w-3.5 h-3.5 md:w-4 md:h-4 text-cyan-400" />
          <span className="text-[10px] md:text-xs font-mono text-white/40 uppercase tracking-wider">
            Telemetry
          </span>
        </div>
        <h1 className="text-lg md:text-xl font-mono font-bold text-white">Telemetry & Replay</h1>
        <p className="text-xs md:text-sm font-mono text-white/50 mt-1">
          Watch simulation replays and explore telemetry data (read-only per C3)
        </p>
      </div>

      {/* Guidance Panel - Blueprint-driven guidance */}
      <div className="max-w-5xl mb-6">
        <GuidancePanel
          projectId={projectId}
          sectionId="replay"
          className="mb-0"
        />
      </div>

      {/* Run Selector */}
      <div className="max-w-5xl mb-6">
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div>
              <h3 className="text-xs font-mono font-bold text-white mb-1">Select Run to Replay</h3>
              <p className="text-[10px] font-mono text-white/40">
                Choose a completed run with telemetry data
              </p>
            </div>
            <div className="min-w-[300px]">
              <RunSelector
                runs={runs}
                selectedRunId={selectedRunId}
                onSelectRun={setSelectedRunId}
                isLoading={runsLoading}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Replay Viewport */}
      <div className="max-w-5xl mb-4">
        <div className="bg-white/5 border border-white/10 aspect-video min-h-[300px] relative">
          {/* Grid Background */}
          <div
            className="absolute inset-0 opacity-20"
            style={{
              backgroundImage: `
                linear-gradient(to right, rgba(255,255,255,0.05) 1px, transparent 1px),
                linear-gradient(to bottom, rgba(255,255,255,0.05) 1px, transparent 1px)
              `,
              backgroundSize: '30px 30px',
            }}
          />

          {/* Loading State */}
          {selectedRunId && isLoading && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/50 z-10">
              <div className="text-center">
                <Loader2 className="w-8 h-8 text-cyan-400 animate-spin mx-auto mb-2" />
                <p className="text-xs font-mono text-white/60">Loading telemetry data...</p>
              </div>
            </div>
          )}

          {/* Error State */}
          {selectedRunId && indexError && !isLoading && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <AlertCircle className="w-8 h-8 text-yellow-400 mx-auto mb-2" />
                <h3 className="text-sm font-mono text-white/60 mb-2">Telemetry not available</h3>
                <p className="text-xs font-mono text-white/40 max-w-sm">
                  This run may not have telemetry data, or the telemetry endpoint is not available.
                </p>
              </div>
            </div>
          )}

          {/* Playback View */}
          {hasTelemetry && !isLoading && (
            <div className="absolute inset-0 p-6">
              {/* Simulation visualization placeholder */}
              <div className="h-full flex flex-col">
                {/* Top info bar */}
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-4">
                    <span className="text-xs font-mono text-white/40">
                      Run: {selectedRunId?.slice(0, 12)}...
                    </span>
                    {telemetrySummary && (
                      <span className="text-xs font-mono text-white/40">
                        Total: {telemetrySummary.total_ticks} ticks
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {isPlaying && (
                      <span className="text-xs font-mono text-cyan-400 flex items-center gap-1">
                        <Zap className="w-3 h-3" />
                        Playing {playbackSpeed}x
                      </span>
                    )}
                  </div>
                </div>

                {/* Main visualization area */}
                <div className="flex-1 flex items-center justify-center">
                  <div className="text-center">
                    <div className="text-6xl font-mono font-bold text-cyan-400 mb-2">
                      {currentTick}
                    </div>
                    <p className="text-xs font-mono text-white/40">Current Tick</p>

                    {currentSlice && (
                      <div className="mt-6 grid grid-cols-3 gap-4">
                        <div className="bg-white/5 border border-white/10 p-3">
                          <p className="text-xl font-mono font-bold text-white">{activeAgents}</p>
                          <p className="text-[10px] font-mono text-white/40">Active Agents</p>
                        </div>
                        <div className="bg-white/5 border border-white/10 p-3">
                          <p className="text-xl font-mono font-bold text-white">{totalAgents}</p>
                          <p className="text-[10px] font-mono text-white/40">Total Agents</p>
                        </div>
                        <div className="bg-white/5 border border-white/10 p-3">
                          <p className="text-xl font-mono font-bold text-white">{eventsThisTick}</p>
                          <p className="text-[10px] font-mono text-white/40">Events</p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Empty State */}
          {!selectedRunId && !isLoading && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <div className="w-16 h-16 bg-white/5 flex items-center justify-center mx-auto mb-4">
                  <Activity className="w-8 h-8 text-white/20" />
                </div>
                <h3 className="text-sm font-mono text-white/60 mb-2">No replay data</h3>
                <p className="text-xs font-mono text-white/40 max-w-sm">
                  Select a completed run above to view its replay
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Playback Controls */}
      <div className="max-w-5xl mb-6">
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                className="w-8 h-8 p-0"
                disabled={!hasTelemetry}
                onClick={handleSkipBack}
              >
                <SkipBack className="w-3 h-3" />
              </Button>
              <Button
                size="sm"
                className="w-8 h-8 p-0"
                disabled={!hasTelemetry}
                onClick={isPlaying ? handlePause : handlePlay}
              >
                {isPlaying ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="w-8 h-8 p-0"
                disabled={!hasTelemetry}
                onClick={handleSkipForward}
              >
                <SkipForward className="w-3 h-3" />
              </Button>
            </div>

            <div className="flex-1 mx-4">
              <input
                type="range"
                min={0}
                max={Math.max(0, totalTicks - 1)}
                value={currentTick}
                onChange={(e) => handleSeek(Number(e.target.value))}
                disabled={!hasTelemetry || totalTicks === 0}
                className="w-full h-1 bg-white/10 rounded-full appearance-none cursor-pointer disabled:opacity-50"
              />
              <div className="flex justify-between mt-1 text-[10px] font-mono text-white/30">
                <span>Tick {currentTick}</span>
                <span>Tick {Math.max(0, totalTicks - 1)}</span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <select
                value={playbackSpeed}
                onChange={(e) => setPlaybackSpeed(Number(e.target.value))}
                disabled={!hasTelemetry}
                className="px-2 py-1 bg-black border border-white/10 text-[10px] font-mono text-white appearance-none cursor-pointer disabled:opacity-50"
              >
                {PLAYBACK_SPEEDS.map((speed) => (
                  <option key={speed} value={speed}>
                    {speed}x
                  </option>
                ))}
              </select>
              <Button size="sm" variant="outline" className="w-8 h-8 p-0" disabled>
                <Settings className="w-3 h-3" />
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Metrics Panel */}
      <div className="max-w-5xl mb-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white/5 border border-white/10 p-4">
            <div className="flex items-center gap-2 mb-2">
              <Clock className="w-4 h-4 text-white/40" />
              <span className="text-[10px] font-mono text-white/40 uppercase">Current Tick</span>
            </div>
            <div className="text-2xl font-mono font-bold text-white">
              {hasTelemetry ? currentTick : '--'}
            </div>
            {hasTelemetry && totalTicks > 0 && (
              <div className="text-[10px] font-mono text-white/40 mt-1">
                {((currentTick / totalTicks) * 100).toFixed(1)}% complete
              </div>
            )}
          </div>
          <div className="bg-white/5 border border-white/10 p-4">
            <div className="flex items-center gap-2 mb-2">
              <Users className="w-4 h-4 text-white/40" />
              <span className="text-[10px] font-mono text-white/40 uppercase">Active Agents</span>
            </div>
            <div className="text-2xl font-mono font-bold text-white">
              {hasTelemetry && currentSlice ? activeAgents : '--'}
            </div>
            {hasTelemetry && currentSlice && totalAgents > 0 && (
              <div className="text-[10px] font-mono text-white/40 mt-1">
                of {totalAgents} total
              </div>
            )}
          </div>
          <div className="bg-white/5 border border-white/10 p-4">
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp className="w-4 h-4 text-white/40" />
              <span className="text-[10px] font-mono text-white/40 uppercase">Events This Tick</span>
            </div>
            <div className="text-2xl font-mono font-bold text-white">
              {hasTelemetry && currentSlice ? eventsThisTick : '--'}
            </div>
            {telemetrySummary && (
              <div className="text-[10px] font-mono text-white/40 mt-1">
                {telemetrySummary.total_events} total events
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Navigation */}
      <div className="max-w-5xl mb-8">
        <div className="flex items-center justify-between gap-4">
          <Link href={`/p/${projectId}/universe-map`}>
            <Button variant="outline" size="sm" className="text-xs font-mono">
              <ArrowLeft className="w-3 h-3 mr-2" />
              Back to Universe Map
            </Button>
          </Link>
          <div className="flex items-center gap-2">
            <Link href={`/p/${projectId}/world-viewer?run=${selectedRunId || ''}&tick=${currentTick}`}>
              <Button variant="outline" size="sm" className="text-xs font-mono">
                <Map className="w-3 h-3 mr-2" />
                View in 2D World
              </Button>
            </Link>
            <Link href={`/p/${projectId}/reports?type=run${selectedRunId ? `&run=${selectedRunId}` : ''}`}>
              <Button variant="outline" size="sm" className="text-xs font-mono">
                <FileText className="w-3 h-3 mr-2" />
                View Report
              </Button>
            </Link>
            <Link href={`/p/${projectId}/results${selectedRunId ? `?run=${selectedRunId}` : ''}`}>
              <Button size="sm" className="text-xs font-mono bg-cyan-500 hover:bg-cyan-600">
                View Results
                <ArrowRight className="w-3 h-3 ml-2" />
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-8 pt-4 border-t border-white/5 max-w-5xl">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-1">
            <Terminal className="w-3 h-3" />
            <span>TELEMETRY & REPLAY (READ-ONLY PER C3)</span>
          </div>
          <span>AGENTVERSE v1.0</span>
        </div>
      </div>
    </div>
  );
}

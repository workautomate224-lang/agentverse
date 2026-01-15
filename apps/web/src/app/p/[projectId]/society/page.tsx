'use client';

/**
 * Society Simulation Page
 * Macro-level metrics dashboard for analyzing simulation runs
 * Supports drill-down to 2D World Viewer and Telemetry Replay
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  Network,
  ArrowLeft,
  Terminal,
  Users,
  Activity,
  TrendingUp,
  TrendingDown,
  Zap,
  AlertTriangle,
  BarChart3,
  Clock,
  ChevronDown,
  CheckCircle,
  Loader2,
  AlertCircle,
  Map,
  Play,
  ExternalLink,
  Info,
  RefreshCw,
  Target,
  Percent,
  Flame,
  Shield,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  useRuns,
  useTelemetryIndex,
  useTelemetrySummary,
  useTelemetrySlice,
  useNode,
} from '@/hooks/useApi';
import type { RunSummary, TelemetrySummary, TelemetrySlice, TelemetryKeyframe } from '@/lib/api';
import { GuidancePanel } from '@/components/pil';

// =============================================================================
// Types
// =============================================================================

interface KPIData {
  label: string;
  value: string | number;
  unit?: string;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  icon: React.ReactNode;
  color: string;
  available: boolean;
  tooltip?: string;
}

interface ChartDataPoint {
  tick: number;
  value: number;
  label?: string;
}

interface TickEventSummary {
  type: string;
  count: number;
  description?: string;
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

function formatNumber(num: number): string {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
  return num.toFixed(0);
}

function formatPercent(num: number): string {
  return (num * 100).toFixed(1) + '%';
}

// Extract metrics from telemetry summary
function extractKPIs(summary: TelemetrySummary | undefined, slice: TelemetrySlice | undefined): KPIData[] {
  const kpis: KPIData[] = [];

  // 1. Population / Active Agents
  const totalAgents = summary?.total_agents;
  const byTick = summary?.key_metrics?.by_tick;
  const latestTick = byTick && byTick.length > 0 ? byTick[byTick.length - 1] : null;
  const activeAgents = latestTick?.active_agents;

  kpis.push({
    label: 'Population',
    value: totalAgents !== undefined ? formatNumber(totalAgents) : 'N/A',
    unit: 'agents',
    icon: <Users className="w-5 h-5" />,
    color: 'text-cyan-400',
    available: totalAgents !== undefined,
    tooltip: totalAgents === undefined ? 'Not emitted by backend' : undefined,
  });

  // 2. Activity Rate
  const activityRate = latestTick?.activity_rate;
  kpis.push({
    label: 'Activity Rate',
    value: activityRate !== undefined ? formatPercent(activityRate) : 'N/A',
    trend: activityRate !== undefined && activityRate > 0.5 ? 'up' : 'down',
    icon: <Activity className="w-5 h-5" />,
    color: 'text-green-400',
    available: activityRate !== undefined,
    tooltip: activityRate === undefined ? 'Not emitted by backend' : undefined,
  });

  // 3. Total Events (as proxy for incidents/activity)
  const totalEvents = summary?.total_events;
  kpis.push({
    label: 'Total Events',
    value: totalEvents !== undefined ? formatNumber(totalEvents) : 'N/A',
    unit: 'events',
    icon: <Zap className="w-5 h-5" />,
    color: 'text-amber-400',
    available: totalEvents !== undefined,
    tooltip: totalEvents === undefined ? 'Not emitted by backend' : undefined,
  });

  // 4. Simulation Duration
  const durationSeconds = summary?.duration_seconds;
  const durationDisplay = durationSeconds !== undefined
    ? durationSeconds < 60 ? `${durationSeconds.toFixed(1)}s` : `${(durationSeconds / 60).toFixed(1)}m`
    : 'N/A';
  kpis.push({
    label: 'Duration',
    value: durationDisplay,
    icon: <Clock className="w-5 h-5" />,
    color: 'text-purple-400',
    available: durationSeconds !== undefined,
    tooltip: durationSeconds === undefined ? 'Not emitted by backend' : undefined,
  });

  // 5. Event Types (diversity metric)
  const eventTypeCount = summary?.event_type_counts ? Object.keys(summary.event_type_counts).length : undefined;
  kpis.push({
    label: 'Event Types',
    value: eventTypeCount !== undefined ? eventTypeCount : 'N/A',
    unit: 'types',
    icon: <Target className="w-5 h-5" />,
    color: 'text-rose-400',
    available: eventTypeCount !== undefined,
    tooltip: eventTypeCount === undefined ? 'Not emitted by backend' : undefined,
  });

  // 6. Coverage (active agents / total agents at latest tick)
  const coverage = latestTick && latestTick.total_agents > 0
    ? latestTick.active_agents / latestTick.total_agents
    : undefined;
  kpis.push({
    label: 'Coverage',
    value: coverage !== undefined ? formatPercent(coverage) : 'N/A',
    icon: <Shield className="w-5 h-5" />,
    color: 'text-indigo-400',
    available: coverage !== undefined,
    tooltip: coverage === undefined ? 'Not emitted by backend' : undefined,
  });

  return kpis;
}

// Extract time-series data for charts
function extractTimeSeriesData(summary: TelemetrySummary | undefined): {
  activityData: ChartDataPoint[];
  agentData: ChartDataPoint[];
} {
  const activityData: ChartDataPoint[] = [];
  const agentData: ChartDataPoint[] = [];

  const byTick = summary?.key_metrics?.by_tick;
  if (byTick && byTick.length > 0) {
    byTick.forEach((point, index) => {
      activityData.push({
        tick: index,
        value: point.activity_rate * 100, // Convert to percentage
      });
      agentData.push({
        tick: index,
        value: point.active_agents,
      });
    });
  }

  return { activityData, agentData };
}

// Extract events from slice
function extractSliceEvents(slice: TelemetrySlice | undefined): TickEventSummary[] {
  if (!slice || !slice.events) return [];

  const eventCounts: Record<string, number> = {};
  slice.events.forEach((event) => {
    const type = event.event_type || 'unknown';
    eventCounts[type] = (eventCounts[type] || 0) + 1;
  });

  return Object.entries(eventCounts).map(([type, count]) => ({
    type,
    count,
    description: `${count} occurrence${count > 1 ? 's' : ''}`,
  }));
}

// Extract agent count from slice
function extractAgentCount(slice: TelemetrySlice | undefined): number {
  if (!slice || !slice.keyframes || slice.keyframes.length === 0) return 0;
  const keyframe = slice.keyframes[0];
  if (!keyframe.agent_states) return 0;
  return Object.keys(keyframe.agent_states).length;
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
  const eligibleRuns = runs?.filter((r) => r.status === 'succeeded') || [];
  const selectedRun = eligibleRuns.find((r) => r.run_id === selectedRunId);

  return (
    <div className="relative">
      <div className="text-[10px] font-mono text-white/40 uppercase mb-1">
        Analyze Run {nodeLabel && <span className="text-cyan-400">({nodeLabel})</span>}
      </div>
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={isLoading || eligibleRuns.length === 0}
        className={cn(
          'w-full px-3 py-2 bg-black border border-white/10 text-left flex items-center justify-between transition-colors',
          'hover:border-white/30 focus:outline-none focus:border-cyan-500/50',
          (isLoading || eligibleRuns.length === 0) && 'opacity-50 cursor-not-allowed'
        )}
      >
        <span className="text-xs font-mono text-white/60 truncate">
          {isLoading ? (
            'Loading runs...'
          ) : selectedRun ? (
            <span className="text-white">
              {selectedRun.run_id.slice(0, 8)}... - {formatDate(selectedRun.created_at)}
            </span>
          ) : eligibleRuns.length === 0 ? (
            'No completed runs'
          ) : (
            'Select a run to analyze'
          )}
        </span>
        <ChevronDown className={cn('w-4 h-4 text-white/40 transition-transform', isOpen && 'rotate-180')} />
      </button>

      {isOpen && eligibleRuns.length > 0 && (
        <div className="absolute z-50 top-full left-0 right-0 mt-1 bg-black border border-white/10 max-h-48 overflow-y-auto">
          {eligibleRuns.map((run) => (
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

// KPI Card component
function KPICard({ kpi }: { kpi: KPIData }) {
  return (
    <div className={cn(
      'bg-white/5 border border-white/10 p-4 relative',
      !kpi.available && 'opacity-60'
    )}>
      <div className="flex items-start justify-between mb-2">
        <div className={cn('p-2 bg-black/50', kpi.color)}>
          {kpi.icon}
        </div>
        {kpi.trend && kpi.available && (
          <div className={cn(
            'flex items-center gap-1 text-[10px] font-mono',
            kpi.trend === 'up' ? 'text-green-400' : kpi.trend === 'down' ? 'text-red-400' : 'text-white/40'
          )}>
            {kpi.trend === 'up' ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
            {kpi.trendValue}
          </div>
        )}
      </div>
      <div className="text-[10px] font-mono text-white/40 uppercase mb-1">{kpi.label}</div>
      <div className="flex items-baseline gap-1">
        <span className={cn('text-xl font-mono font-bold', kpi.available ? 'text-white' : 'text-white/40')}>
          {kpi.value}
        </span>
        {kpi.unit && <span className="text-xs font-mono text-white/40">{kpi.unit}</span>}
      </div>
      {kpi.tooltip && !kpi.available && (
        <div className="absolute top-2 right-2 group">
          <Info className="w-3 h-3 text-white/30" />
          <div className="hidden group-hover:block absolute right-0 top-4 bg-black border border-white/20 px-2 py-1 text-[10px] font-mono text-white/60 whitespace-nowrap z-10">
            {kpi.tooltip}
          </div>
        </div>
      )}
    </div>
  );
}

// Simple Time Series Chart component
function TimeSeriesChart({
  data,
  label,
  unit,
  color,
  focusedTick,
  onHover,
  onClick,
}: {
  data: ChartDataPoint[];
  label: string;
  unit: string;
  color: string;
  focusedTick: number | null;
  onHover: (tick: number | null) => void;
  onClick: (tick: number) => void;
}) {
  if (data.length === 0) {
    return (
      <div className="bg-white/5 border border-white/10 p-4">
        <div className="text-[10px] font-mono text-white/40 uppercase mb-2">{label}</div>
        <div className="h-32 flex items-center justify-center">
          <span className="text-xs font-mono text-white/30">No data available</span>
        </div>
      </div>
    );
  }

  const maxValue = Math.max(...data.map(d => d.value));
  const minValue = Math.min(...data.map(d => d.value));
  const range = maxValue - minValue || 1;

  return (
    <div className="bg-white/5 border border-white/10 p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="text-[10px] font-mono text-white/40 uppercase">{label}</div>
        <div className="text-[10px] font-mono text-white/40">
          {focusedTick !== null && data[focusedTick] ? (
            <span className={color}>Tick {focusedTick}: {data[focusedTick].value.toFixed(1)}{unit}</span>
          ) : (
            <span>Hover to inspect</span>
          )}
        </div>
      </div>
      <div className="h-32 flex items-end gap-px">
        {data.map((point, index) => {
          const height = ((point.value - minValue) / range) * 100;
          const isFocused = focusedTick === index;

          return (
            <div
              key={point.tick}
              className="flex-1 relative group cursor-pointer"
              onMouseEnter={() => onHover(index)}
              onMouseLeave={() => onHover(null)}
              onClick={() => onClick(index)}
            >
              <div
                className={cn(
                  'w-full transition-all duration-100',
                  isFocused ? 'bg-cyan-400' : color.replace('text-', 'bg-').replace('-400', '-500/60'),
                  'hover:opacity-100'
                )}
                style={{ height: `${Math.max(2, height)}%` }}
              />
              {isFocused && (
                <div className="absolute -top-6 left-1/2 transform -translate-x-1/2 bg-black border border-white/20 px-1 text-[9px] font-mono text-white whitespace-nowrap z-10">
                  {point.value.toFixed(1)}{unit}
                </div>
              )}
            </div>
          );
        })}
      </div>
      <div className="flex justify-between mt-2 text-[9px] font-mono text-white/30">
        <span>Tick 0</span>
        <span>Tick {data.length - 1}</span>
      </div>
    </div>
  );
}

// Focused Tick Panel component
function FocusedTickPanel({
  tick,
  slice,
  sliceLoading,
  runId,
  projectId,
  totalTicks,
  fallbackAgentCount,
  onRefresh,
}: {
  tick: number;
  slice: TelemetrySlice | undefined;
  sliceLoading: boolean;
  runId: string;
  projectId: string;
  totalTicks: number;
  fallbackAgentCount: number;
  onRefresh: () => void;
}) {
  const events = extractSliceEvents(slice);
  // Use slice agent count, but fallback to index/summary count when slice is empty
  const sliceAgentCount = extractAgentCount(slice);
  const agentCount = sliceAgentCount > 0 ? sliceAgentCount : fallbackAgentCount;

  return (
    <div className="bg-white/5 border border-white/10">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Target className="w-4 h-4 text-cyan-400" />
          <h3 className="text-sm font-mono font-bold text-white">Focused Tick: {tick}</h3>
          <span className="text-[10px] font-mono text-white/40">/ {totalTicks - 1}</span>
        </div>
        <button
          onClick={onRefresh}
          className="p-1 hover:bg-white/10 transition-colors"
          title="Refresh tick data"
        >
          <RefreshCw className={cn('w-4 h-4 text-white/40', sliceLoading && 'animate-spin')} />
        </button>
      </div>

      {/* Content */}
      <div className="p-4">
        {sliceLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 text-cyan-400 animate-spin" />
          </div>
        ) : !slice ? (
          <div className="text-center py-8">
            <AlertCircle className="w-8 h-8 text-yellow-400/50 mx-auto mb-2" />
            <p className="text-xs font-mono text-white/40">Telemetry incomplete</p>
            <Button size="sm" variant="outline" className="mt-2 text-xs" onClick={onRefresh}>
              <RefreshCw className="w-3 h-3 mr-1" />
              Retry
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Quick Stats */}
            <div className="grid grid-cols-2 gap-2">
              <div className="bg-black/30 p-2">
                <div className="text-[10px] font-mono text-white/40 uppercase">Agents</div>
                <div className="text-sm font-mono text-white">{agentCount}</div>
              </div>
              <div className="bg-black/30 p-2">
                <div className="text-[10px] font-mono text-white/40 uppercase">Events</div>
                <div className="text-sm font-mono text-white">{slice.total_events || 0}</div>
              </div>
            </div>

            {/* Events at this tick */}
            {events.length > 0 && (
              <div>
                <div className="text-[10px] font-mono text-white/40 uppercase mb-2">Events at Tick {tick}</div>
                <div className="space-y-1 max-h-24 overflow-y-auto">
                  {events.map((event, index) => (
                    <div key={index} className="flex items-center justify-between text-xs font-mono">
                      <span className="text-white/60">{event.type}</span>
                      <span className="text-amber-400">{event.count}x</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {events.length === 0 && (
              <div className="text-center py-4">
                <p className="text-xs font-mono text-white/30">No events at this tick</p>
              </div>
            )}

            {/* Drilldown Actions */}
            <div className="pt-4 border-t border-white/10 space-y-2">
              <Link href={`/p/${projectId}/world-viewer?run=${runId}&tick=${tick}`}>
                <Button variant="secondary" size="sm" className="w-full text-xs justify-start">
                  <Map className="w-3 h-3 mr-2" />
                  Open in 2D World Viewer
                  <ExternalLink className="w-3 h-3 ml-auto" />
                </Button>
              </Link>
              <Link href={`/p/${projectId}/replay?run=${runId}&tick=${tick}`}>
                <Button variant="secondary" size="sm" className="w-full text-xs justify-start">
                  <Play className="w-3 h-3 mr-2" />
                  Open Telemetry & Replay
                  <ExternalLink className="w-3 h-3 ml-auto" />
                </Button>
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// Main Page Component
// =============================================================================

export default function SocietySimulationPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const projectId = params.projectId as string;

  // URL params
  const urlRunId = searchParams.get('run');
  const urlTick = searchParams.get('tick');

  // State
  const [selectedRunId, setSelectedRunId] = useState<string | null>(urlRunId);
  const [focusedTick, setFocusedTick] = useState<number | null>(urlTick ? parseInt(urlTick, 10) : null);
  const [hoveredTick, setHoveredTick] = useState<number | null>(null);

  // API hooks
  const { data: runs, isLoading: runsLoading } = useRuns({ project_id: projectId, status: 'succeeded', limit: 50 });
  const { data: telemetryIndex, isLoading: indexLoading, error: indexError, refetch: refetchIndex } = useTelemetryIndex(selectedRunId || undefined);
  const { data: telemetrySummary, isLoading: summaryLoading, refetch: refetchSummary } = useTelemetrySummary(selectedRunId || undefined);
  const { data: focusedSlice, isLoading: sliceLoading, refetch: refetchSlice } = useTelemetrySlice(
    selectedRunId || undefined,
    focusedTick ?? 0
  );

  // Get run's node for label
  const selectedRun = runs?.find(r => r.run_id === selectedRunId);
  const { data: runNode } = useNode(selectedRun?.node_id);

  // Derived state
  const totalTicks = telemetrySummary?.total_ticks || telemetryIndex?.total_ticks || 0;
  const isLoading = indexLoading || summaryLoading;
  const hasTelemetry = selectedRunId && !indexError && (telemetryIndex || telemetrySummary);

  // Extract data for display
  const kpis = useMemo(() => extractKPIs(telemetrySummary, focusedSlice), [telemetrySummary, focusedSlice]);
  const { activityData, agentData } = useMemo(() => extractTimeSeriesData(telemetrySummary), [telemetrySummary]);

  // Set initial focused tick when data loads
  useEffect(() => {
    if (telemetrySummary && focusedTick === null) {
      // Default to mid-point tick
      const midTick = Math.floor((telemetrySummary.total_ticks || 0) / 2);
      setFocusedTick(midTick);
    }
  }, [telemetrySummary, focusedTick]);

  // Update URL when state changes
  useEffect(() => {
    const params = new URLSearchParams();
    if (selectedRunId) params.set('run', selectedRunId);
    if (focusedTick !== null && focusedTick > 0) params.set('tick', focusedTick.toString());

    const newUrl = `/p/${projectId}/society${params.toString() ? `?${params.toString()}` : ''}`;
    window.history.replaceState({}, '', newUrl);
  }, [projectId, selectedRunId, focusedTick]);

  // Handlers
  const handleSelectRun = useCallback((runId: string) => {
    setSelectedRunId(runId);
    setFocusedTick(null); // Reset focused tick
  }, []);

  const handleChartClick = useCallback((tick: number) => {
    setFocusedTick(tick);
  }, []);

  const handleRefreshSlice = useCallback(() => {
    refetchSlice();
  }, [refetchSlice]);

  // Check states
  const showEmptyState = !selectedRunId;
  const showNoDataState = selectedRunId && !isLoading && indexError;
  const showIncompleteState = selectedRunId && !isLoading && !indexError && !telemetrySummary;

  return (
    <div className="min-h-screen bg-black flex flex-col">
      {/* Header */}
      <div className="p-4 md:p-6 border-b border-white/10">
        <Link href={`/p/${projectId}/overview`}>
          <Button variant="ghost" size="sm" className="mb-3 text-[10px] md:text-xs">
            <ArrowLeft className="w-3 h-3 mr-1 md:mr-2" />
            BACK TO OVERVIEW
          </Button>
        </Link>
        <div className="flex items-center gap-2 mb-1">
          <Network className="w-3.5 h-3.5 md:w-4 md:h-4 text-cyan-400" />
          <span className="text-[10px] md:text-xs font-mono text-white/40 uppercase tracking-wider">Society Mode</span>
        </div>
        <h1 className="text-lg md:text-xl font-mono font-bold text-white">Society Simulation</h1>
        <p className="text-xs md:text-sm font-mono text-white/50 mt-1">
          Macro-level metrics and analysis for simulation runs
        </p>
        {/* Guidance Panel - Blueprint-driven guidance */}
        <div className="mt-4">
          <GuidancePanel
            projectId={projectId}
            sectionId="society"
            compact={true}
            className="mb-0"
          />
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex">
        {/* Left Panel - Run Selection & Tick Focus */}
        <div className="w-72 border-r border-white/10 p-4 flex flex-col">
          {/* Run Selector */}
          <div className="mb-6">
            <RunSelector
              runs={runs}
              selectedRunId={selectedRunId}
              onSelectRun={handleSelectRun}
              isLoading={runsLoading}
              nodeLabel={runNode?.label}
            />
          </div>

          {/* Run Info */}
          {selectedRun && (
            <div className="mb-6 p-3 bg-white/5 border border-white/10">
              <div className="text-[10px] font-mono text-white/40 uppercase mb-2">Run Details</div>
              <div className="space-y-1 text-xs font-mono">
                <div className="flex justify-between">
                  <span className="text-white/40">Status</span>
                  <span className="text-green-400">{selectedRun.status}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-white/40">Ticks</span>
                  <span className="text-white">{totalTicks}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-white/40">Created</span>
                  <span className="text-white/60">{formatDate(selectedRun.created_at)}</span>
                </div>
              </div>
            </div>
          )}

          {/* Focused Tick Panel */}
          {hasTelemetry && focusedTick !== null && (
            <FocusedTickPanel
              tick={focusedTick}
              slice={focusedSlice}
              sliceLoading={sliceLoading}
              runId={selectedRunId!}
              projectId={projectId}
              totalTicks={totalTicks}
              fallbackAgentCount={telemetryIndex?.agent_ids?.length ?? telemetrySummary?.total_agents ?? 0}
              onRefresh={handleRefreshSlice}
            />
          )}

          {/* Spacer */}
          <div className="flex-1" />

          {/* Quick Links */}
          <div className="border-t border-white/10 pt-4 mt-4">
            <div className="text-[10px] font-mono text-white/40 uppercase mb-2">Quick Actions</div>
            <div className="space-y-2">
              <Link href={`/p/${projectId}/run-center`}>
                <Button variant="ghost" size="sm" className="w-full justify-start text-xs">
                  <Activity className="w-3 h-3 mr-2" />
                  Run Center
                </Button>
              </Link>
              <Link href={`/p/${projectId}/event-lab`}>
                <Button variant="ghost" size="sm" className="w-full justify-start text-xs">
                  <Zap className="w-3 h-3 mr-2" />
                  Event Lab
                </Button>
              </Link>
            </div>
          </div>
        </div>

        {/* Main Dashboard Area */}
        <div className="flex-1 p-6 overflow-y-auto">
          {/* Loading State */}
          {isLoading && (
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <Loader2 className="w-8 h-8 text-cyan-400 animate-spin mx-auto mb-2" />
                <p className="text-xs font-mono text-white/60">Loading telemetry data...</p>
              </div>
            </div>
          )}

          {/* Empty State - No Run Selected */}
          {showEmptyState && !isLoading && (
            <div className="flex items-center justify-center h-64">
              <div className="text-center max-w-md">
                <div className="w-20 h-20 bg-white/5 flex items-center justify-center mx-auto mb-4 rounded-full">
                  <BarChart3 className="w-10 h-10 text-white/20" />
                </div>
                <h3 className="text-sm font-mono text-white/60 mb-2">Select a Run to Analyze</h3>
                <p className="text-xs font-mono text-white/40 mb-4">
                  Choose a completed simulation run from the selector to view macro-level metrics and insights.
                </p>
                <Link href={`/p/${projectId}/run-center`}>
                  <Button size="sm" variant="secondary" className="text-xs">
                    GO TO RUN CENTER
                  </Button>
                </Link>
              </div>
            </div>
          )}

          {/* Error State - No Telemetry */}
          {showNoDataState && (
            <div className="flex items-center justify-center h-64">
              <div className="text-center max-w-md">
                <div className="w-20 h-20 bg-red-500/10 flex items-center justify-center mx-auto mb-4 rounded-full">
                  <AlertCircle className="w-10 h-10 text-red-400/60" />
                </div>
                <h3 className="text-sm font-mono text-white/60 mb-2">Telemetry Not Available</h3>
                <p className="text-xs font-mono text-white/40 mb-4">
                  This run does not have telemetry data available or it could not be loaded.
                </p>
                <Button size="sm" variant="secondary" className="text-xs" onClick={() => refetchIndex()}>
                  <RefreshCw className="w-3 h-3 mr-2" />
                  Retry
                </Button>
              </div>
            </div>
          )}

          {/* Incomplete Telemetry State */}
          {showIncompleteState && (
            <div className="flex items-center justify-center h-64">
              <div className="text-center max-w-md">
                <div className="w-20 h-20 bg-yellow-500/10 flex items-center justify-center mx-auto mb-4 rounded-full">
                  <AlertTriangle className="w-10 h-10 text-yellow-400/60" />
                </div>
                <h3 className="text-sm font-mono text-white/60 mb-2">Telemetry Incomplete</h3>
                <p className="text-xs font-mono text-white/40 mb-4">
                  Telemetry index exists but summary data is missing. The run may still be processing.
                </p>
                <div className="flex gap-2 justify-center">
                  <Button size="sm" variant="secondary" className="text-xs" onClick={() => refetchSummary()}>
                    <RefreshCw className="w-3 h-3 mr-2" />
                    Retry
                  </Button>
                  <Link href={`/p/${projectId}/replay?run=${selectedRunId}`}>
                    <Button size="sm" variant="outline" className="text-xs">
                      Try Telemetry Replay
                    </Button>
                  </Link>
                </div>
              </div>
            </div>
          )}

          {/* Dashboard Content */}
          {hasTelemetry && !isLoading && (
            <div className="space-y-6">
              {/* KPI Cards */}
              <div>
                <h2 className="text-sm font-mono font-bold text-white mb-3">Key Metrics</h2>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                  {kpis.map((kpi, index) => (
                    <KPICard key={index} kpi={kpi} />
                  ))}
                </div>
              </div>

              {/* Time Series Charts */}
              <div>
                <h2 className="text-sm font-mono font-bold text-white mb-3">Metrics Over Time</h2>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  <TimeSeriesChart
                    data={activityData}
                    label="Activity Rate"
                    unit="%"
                    color="text-green-400"
                    focusedTick={hoveredTick ?? focusedTick}
                    onHover={setHoveredTick}
                    onClick={handleChartClick}
                  />
                  <TimeSeriesChart
                    data={agentData}
                    label="Active Agents"
                    unit=""
                    color="text-cyan-400"
                    focusedTick={hoveredTick ?? focusedTick}
                    onHover={setHoveredTick}
                    onClick={handleChartClick}
                  />
                </div>
              </div>

              {/* Event Type Distribution */}
              {telemetrySummary?.event_type_counts && Object.keys(telemetrySummary.event_type_counts).length > 0 && (
                <div>
                  <h2 className="text-sm font-mono font-bold text-white mb-3">Event Distribution</h2>
                  <div className="bg-white/5 border border-white/10 p-4">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      {Object.entries(telemetrySummary.event_type_counts).map(([type, count]) => (
                        <div key={type} className="flex items-center justify-between p-2 bg-black/30">
                          <span className="text-xs font-mono text-white/60 truncate">{type}</span>
                          <span className="text-xs font-mono text-amber-400 ml-2">{count}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Tick Selector */}
              <div>
                <h2 className="text-sm font-mono font-bold text-white mb-3">
                  Select Tick for Drilldown
                </h2>
                <div className="bg-white/5 border border-white/10 p-4">
                  <div className="flex items-center gap-4">
                    <span className="text-xs font-mono text-white/40">Tick:</span>
                    <input
                      type="range"
                      min={0}
                      max={Math.max(0, totalTicks - 1)}
                      value={focusedTick ?? 0}
                      onChange={(e) => setFocusedTick(parseInt(e.target.value, 10))}
                      className="flex-1 accent-cyan-500"
                    />
                    <span className="text-xs font-mono text-cyan-400 w-20 text-right">
                      {focusedTick ?? 0} / {totalTicks - 1}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="h-8 border-t border-white/10 flex items-center justify-between px-4 text-[10px] font-mono text-white/30">
        <div className="flex items-center gap-1">
          <Terminal className="w-3 h-3" />
          <span>SOCIETY SIMULATION</span>
        </div>
        <span>AGENTVERSE v1.0</span>
      </div>
    </div>
  );
}

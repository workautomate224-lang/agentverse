'use client';

/**
 * Society Output Panel Component
 * Reference: Interaction_design.md §5.12
 *
 * Display trend charts, distribution charts, and key events.
 */

import { useState } from 'react';
import {
  BarChart3,
  TrendingUp,
  PieChart,
  Zap,
  Loader2,
  Clock,
  ChevronRight,
  Activity,
} from 'lucide-react';
import { RunProgressUpdate, SpecRunResults, RunSummary } from '@/lib/api';
import { cn } from '@/lib/utils';

interface SocietyOutputPanelProps {
  runProgress: RunProgressUpdate | null;
  runResults: SpecRunResults | null;
  isLoading: boolean;
  completedRuns: RunSummary[];
  onSelectRun: (runId: string) => void;
}

// Simple bar chart component
function SimpleBarChart({
  data,
  maxValue,
}: {
  data: { label: string; value: number; color?: string }[];
  maxValue: number;
}) {
  return (
    <div className="space-y-2">
      {data.map((item, i) => (
        <div key={i} className="flex items-center gap-2">
          <div className="w-20 text-xs text-white/60 truncate">{item.label}</div>
          <div className="flex-1 h-4 bg-white/10 overflow-hidden">
            <div
              className={cn(
                'h-full transition-all',
                item.color ?? 'bg-gradient-to-r from-cyan-500 to-purple-500'
              )}
              style={{ width: `${(item.value / maxValue) * 100}%` }}
            />
          </div>
          <div className="w-12 text-xs font-mono text-white/80 text-right">
            {(item.value * 100).toFixed(1)}%
          </div>
        </div>
      ))}
    </div>
  );
}

// Simple line chart component (sparkline style)
function SparklineChart({
  values,
  height = 40,
}: {
  values: number[];
  height?: number;
}) {
  if (values.length === 0) return null;

  const max = Math.max(...values);
  const min = Math.min(...values);
  const range = max - min || 1;

  const points = values.map((v, i) => {
    const x = (i / (values.length - 1)) * 100;
    const y = height - ((v - min) / range) * height;
    return `${x},${y}`;
  }).join(' ');

  return (
    <svg
      width="100%"
      height={height}
      className="text-cyan-400"
      preserveAspectRatio="none"
    >
      <polyline
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        points={points}
      />
    </svg>
  );
}

export function SocietyOutputPanel({
  runProgress,
  runResults,
  isLoading,
  completedRuns,
  onSelectRun,
}: SocietyOutputPanelProps) {
  const [activeTab, setActiveTab] = useState<'trends' | 'distribution' | 'events'>('trends');

  // Empty state - no run yet
  if (!runProgress && !runResults && !isLoading) {
    return (
      <div className="h-full flex flex-col">
        {/* Header */}
        <div className="flex-none p-4 border-b border-white/10">
          <div className="flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-cyan-400" />
            <h3 className="text-sm font-medium">Simulation Output</h3>
          </div>
        </div>

        <div className="flex-1 flex items-center justify-center p-8">
          <div className="text-center max-w-xs">
            <Activity className="h-10 w-10 mx-auto mb-3 text-white/20" />
            <h3 className="text-sm font-medium text-white/60 mb-2">No Simulation Results</h3>
            <p className="text-xs text-white/40">
              Configure your run parameters and click &quot;Run Society Simulation&quot; to see emergent behavior results.
            </p>
          </div>
        </div>

        {/* Recent Runs */}
        {completedRuns.length > 0 && (
          <div className="flex-none border-t border-white/10 p-4">
            <div className="text-xs text-white/40 mb-2">Recent Completed Runs</div>
            <div className="space-y-1">
              {completedRuns.map((run) => (
                <button
                  key={run.run_id}
                  onClick={() => onSelectRun(run.run_id)}
                  className="w-full text-left flex items-center justify-between p-2 bg-white/5 border border-white/10 hover:border-white/20 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <Clock className="h-3 w-3 text-white/40" />
                    <span className="text-xs text-white/80">
                      {new Date(run.created_at).toLocaleString()}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-green-400">
                      {run.timing.total_ticks} ticks
                    </span>
                    <ChevronRight className="h-3 w-3 text-white/40" />
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  // Loading state
  if (isLoading && !runResults) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-6 w-6 mx-auto mb-3 text-cyan-400 animate-spin" />
          <p className="text-sm text-white/60">Loading results...</p>
        </div>
      </div>
    );
  }

  // Running state
  if (runProgress?.status === 'running') {
    // Estimate progress based on current tick (assuming typical 100 tick runs)
    const estimatedTotal = 100;
    const progressPercent = Math.min((runProgress.current_tick / estimatedTotal) * 100, 99);

    return (
      <div className="h-full flex flex-col">
        {/* Header */}
        <div className="flex-none p-4 border-b border-white/10">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Loader2 className="h-4 w-4 text-yellow-400 animate-spin" />
              <h3 className="text-sm font-medium">Simulation Running</h3>
            </div>
            <span className="text-sm font-mono text-yellow-400">
              {progressPercent.toFixed(1)}%
            </span>
          </div>
        </div>

        <div className="flex-1 flex items-center justify-center p-8">
          <div className="w-full max-w-md text-center">
            {/* Progress Bar */}
            <div className="mb-4">
              <div className="h-3 bg-white/10 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-cyan-500 to-purple-500 transition-all"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 text-center">
              <div>
                <div className="text-2xl font-mono text-cyan-400">
                  {runProgress.current_tick}
                </div>
                <div className="text-xs text-white/40">Current Tick</div>
              </div>
              <div>
                <div className="text-2xl font-mono text-purple-400">
                  {runProgress.ticks_per_second?.toFixed(1) ?? '-'}
                </div>
                <div className="text-xs text-white/40">Ticks/sec</div>
              </div>
            </div>

            {runProgress.estimated_completion && (
              <div className="mt-4 text-xs text-white/40">
                Estimated completion: {new Date(runProgress.estimated_completion).toLocaleTimeString()}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Results state
  if (runResults) {
    const outcomeData = Object.entries(runResults.outcome_distribution).map(([label, value]) => ({
      label,
      value,
    }));
    const maxOutcome = Math.max(...outcomeData.map((d) => d.value));

    return (
      <div className="h-full flex flex-col">
        {/* Header with Tabs */}
        <div className="flex-none border-b border-white/10">
          <div className="flex items-center gap-4 p-4">
            <BarChart3 className="h-4 w-4 text-green-400" />
            <h3 className="text-sm font-medium">Results</h3>
          </div>
          <div className="flex px-4">
            {[
              { id: 'trends', label: 'Trends', icon: TrendingUp },
              { id: 'distribution', label: 'Distribution', icon: PieChart },
              { id: 'events', label: 'Events', icon: Zap },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as typeof activeTab)}
                className={cn(
                  'flex items-center gap-1.5 px-3 py-2 text-xs border-b-2 transition-colors',
                  activeTab === tab.id
                    ? 'text-cyan-400 border-cyan-400'
                    : 'text-white/60 border-transparent hover:text-white/80'
                )}
              >
                <tab.icon className="h-3 w-3" />
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {activeTab === 'trends' && (
            <div className="space-y-6">
              {runResults.metric_time_series.map((metric) => (
                <div key={metric.metric_name}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-white/80">{metric.metric_name}</span>
                    <span className="text-xs font-mono text-cyan-400">
                      {metric.values[metric.values.length - 1]?.value.toFixed(2)}
                    </span>
                  </div>
                  <div className="bg-white/5 border border-white/10 p-2">
                    <SparklineChart
                      values={metric.values.map((v) => v.value)}
                      height={50}
                    />
                  </div>
                </div>
              ))}
              {runResults.metric_time_series.length === 0 && (
                <div className="text-center py-8 text-white/40 text-sm">
                  No trend data available
                </div>
              )}
            </div>
          )}

          {activeTab === 'distribution' && (
            <div className="space-y-4">
              <div className="text-sm text-white/80 mb-3">Outcome Distribution</div>
              <SimpleBarChart data={outcomeData} maxValue={maxOutcome || 1} />

              {/* Key Metrics */}
              <div className="mt-6">
                <div className="text-sm text-white/80 mb-3">Key Metrics</div>
                <div className="grid grid-cols-2 gap-2">
                  {runResults.key_events.slice(0, 4).map((event, i) => (
                    <div key={i} className="border border-white/10 bg-white/5 p-3">
                      <div className="text-lg font-mono text-cyan-400">
                        {event.impact_score.toFixed(2)}
                      </div>
                      <div className="text-xs text-white/60 truncate">{event.event_type}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'events' && (
            <div className="space-y-2">
              {runResults.key_events.map((event, i) => (
                <div
                  key={i}
                  className="border border-white/10 bg-white/5 p-3"
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <Zap className="h-3 w-3 text-yellow-400" />
                      <span className="text-sm font-medium text-white/90">
                        {event.event_type}
                      </span>
                    </div>
                    <span className="text-xs font-mono text-white/40">
                      t{event.tick}
                    </span>
                  </div>
                  <p className="text-xs text-white/60">{event.description}</p>
                  <div className="mt-2 flex items-center gap-2">
                    <span className="text-xs text-white/40">Impact:</span>
                    <div className="flex-1 h-1.5 bg-white/10 overflow-hidden">
                      <div
                        className="h-full bg-yellow-500"
                        style={{ width: `${Math.min(event.impact_score * 100, 100)}%` }}
                      />
                    </div>
                    <span className="text-xs font-mono text-yellow-400">
                      {event.impact_score.toFixed(2)}
                    </span>
                  </div>
                </div>
              ))}

              {/* Turning Points */}
              {runResults.turning_points.length > 0 && (
                <div className="mt-4 pt-4 border-t border-white/10">
                  <div className="text-xs text-white/40 mb-2">Turning Points</div>
                  {runResults.turning_points.map((tp, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-2 py-1.5 text-xs"
                    >
                      <span className="font-mono text-white/40">t{tp.tick}</span>
                      <span className="text-white/80">{tp.metric}</span>
                      <span
                        className={cn(
                          'px-1.5 py-0.5',
                          tp.direction === 'increase'
                            ? 'bg-green-500/20 text-green-300'
                            : 'bg-red-500/20 text-red-300'
                        )}
                      >
                        {tp.direction === 'increase' ? '↑' : '↓'} {tp.magnitude.toFixed(2)}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {runResults.key_events.length === 0 && (
                <div className="text-center py-8 text-white/40 text-sm">
                  No key events recorded
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    );
  }

  return null;
}

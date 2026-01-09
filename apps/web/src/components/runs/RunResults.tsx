'use client';

/**
 * RunResults Component
 * Displays simulation run results with outcome distribution and metrics.
 * Reference: project.md §6.6 (Run results), C4 (auditable artifacts)
 */

import { memo, useMemo } from 'react';
import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  Download,
  ExternalLink,
  Percent,
  Zap,
  GitBranch,
  Info,
  Activity,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import type { SpecRunResults } from '@/lib/api';

interface RunResultsProps {
  results: SpecRunResults;
  runId: string;
  onExport?: (format: 'json' | 'csv') => void;
  onViewTelemetry?: (runId: string) => void;
  className?: string;
}

// Color palette for outcomes
const outcomeColors = [
  'bg-cyan-500',
  'bg-blue-500',
  'bg-purple-500',
  'bg-pink-500',
  'bg-orange-500',
  'bg-yellow-500',
  'bg-green-500',
  'bg-red-500',
];

export const RunResults = memo(function RunResults({
  results,
  runId,
  onExport,
  onViewTelemetry,
  className,
}: RunResultsProps) {
  // Process outcome distribution
  const outcomeData = useMemo(() => {
    if (!results.outcome_distribution) return [];

    const total = Object.values(results.outcome_distribution).reduce((a, b) => a + b, 0);
    const entries = Object.entries(results.outcome_distribution)
      .map(([label, count], index) => ({
        label,
        count,
        percentage: total > 0 ? (count / total) * 100 : 0,
        color: outcomeColors[index % outcomeColors.length],
      }))
      .sort((a, b) => b.count - a.count);

    return entries;
  }, [results.outcome_distribution]);

  // Find dominant outcome
  const dominantOutcome = outcomeData[0];

  // Total agents from outcome distribution
  const totalAgents = useMemo(() => {
    if (!results.outcome_distribution) return 0;
    return Object.values(results.outcome_distribution).reduce((a, b) => a + b, 0);
  }, [results.outcome_distribution]);

  return (
    <div className={cn('space-y-6', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-green-500/10">
            <BarChart3 className="w-5 h-5 text-green-400" />
          </div>
          <div>
            <h3 className="text-lg font-mono font-bold text-white">
              Run Results
            </h3>
            <p className="text-xs font-mono text-white/40">
              Run ID: {runId.slice(0, 12)}...
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {onExport && (
            <>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => onExport('json')}
              >
                <Download className="w-3 h-3 mr-1" />
                JSON
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => onExport('csv')}
              >
                <Download className="w-3 h-3 mr-1" />
                CSV
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {/* Total Agents */}
        <div className="p-4 bg-black border border-white/10">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="w-4 h-4 text-white/40" />
            <span className="text-[10px] font-mono text-white/40 uppercase tracking-wider">
              Total Agents
            </span>
          </div>
          <p className="text-2xl font-mono font-bold text-white">
            {totalAgents.toLocaleString()}
          </p>
        </div>

        {/* Outcomes */}
        <div className="p-4 bg-black border border-white/10">
          <div className="flex items-center gap-2 mb-2">
            <Percent className="w-4 h-4 text-white/40" />
            <span className="text-[10px] font-mono text-white/40 uppercase tracking-wider">
              Outcomes
            </span>
          </div>
          <p className="text-2xl font-mono font-bold text-white">
            {outcomeData.length}
          </p>
        </div>

        {/* Key Events */}
        <div className="p-4 bg-black border border-white/10">
          <div className="flex items-center gap-2 mb-2">
            <Zap className="w-4 h-4 text-yellow-400" />
            <span className="text-[10px] font-mono text-white/40 uppercase tracking-wider">
              Key Events
            </span>
          </div>
          <p className="text-2xl font-mono font-bold text-white">
            {results.key_events?.length || 0}
          </p>
        </div>

        {/* Turning Points */}
        <div className="p-4 bg-black border border-white/10">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-4 h-4 text-white/40" />
            <span className="text-[10px] font-mono text-white/40 uppercase tracking-wider">
              Turning Points
            </span>
          </div>
          <p className="text-2xl font-mono font-bold text-white">
            {results.turning_points?.length || 0}
          </p>
        </div>
      </div>

      {/* Outcome Distribution */}
      {outcomeData.length > 0 && (
        <div className="bg-black border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-4">
            <Percent className="w-4 h-4 text-white/40" />
            <span className="text-xs font-mono text-white/40 uppercase tracking-wider">
              Outcome Distribution
            </span>
          </div>

          {/* Visual Bar */}
          <div className="h-8 flex overflow-hidden mb-4">
            {outcomeData.map((outcome) => (
              <div
                key={outcome.label}
                className={cn(
                  'h-full transition-all duration-500',
                  outcome.color
                )}
                style={{ width: `${outcome.percentage}%` }}
                title={`${outcome.label}: ${outcome.percentage.toFixed(1)}%`}
              />
            ))}
          </div>

          {/* Legend */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {outcomeData.map((outcome) => (
              <div
                key={outcome.label}
                className="flex items-center gap-2 p-2 bg-white/5 border border-white/10"
              >
                <div className={cn('w-3 h-3', outcome.color)} />
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-mono text-white truncate">
                    {outcome.label}
                  </p>
                  <p className="text-[10px] font-mono text-white/40">
                    {outcome.count.toLocaleString()} ({outcome.percentage.toFixed(1)}%)
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Dominant Outcome Highlight */}
      {dominantOutcome && (
        <div className="flex items-center justify-between p-4 bg-cyan-500/10 border border-cyan-500/30">
          <div className="flex items-center gap-3">
            <TrendingUp className="w-5 h-5 text-cyan-400" />
            <div>
              <p className="text-sm font-mono font-bold text-cyan-400">
                Dominant Outcome: {dominantOutcome.label}
              </p>
              <p className="text-xs font-mono text-cyan-400/60">
                {dominantOutcome.percentage.toFixed(1)}% of agents
              </p>
            </div>
          </div>
          <span className="text-2xl font-mono font-bold text-cyan-400">
            {dominantOutcome.count.toLocaleString()}
          </span>
        </div>
      )}

      {/* Key Events */}
      {results.key_events && results.key_events.length > 0 && (
        <div className="bg-black border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-4">
            <Zap className="w-4 h-4 text-yellow-400" />
            <span className="text-xs font-mono text-white/40 uppercase tracking-wider">
              Key Events
            </span>
          </div>
          <div className="space-y-2">
            {results.key_events.slice(0, 5).map((event, index) => (
              <div
                key={index}
                className="flex items-start gap-3 p-3 bg-white/5 border border-white/10"
              >
                <div className="text-xs font-mono text-white/40 w-16 flex-shrink-0">
                  Tick {event.tick}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-mono text-white font-bold">
                    {event.event_type}
                  </p>
                  <p className="text-[10px] font-mono text-white/60 mt-1">
                    {event.description}
                  </p>
                </div>
                <div className="text-xs font-mono text-cyan-400">
                  Impact: {event.impact_score.toFixed(2)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Turning Points */}
      {results.turning_points && results.turning_points.length > 0 && (
        <div className="bg-black border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-4">
            <GitBranch className="w-4 h-4 text-purple-400" />
            <span className="text-xs font-mono text-white/40 uppercase tracking-wider">
              Turning Points
            </span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {results.turning_points.slice(0, 8).map((tp, index) => (
              <div
                key={index}
                className="p-3 bg-white/5 border border-white/10"
              >
                <div className="flex items-center gap-2 mb-2">
                  {tp.direction === 'increase' ? (
                    <TrendingUp className="w-3 h-3 text-green-400" />
                  ) : (
                    <TrendingDown className="w-3 h-3 text-red-400" />
                  )}
                  <span className="text-xs font-mono text-white">{tp.metric}</span>
                </div>
                <p className="text-[10px] font-mono text-white/40">
                  Tick {tp.tick} • {tp.direction} by {tp.magnitude.toFixed(2)}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Metric Time Series Summary */}
      {results.metric_time_series && results.metric_time_series.length > 0 && (
        <div className="bg-black border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="w-4 h-4 text-white/40" />
            <span className="text-xs font-mono text-white/40 uppercase tracking-wider">
              Tracked Metrics
            </span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {results.metric_time_series.map((metric) => {
              const lastValue = metric.values[metric.values.length - 1]?.value ?? 0;
              const firstValue = metric.values[0]?.value ?? 0;
              const trend = lastValue > firstValue ? 'increase' : lastValue < firstValue ? 'decrease' : 'stable';
              return (
                <div
                  key={metric.metric_name}
                  className="p-3 bg-white/5 border border-white/10"
                >
                  <p className="text-xs font-mono text-white font-bold truncate">
                    {metric.metric_name}
                  </p>
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-lg font-mono text-white">
                      {lastValue.toFixed(2)}
                    </span>
                    {trend === 'increase' && <TrendingUp className="w-3 h-3 text-green-400" />}
                    {trend === 'decrease' && <TrendingDown className="w-3 h-3 text-red-400" />}
                  </div>
                  <p className="text-[10px] font-mono text-white/40">
                    {metric.values.length} data points
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-between pt-4 border-t border-white/10">
        <div className="flex items-start gap-2 text-[10px] font-mono text-white/30">
          <Info className="w-3 h-3 flex-shrink-0 mt-0.5" />
          <span>
            Run ID: {results.run_id}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {onViewTelemetry && (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => onViewTelemetry(runId)}
            >
              <BarChart3 className="w-3 h-3 mr-1" />
              View Telemetry
            </Button>
          )}
        </div>
      </div>
    </div>
  );
});

export default RunResults;

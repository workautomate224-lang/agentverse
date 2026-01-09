'use client';

/**
 * TelemetryMetrics Component
 * Displays time-series metric graphs for simulation telemetry.
 * Reference: project.md §6.8 (Telemetry), C3 (read-only replay)
 *
 * IMPORTANT: This is READ-ONLY. It must NEVER trigger new simulations.
 */

import { memo, useMemo, useState, useCallback } from 'react';
import {
  Activity,
  TrendingUp,
  TrendingDown,
  Minus,
  BarChart3,
  LineChart,
  ChevronDown,
  Eye,
  EyeOff,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

interface MetricSeries {
  id: string;
  name: string;
  unit?: string;
  color: string;
  data: { tick: number; value: number }[];
  visible?: boolean;
}

interface TelemetryMetricsProps {
  metrics: MetricSeries[];
  currentTick: number;
  totalTicks: number;
  onMetricToggle?: (metricId: string, visible: boolean) => void;
  height?: number;
  className?: string;
}

// Default colors for metrics
const METRIC_COLORS = [
  '#06b6d4', // cyan
  '#22c55e', // green
  '#eab308', // yellow
  '#ef4444', // red
  '#a855f7', // purple
  '#f97316', // orange
  '#ec4899', // pink
  '#14b8a6', // teal
];

// Calculate trend from recent values
function calculateTrend(data: { tick: number; value: number }[], currentTick: number): 'up' | 'down' | 'stable' {
  const recentData = data.filter(d => d.tick >= currentTick - 10 && d.tick <= currentTick);
  if (recentData.length < 2) return 'stable';

  const first = recentData[0].value;
  const last = recentData[recentData.length - 1].value;
  const change = ((last - first) / first) * 100;

  if (Math.abs(change) < 1) return 'stable';
  return change > 0 ? 'up' : 'down';
}

// Get current value at tick
function getValueAtTick(data: { tick: number; value: number }[], tick: number): number | null {
  const point = data.find(d => d.tick === tick);
  if (point) return point.value;

  // Interpolate if exact tick not found
  const before = [...data].reverse().find(d => d.tick <= tick);
  const after = data.find(d => d.tick >= tick);

  if (!before && !after) return null;
  if (!before) return after!.value;
  if (!after) return before.value;

  const ratio = (tick - before.tick) / (after.tick - before.tick);
  return before.value + (after.value - before.value) * ratio;
}

// Mini sparkline component
const Sparkline = memo(function Sparkline({
  data,
  currentTick,
  color,
  width = 100,
  height = 30,
}: {
  data: { tick: number; value: number }[];
  currentTick: number;
  color: string;
  width?: number;
  height?: number;
}) {
  const path = useMemo(() => {
    if (data.length < 2) return '';

    const minVal = Math.min(...data.map(d => d.value));
    const maxVal = Math.max(...data.map(d => d.value));
    const range = maxVal - minVal || 1;

    const maxTick = Math.max(...data.map(d => d.tick));
    const minTick = Math.min(...data.map(d => d.tick));
    const tickRange = maxTick - minTick || 1;

    const points = data.map(d => ({
      x: ((d.tick - minTick) / tickRange) * width,
      y: height - ((d.value - minVal) / range) * height,
    }));

    return `M ${points.map(p => `${p.x},${p.y}`).join(' L ')}`;
  }, [data, width, height]);

  const currentX = useMemo(() => {
    if (data.length === 0) return 0;
    const maxTick = Math.max(...data.map(d => d.tick));
    const minTick = Math.min(...data.map(d => d.tick));
    const tickRange = maxTick - minTick || 1;
    return ((currentTick - minTick) / tickRange) * width;
  }, [data, currentTick, width]);

  return (
    <svg width={width} height={height} className="overflow-visible">
      {/* Grid lines */}
      <line x1={0} y1={height / 2} x2={width} y2={height / 2} stroke="rgba(255,255,255,0.1)" strokeDasharray="2 2" />

      {/* Data line */}
      <path d={path} fill="none" stroke={color} strokeWidth={1.5} opacity={0.8} />

      {/* Current position indicator */}
      <line
        x1={currentX}
        y1={0}
        x2={currentX}
        y2={height}
        stroke={color}
        strokeWidth={1}
        strokeDasharray="2 2"
      />
    </svg>
  );
});

// Individual metric card
const MetricCard = memo(function MetricCard({
  metric,
  currentTick,
  onToggle,
}: {
  metric: MetricSeries;
  currentTick: number;
  onToggle?: (visible: boolean) => void;
}) {
  const currentValue = getValueAtTick(metric.data, currentTick);
  const trend = calculateTrend(metric.data, currentTick);
  const isVisible = metric.visible !== false;

  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus;
  const trendColor = trend === 'up' ? 'text-green-400' : trend === 'down' ? 'text-red-400' : 'text-white/40';

  return (
    <div
      className={cn(
        'p-3 bg-white/5 border border-white/10 transition-opacity',
        !isVisible && 'opacity-50'
      )}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div
            className="w-2 h-2 rounded-full"
            style={{ backgroundColor: metric.color }}
          />
          <span className="text-xs font-mono text-white/60">{metric.name}</span>
        </div>
        <button
          onClick={() => onToggle?.(!isVisible)}
          className="p-1 text-white/40 hover:text-white transition-colors"
        >
          {isVisible ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
        </button>
      </div>

      <div className="flex items-end justify-between">
        <div>
          <div className="text-lg font-mono font-bold text-white">
            {currentValue !== null ? currentValue.toFixed(2) : '--'}
          </div>
          {metric.unit && (
            <div className="text-[10px] font-mono text-white/40">{metric.unit}</div>
          )}
        </div>
        <div className="flex items-center gap-1">
          <TrendIcon className={cn('w-3 h-3', trendColor)} />
        </div>
      </div>

      {/* Sparkline */}
      <div className="mt-2">
        <Sparkline
          data={metric.data}
          currentTick={currentTick}
          color={metric.color}
          width={120}
          height={24}
        />
      </div>
    </div>
  );
});

// Main chart component
const MetricsChart = memo(function MetricsChart({
  metrics,
  currentTick,
  totalTicks,
  height = 200,
}: {
  metrics: MetricSeries[];
  currentTick: number;
  totalTicks: number;
  height?: number;
}) {
  const visibleMetrics = metrics.filter(m => m.visible !== false);

  // Calculate bounds
  const bounds = useMemo(() => {
    const allValues = visibleMetrics.flatMap(m => m.data.map(d => d.value));
    if (allValues.length === 0) return { min: 0, max: 100 };
    const min = Math.min(...allValues);
    const max = Math.max(...allValues);
    const padding = (max - min) * 0.1 || 10;
    return { min: min - padding, max: max + padding };
  }, [visibleMetrics]);

  const width = 600;

  return (
    <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="xMidYMid meet">
      {/* Background grid */}
      <defs>
        <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
          <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="1" />
        </pattern>
      </defs>
      <rect width={width} height={height} fill="url(#grid)" />

      {/* Y-axis labels */}
      {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
        const y = height - ratio * height;
        const value = bounds.min + ratio * (bounds.max - bounds.min);
        return (
          <g key={ratio}>
            <line x1={0} y1={y} x2={width} y2={y} stroke="rgba(255,255,255,0.1)" />
            <text x={5} y={y - 3} fill="rgba(255,255,255,0.3)" fontSize={8} fontFamily="monospace">
              {value.toFixed(1)}
            </text>
          </g>
        );
      })}

      {/* Data lines */}
      {visibleMetrics.map((metric) => {
        const range = bounds.max - bounds.min || 1;
        const points = metric.data.map((d) => ({
          x: (d.tick / totalTicks) * width,
          y: height - ((d.value - bounds.min) / range) * height,
        }));

        if (points.length < 2) return null;

        const path = `M ${points.map((p) => `${p.x},${p.y}`).join(' L ')}`;

        return (
          <g key={metric.id}>
            {/* Area fill */}
            <path
              d={`${path} L ${points[points.length - 1].x},${height} L ${points[0].x},${height} Z`}
              fill={metric.color}
              opacity={0.1}
            />
            {/* Line */}
            <path d={path} fill="none" stroke={metric.color} strokeWidth={2} />
          </g>
        );
      })}

      {/* Current tick indicator */}
      <line
        x1={(currentTick / totalTicks) * width}
        y1={0}
        x2={(currentTick / totalTicks) * width}
        y2={height}
        stroke="rgba(6,182,212,0.8)"
        strokeWidth={2}
        strokeDasharray="4 2"
      />
    </svg>
  );
});

export const TelemetryMetrics = memo(function TelemetryMetrics({
  metrics,
  currentTick,
  totalTicks,
  onMetricToggle,
  height = 200,
  className,
}: TelemetryMetricsProps) {
  const [viewMode, setViewMode] = useState<'chart' | 'cards'>('chart');
  const [showLegend, setShowLegend] = useState(true);

  // Assign colors to metrics if not provided
  const coloredMetrics = useMemo(() => {
    return metrics.map((m, i) => ({
      ...m,
      color: m.color || METRIC_COLORS[i % METRIC_COLORS.length],
      visible: m.visible !== false,
    }));
  }, [metrics]);

  const handleToggle = useCallback(
    (metricId: string, visible: boolean) => {
      onMetricToggle?.(metricId, visible);
    },
    [onMetricToggle]
  );

  return (
    <div className={cn('space-y-3', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-white/40" />
          <span className="text-xs font-mono text-white/40 uppercase tracking-wider">
            Metrics
          </span>
          <span className="text-[10px] font-mono text-white/30">
            ({coloredMetrics.length} series)
          </span>
        </div>

        <div className="flex items-center gap-1">
          <Button
            variant={viewMode === 'chart' ? 'secondary' : 'ghost'}
            size="icon-sm"
            onClick={() => setViewMode('chart')}
            title="Chart View"
          >
            <LineChart className="w-3 h-3" />
          </Button>
          <Button
            variant={viewMode === 'cards' ? 'secondary' : 'ghost'}
            size="icon-sm"
            onClick={() => setViewMode('cards')}
            title="Cards View"
          >
            <BarChart3 className="w-3 h-3" />
          </Button>
        </div>
      </div>

      {/* Main View */}
      {viewMode === 'chart' ? (
        <div className="bg-black border border-white/10 p-3">
          <MetricsChart
            metrics={coloredMetrics}
            currentTick={currentTick}
            totalTicks={totalTicks}
            height={height}
          />

          {/* Legend */}
          {showLegend && (
            <div className="flex flex-wrap gap-3 mt-3 pt-3 border-t border-white/10">
              {coloredMetrics.map((metric) => (
                <button
                  key={metric.id}
                  onClick={() => handleToggle(metric.id, !metric.visible)}
                  className={cn(
                    'flex items-center gap-2 px-2 py-1 text-xs font-mono transition-opacity',
                    metric.visible ? 'opacity-100' : 'opacity-40'
                  )}
                >
                  <div
                    className="w-3 h-1"
                    style={{ backgroundColor: metric.color }}
                  />
                  <span className="text-white/60">{metric.name}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
          {coloredMetrics.map((metric) => (
            <MetricCard
              key={metric.id}
              metric={metric}
              currentTick={currentTick}
              onToggle={(visible) => handleToggle(metric.id, visible)}
            />
          ))}
        </div>
      )}

      {/* Empty state */}
      {coloredMetrics.length === 0 && (
        <div className="flex items-center justify-center py-8 bg-black border border-white/10">
          <div className="text-center">
            <Activity className="w-6 h-6 text-white/20 mx-auto mb-2" />
            <p className="text-xs font-mono text-white/40">No metrics available</p>
          </div>
        </div>
      )}
    </div>
  );
});

export default TelemetryMetrics;

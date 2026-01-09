'use client';

/**
 * 2D Replay Timeline Component
 * Reference: project.md §11 Phase 8, Interaction_design.md §5.17
 *
 * Bottom panel with mini charts synced to playback position.
 * Shows aggregate metrics over time with current tick indicator.
 */

import React, { useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  ResponsiveContainer,
  ReferenceLine,
  Area,
  AreaChart,
} from 'recharts';
import { cn } from '@/lib/utils';

interface MetricPoint {
  tick: number;
  value: number;
}

interface MetricSeries {
  name: string;
  data: MetricPoint[];
  color: string;
}

interface ReplayTimelineProps {
  currentTick: number;
  totalTicks: number;
  metrics: MetricSeries[];
  onSeek: (tick: number) => void;
  height?: number;
  className?: string;
}

// Default metrics if none provided
const DEFAULT_METRICS: MetricSeries[] = [
  { name: 'Avg Stance', data: [], color: '#4ade80' },
  { name: 'Avg Emotion', data: [], color: '#fbbf24' },
  { name: 'Event Activity', data: [], color: '#a855f7' },
];

export function ReplayTimeline({
  currentTick,
  totalTicks,
  metrics,
  onSeek,
  height = 80,
  className,
}: ReplayTimelineProps) {
  // Use provided metrics or defaults
  const displayMetrics = metrics.length > 0 ? metrics : DEFAULT_METRICS;

  // Handle chart click
  const handleChartClick = (e: { activeLabel?: string | number }) => {
    if (e.activeLabel !== undefined) {
      const tick = typeof e.activeLabel === 'string' ? parseInt(e.activeLabel) : e.activeLabel;
      if (!isNaN(tick)) {
        onSeek(tick);
      }
    }
  };

  // Calculate current position percentage
  const currentPosition = totalTicks > 0 ? (currentTick / totalTicks) * 100 : 0;

  // Prepare chart data - combine all metrics into single dataset
  const chartData = useMemo(() => {
    if (displayMetrics.length === 0 || displayMetrics[0].data.length === 0) {
      // Generate placeholder data
      return Array.from({ length: Math.min(100, totalTicks || 100) }, (_, i) => ({
        tick: i,
        ...displayMetrics.reduce((acc, m) => ({ ...acc, [m.name]: 0 }), {}),
      }));
    }

    // Use the first metric's ticks as reference
    const refData = displayMetrics[0].data;
    return refData.map((point, idx) => {
      const dataPoint: Record<string, number> = { tick: point.tick };
      displayMetrics.forEach(metric => {
        dataPoint[metric.name] = metric.data[idx]?.value ?? 0;
      });
      return dataPoint;
    });
  }, [displayMetrics, totalTicks]);

  return (
    <div className={cn(
      'bg-black/80 border-t border-white/10',
      className
    )}>
      {/* Metric labels */}
      <div className="flex items-center gap-4 px-3 py-1 border-b border-white/5">
        {displayMetrics.map(metric => (
          <div key={metric.name} className="flex items-center gap-1 text-xs">
            <div
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: metric.color }}
            />
            <span className="text-white/60">{metric.name}</span>
          </div>
        ))}
        <div className="flex-1" />
        <span className="text-xs text-white/40 font-mono">
          T{currentTick} / {totalTicks}
        </span>
      </div>

      {/* Charts */}
      <div className="flex">
        {displayMetrics.map((metric, idx) => (
          <div
            key={metric.name}
            className="flex-1 border-r border-white/5 last:border-r-0"
            style={{ height }}
          >
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={chartData}
                margin={{ top: 5, right: 5, bottom: 5, left: 5 }}
                onClick={handleChartClick}
              >
                <defs>
                  <linearGradient id={`gradient-${idx}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={metric.color} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={metric.color} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis
                  dataKey="tick"
                  hide
                  domain={[0, totalTicks]}
                />
                <YAxis
                  hide
                  domain={[-1, 1]}
                />
                <Area
                  type="monotone"
                  dataKey={metric.name}
                  stroke={metric.color}
                  strokeWidth={1}
                  fill={`url(#gradient-${idx})`}
                  isAnimationActive={false}
                />
                {/* Current tick indicator */}
                <ReferenceLine
                  x={currentTick}
                  stroke="#00ffff"
                  strokeWidth={1}
                  strokeDasharray="3 3"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ))}
      </div>

      {/* Timeline ruler */}
      <div className="relative h-4 border-t border-white/5">
        {/* Progress bar */}
        <div
          className="absolute top-0 left-0 h-full bg-cyan-500/20 transition-all"
          style={{ width: `${currentPosition}%` }}
        />

        {/* Tick marks */}
        <div className="absolute inset-0 flex justify-between px-2">
          {[0, 25, 50, 75, 100].map(percent => {
            const tick = Math.round((percent / 100) * totalTicks);
            return (
              <span key={percent} className="text-[10px] text-white/30 font-mono">
                {tick}
              </span>
            );
          })}
        </div>

        {/* Current position indicator */}
        <div
          className="absolute top-0 w-0.5 h-full bg-cyan-400 transition-all"
          style={{ left: `${currentPosition}%` }}
        />
      </div>
    </div>
  );
}

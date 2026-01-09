'use client';

import { useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
} from 'recharts';
import { cn } from '@/lib/utils';
import { CHART_COLORS, formatNumber, calculateSignificance } from '@/lib/chartUtils';

interface ComparisonDataItem {
  name: string;
  [key: string]: string | number;
}

interface ComparisonChartProps {
  data: ComparisonDataItem[];
  seriesKeys: string[];
  seriesLabels?: Record<string, string>;
  title?: string;
  subtitle?: string;
  chartType?: 'bar' | 'grouped' | 'radar';
  showSignificance?: boolean;
  colors?: string[];
  className?: string;
  height?: number;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-black border border-white/20 p-3 font-mono">
        <p className="text-sm text-white font-bold mb-2">{label}</p>
        {payload.map((entry: any, index: number) => (
          <div key={index} className="flex items-center justify-between gap-4 text-xs">
            <span style={{ color: entry.color }}>{entry.name}</span>
            <span className="text-white">{formatNumber(entry.value)}</span>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

export function ComparisonChart({
  data,
  seriesKeys,
  seriesLabels = {},
  title,
  subtitle,
  chartType = 'grouped',
  showSignificance = true,
  colors = CHART_COLORS.categorical,
  className,
  height = 350,
}: ComparisonChartProps) {
  // Calculate significance between series
  const significanceResults = useMemo(() => {
    if (!showSignificance || seriesKeys.length < 2) return null;

    const results: Record<string, { isSignificant: boolean; pValue: number }> = {};

    // Compare first series to each other series
    const baseline = seriesKeys[0];
    const baselineValues = data.map(d => Number(d[baseline]) || 0);
    const baselineTotal = baselineValues.reduce((a, b) => a + b, 0);

    seriesKeys.slice(1).forEach(key => {
      const compareValues = data.map(d => Number(d[key]) || 0);
      const compareTotal = compareValues.reduce((a, b) => a + b, 0);

      // Normalize for chi-square
      const expected = baselineValues.map(v => (v / baselineTotal) * compareTotal);
      const { isSignificant, pValue } = calculateSignificance(compareValues, expected);

      results[key] = { isSignificant, pValue };
    });

    return results;
  }, [data, seriesKeys, showSignificance]);

  // Calculate comparison stats
  const stats = useMemo(() => {
    return seriesKeys.map(key => {
      const values = data.map(d => Number(d[key]) || 0);
      const total = values.reduce((a, b) => a + b, 0);
      const avg = total / values.length;
      const max = Math.max(...values);

      return {
        key,
        label: seriesLabels[key] || key,
        total,
        avg,
        max,
      };
    });
  }, [data, seriesKeys, seriesLabels]);

  if (data.length === 0) {
    return (
      <div className={cn("bg-white/5 border border-white/10 p-4", className)}>
        <div className="flex items-center justify-center h-[200px]">
          <p className="text-sm font-mono text-white/40">No data available</p>
        </div>
      </div>
    );
  }

  const renderChart = () => {
    if (chartType === 'radar') {
      return (
        <RadarChart cx="50%" cy="50%" outerRadius="80%" data={data}>
          <PolarGrid stroke="#404040" />
          <PolarAngleAxis
            dataKey="name"
            tick={{ fill: '#737373', fontSize: 10, fontFamily: 'monospace' }}
          />
          <PolarRadiusAxis
            tick={{ fill: '#525252', fontSize: 9, fontFamily: 'monospace' }}
            axisLine={false}
          />
          {seriesKeys.map((key, index) => (
            <Radar
              key={key}
              name={seriesLabels[key] || key}
              dataKey={key}
              stroke={colors[index % colors.length]}
              fill={colors[index % colors.length]}
              fillOpacity={0.2}
              strokeWidth={2}
            />
          ))}
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ fontSize: 10, fontFamily: 'monospace' }}
          />
        </RadarChart>
      );
    }

    return (
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#262626" vertical={false} />
        <XAxis
          dataKey="name"
          tick={{ fill: '#737373', fontSize: 10, fontFamily: 'monospace' }}
          axisLine={{ stroke: '#404040' }}
          tickLine={{ stroke: '#404040' }}
        />
        <YAxis
          tick={{ fill: '#737373', fontSize: 10, fontFamily: 'monospace' }}
          axisLine={{ stroke: '#404040' }}
          tickLine={{ stroke: '#404040' }}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend
          wrapperStyle={{ fontSize: 10, fontFamily: 'monospace' }}
        />
        {seriesKeys.map((key, index) => (
          <Bar
            key={key}
            dataKey={key}
            name={seriesLabels[key] || key}
            fill={colors[index % colors.length]}
            radius={[4, 4, 0, 0]}
          />
        ))}
      </BarChart>
    );
  };

  return (
    <div className={cn("bg-white/5 border border-white/10 p-4", className)}>
      {(title || subtitle) && (
        <div className="mb-4">
          {title && (
            <h3 className="text-sm font-mono font-bold text-white">{title}</h3>
          )}
          {subtitle && (
            <p className="text-[10px] font-mono text-white/40 mt-1">{subtitle}</p>
          )}
        </div>
      )}

      <ResponsiveContainer width="100%" height={height}>
        {renderChart()}
      </ResponsiveContainer>

      {/* Comparison Stats */}
      <div className="mt-4 pt-4 border-t border-white/10">
        <div className="grid gap-3" style={{ gridTemplateColumns: `repeat(${seriesKeys.length}, 1fr)` }}>
          {stats.map((stat, index) => (
            <div
              key={stat.key}
              className="p-3 border border-white/10"
              style={{ borderLeftColor: colors[index % colors.length], borderLeftWidth: 2 }}
            >
              <p className="text-[10px] font-mono text-white/40 uppercase mb-1">
                {stat.label}
              </p>
              <p className="text-lg font-mono font-bold text-white">
                {formatNumber(stat.total)}
              </p>
              <p className="text-[10px] font-mono text-white/40 mt-1">
                Avg: {formatNumber(stat.avg)} • Max: {formatNumber(stat.max)}
              </p>
              {showSignificance && significanceResults?.[stat.key] && (
                <p className={cn(
                  "text-[10px] font-mono mt-1",
                  significanceResults[stat.key].isSignificant ? "text-green-400" : "text-white/40"
                )}>
                  {significanceResults[stat.key].isSignificant ? '✓ Significant' : '○ Not significant'}
                  <span className="text-white/30 ml-1">
                    (p={significanceResults[stat.key].pValue.toFixed(3)})
                  </span>
                </p>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

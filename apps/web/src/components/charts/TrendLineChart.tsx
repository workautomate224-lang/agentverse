'use client';

import { useState, useCallback, useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
  Area,
  ComposedChart,
} from 'recharts';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { cn } from '@/lib/utils';
import { CHART_COLORS, formatNumber, calculateTrend, calculateConfidenceInterval, calculateMean, calculateStdDev } from '@/lib/chartUtils';

interface DataPoint {
  name: string;
  value: number;
  [key: string]: unknown;
}

interface TrendLineChartProps {
  data: DataPoint[];
  title?: string;
  subtitle?: string;
  onPointClick?: (data: DataPoint, index: number) => void;
  showGrid?: boolean;
  showTrendLine?: boolean;
  showConfidenceBand?: boolean;
  showArea?: boolean;
  multiSeries?: boolean;
  dataKeys?: string[];
  colors?: string[];
  className?: string;
  height?: number;
  confidenceLevel?: number;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-black border border-white/20 p-3 font-mono">
        <p className="text-sm text-white font-bold mb-1">{label}</p>
        {payload.map((entry: any, index: number) => (
          <p key={index} className="text-xs" style={{ color: entry.color }}>
            {entry.name}: <span className="text-white">{formatNumber(entry.value)}</span>
          </p>
        ))}
      </div>
    );
  }
  return null;
};

const CustomLegend = ({ payload, hiddenKeys, onClick }: any) => {
  return (
    <div className="flex flex-wrap justify-center gap-3 mt-2">
      {payload.map((entry: any, index: number) => (
        <button
          key={entry.value}
          onClick={() => onClick?.(entry.value)}
          className={cn(
            "flex items-center gap-1.5 px-2 py-1 transition-colors",
            hiddenKeys?.has(entry.value) ? "opacity-40" : "hover:bg-white/5"
          )}
        >
          <div
            className="w-3 h-0.5"
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-[10px] font-mono text-white/60">
            {entry.value}
          </span>
        </button>
      ))}
    </div>
  );
};

export function TrendLineChart({
  data,
  title,
  subtitle,
  onPointClick,
  showGrid = true,
  showTrendLine = true,
  showConfidenceBand = false,
  showArea = false,
  multiSeries = false,
  dataKeys = ['value'],
  colors = CHART_COLORS.categorical,
  className,
  height = 300,
  confidenceLevel = 0.95,
}: TrendLineChartProps) {
  const [hiddenKeys, setHiddenKeys] = useState<Set<string>>(new Set());

  const handleLegendClick = useCallback((key: string) => {
    setHiddenKeys(prev => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }, []);

  // Calculate trend for primary series
  const trend = useMemo(() => {
    const values = data.map(d => d.value);
    return calculateTrend(values);
  }, [data]);

  // Calculate confidence band
  const dataWithConfidence = useMemo(() => {
    if (!showConfidenceBand) return data;

    const values = data.map(d => d.value);
    const mean = calculateMean(values);
    const stdDev = calculateStdDev(values);
    const { lower, upper } = calculateConfidenceInterval(mean, stdDev, values.length, confidenceLevel);

    return data.map(d => ({
      ...d,
      confidenceLower: Math.max(0, d.value - (mean - lower)),
      confidenceUpper: d.value + (upper - mean),
    }));
  }, [data, showConfidenceBand, confidenceLevel]);

  // Generate trend line data
  const trendLineData = useMemo(() => {
    if (!showTrendLine || data.length < 2) return null;

    return data.map((d, i) => ({
      name: d.name,
      trendValue: trend.intercept + trend.slope * i,
    }));
  }, [data, showTrendLine, trend]);

  const TrendIcon = trend.direction === 'up' ? TrendingUp : trend.direction === 'down' ? TrendingDown : Minus;
  const trendColor = trend.direction === 'up' ? 'text-green-400' : trend.direction === 'down' ? 'text-red-400' : 'text-white/40';

  if (data.length === 0) {
    return (
      <div className={cn("bg-white/5 border border-white/10 p-4", className)}>
        <div className="flex items-center justify-center h-[200px]">
          <p className="text-sm font-mono text-white/40">No data available</p>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("bg-white/5 border border-white/10 p-4", className)}>
      {(title || subtitle) && (
        <div className="flex items-start justify-between mb-4">
          <div>
            {title && (
              <h3 className="text-sm font-mono font-bold text-white">{title}</h3>
            )}
            {subtitle && (
              <p className="text-[10px] font-mono text-white/40 mt-1">{subtitle}</p>
            )}
          </div>
          {showTrendLine && (
            <div className={cn("flex items-center gap-1 px-2 py-1 bg-white/5", trendColor)}>
              <TrendIcon className="w-3 h-3" />
              <span className="text-[10px] font-mono">
                {trend.direction === 'flat' ? 'Stable' : `${trend.slope > 0 ? '+' : ''}${(trend.slope * 100).toFixed(1)}%`}
              </span>
            </div>
          )}
        </div>
      )}

      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart data={dataWithConfidence}>
          {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="#262626" vertical={false} />}
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
          {multiSeries && (
            <Legend content={<CustomLegend hiddenKeys={hiddenKeys} onClick={handleLegendClick} />} />
          )}

          {/* Confidence band */}
          {showConfidenceBand && (
            <Area
              type="monotone"
              dataKey="confidenceUpper"
              stroke="none"
              fill={colors[0]}
              fillOpacity={0.1}
            />
          )}

          {/* Main data lines */}
          {dataKeys.map((key, keyIndex) => (
            !hiddenKeys.has(key) && (
              <Line
                key={key}
                type="monotone"
                dataKey={key}
                stroke={colors[keyIndex % colors.length]}
                strokeWidth={2}
                dot={{ fill: colors[keyIndex % colors.length], strokeWidth: 0, r: 3 }}
                activeDot={{
                  r: 5,
                  fill: '#fff',
                  onClick: onPointClick ? (event: unknown, payload: unknown) => {
                    const dataPoint = payload as DataPoint;
                    if (dataPoint) {
                      onPointClick(dataPoint, 0);
                    }
                  } : undefined
                }}
                style={{ cursor: onPointClick ? 'pointer' : 'default' }}
              />
            )
          ))}

          {/* Trend line */}
          {showTrendLine && trendLineData && (
            <Line
              data={trendLineData}
              type="monotone"
              dataKey="trendValue"
              stroke="#f59e0b"
              strokeWidth={1}
              strokeDasharray="5 5"
              dot={false}
              name="Trend"
            />
          )}

          {/* Mean reference line */}
          <ReferenceLine
            y={calculateMean(data.map(d => d.value))}
            stroke="#525252"
            strokeDasharray="3 3"
          />
        </ComposedChart>
      </ResponsiveContainer>

      {/* Trend Statistics */}
      <div className="mt-4 pt-4 border-t border-white/10 grid grid-cols-4 gap-4">
        <div>
          <p className="text-[10px] font-mono text-white/40">Trend</p>
          <p className={cn("text-sm font-mono flex items-center gap-1", trendColor)}>
            <TrendIcon className="w-3 h-3" />
            {trend.direction.charAt(0).toUpperCase() + trend.direction.slice(1)}
          </p>
        </div>
        <div>
          <p className="text-[10px] font-mono text-white/40">R²</p>
          <p className="text-sm font-mono text-white">
            {(trend.rSquared * 100).toFixed(1)}%
          </p>
        </div>
        <div>
          <p className="text-[10px] font-mono text-white/40">Start</p>
          <p className="text-sm font-mono text-white">
            {formatNumber(data[0]?.value || 0)}
          </p>
        </div>
        <div>
          <p className="text-[10px] font-mono text-white/40">End</p>
          <p className="text-sm font-mono text-white">
            {formatNumber(data[data.length - 1]?.value || 0)}
          </p>
        </div>
      </div>
    </div>
  );
}

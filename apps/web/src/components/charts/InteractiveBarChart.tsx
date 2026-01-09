'use client';

import { useState, useCallback } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from 'recharts';
import { cn } from '@/lib/utils';
import { CHART_COLORS, formatNumber, calculateMean } from '@/lib/chartUtils';

interface DataItem {
  name: string;
  value: number;
  [key: string]: unknown;
}

interface InteractiveBarChartProps {
  data: DataItem[];
  title?: string;
  subtitle?: string;
  onBarClick?: (data: DataItem, index: number) => void;
  showGrid?: boolean;
  showLegend?: boolean;
  showMeanLine?: boolean;
  horizontal?: boolean;
  stacked?: boolean;
  dataKeys?: string[];
  colors?: string[];
  className?: string;
  height?: number;
  barSize?: number;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-black border border-white/20 p-3 font-mono">
        <p className="text-sm text-white font-bold mb-1">{label}</p>
        {payload.map((entry: any, index: number) => (
          <p key={index} className="text-xs text-white/60">
            {entry.name}: <span className="text-white">{formatNumber(entry.value)}</span>
          </p>
        ))}
      </div>
    );
  }
  return null;
};

const CustomLegend = ({ payload, onClick }: any) => {
  return (
    <div className="flex flex-wrap justify-center gap-3 mt-2">
      {payload.map((entry: any, index: number) => (
        <button
          key={entry.value}
          onClick={() => onClick?.(entry, index)}
          className="flex items-center gap-1.5 px-2 py-1 hover:bg-white/5 transition-colors"
        >
          <div
            className="w-3 h-3"
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

export function InteractiveBarChart({
  data,
  title,
  subtitle,
  onBarClick,
  showGrid = true,
  showLegend = false,
  showMeanLine = false,
  horizontal = false,
  stacked = false,
  dataKeys = ['value'],
  colors = CHART_COLORS.categorical,
  className,
  height = 300,
  barSize = 30,
}: InteractiveBarChartProps) {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);
  const [hiddenKeys, setHiddenKeys] = useState<Set<string>>(new Set());

  const handleBarClick = useCallback(
    (data: DataItem, index: number) => {
      onBarClick?.(data, index);
    },
    [onBarClick]
  );

  const handleLegendClick = useCallback((entry: any) => {
    setHiddenKeys(prev => {
      const next = new Set(prev);
      if (next.has(entry.value)) {
        next.delete(entry.value);
      } else {
        next.add(entry.value);
      }
      return next;
    });
  }, []);

  const mean = showMeanLine ? calculateMean(data.map(d => d.value)) : 0;

  if (data.length === 0) {
    return (
      <div className={cn("bg-white/5 border border-white/10 p-4", className)}>
        <div className="flex items-center justify-center h-[200px]">
          <p className="text-sm font-mono text-white/40">No data available</p>
        </div>
      </div>
    );
  }

  const ChartComponent = horizontal ? (
    <BarChart data={data} layout="vertical" margin={{ left: 60 }}>
      {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="#262626" />}
      <XAxis
        type="number"
        tick={{ fill: '#737373', fontSize: 10, fontFamily: 'monospace' }}
        axisLine={{ stroke: '#404040' }}
        tickLine={{ stroke: '#404040' }}
      />
      <YAxis
        dataKey="name"
        type="category"
        tick={{ fill: '#737373', fontSize: 10, fontFamily: 'monospace' }}
        axisLine={{ stroke: '#404040' }}
        tickLine={{ stroke: '#404040' }}
        width={80}
      />
      <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.05)' }} />
      {showLegend && <Legend content={<CustomLegend onClick={handleLegendClick} />} />}
      {dataKeys.map((key, keyIndex) => (
        !hiddenKeys.has(key) && (
          <Bar
            key={key}
            dataKey={key}
            fill={colors[keyIndex % colors.length]}
            barSize={barSize}
            onClick={(data, index) => handleBarClick(data, index)}
            style={{ cursor: onBarClick ? 'pointer' : 'default' }}
            stackId={stacked ? 'stack' : undefined}
          >
            {data.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={activeIndex === index ? '#fff' : colors[keyIndex % colors.length]}
                onMouseEnter={() => setActiveIndex(index)}
                onMouseLeave={() => setActiveIndex(null)}
              />
            ))}
          </Bar>
        )
      ))}
    </BarChart>
  ) : (
    <BarChart data={data}>
      {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="#262626" vertical={false} />}
      <XAxis
        dataKey="name"
        tick={{ fill: '#737373', fontSize: 10, fontFamily: 'monospace' }}
        axisLine={{ stroke: '#404040' }}
        tickLine={{ stroke: '#404040' }}
        interval={0}
        angle={data.length > 8 ? -45 : 0}
        textAnchor={data.length > 8 ? 'end' : 'middle'}
        height={data.length > 8 ? 80 : 30}
      />
      <YAxis
        tick={{ fill: '#737373', fontSize: 10, fontFamily: 'monospace' }}
        axisLine={{ stroke: '#404040' }}
        tickLine={{ stroke: '#404040' }}
      />
      <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.05)' }} />
      {showLegend && <Legend content={<CustomLegend onClick={handleLegendClick} />} />}
      {showMeanLine && (
        <ReferenceLine
          y={mean}
          stroke="#f59e0b"
          strokeDasharray="5 5"
          label={{
            value: `Mean: ${formatNumber(mean)}`,
            fill: '#f59e0b',
            fontSize: 10,
            fontFamily: 'monospace',
          }}
        />
      )}
      {dataKeys.map((key, keyIndex) => (
        !hiddenKeys.has(key) && (
          <Bar
            key={key}
            dataKey={key}
            fill={colors[keyIndex % colors.length]}
            barSize={barSize}
            onClick={(data, index) => handleBarClick(data, index)}
            style={{ cursor: onBarClick ? 'pointer' : 'default' }}
            stackId={stacked ? 'stack' : undefined}
            radius={[4, 4, 0, 0]}
          >
            {data.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={activeIndex === index ? '#fff' : colors[keyIndex % colors.length]}
                onMouseEnter={() => setActiveIndex(index)}
                onMouseLeave={() => setActiveIndex(null)}
              />
            ))}
          </Bar>
        )
      ))}
    </BarChart>
  );

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
        {ChartComponent}
      </ResponsiveContainer>

      {/* Quick Stats */}
      <div className="mt-4 pt-4 border-t border-white/10 grid grid-cols-3 gap-4">
        <div>
          <p className="text-[10px] font-mono text-white/40">Max</p>
          <p className="text-sm font-mono text-white">
            {formatNumber(Math.max(...data.map(d => d.value)))}
          </p>
        </div>
        <div>
          <p className="text-[10px] font-mono text-white/40">Mean</p>
          <p className="text-sm font-mono text-white">
            {formatNumber(calculateMean(data.map(d => d.value)))}
          </p>
        </div>
        <div>
          <p className="text-[10px] font-mono text-white/40">Min</p>
          <p className="text-sm font-mono text-white">
            {formatNumber(Math.min(...data.map(d => d.value)))}
          </p>
        </div>
      </div>
    </div>
  );
}

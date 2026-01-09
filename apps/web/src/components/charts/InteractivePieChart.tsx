'use client';

import { useState, useCallback } from 'react';
import {
  PieChart,
  Pie,
  Cell,
  Sector,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from 'recharts';
import { cn } from '@/lib/utils';
import { CHART_COLORS, formatPercent } from '@/lib/chartUtils';

interface DataItem {
  name: string;
  value: number;
  color?: string;
  [key: string]: unknown;
}

interface InteractivePieChartProps {
  data: DataItem[];
  title?: string;
  subtitle?: string;
  onSliceClick?: (data: DataItem, index: number) => void;
  showLegend?: boolean;
  showLabels?: boolean;
  innerRadius?: number;
  outerRadius?: number;
  colors?: string[];
  className?: string;
  height?: number;
}

// Active shape renderer for hover effect
const renderActiveShape = (props: any) => {
  const {
    cx,
    cy,
    innerRadius,
    outerRadius,
    startAngle,
    endAngle,
    fill,
    payload,
    percent,
    value,
  } = props;

  return (
    <g>
      <text
        x={cx}
        y={cy - 10}
        textAnchor="middle"
        fill="#fff"
        className="text-sm font-mono font-bold"
      >
        {payload.name}
      </text>
      <text
        x={cx}
        y={cy + 10}
        textAnchor="middle"
        fill="#a3a3a3"
        className="text-xs font-mono"
      >
        {value.toLocaleString()} ({(percent * 100).toFixed(1)}%)
      </text>
      <Sector
        cx={cx}
        cy={cy}
        innerRadius={innerRadius}
        outerRadius={outerRadius + 8}
        startAngle={startAngle}
        endAngle={endAngle}
        fill={fill}
      />
      <Sector
        cx={cx}
        cy={cy}
        startAngle={startAngle}
        endAngle={endAngle}
        innerRadius={outerRadius + 10}
        outerRadius={outerRadius + 14}
        fill={fill}
      />
    </g>
  );
};

const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-black border border-white/20 p-3 font-mono">
        <p className="text-sm text-white font-bold">{data.name}</p>
        <p className="text-xs text-white/60">
          Value: <span className="text-white">{data.value.toLocaleString()}</span>
        </p>
        <p className="text-xs text-white/60">
          Share: <span className="text-white">{formatPercent(data.value / payload[0].payload.total || 0)}</span>
        </p>
      </div>
    );
  }
  return null;
};

const CustomLegend = ({ payload, onClick }: any) => {
  return (
    <div className="flex flex-wrap justify-center gap-3 mt-4">
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

export function InteractivePieChart({
  data,
  title,
  subtitle,
  onSliceClick,
  showLegend = true,
  showLabels = false,
  innerRadius = 60,
  outerRadius = 100,
  colors = CHART_COLORS.categorical,
  className,
  height = 300,
}: InteractivePieChartProps) {
  const [activeIndex, setActiveIndex] = useState<number | undefined>(undefined);

  const onPieEnter = useCallback((_: any, index: number) => {
    setActiveIndex(index);
  }, []);

  const onPieLeave = useCallback(() => {
    setActiveIndex(undefined);
  }, []);

  const handleClick = useCallback(
    (data: DataItem, index: number) => {
      onSliceClick?.(data, index);
    },
    [onSliceClick]
  );

  // Calculate total for percentages
  const total = data.reduce((sum, item) => sum + item.value, 0);
  const dataWithTotal = data.map(item => ({ ...item, total }));

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
        <PieChart>
          <Pie
            data={dataWithTotal}
            cx="50%"
            cy="50%"
            innerRadius={innerRadius}
            outerRadius={outerRadius}
            dataKey="value"
            activeIndex={activeIndex}
            activeShape={renderActiveShape}
            onMouseEnter={onPieEnter}
            onMouseLeave={onPieLeave}
            onClick={(data, index) => handleClick(data, index)}
            label={showLabels ? ({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%` : undefined}
            labelLine={showLabels}
            style={{ cursor: onSliceClick ? 'pointer' : 'default' }}
          >
            {data.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.color || colors[index % colors.length]}
                stroke="transparent"
              />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          {showLegend && (
            <Legend
              content={<CustomLegend onClick={handleClick} />}
              verticalAlign="bottom"
            />
          )}
        </PieChart>
      </ResponsiveContainer>

      {/* Summary Stats */}
      <div className="mt-4 pt-4 border-t border-white/10">
        <div className="flex justify-between text-[10px] font-mono">
          <span className="text-white/40">Total</span>
          <span className="text-white">{total.toLocaleString()}</span>
        </div>
        <div className="flex justify-between text-[10px] font-mono mt-1">
          <span className="text-white/40">Categories</span>
          <span className="text-white">{data.length}</span>
        </div>
      </div>
    </div>
  );
}

'use client';

import { useState, useMemo } from 'react';
import { cn } from '@/lib/utils';
import { generateGradient, formatNumber } from '@/lib/chartUtils';

interface HeatmapChartProps {
  data: {
    rows: string[];
    cols: string[];
    values: number[][];
  };
  title?: string;
  subtitle?: string;
  onCellClick?: (row: string, col: string, value: number) => void;
  colorScale?: { low: string; mid: string; high: string };
  showValues?: boolean;
  showLegend?: boolean;
  className?: string;
  cellSize?: number;
}

export function HeatmapChart({
  data,
  title,
  subtitle,
  onCellClick,
  colorScale = { low: '#1e3a5f', mid: '#3b82f6', high: '#ef4444' },
  showValues = true,
  showLegend = true,
  className,
  cellSize = 40,
}: HeatmapChartProps) {
  const [hoveredCell, setHoveredCell] = useState<{ row: number; col: number } | null>(null);

  // Calculate min, max for color scaling
  const { minValue, maxValue, midValue } = useMemo(() => {
    const flatValues = data.values.flat();
    const min = Math.min(...flatValues);
    const max = Math.max(...flatValues);
    return { minValue: min, maxValue: max, midValue: (min + max) / 2 };
  }, [data.values]);

  // Generate color for a value
  const getColor = (value: number): string => {
    if (maxValue === minValue) return colorScale.mid;

    const ratio = (value - minValue) / (maxValue - minValue);

    if (ratio < 0.5) {
      // Interpolate between low and mid
      const t = ratio * 2;
      return interpolateColor(colorScale.low, colorScale.mid, t);
    } else {
      // Interpolate between mid and high
      const t = (ratio - 0.5) * 2;
      return interpolateColor(colorScale.mid, colorScale.high, t);
    }
  };

  // Color interpolation helper
  const interpolateColor = (color1: string, color2: string, t: number): string => {
    const rgb1 = hexToRgb(color1);
    const rgb2 = hexToRgb(color2);
    if (!rgb1 || !rgb2) return color1;

    const r = Math.round(rgb1.r + (rgb2.r - rgb1.r) * t);
    const g = Math.round(rgb1.g + (rgb2.g - rgb1.g) * t);
    const b = Math.round(rgb1.b + (rgb2.b - rgb1.b) * t);

    return `rgb(${r}, ${g}, ${b})`;
  };

  const hexToRgb = (hex: string): { r: number; g: number; b: number } | null => {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result
      ? {
          r: parseInt(result[1], 16),
          g: parseInt(result[2], 16),
          b: parseInt(result[3], 16),
        }
      : null;
  };

  const getTextColor = (bgColor: string): string => {
    const rgb = hexToRgb(bgColor) || { r: 0, g: 0, b: 0 };
    // Calculate relative luminance
    const luminance = (0.299 * rgb.r + 0.587 * rgb.g + 0.114 * rgb.b) / 255;
    return luminance > 0.5 ? '#000' : '#fff';
  };

  if (data.rows.length === 0 || data.cols.length === 0) {
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

      <div className="overflow-x-auto">
        <div className="inline-block">
          {/* Column headers */}
          <div className="flex" style={{ marginLeft: 100 }}>
            {data.cols.map((col, colIndex) => (
              <div
                key={col}
                className="text-[10px] font-mono text-white/60 text-center truncate"
                style={{ width: cellSize, padding: '4px 2px' }}
                title={col}
              >
                {col.length > 6 ? col.slice(0, 5) + '…' : col}
              </div>
            ))}
          </div>

          {/* Rows */}
          {data.rows.map((row, rowIndex) => (
            <div key={row} className="flex items-center">
              {/* Row label */}
              <div
                className="text-[10px] font-mono text-white/60 truncate text-right pr-2"
                style={{ width: 100 }}
                title={row}
              >
                {row}
              </div>

              {/* Cells */}
              {data.cols.map((col, colIndex) => {
                const value = data.values[rowIndex]?.[colIndex] ?? 0;
                const bgColor = getColor(value);
                const isHovered = hoveredCell?.row === rowIndex && hoveredCell?.col === colIndex;

                return (
                  <button
                    key={`${row}-${col}`}
                    className={cn(
                      "flex items-center justify-center transition-all border",
                      isHovered ? "border-white z-10 scale-110" : "border-transparent",
                      onCellClick && "cursor-pointer"
                    )}
                    style={{
                      width: cellSize,
                      height: cellSize,
                      backgroundColor: bgColor,
                    }}
                    onMouseEnter={() => setHoveredCell({ row: rowIndex, col: colIndex })}
                    onMouseLeave={() => setHoveredCell(null)}
                    onClick={() => onCellClick?.(row, col, value)}
                    title={`${row} × ${col}: ${formatNumber(value)}`}
                  >
                    {showValues && (
                      <span
                        className="text-[9px] font-mono font-bold"
                        style={{ color: isHovered ? '#fff' : getTextColor(bgColor) }}
                      >
                        {value >= 1000 ? formatNumber(value) : value.toFixed(0)}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      </div>

      {/* Legend */}
      {showLegend && (
        <div className="mt-4 pt-4 border-t border-white/10">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-white/40">
              {formatNumber(minValue)}
            </span>
            <div
              className="flex-1 h-3 mx-2"
              style={{
                background: `linear-gradient(to right, ${colorScale.low}, ${colorScale.mid}, ${colorScale.high})`,
              }}
            />
            <span className="text-[10px] font-mono text-white/40">
              {formatNumber(maxValue)}
            </span>
          </div>
        </div>
      )}

      {/* Hover tooltip */}
      {hoveredCell && (
        <div className="mt-4 p-3 bg-white/5 border border-white/10">
          <div className="flex items-center justify-between text-xs font-mono">
            <span className="text-white/60">
              {data.rows[hoveredCell.row]} × {data.cols[hoveredCell.col]}
            </span>
            <span className="text-white font-bold">
              {formatNumber(data.values[hoveredCell.row]?.[hoveredCell.col] ?? 0)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Chart Utility Functions
 * Color schemes, statistical functions, and chart helpers
 */

// Color palettes for different chart types
export const CHART_COLORS = {
  primary: ['#3b82f6', '#60a5fa', '#93c5fd', '#bfdbfe', '#dbeafe'],
  sentiment: {
    positive: '#22c55e',
    neutral: '#a3a3a3',
    negative: '#ef4444',
  },
  sequential: ['#0a0a0a', '#171717', '#262626', '#404040', '#525252', '#737373', '#a3a3a3', '#d4d4d4', '#ffffff'],
  categorical: ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'],
  monochrome: ['#ffffff', '#e5e5e5', '#a3a3a3', '#737373', '#525252', '#262626', '#171717', '#0a0a0a'],
  heatmap: ['#1e3a5f', '#2563eb', '#60a5fa', '#93c5fd', '#f97316', '#dc2626'],
};

// Get color by index with wrapping
export function getChartColor(index: number, palette: string[] = CHART_COLORS.categorical): string {
  return palette[index % palette.length];
}

// Generate gradient colors between two colors
export function generateGradient(startColor: string, endColor: string, steps: number): string[] {
  const start = hexToRgb(startColor);
  const end = hexToRgb(endColor);
  if (!start || !end) return Array(steps).fill(startColor);

  return Array.from({ length: steps }, (_, i) => {
    const ratio = i / (steps - 1);
    const r = Math.round(start.r + (end.r - start.r) * ratio);
    const g = Math.round(start.g + (end.g - start.g) * ratio);
    const b = Math.round(start.b + (end.b - start.b) * ratio);
    return rgbToHex(r, g, b);
  });
}

function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result
    ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16),
      }
    : null;
}

function rgbToHex(r: number, g: number, b: number): string {
  return '#' + [r, g, b].map(x => x.toString(16).padStart(2, '0')).join('');
}

// Statistical functions
export function calculateMean(values: number[]): number {
  if (values.length === 0) return 0;
  return values.reduce((sum, val) => sum + val, 0) / values.length;
}

export function calculateStdDev(values: number[]): number {
  if (values.length === 0) return 0;
  const mean = calculateMean(values);
  const squaredDiffs = values.map(val => Math.pow(val - mean, 2));
  return Math.sqrt(squaredDiffs.reduce((sum, val) => sum + val, 0) / values.length);
}

export function calculateMedian(values: number[]): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 !== 0 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

export function calculatePercentile(values: number[], percentile: number): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const index = (percentile / 100) * (sorted.length - 1);
  const lower = Math.floor(index);
  const upper = Math.ceil(index);
  const weight = index - lower;
  return sorted[lower] * (1 - weight) + sorted[upper] * weight;
}

// Statistical significance (chi-square approximation)
export function calculateSignificance(
  observed: number[],
  expected: number[]
): { chiSquare: number; pValue: number; isSignificant: boolean } {
  if (observed.length !== expected.length || observed.length === 0) {
    return { chiSquare: 0, pValue: 1, isSignificant: false };
  }

  const chiSquare = observed.reduce((sum, obs, i) => {
    const exp = expected[i];
    if (exp === 0) return sum;
    return sum + Math.pow(obs - exp, 2) / exp;
  }, 0);

  const df = observed.length - 1;
  // Simplified p-value estimation
  const pValue = 1 - chiSquareCDF(chiSquare, df);

  return {
    chiSquare,
    pValue,
    isSignificant: pValue < 0.05,
  };
}

// Simplified chi-square CDF approximation
function chiSquareCDF(x: number, k: number): number {
  if (x < 0) return 0;
  if (k <= 0) return 0;

  // Wilson-Hilferty approximation
  const z = Math.pow(x / k, 1/3) - (1 - 2/(9*k));
  const stdDev = Math.sqrt(2/(9*k));

  // Standard normal CDF approximation
  return 0.5 * (1 + erf(z / (stdDev * Math.sqrt(2))));
}

// Error function approximation
function erf(x: number): number {
  const a1 =  0.254829592;
  const a2 = -0.284496736;
  const a3 =  1.421413741;
  const a4 = -1.453152027;
  const a5 =  1.061405429;
  const p  =  0.3275911;

  const sign = x < 0 ? -1 : 1;
  x = Math.abs(x);

  const t = 1.0 / (1.0 + p * x);
  const y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * Math.exp(-x * x);

  return sign * y;
}

// Confidence interval calculation
export function calculateConfidenceInterval(
  mean: number,
  stdDev: number,
  sampleSize: number,
  confidence: number = 0.95
): { lower: number; upper: number } {
  // Z-scores for common confidence levels
  const zScores: Record<number, number> = {
    0.90: 1.645,
    0.95: 1.96,
    0.99: 2.576,
  };

  const z = zScores[confidence] || 1.96;
  const standardError = stdDev / Math.sqrt(sampleSize);
  const marginOfError = z * standardError;

  return {
    lower: mean - marginOfError,
    upper: mean + marginOfError,
  };
}

// Format numbers for display
export function formatNumber(value: number, decimals: number = 1): string {
  if (Math.abs(value) >= 1000000) {
    return (value / 1000000).toFixed(decimals) + 'M';
  }
  if (Math.abs(value) >= 1000) {
    return (value / 1000).toFixed(decimals) + 'K';
  }
  return value.toFixed(decimals);
}

export function formatPercent(value: number, decimals: number = 1): string {
  return (value * 100).toFixed(decimals) + '%';
}

// Data transformation utilities
export function groupBy<T>(array: T[], key: keyof T): Record<string, T[]> {
  return array.reduce((result, item) => {
    const groupKey = String(item[key]);
    (result[groupKey] = result[groupKey] || []).push(item);
    return result;
  }, {} as Record<string, T[]>);
}

export function aggregateByKey<T>(
  data: T[],
  groupKey: keyof T,
  valueKey: keyof T,
  aggregateFn: (values: number[]) => number = calculateMean
): { name: string; value: number }[] {
  const grouped = groupBy(data, groupKey);
  return Object.entries(grouped).map(([name, items]) => ({
    name,
    value: aggregateFn(items.map(item => Number(item[valueKey]))),
  }));
}

// Cross-tabulation for heatmaps
export function crossTabulate<T>(
  data: T[],
  rowKey: keyof T,
  colKey: keyof T,
  valueKey?: keyof T
): { rows: string[]; cols: string[]; values: number[][] } {
  const rowValues = [...new Set(data.map(d => String(d[rowKey])))].sort();
  const colValues = [...new Set(data.map(d => String(d[colKey])))].sort();

  const values = rowValues.map(row =>
    colValues.map(col => {
      const matches = data.filter(
        d => String(d[rowKey]) === row && String(d[colKey]) === col
      );
      if (valueKey) {
        return matches.reduce((sum, m) => sum + Number(m[valueKey]), 0) / (matches.length || 1);
      }
      return matches.length;
    })
  );

  return { rows: rowValues, cols: colValues, values };
}

// Trend calculation
export function calculateTrend(values: number[]): {
  slope: number;
  intercept: number;
  rSquared: number;
  direction: 'up' | 'down' | 'flat';
} {
  if (values.length < 2) {
    return { slope: 0, intercept: values[0] || 0, rSquared: 0, direction: 'flat' };
  }

  const n = values.length;
  const xMean = (n - 1) / 2;
  const yMean = calculateMean(values);

  let ssXX = 0;
  let ssXY = 0;
  let ssYY = 0;

  for (let i = 0; i < n; i++) {
    const xDiff = i - xMean;
    const yDiff = values[i] - yMean;
    ssXX += xDiff * xDiff;
    ssXY += xDiff * yDiff;
    ssYY += yDiff * yDiff;
  }

  const slope = ssXX === 0 ? 0 : ssXY / ssXX;
  const intercept = yMean - slope * xMean;
  const rSquared = ssYY === 0 ? 0 : (ssXY * ssXY) / (ssXX * ssYY);

  let direction: 'up' | 'down' | 'flat' = 'flat';
  if (Math.abs(slope) > 0.01) {
    direction = slope > 0 ? 'up' : 'down';
  }

  return { slope, intercept, rSquared, direction };
}

'use client';

/**
 * Reliability Page
 * Node-aware reliability dashboard showing trust metrics for runs and telemetry data.
 * Route: /p/{projectId}/reliability?node={nodeId}
 *
 * Questions this page answers:
 * - Can I trust this run?
 * - Is this branch better than baseline?
 * - Do I have enough telemetry?
 */

import { useState, useMemo, useEffect } from 'react';
import { useParams, useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  ShieldCheck,
  ArrowLeft,
  Activity,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Info,
  ChevronDown,
  Database,
  GitBranch,
  Play,
  Layers,
  BarChart3,
  ExternalLink,
  RefreshCw,
  Target,
  Loader2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useNodes, useRuns, useTelemetryIndex, useTelemetrySummary, usePhase6ReliabilitySummary } from '@/hooks/useApi';
import type { NodeSummary, RunSummary, TelemetryIndex, TelemetrySummary, SpecRunStatus, Phase6ReliabilitySummaryResponse, Phase6ReliabilityQueryParams } from '@/lib/api';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  ReferenceLine,
} from 'recharts';

// ============================================================================
// Types for Reliability Metrics
// ============================================================================

interface ReliabilityMetrics {
  coverageScore: number; // 0-100
  integrityScore: number; // 0-100
  activityScore: number; // 0-100
  stabilityScore: number | null; // 0-100, null if insufficient data
  overallScore: number; // 0-100
}

interface ReliabilityWarning {
  type: 'error' | 'warning' | 'info';
  message: string;
  fixAction?: {
    label: string;
    href: string;
  };
}

interface BranchComparison {
  baselineRunId: string;
  branchRunId: string;
  divergencePercent: number;
  metricsDelta: {
    coverage: number;
    activity: number;
    integrity: number;
  };
}

// ============================================================================
// Metric Computation Functions
// ============================================================================

function computeCoverageScore(telemetryIndex: TelemetryIndex | null | undefined): number {
  if (!telemetryIndex) return 0;
  const { total_ticks, keyframe_ticks } = telemetryIndex;
  if (total_ticks === 0) return 0;
  // Coverage = percentage of ticks that have keyframes
  const coverage = (keyframe_ticks.length / total_ticks) * 100;
  return Math.min(100, Math.round(coverage * 10)); // Scale up since keyframes are sparse
}

function computeIntegrityScore(telemetryIndex: TelemetryIndex | null | undefined): number {
  if (!telemetryIndex) return 0;
  // Check if telemetry has valid storage reference and basic metadata
  let score = 0;
  if (telemetryIndex.run_id) score += 25;
  if (telemetryIndex.total_ticks > 0) score += 25;
  if (telemetryIndex.storage_ref?.bucket && telemetryIndex.storage_ref?.key) score += 25;
  if (telemetryIndex.keyframe_ticks.length > 0) score += 25;
  return score;
}

function computeActivityScore(telemetrySummary: TelemetrySummary | null | undefined): number {
  if (!telemetrySummary) return 0;
  // Check agent activity from summary
  const { total_agents, total_events, key_metrics } = telemetrySummary;
  if (total_agents === 0) return 0;

  // Average events per agent
  const eventsPerAgent = total_events / total_agents;
  // Activity rate from key_metrics if available
  const activityRates = key_metrics?.by_tick?.map(t => t.activity_rate) || [];
  const avgActivityRate = activityRates.length > 0
    ? activityRates.reduce((a, b) => a + b, 0) / activityRates.length
    : 0.5;

  // Combine metrics: activity rate (60%) + events engagement (40%)
  const engagementScore = Math.min(1, eventsPerAgent / 100);
  const score = (avgActivityRate * 0.6 + engagementScore * 0.4) * 100;
  return Math.round(Math.min(100, score));
}

function computeStabilityScore(
  runs: RunSummary[] | undefined,
  nodeId: string | null
): number | null {
  if (!runs || !nodeId) return null;
  // Filter runs for this node with SUCCEEDED status
  const nodeRuns = runs.filter(r => r.node_id === nodeId && r.status === 'succeeded');
  if (nodeRuns.length < 3) return null; // Need at least 3 runs for stability

  // Compute variance in run durations as stability proxy
  const durations = nodeRuns
    .map(r => {
      if (!r.timing.started_at || !r.timing.ended_at) return null;
      return new Date(r.timing.ended_at).getTime() - new Date(r.timing.started_at).getTime();
    })
    .filter((d): d is number => d !== null);

  if (durations.length < 3) return null;

  const mean = durations.reduce((a, b) => a + b, 0) / durations.length;
  const variance = durations.reduce((sum, d) => sum + Math.pow(d - mean, 2), 0) / durations.length;
  const stdDev = Math.sqrt(variance);
  const coeffVariation = mean > 0 ? stdDev / mean : 1;

  // Lower variance = higher stability score
  const stabilityScore = Math.max(0, 100 - coeffVariation * 100);
  return Math.round(stabilityScore);
}

function computeOverallScore(metrics: Omit<ReliabilityMetrics, 'overallScore'>): number {
  const weights = {
    coverage: 0.25,
    integrity: 0.3,
    activity: 0.25,
    stability: 0.2,
  };

  const stabilityValue = metrics.stabilityScore ?? 50; // Default to 50 if no stability data
  const overall =
    metrics.coverageScore * weights.coverage +
    metrics.integrityScore * weights.integrity +
    metrics.activityScore * weights.activity +
    stabilityValue * weights.stability;

  return Math.round(overall);
}

function generateWarnings(
  metrics: ReliabilityMetrics,
  telemetryIndex: TelemetryIndex | null | undefined,
  telemetrySummary: TelemetrySummary | null | undefined,
  nodeId: string | null,
  projectId: string
): ReliabilityWarning[] {
  const warnings: ReliabilityWarning[] = [];

  if (!telemetryIndex) {
    warnings.push({
      type: 'error',
      message: 'No telemetry data found for this run',
      fixAction: {
        label: 'Run a simulation',
        href: `/p/${projectId}/run-center${nodeId ? `?node=${nodeId}` : ''}`,
      },
    });
    return warnings;
  }

  if (metrics.coverageScore < 50) {
    warnings.push({
      type: 'warning',
      message: `Low telemetry coverage (${metrics.coverageScore}%). Keyframes may be sparse.`,
      fixAction: {
        label: 'View telemetry',
        href: `/p/${projectId}/replay`,
      },
    });
  }

  if (metrics.activityScore < 40) {
    warnings.push({
      type: 'warning',
      message: `Low agent activity (${metrics.activityScore}%). Agents may be underutilized.`,
    });
  }

  if (metrics.stabilityScore === null) {
    warnings.push({
      type: 'info',
      message: 'Run at least 3 simulations to calculate stability score',
      fixAction: {
        label: 'Queue more runs',
        href: `/p/${projectId}/run-center${nodeId ? `?node=${nodeId}` : ''}`,
      },
    });
  } else if (metrics.stabilityScore < 60) {
    warnings.push({
      type: 'warning',
      message: `Low stability (${metrics.stabilityScore}%). Results vary significantly between runs.`,
    });
  }

  if (telemetrySummary && telemetrySummary.total_agents === 0) {
    warnings.push({
      type: 'error',
      message: 'No agents found in telemetry',
    });
  }

  return warnings;
}

// ============================================================================
// UI Components
// ============================================================================

interface ScoreRingProps {
  score: number;
  size?: 'sm' | 'md' | 'lg';
  label?: string;
  showValue?: boolean;
  loading?: boolean;
}

function ScoreRing({ score, size = 'md', label, showValue = true, loading = false }: ScoreRingProps) {
  const sizeClasses = {
    sm: 'w-16 h-16',
    md: 'w-24 h-24',
    lg: 'w-32 h-32',
  };

  const strokeWidth = size === 'sm' ? 4 : size === 'md' ? 6 : 8;
  const radius = size === 'sm' ? 28 : size === 'md' ? 42 : 56;
  const circumference = 2 * Math.PI * radius;
  const offset = loading ? circumference * 0.75 : circumference - (score / 100) * circumference;

  const getColor = (s: number) => {
    if (s >= 80) return 'text-green-400';
    if (s >= 60) return 'text-cyan-400';
    if (s >= 40) return 'text-yellow-400';
    return 'text-red-400';
  };

  return (
    <div className="relative flex flex-col items-center">
      <svg className={cn(sizeClasses[size], 'transform -rotate-90', loading && 'animate-spin')}>
        <circle
          cx="50%"
          cy="50%"
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          className="text-white/10"
        />
        <circle
          cx="50%"
          cy="50%"
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className={cn(loading ? 'text-cyan-400/50' : getColor(score), 'transition-all duration-700')}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        {loading ? (
          <span className="text-sm font-mono text-white/40">...</span>
        ) : showValue && (
          <span className={cn('font-mono font-bold', size === 'lg' ? 'text-2xl' : size === 'md' ? 'text-lg' : 'text-sm')}>
            {score}
          </span>
        )}
      </div>
      {label && <span className="mt-2 text-xs font-mono text-white/60">{label}</span>}
    </div>
  );
}

interface WarningCardProps {
  warning: ReliabilityWarning;
}

function WarningCard({ warning }: WarningCardProps) {
  const styles = {
    error: 'border-red-500/30 bg-red-500/10',
    warning: 'border-yellow-500/30 bg-yellow-500/10',
    info: 'border-cyan-500/30 bg-cyan-500/10',
  };

  const icons = {
    error: XCircle,
    warning: AlertTriangle,
    info: Info,
  };

  const textColors = {
    error: 'text-red-400',
    warning: 'text-yellow-400',
    info: 'text-cyan-400',
  };

  const Icon = icons[warning.type];

  return (
    <div className={cn('border p-3 flex items-start gap-3', styles[warning.type])}>
      <Icon className={cn('w-4 h-4 flex-shrink-0 mt-0.5', textColors[warning.type])} />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-mono text-white/80">{warning.message}</p>
        {warning.fixAction && (
          <Link
            href={warning.fixAction.href}
            className={cn('inline-flex items-center gap-1 text-xs font-mono mt-1', textColors[warning.type], 'hover:underline')}
          >
            {warning.fixAction.label}
            <ExternalLink className="w-3 h-3" />
          </Link>
        )}
      </div>
    </div>
  );
}

interface NodePickerProps {
  nodes: NodeSummary[] | undefined;
  selectedNodeId: string | null;
  onSelect: (nodeId: string) => void;
  loading?: boolean;
}

function NodePicker({ nodes, selectedNodeId, onSelect, loading }: NodePickerProps) {
  const [open, setOpen] = useState(false);

  const selectedNode = nodes?.find(n => n.node_id === selectedNodeId);

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        disabled={loading}
        className={cn(
          'flex items-center gap-2 px-3 py-2 border border-white/10 bg-white/5',
          'hover:bg-white/10 transition-colors min-w-[200px]',
          'disabled:opacity-50'
        )}
      >
        {loading ? (
          <Loader2 className="w-4 h-4 animate-spin text-white/40" />
        ) : (
          <GitBranch className={cn('w-4 h-4', selectedNode?.is_baseline ? 'text-cyan-400' : 'text-purple-400')} />
        )}
        <span className="flex-1 text-left text-sm font-mono truncate">
          {selectedNode ? (selectedNode.label || `Node ${selectedNode.node_id.slice(0, 8)}`) : 'Select node...'}
        </span>
        <ChevronDown className="w-4 h-4 text-white/40" />
      </button>

      {open && nodes && (
        <div className="absolute z-50 mt-1 w-full border border-white/10 bg-black/95 backdrop-blur max-h-[300px] overflow-auto">
          {nodes.map(node => (
            <button
              key={node.node_id}
              onClick={() => {
                onSelect(node.node_id);
                setOpen(false);
              }}
              className={cn(
                'w-full flex items-center gap-2 px-3 py-2 text-left',
                'hover:bg-white/10 transition-colors',
                node.node_id === selectedNodeId && 'bg-cyan-500/10'
              )}
            >
              <GitBranch className={cn('w-4 h-4', node.is_baseline ? 'text-cyan-400' : 'text-purple-400')} />
              <span className="flex-1 text-sm font-mono truncate">
                {node.label || `Node ${node.node_id.slice(0, 8)}`}
              </span>
              {node.is_baseline && (
                <span className="text-[10px] font-mono text-cyan-400 border border-cyan-400/30 px-1">BASELINE</span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

interface RunPickerProps {
  runs: RunSummary[] | undefined;
  selectedRunId: string | null;
  onSelect: (runId: string) => void;
  loading?: boolean;
}

function RunPicker({ runs, selectedRunId, onSelect, loading }: RunPickerProps) {
  const [open, setOpen] = useState(false);

  const selectedRun = runs?.find(r => r.run_id === selectedRunId);
  const succeededRuns = runs?.filter(r => r.status === 'succeeded') || [];

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        disabled={loading || succeededRuns.length === 0}
        className={cn(
          'flex items-center gap-2 px-3 py-2 border border-white/10 bg-white/5',
          'hover:bg-white/10 transition-colors min-w-[200px]',
          'disabled:opacity-50'
        )}
      >
        {loading ? (
          <Loader2 className="w-4 h-4 animate-spin text-white/40" />
        ) : (
          <Play className="w-4 h-4 text-green-400" />
        )}
        <span className="flex-1 text-left text-sm font-mono truncate">
          {selectedRun
            ? `Run ${selectedRun.run_id.slice(0, 8)}`
            : succeededRuns.length === 0
              ? 'No runs available'
              : 'Select run...'}
        </span>
        <ChevronDown className="w-4 h-4 text-white/40" />
      </button>

      {open && succeededRuns.length > 0 && (
        <div className="absolute z-50 mt-1 w-full border border-white/10 bg-black/95 backdrop-blur max-h-[300px] overflow-auto">
          {succeededRuns.map(run => (
            <button
              key={run.run_id}
              onClick={() => {
                onSelect(run.run_id);
                setOpen(false);
              }}
              className={cn(
                'w-full flex items-center gap-2 px-3 py-2 text-left',
                'hover:bg-white/10 transition-colors',
                run.run_id === selectedRunId && 'bg-cyan-500/10'
              )}
            >
              <Play className="w-4 h-4 text-green-400" />
              <div className="flex-1 min-w-0">
                <div className="text-sm font-mono truncate">Run {run.run_id.slice(0, 8)}</div>
                <div className="text-[10px] font-mono text-white/40">
                  {run.timing.total_ticks} ticks • {new Date(run.created_at).toLocaleDateString()}
                </div>
              </div>
              <CheckCircle2 className="w-4 h-4 text-green-400" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

interface MetricCardProps {
  label: string;
  score: number | null;
  icon: React.ElementType;
  description?: string;
  loading?: boolean;
}

function MetricCard({ label, score, icon: Icon, description, loading }: MetricCardProps) {
  const getScoreColor = (s: number | null) => {
    if (s === null) return 'text-white/30';
    if (s >= 80) return 'text-green-400';
    if (s >= 60) return 'text-cyan-400';
    if (s >= 40) return 'text-yellow-400';
    return 'text-red-400';
  };

  return (
    <div className="border border-white/10 bg-white/5 p-4">
      <div className="flex items-center gap-2 mb-2">
        <Icon className="w-4 h-4 text-white/40" />
        <span className="text-xs font-mono text-white/60 uppercase">{label}</span>
      </div>
      <div className={cn('text-3xl font-mono font-bold', getScoreColor(score))}>
        {loading ? (
          <Loader2 className="w-6 h-6 animate-spin text-white/40" />
        ) : score !== null ? (
          score
        ) : (
          '--'
        )}
      </div>
      {description && (
        <div className="text-[10px] font-mono text-white/40 mt-1">{description}</div>
      )}
    </div>
  );
}

// ============================================================================
// PHASE 6: Reliability Integration Components
// ============================================================================

interface Phase6SensitivityChartProps {
  data: Phase6ReliabilitySummaryResponse | undefined;
  loading?: boolean;
}

function Phase6SensitivityChart({ data, loading }: Phase6SensitivityChartProps) {
  if (loading) {
    return (
      <div className="h-64 flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-cyan-400/50" />
      </div>
    );
  }

  if (!data?.sensitivity) {
    return (
      <div className="h-64 flex items-center justify-center text-white/40 text-sm font-mono">
        No sensitivity data available
      </div>
    );
  }

  const chartData = data.sensitivity.threshold_grid.map((threshold, i) => ({
    threshold: threshold.toFixed(2),
    probability: (data.sensitivity!.probabilities[i] * 100).toFixed(1),
  }));

  return (
    <ResponsiveContainer width="100%" height={256}>
      <LineChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
        <XAxis
          dataKey="threshold"
          stroke="rgba(255,255,255,0.4)"
          tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 10 }}
          label={{ value: `Threshold (${data.sensitivity.metric_key})`, position: 'bottom', fill: 'rgba(255,255,255,0.4)', fontSize: 10 }}
        />
        <YAxis
          stroke="rgba(255,255,255,0.4)"
          tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 10 }}
          label={{ value: 'P(%)', angle: -90, position: 'insideLeft', fill: 'rgba(255,255,255,0.4)', fontSize: 10 }}
          domain={[0, 100]}
        />
        <Tooltip
          contentStyle={{ backgroundColor: '#000', border: '1px solid rgba(255,255,255,0.2)', fontFamily: 'monospace', fontSize: 12 }}
          labelStyle={{ color: 'rgba(255,255,255,0.6)' }}
          itemStyle={{ color: '#00FFFF' }}
          formatter={(value: string) => [`${value}%`, 'Probability']}
        />
        <Line
          type="monotone"
          dataKey="probability"
          stroke="#00FFFF"
          strokeWidth={2}
          dot={{ fill: '#00FFFF', r: 3 }}
          activeDot={{ r: 5, fill: '#00FFFF' }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

interface Phase6DriftStatusProps {
  data: Phase6ReliabilitySummaryResponse | undefined;
  loading?: boolean;
}

function Phase6DriftStatus({ data, loading }: Phase6DriftStatusProps) {
  if (loading) {
    return (
      <div className="flex items-center gap-2">
        <Loader2 className="w-4 h-4 animate-spin text-white/40" />
        <span className="text-sm font-mono text-white/40">Checking drift...</span>
      </div>
    );
  }

  if (!data?.drift) {
    return (
      <div className="flex items-center gap-2 text-white/40">
        <Info className="w-4 h-4" />
        <span className="text-sm font-mono">Insufficient data for drift detection</span>
      </div>
    );
  }

  const { drift_status, ks_statistic, psi, baseline_n, recent_n } = data.drift;

  const statusConfig = {
    stable: { color: 'text-green-400', bg: 'bg-green-400/10', border: 'border-green-400/30', label: 'STABLE' },
    warning: { color: 'text-yellow-400', bg: 'bg-yellow-400/10', border: 'border-yellow-400/30', label: 'WARNING' },
    drifting: { color: 'text-red-400', bg: 'bg-red-400/10', border: 'border-red-400/30', label: 'DRIFTING' },
  };

  const config = statusConfig[drift_status];

  return (
    <div className={cn('border p-4', config.bg, config.border)}>
      <div className="flex items-center gap-2 mb-3">
        {drift_status === 'stable' && <CheckCircle2 className={cn('w-5 h-5', config.color)} />}
        {drift_status === 'warning' && <AlertTriangle className={cn('w-5 h-5', config.color)} />}
        {drift_status === 'drifting' && <XCircle className={cn('w-5 h-5', config.color)} />}
        <span className={cn('text-sm font-mono font-bold', config.color)}>{config.label}</span>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs font-mono">
        <div>
          <div className="text-white/40">KS Statistic</div>
          <div className="text-white">{ks_statistic.toFixed(4)}</div>
        </div>
        <div>
          <div className="text-white/40">PSI</div>
          <div className="text-white">{psi.toFixed(4)}</div>
        </div>
        <div>
          <div className="text-white/40">Baseline Runs</div>
          <div className="text-white">{baseline_n}</div>
        </div>
        <div>
          <div className="text-white/40">Recent Runs</div>
          <div className="text-white">{recent_n}</div>
        </div>
      </div>
    </div>
  );
}

interface Phase6StabilityDisplayProps {
  data: Phase6ReliabilitySummaryResponse | undefined;
  loading?: boolean;
}

function Phase6StabilityDisplay({ data, loading }: Phase6StabilityDisplayProps) {
  if (loading) {
    return (
      <div className="flex items-center gap-2">
        <Loader2 className="w-4 h-4 animate-spin text-white/40" />
        <span className="text-sm font-mono text-white/40">Computing stability...</span>
      </div>
    );
  }

  if (!data?.stability) {
    return (
      <div className="flex items-center gap-2 text-white/40">
        <Info className="w-4 h-4" />
        <span className="text-sm font-mono">Insufficient data for stability analysis</span>
      </div>
    );
  }

  const { bootstrap_mean, bootstrap_std, ci_95_lower, ci_95_upper, n_bootstrap, seed_hash } = data.stability;

  return (
    <div className="border border-white/10 bg-white/5 p-4">
      <div className="flex items-center gap-2 mb-3">
        <BarChart3 className="w-5 h-5 text-cyan-400" />
        <span className="text-sm font-mono font-bold text-white">Bootstrap Analysis</span>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-xs font-mono">
        <div>
          <div className="text-white/40">Mean</div>
          <div className="text-xl font-bold text-cyan-400">{bootstrap_mean.toFixed(3)}</div>
        </div>
        <div>
          <div className="text-white/40">Std Dev</div>
          <div className="text-xl font-bold text-white">{bootstrap_std.toFixed(3)}</div>
        </div>
        <div>
          <div className="text-white/40">95% CI</div>
          <div className="text-sm text-white">[{ci_95_lower.toFixed(3)}, {ci_95_upper.toFixed(3)}]</div>
        </div>
      </div>
      <div className="mt-3 pt-3 border-t border-white/10 flex items-center justify-between text-[10px] font-mono text-white/40">
        <span>{n_bootstrap} bootstrap samples</span>
        <span>Seed: {seed_hash.slice(0, 8)}</span>
      </div>
    </div>
  );
}

// Metric key options for Phase 6
const METRIC_KEY_OPTIONS = [
  { value: 'purchase_rate', label: 'Purchase Rate' },
  { value: 'revenue', label: 'Revenue' },
  { value: 'conversion_rate', label: 'Conversion Rate' },
  { value: 'engagement_score', label: 'Engagement Score' },
  { value: 'activity_rate', label: 'Activity Rate' },
];

// ============================================================================
// Main Page Component
// ============================================================================

export default function ReliabilityPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const projectId = params.projectId as string;

  // Get initial node from URL
  const initialNodeId = searchParams.get('node');
  const initialMetricKey = searchParams.get('metric_key') || 'purchase_rate';

  // State
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(initialNodeId);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [selectedMetricKey, setSelectedMetricKey] = useState<string>(initialMetricKey);
  const [showPhase6, setShowPhase6] = useState(true);

  // Fetch nodes for this project
  const { data: nodes, isLoading: nodesLoading } = useNodes({ project_id: projectId });

  // Fetch runs for selected node (or all project runs if no node selected)
  const { data: runs, isLoading: runsLoading } = useRuns({
    project_id: projectId,
    node_id: selectedNodeId || undefined,
    status: 'succeeded' as SpecRunStatus,
    limit: 50,
  });

  // Fetch telemetry for selected run
  const { data: telemetryIndex, isLoading: indexLoading } = useTelemetryIndex(selectedRunId || undefined);
  const { data: telemetrySummary, isLoading: summaryLoading } = useTelemetrySummary(selectedRunId || undefined);

  // PHASE 6: Fetch reliability metrics
  const phase6Params: Phase6ReliabilityQueryParams | undefined = selectedNodeId
    ? { metric_key: selectedMetricKey, op: 'gte', min_runs: 3 }
    : undefined;
  const { data: phase6Data, isLoading: phase6Loading } = usePhase6ReliabilitySummary(selectedNodeId || undefined, phase6Params);

  // Auto-select baseline node if none selected
  useEffect(() => {
    if (!selectedNodeId && nodes && nodes.length > 0) {
      const baseline = nodes.find(n => n.is_baseline);
      if (baseline) {
        setSelectedNodeId(baseline.node_id);
      } else {
        setSelectedNodeId(nodes[0].node_id);
      }
    }
  }, [nodes, selectedNodeId]);

  // Auto-select latest run when node changes
  useEffect(() => {
    if (runs && runs.length > 0 && !selectedRunId) {
      const succeededRuns = runs.filter(r => r.status === 'succeeded');
      if (succeededRuns.length > 0) {
        // Select the most recent succeeded run
        const sorted = [...succeededRuns].sort((a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        );
        setSelectedRunId(sorted[0].run_id);
      }
    }
  }, [runs, selectedRunId]);

  // Update URL when node changes
  const handleNodeSelect = (nodeId: string) => {
    setSelectedNodeId(nodeId);
    setSelectedRunId(null); // Reset run selection
    router.push(`/p/${projectId}/reliability?node=${nodeId}`);
  };

  // Compute metrics
  const metrics = useMemo((): ReliabilityMetrics => {
    const coverageScore = computeCoverageScore(telemetryIndex);
    const integrityScore = computeIntegrityScore(telemetryIndex);
    const activityScore = computeActivityScore(telemetrySummary);
    const stabilityScore = computeStabilityScore(runs, selectedNodeId);

    return {
      coverageScore,
      integrityScore,
      activityScore,
      stabilityScore,
      overallScore: computeOverallScore({ coverageScore, integrityScore, activityScore, stabilityScore }),
    };
  }, [telemetryIndex, telemetrySummary, runs, selectedNodeId]);

  // Generate warnings
  const warnings = useMemo(() => {
    return generateWarnings(metrics, telemetryIndex, telemetrySummary, selectedNodeId, projectId);
  }, [metrics, telemetryIndex, telemetrySummary, selectedNodeId, projectId]);

  // Find baseline node for comparison
  const selectedNode = nodes?.find(n => n.node_id === selectedNodeId);
  const baselineNode = nodes?.find(n => n.is_baseline);
  const isViewingBranch = selectedNode && !selectedNode.is_baseline && baselineNode;

  // Loading states
  const isLoadingData = nodesLoading || runsLoading;
  const isLoadingMetrics = indexLoading || summaryLoading;

  // Empty states
  const hasNoNodes = !nodesLoading && (!nodes || nodes.length === 0);
  const hasNoRuns = !runsLoading && (!runs || runs.filter(r => r.status === 'succeeded').length === 0);

  return (
    <div className="min-h-screen bg-black p-4 md:p-6">
      {/* Header */}
      <div className="mb-6 md:mb-8">
        <Link href={`/p/${projectId}/overview`}>
          <Button variant="ghost" size="sm" className="mb-3 text-[10px] md:text-xs">
            <ArrowLeft className="w-3 h-3 mr-1 md:mr-2" />
            BACK TO OVERVIEW
          </Button>
        </Link>
        <div className="flex items-center gap-2 mb-1">
          <ShieldCheck className="w-3.5 h-3.5 md:w-4 md:h-4 text-cyan-400" />
          <span className="text-[10px] md:text-xs font-mono text-white/40 uppercase tracking-wider">Reliability</span>
        </div>
        <h1 className="text-lg md:text-xl font-mono font-bold text-white">Run Reliability</h1>
        <p className="text-xs md:text-sm font-mono text-white/50 mt-1">
          Trust metrics for simulation runs and telemetry data
        </p>
      </div>

      {/* Node & Run Selection */}
      <div className="max-w-6xl mb-6">
        <div className="flex flex-wrap items-center gap-4">
          <div>
            <div className="text-[10px] font-mono text-white/40 uppercase mb-1">Node</div>
            <NodePicker
              nodes={nodes}
              selectedNodeId={selectedNodeId}
              onSelect={handleNodeSelect}
              loading={nodesLoading}
            />
          </div>
          <div>
            <div className="text-[10px] font-mono text-white/40 uppercase mb-1">Run</div>
            <RunPicker
              runs={runs}
              selectedRunId={selectedRunId}
              onSelect={setSelectedRunId}
              loading={runsLoading}
            />
          </div>
          {selectedRunId && (
            <Link href={`/p/${projectId}/replay?run=${selectedRunId}`} className="mt-5">
              <Button variant="outline" size="sm" className="text-xs">
                <Play className="w-3 h-3 mr-1" />
                View Replay
              </Button>
            </Link>
          )}
        </div>
      </div>

      {/* Empty States */}
      {hasNoNodes && (
        <div className="max-w-4xl">
          <div className="border border-white/10 bg-white/5 p-8 text-center">
            <Layers className="w-12 h-12 mx-auto text-white/20 mb-4" />
            <h2 className="text-lg font-mono font-bold text-white mb-2">No Nodes Found</h2>
            <p className="text-sm font-mono text-white/50 mb-4">
              Create a simulation first to see reliability metrics.
            </p>
            <Link href={`/p/${projectId}/universe-map`}>
              <Button variant="outline" className="text-xs">
                <GitBranch className="w-3 h-3 mr-1" />
                Go to Universe Map
              </Button>
            </Link>
          </div>
        </div>
      )}

      {!hasNoNodes && hasNoRuns && (
        <div className="max-w-4xl">
          <div className="border border-yellow-500/20 bg-yellow-500/5 p-8 text-center">
            <Play className="w-12 h-12 mx-auto text-yellow-400/40 mb-4" />
            <h2 className="text-lg font-mono font-bold text-white mb-2">No Completed Runs</h2>
            <p className="text-sm font-mono text-white/50 mb-4">
              Run a simulation to see reliability metrics. Only SUCCEEDED runs are analyzed.
            </p>
            <Link href={`/p/${projectId}/run-center${selectedNodeId ? `?node=${selectedNodeId}` : ''}`}>
              <Button variant="outline" className="text-xs">
                <Play className="w-3 h-3 mr-1" />
                Go to Run Center
              </Button>
            </Link>
          </div>
        </div>
      )}

      {/* Main Content */}
      {!hasNoNodes && !hasNoRuns && (
        <>
          {/* Overall Score & Metrics Grid */}
          <div className="max-w-6xl mb-6">
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
              {/* Overall Score */}
              <div className="lg:col-span-1 border border-white/10 bg-white/5 p-6 flex flex-col items-center justify-center">
                <ScoreRing
                  score={metrics.overallScore}
                  size="lg"
                  loading={isLoadingMetrics}
                />
                <div className="mt-3 text-center">
                  <div className="text-sm font-mono font-bold text-white">Overall Score</div>
                  <div className="text-[10px] font-mono text-white/40 mt-1">
                    {metrics.overallScore >= 80 ? 'High confidence' :
                     metrics.overallScore >= 60 ? 'Moderate confidence' :
                     metrics.overallScore >= 40 ? 'Low confidence' : 'Needs attention'}
                  </div>
                </div>
              </div>

              {/* Individual Metrics */}
              <div className="lg:col-span-4 grid grid-cols-2 md:grid-cols-4 gap-4">
                <MetricCard
                  label="Coverage"
                  score={metrics.coverageScore}
                  icon={Target}
                  description="Telemetry keyframe density"
                  loading={isLoadingMetrics}
                />
                <MetricCard
                  label="Integrity"
                  score={metrics.integrityScore}
                  icon={Database}
                  description="Data completeness"
                  loading={isLoadingMetrics}
                />
                <MetricCard
                  label="Activity"
                  score={metrics.activityScore}
                  icon={Activity}
                  description="Agent engagement"
                  loading={isLoadingMetrics}
                />
                <MetricCard
                  label="Stability"
                  score={metrics.stabilityScore}
                  icon={BarChart3}
                  description={metrics.stabilityScore === null ? 'Needs 3+ runs' : 'Run variance'}
                  loading={isLoadingMetrics}
                />
              </div>
            </div>
          </div>

          {/* Warnings */}
          {warnings.length > 0 && (
            <div className="max-w-6xl mb-6">
              <div className="text-[10px] font-mono text-white/40 uppercase mb-2">Warnings & Recommendations</div>
              <div className="space-y-2">
                {warnings.map((warning, i) => (
                  <WarningCard key={i} warning={warning} />
                ))}
              </div>
            </div>
          )}

          {/* Branch Comparison */}
          {isViewingBranch && baselineNode && (
            <div className="max-w-6xl mb-6">
              <div className="text-[10px] font-mono text-white/40 uppercase mb-2">Branch vs Baseline</div>
              <div className="border border-purple-500/20 bg-purple-500/5 p-4">
                <div className="flex items-center gap-3 mb-4">
                  <GitBranch className="w-5 h-5 text-purple-400" />
                  <div>
                    <div className="text-sm font-mono text-white">
                      Comparing to baseline: <span className="text-cyan-400">{baselineNode.label || baselineNode.node_id.slice(0, 8)}</span>
                    </div>
                    <div className="text-[10px] font-mono text-white/40">
                      View baseline reliability to compare metrics
                    </div>
                  </div>
                  <Link href={`/p/${projectId}/reliability?node=${baselineNode.node_id}`} className="ml-auto">
                    <Button variant="outline" size="sm" className="text-xs">
                      <ArrowLeft className="w-3 h-3 mr-1" />
                      View Baseline
                    </Button>
                  </Link>
                </div>
              </div>
            </div>
          )}

          {/* Telemetry Summary */}
          {telemetrySummary && (
            <div className="max-w-6xl mb-6">
              <div className="text-[10px] font-mono text-white/40 uppercase mb-2">Telemetry Summary</div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="border border-white/10 bg-white/5 p-3">
                  <div className="text-[10px] font-mono text-white/40 uppercase">Total Ticks</div>
                  <div className="text-xl font-mono font-bold text-cyan-400">{telemetrySummary.total_ticks}</div>
                </div>
                <div className="border border-white/10 bg-white/5 p-3">
                  <div className="text-[10px] font-mono text-white/40 uppercase">Total Events</div>
                  <div className="text-xl font-mono font-bold text-cyan-400">{telemetrySummary.total_events}</div>
                </div>
                <div className="border border-white/10 bg-white/5 p-3">
                  <div className="text-[10px] font-mono text-white/40 uppercase">Agents</div>
                  <div className="text-xl font-mono font-bold text-cyan-400">{telemetrySummary.total_agents}</div>
                </div>
                <div className="border border-white/10 bg-white/5 p-3">
                  <div className="text-[10px] font-mono text-white/40 uppercase">Duration</div>
                  <div className="text-xl font-mono font-bold text-cyan-400">{telemetrySummary.duration_seconds}s</div>
                </div>
              </div>
            </div>
          )}

          {/* PHASE 6: Statistical Reliability Analysis */}
          {showPhase6 && selectedNodeId && (
            <div className="max-w-6xl mb-6">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Activity className="w-4 h-4 text-cyan-400" />
                  <span className="text-[10px] font-mono text-white/40 uppercase tracking-wider">
                    Statistical Reliability Analysis
                  </span>
                  {phase6Data?.status === 'insufficient_data' && (
                    <span className="text-[10px] font-mono text-yellow-400 bg-yellow-400/10 px-2 py-0.5">
                      {phase6Data.n_runs_used}/{phase6Data.n_runs_total} runs
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <select
                    value={selectedMetricKey}
                    onChange={(e) => setSelectedMetricKey(e.target.value)}
                    className="text-xs font-mono bg-black border border-white/20 text-white px-2 py-1 focus:outline-none focus:border-cyan-400"
                  >
                    {METRIC_KEY_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                  <button
                    onClick={() => setShowPhase6(!showPhase6)}
                    className="text-[10px] font-mono text-white/40 hover:text-white/60"
                  >
                    <ChevronDown className={cn('w-4 h-4 transition-transform', !showPhase6 && '-rotate-90')} />
                  </button>
                </div>
              </div>

              {phase6Data?.status === 'insufficient_data' ? (
                <div className="border border-yellow-500/20 bg-yellow-500/5 p-6 text-center">
                  <Info className="w-8 h-8 mx-auto text-yellow-400/50 mb-3" />
                  <p className="text-sm font-mono text-white/60 mb-2">
                    Insufficient data for statistical analysis
                  </p>
                  <p className="text-xs font-mono text-white/40">
                    Need at least 3 completed runs. Currently have {phase6Data.n_runs_total} runs.
                  </p>
                  <Link href={`/p/${projectId}/run-center${selectedNodeId ? `?node=${selectedNodeId}` : ''}`} className="mt-4 inline-block">
                    <Button variant="outline" size="sm" className="text-xs">
                      <Play className="w-3 h-3 mr-1" />
                      Queue More Runs
                    </Button>
                  </Link>
                </div>
              ) : (
                <div className="space-y-4">
                  {/* Sensitivity Chart */}
                  <div className="border border-white/10 bg-white/5 p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <Target className="w-4 h-4 text-cyan-400" />
                      <span className="text-sm font-mono font-bold text-white">Sensitivity Curve</span>
                      <span className="text-[10px] font-mono text-white/40">
                        P({selectedMetricKey} {'>='} threshold)
                      </span>
                    </div>
                    <Phase6SensitivityChart data={phase6Data} loading={phase6Loading} />
                  </div>

                  {/* Drift Status */}
                  <div>
                    <div className="text-[10px] font-mono text-white/40 uppercase mb-2">Distribution Drift</div>
                    <Phase6DriftStatus data={phase6Data} loading={phase6Loading} />
                  </div>

                  {/* Stability / Bootstrap Analysis */}
                  <div>
                    <div className="text-[10px] font-mono text-white/40 uppercase mb-2">Bootstrap Stability</div>
                    <Phase6StabilityDisplay data={phase6Data} loading={phase6Loading} />
                  </div>

                  {/* Audit Info */}
                  {phase6Data?.audit && (
                    <div className="text-[10px] font-mono text-white/30 flex items-center justify-between">
                      <span>Computed: {new Date(phase6Data.audit.computed_at).toLocaleString()}</span>
                      <span>Seed: {phase6Data.audit.deterministic_seed.slice(0, 12)}...</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Quick Links */}
          <div className="max-w-6xl">
            <div className="text-[10px] font-mono text-white/40 uppercase mb-2">Quick Actions</div>
            <div className="flex flex-wrap gap-2">
              <Link href={`/p/${projectId}/universe-map${selectedNodeId ? `?node=${selectedNodeId}` : ''}`}>
                <Button variant="outline" size="sm" className="text-xs">
                  <GitBranch className="w-3 h-3 mr-1" />
                  Universe Map
                </Button>
              </Link>
              <Link href={`/p/${projectId}/run-center${selectedNodeId ? `?node=${selectedNodeId}` : ''}`}>
                <Button variant="outline" size="sm" className="text-xs">
                  <Play className="w-3 h-3 mr-1" />
                  Run Center
                </Button>
              </Link>
              {selectedRunId && (
                <Link href={`/p/${projectId}/replay?run=${selectedRunId}`}>
                  <Button variant="outline" size="sm" className="text-xs">
                    <RefreshCw className="w-3 h-3 mr-1" />
                    Replay
                  </Button>
                </Link>
              )}
            </div>
          </div>
        </>
      )}

      {/* Footer */}
      <div className="mt-8 pt-4 border-t border-white/5 max-w-6xl">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-1">
            <ShieldCheck className="w-3 h-3" />
            <span>RELIABILITY • {selectedNodeId?.slice(0, 8) || 'NO NODE'}</span>
          </div>
          <span>AGENTVERSE v1.0</span>
        </div>
      </div>
    </div>
  );
}

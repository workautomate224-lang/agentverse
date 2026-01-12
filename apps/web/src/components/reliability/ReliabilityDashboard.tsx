'use client';

import { useState } from 'react';
import {
  Shield,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Activity,
  Database,
  BarChart3,
  Target,
  Clock,
  ChevronDown,
  ChevronUp,
  Info,
  AlertOctagon,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useProject } from '@/components/project/ProjectContext';
import type {
  ReliabilityReport,
  ReliabilitySummary,
  ReliabilityConfidenceLevel,
  DriftSeverity,
} from '@/lib/api';

// ============================================================================
// Mock Data (will be replaced with actual API calls)
// ============================================================================

const MOCK_REPORT: ReliabilityReport = {
  report_id: 'rel-001',
  project_id: 'proj-001',
  generated_at: new Date().toISOString(),
  valid_until: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
  engine_version: '0.1.0',
  report_version: '1.0.0',
  calibration: {
    accuracy: 0.78,
    historical_scenarios_run: 12,
    best_scenario_accuracy: 0.92,
    worst_scenario_accuracy: 0.64,
    mean_error: 0.22,
  },
  stability: {
    score: 0.85,
    seeds_tested: 10,
    variance_coefficient: 0.08,
    is_stable: true,
    most_stable_outcome: 'outcome_a',
    least_stable_outcome: 'outcome_c',
  },
  sensitivity: {
    n_high_impact_variables: 3,
    top_impact_variables: ['media_influence', 'economic_outlook', 'social_trust'],
    impact_scores: {
      media_influence: 0.72,
      economic_outlook: 0.65,
      social_trust: 0.58,
      network_density: 0.32,
      regional_bias: 0.21,
    },
    recommendations: ['Focus validation on high-impact variables: media_influence, economic_outlook'],
  },
  drift: {
    drift_detected: true,
    severity: 'low',
    drifted_variables: ['consumer_confidence'],
    last_check: new Date().toISOString(),
    days_since_calibration: 14,
    recommendations: ['Monitor consumer_confidence for continued drift'],
  },
  data_gaps: {
    total_variables: 24,
    variables_with_gaps: 2,
    gap_percentage: 0.083,
    critical_gaps: [],
    recommendations: ['Minor gaps detected - no immediate action required'],
  },
  confidence: {
    overall: 0.76,
    level: 'moderate',
    by_category: {
      category_a: 0.82,
      category_b: 0.71,
      category_c: 0.75,
    },
    by_time_horizon: {
      '1_week': 0.88,
      '1_month': 0.76,
      '3_months': 0.62,
      '6_months': 0.45,
    },
    factors: {
      calibration: 0.78,
      stability: 0.85,
      data_quality: 0.92,
      drift_free: 0.80,
    },
  },
  overall_reliability_score: 0.76,
  confidence_level: 'moderate',
  is_reliable: true,
  reliability_threshold: 0.7,
  recommendations: [
    'Consider running more historical scenarios to improve calibration',
    'Monitor drift in consumer_confidence over the next week',
  ],
  warnings: [],
};

// ============================================================================
// Helper Components
// ============================================================================

interface ScoreRingProps {
  score: number;
  size?: 'sm' | 'md' | 'lg';
  label?: string;
  showPercentage?: boolean;
}

function ScoreRing({ score, size = 'md', label, showPercentage = true }: ScoreRingProps) {
  const sizeClasses = {
    sm: 'w-16 h-16',
    md: 'w-24 h-24',
    lg: 'w-32 h-32',
  };

  const strokeWidth = size === 'sm' ? 4 : size === 'md' ? 6 : 8;
  const radius = size === 'sm' ? 28 : size === 'md' ? 42 : 56;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - score * circumference;

  const getColor = (s: number) => {
    if (s >= 0.8) return 'text-green-400';
    if (s >= 0.6) return 'text-cyan-400';
    if (s >= 0.4) return 'text-yellow-400';
    return 'text-red-400';
  };

  return (
    <div className="relative flex flex-col items-center">
      <svg className={cn(sizeClasses[size], 'transform -rotate-90')}>
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
          className={cn(getColor(score), 'transition-all duration-700')}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        {showPercentage && (
          <span className={cn('font-mono font-bold', size === 'lg' ? 'text-2xl' : 'text-lg')}>
            {Math.round(score * 100)}%
          </span>
        )}
      </div>
      {label && <span className="mt-2 text-xs text-white/60">{label}</span>}
    </div>
  );
}

interface StatusBadgeProps {
  status: 'good' | 'warning' | 'error' | 'info';
  children: React.ReactNode;
}

function StatusBadge({ status, children }: StatusBadgeProps) {
  const styles = {
    good: 'bg-green-500/20 text-green-400 border-green-500/30',
    warning: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    error: 'bg-red-500/20 text-red-400 border-red-500/30',
    info: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
  };

  const icons = {
    good: CheckCircle2,
    warning: AlertTriangle,
    error: XCircle,
    info: Info,
  };

  const Icon = icons[status];

  return (
    <span className={cn('inline-flex items-center gap-1.5 px-2 py-1 text-xs border', styles[status])}>
      <Icon className="w-3 h-3" />
      {children}
    </span>
  );
}

interface SectionCardProps {
  title: string;
  icon: React.ElementType;
  children: React.ReactNode;
  status?: 'good' | 'warning' | 'error';
  collapsible?: boolean;
  defaultExpanded?: boolean;
}

function SectionCard({
  title,
  icon: Icon,
  children,
  status,
  collapsible = false,
  defaultExpanded = true,
}: SectionCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  const statusColors = {
    good: 'border-green-500/30',
    warning: 'border-yellow-500/30',
    error: 'border-red-500/30',
  };

  return (
    <div className={cn('border border-white/10 bg-black/40', status && statusColors[status])}>
      <div
        className={cn(
          'flex items-center justify-between px-3 md:px-4 py-2.5 md:py-3 border-b border-white/10',
          collapsible && 'cursor-pointer hover:bg-white/5'
        )}
        onClick={() => collapsible && setExpanded(!expanded)}
      >
        <div className="flex items-center gap-1.5 md:gap-2 min-w-0">
          <Icon className="w-3.5 h-3.5 md:w-4 md:h-4 text-cyan-400 flex-shrink-0" />
          <span className="text-sm md:text-base font-medium truncate">{title}</span>
        </div>
        {collapsible && (
          <button className="text-white/40 hover:text-white/60 flex-shrink-0">
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        )}
      </div>
      {expanded && <div className="p-3 md:p-4">{children}</div>}
    </div>
  );
}

// ============================================================================
// Main Dashboard Component
// ============================================================================

interface ReliabilityDashboardProps {
  projectId: string;
}

export function ReliabilityDashboard({ projectId }: ReliabilityDashboardProps) {
  const [isRefreshing, setIsRefreshing] = useState(false);

  // In production, this would fetch from API
  const report = MOCK_REPORT;

  const handleRefresh = async () => {
    setIsRefreshing(true);
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1500));
    setIsRefreshing(false);
  };

  const getConfidenceLevelBadge = (level: ReliabilityConfidenceLevel) => {
    const styles: Record<ReliabilityConfidenceLevel, { status: 'good' | 'warning' | 'error'; label: string }> = {
      high: { status: 'good', label: 'High Confidence' },
      moderate: { status: 'warning', label: 'Moderate Confidence' },
      low: { status: 'error', label: 'Low Confidence' },
    };
    return styles[level];
  };

  const getDriftBadge = (severity: DriftSeverity) => {
    const styles: Record<DriftSeverity, { status: 'good' | 'warning' | 'error' | 'info'; label: string }> = {
      none: { status: 'good', label: 'No Drift' },
      low: { status: 'info', label: 'Minor Drift' },
      moderate: { status: 'warning', label: 'Moderate Drift' },
      high: { status: 'warning', label: 'High Drift' },
      critical: { status: 'error', label: 'Critical Drift' },
    };
    return styles[severity];
  };

  const confidenceBadge = getConfidenceLevelBadge(report.confidence_level);
  const driftBadge = getDriftBadge(report.drift.severity);

  return (
    <div className="space-y-4 md:space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2 md:gap-3">
          <Shield className="w-5 h-5 md:w-6 md:h-6 text-cyan-400 flex-shrink-0" />
          <div className="min-w-0">
            <h1 className="text-lg md:text-xl font-bold">Reliability Report</h1>
            <p className="text-xs md:text-sm text-white/60 truncate">
              <span className="hidden sm:inline">Generated </span>{new Date(report.generated_at).toLocaleDateString()} | Valid until{' '}
              {new Date(report.valid_until).toLocaleDateString()}
            </p>
          </div>
        </div>
        <button
          onClick={handleRefresh}
          disabled={isRefreshing}
          className={cn(
            'flex items-center justify-center gap-1.5 md:gap-2 px-3 md:px-4 py-1.5 md:py-2 border border-cyan-500/30',
            'bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500/20 text-xs md:text-sm',
            'disabled:opacity-50 disabled:cursor-not-allowed self-start sm:self-auto'
          )}
        >
          <RefreshCw className={cn('w-3.5 h-3.5 md:w-4 md:h-4', isRefreshing && 'animate-spin')} />
          {isRefreshing ? 'Computing...' : <span><span className="hidden sm:inline">Refresh </span>Report</span>}
        </button>
      </div>

      {/* Overall Score & Status */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-6">
        {/* Main Score Ring */}
        <div className="lg:col-span-1 border border-white/10 bg-black/40 p-4 md:p-6 flex flex-col items-center justify-center">
          <ScoreRing score={report.overall_reliability_score} size="lg" />
          <div className="mt-3 md:mt-4 text-center">
            <h2 className="text-base md:text-lg font-semibold">Overall Reliability</h2>
            <div className="mt-1.5 md:mt-2 flex justify-center gap-2">
              <StatusBadge status={confidenceBadge.status}>{confidenceBadge.label}</StatusBadge>
            </div>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="lg:col-span-2 grid grid-cols-2 gap-2 md:gap-4">
          <div className="border border-white/10 bg-black/40 p-2.5 md:p-4">
            <div className="flex items-center gap-1.5 md:gap-2 text-white/60 text-xs md:text-sm mb-1.5 md:mb-2">
              <Target className="w-3.5 h-3.5 md:w-4 md:h-4 flex-shrink-0" />
              <span className="truncate">Calibration</span>
            </div>
            <div className="text-xl md:text-2xl font-mono font-bold text-cyan-400">
              {Math.round(report.calibration.accuracy * 100)}%
            </div>
            <div className="text-[10px] md:text-xs text-white/40 mt-0.5 md:mt-1 truncate">
              {report.calibration.historical_scenarios_run} scenarios
            </div>
          </div>

          <div className="border border-white/10 bg-black/40 p-2.5 md:p-4">
            <div className="flex items-center gap-1.5 md:gap-2 text-white/60 text-xs md:text-sm mb-1.5 md:mb-2">
              <Activity className="w-3.5 h-3.5 md:w-4 md:h-4 flex-shrink-0" />
              <span className="truncate">Stability</span>
            </div>
            <div className="text-xl md:text-2xl font-mono font-bold text-green-400">
              {Math.round(report.stability.score * 100)}%
            </div>
            <div className="text-[10px] md:text-xs text-white/40 mt-0.5 md:mt-1 truncate">{report.stability.seeds_tested} seeds tested</div>
          </div>

          <div className="border border-white/10 bg-black/40 p-2.5 md:p-4">
            <div className="flex items-center gap-1.5 md:gap-2 text-white/60 text-xs md:text-sm mb-1.5 md:mb-2">
              <TrendingUp className="w-3.5 h-3.5 md:w-4 md:h-4 flex-shrink-0" />
              <span className="truncate">Drift Status</span>
            </div>
            <StatusBadge status={driftBadge.status}>{driftBadge.label}</StatusBadge>
            <div className="text-[10px] md:text-xs text-white/40 mt-1.5 md:mt-2 truncate">
              {report.drift.days_since_calibration}d since calibration
            </div>
          </div>

          <div className="border border-white/10 bg-black/40 p-2.5 md:p-4">
            <div className="flex items-center gap-1.5 md:gap-2 text-white/60 text-xs md:text-sm mb-1.5 md:mb-2">
              <Database className="w-3.5 h-3.5 md:w-4 md:h-4 flex-shrink-0" />
              <span className="truncate">Data Quality</span>
            </div>
            <div className="text-xl md:text-2xl font-mono font-bold text-green-400">
              {Math.round((1 - report.data_gaps.gap_percentage) * 100)}%
            </div>
            <div className="text-[10px] md:text-xs text-white/40 mt-0.5 md:mt-1 truncate">{report.data_gaps.critical_gaps.length} critical gaps</div>
          </div>
        </div>
      </div>

      {/* Warnings & Recommendations */}
      {(report.warnings.length > 0 || report.recommendations.length > 0) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4">
          {report.warnings.length > 0 && (
            <div className="border border-red-500/30 bg-red-500/10 p-3 md:p-4">
              <div className="flex items-center gap-1.5 md:gap-2 mb-2 md:mb-3">
                <AlertOctagon className="w-3.5 h-3.5 md:w-4 md:h-4 text-red-400 flex-shrink-0" />
                <span className="text-sm md:text-base font-medium text-red-400">Warnings</span>
              </div>
              <ul className="space-y-1.5 md:space-y-2">
                {report.warnings.map((warning, i) => (
                  <li key={i} className="text-xs md:text-sm text-red-300/80 flex items-start gap-1.5 md:gap-2">
                    <span className="text-red-400 flex-shrink-0">-</span>
                    <span>{warning}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {report.recommendations.length > 0 && (
            <div className="border border-cyan-500/30 bg-cyan-500/10 p-3 md:p-4">
              <div className="flex items-center gap-1.5 md:gap-2 mb-2 md:mb-3">
                <Info className="w-3.5 h-3.5 md:w-4 md:h-4 text-cyan-400 flex-shrink-0" />
                <span className="text-sm md:text-base font-medium text-cyan-400">Recommendations</span>
              </div>
              <ul className="space-y-1.5 md:space-y-2">
                {report.recommendations.map((rec, i) => (
                  <li key={i} className="text-xs md:text-sm text-cyan-300/80 flex items-start gap-1.5 md:gap-2">
                    <span className="text-cyan-400 flex-shrink-0">-</span>
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Detailed Sections */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
        {/* Calibration Details */}
        <SectionCard
          title="Calibration Analysis"
          icon={Target}
          status={report.calibration.accuracy >= 0.7 ? 'good' : 'warning'}
          collapsible
        >
          <div className="space-y-3 md:space-y-4">
            <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
              <ScoreRing score={report.calibration.accuracy} size="sm" label="Accuracy" />
              <div className="text-center sm:text-right">
                <div className="text-xs md:text-sm text-white/60">Best: {Math.round(report.calibration.best_scenario_accuracy * 100)}%</div>
                <div className="text-xs md:text-sm text-white/60">Worst: {Math.round(report.calibration.worst_scenario_accuracy * 100)}%</div>
                <div className="text-xs md:text-sm text-white/60">Mean Error: {report.calibration.mean_error.toFixed(3)}</div>
              </div>
            </div>
            <div className="border-t border-white/10 pt-2 md:pt-3">
              <div className="text-xs md:text-sm text-white/60 mb-1.5 md:mb-2">
                {report.calibration.historical_scenarios_run} historical scenarios analyzed
              </div>
              <button className="text-[10px] md:text-xs text-cyan-400 hover:text-cyan-300">View scenario details &rarr;</button>
            </div>
          </div>
        </SectionCard>

        {/* Stability Details */}
        <SectionCard
          title="Stability Analysis"
          icon={Activity}
          status={report.stability.is_stable ? 'good' : 'warning'}
          collapsible
        >
          <div className="space-y-3 md:space-y-4">
            <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
              <ScoreRing score={report.stability.score} size="sm" label="Stability" />
              <div className="text-center sm:text-right">
                <div className="text-xs md:text-sm text-white/60">Seeds tested: {report.stability.seeds_tested}</div>
                <div className="text-xs md:text-sm text-white/60">
                  Variance coeff: {report.stability.variance_coefficient.toFixed(3)}
                </div>
              </div>
            </div>
            <div className="border-t border-white/10 pt-2 md:pt-3">
              <div className="flex justify-between text-xs md:text-sm">
                <span className="text-white/60">Most stable:</span>
                <span className="text-green-400 font-mono truncate ml-2">{report.stability.most_stable_outcome}</span>
              </div>
              <div className="flex justify-between text-xs md:text-sm mt-1">
                <span className="text-white/60">Least stable:</span>
                <span className="text-yellow-400 font-mono truncate ml-2">{report.stability.least_stable_outcome}</span>
              </div>
            </div>
          </div>
        </SectionCard>

        {/* Sensitivity Details */}
        <SectionCard title="Sensitivity Analysis" icon={BarChart3} collapsible>
          <div className="space-y-3 md:space-y-4">
            <div className="text-xs md:text-sm text-white/60 mb-2 md:mb-3">
              {report.sensitivity.n_high_impact_variables} high-impact variables detected
            </div>
            <div className="space-y-1.5 md:space-y-2">
              {report.sensitivity.top_impact_variables.map((variable) => {
                const score = report.sensitivity.impact_scores[variable] || 0;
                return (
                  <div key={variable} className="flex items-center gap-2 md:gap-3">
                    <span className="text-[10px] md:text-sm font-mono text-white/80 w-20 md:w-32 truncate">{variable}</span>
                    <div className="flex-1 h-1.5 md:h-2 bg-white/10">
                      <div
                        className={cn(
                          'h-full',
                          score >= 0.5 ? 'bg-red-400' : score >= 0.3 ? 'bg-yellow-400' : 'bg-green-400'
                        )}
                        style={{ width: `${score * 100}%` }}
                      />
                    </div>
                    <span className="text-[10px] md:text-sm text-white/60 w-8 md:w-12 text-right">{Math.round(score * 100)}%</span>
                  </div>
                );
              })}
            </div>
          </div>
        </SectionCard>

        {/* Drift Details */}
        <SectionCard
          title="Drift Detection"
          icon={TrendingDown}
          status={report.drift.drift_detected ? 'warning' : 'good'}
          collapsible
        >
          <div className="space-y-3 md:space-y-4">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
              <StatusBadge status={driftBadge.status}>{driftBadge.label}</StatusBadge>
              <div className="text-xs md:text-sm text-white/60">
                Last check: {new Date(report.drift.last_check).toLocaleTimeString()}
              </div>
            </div>
            {report.drift.drifted_variables.length > 0 && (
              <div className="border-t border-white/10 pt-2 md:pt-3">
                <div className="text-xs md:text-sm text-white/60 mb-1.5 md:mb-2">Drifted variables:</div>
                <div className="flex flex-wrap gap-1.5 md:gap-2">
                  {report.drift.drifted_variables.map((v) => (
                    <span key={v} className="px-1.5 md:px-2 py-0.5 md:py-1 text-[10px] md:text-xs bg-yellow-500/20 text-yellow-400 border border-yellow-500/30">
                      {v}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {report.drift.recommendations && (
              <div className="text-xs md:text-sm text-white/60">{report.drift.recommendations[0]}</div>
            )}
          </div>
        </SectionCard>
      </div>

      {/* Confidence by Time Horizon */}
      <SectionCard title="Confidence by Time Horizon" icon={Clock} collapsible defaultExpanded={false}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
          {Object.entries(report.confidence.by_time_horizon).map(([horizon, score]) => (
            <div key={horizon} className="text-center">
              <ScoreRing score={score} size="sm" />
              <div className="mt-1.5 md:mt-2 text-xs md:text-sm text-white/60">{horizon.replace('_', ' ')}</div>
            </div>
          ))}
        </div>
      </SectionCard>

      {/* Data Gaps */}
      <SectionCard
        title="Data Quality & Gaps"
        icon={Database}
        status={report.data_gaps.critical_gaps.length > 0 ? 'warning' : 'good'}
        collapsible
        defaultExpanded={false}
      >
        <div className="space-y-3 md:space-y-4">
          <div className="grid grid-cols-3 gap-2 md:gap-4 text-center">
            <div>
              <div className="text-xl md:text-2xl font-mono font-bold text-cyan-400">{report.data_gaps.total_variables}</div>
              <div className="text-[10px] md:text-xs text-white/60">Total Variables</div>
            </div>
            <div>
              <div className="text-xl md:text-2xl font-mono font-bold text-yellow-400">{report.data_gaps.variables_with_gaps}</div>
              <div className="text-[10px] md:text-xs text-white/60">With Gaps</div>
            </div>
            <div>
              <div className="text-xl md:text-2xl font-mono font-bold text-red-400">{report.data_gaps.critical_gaps.length}</div>
              <div className="text-[10px] md:text-xs text-white/60">Critical Gaps</div>
            </div>
          </div>
          {report.data_gaps.recommendations.length > 0 && (
            <div className="border-t border-white/10 pt-2 md:pt-3">
              <div className="text-xs md:text-sm text-white/60">{report.data_gaps.recommendations[0]}</div>
            </div>
          )}
        </div>
      </SectionCard>

      {/* Footer */}
      <div className="text-center text-[10px] md:text-xs text-white/40 pt-3 md:pt-4 border-t border-white/10">
        <span className="hidden sm:inline">Engine v{report.engine_version} | Report v{report.report_version} | Generated{' '}</span>
        <span className="sm:hidden">v{report.engine_version} | </span>
        {new Date(report.generated_at).toLocaleString()}
      </div>
    </div>
  );
}

export default ReliabilityDashboard;

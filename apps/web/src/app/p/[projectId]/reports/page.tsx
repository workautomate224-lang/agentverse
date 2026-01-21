'use client';

/**
 * Reports Page
 * Generate comprehensive reports for runs, nodes, and projects.
 * Route: /p/{projectId}/reports?run={runId}&node={nodeId}
 *
 * Report Types:
 * 1. Run Report - Full details for a specific run
 * 2. Node Summary Report - Aggregated stats for a node across all runs
 * 3. Project Overview Report - Setup checklist and system health
 */

import { useState, useMemo, useCallback } from 'react';
import { useParams, useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  FileBarChart,
  ArrowLeft,
  Download,
  FileText,
  Copy,
  Check,
  Terminal,
  ChevronDown,
  Play,
  GitBranch,
  Activity,
  Target,
  Database,
  BarChart3,
  Clock,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Info,
  Loader2,
  ExternalLink,
  Layers,
  Users,
  Settings,
  Zap,
  Calendar,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  useNodes,
  useRuns,
  useNode,
  useRun,
  useTelemetryIndex,
  useTelemetrySummary,
  useProject,
  useProjectSpec,
  // Phase 7: Aggregated Report hook
  useNodeReport,
} from '@/hooks/useApi';
import type {
  NodeSummary,
  RunSummary,
  TelemetryIndex,
  TelemetrySummary,
  SpecRunStatus,
  // Phase 7: Aggregated Report types
  ReportResponse,
  ReportQueryParams,
  ReportOperator,
  ReportDriftStatus,
} from '@/lib/api';
import { GuidancePanel } from '@/components/pil';
import { isMvpMode } from '@/lib/feature-flags';

// ============================================================================
// Types
// ============================================================================

type ReportType = 'project' | 'node' | 'run' | 'prediction' | 'mvp';

interface ReliabilityMetrics {
  coverageScore: number;
  integrityScore: number;
  activityScore: number;
  stabilityScore: number | null;
  overallScore: number;
}

interface ReliabilityWarning {
  type: 'error' | 'warning' | 'info';
  message: string;
  fixAction?: {
    label: string;
    href: string;
  };
}

// ============================================================================
// Metric Computation Functions (from Reliability page)
// ============================================================================

function computeCoverageScore(telemetryIndex: TelemetryIndex | null | undefined): number {
  if (!telemetryIndex) return 0;
  const { total_ticks, keyframe_ticks } = telemetryIndex;
  if (total_ticks === 0) return 0;
  const coverage = (keyframe_ticks.length / total_ticks) * 100;
  return Math.min(100, Math.round(coverage * 10));
}

function computeIntegrityScore(telemetryIndex: TelemetryIndex | null | undefined): number {
  if (!telemetryIndex) return 0;
  let score = 0;
  if (telemetryIndex.run_id) score += 25;
  if (telemetryIndex.total_ticks > 0) score += 25;
  if (telemetryIndex.storage_ref?.bucket && telemetryIndex.storage_ref?.key) score += 25;
  if (telemetryIndex.keyframe_ticks.length > 0) score += 25;
  return score;
}

function computeActivityScore(telemetrySummary: TelemetrySummary | null | undefined): number {
  if (!telemetrySummary) return 0;
  const { total_agents, total_events, key_metrics } = telemetrySummary;
  if (total_agents === 0) return 0;
  const eventsPerAgent = total_events / total_agents;
  const activityRates = key_metrics?.by_tick?.map(t => t.activity_rate) || [];
  const avgActivityRate = activityRates.length > 0
    ? activityRates.reduce((a, b) => a + b, 0) / activityRates.length
    : 0.5;
  const engagementScore = Math.min(1, eventsPerAgent / 100);
  const score = (avgActivityRate * 0.6 + engagementScore * 0.4) * 100;
  return Math.round(Math.min(100, score));
}

function computeStabilityScore(runs: RunSummary[] | undefined, nodeId: string | null): number | null {
  if (!runs || !nodeId) return null;
  const nodeRuns = runs.filter(r => r.node_id === nodeId && r.status === 'succeeded');
  if (nodeRuns.length < 3) return null;
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
  const stabilityScore = Math.max(0, 100 - coeffVariation * 100);
  return Math.round(stabilityScore);
}

function computeOverallScore(metrics: Omit<ReliabilityMetrics, 'overallScore'>): number {
  const weights = { coverage: 0.25, integrity: 0.3, activity: 0.25, stability: 0.2 };
  const stabilityValue = metrics.stabilityScore ?? 50;
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
      fixAction: { label: 'Run a simulation', href: `/p/${projectId}/run-center${nodeId ? `?node=${nodeId}` : ''}` },
    });
    return warnings;
  }
  if (metrics.coverageScore < 50) {
    warnings.push({
      type: 'warning',
      message: `Low telemetry coverage (${metrics.coverageScore}%). Keyframes may be sparse.`,
      fixAction: { label: 'View telemetry', href: `/p/${projectId}/replay` },
    });
  }
  if (metrics.activityScore < 40) {
    warnings.push({ type: 'warning', message: `Low agent activity (${metrics.activityScore}%). Agents may be underutilized.` });
  }
  if (metrics.stabilityScore === null) {
    warnings.push({
      type: 'info',
      message: 'Run at least 3 simulations to calculate stability score',
      fixAction: { label: 'Queue more runs', href: `/p/${projectId}/run-center${nodeId ? `?node=${nodeId}` : ''}` },
    });
  } else if (metrics.stabilityScore < 60) {
    warnings.push({ type: 'warning', message: `Low stability (${metrics.stabilityScore}%). Results vary significantly between runs.` });
  }
  return warnings;
}

// ============================================================================
// Export Functions
// ============================================================================

interface ExportData {
  reportType: ReportType;
  generatedAt: string;
  projectId: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: Record<string, any>;
}

function exportToJSON(data: ExportData, filename: string) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${filename}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

function exportToMarkdown(data: ExportData, filename: string) {
  let md = `# ${data.reportType.charAt(0).toUpperCase() + data.reportType.slice(1)} Report\n\n`;
  md += `**Generated:** ${data.generatedAt}\n`;
  md += `**Project ID:** ${data.projectId}\n\n`;
  md += `---\n\n`;

  const formatValue = (val: unknown): string => {
    if (val === null || val === undefined) return 'N/A';
    if (typeof val === 'object') return JSON.stringify(val, null, 2);
    return String(val);
  };

  const renderSection = (title: string, obj: Record<string, unknown>) => {
    md += `## ${title}\n\n`;
    for (const [key, value] of Object.entries(obj)) {
      md += `- **${key}:** ${formatValue(value)}\n`;
    }
    md += `\n`;
  };

  for (const [sectionKey, sectionValue] of Object.entries(data.data)) {
    if (typeof sectionValue === 'object' && sectionValue !== null) {
      renderSection(sectionKey, sectionValue as Record<string, unknown>);
    } else {
      md += `**${sectionKey}:** ${formatValue(sectionValue)}\n`;
    }
  }

  const blob = new Blob([md], { type: 'text/markdown' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${filename}.md`;
  a.click();
  URL.revokeObjectURL(url);
}

// ============================================================================
// MVP Demo2 Report Component (Task 7: Minimal report export)
// ============================================================================

interface MvpReportData {
  goal: string;
  mode: string;
  cutoffDate: string | null;
  personas: {
    count: number;
    generationMethod: string;
    status: string;
  } | null;
  evidence: {
    total: number;
    passed: number;
    warned: number;
    failed: number;
    urls: string[];
  } | null;
  baselineRun: {
    runId: string;
    status: string;
    probability: number | null;
    createdAt: string;
  } | null;
  branchRuns: {
    runId: string;
    label: string;
    status: string;
    probability: number | null;
    deltaFromBaseline: number | null;
    createdAt: string;
  }[];
  manifests: {
    runId: string;
    manifestId: string | null;
  }[];
}

function generateMvpReport(data: MvpReportData, projectId: string): ExportData {
  return {
    reportType: 'mvp',
    generatedAt: new Date().toISOString(),
    projectId,
    data: {
      'Project Summary': {
        goal: data.goal || 'Not specified',
        mode: data.mode || 'Collective Dynamics',
        temporalCutoff: data.cutoffDate || 'Not set',
      },
      'Personas': data.personas ? {
        count: data.personas.count,
        generationMethod: data.personas.generationMethod,
        status: data.personas.status,
      } : { status: 'Not generated' },
      'Evidence': data.evidence ? {
        totalSources: data.evidence.total,
        passed: data.evidence.passed,
        warned: data.evidence.warned,
        failed: data.evidence.failed,
        urls: data.evidence.urls.slice(0, 10), // Limit to first 10
      } : { status: 'No evidence ingested' },
      'Baseline Run': data.baselineRun ? {
        runId: data.baselineRun.runId,
        status: data.baselineRun.status,
        probability: data.baselineRun.probability != null
          ? `${(data.baselineRun.probability * 100).toFixed(1)}%`
          : 'N/A',
        createdAt: data.baselineRun.createdAt,
      } : { status: 'No baseline run' },
      'Branch Runs': data.branchRuns.length > 0 ? data.branchRuns.map(br => ({
        runId: br.runId,
        label: br.label,
        status: br.status,
        probability: br.probability != null
          ? `${(br.probability * 100).toFixed(1)}%`
          : 'N/A',
        deltaFromBaseline: br.deltaFromBaseline != null
          ? `${br.deltaFromBaseline > 0 ? '+' : ''}${(br.deltaFromBaseline * 100).toFixed(1)}%`
          : 'N/A',
        createdAt: br.createdAt,
      })) : 'No branch runs',
      'Run Manifests': data.manifests.length > 0
        ? data.manifests.map(m => ({ runId: m.runId, manifestId: m.manifestId || 'N/A' }))
        : 'No manifests',
    },
  };
}

interface MvpReportProps {
  projectId: string;
  onExportJSON: (data: ExportData) => void;
  onExportMarkdown: (data: ExportData) => void;
  onCopyLink: () => void;
  linkCopied: boolean;
}

function MvpReport({ projectId, onExportJSON, onExportMarkdown, onCopyLink, linkCopied }: MvpReportProps) {
  const { data: project, isLoading: projectLoading } = useProjectSpec(projectId);
  const { data: nodes, isLoading: nodesLoading } = useNodes({ project_id: projectId });
  const { data: runs, isLoading: runsLoading } = useRuns({ project_id: projectId, limit: 100 });

  const isLoading = projectLoading || nodesLoading || runsLoading;

  // Compute report data
  const reportData = useMemo<MvpReportData | null>(() => {
    if (!project) return null;

    // Find baseline node and runs
    const baselineNode = nodes?.find(n => n.is_baseline);
    const baselineRuns = runs?.filter(r => r.node_id === baselineNode?.node_id && r.status === 'succeeded') || [];
    const latestBaselineRun = baselineRuns.sort((a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    )[0];

    // Find branch runs (non-baseline nodes)
    const branchNodes = nodes?.filter(n => !n.is_baseline) || [];
    const branchRuns = branchNodes.flatMap(node => {
      const nodeRuns = runs?.filter(r => r.node_id === node.node_id && r.status === 'succeeded') || [];
      if (nodeRuns.length === 0) return [];
      const latestRun = nodeRuns.sort((a, b) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      )[0];
      const baselineProbability = baselineNode?.probability ?? null;
      return [{
        runId: latestRun.run_id,
        label: node.label || `Branch ${node.node_id.slice(0, 8)}`,
        status: latestRun.status,
        probability: node.probability,
        deltaFromBaseline: baselineProbability != null && node.probability != null
          ? node.probability - baselineProbability
          : null,
        createdAt: latestRun.created_at,
      }];
    });

    // Get manifests from runs (use run_id as manifest reference)
    const manifests = runs?.filter(r => r.status === 'succeeded').map(r => ({
      runId: r.run_id,
      manifestId: r.run_id, // Use run_id as manifest reference
    })) || [];

    // Get personas count from project settings (default_agent_count)
    const personasCount = project?.settings?.default_agent_count || 0;

    // Extract goal from description or use project name
    const goalText = project.description || project.name || 'Not specified';

    return {
      goal: goalText,
      mode: project.domain || 'Collective Dynamics',
      cutoffDate: project.temporal_context?.as_of_datetime || null,
      personas: personasCount > 0 ? {
        count: personasCount,
        generationMethod: 'Natural Language Generation',
        status: 'Active',
      } : null,
      // Evidence data not yet integrated - will be populated when evidence API is connected
      evidence: null,
      baselineRun: latestBaselineRun ? {
        runId: latestBaselineRun.run_id,
        status: latestBaselineRun.status,
        probability: baselineNode?.probability ?? null,
        createdAt: latestBaselineRun.created_at,
      } : null,
      branchRuns,
      manifests,
    };
  }, [project, nodes, runs]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-12">
        <Loader2 className="w-8 h-8 animate-spin text-cyan-400" />
      </div>
    );
  }

  if (!project || !reportData) {
    return (
      <div className="border border-red-500/20 bg-red-500/5 p-8 text-center">
        <XCircle className="w-12 h-12 mx-auto text-red-400/40 mb-4" />
        <h2 className="text-lg font-mono font-bold text-white mb-2">Project Not Found</h2>
        <p className="text-sm font-mono text-white/50">Could not load project data.</p>
      </div>
    );
  }

  const exportData = generateMvpReport(reportData, projectId);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border border-cyan-500/30 bg-cyan-500/5 p-4">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <FileBarChart className="w-5 h-5 text-cyan-400" />
              <h2 className="text-lg font-mono font-bold text-white">Demo2 MVP Report</h2>
            </div>
            <p className="text-sm font-mono text-white/60">
              Comprehensive summary with predictions, evidence, and manifests
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={onCopyLink} className="text-xs">
              {linkCopied ? <Check className="w-3 h-3 mr-1" /> : <Copy className="w-3 h-3 mr-1" />}
              {linkCopied ? 'Copied!' : 'Copy Link'}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onExportJSON(exportData)}
              className="text-xs border-cyan-500/30 hover:bg-cyan-500/10"
            >
              <Download className="w-3 h-3 mr-1" /> JSON
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onExportMarkdown(exportData)}
              className="text-xs border-cyan-500/30 hover:bg-cyan-500/10"
            >
              <FileText className="w-3 h-3 mr-1" /> Markdown
            </Button>
          </div>
        </div>
      </div>

      {/* Project Summary */}
      <div className="border border-white/10 bg-white/5 p-4">
        <h3 className="text-sm font-mono font-bold text-white/60 uppercase mb-4 flex items-center gap-2">
          <Layers className="w-4 h-4" /> Project Summary
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-3 border border-white/10 bg-white/5">
            <div className="text-[10px] font-mono text-white/40 uppercase">Goal</div>
            <div className="text-sm font-mono text-white mt-1">{reportData.goal}</div>
          </div>
          <div className="p-3 border border-white/10 bg-white/5">
            <div className="text-[10px] font-mono text-white/40 uppercase">Mode</div>
            <div className="text-sm font-mono text-white mt-1">{reportData.mode}</div>
          </div>
          <div className="p-3 border border-white/10 bg-white/5">
            <div className="text-[10px] font-mono text-white/40 uppercase">Temporal Cutoff</div>
            <div className="text-sm font-mono text-white mt-1 flex items-center gap-1">
              <Calendar className="w-3 h-3 text-cyan-400" />
              {reportData.cutoffDate
                ? new Date(reportData.cutoffDate).toLocaleDateString()
                : 'Not set'}
            </div>
          </div>
        </div>
      </div>

      {/* Personas Summary */}
      <div className="border border-white/10 bg-white/5 p-4">
        <h3 className="text-sm font-mono font-bold text-white/60 uppercase mb-4 flex items-center gap-2">
          <Users className="w-4 h-4" /> Personas
        </h3>
        {reportData.personas ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-3 border border-green-500/20 bg-green-500/5">
              <div className="text-[10px] font-mono text-green-400 uppercase">Count</div>
              <div className="text-xl font-mono font-bold text-green-400">{reportData.personas.count.toLocaleString()}</div>
            </div>
            <div className="p-3 border border-white/10 bg-white/5">
              <div className="text-[10px] font-mono text-white/40 uppercase">Generation Method</div>
              <div className="text-sm font-mono text-white mt-1">{reportData.personas.generationMethod}</div>
            </div>
            <div className="p-3 border border-white/10 bg-white/5">
              <div className="text-[10px] font-mono text-white/40 uppercase">Status</div>
              <div className="text-sm font-mono text-white mt-1 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3 text-green-400" />
                {reportData.personas.status}
              </div>
            </div>
          </div>
        ) : (
          <div className="p-4 border border-yellow-500/20 bg-yellow-500/5 text-center">
            <AlertTriangle className="w-6 h-6 mx-auto text-yellow-400/60 mb-2" />
            <p className="text-sm font-mono text-white/50">No personas generated yet</p>
            <Link href={`/p/${projectId}/data-personas`}>
              <Button variant="outline" size="sm" className="mt-2 text-xs">
                <Users className="w-3 h-3 mr-1" /> Generate Personas
              </Button>
            </Link>
          </div>
        )}
      </div>

      {/* Evidence Summary */}
      <div className="border border-white/10 bg-white/5 p-4">
        <h3 className="text-sm font-mono font-bold text-white/60 uppercase mb-4 flex items-center gap-2">
          <Database className="w-4 h-4" /> Evidence Sources
        </h3>
        {reportData.evidence && reportData.evidence.total > 0 ? (
          <div className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-3 border border-white/10 bg-white/5">
                <div className="text-[10px] font-mono text-white/40 uppercase">Total</div>
                <div className="text-xl font-mono font-bold text-white">{reportData.evidence.total}</div>
              </div>
              <div className="p-3 border border-green-500/20 bg-green-500/5">
                <div className="text-[10px] font-mono text-green-400 uppercase">Passed</div>
                <div className="text-xl font-mono font-bold text-green-400">{reportData.evidence.passed}</div>
              </div>
              <div className="p-3 border border-yellow-500/20 bg-yellow-500/5">
                <div className="text-[10px] font-mono text-yellow-400 uppercase">Warned</div>
                <div className="text-xl font-mono font-bold text-yellow-400">{reportData.evidence.warned}</div>
              </div>
              <div className="p-3 border border-red-500/20 bg-red-500/5">
                <div className="text-[10px] font-mono text-red-400 uppercase">Failed</div>
                <div className="text-xl font-mono font-bold text-red-400">{reportData.evidence.failed}</div>
              </div>
            </div>
            {reportData.evidence.urls.length > 0 && (
              <div className="p-3 border border-white/5 bg-white/[0.02]">
                <div className="text-[10px] font-mono text-white/40 uppercase mb-2">Source URLs</div>
                <div className="space-y-1 max-h-[150px] overflow-auto">
                  {reportData.evidence.urls.map((url, i) => (
                    <div key={i} className="text-xs font-mono text-cyan-400/70 truncate">{url}</div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="p-4 border border-white/5 bg-white/[0.02] text-center">
            <p className="text-sm font-mono text-white/50">No evidence sources ingested</p>
          </div>
        )}
      </div>

      {/* Baseline vs Branch Comparison */}
      <div className="border border-white/10 bg-white/5 p-4">
        <h3 className="text-sm font-mono font-bold text-white/60 uppercase mb-4 flex items-center gap-2">
          <GitBranch className="w-4 h-4" /> Baseline vs Branch Comparison
        </h3>
        <div className="space-y-4">
          {/* Baseline */}
          {reportData.baselineRun ? (
            <div className="p-4 border border-cyan-500/30 bg-cyan-500/5">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono text-cyan-400 border border-cyan-400/30 px-2 py-0.5">BASELINE</span>
                  <span className="text-sm font-mono text-white">Run {reportData.baselineRun.runId.slice(0, 8)}</span>
                </div>
                <span className={cn(
                  'text-[10px] font-mono px-2 py-0.5 border',
                  reportData.baselineRun.status === 'succeeded'
                    ? 'text-green-400 border-green-400/30'
                    : 'text-white/40 border-white/10'
                )}>
                  {reportData.baselineRun.status.toUpperCase()}
                </span>
              </div>
              <div className="text-3xl font-mono font-bold text-cyan-400">
                {reportData.baselineRun.probability != null
                  ? `${(reportData.baselineRun.probability * 100).toFixed(1)}%`
                  : 'N/A'}
              </div>
              <div className="text-[10px] font-mono text-white/40 mt-1">
                {new Date(reportData.baselineRun.createdAt).toLocaleString()}
              </div>
            </div>
          ) : (
            <div className="p-4 border border-yellow-500/20 bg-yellow-500/5 text-center">
              <AlertTriangle className="w-6 h-6 mx-auto text-yellow-400/60 mb-2" />
              <p className="text-sm font-mono text-white/50">No baseline run completed</p>
              <Link href={`/p/${projectId}/run-center`}>
                <Button variant="outline" size="sm" className="mt-2 text-xs">
                  <Play className="w-3 h-3 mr-1" /> Run Baseline
                </Button>
              </Link>
            </div>
          )}

          {/* Branches */}
          {reportData.branchRuns.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {reportData.branchRuns.map((branch) => (
                <div key={branch.runId} className="p-4 border border-purple-500/30 bg-purple-500/5">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono text-purple-400 border border-purple-400/30 px-2 py-0.5">BRANCH</span>
                      <span className="text-sm font-mono text-white truncate max-w-[150px]">{branch.label}</span>
                    </div>
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-2xl font-mono font-bold text-purple-400">
                      {branch.probability != null
                        ? `${(branch.probability * 100).toFixed(1)}%`
                        : 'N/A'}
                    </span>
                    {branch.deltaFromBaseline != null && (
                      <span className={cn(
                        'text-sm font-mono',
                        branch.deltaFromBaseline > 0 ? 'text-green-400' :
                        branch.deltaFromBaseline < 0 ? 'text-red-400' : 'text-white/40'
                      )}>
                        ({branch.deltaFromBaseline > 0 ? '+' : ''}{(branch.deltaFromBaseline * 100).toFixed(1)}%)
                      </span>
                    )}
                  </div>
                  <div className="text-[10px] font-mono text-white/40 mt-1">
                    {new Date(branch.createdAt).toLocaleString()}
                  </div>
                </div>
              ))}
            </div>
          ) : reportData.baselineRun ? (
            <div className="p-4 border border-white/5 bg-white/[0.02] text-center">
              <p className="text-sm font-mono text-white/50">No branch scenarios run yet</p>
              <Link href={`/p/${projectId}/event-lab`}>
                <Button variant="outline" size="sm" className="mt-2 text-xs">
                  <Zap className="w-3 h-3 mr-1" /> Ask What-If
                </Button>
              </Link>
            </div>
          ) : null}
        </div>
      </div>

      {/* Manifest IDs */}
      {reportData.manifests.length > 0 && (
        <div className="border border-white/10 bg-white/5 p-4">
          <h3 className="text-sm font-mono font-bold text-white/60 uppercase mb-4 flex items-center gap-2">
            <Settings className="w-4 h-4" /> Run Manifests
          </h3>
          <div className="space-y-2 max-h-[200px] overflow-auto">
            {reportData.manifests.map((m) => (
              <div key={m.runId} className="flex items-center justify-between p-2 border border-white/5 bg-white/[0.02]">
                <span className="text-xs font-mono text-white/60">Run {m.runId.slice(0, 8)}</span>
                <span className="text-xs font-mono text-cyan-400">{m.manifestId || 'N/A'}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="border border-white/5 bg-white/[0.02] p-4 text-center">
        <div className="text-[10px] font-mono text-white/30 flex items-center justify-center gap-2">
          <Terminal className="w-3 h-3" />
          Report generated at {new Date().toLocaleString()} • AgentVerse Demo2 MVP
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// UI Components
// ============================================================================

interface ScoreRingProps {
  score: number;
  size?: 'sm' | 'md' | 'lg';
  label?: string;
  loading?: boolean;
}

function ScoreRing({ score, size = 'md', label, loading = false }: ScoreRingProps) {
  const sizeClasses = { sm: 'w-16 h-16', md: 'w-24 h-24', lg: 'w-32 h-32' };
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
        <circle cx="50%" cy="50%" r={radius} fill="none" stroke="currentColor" strokeWidth={strokeWidth} className="text-white/10" />
        <circle
          cx="50%" cy="50%" r={radius} fill="none" stroke="currentColor" strokeWidth={strokeWidth}
          strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round"
          className={cn(loading ? 'text-cyan-400/50' : getColor(score), 'transition-all duration-700')}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        {loading ? <span className="text-sm font-mono text-white/40">...</span> : (
          <span className={cn('font-mono font-bold', size === 'lg' ? 'text-2xl' : size === 'md' ? 'text-lg' : 'text-sm')}>{score}</span>
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
  const styles = { error: 'border-red-500/30 bg-red-500/10', warning: 'border-yellow-500/30 bg-yellow-500/10', info: 'border-cyan-500/30 bg-cyan-500/10' };
  const icons = { error: XCircle, warning: AlertTriangle, info: Info };
  const textColors = { error: 'text-red-400', warning: 'text-yellow-400', info: 'text-cyan-400' };
  const Icon = icons[warning.type];
  return (
    <div className={cn('border p-3 flex items-start gap-3', styles[warning.type])}>
      <Icon className={cn('w-4 h-4 flex-shrink-0 mt-0.5', textColors[warning.type])} />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-mono text-white/80">{warning.message}</p>
        {warning.fixAction && (
          <Link href={warning.fixAction.href} className={cn('inline-flex items-center gap-1 text-xs font-mono mt-1', textColors[warning.type], 'hover:underline')}>
            {warning.fixAction.label}
            <ExternalLink className="w-3 h-3" />
          </Link>
        )}
      </div>
    </div>
  );
}

interface ReportTypeSelectorProps {
  value: ReportType;
  onChange: (type: ReportType) => void;
}

function ReportTypeSelector({ value, onChange }: ReportTypeSelectorProps) {
  const mvpMode = isMvpMode();

  // In MVP mode, only show MVP report option
  const types: { value: ReportType; label: string; icon: React.ElementType; color: string }[] = mvpMode
    ? [
        { value: 'mvp', label: 'MVP Report', icon: FileBarChart, color: 'cyan' },
      ]
    : [
        { value: 'project', label: 'Project Overview', icon: Layers, color: 'cyan' },
        { value: 'node', label: 'Node Summary', icon: GitBranch, color: 'purple' },
        { value: 'run', label: 'Run Report', icon: Play, color: 'green' },
        { value: 'prediction', label: 'Prediction Report', icon: Target, color: 'orange' },
      ];
  return (
    <div className="flex gap-2">
      {types.map(t => (
        <button
          key={t.value}
          onClick={() => onChange(t.value)}
          className={cn(
            'flex items-center gap-2 px-4 py-2 border transition-all',
            value === t.value
              ? `border-${t.color}-500/50 bg-${t.color}-500/10`
              : 'border-white/10 bg-white/5 hover:bg-white/10'
          )}
        >
          <t.icon className={cn('w-4 h-4', value === t.value ? `text-${t.color}-400` : 'text-white/40')} />
          <span className="text-sm font-mono">{t.label}</span>
        </button>
      ))}
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
      <button onClick={() => setOpen(!open)} disabled={loading}
        className={cn('flex items-center gap-2 px-3 py-2 border border-white/10 bg-white/5 hover:bg-white/10 transition-colors min-w-[200px] disabled:opacity-50')}>
        {loading ? <Loader2 className="w-4 h-4 animate-spin text-white/40" /> : <GitBranch className={cn('w-4 h-4', selectedNode?.is_baseline ? 'text-cyan-400' : 'text-purple-400')} />}
        <span className="flex-1 text-left text-sm font-mono truncate">{selectedNode ? (selectedNode.label || `Node ${selectedNode.node_id.slice(0, 8)}`) : 'Select node...'}</span>
        <ChevronDown className="w-4 h-4 text-white/40" />
      </button>
      {open && nodes && (
        <div className="absolute z-50 mt-1 w-full border border-white/10 bg-black/95 backdrop-blur max-h-[300px] overflow-auto">
          {nodes.map(node => (
            <button key={node.node_id} onClick={() => { onSelect(node.node_id); setOpen(false); }}
              className={cn('w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-white/10 transition-colors', node.node_id === selectedNodeId && 'bg-cyan-500/10')}>
              <GitBranch className={cn('w-4 h-4', node.is_baseline ? 'text-cyan-400' : 'text-purple-400')} />
              <span className="flex-1 text-sm font-mono truncate">{node.label || `Node ${node.node_id.slice(0, 8)}`}</span>
              {node.is_baseline && <span className="text-[10px] font-mono text-cyan-400 border border-cyan-400/30 px-1">BASELINE</span>}
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
      <button onClick={() => setOpen(!open)} disabled={loading || succeededRuns.length === 0}
        className={cn('flex items-center gap-2 px-3 py-2 border border-white/10 bg-white/5 hover:bg-white/10 transition-colors min-w-[200px] disabled:opacity-50')}>
        {loading ? <Loader2 className="w-4 h-4 animate-spin text-white/40" /> : <Play className="w-4 h-4 text-green-400" />}
        <span className="flex-1 text-left text-sm font-mono truncate">{selectedRun ? `Run ${selectedRun.run_id.slice(0, 8)}` : succeededRuns.length === 0 ? 'No runs available' : 'Select run...'}</span>
        <ChevronDown className="w-4 h-4 text-white/40" />
      </button>
      {open && succeededRuns.length > 0 && (
        <div className="absolute z-50 mt-1 w-full border border-white/10 bg-black/95 backdrop-blur max-h-[300px] overflow-auto">
          {succeededRuns.map(run => (
            <button key={run.run_id} onClick={() => { onSelect(run.run_id); setOpen(false); }}
              className={cn('w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-white/10 transition-colors', run.run_id === selectedRunId && 'bg-cyan-500/10')}>
              <Play className="w-4 h-4 text-green-400" />
              <div className="flex-1 min-w-0">
                <div className="text-sm font-mono truncate">Run {run.run_id.slice(0, 8)}</div>
                <div className="text-[10px] font-mono text-white/40">{run.timing.total_ticks} ticks • {new Date(run.created_at).toLocaleDateString()}</div>
              </div>
              <CheckCircle2 className="w-4 h-4 text-green-400" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Run Report Component
// ============================================================================

interface RunReportProps {
  projectId: string;
  runId: string;
  runs: RunSummary[] | undefined;
  onExportJSON: () => void;
  onExportMarkdown: () => void;
  onCopyLink: () => void;
  linkCopied: boolean;
}

function RunReport({ projectId, runId, runs, onExportJSON, onExportMarkdown, onCopyLink, linkCopied }: RunReportProps) {
  const { data: run, isLoading: runLoading, isError: runError } = useRun(runId);
  const { data: telemetryIndex, isError: indexError } = useTelemetryIndex(runId);
  const { data: telemetrySummary, isError: summaryError } = useTelemetrySummary(runId);
  const { data: node } = useNode(run?.node_id);

  const isLoading = runLoading;
  const hasTelemetryError = indexError || summaryError;
  const hasTelemetryData = !!telemetryIndex && !!telemetrySummary && !hasTelemetryError;

  const metrics = useMemo((): ReliabilityMetrics => {
    // Only compute metrics if we have telemetry data
    if (!hasTelemetryData) {
      return {
        coverageScore: 0,
        integrityScore: 0,
        activityScore: 0,
        stabilityScore: null,
        overallScore: 0,
      };
    }
    const coverageScore = computeCoverageScore(telemetryIndex);
    const integrityScore = computeIntegrityScore(telemetryIndex);
    const activityScore = computeActivityScore(telemetrySummary);
    const stabilityScore = computeStabilityScore(runs, run?.node_id || null);
    return {
      coverageScore, integrityScore, activityScore, stabilityScore,
      overallScore: computeOverallScore({ coverageScore, integrityScore, activityScore, stabilityScore }),
    };
  }, [telemetryIndex, telemetrySummary, runs, run?.node_id, hasTelemetryData]);

  const warnings = useMemo(() => {
    if (!hasTelemetryData) {
      return [{
        type: 'error' as const,
        message: 'Telemetry data could not be loaded for this run',
        fixAction: { label: 'View Run Center', href: `/p/${projectId}/run-center` },
      }];
    }
    return generateWarnings(metrics, telemetryIndex, telemetrySummary, run?.node_id || null, projectId);
  }, [metrics, telemetryIndex, telemetrySummary, run?.node_id, projectId, hasTelemetryData]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-12">
        <Loader2 className="w-8 h-8 animate-spin text-cyan-400" />
      </div>
    );
  }

  if (runError || !run) {
    return (
      <div className="border border-red-500/20 bg-red-500/5 p-8 text-center">
        <XCircle className="w-12 h-12 mx-auto text-red-400/40 mb-4" />
        <h2 className="text-lg font-mono font-bold text-white mb-2">Run Not Found</h2>
        <p className="text-sm font-mono text-white/50">The specified run could not be loaded.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Section 1: Header */}
      <div className="border border-white/10 bg-white/5 p-4">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Play className="w-5 h-5 text-green-400" />
              <h2 className="text-lg font-mono font-bold text-white">Run Report</h2>
            </div>
            <div className="text-sm font-mono text-white/60">
              <span className="text-cyan-400">{runId.slice(0, 8)}</span>
              <span className="mx-2">•</span>
              <span>{new Date(run.created_at).toLocaleString()}</span>
            </div>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={onCopyLink} className="text-xs">
              {linkCopied ? <Check className="w-3 h-3 mr-1" /> : <Copy className="w-3 h-3 mr-1" />}
              {linkCopied ? 'Copied!' : 'Copy Link'}
            </Button>
            <Button variant="outline" size="sm" onClick={onExportJSON} className="text-xs">
              <Download className="w-3 h-3 mr-1" />
              JSON
            </Button>
            <Button variant="outline" size="sm" onClick={onExportMarkdown} className="text-xs">
              <FileText className="w-3 h-3 mr-1" />
              Markdown
            </Button>
          </div>
        </div>
      </div>

      {/* Section 2: Executive Summary */}
      <div className="border border-white/10 bg-white/5 p-4">
        <h3 className="text-sm font-mono font-bold text-white/60 uppercase mb-4">Executive Summary</h3>
        {hasTelemetryData ? (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="flex flex-col items-center p-4 border border-white/10 bg-white/5">
              <ScoreRing score={metrics.overallScore} size="md" />
              <span className="mt-2 text-xs font-mono text-white/60">Overall Score</span>
            </div>
            <div className="col-span-3 grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="p-3 border border-white/10 bg-white/5">
                <div className="text-[10px] font-mono text-white/40 uppercase flex items-center gap-1"><Target className="w-3 h-3" /> Coverage</div>
                <div className={cn('text-xl font-mono font-bold', metrics.coverageScore >= 60 ? 'text-green-400' : 'text-yellow-400')}>{metrics.coverageScore}</div>
              </div>
              <div className="p-3 border border-white/10 bg-white/5">
                <div className="text-[10px] font-mono text-white/40 uppercase flex items-center gap-1"><Database className="w-3 h-3" /> Integrity</div>
                <div className={cn('text-xl font-mono font-bold', metrics.integrityScore >= 60 ? 'text-green-400' : 'text-yellow-400')}>{metrics.integrityScore}</div>
              </div>
              <div className="p-3 border border-white/10 bg-white/5">
                <div className="text-[10px] font-mono text-white/40 uppercase flex items-center gap-1"><Activity className="w-3 h-3" /> Activity</div>
                <div className={cn('text-xl font-mono font-bold', metrics.activityScore >= 60 ? 'text-green-400' : 'text-yellow-400')}>{metrics.activityScore}</div>
              </div>
              <div className="p-3 border border-white/10 bg-white/5">
                <div className="text-[10px] font-mono text-white/40 uppercase flex items-center gap-1"><BarChart3 className="w-3 h-3" /> Stability</div>
                <div className={cn('text-xl font-mono font-bold', metrics.stabilityScore !== null && metrics.stabilityScore >= 60 ? 'text-green-400' : 'text-white/30')}>
                  {metrics.stabilityScore ?? '--'}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-4 p-4 border border-white/10 bg-white/5">
            <div className="flex flex-col items-center">
              <ScoreRing score={0} size="md" loading={!hasTelemetryError} />
              <span className="mt-2 text-xs font-mono text-white/40">
                {hasTelemetryError ? 'Unavailable' : 'Loading...'}
              </span>
            </div>
            <div className="flex-1">
              <p className="text-sm font-mono text-white/60">
                {hasTelemetryError
                  ? 'Telemetry data could not be loaded. Reliability metrics are unavailable for this run.'
                  : 'Loading telemetry data...'}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Section 3: Reliability Snapshot with Warnings */}
      {warnings.length > 0 && (
        <div className="border border-white/10 bg-white/5 p-4">
          <h3 className="text-sm font-mono font-bold text-white/60 uppercase mb-4">Warnings & Recommendations</h3>
          <div className="space-y-2">
            {warnings.map((warning, i) => <WarningCard key={i} warning={warning} />)}
          </div>
        </div>
      )}

      {/* Section 4: Run Configuration */}
      <div className="border border-white/10 bg-white/5 p-4">
        <h3 className="text-sm font-mono font-bold text-white/60 uppercase mb-4">Run Configuration</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <div className="text-[10px] font-mono text-white/40 uppercase">Node</div>
            <div className="text-sm font-mono text-white flex items-center gap-1">
              <GitBranch className={cn('w-3 h-3', node?.is_baseline ? 'text-cyan-400' : 'text-purple-400')} />
              {node?.label || run.node_id.slice(0, 8)}
            </div>
          </div>
          <div>
            <div className="text-[10px] font-mono text-white/40 uppercase">Status</div>
            <div className="text-sm font-mono text-green-400 flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3" /> {run.status.toUpperCase()}
            </div>
          </div>
          <div>
            <div className="text-[10px] font-mono text-white/40 uppercase">Total Ticks</div>
            <div className="text-sm font-mono text-cyan-400">{run.timing.total_ticks}</div>
          </div>
          <div>
            <div className="text-[10px] font-mono text-white/40 uppercase">Triggered By</div>
            <div className="text-sm font-mono text-white">{run.triggered_by}</div>
          </div>
        </div>
      </div>

      {/* Section 5: Timeline Highlights (Telemetry Summary) */}
      {hasTelemetryData && telemetrySummary && (
        <div className="border border-white/10 bg-white/5 p-4">
          <h3 className="text-sm font-mono font-bold text-white/60 uppercase mb-4">Timeline Highlights</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-3 border border-cyan-500/20 bg-cyan-500/5">
              <div className="text-[10px] font-mono text-cyan-400 uppercase">Total Ticks</div>
              <div className="text-xl font-mono font-bold text-white">{telemetrySummary.total_ticks}</div>
            </div>
            <div className="p-3 border border-cyan-500/20 bg-cyan-500/5">
              <div className="text-[10px] font-mono text-cyan-400 uppercase">Total Events</div>
              <div className="text-xl font-mono font-bold text-white">{telemetrySummary.total_events}</div>
            </div>
            <div className="p-3 border border-cyan-500/20 bg-cyan-500/5">
              <div className="text-[10px] font-mono text-cyan-400 uppercase">Agents</div>
              <div className="text-xl font-mono font-bold text-white">{telemetrySummary.total_agents}</div>
            </div>
            <div className="p-3 border border-cyan-500/20 bg-cyan-500/5">
              <div className="text-[10px] font-mono text-cyan-400 uppercase">Duration</div>
              <div className="text-xl font-mono font-bold text-white">{telemetrySummary.duration_seconds ?? 'N/A'}{telemetrySummary.duration_seconds !== undefined && 's'}</div>
            </div>
          </div>
          {Object.keys(telemetrySummary.event_type_counts || {}).length > 0 && (
            <div className="mt-4">
              <div className="text-[10px] font-mono text-white/40 uppercase mb-2">Event Types</div>
              <div className="flex flex-wrap gap-2">
                {Object.entries(telemetrySummary.event_type_counts).map(([type, count]) => (
                  <span key={type} className="text-xs font-mono px-2 py-1 border border-white/10 bg-white/5">
                    {type}: <span className="text-cyan-400">{count}</span>
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Section 6: Branch Comparison (if not baseline) */}
      {node && !node.is_baseline && (
        <div className="border border-purple-500/20 bg-purple-500/5 p-4">
          <h3 className="text-sm font-mono font-bold text-white/60 uppercase mb-4">Branch Information</h3>
          <div className="flex items-center gap-3">
            <GitBranch className="w-5 h-5 text-purple-400" />
            <div>
              <div className="text-sm font-mono text-white">This run is from a branch node</div>
              <div className="text-[10px] font-mono text-white/40">Compare with baseline for delta analysis</div>
            </div>
            <Link href={`/p/${projectId}/reliability?node=${run.node_id}`} className="ml-auto">
              <Button variant="outline" size="sm" className="text-xs">View in Reliability</Button>
            </Link>
          </div>
        </div>
      )}

      {/* Section 7: Quick Navigation */}
      <div className="border border-white/10 bg-white/5 p-4">
        <h3 className="text-sm font-mono font-bold text-white/60 uppercase mb-4">Quick Navigation</h3>
        <div className="flex flex-wrap gap-2">
          <Link href={`/p/${projectId}/replay?run=${runId}`}>
            <Button variant="outline" size="sm" className="text-xs"><Play className="w-3 h-3 mr-1" /> View Replay</Button>
          </Link>
          <Link href={`/p/${projectId}/universe-map?node=${run.node_id}`}>
            <Button variant="outline" size="sm" className="text-xs"><GitBranch className="w-3 h-3 mr-1" /> Universe Map</Button>
          </Link>
          <Link href={`/p/${projectId}/reliability?node=${run.node_id}`}>
            <Button variant="outline" size="sm" className="text-xs"><Activity className="w-3 h-3 mr-1" /> Reliability</Button>
          </Link>
          <Link href={`/p/${projectId}/run-center?node=${run.node_id}`}>
            <Button variant="outline" size="sm" className="text-xs"><Zap className="w-3 h-3 mr-1" /> Run Center</Button>
          </Link>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Node Summary Report Component
// ============================================================================

interface NodeSummaryReportProps {
  projectId: string;
  nodeId: string;
  onExportJSON: () => void;
  onExportMarkdown: () => void;
  onCopyLink: () => void;
  linkCopied: boolean;
}

function NodeSummaryReport({ projectId, nodeId, onExportJSON, onExportMarkdown, onCopyLink, linkCopied }: NodeSummaryReportProps) {
  const { data: node, isLoading: nodeLoading } = useNode(nodeId);
  const { data: runs, isLoading: runsLoading } = useRuns({ project_id: projectId, node_id: nodeId, limit: 100 });

  const isLoading = nodeLoading || runsLoading;

  const stats = useMemo(() => {
    if (!runs) return null;
    const succeededRuns = runs.filter(r => r.status === 'succeeded');
    const failedRuns = runs.filter(r => r.status === 'failed');
    const totalRuns = runs.length;
    const successRate = totalRuns > 0 ? (succeededRuns.length / totalRuns) * 100 : 0;
    const latestRun = runs.length > 0 ? runs.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0] : null;
    return { totalRuns, succeededRuns: succeededRuns.length, failedRuns: failedRuns.length, successRate, latestRun };
  }, [runs]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-12">
        <Loader2 className="w-8 h-8 animate-spin text-cyan-400" />
      </div>
    );
  }

  if (!node) {
    return (
      <div className="border border-red-500/20 bg-red-500/5 p-8 text-center">
        <XCircle className="w-12 h-12 mx-auto text-red-400/40 mb-4" />
        <h2 className="text-lg font-mono font-bold text-white mb-2">Node Not Found</h2>
        <p className="text-sm font-mono text-white/50">The specified node could not be loaded.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border border-white/10 bg-white/5 p-4">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <GitBranch className={cn('w-5 h-5', node.is_baseline ? 'text-cyan-400' : 'text-purple-400')} />
              <h2 className="text-lg font-mono font-bold text-white">Node Summary</h2>
              {node.is_baseline && <span className="text-[10px] font-mono text-cyan-400 border border-cyan-400/30 px-2 py-0.5">BASELINE</span>}
            </div>
            <div className="text-sm font-mono text-white/60">
              <span className={node.is_baseline ? 'text-cyan-400' : 'text-purple-400'}>{node.label || nodeId.slice(0, 8)}</span>
              <span className="mx-2">•</span>
              <span>Created {new Date(node.created_at).toLocaleDateString()}</span>
            </div>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={onCopyLink} className="text-xs">
              {linkCopied ? <Check className="w-3 h-3 mr-1" /> : <Copy className="w-3 h-3 mr-1" />}
              {linkCopied ? 'Copied!' : 'Copy Link'}
            </Button>
            <Button variant="outline" size="sm" onClick={onExportJSON} className="text-xs">
              <Download className="w-3 h-3 mr-1" /> JSON
            </Button>
            <Button variant="outline" size="sm" onClick={onExportMarkdown} className="text-xs">
              <FileText className="w-3 h-3 mr-1" /> Markdown
            </Button>
          </div>
        </div>
      </div>

      {/* Node Properties */}
      <div className="border border-white/10 bg-white/5 p-4">
        <h3 className="text-sm font-mono font-bold text-white/60 uppercase mb-4">Node Properties</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <div className="text-[10px] font-mono text-white/40 uppercase">Probability</div>
            <div className="text-lg font-mono font-bold text-cyan-400">{(node.probability * 100).toFixed(1)}%</div>
          </div>
          <div>
            <div className="text-[10px] font-mono text-white/40 uppercase">Confidence</div>
            <div className="text-lg font-mono font-bold text-white">{node.confidence?.confidence_level || node.confidence?.level || 'N/A'}</div>
          </div>
          <div>
            <div className="text-[10px] font-mono text-white/40 uppercase">Depth</div>
            <div className="text-lg font-mono font-bold text-white">{node.depth}</div>
          </div>
          <div>
            <div className="text-[10px] font-mono text-white/40 uppercase">Has Outcome</div>
            <div className="text-lg font-mono font-bold">{node.aggregated_outcome ? <CheckCircle2 className="w-5 h-5 text-green-400" /> : <XCircle className="w-5 h-5 text-white/30" />}</div>
          </div>
        </div>
      </div>

      {/* Run Statistics */}
      {stats && (
        <div className="border border-white/10 bg-white/5 p-4">
          <h3 className="text-sm font-mono font-bold text-white/60 uppercase mb-4">Run Statistics</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-3 border border-white/10 bg-white/5">
              <div className="text-[10px] font-mono text-white/40 uppercase">Total Runs</div>
              <div className="text-xl font-mono font-bold text-white">{stats.totalRuns}</div>
            </div>
            <div className="p-3 border border-green-500/20 bg-green-500/5">
              <div className="text-[10px] font-mono text-green-400 uppercase">Succeeded</div>
              <div className="text-xl font-mono font-bold text-green-400">{stats.succeededRuns}</div>
            </div>
            <div className="p-3 border border-red-500/20 bg-red-500/5">
              <div className="text-[10px] font-mono text-red-400 uppercase">Failed</div>
              <div className="text-xl font-mono font-bold text-red-400">{stats.failedRuns}</div>
            </div>
            <div className="p-3 border border-cyan-500/20 bg-cyan-500/5">
              <div className="text-[10px] font-mono text-cyan-400 uppercase">Success Rate</div>
              <div className="text-xl font-mono font-bold text-cyan-400">{stats.successRate.toFixed(1)}%</div>
            </div>
          </div>
        </div>
      )}

      {/* Run History */}
      {runs && runs.length > 0 && (
        <div className="border border-white/10 bg-white/5 p-4">
          <h3 className="text-sm font-mono font-bold text-white/60 uppercase mb-4">Run History</h3>
          <div className="space-y-2 max-h-[300px] overflow-auto">
            {runs.slice(0, 10).map(run => (
              <Link key={run.run_id} href={`/p/${projectId}/reports?run=${run.run_id}`}
                className="flex items-center gap-3 p-2 border border-white/5 bg-white/[0.02] hover:bg-white/5 transition-colors">
                <Play className={cn('w-4 h-4', run.status === 'succeeded' ? 'text-green-400' : run.status === 'failed' ? 'text-red-400' : 'text-yellow-400')} />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-mono text-white truncate">Run {run.run_id.slice(0, 8)}</div>
                  <div className="text-[10px] font-mono text-white/40">{new Date(run.created_at).toLocaleString()}</div>
                </div>
                <span className={cn('text-[10px] font-mono px-2 py-0.5 border',
                  run.status === 'succeeded' ? 'text-green-400 border-green-400/30' :
                  run.status === 'failed' ? 'text-red-400 border-red-400/30' : 'text-yellow-400 border-yellow-400/30'
                )}>{run.status.toUpperCase()}</span>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Quick Navigation */}
      <div className="border border-white/10 bg-white/5 p-4">
        <h3 className="text-sm font-mono font-bold text-white/60 uppercase mb-4">Quick Navigation</h3>
        <div className="flex flex-wrap gap-2">
          <Link href={`/p/${projectId}/universe-map?node=${nodeId}`}>
            <Button variant="outline" size="sm" className="text-xs"><GitBranch className="w-3 h-3 mr-1" /> Universe Map</Button>
          </Link>
          <Link href={`/p/${projectId}/reliability?node=${nodeId}`}>
            <Button variant="outline" size="sm" className="text-xs"><Activity className="w-3 h-3 mr-1" /> Reliability</Button>
          </Link>
          <Link href={`/p/${projectId}/run-center?node=${nodeId}`}>
            <Button variant="outline" size="sm" className="text-xs"><Zap className="w-3 h-3 mr-1" /> Run Center</Button>
          </Link>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Project Overview Report Component
// ============================================================================

interface ProjectOverviewReportProps {
  projectId: string;
  onExportJSON: () => void;
  onExportMarkdown: () => void;
  onCopyLink: () => void;
  linkCopied: boolean;
}

function ProjectOverviewReport({ projectId, onExportJSON, onExportMarkdown, onCopyLink, linkCopied }: ProjectOverviewReportProps) {
  const { data: project, isLoading: projectLoading } = useProject(projectId);
  const { data: nodes, isLoading: nodesLoading } = useNodes({ project_id: projectId });
  const { data: runs, isLoading: runsLoading } = useRuns({ project_id: projectId, limit: 100 });

  const isLoading = projectLoading || nodesLoading || runsLoading;

  const setupChecklist = useMemo(() => {
    const items = [
      { label: 'Project Created', done: !!project, icon: Layers },
      { label: 'Baseline Node Exists', done: nodes?.some(n => n.is_baseline), icon: GitBranch },
      { label: 'At Least One Run Completed', done: runs?.some(r => r.status === 'succeeded'), icon: Play },
      { label: 'Telemetry Data Available', done: runs?.some(r => r.has_results), icon: Database },
    ];
    const completedCount = items.filter(i => i.done).length;
    return { items, completedCount, total: items.length, percent: (completedCount / items.length) * 100 };
  }, [project, nodes, runs]);

  const stats = useMemo(() => {
    if (!nodes || !runs) return null;
    const baselineNode = nodes.find(n => n.is_baseline);
    const branchNodes = nodes.filter(n => !n.is_baseline);
    const succeededRuns = runs.filter(r => r.status === 'succeeded');
    const failedRuns = runs.filter(r => r.status === 'failed');
    return {
      totalNodes: nodes.length,
      baselineExists: !!baselineNode,
      branchCount: branchNodes.length,
      totalRuns: runs.length,
      succeededRuns: succeededRuns.length,
      failedRuns: failedRuns.length,
      successRate: runs.length > 0 ? (succeededRuns.length / runs.length) * 100 : 0,
    };
  }, [nodes, runs]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-12">
        <Loader2 className="w-8 h-8 animate-spin text-cyan-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border border-white/10 bg-white/5 p-4">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Layers className="w-5 h-5 text-cyan-400" />
              <h2 className="text-lg font-mono font-bold text-white">Project Overview</h2>
            </div>
            <div className="text-sm font-mono text-white/60">
              <span className="text-cyan-400">{project?.name || projectId.slice(0, 8)}</span>
              {project?.created_at && (
                <>
                  <span className="mx-2">•</span>
                  <span>Created {new Date(project.created_at).toLocaleDateString()}</span>
                </>
              )}
            </div>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={onCopyLink} className="text-xs">
              {linkCopied ? <Check className="w-3 h-3 mr-1" /> : <Copy className="w-3 h-3 mr-1" />}
              {linkCopied ? 'Copied!' : 'Copy Link'}
            </Button>
            <Button variant="outline" size="sm" onClick={onExportJSON} className="text-xs">
              <Download className="w-3 h-3 mr-1" /> JSON
            </Button>
            <Button variant="outline" size="sm" onClick={onExportMarkdown} className="text-xs">
              <FileText className="w-3 h-3 mr-1" /> Markdown
            </Button>
          </div>
        </div>
      </div>

      {/* Setup Checklist */}
      <div className="border border-white/10 bg-white/5 p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-mono font-bold text-white/60 uppercase">Setup Checklist</h3>
          <span className="text-sm font-mono text-cyan-400">{setupChecklist.completedCount}/{setupChecklist.total} Complete</span>
        </div>
        <div className="w-full bg-white/10 h-2 mb-4">
          <div className="h-2 bg-cyan-400 transition-all" style={{ width: `${setupChecklist.percent}%` }} />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {setupChecklist.items.map((item, i) => (
            <div key={i} className={cn('flex items-center gap-3 p-3 border', item.done ? 'border-green-500/20 bg-green-500/5' : 'border-white/10 bg-white/5')}>
              {item.done ? <CheckCircle2 className="w-4 h-4 text-green-400" /> : <XCircle className="w-4 h-4 text-white/30" />}
              <item.icon className={cn('w-4 h-4', item.done ? 'text-green-400' : 'text-white/30')} />
              <span className={cn('text-sm font-mono', item.done ? 'text-white' : 'text-white/50')}>{item.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Project Statistics */}
      {stats && (
        <div className="border border-white/10 bg-white/5 p-4">
          <h3 className="text-sm font-mono font-bold text-white/60 uppercase mb-4">Project Statistics</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-3 border border-cyan-500/20 bg-cyan-500/5">
              <div className="text-[10px] font-mono text-cyan-400 uppercase flex items-center gap-1"><GitBranch className="w-3 h-3" /> Nodes</div>
              <div className="text-xl font-mono font-bold text-white">{stats.totalNodes}</div>
            </div>
            <div className="p-3 border border-purple-500/20 bg-purple-500/5">
              <div className="text-[10px] font-mono text-purple-400 uppercase flex items-center gap-1"><GitBranch className="w-3 h-3" /> Branches</div>
              <div className="text-xl font-mono font-bold text-white">{stats.branchCount}</div>
            </div>
            <div className="p-3 border border-green-500/20 bg-green-500/5">
              <div className="text-[10px] font-mono text-green-400 uppercase flex items-center gap-1"><Play className="w-3 h-3" /> Runs</div>
              <div className="text-xl font-mono font-bold text-white">{stats.totalRuns}</div>
            </div>
            <div className="p-3 border border-white/10 bg-white/5">
              <div className="text-[10px] font-mono text-white/40 uppercase">Success Rate</div>
              <div className={cn('text-xl font-mono font-bold', stats.successRate >= 80 ? 'text-green-400' : stats.successRate >= 50 ? 'text-yellow-400' : 'text-red-400')}>
                {stats.successRate.toFixed(1)}%
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Nodes Overview */}
      {nodes && nodes.length > 0 && (
        <div className="border border-white/10 bg-white/5 p-4">
          <h3 className="text-sm font-mono font-bold text-white/60 uppercase mb-4">Nodes</h3>
          <div className="space-y-2 max-h-[200px] overflow-auto">
            {nodes.map(node => (
              <Link key={node.node_id} href={`/p/${projectId}/reports?node=${node.node_id}`}
                className="flex items-center gap-3 p-2 border border-white/5 bg-white/[0.02] hover:bg-white/5 transition-colors">
                <GitBranch className={cn('w-4 h-4', node.is_baseline ? 'text-cyan-400' : 'text-purple-400')} />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-mono text-white truncate">{node.label || node.node_id.slice(0, 8)}</div>
                  <div className="text-[10px] font-mono text-white/40">{node.child_count} children</div>
                </div>
                {node.is_baseline && <span className="text-[10px] font-mono text-cyan-400 border border-cyan-400/30 px-1">BASELINE</span>}
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Quick Navigation */}
      <div className="border border-white/10 bg-white/5 p-4">
        <h3 className="text-sm font-mono font-bold text-white/60 uppercase mb-4">Quick Navigation</h3>
        <div className="flex flex-wrap gap-2">
          <Link href={`/p/${projectId}/overview`}>
            <Button variant="outline" size="sm" className="text-xs"><Layers className="w-3 h-3 mr-1" /> Overview</Button>
          </Link>
          <Link href={`/p/${projectId}/universe-map`}>
            <Button variant="outline" size="sm" className="text-xs"><GitBranch className="w-3 h-3 mr-1" /> Universe Map</Button>
          </Link>
          <Link href={`/p/${projectId}/run-center`}>
            <Button variant="outline" size="sm" className="text-xs"><Zap className="w-3 h-3 mr-1" /> Run Center</Button>
          </Link>
          <Link href={`/p/${projectId}/settings`}>
            <Button variant="outline" size="sm" className="text-xs"><Settings className="w-3 h-3 mr-1" /> Settings</Button>
          </Link>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Phase 7: Prediction Report Component
// ============================================================================

interface PredictionReportParamsProps {
  metricKey: string;
  setMetricKey: (v: string) => void;
  op: ReportOperator;
  setOp: (v: ReportOperator) => void;
  threshold: number;
  setThreshold: (v: number) => void;
  windowDays: number;
  setWindowDays: (v: number) => void;
  minRuns: number;
  setMinRuns: (v: number) => void;
}

function PredictionReportParams({
  metricKey, setMetricKey, op, setOp, threshold, setThreshold,
  windowDays, setWindowDays, minRuns, setMinRuns,
}: PredictionReportParamsProps) {
  const operators: { value: ReportOperator; label: string }[] = [
    { value: 'ge', label: '>=' },
    { value: 'gt', label: '>' },
    { value: 'le', label: '<=' },
    { value: 'lt', label: '<' },
    { value: 'eq', label: '=' },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
      <div>
        <label className="text-[10px] font-mono text-white/40 uppercase mb-1 block">Metric Key</label>
        <input
          type="text"
          value={metricKey}
          onChange={(e) => setMetricKey(e.target.value)}
          placeholder="e.g., revenue"
          className="w-full px-3 py-2 bg-white/5 border border-white/10 text-sm font-mono text-white placeholder:text-white/30 focus:border-cyan-500/50 focus:outline-none"
        />
      </div>
      <div>
        <label className="text-[10px] font-mono text-white/40 uppercase mb-1 block">Operator</label>
        <select
          value={op}
          onChange={(e) => setOp(e.target.value as ReportOperator)}
          className="w-full px-3 py-2 bg-white/5 border border-white/10 text-sm font-mono text-white focus:border-cyan-500/50 focus:outline-none"
        >
          {operators.map(o => (
            <option key={o.value} value={o.value} className="bg-black">{o.label}</option>
          ))}
        </select>
      </div>
      <div>
        <label className="text-[10px] font-mono text-white/40 uppercase mb-1 block">Threshold</label>
        <input
          type="number"
          value={threshold}
          onChange={(e) => setThreshold(parseFloat(e.target.value) || 0)}
          step="0.01"
          className="w-full px-3 py-2 bg-white/5 border border-white/10 text-sm font-mono text-white focus:border-cyan-500/50 focus:outline-none"
        />
      </div>
      <div>
        <label className="text-[10px] font-mono text-white/40 uppercase mb-1 block">Window (days)</label>
        <input
          type="number"
          value={windowDays}
          onChange={(e) => setWindowDays(parseInt(e.target.value) || 30)}
          min={1}
          className="w-full px-3 py-2 bg-white/5 border border-white/10 text-sm font-mono text-white focus:border-cyan-500/50 focus:outline-none"
        />
      </div>
      <div>
        <label className="text-[10px] font-mono text-white/40 uppercase mb-1 block">Min Runs</label>
        <input
          type="number"
          value={minRuns}
          onChange={(e) => setMinRuns(parseInt(e.target.value) || 3)}
          min={1}
          className="w-full px-3 py-2 bg-white/5 border border-white/10 text-sm font-mono text-white focus:border-cyan-500/50 focus:outline-none"
        />
      </div>
    </div>
  );
}

interface DistributionHistogramProps {
  bins: number[];
  counts: number[];
  threshold: number;
  op: ReportOperator;
}

function DistributionHistogram({ bins, counts, threshold, op }: DistributionHistogramProps) {
  const maxCount = Math.max(...counts, 1);
  const barWidth = 100 / bins.length;

  // Determine which bars meet the target condition
  const meetsTarget = (binValue: number): boolean => {
    switch (op) {
      case 'ge': return binValue >= threshold;
      case 'gt': return binValue > threshold;
      case 'le': return binValue <= threshold;
      case 'lt': return binValue < threshold;
      case 'eq': return Math.abs(binValue - threshold) < 0.001;
      default: return false;
    }
  };

  return (
    <div className="h-40 flex items-end gap-[2px] px-2">
      {bins.map((bin, i) => {
        const height = (counts[i] / maxCount) * 100;
        const isTarget = meetsTarget(bin);
        return (
          <div
            key={i}
            className="relative group"
            style={{ width: `${barWidth}%`, height: '100%' }}
          >
            <div
              className={cn(
                'absolute bottom-0 w-full transition-all',
                isTarget ? 'bg-cyan-400' : 'bg-white/20'
              )}
              style={{ height: `${height}%` }}
            />
            <div className="absolute -top-8 left-1/2 -translate-x-1/2 hidden group-hover:block bg-black/90 border border-white/20 px-2 py-1 text-[10px] font-mono text-white whitespace-nowrap z-10">
              {bin.toFixed(2)}: {counts[i]}
            </div>
          </div>
        );
      })}
    </div>
  );
}

interface CalibrationCurveChartProps {
  pPred: number[];
  pTrue: number[];
  counts: number[];
}

function CalibrationCurveChart({ pPred, pTrue, counts }: CalibrationCurveChartProps) {
  // Simple SVG-based calibration curve
  const width = 200;
  const height = 200;
  const padding = 30;
  const plotWidth = width - 2 * padding;
  const plotHeight = height - 2 * padding;

  const points = pPred.map((pred, i) => ({
    x: padding + pred * plotWidth,
    y: height - padding - pTrue[i] * plotHeight,
    count: counts[i],
  }));

  return (
    <svg width={width} height={height} className="mx-auto">
      {/* Grid */}
      <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="rgba(255,255,255,0.1)" />
      <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="rgba(255,255,255,0.1)" />

      {/* Perfect calibration line */}
      <line
        x1={padding}
        y1={height - padding}
        x2={width - padding}
        y2={padding}
        stroke="rgba(255,255,255,0.3)"
        strokeDasharray="4 4"
      />

      {/* Calibration curve */}
      {points.length > 1 && (
        <polyline
          points={points.map(p => `${p.x},${p.y}`).join(' ')}
          fill="none"
          stroke="#00FFFF"
          strokeWidth={2}
        />
      )}

      {/* Points */}
      {points.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r={4} fill="#00FFFF" />
      ))}

      {/* Labels */}
      <text x={width / 2} y={height - 5} textAnchor="middle" className="text-[10px] fill-white/40 font-mono">Predicted</text>
      <text x={10} y={height / 2} textAnchor="middle" transform={`rotate(-90, 10, ${height / 2})`} className="text-[10px] fill-white/40 font-mono">Actual</text>
    </svg>
  );
}

interface SensitivityCurveChartProps {
  thresholds: number[];
  probabilities: number[];
  currentThreshold: number;
}

function SensitivityCurveChart({ thresholds, probabilities, currentThreshold }: SensitivityCurveChartProps) {
  const width = 200;
  const height = 150;
  const padding = 30;
  const plotWidth = width - 2 * padding;
  const plotHeight = height - 2 * padding;

  const minT = Math.min(...thresholds);
  const maxT = Math.max(...thresholds);
  const range = maxT - minT || 1;

  const points = thresholds.map((t, i) => ({
    x: padding + ((t - minT) / range) * plotWidth,
    y: height - padding - probabilities[i] * plotHeight,
  }));

  const currentX = padding + ((currentThreshold - minT) / range) * plotWidth;

  return (
    <svg width={width} height={height} className="mx-auto">
      {/* Grid */}
      <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="rgba(255,255,255,0.1)" />
      <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="rgba(255,255,255,0.1)" />

      {/* Sensitivity curve */}
      {points.length > 1 && (
        <polyline
          points={points.map(p => `${p.x},${p.y}`).join(' ')}
          fill="none"
          stroke="#A855F7"
          strokeWidth={2}
        />
      )}

      {/* Current threshold line */}
      <line
        x1={currentX}
        y1={padding}
        x2={currentX}
        y2={height - padding}
        stroke="#00FFFF"
        strokeWidth={1}
        strokeDasharray="4 4"
      />

      {/* Labels */}
      <text x={width / 2} y={height - 5} textAnchor="middle" className="text-[10px] fill-white/40 font-mono">Threshold</text>
      <text x={10} y={height / 2} textAnchor="middle" transform={`rotate(-90, 10, ${height / 2})`} className="text-[10px] fill-white/40 font-mono">P(target)</text>
    </svg>
  );
}

function getDriftStatusColor(status: ReportDriftStatus): string {
  switch (status) {
    case 'stable': return 'text-green-400';
    case 'warning': return 'text-yellow-400';
    case 'drifting': return 'text-red-400';
    default: return 'text-white/40';
  }
}

function getDriftStatusBg(status: ReportDriftStatus): string {
  switch (status) {
    case 'stable': return 'border-green-500/20 bg-green-500/5';
    case 'warning': return 'border-yellow-500/20 bg-yellow-500/5';
    case 'drifting': return 'border-red-500/20 bg-red-500/5';
    default: return 'border-white/10 bg-white/5';
  }
}

interface PredictionReportProps {
  projectId: string;
  nodeId: string;
  params: ReportQueryParams;
  onExportJSON: () => void;
  onCopyLink: () => void;
  linkCopied: boolean;
}

function PredictionReport({
  projectId,
  nodeId,
  params,
  onExportJSON,
  onCopyLink,
  linkCopied,
}: PredictionReportProps) {
  const { data: report, isLoading, isError, error } = useNodeReport(nodeId, params);
  const { data: node } = useNode(nodeId);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-12">
        <Loader2 className="w-8 h-8 animate-spin text-cyan-400" />
        <span className="ml-3 text-sm font-mono text-white/60">Generating report...</span>
      </div>
    );
  }

  if (isError || !report) {
    return (
      <div className="border border-red-500/20 bg-red-500/5 p-8 text-center">
        <XCircle className="w-12 h-12 mx-auto text-red-400/40 mb-4" />
        <h2 className="text-lg font-mono font-bold text-white mb-2">Report Generation Failed</h2>
        <p className="text-sm font-mono text-white/50">
          {error instanceof Error ? error.message : 'Unable to generate prediction report.'}
        </p>
      </div>
    );
  }

  // Check for insufficient data
  if (report.insufficient_data) {
    return (
      <div className="space-y-6">
        <div className="border border-yellow-500/20 bg-yellow-500/5 p-6">
          <div className="flex items-start gap-4">
            <AlertTriangle className="w-8 h-8 text-yellow-400 flex-shrink-0" />
            <div>
              <h3 className="text-lg font-mono font-bold text-white mb-2">Insufficient Data</h3>
              <p className="text-sm font-mono text-white/60 mb-4">
                Not enough simulation runs to generate a reliable prediction report.
                Current: {report.provenance.n_runs} runs, Required: {report.provenance.filters.min_runs} minimum.
              </p>
              <Link href={`/p/${projectId}/run-center?node=${nodeId}`}>
                <Button variant="outline" size="sm" className="text-xs">
                  <Play className="w-3 h-3 mr-1" /> Run More Simulations
                </Button>
              </Link>
            </div>
          </div>
        </div>
        {report.errors.length > 0 && (
          <div className="border border-red-500/20 bg-red-500/5 p-4">
            <h4 className="text-sm font-mono font-bold text-red-400 mb-2">Errors</h4>
            <ul className="text-xs font-mono text-white/60 space-y-1">
              {report.errors.map((err, i) => (
                <li key={i}>• {err}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  }

  const opSymbol = { ge: '≥', gt: '>', le: '≤', lt: '<', eq: '=' }[report.target.op] || report.target.op;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border border-white/10 bg-white/5 p-4">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Target className="w-5 h-5 text-orange-400" />
              <h2 className="text-lg font-mono font-bold text-white">Prediction Report</h2>
            </div>
            <div className="text-sm font-mono text-white/60">
              <span className="text-cyan-400">{report.metric_key}</span>
              <span className="mx-2">{opSymbol}</span>
              <span className="text-orange-400">{report.target.threshold}</span>
              <span className="mx-2">•</span>
              <span>Node: {node?.label || nodeId.slice(0, 8)}</span>
            </div>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={onCopyLink} className="text-xs">
              {linkCopied ? <Check className="w-3 h-3 mr-1" /> : <Copy className="w-3 h-3 mr-1" />}
              {linkCopied ? 'Copied!' : 'Copy Link'}
            </Button>
            <Button variant="outline" size="sm" onClick={onExportJSON} className="text-xs">
              <Download className="w-3 h-3 mr-1" /> Export JSON
            </Button>
          </div>
        </div>
      </div>

      {/* Target Probability - Hero Metric */}
      <div className="border border-cyan-500/30 bg-cyan-500/5 p-6">
        <h3 className="text-sm font-mono font-bold text-white/60 uppercase mb-4">Target Probability</h3>
        <div className="flex items-center gap-8">
          <div className="text-center">
            <div className="text-5xl font-mono font-bold text-cyan-400">
              {(report.prediction.target_probability * 100).toFixed(1)}%
            </div>
            <div className="text-xs font-mono text-white/40 mt-2">
              P({report.metric_key} {opSymbol} {report.target.threshold})
            </div>
          </div>
          <div className="flex-1 border-l border-white/10 pl-6">
            <div className="text-xs font-mono text-white/40 uppercase mb-2">Distribution</div>
            <DistributionHistogram
              bins={report.prediction.distribution.bins}
              counts={report.prediction.distribution.counts}
              threshold={report.target.threshold}
              op={report.target.op}
            />
            <div className="flex justify-between text-[10px] font-mono text-white/30 mt-1 px-2">
              <span>{report.prediction.distribution.min.toFixed(2)}</span>
              <span>{report.prediction.distribution.max.toFixed(2)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Reliability Section */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Sensitivity */}
        <div className="border border-purple-500/20 bg-purple-500/5 p-4">
          <h3 className="text-sm font-mono font-bold text-purple-400 uppercase mb-3 flex items-center gap-2">
            <Activity className="w-4 h-4" /> Sensitivity
          </h3>
          <SensitivityCurveChart
            thresholds={report.reliability.sensitivity.thresholds}
            probabilities={report.reliability.sensitivity.probabilities}
            currentThreshold={report.target.threshold}
          />
          <div className="text-[10px] font-mono text-white/40 mt-2 text-center">
            How probability changes with threshold
          </div>
        </div>

        {/* Stability */}
        <div className="border border-white/10 bg-white/5 p-4">
          <h3 className="text-sm font-mono font-bold text-white/60 uppercase mb-3 flex items-center gap-2">
            <BarChart3 className="w-4 h-4" /> Stability
          </h3>
          <div className="space-y-3">
            <div className="text-center">
              <div className="text-3xl font-mono font-bold text-white">
                {(report.reliability.stability.mean * 100).toFixed(1)}%
              </div>
              <div className="text-xs font-mono text-white/40">Mean Probability</div>
            </div>
            <div className="flex justify-center items-center gap-2">
              <div className="text-sm font-mono text-white/60">
                [{(report.reliability.stability.ci_low * 100).toFixed(1)}% - {(report.reliability.stability.ci_high * 100).toFixed(1)}%]
              </div>
            </div>
            <div className="text-[10px] font-mono text-white/30 text-center">
              95% CI from {report.reliability.stability.bootstrap_samples} bootstrap samples
            </div>
          </div>
        </div>

        {/* Drift */}
        <div className={cn('border p-4', getDriftStatusBg(report.reliability.drift.status))}>
          <h3 className="text-sm font-mono font-bold text-white/60 uppercase mb-3 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" /> Drift Status
          </h3>
          <div className="text-center">
            <div className={cn('text-2xl font-mono font-bold uppercase', getDriftStatusColor(report.reliability.drift.status))}>
              {report.reliability.drift.status}
            </div>
            <div className="mt-3 space-y-1">
              {report.reliability.drift.ks != null && (
                <div className="text-xs font-mono text-white/60">
                  KS Statistic: <span className="text-white">{report.reliability.drift.ks.toFixed(4)}</span>
                </div>
              )}
              {report.reliability.drift.psi != null && (
                <div className="text-xs font-mono text-white/60">
                  PSI: <span className="text-white">{report.reliability.drift.psi.toFixed(4)}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Calibration Section */}
      <div className="border border-white/10 bg-white/5 p-4">
        <h3 className="text-sm font-mono font-bold text-white/60 uppercase mb-4 flex items-center gap-2">
          <Target className="w-4 h-4" /> Calibration
        </h3>
        {report.calibration.available ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex flex-col items-center">
              <CalibrationCurveChart
                pPred={report.calibration.curve?.p_pred || []}
                pTrue={report.calibration.curve?.p_true || []}
                counts={report.calibration.curve?.counts || []}
              />
              <div className="text-[10px] font-mono text-white/40 mt-2">Calibration Curve</div>
            </div>
            <div className="flex flex-col items-center justify-center p-4 border border-white/10 bg-white/5">
              <div className="text-xs font-mono text-white/40 uppercase">Brier Score</div>
              <div className="text-3xl font-mono font-bold text-cyan-400">
                {report.calibration.brier?.toFixed(4) ?? 'N/A'}
              </div>
              <div className="text-[10px] font-mono text-white/30 mt-1">Lower is better (0-1)</div>
            </div>
            <div className="flex flex-col items-center justify-center p-4 border border-white/10 bg-white/5">
              <div className="text-xs font-mono text-white/40 uppercase">ECE</div>
              <div className="text-3xl font-mono font-bold text-cyan-400">
                {report.calibration.ece?.toFixed(4) ?? 'N/A'}
              </div>
              <div className="text-[10px] font-mono text-white/30 mt-1">Expected Calibration Error</div>
            </div>
          </div>
        ) : (
          <div className="text-center p-6 border border-white/10 bg-white/5">
            <Info className="w-8 h-8 mx-auto text-white/30 mb-2" />
            <p className="text-sm font-mono text-white/50">Calibration data not available</p>
            <p className="text-[10px] font-mono text-white/30 mt-1">Run calibration job to compute Brier/ECE metrics</p>
            <Link href={`/p/${projectId}/calibration?node=${nodeId}`}>
              <Button variant="outline" size="sm" className="mt-3 text-xs">
                Go to Calibration
              </Button>
            </Link>
          </div>
        )}
      </div>

      {/* Provenance Panel */}
      <div className="border border-white/10 bg-white/5 p-4">
        <h3 className="text-sm font-mono font-bold text-white/60 uppercase mb-4 flex items-center gap-2">
          <Database className="w-4 h-4" /> Provenance
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <div className="text-[10px] font-mono text-white/40 uppercase">Runs Analyzed</div>
            <div className="text-lg font-mono font-bold text-white">{report.provenance.n_runs}</div>
          </div>
          <div>
            <div className="text-[10px] font-mono text-white/40 uppercase">Window</div>
            <div className="text-lg font-mono font-bold text-white">{report.provenance.filters.window_days} days</div>
          </div>
          <div>
            <div className="text-[10px] font-mono text-white/40 uppercase">Min Runs</div>
            <div className="text-lg font-mono font-bold text-white">{report.provenance.filters.min_runs}</div>
          </div>
          <div>
            <div className="text-[10px] font-mono text-white/40 uppercase">Updated</div>
            <div className="text-sm font-mono text-white">{new Date(report.provenance.updated_at).toLocaleString()}</div>
          </div>
        </div>
        {report.provenance.manifest_hash && (
          <div className="mt-3 pt-3 border-t border-white/10">
            <div className="text-[10px] font-mono text-white/40 uppercase">Manifest Hash</div>
            <div className="text-xs font-mono text-cyan-400 truncate">{report.provenance.manifest_hash}</div>
          </div>
        )}
      </div>

      {/* Errors (if any) */}
      {report.errors.length > 0 && (
        <div className="border border-yellow-500/20 bg-yellow-500/5 p-4">
          <h4 className="text-sm font-mono font-bold text-yellow-400 mb-2 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" /> Warnings
          </h4>
          <ul className="text-xs font-mono text-white/60 space-y-1">
            {report.errors.map((err, i) => (
              <li key={i}>• {err}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Quick Navigation */}
      <div className="border border-white/10 bg-white/5 p-4">
        <h3 className="text-sm font-mono font-bold text-white/60 uppercase mb-4">Quick Navigation</h3>
        <div className="flex flex-wrap gap-2">
          <Link href={`/p/${projectId}/universe-map?node=${nodeId}`}>
            <Button variant="outline" size="sm" className="text-xs"><GitBranch className="w-3 h-3 mr-1" /> Universe Map</Button>
          </Link>
          <Link href={`/p/${projectId}/reliability?node=${nodeId}`}>
            <Button variant="outline" size="sm" className="text-xs"><Activity className="w-3 h-3 mr-1" /> Reliability</Button>
          </Link>
          <Link href={`/p/${projectId}/calibration?node=${nodeId}`}>
            <Button variant="outline" size="sm" className="text-xs"><Target className="w-3 h-3 mr-1" /> Calibration</Button>
          </Link>
          <Link href={`/p/${projectId}/run-center?node=${nodeId}`}>
            <Button variant="outline" size="sm" className="text-xs"><Zap className="w-3 h-3 mr-1" /> Run Center</Button>
          </Link>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Main Page Component
// ============================================================================

export default function ReportsPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const projectId = params.projectId as string;

  // Get initial values from URL
  const initialRunId = searchParams.get('run');
  const initialNodeId = searchParams.get('node');

  // Determine initial report type based on URL params
  const mvpMode = isMvpMode();
  const getInitialType = (): ReportType => {
    // In MVP mode, always default to MVP report
    if (mvpMode) return 'mvp';
    const typeParam = searchParams.get('type');
    if (typeParam === 'prediction') return 'prediction';
    if (initialRunId) return 'run';
    if (initialNodeId) return 'node';
    return 'project';
  };

  // State
  const [reportType, setReportType] = useState<ReportType>(getInitialType());
  const [selectedRunId, setSelectedRunId] = useState<string | null>(initialRunId);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(initialNodeId);
  const [linkCopied, setLinkCopied] = useState(false);

  // Phase 7: Prediction Report parameters
  const [predMetricKey, setPredMetricKey] = useState<string>(searchParams.get('metric') || 'revenue');
  const [predOp, setPredOp] = useState<ReportOperator>((searchParams.get('op') as ReportOperator) || 'ge');
  const [predThreshold, setPredThreshold] = useState<number>(parseFloat(searchParams.get('threshold') || '100'));
  const [predWindowDays, setPredWindowDays] = useState<number>(parseInt(searchParams.get('window') || '30'));
  const [predMinRuns, setPredMinRuns] = useState<number>(parseInt(searchParams.get('min_runs') || '3'));

  // Build prediction report query params
  const predictionParams: ReportQueryParams | undefined = useMemo(() => {
    if (!predMetricKey || !predOp || predThreshold === undefined) return undefined;
    return {
      metric_key: predMetricKey,
      op: predOp,
      threshold: predThreshold,
      window_days: predWindowDays,
      min_runs: predMinRuns,
    };
  }, [predMetricKey, predOp, predThreshold, predWindowDays, predMinRuns]);

  // Fetch data for pickers
  const { data: nodes, isLoading: nodesLoading } = useNodes({ project_id: projectId });
  const { data: runs, isLoading: runsLoading } = useRuns({
    project_id: projectId,
    node_id: selectedNodeId || undefined,
    status: 'succeeded' as SpecRunStatus,
    limit: 50,
  });

  // Handle report type change
  const handleReportTypeChange = (type: ReportType) => {
    setReportType(type);
    if (type === 'project') {
      setSelectedRunId(null);
      setSelectedNodeId(null);
      router.push(`/p/${projectId}/reports`);
    }
  };

  // Handle node selection
  const handleNodeSelect = (nodeId: string) => {
    setSelectedNodeId(nodeId);
    setSelectedRunId(null);
    if (reportType === 'node') {
      router.push(`/p/${projectId}/reports?node=${nodeId}`);
    } else if (reportType === 'prediction') {
      // Deep-link for prediction reports
      const params = new URLSearchParams();
      params.set('type', 'prediction');
      params.set('node', nodeId);
      params.set('metric', predMetricKey);
      params.set('op', predOp);
      params.set('threshold', String(predThreshold));
      params.set('window', String(predWindowDays));
      params.set('min_runs', String(predMinRuns));
      router.push(`/p/${projectId}/reports?${params.toString()}`);
    }
  };

  // Update URL when prediction params change
  const updatePredictionUrl = useCallback(() => {
    if (reportType !== 'prediction' || !selectedNodeId) return;
    const params = new URLSearchParams();
    params.set('type', 'prediction');
    params.set('node', selectedNodeId);
    params.set('metric', predMetricKey);
    params.set('op', predOp);
    params.set('threshold', String(predThreshold));
    params.set('window', String(predWindowDays));
    params.set('min_runs', String(predMinRuns));
    router.replace(`/p/${projectId}/reports?${params.toString()}`);
  }, [reportType, selectedNodeId, predMetricKey, predOp, predThreshold, predWindowDays, predMinRuns, projectId, router]);

  // Handle run selection
  const handleRunSelect = (runId: string) => {
    setSelectedRunId(runId);
    router.push(`/p/${projectId}/reports?run=${runId}`);
  };

  // Copy link handler
  const handleCopyLink = useCallback(() => {
    const url = window.location.href;
    navigator.clipboard.writeText(url);
    setLinkCopied(true);
    setTimeout(() => setLinkCopied(false), 2000);
  }, []);

  // Export handlers - accept optional ExportData for custom reports (like MvpReport)
  const handleExportJSON = useCallback((customData?: ExportData) => {
    const data: ExportData = customData || {
      reportType,
      generatedAt: new Date().toISOString(),
      projectId,
      data: {
        selectedNodeId,
        selectedRunId,
      },
    };
    const filename = `agentverse-${data.reportType}-report-${Date.now()}`;
    exportToJSON(data, filename);
  }, [reportType, projectId, selectedNodeId, selectedRunId]);

  const handleExportMarkdown = useCallback((customData?: ExportData) => {
    const data: ExportData = customData || {
      reportType,
      generatedAt: new Date().toISOString(),
      projectId,
      data: {
        selectedNodeId,
        selectedRunId,
      },
    };
    const filename = `agentverse-${data.reportType}-report-${Date.now()}`;
    exportToMarkdown(data, filename);
  }, [reportType, projectId, selectedNodeId, selectedRunId]);

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
          <FileBarChart className="w-3.5 h-3.5 md:w-4 md:h-4 text-cyan-400" />
          <span className="text-[10px] md:text-xs font-mono text-white/40 uppercase tracking-wider">Reports</span>
        </div>
        <h1 className="text-lg md:text-xl font-mono font-bold text-white">Reports</h1>
        <p className="text-xs md:text-sm font-mono text-white/50 mt-1">
          Generate comprehensive reports for runs, nodes, projects, and predictions
        </p>
      </div>

      {/* Report Type Selector */}
      <div className="max-w-6xl mb-6">
        <div className="text-[10px] font-mono text-white/40 uppercase mb-2">Report Type</div>
        <ReportTypeSelector value={reportType} onChange={handleReportTypeChange} />
      </div>

      {/* Context Selectors (for node, run, and prediction reports) */}
      {(reportType === 'node' || reportType === 'run' || reportType === 'prediction') && (
        <div className="max-w-6xl mb-6">
          <div className="flex flex-wrap items-end gap-4">
            <div>
              <div className="text-[10px] font-mono text-white/40 uppercase mb-1">Node</div>
              <NodePicker nodes={nodes} selectedNodeId={selectedNodeId} onSelect={handleNodeSelect} loading={nodesLoading} />
            </div>
            {reportType === 'run' && (
              <div>
                <div className="text-[10px] font-mono text-white/40 uppercase mb-1">Run</div>
                <RunPicker runs={runs} selectedRunId={selectedRunId} onSelect={handleRunSelect} loading={runsLoading} />
              </div>
            )}
          </div>
          {/* Prediction Report Parameters */}
          {reportType === 'prediction' && selectedNodeId && (
            <div className="mt-4 p-4 border border-orange-500/20 bg-orange-500/5">
              <div className="text-[10px] font-mono text-orange-400 uppercase mb-3">Target Configuration</div>
              <PredictionReportParams
                metricKey={predMetricKey}
                setMetricKey={setPredMetricKey}
                op={predOp}
                setOp={setPredOp}
                threshold={predThreshold}
                setThreshold={setPredThreshold}
                windowDays={predWindowDays}
                setWindowDays={setPredWindowDays}
                minRuns={predMinRuns}
                setMinRuns={setPredMinRuns}
              />
              <div className="mt-3 flex justify-end">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={updatePredictionUrl}
                  className="text-xs border-orange-500/30 hover:bg-orange-500/10"
                >
                  <Target className="w-3 h-3 mr-1" /> Update Report
                </Button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Report Content */}
      <div className="max-w-6xl">
        {/* Project Overview Report */}
        {reportType === 'project' && (
          <ProjectOverviewReport
            projectId={projectId}
            onExportJSON={handleExportJSON}
            onExportMarkdown={handleExportMarkdown}
            onCopyLink={handleCopyLink}
            linkCopied={linkCopied}
          />
        )}

        {/* Node Summary Report */}
        {reportType === 'node' && !selectedNodeId && (
          <div className="border border-yellow-500/20 bg-yellow-500/5 p-8 text-center">
            <GitBranch className="w-12 h-12 mx-auto text-yellow-400/40 mb-4" />
            <h2 className="text-lg font-mono font-bold text-white mb-2">Select a Node</h2>
            <p className="text-sm font-mono text-white/50">Choose a node from the picker above to generate a summary report.</p>
          </div>
        )}

        {reportType === 'node' && selectedNodeId && (
          <NodeSummaryReport
            projectId={projectId}
            nodeId={selectedNodeId}
            onExportJSON={handleExportJSON}
            onExportMarkdown={handleExportMarkdown}
            onCopyLink={handleCopyLink}
            linkCopied={linkCopied}
          />
        )}

        {/* Run Report */}
        {reportType === 'run' && !selectedRunId && (
          <div className="border border-yellow-500/20 bg-yellow-500/5 p-8 text-center">
            <Play className="w-12 h-12 mx-auto text-yellow-400/40 mb-4" />
            <h2 className="text-lg font-mono font-bold text-white mb-2">Select a Run</h2>
            <p className="text-sm font-mono text-white/50">
              {hasNoRuns
                ? 'No completed runs available. Run a simulation first.'
                : 'Choose a run from the picker above to generate a detailed report.'}
            </p>
            {hasNoRuns && (
              <Link href={`/p/${projectId}/run-center`}>
                <Button variant="outline" size="sm" className="mt-4 text-xs">
                  <Play className="w-3 h-3 mr-1" /> Go to Run Center
                </Button>
              </Link>
            )}
          </div>
        )}

        {reportType === 'run' && selectedRunId && (
          <RunReport
            projectId={projectId}
            runId={selectedRunId}
            runs={runs}
            onExportJSON={handleExportJSON}
            onExportMarkdown={handleExportMarkdown}
            onCopyLink={handleCopyLink}
            linkCopied={linkCopied}
          />
        )}

        {/* Phase 7: Prediction Report */}
        {reportType === 'prediction' && !selectedNodeId && (
          <div className="border border-yellow-500/20 bg-yellow-500/5 p-8 text-center">
            <Target className="w-12 h-12 mx-auto text-yellow-400/40 mb-4" />
            <h2 className="text-lg font-mono font-bold text-white mb-2">Select a Node</h2>
            <p className="text-sm font-mono text-white/50">Choose a node from the picker above to generate a prediction report.</p>
          </div>
        )}

        {reportType === 'prediction' && selectedNodeId && predictionParams && (
          <PredictionReport
            projectId={projectId}
            nodeId={selectedNodeId}
            params={predictionParams}
            onExportJSON={handleExportJSON}
            onCopyLink={handleCopyLink}
            linkCopied={linkCopied}
          />
        )}

        {/* MVP Report - Demo2 simplified export */}
        {reportType === 'mvp' && (
          <MvpReport
            projectId={projectId}
            onExportJSON={handleExportJSON}
            onExportMarkdown={handleExportMarkdown}
            onCopyLink={handleCopyLink}
            linkCopied={linkCopied}
          />
        )}

        {/* Guidance Panel - Blueprint-driven guidance for reports section (blueprint.md §7) */}
        {!mvpMode && (
          <div className="mt-6">
            <GuidancePanel
              projectId={projectId}
              sectionId="reports"
              className="mb-6"
            />
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="mt-8 pt-4 border-t border-white/5 max-w-6xl">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-1">
            <FileBarChart className="w-3 h-3" />
            <span>REPORTS • {reportType.toUpperCase()}</span>
          </div>
          <span>AGENTVERSE v1.0</span>
        </div>
      </div>
    </div>
  );
}

'use client';

/**
 * Run Audit Report Page
 * Displays temporal isolation audit report with PASS/FAIL indicator
 * Reference: temporal.md §8 Phase 5
 */

import { useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import {
  ArrowLeft,
  Loader2,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Shield,
  Clock,
  Database,
  FileText,
  Hash,
  GitBranch,
  Download,
  ChevronDown,
  ChevronUp,
  Activity,
  Terminal,
  Layers,
  AlertCircle,
  Globe,
  Lock,
} from 'lucide-react';
import { useRunAuditReport, useRun } from '@/hooks/useApi';
import { cn } from '@/lib/utils';
import type { SourceAccessEntry, IsolationViolation } from '@/lib/api';

// =============================================================================
// Utility Components
// =============================================================================

function IsolationBadge({ status, score }: { status: 'PASS' | 'FAIL'; score: number }) {
  const isPassing = status === 'PASS';

  return (
    <div className={cn(
      "flex items-center gap-3 p-4 border",
      isPassing
        ? "bg-green-500/10 border-green-500/30"
        : "bg-red-500/10 border-red-500/30"
    )}>
      <div className={cn(
        "w-12 h-12 flex items-center justify-center",
        isPassing ? "bg-green-500/20" : "bg-red-500/20"
      )}>
        {isPassing ? (
          <CheckCircle className="w-6 h-6 text-green-400" />
        ) : (
          <XCircle className="w-6 h-6 text-red-400" />
        )}
      </div>
      <div>
        <div className={cn(
          "text-xl font-mono font-bold",
          isPassing ? "text-green-400" : "text-red-400"
        )}>
          {status}
        </div>
        <div className="text-xs font-mono text-white/50">
          Compliance Score: {(score * 100).toFixed(1)}%
        </div>
      </div>
    </div>
  );
}

function ViolationCard({ violation }: { violation: IsolationViolation }) {
  const severityColors = {
    critical: 'border-red-500/50 bg-red-500/10',
    high: 'border-orange-500/50 bg-orange-500/10',
    medium: 'border-yellow-500/50 bg-yellow-500/10',
    low: 'border-white/20 bg-white/5',
  };

  const severityTextColors = {
    critical: 'text-red-400',
    high: 'text-orange-400',
    medium: 'text-yellow-400',
    low: 'text-white/60',
  };

  const severity = violation.severity as keyof typeof severityColors;

  return (
    <div className={cn("border p-4", severityColors[severity] || severityColors.medium)}>
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <AlertTriangle className={cn("w-4 h-4", severityTextColors[severity] || severityTextColors.medium)} />
          <span className={cn("text-xs font-mono font-bold uppercase", severityTextColors[severity] || severityTextColors.medium)}>
            {violation.severity}
          </span>
        </div>
        <span className="text-xs font-mono text-white/40">
          {(violation.confidence * 100).toFixed(0)}% confidence
        </span>
      </div>
      <p className="text-sm font-mono text-white mb-2">{violation.description}</p>
      <div className="text-xs font-mono text-white/50">
        <span className="text-white/30">Type:</span> {violation.violation_type.replace(/_/g, ' ')}
      </div>
      {violation.evidence && (
        <div className="mt-2 p-2 bg-black/30 text-xs font-mono text-white/60 overflow-x-auto">
          {violation.evidence}
        </div>
      )}
      {violation.line_number && (
        <div className="mt-1 text-[10px] font-mono text-white/30">
          Line {violation.line_number}
        </div>
      )}
    </div>
  );
}

function SourceAccessTable({ entries }: { entries: SourceAccessEntry[] }) {
  const [expanded, setExpanded] = useState<Record<number, boolean>>({});

  if (!entries.length) {
    return (
      <div className="text-center py-8">
        <Database className="w-8 h-8 text-white/20 mx-auto mb-2" />
        <p className="text-xs font-mono text-white/40">No data sources accessed</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {entries.map((entry, idx) => (
        <div key={idx} className="border border-white/10 bg-white/5">
          <button
            onClick={() => setExpanded(prev => ({ ...prev, [idx]: !prev[idx] }))}
            className="w-full p-3 flex items-center justify-between hover:bg-white/[0.02] transition-colors"
          >
            <div className="flex items-center gap-3">
              <Database className="w-4 h-4 text-cyan-400" />
              <span className="text-sm font-mono text-white font-bold">
                {entry.source_name}
              </span>
              <span className="text-xs font-mono text-white/40">
                {entry.record_count} records
              </span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs font-mono text-white/30">
                {entry.response_time_ms}ms
              </span>
              {expanded[idx] ? (
                <ChevronUp className="w-4 h-4 text-white/40" />
              ) : (
                <ChevronDown className="w-4 h-4 text-white/40" />
              )}
            </div>
          </button>

          {expanded[idx] && (
            <div className="px-3 pb-3 space-y-2 border-t border-white/10 pt-3">
              <div className="grid grid-cols-2 gap-4 text-xs font-mono">
                <div>
                  <span className="text-white/40">Endpoint</span>
                  <p className="text-white/70 truncate">{entry.endpoint}</p>
                </div>
                <div>
                  <span className="text-white/40">Filtered</span>
                  <p className="text-white/70">{entry.filtered_count} records</p>
                </div>
              </div>

              {entry.time_window && (
                <div className="text-xs font-mono">
                  <span className="text-white/40">Time Window</span>
                  <p className="text-white/70">
                    {JSON.stringify(entry.time_window)}
                  </p>
                </div>
              )}

              <div className="flex items-center gap-2 text-xs font-mono">
                <Hash className="w-3 h-3 text-white/40" />
                <span className="text-white/40">Payload Hash:</span>
                <code className="text-cyan-400/70 truncate flex-1">
                  {entry.payload_hash}
                </code>
              </div>

              <div className="text-[10px] font-mono text-white/30">
                Accessed: {new Date(entry.timestamp).toLocaleString()}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// =============================================================================
// Main Page Component
// =============================================================================

export default function RunAuditReportPage() {
  const params = useParams();
  const router = useRouter();
  const runId = params.id as string;

  const { data: auditReport, isLoading, error } = useRunAuditReport(runId);
  const { data: run } = useRun(runId);

  const [showHashes, setShowHashes] = useState(false);

  const handleExport = async () => {
    if (!auditReport) return;

    // Download as JSON
    const blob = new Blob([JSON.stringify(auditReport, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `audit_report_${runId}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-cyan-400" />
      </div>
    );
  }

  if (error || !auditReport) {
    return (
      <div className="min-h-screen bg-black p-6">
        <div className="bg-red-500/10 border border-red-500/30 p-6 max-w-md mx-auto mt-12">
          <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-4" />
          <p className="text-sm font-mono text-red-400 text-center mb-4">
            Failed to load audit report
          </p>
          <div className="flex justify-center gap-2">
            <Button variant="secondary" size="sm" onClick={() => router.back()}>
              GO BACK
            </Button>
          </div>
        </div>
      </div>
    );
  }

  const isolationLevel = auditReport.temporal_context.isolation_level;
  const isolationLevelLabels: Record<number, string> = {
    1: 'Basic',
    2: 'Strict',
    3: 'Audit-First',
  };

  return (
    <div className="min-h-screen bg-black p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <Link
            href={`/dashboard/runs/${runId}`}
            className="flex items-center gap-1 text-xs font-mono text-white/40 hover:text-white mb-2"
          >
            <ArrowLeft className="w-3 h-3" />
            Back to Run
          </Link>
          <div className="flex items-center gap-3">
            <div className="p-2 border border-white/10 bg-white/5">
              <Shield className="w-5 h-5 text-purple-400" />
            </div>
            <div>
              <h1 className="text-xl font-mono font-bold text-white">
                Temporal Audit Report
              </h1>
              <p className="text-xs font-mono text-white/40">
                Run {runId.slice(0, 16)}...
              </p>
            </div>
          </div>
        </div>
        <Button variant="secondary" size="sm" onClick={handleExport}>
          <Download className="w-3 h-3 mr-2" />
          EXPORT JSON
        </Button>
      </div>

      {/* Isolation Status */}
      <div className="mb-6">
        <IsolationBadge
          status={auditReport.isolation_status}
          score={auditReport.compliance_score}
        />
      </div>

      {/* Temporal Context */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="w-4 h-4 text-cyan-400" />
            <span className="text-xs font-mono text-white/40 uppercase">Mode</span>
          </div>
          <p className={cn(
            "text-lg font-mono font-bold uppercase",
            auditReport.temporal_context.mode === 'backtest' ? "text-yellow-400" : "text-green-400"
          )}>
            {auditReport.temporal_context.mode}
          </p>
        </div>

        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-2">
            <Clock className="w-4 h-4 text-purple-400" />
            <span className="text-xs font-mono text-white/40 uppercase">Cutoff</span>
          </div>
          <p className="text-sm font-mono text-white">
            {auditReport.temporal_context.as_of_datetime
              ? new Date(auditReport.temporal_context.as_of_datetime).toLocaleString()
              : 'Live (No Cutoff)'}
          </p>
        </div>

        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-2">
            <Globe className="w-4 h-4 text-blue-400" />
            <span className="text-xs font-mono text-white/40 uppercase">Timezone</span>
          </div>
          <p className="text-sm font-mono text-white">
            {auditReport.temporal_context.timezone}
          </p>
        </div>

        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-2">
            <Lock className="w-4 h-4 text-orange-400" />
            <span className="text-xs font-mono text-white/40 uppercase">Isolation Level</span>
          </div>
          <p className="text-sm font-mono text-white">
            Level {isolationLevel}: {isolationLevelLabels[isolationLevel] || 'Unknown'}
          </p>
        </div>
      </div>

      {/* Violations */}
      {auditReport.violations.length > 0 && (
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-4">
            <AlertCircle className="w-4 h-4 text-red-400" />
            <h2 className="text-sm font-mono font-bold text-white uppercase">
              Violations ({auditReport.violations.length})
            </h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {auditReport.violations.map((violation, idx) => (
              <ViolationCard key={idx} violation={violation} />
            ))}
          </div>
        </div>
      )}

      {/* Data Manifest Summary */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <div className="lg:col-span-2">
          <div className="flex items-center gap-2 mb-4">
            <Database className="w-4 h-4 text-cyan-400" />
            <h2 className="text-sm font-mono font-bold text-white uppercase">
              Data Sources Accessed
            </h2>
          </div>
          <SourceAccessTable entries={auditReport.sources_accessed} />
        </div>

        <div>
          <div className="flex items-center gap-2 mb-4">
            <Layers className="w-4 h-4 text-purple-400" />
            <h2 className="text-sm font-mono font-bold text-white uppercase">
              Summary
            </h2>
          </div>
          <div className="bg-white/5 border border-white/10 p-4 space-y-3">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-white/50">Total Records</span>
              <span className="text-white font-bold">{auditReport.total_records.toLocaleString()}</span>
            </div>
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-white/50">Filtered Out</span>
              <span className="text-yellow-400">{auditReport.total_filtered.toLocaleString()}</span>
            </div>
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-white/50">Sources Used</span>
              <span className="text-white">{auditReport.sources_accessed.length}</span>
            </div>
            {auditReport.random_seed && (
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-white/50">Random Seed</span>
                <span className="text-cyan-400">{auditReport.random_seed}</span>
              </div>
            )}
          </div>

          {/* Payload Hashes */}
          <div className="mt-4">
            <button
              onClick={() => setShowHashes(!showHashes)}
              className="flex items-center gap-2 text-xs font-mono text-white/50 hover:text-white"
            >
              <Hash className="w-3 h-3" />
              <span>Payload Hashes</span>
              {showHashes ? (
                <ChevronUp className="w-3 h-3" />
              ) : (
                <ChevronDown className="w-3 h-3" />
              )}
            </button>
            {showHashes && (
              <div className="mt-2 bg-white/5 border border-white/10 p-3 space-y-2">
                {Object.entries(auditReport.payload_hashes).map(([source, hash]) => (
                  <div key={source} className="text-[10px] font-mono">
                    <span className="text-white/40">{source}:</span>
                    <code className="text-cyan-400/60 break-all ml-1">{hash}</code>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Version Information */}
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-4">
          <GitBranch className="w-4 h-4 text-white/40" />
          <h2 className="text-sm font-mono font-bold text-white uppercase">
            Version Snapshot
          </h2>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white/5 border border-white/10 p-3">
            <span className="text-[10px] font-mono text-white/40 uppercase">Engine</span>
            <p className="text-sm font-mono text-white">{auditReport.versions.engine_version}</p>
          </div>
          <div className="bg-white/5 border border-white/10 p-3">
            <span className="text-[10px] font-mono text-white/40 uppercase">Ruleset</span>
            <p className="text-sm font-mono text-white">{auditReport.versions.ruleset_version}</p>
          </div>
          <div className="bg-white/5 border border-white/10 p-3">
            <span className="text-[10px] font-mono text-white/40 uppercase">Dataset</span>
            <p className="text-sm font-mono text-white">{auditReport.versions.dataset_version}</p>
          </div>
          <div className="bg-white/5 border border-white/10 p-3">
            <span className="text-[10px] font-mono text-white/40 uppercase">Policy</span>
            <p className="text-sm font-mono text-white">{auditReport.versions.policy_version}</p>
          </div>
        </div>
      </div>

      {/* Timestamps */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-2">
            <Clock className="w-4 h-4 text-white/40" />
            <span className="text-xs font-mono text-white/40">Created</span>
          </div>
          <p className="text-sm font-mono text-white">
            {new Date(auditReport.created_at).toLocaleString()}
          </p>
        </div>
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle className="w-4 h-4 text-white/40" />
            <span className="text-xs font-mono text-white/40">Completed</span>
          </div>
          <p className="text-sm font-mono text-white">
            {auditReport.completed_at
              ? new Date(auditReport.completed_at).toLocaleString()
              : 'In Progress'}
          </p>
        </div>
      </div>

      {/* Related Links */}
      <div className="flex items-center gap-4 mb-6">
        {auditReport.project_id && (
          <Link href={`/dashboard/projects/${auditReport.project_id}`}>
            <Button variant="secondary" size="sm">
              <FileText className="w-3 h-3 mr-2" />
              VIEW PROJECT
            </Button>
          </Link>
        )}
        {auditReport.node_id && (
          <Link href={`/dashboard/nodes/${auditReport.node_id}`}>
            <Button variant="secondary" size="sm">
              <GitBranch className="w-3 h-3 mr-2" />
              VIEW NODE
            </Button>
          </Link>
        )}
        {run && (
          <Link href={`/dashboard/runs/${runId}/telemetry`}>
            <Button variant="secondary" size="sm">
              <Activity className="w-3 h-3 mr-2" />
              VIEW TELEMETRY
            </Button>
          </Link>
        )}
      </div>

      {/* Footer */}
      <div className="mt-8 pt-4 border-t border-white/5">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1">
              <Terminal className="w-3 h-3" />
              <span>TEMPORAL AUDIT REPORT</span>
            </div>
            <div className="flex items-center gap-1">
              <Shield className="w-3 h-3" />
              <span>TEMPORAL.MD §8 PHASE 5</span>
            </div>
          </div>
          <span>AGENTVERSE v1.0.0</span>
        </div>
      </div>
    </div>
  );
}

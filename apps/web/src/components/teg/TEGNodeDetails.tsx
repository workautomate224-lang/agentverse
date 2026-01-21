'use client';

/**
 * TEG Node Details Panel
 *
 * Right-side panel showing selected node details.
 * Reference: docs/TEG_UNIVERSE_MAP_EXECUTION.md Section 2.3
 */

import {
  CheckCircle,
  Clock,
  Activity,
  XCircle,
  Edit3,
  FileText,
  Sparkles,
  GitBranch,
  Play,
  Zap,
  RefreshCw,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  Minus,
  ExternalLink,
  BarChart3,
  Users,
  Link2,
  Loader2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type {
  TEGNodeDetailsProps,
  TEGNode,
  TEGNodeType,
  TEGNodeStatus,
  TEGVerifiedPayload,
  TEGDraftPayload,
  TEGFailedPayload,
  ConfidenceLevel,
} from './types';

const statusConfig: Record<TEGNodeStatus, { icon: typeof CheckCircle; color: string; bg: string; label: string }> = {
  DRAFT: { icon: Edit3, color: 'text-gray-400', bg: 'bg-gray-500/10', label: 'Draft' },
  QUEUED: { icon: Clock, color: 'text-blue-400', bg: 'bg-blue-500/10', label: 'Queued' },
  RUNNING: { icon: Activity, color: 'text-cyan-400', bg: 'bg-cyan-500/10', label: 'Running' },
  DONE: { icon: CheckCircle, color: 'text-green-400', bg: 'bg-green-500/10', label: 'Done' },
  FAILED: { icon: XCircle, color: 'text-red-400', bg: 'bg-red-500/10', label: 'Failed' },
};

const typeConfig: Record<TEGNodeType, { icon: typeof FileText; color: string; label: string }> = {
  OUTCOME_VERIFIED: { icon: CheckCircle, color: 'text-cyan-400', label: 'Verified Outcome' },
  SCENARIO_DRAFT: { icon: Sparkles, color: 'text-purple-400', label: 'Draft Scenario' },
  EVIDENCE: { icon: FileText, color: 'text-amber-400', label: 'Evidence' },
};

const confidenceConfig: Record<ConfidenceLevel, { color: string; bg: string }> = {
  high: { color: 'text-green-400', bg: 'bg-green-500/10' },
  medium: { color: 'text-yellow-400', bg: 'bg-yellow-500/10' },
  low: { color: 'text-red-400', bg: 'bg-red-500/10' },
};

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border-b border-white/10 pb-4 mb-4 last:border-0 last:mb-0 last:pb-0">
      <h4 className="text-[10px] font-mono uppercase text-white/40 mb-3">{title}</h4>
      {children}
    </div>
  );
}

function MetricRow({ label, value, icon: Icon, valueColor }: {
  label: string;
  value: React.ReactNode;
  icon?: typeof TrendingUp;
  valueColor?: string;
}) {
  return (
    <div className="flex items-center justify-between py-1.5">
      <span className="text-xs text-white/50">{label}</span>
      <div className="flex items-center gap-1.5">
        {Icon && <Icon className={cn('w-3 h-3', valueColor || 'text-white/50')} />}
        <span className={cn('text-sm font-mono', valueColor || 'text-white/90')}>{value}</span>
      </div>
    </div>
  );
}

export function TEGNodeDetails({
  node,
  onExpand,
  onRun,
  onEdit,
  onRetry,
  loading,
  baselineNode,
}: TEGNodeDetailsProps) {
  if (!node) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 text-center">
        <GitBranch className="w-12 h-12 text-white/20 mb-4" />
        <h3 className="text-sm font-medium text-white/60 mb-2">No Node Selected</h3>
        <p className="text-xs text-white/40">
          Click on a node in the graph or table to view its details.
        </p>
      </div>
    );
  }

  const status = statusConfig[node.status];
  const type = typeConfig[node.type];
  const StatusIcon = status.icon;
  const TypeIcon = type.icon;

  const isVerified = node.type === 'OUTCOME_VERIFIED';
  const isDraft = node.type === 'SCENARIO_DRAFT';
  const isFailed = node.status === 'FAILED';
  const isRunning = node.status === 'RUNNING' || node.status === 'QUEUED';

  // Type-safe payload access
  const verifiedPayload = isVerified ? (node.payload as TEGVerifiedPayload) : null;
  const draftPayload = isDraft ? (node.payload as TEGDraftPayload) : null;
  const failedPayload = isFailed ? (node.payload as TEGFailedPayload) : null;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-white/10">
        <div className="flex items-start justify-between gap-3 mb-3">
          <h3 className="text-base font-medium text-white/90 line-clamp-2">{node.title}</h3>
          <div className={cn('flex items-center gap-1 px-2 py-0.5 text-[10px] font-mono shrink-0', status.bg, status.color)}>
            <StatusIcon className="w-3 h-3" />
            {status.label}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className={cn('flex items-center gap-1 px-2 py-0.5 text-[10px] font-mono', type.color)}>
            <TypeIcon className="w-3 h-3" />
            {type.label}
          </div>
          <span className="text-[10px] text-white/30">|</span>
          <span className="text-[10px] text-white/40 font-mono">
            {new Date(node.created_at).toLocaleString()}
          </span>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {loading ? (
          <div className="flex items-center justify-center h-40">
            <Loader2 className="w-6 h-6 text-cyan-500 animate-spin" />
          </div>
        ) : (
          <>
            {/* Summary */}
            {node.summary && (
              <Section title="Summary">
                <p className="text-sm text-white/70">{node.summary}</p>
              </Section>
            )}

            {/* Verified Outcome Details */}
            {isVerified && verifiedPayload && (
              <>
                <Section title="Outcome">
                  {verifiedPayload.primary_outcome_probability !== undefined && (
                    <MetricRow
                      label="Probability"
                      value={`${(verifiedPayload.primary_outcome_probability * 100).toFixed(1)}%`}
                      valueColor="text-cyan-400"
                    />
                  )}
                  {verifiedPayload.actual_delta !== undefined && (
                    <MetricRow
                      label="Delta vs Parent"
                      value={`${verifiedPayload.actual_delta > 0 ? '+' : ''}${(verifiedPayload.actual_delta * 100).toFixed(1)}%`}
                      icon={verifiedPayload.actual_delta > 0 ? TrendingUp : verifiedPayload.actual_delta < 0 ? TrendingDown : Minus}
                      valueColor={verifiedPayload.actual_delta > 0 ? 'text-green-400' : verifiedPayload.actual_delta < 0 ? 'text-red-400' : 'text-white/50'}
                    />
                  )}
                  {verifiedPayload.uncertainty !== undefined && (
                    <MetricRow
                      label="Uncertainty"
                      value={`\u00B1${(verifiedPayload.uncertainty * 100).toFixed(1)}%`}
                      valueColor="text-amber-400"
                    />
                  )}
                </Section>

                {verifiedPayload.top_drivers && verifiedPayload.top_drivers.length > 0 && (
                  <Section title="Top Drivers">
                    <div className="space-y-2">
                      {verifiedPayload.top_drivers.slice(0, 5).map((driver, i) => (
                        <div key={i} className="flex items-center justify-between text-xs">
                          <span className="text-white/70">{driver.name}</span>
                          <span className={cn(
                            'font-mono',
                            driver.direction === 'positive' ? 'text-green-400' : 'text-red-400'
                          )}>
                            {driver.direction === 'positive' ? '+' : ''}{(driver.impact * 100).toFixed(0)}%
                          </span>
                        </div>
                      ))}
                    </div>
                  </Section>
                )}

                {verifiedPayload.persona_segment_shifts && verifiedPayload.persona_segment_shifts.length > 0 && (
                  <Section title="Persona Segment Shifts">
                    <div className="space-y-2">
                      {verifiedPayload.persona_segment_shifts.slice(0, 3).map((segment, i) => (
                        <div key={i} className="flex items-center justify-between text-xs">
                          <span className="text-white/70 flex items-center gap-1">
                            <Users className="w-3 h-3" />
                            {segment.segment}
                          </span>
                          <span className={cn(
                            'font-mono',
                            segment.shift > 0 ? 'text-green-400' : segment.shift < 0 ? 'text-red-400' : 'text-white/50'
                          )}>
                            {segment.shift > 0 ? '+' : ''}{(segment.shift * 100).toFixed(0)}%
                          </span>
                        </div>
                      ))}
                    </div>
                  </Section>
                )}

                {/* Manifest Links */}
                {(verifiedPayload.run_id || verifiedPayload.run_manifest_link) && (
                  <Section title="Audit Trail">
                    {verifiedPayload.run_id && (
                      <div className="flex items-center gap-2 text-xs mb-2">
                        <span className="text-white/40">Run ID:</span>
                        <code className="text-cyan-400 font-mono">{verifiedPayload.run_id.slice(0, 8)}...</code>
                      </div>
                    )}
                    {verifiedPayload.persona_set_version && (
                      <div className="flex items-center gap-2 text-xs mb-2">
                        <span className="text-white/40">Persona Version:</span>
                        <code className="text-cyan-400 font-mono">{verifiedPayload.persona_set_version}</code>
                      </div>
                    )}
                    {verifiedPayload.cutoff_snapshot && (
                      <div className="flex items-center gap-2 text-xs">
                        <span className="text-white/40">Cutoff:</span>
                        <code className="text-cyan-400 font-mono">{verifiedPayload.cutoff_snapshot}</code>
                      </div>
                    )}
                  </Section>
                )}
              </>
            )}

            {/* Draft Scenario Details */}
            {isDraft && draftPayload && (
              <>
                <Section title="Scenario">
                  {draftPayload.scenario_description && (
                    <p className="text-sm text-white/70 mb-3">{draftPayload.scenario_description}</p>
                  )}
                  {draftPayload.estimated_delta !== undefined && (
                    <MetricRow
                      label="Estimated Delta"
                      value={`${draftPayload.estimated_delta > 0 ? '+' : ''}${(draftPayload.estimated_delta * 100).toFixed(0)}%`}
                      icon={draftPayload.delta_direction === 'positive' ? TrendingUp : draftPayload.delta_direction === 'negative' ? TrendingDown : Minus}
                      valueColor={draftPayload.delta_direction === 'positive' ? 'text-green-400' : draftPayload.delta_direction === 'negative' ? 'text-red-400' : 'text-purple-400'}
                    />
                  )}
                  {draftPayload.confidence_level && (
                    <MetricRow
                      label="Confidence"
                      value={
                        <span className={cn('px-2 py-0.5 uppercase text-[10px]', confidenceConfig[draftPayload.confidence_level].bg, confidenceConfig[draftPayload.confidence_level].color)}>
                          {draftPayload.confidence_level}
                        </span>
                      }
                    />
                  )}
                </Section>

                {draftPayload.rationale && draftPayload.rationale.length > 0 && (
                  <Section title="Rationale">
                    <ul className="space-y-1.5">
                      {draftPayload.rationale.map((point, i) => (
                        <li key={i} className="text-xs text-white/60 flex items-start gap-2">
                          <span className="text-cyan-400 mt-0.5">\u2022</span>
                          {point}
                        </li>
                      ))}
                    </ul>
                  </Section>
                )}

                {draftPayload.evidence_refs && draftPayload.evidence_refs.length > 0 && (
                  <Section title="Evidence">
                    <div className="space-y-2">
                      {draftPayload.evidence_refs.map((ref, i) => (
                        <div key={i} className="flex items-center gap-2 text-xs p-2 bg-white/5 border border-white/10">
                          <Link2 className="w-3 h-3 text-amber-400" />
                          <span className="text-white/70 truncate flex-1">
                            {ref.source_url || ref.evidence_pack_id}
                          </span>
                          <span className={cn(
                            'text-[9px] font-mono px-1.5 py-0.5',
                            ref.temporal_compliance === 'PASS' ? 'text-green-400 bg-green-500/10' :
                            ref.temporal_compliance === 'WARN' ? 'text-yellow-400 bg-yellow-500/10' :
                            'text-red-400 bg-red-500/10'
                          )}>
                            {ref.temporal_compliance}
                          </span>
                        </div>
                      ))}
                    </div>
                  </Section>
                )}
              </>
            )}

            {/* Failed Node Details */}
            {isFailed && failedPayload && (
              <Section title="Error Details">
                <div className="p-3 bg-red-500/10 border border-red-500/30">
                  <div className="flex items-start gap-2 mb-2">
                    <AlertTriangle className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-sm text-red-400 font-medium">{failedPayload.stage}</p>
                      <p className="text-xs text-red-400/80 mt-1">{failedPayload.message}</p>
                    </div>
                  </div>
                  {failedPayload.correlation_id && (
                    <div className="text-[10px] text-red-400/60 font-mono mt-2">
                      Correlation ID: {failedPayload.correlation_id}
                    </div>
                  )}
                  {failedPayload.guidance && (
                    <p className="text-xs text-amber-400/80 mt-3 pt-2 border-t border-red-500/20">
                      {failedPayload.guidance}
                    </p>
                  )}
                </div>
              </Section>
            )}
          </>
        )}
      </div>

      {/* Actions */}
      <div className="p-4 border-t border-white/10 space-y-2">
        {/* Expand button - available for verified outcomes */}
        {isVerified && node.status === 'DONE' && onExpand && (
          <Button
            onClick={() => onExpand(node.node_id)}
            className="w-full bg-purple-500/20 hover:bg-purple-500/30 text-purple-400 border border-purple-500/40"
            disabled={isRunning || loading}
          >
            <Zap className="w-4 h-4 mr-2" />
            Expand (Generate Scenarios)
          </Button>
        )}

        {/* Run button - available for draft scenarios */}
        {isDraft && node.status === 'DRAFT' && onRun && (
          <Button
            onClick={() => onRun(node.node_id)}
            className="w-full bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-400 border border-cyan-500/40"
            disabled={isRunning || loading}
          >
            <Play className="w-4 h-4 mr-2" />
            Run (Verify Scenario)
          </Button>
        )}

        {/* Edit button - optional for draft scenarios */}
        {isDraft && node.status === 'DRAFT' && onEdit && (
          <Button
            variant="outline"
            onClick={() => onEdit(node.node_id)}
            className="w-full text-white/60 border-white/20 hover:bg-white/5"
            disabled={isRunning || loading}
          >
            <Edit3 className="w-4 h-4 mr-2" />
            Edit Scenario
          </Button>
        )}

        {/* Retry button - for failed nodes */}
        {isFailed && failedPayload?.retryable && onRetry && (
          <Button
            onClick={() => onRetry(node.node_id)}
            className="w-full bg-amber-500/20 hover:bg-amber-500/30 text-amber-400 border border-amber-500/40"
            disabled={loading}
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Retry
          </Button>
        )}

        {/* Running indicator */}
        {isRunning && (
          <div className="flex items-center justify-center gap-2 py-2 text-cyan-400">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-xs font-mono">{node.status === 'QUEUED' ? 'Queued...' : 'Running...'}</span>
          </div>
        )}
      </div>
    </div>
  );
}

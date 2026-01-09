'use client';

/**
 * Node Detail Page
 * Spec-compliant node viewer with outcome data, children, and fork capability
 * Reference: project.md §6.7 (Node/Edge), C1 (fork-not-mutate)
 */

import { useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import {
  GitBranch,
  GitMerge,
  Target,
  Loader2,
  ArrowLeft,
  Play,
  BarChart3,
  Terminal,
  RefreshCw,
  AlertTriangle,
  Percent,
  TrendingUp,
  TrendingDown,
  Minus,
  ChevronRight,
  ExternalLink,
  FileText,
  Clock,
  Layers,
  Route,
  CheckCircle,
  Tag,
  Pin,
  Star,
  Settings2,
} from 'lucide-react';
import { useNode, useNodeChildren, useNodeEdges, useForkNode } from '@/hooks/useApi';
import { cn } from '@/lib/utils';
import { ForkTuneDrawer } from '@/components/nodes/ForkTuneDrawer';
import type { EdgeSummary, SpecNode } from '@/lib/api';

const confidenceColors: Record<string, { bg: string; text: string; border: string }> = {
  high: { bg: 'bg-green-500/10', text: 'text-green-400', border: 'border-green-500/30' },
  medium: { bg: 'bg-yellow-500/10', text: 'text-yellow-400', border: 'border-yellow-500/30' },
  low: { bg: 'bg-orange-500/10', text: 'text-orange-400', border: 'border-orange-500/30' },
  very_low: { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/30' },
};

const trendIcons = {
  increasing: TrendingUp,
  stable: Minus,
  decreasing: TrendingDown,
};

export default function NodeDetailPage() {
  const params = useParams();
  const router = useRouter();
  const nodeId = params.id as string;

  const { data: node, isLoading, error, refetch } = useNode(nodeId);
  const { data: children = [] } = useNodeChildren(nodeId);
  const { data: edges = [] } = useNodeEdges(nodeId);
  const forkNode = useForkNode();

  const [forkLabel, setForkLabel] = useState('');
  const [forkDrawerOpen, setForkDrawerOpen] = useState(false);

  const handleFork = async () => {
    try {
      const result = await forkNode.mutateAsync({
        parent_node_id: nodeId,
        label: forkLabel || `Fork of ${nodeId.slice(0, 8)}`,
      });
      if (result?.node?.node_id) {
        router.push(`/dashboard/nodes/${result.node.node_id}`);
      }
    } catch {
      // Error handled by mutation
    }
  };

  const handleForkCreated = (newNodeId: string, runId?: string) => {
    if (runId) {
      router.push(`/dashboard/runs/${runId}`);
    } else {
      router.push(`/dashboard/nodes/${newNodeId}`);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-cyan-400" />
      </div>
    );
  }

  if (error || !node) {
    return (
      <div className="min-h-screen bg-black p-6">
        <div className="bg-red-500/10 border border-red-500/30 p-6 max-w-md mx-auto mt-12">
          <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-4" />
          <p className="text-sm font-mono text-red-400 text-center mb-4">
            Failed to load node details
          </p>
          <div className="flex justify-center gap-2">
            <Button variant="secondary" size="sm" onClick={() => refetch()}>
              RETRY
            </Button>
            <Button variant="secondary" size="sm" onClick={() => router.push('/dashboard/nodes')}>
              BACK TO NODES
            </Button>
          </div>
        </div>
      </div>
    );
  }

  const isRoot = !node.parent_node_id;
  const confidence = confidenceColors[node.confidence?.confidence_level] || confidenceColors.low;

  return (
    <div className="min-h-screen bg-black p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <Link
            href="/dashboard/nodes"
            className="flex items-center gap-1 text-xs font-mono text-white/40 hover:text-white mb-2"
          >
            <ArrowLeft className="w-3 h-3" />
            Back to Universe Map
          </Link>
          <div className="flex items-center gap-3">
            <div className={cn(
              'p-2 border',
              isRoot ? 'bg-cyan-500/10 border-cyan-500/30' : 'bg-purple-500/10 border-purple-500/30'
            )}>
              {isRoot ? (
                <Target className="w-5 h-5 text-cyan-400" />
              ) : (
                <GitBranch className="w-5 h-5 text-purple-400" />
              )}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-mono font-bold text-white">
                  {isRoot ? 'Root Node' : 'Fork Node'}
                </h1>
                {node.is_baseline && (
                  <span className="px-2 py-0.5 bg-blue-500/20 text-blue-400 text-[10px] font-mono uppercase">
                    Baseline
                  </span>
                )}
                {node.is_pinned && (
                  <Pin className="w-4 h-4 text-yellow-400" />
                )}
              </div>
              <p className="text-xs font-mono text-white/40">
                {node.node_id}
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" onClick={() => refetch()}>
            <RefreshCw className="w-3 h-3 mr-2" />
            REFRESH
          </Button>
        </div>
      </div>

      {/* Node Label */}
      {node.label && (
        <div className="bg-white/5 border border-white/10 p-4 mb-6">
          <div className="flex items-center gap-2 mb-2">
            <Tag className="w-4 h-4 text-white/40" />
            <span className="text-xs font-mono text-white/40 uppercase">Label</span>
          </div>
          <p className="text-lg font-mono text-white">{node.label}</p>
          {node.description && (
            <p className="text-sm font-mono text-white/60 mt-2">{node.description}</p>
          )}
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {/* Probability */}
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-2">
            <Percent className="w-4 h-4 text-cyan-400" />
            <span className="text-xs font-mono text-white/40">Probability</span>
          </div>
          <span className="text-2xl font-mono font-bold text-white">
            {(node.probability * 100).toFixed(1)}%
          </span>
        </div>

        {/* Cumulative Probability */}
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-2">
            <Route className="w-4 h-4 text-purple-400" />
            <span className="text-xs font-mono text-white/40">Cumulative</span>
          </div>
          <span className="text-2xl font-mono font-bold text-white">
            {(node.cumulative_probability * 100).toFixed(1)}%
          </span>
        </div>

        {/* Depth */}
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-2">
            <Layers className="w-4 h-4 text-blue-400" />
            <span className="text-xs font-mono text-white/40">Depth</span>
          </div>
          <span className="text-2xl font-mono font-bold text-white">
            {node.depth}
          </span>
        </div>

        {/* Children */}
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-2">
            <GitMerge className="w-4 h-4 text-green-400" />
            <span className="text-xs font-mono text-white/40">Forks</span>
          </div>
          <span className="text-2xl font-mono font-bold text-white">
            {node.child_count}
          </span>
        </div>
      </div>

      {/* Confidence Section */}
      <div className={cn('border p-6 mb-6', confidence.bg, confidence.border)}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <CheckCircle className={cn('w-5 h-5', confidence.text)} />
            <span className={cn('text-lg font-mono font-bold uppercase', confidence.text)}>
              {node.confidence?.confidence_level} Confidence
            </span>
          </div>
          <span className={cn('text-2xl font-mono font-bold', confidence.text)}>
            {((node.confidence?.confidence_score || 0) * 100).toFixed(0)}%
          </span>
        </div>

        {node.confidence?.factors && node.confidence.factors.length > 0 && (
          <div className="space-y-2">
            <span className="text-xs font-mono text-white/40 uppercase">Confidence Factors</span>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {node.confidence.factors.map((factor, index) => (
                <div key={index} className="flex items-center justify-between px-3 py-2 bg-black/30">
                  <span className="text-xs font-mono text-white/60">{factor.factor_name}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono text-white">
                      {(factor.score * 100).toFixed(0)}%
                    </span>
                    <span className="text-[10px] font-mono text-white/30">
                      w:{factor.weight}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Aggregated Outcome Section */}
      {node.aggregated_outcome && (
        <div className="bg-white/5 border border-white/10 p-6 mb-6">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="w-5 h-5 text-cyan-400" />
            <span className="text-lg font-mono font-bold text-white">Aggregated Outcome</span>
          </div>

          {/* Primary Outcome */}
          <div className="mb-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-mono text-white/60">Primary Outcome</span>
              <span className="text-sm font-mono text-cyan-400">
                {(node.aggregated_outcome.primary_outcome_probability * 100).toFixed(1)}% likely
              </span>
            </div>
            <p className="text-lg font-mono text-white">
              {node.aggregated_outcome.primary_outcome}
            </p>
          </div>

          {/* Outcome Distribution */}
          {node.aggregated_outcome.outcome_distribution && (
            <div className="mb-4">
              <span className="text-xs font-mono text-white/40 uppercase mb-2 block">
                Outcome Distribution
              </span>
              <div className="flex gap-1 h-6 mb-2">
                {Object.entries(node.aggregated_outcome.outcome_distribution).map(([label, count], index) => {
                  const total = Object.values(node.aggregated_outcome?.outcome_distribution || {}).reduce(
                    (a, b) => a + (b as number),
                    0
                  );
                  const percent = total > 0 ? ((count as number) / total) * 100 : 0;
                  const colors = ['bg-cyan-500', 'bg-blue-500', 'bg-purple-500', 'bg-pink-500', 'bg-orange-500'];
                  return (
                    <div
                      key={label}
                      className={cn('h-full', colors[index % colors.length])}
                      style={{ width: `${percent}%` }}
                      title={`${label}: ${percent.toFixed(1)}%`}
                    />
                  );
                })}
              </div>
              <div className="flex flex-wrap gap-3">
                {Object.entries(node.aggregated_outcome.outcome_distribution).map(([label, count], index) => {
                  const total = Object.values(node.aggregated_outcome?.outcome_distribution || {}).reduce(
                    (a, b) => a + (b as number),
                    0
                  );
                  const percent = total > 0 ? ((count as number) / total) * 100 : 0;
                  const colors = ['text-cyan-400', 'text-blue-400', 'text-purple-400', 'text-pink-400', 'text-orange-400'];
                  return (
                    <div key={label} className="flex items-center gap-1">
                      <span className={cn('text-xs font-mono', colors[index % colors.length])}>●</span>
                      <span className="text-xs font-mono text-white/60">{label}:</span>
                      <span className="text-xs font-mono text-white">{percent.toFixed(1)}%</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Key Metrics */}
          {node.aggregated_outcome.key_metrics && node.aggregated_outcome.key_metrics.length > 0 && (
            <div>
              <span className="text-xs font-mono text-white/40 uppercase mb-2 block">
                Key Metrics
              </span>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {node.aggregated_outcome.key_metrics.map((metric, index) => {
                  const TrendIcon = metric.trend ? trendIcons[metric.trend] : Minus;
                  const trendColor = metric.trend === 'increasing' ? 'text-green-400' :
                                     metric.trend === 'decreasing' ? 'text-red-400' : 'text-white/40';
                  return (
                    <div key={index} className="bg-black/30 p-3">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[10px] font-mono text-white/40 truncate">
                          {metric.metric_name}
                        </span>
                        {metric.trend && (
                          <TrendIcon className={cn('w-3 h-3', trendColor)} />
                        )}
                      </div>
                      <span className="text-lg font-mono text-white">
                        {metric.value}{metric.unit ? ` ${metric.unit}` : ''}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Summary Text */}
          {node.aggregated_outcome.summary_text && (
            <div className="mt-4 pt-4 border-t border-white/10">
              <p className="text-sm font-mono text-white/60">
                {node.aggregated_outcome.summary_text}
              </p>
            </div>
          )}
        </div>
      )}

      {/* References Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {/* Project */}
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-2">
            <FileText className="w-4 h-4 text-white/40" />
            <span className="text-xs font-mono text-white/40">Project</span>
          </div>
          <Link
            href={`/dashboard/projects/${node.project_id}`}
            className="text-sm font-mono text-cyan-400 hover:text-cyan-300 hover:underline"
          >
            {node.project_id.slice(0, 16)}...
          </Link>
        </div>

        {/* Parent Node */}
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-2">
            <GitBranch className="w-4 h-4 text-white/40" />
            <span className="text-xs font-mono text-white/40">Parent Node</span>
          </div>
          {node.parent_node_id ? (
            <Link
              href={`/dashboard/nodes/${node.parent_node_id}`}
              className="text-sm font-mono text-cyan-400 hover:text-cyan-300 hover:underline"
            >
              {node.parent_node_id.slice(0, 16)}...
            </Link>
          ) : (
            <span className="text-sm font-mono text-white/30">Root (no parent)</span>
          )}
        </div>

        {/* Run Reference */}
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-2">
            <Play className="w-4 h-4 text-white/40" />
            <span className="text-xs font-mono text-white/40">Run</span>
          </div>
          {node.run_refs && node.run_refs.length > 0 ? (
            <Link
              href={`/dashboard/runs/${node.run_refs[0].artifact_id}`}
              className="text-sm font-mono text-cyan-400 hover:text-cyan-300 hover:underline"
            >
              {node.run_refs[0].artifact_id.slice(0, 16)}...
            </Link>
          ) : (
            <span className="text-sm font-mono text-white/30">No runs</span>
          )}
        </div>

        {/* Telemetry */}
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-2">
            <BarChart3 className="w-4 h-4 text-white/40" />
            <span className="text-xs font-mono text-white/40">Telemetry</span>
          </div>
          {node.telemetry_ref ? (
            <Link
              href={`/dashboard/runs/${node.run_refs?.[0]?.artifact_id}/telemetry`}
              className="text-sm font-mono text-cyan-400 hover:text-cyan-300 hover:underline"
            >
              View Telemetry
            </Link>
          ) : (
            <span className="text-sm font-mono text-white/30">No telemetry</span>
          )}
        </div>
      </div>

      {/* Timestamps */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-2">
            <Clock className="w-4 h-4 text-white/40" />
            <span className="text-xs font-mono text-white/40">Created</span>
          </div>
          <span className="text-sm font-mono text-white">
            {new Date(node.created_at).toLocaleString()}
          </span>
        </div>
        <div className="bg-white/5 border border-white/10 p-4">
          <div className="flex items-center gap-2 mb-2">
            <RefreshCw className="w-4 h-4 text-white/40" />
            <span className="text-xs font-mono text-white/40">Updated</span>
          </div>
          <span className="text-sm font-mono text-white">
            {new Date(node.updated_at).toLocaleString()}
          </span>
        </div>
      </div>

      {/* Tags */}
      {node.tags && node.tags.length > 0 && (
        <div className="bg-white/5 border border-white/10 p-4 mb-6">
          <div className="flex items-center gap-2 mb-3">
            <Tag className="w-4 h-4 text-white/40" />
            <span className="text-xs font-mono text-white/40 uppercase">Tags</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {node.tags.map((tag, index) => (
              <span
                key={index}
                className="px-2 py-1 bg-white/10 text-xs font-mono text-white/60"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Children (Forks) */}
      {children.length > 0 && (
        <div className="bg-white/5 border border-white/10 p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <GitMerge className="w-5 h-5 text-purple-400" />
              <span className="text-lg font-mono font-bold text-white">
                Fork Nodes ({children.length})
              </span>
            </div>
          </div>
          <div className="space-y-2">
            {children.map((child) => (
              <Link
                key={child.node_id}
                href={`/dashboard/nodes/${child.node_id}`}
                className="flex items-center justify-between p-3 bg-black hover:bg-white/5 border border-white/10 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <GitBranch className="w-4 h-4 text-purple-400" />
                  <div>
                    <span className="text-sm font-mono text-white">
                      {child.node_id.slice(0, 16)}...
                    </span>
                    {child.label && (
                      <p className="text-xs font-mono text-white/40">{child.label}</p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-xs font-mono text-white/40">
                    {(child.probability * 100).toFixed(1)}%
                  </span>
                  <ChevronRight className="w-4 h-4 text-white/40" />
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Edges */}
      {edges.length > 0 && (
        <div className="bg-white/5 border border-white/10 p-6 mb-6">
          <div className="flex items-center gap-2 mb-4">
            <Route className="w-5 h-5 text-white/40" />
            <span className="text-lg font-mono font-bold text-white">
              Edges ({edges.length})
            </span>
          </div>
          <div className="space-y-2">
            {edges.map((edge: EdgeSummary) => (
              <div
                key={edge.edge_id}
                className="p-3 bg-black border border-white/10 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono text-white/60">
                      {edge.from_node_id.slice(0, 8)} → {edge.to_node_id.slice(0, 8)}
                    </span>
                  </div>
                  <span className="text-[10px] font-mono text-white/30 uppercase">
                    {edge.intervention_type || 'fork'}
                  </span>
                </div>
                {edge.short_label && (
                  <p className="text-xs font-mono text-white/40 mt-2">
                    {edge.short_label}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Fork Action */}
      <div className="bg-purple-500/10 border border-purple-500/30 p-6">
        <div className="flex items-center gap-2 mb-4">
          <GitBranch className="w-5 h-5 text-purple-400" />
          <span className="text-lg font-mono font-bold text-purple-400">
            Fork This Node
          </span>
        </div>
        <p className="text-sm font-mono text-white/60 mb-4">
          Create a new branch from this node to explore alternative outcomes.
          Fork-not-mutate: the original node remains unchanged.
        </p>

        {/* Fork Options */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Quick Fork */}
          <div className="bg-black/30 border border-white/10 p-4">
            <div className="flex items-center gap-2 mb-3">
              <GitBranch className="w-4 h-4 text-white/40" />
              <span className="text-xs font-mono text-white/60 uppercase">Quick Fork</span>
            </div>
            <p className="text-[10px] font-mono text-white/40 mb-3">
              Create a simple fork without parameter changes
            </p>
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Optional label..."
                value={forkLabel}
                onChange={(e) => setForkLabel(e.target.value)}
                className="flex-1 px-3 py-2 bg-white/5 border border-white/10 text-xs font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/20"
              />
              <Button
                variant="secondary"
                size="sm"
                onClick={handleFork}
                disabled={forkNode.isPending}
              >
                {forkNode.isPending ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <GitBranch className="w-3 h-3" />
                )}
              </Button>
            </div>
          </div>

          {/* Fork & Tune */}
          <div className="bg-black/30 border border-cyan-500/30 p-4">
            <div className="flex items-center gap-2 mb-3">
              <Settings2 className="w-4 h-4 text-cyan-400" />
              <span className="text-xs font-mono text-cyan-400 uppercase">Fork & Tune</span>
            </div>
            <p className="text-[10px] font-mono text-white/40 mb-3">
              Adjust variables and run a simulation with modified parameters
            </p>
            <Button
              onClick={() => setForkDrawerOpen(true)}
              className="w-full"
            >
              <Settings2 className="w-3.5 h-3.5 mr-2" />
              OPEN TUNING DRAWER
            </Button>
          </div>
        </div>
      </div>

      {/* Fork & Tune Drawer */}
      {node && (
        <ForkTuneDrawer
          nodeId={node.node_id}
          projectId={node.project_id}
          open={forkDrawerOpen}
          onOpenChange={setForkDrawerOpen}
          onForkCreated={handleForkCreated}
        />
      )}

      {/* Footer */}
      <div className="mt-8 pt-4 border-t border-white/5">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1">
              <Terminal className="w-3 h-3" />
              <span>SPEC-COMPLIANT NODE</span>
            </div>
            <div className="flex items-center gap-1">
              <GitBranch className="w-3 h-3" />
              <span>C1: FORK-NOT-MUTATE</span>
            </div>
          </div>
          <span>project.md §6.7</span>
        </div>
      </div>
    </div>
  );
}

'use client';

/**
 * Thought Expansion Graph (TEG) Main Component
 *
 * Replaces the old Universe Map with a "parallel universe / probability mind-map" UI.
 * Reference: docs/TEG_UNIVERSE_MAP_EXECUTION.md
 */

import { useState, useCallback } from 'react';
import { ReactFlowProvider } from '@xyflow/react';
import {
  Globe,
  Search,
  RefreshCw,
  Loader2,
  AlertCircle,
  GitBranch,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import { TEGCanvas } from './TEGCanvas';
import { TEGTable } from './TEGTable';
import { TEGRaw } from './TEGRaw';
import { TEGNodeDetails } from './TEGNodeDetails';
import { TEGViewToggle } from './TEGViewToggle';
import type { TEGViewMode, TEGNode, TEGEdge, TEGGraph } from './types';

interface ThoughtExpansionGraphProps {
  projectId: string;
  graph: TEGGraph | null;
  loading?: boolean;
  error?: Error | null;
  onRefresh?: () => void;
  onExpand?: (nodeId: string) => void;
  onRun?: (nodeId: string) => void;
}

export function ThoughtExpansionGraph({
  projectId,
  graph,
  loading = false,
  error = null,
  onRefresh,
  onExpand,
  onRun,
}: ThoughtExpansionGraphProps) {
  const [viewMode, setViewMode] = useState<TEGViewMode>('graph');
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const nodes = graph?.nodes || [];
  const edges = graph?.edges || [];

  // Find selected node
  const selectedNode = selectedNodeId
    ? nodes.find((n) => n.node_id === selectedNodeId) || null
    : null;

  // Find baseline node for comparison
  const baselineNode = graph?.active_baseline_node_id
    ? nodes.find((n) => n.node_id === graph.active_baseline_node_id) || null
    : nodes.find((n) => n.type === 'OUTCOME_VERIFIED' && !n.parent_node_id) || null;

  // Filter nodes by search
  const filteredNodes = searchQuery
    ? nodes.filter(
        (n) =>
          n.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
          n.summary?.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : nodes;

  const handleNodeSelect = useCallback((nodeId: string | null) => {
    setSelectedNodeId(nodeId);
  }, []);

  // Error state
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 text-center">
        <AlertCircle className="w-12 h-12 text-red-400 mb-4" />
        <h3 className="text-lg font-medium text-white/80 mb-2">Failed to Load TEG</h3>
        <p className="text-sm text-white/50 mb-4 max-w-md">{error.message}</p>
        {onRefresh && (
          <Button onClick={onRefresh} variant="outline" className="text-white/60">
            <RefreshCw className="w-4 h-4 mr-2" />
            Retry
          </Button>
        )}
      </div>
    );
  }

  // Empty state (no baseline run yet)
  if (!loading && nodes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 text-center">
        <div className="relative mb-6">
          <GitBranch className="w-16 h-16 text-cyan-500/30" />
          <div className="absolute -inset-4 bg-cyan-500/10 blur-xl rounded-full" />
        </div>
        <h3 className="text-xl font-medium text-white/80 mb-3">
          Thought Expansion Graph
        </h3>
        <p className="text-sm text-white/50 max-w-md mb-6">
          Run a baseline simulation first to populate the TEG. Once you have a verified
          baseline outcome, you can expand it to explore alternative scenarios.
        </p>
        <div className="flex items-center gap-2 text-xs text-white/30">
          <span className="w-2 h-2 rounded-full bg-cyan-500/50" />
          <span>Verified outcomes appear here after runs complete</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-black">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Globe className="w-5 h-5 text-cyan-400" />
            <h1 className="text-lg font-medium text-white/90">Thought Expansion Graph</h1>
          </div>
          <span className="text-xs font-mono text-white/30 bg-white/5 px-2 py-0.5">
            {nodes.length} node{nodes.length !== 1 ? 's' : ''}
          </span>
        </div>

        <div className="flex items-center gap-3">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search nodes..."
              className="w-48 pl-8 h-8 text-xs bg-black/40 border-white/10 focus:border-cyan-500/50"
            />
          </div>

          {/* View Toggle */}
          <TEGViewToggle mode={viewMode} onChange={setViewMode} />

          {/* Refresh */}
          {onRefresh && (
            <Button
              onClick={onRefresh}
              variant="ghost"
              size="sm"
              disabled={loading}
              className="text-white/60 hover:text-white"
            >
              <RefreshCw className={cn('w-4 h-4', loading && 'animate-spin')} />
            </Button>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex min-h-0">
        {/* Graph/Table/Raw View */}
        <div className="flex-1 min-w-0">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <Loader2 className="w-8 h-8 text-cyan-500 animate-spin mx-auto mb-4" />
                <p className="text-white/60 font-mono text-sm">Loading TEG...</p>
              </div>
            </div>
          ) : (
            <>
              {viewMode === 'graph' && (
                <ReactFlowProvider>
                  <TEGCanvas
                    nodes={filteredNodes}
                    edges={edges}
                    selectedNodeId={selectedNodeId}
                    onNodeSelect={handleNodeSelect}
                    onExpand={onExpand}
                    onRun={onRun}
                  />
                </ReactFlowProvider>
              )}

              {viewMode === 'table' && (
                <TEGTable
                  nodes={filteredNodes}
                  selectedNodeId={selectedNodeId}
                  onNodeSelect={handleNodeSelect}
                />
              )}

              {viewMode === 'raw' && (
                <TEGRaw node={selectedNode} edges={edges} />
              )}
            </>
          )}
        </div>

        {/* Node Details Panel (right side) */}
        <div className="w-80 border-l border-white/10 bg-black/50 flex-shrink-0">
          <TEGNodeDetails
            node={selectedNode}
            onExpand={onExpand}
            onRun={onRun}
            loading={loading}
            baselineNode={baselineNode}
          />
        </div>
      </div>
    </div>
  );
}

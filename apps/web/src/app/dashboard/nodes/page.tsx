'use client';

/**
 * Nodes/Universe Map Page
 * Spec-compliant node browser with visualization
 * Reference: project.md §6.7 (Node/Edge), C1 (fork-not-mutate)
 */

import { useState, useMemo } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import {
  GitBranch,
  GitMerge,
  Loader2,
  Search,
  RefreshCw,
  Target,
  Route,
  ChevronRight,
  Play,
  Eye,
  Terminal,
  AlertTriangle,
  Layers,
  TreeDeciduous,
} from 'lucide-react';
import { useNodes, useUniverseMap, useForkNode, useProjectSpecs } from '@/hooks/useApi';
import { cn } from '@/lib/utils';

export default function NodesPage() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');

  // Fetch available projects
  const { data: projects } = useProjectSpecs();

  // Fetch nodes for selected project
  const {
    data: nodes,
    isLoading,
    error,
    refetch
  } = useNodes(selectedProjectId ? { project_id: selectedProjectId } : undefined);

  // Fetch universe map for selected project
  const { data: universeMap } = useUniverseMap(selectedProjectId || undefined);

  // Fork node mutation
  const forkNode = useForkNode();

  // Filter nodes by search
  const filteredNodes = useMemo(() => {
    if (!nodes) return [];
    if (!searchQuery) return nodes;
    return nodes.filter(node =>
      node.node_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      node.label?.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [nodes, searchQuery]);

  // Group nodes by level (root vs children)
  const { rootNodes, childNodes } = useMemo(() => {
    const root = filteredNodes.filter(n => !n.parent_node_id);
    const children = filteredNodes.filter(n => n.parent_node_id);
    return { rootNodes: root, childNodes: children };
  }, [filteredNodes]);

  const handleFork = async (nodeId: string) => {
    try {
      const result = await forkNode.mutateAsync({
        parent_node_id: nodeId,
        label: `Fork of ${nodeId.slice(0, 8)}`,
      });
      if (result?.node?.node_id) {
        refetch();
        router.push(`/dashboard/nodes/${result.node.node_id}`);
      }
    } catch {
      // Error handled by mutation
    }
  };

  return (
    <div className="min-h-screen bg-black p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <GitMerge className="w-4 h-4 text-purple-400" />
            <span className="text-xs font-mono text-white/40 uppercase tracking-wider">Universe Map</span>
          </div>
          <h1 className="text-xl font-mono font-bold text-white">Simulation Nodes</h1>
          <p className="text-sm font-mono text-white/50 mt-1">
            Browse and fork simulation decision points
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" onClick={() => refetch()}>
            <RefreshCw className="w-3 h-3 mr-2" />
            REFRESH
          </Button>
        </div>
      </div>

      {/* Project Selector */}
      <div className="bg-white/5 border border-white/10 p-4 mb-6">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-white/40" />
            <span className="text-xs font-mono text-white/40 uppercase">Select Project</span>
          </div>
          <select
            value={selectedProjectId}
            onChange={(e) => setSelectedProjectId(e.target.value)}
            className="flex-1 max-w-md px-3 py-2 bg-white/5 border border-white/10 text-sm font-mono text-white appearance-none focus:outline-none focus:border-purple-500/50"
          >
            <option value="">All Projects</option>
            {projects?.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name || project.id.slice(0, 12)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Stats Bar */}
      {nodes && nodes.length > 0 && (
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-white/5 border border-white/10 p-4">
            <div className="flex items-center gap-2 mb-2">
              <Target className="w-4 h-4 text-cyan-400" />
              <span className="text-xs font-mono text-white/40">ROOT NODES</span>
            </div>
            <span className="text-2xl font-mono font-bold text-white">
              {rootNodes.length}
            </span>
          </div>
          <div className="bg-white/5 border border-white/10 p-4">
            <div className="flex items-center gap-2 mb-2">
              <GitBranch className="w-4 h-4 text-purple-400" />
              <span className="text-xs font-mono text-white/40">FORK NODES</span>
            </div>
            <span className="text-2xl font-mono font-bold text-white">
              {childNodes.length}
            </span>
          </div>
          <div className="bg-white/5 border border-white/10 p-4">
            <div className="flex items-center gap-2 mb-2">
              <TreeDeciduous className="w-4 h-4 text-green-400" />
              <span className="text-xs font-mono text-white/40">TOTAL NODES</span>
            </div>
            <span className="text-2xl font-mono font-bold text-white">
              {nodes.length}
            </span>
          </div>
          <div className="bg-white/5 border border-white/10 p-4">
            <div className="flex items-center gap-2 mb-2">
              <Route className="w-4 h-4 text-orange-400" />
              <span className="text-xs font-mono text-white/40">VISIBLE EDGES</span>
            </div>
            <span className="text-2xl font-mono font-bold text-white">
              {universeMap?.visible_edges?.length || 0}
            </span>
          </div>
        </div>
      )}

      {/* Search */}
      <div className="flex gap-3 mb-6">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-white/30" />
          <input
            type="text"
            placeholder="Search nodes..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-7 pr-3 py-1.5 bg-white/5 border border-white/10 text-xs font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-purple-500/50"
          />
        </div>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-4 h-4 animate-spin text-purple-400" />
          <span className="ml-2 text-sm font-mono text-white/40">Loading nodes...</span>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 p-4">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="w-4 h-4 text-red-400" />
            <p className="text-sm font-mono text-red-400">Failed to load nodes</p>
          </div>
          <Button variant="secondary" size="sm" onClick={() => refetch()}>
            RETRY
          </Button>
        </div>
      )}

      {/* No Project Selected */}
      {!selectedProjectId && !isLoading && (
        <div className="bg-white/5 border border-white/10 p-12 text-center">
          <Layers className="w-12 h-12 text-white/20 mx-auto mb-4" />
          <p className="text-sm font-mono text-white/60 mb-2">Select a Project</p>
          <p className="text-xs font-mono text-white/30">
            Choose a project above to view its Universe Map nodes
          </p>
        </div>
      )}

      {/* Empty State */}
      {selectedProjectId && !isLoading && !error && filteredNodes.length === 0 && (
        <div className="bg-white/5 border border-white/10 p-12 text-center">
          <GitBranch className="w-12 h-12 text-white/20 mx-auto mb-4" />
          <p className="text-sm font-mono text-white/60 mb-2">No nodes found</p>
          <p className="text-xs font-mono text-white/30 mb-4">
            Run a simulation to create nodes in the Universe Map
          </p>
          <Link href="/dashboard/runs">
            <Button size="sm">
              <Play className="w-3 h-3 mr-2" />
              VIEW RUNS
            </Button>
          </Link>
        </div>
      )}

      {/* Nodes Grid */}
      {!isLoading && !error && filteredNodes.length > 0 && (
        <div className="space-y-6">
          {/* Root Nodes */}
          {rootNodes.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <Target className="w-4 h-4 text-cyan-400" />
                <span className="text-xs font-mono text-white/40 uppercase tracking-wider">
                  Root Nodes ({rootNodes.length})
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {rootNodes.map((node) => (
                  <NodeCard
                    key={node.node_id}
                    node={node}
                    isRoot
                    onFork={() => handleFork(node.node_id)}
                    isForkPending={forkNode.isPending}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Child Nodes */}
          {childNodes.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <GitBranch className="w-4 h-4 text-purple-400" />
                <span className="text-xs font-mono text-white/40 uppercase tracking-wider">
                  Fork Nodes ({childNodes.length})
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {childNodes.map((node) => (
                  <NodeCard
                    key={node.node_id}
                    node={node}
                    onFork={() => handleFork(node.node_id)}
                    isForkPending={forkNode.isPending}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Footer */}
      <div className="mt-8 pt-4 border-t border-white/5">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1">
              <Terminal className="w-3 h-3" />
              <span>UNIVERSE MAP</span>
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

interface NodeCardProps {
  node: {
    node_id: string;
    parent_node_id?: string;
    label?: string;
    probability: number;
    confidence_level: string;
    is_baseline: boolean;
    has_outcome: boolean;
    child_count: number;
    created_at: string;
  };
  isRoot?: boolean;
  onFork: () => void;
  isForkPending: boolean;
}

function NodeCard({ node, isRoot, onFork, isForkPending }: NodeCardProps) {
  return (
    <div className={cn(
      'bg-white/5 border p-4 hover:bg-white/10 transition-colors',
      isRoot ? 'border-cyan-500/30' : 'border-white/10'
    )}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {isRoot ? (
            <Target className="w-4 h-4 text-cyan-400" />
          ) : (
            <GitBranch className="w-4 h-4 text-purple-400" />
          )}
          <span className="text-xs font-mono text-white/40">
            {isRoot ? 'ROOT' : 'FORK'}
          </span>
        </div>
        {node.is_baseline && (
          <span className="px-1.5 py-0.5 bg-blue-500/20 text-blue-400 text-[10px] font-mono uppercase">
            Baseline
          </span>
        )}
      </div>

      {/* Node ID */}
      <Link
        href={`/dashboard/nodes/${node.node_id}`}
        className="block mb-3"
      >
        <span className="text-sm font-mono text-cyan-400 hover:text-cyan-300 hover:underline">
          {node.node_id.slice(0, 16)}...
        </span>
        {node.label && (
          <p className="text-xs font-mono text-white/40 mt-1 truncate">
            {node.label}
          </p>
        )}
      </Link>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-2 mb-3">
        <div>
          <span className="text-[10px] font-mono text-white/30 uppercase">Probability</span>
          <p className="text-sm font-mono text-white">
            {(node.probability * 100).toFixed(1)}%
          </p>
        </div>
        <div>
          <span className="text-[10px] font-mono text-white/30 uppercase">Confidence</span>
          <p className="text-sm font-mono text-white capitalize">
            {node.confidence_level}
          </p>
        </div>
        <div>
          <span className="text-[10px] font-mono text-white/30 uppercase">Children</span>
          <p className="text-sm font-mono text-white">
            {node.child_count}
          </p>
        </div>
        <div>
          <span className="text-[10px] font-mono text-white/30 uppercase">Has Outcome</span>
          <p className="text-sm font-mono text-white">
            {node.has_outcome ? 'Yes' : 'No'}
          </p>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 pt-3 border-t border-white/10">
        <Link href={`/dashboard/nodes/${node.node_id}`} className="flex-1">
          <Button variant="secondary" size="sm" className="w-full">
            <Eye className="w-3 h-3 mr-1" />
            View
          </Button>
        </Link>
        <Button
          variant="secondary"
          size="sm"
          onClick={onFork}
          disabled={isForkPending}
          className="flex-1"
        >
          <GitBranch className="w-3 h-3 mr-1" />
          Fork
        </Button>
      </div>

      {/* Timestamp */}
      <p className="text-[10px] font-mono text-white/20 mt-3">
        Created: {new Date(node.created_at).toLocaleDateString()}
      </p>
    </div>
  );
}

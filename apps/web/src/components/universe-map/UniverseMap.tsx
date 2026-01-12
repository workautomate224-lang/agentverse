'use client';

/**
 * UniverseMap Component
 * Main container for Universe Map visualization.
 * Reference: project.md §6.7 (Node/Edge), C1 (fork-not-mutate), C3 (read-only)
 */

import { memo, useState, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import {
  GitBranch,
  GitMerge,
  Play,
  Target,
  Route,
  AlertCircle,
  Loader2,
  ChevronRight,
  ExternalLink,
  RefreshCw,
  BarChart3,
  Check,
  HelpCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { UniverseMapCanvas } from './UniverseMapCanvas';
import { UniverseMapControls } from './UniverseMapControls';
import { NodeCard } from './NodeCard';
import { CompareView, AskDrawer, ForkTuneDrawer } from '@/components/nodes';
import {
  useUniverseMap,
  useNodes,
  useNode,
  useNodeChildren,
  useNodeEdges,
  useForkNode,
  useAnalyzeNodePath,
  useMostLikelyPaths,
} from '@/hooks/useApi';
import type { SpecNode, SpecEdge, PathAnalysis, NodeCluster } from '@/lib/api';

// Helper to get run ID from run_refs (handles both string and object formats)
function getRunId(runRef: string | { artifact_id: string }): string {
  return typeof runRef === 'string' ? runRef : runRef.artifact_id;
}

interface UniverseMapProps {
  projectId: string;
  initialSelectedNodeId?: string;
  onNodeSelect?: (nodeId: string) => void;
  onRunSelect?: (runId: string) => void;
  showSidebar?: boolean;
  className?: string;
}

export const UniverseMap = memo(function UniverseMap({
  projectId,
  initialSelectedNodeId,
  onNodeSelect,
  onRunSelect,
  showSidebar = true,
  className,
}: UniverseMapProps) {
  const router = useRouter();

  // State
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(
    initialSelectedNodeId || null
  );
  const [showClusters, setShowClusters] = useState(false);
  const [highlightedPath, setHighlightedPath] = useState<PathAnalysis | null>(null);

  // Compare mode state
  const [compareMode, setCompareMode] = useState(false);
  const [compareNodeIds, setCompareNodeIds] = useState<string[]>([]);
  const [pinnedNodeId, setPinnedNodeId] = useState<string | null>(null);

  // Ask drawer state
  const [askDrawerOpen, setAskDrawerOpen] = useState(false);

  // Fork drawer state
  const [forkDrawerOpen, setForkDrawerOpen] = useState(false);
  const [forkNodeId, setForkNodeId] = useState<string | null>(null);

  // Fetch universe map data
  const {
    data: universeMap,
    isLoading: mapLoading,
    error: mapError,
    refetch: refetchMap,
  } = useUniverseMap(projectId);

  // Fetch nodes for the project
  const {
    data: nodes = [],
    isLoading: nodesLoading,
    refetch: refetchNodes,
  } = useNodes({ project_id: projectId });

  // Fetch full node details (includes run_refs)
  const { data: fullSelectedNode } = useNode(selectedNodeId || undefined);

  // Fetch edges for selected node
  const { data: selectedNodeEdges = [] } = useNodeEdges(selectedNodeId || undefined);

  // Fetch children for selected node
  const { data: selectedNodeChildren } = useNodeChildren(selectedNodeId || undefined);

  // Fork node mutation
  const forkNode = useForkNode();

  // Path analysis
  const analyzeNodePath = useAnalyzeNodePath();

  // Most likely paths
  const { data: mostLikelyPaths } = useMostLikelyPaths(projectId, 3);

  // Build edges from node parent relationships
  const edges: SpecEdge[] = useMemo(() => {
    const edgeList: SpecEdge[] = [];
    nodes.forEach((node) => {
      if (node.parent_node_id) {
        edgeList.push({
          edge_id: `${node.parent_node_id}-${node.node_id}`,
          from_node_id: node.parent_node_id,
          to_node_id: node.node_id,
          created_at: node.created_at,
        } as SpecEdge);
      }
    });
    return edgeList;
  }, [nodes]);

  // Find selected node
  const selectedNode = useMemo(
    () => nodes.find((n) => n.node_id === selectedNodeId),
    [nodes, selectedNodeId]
  );

  // Find root node
  const rootNode = useMemo(
    () => nodes.find((n) => !n.parent_node_id),
    [nodes]
  );

  // Compute compare nodes list from selected IDs
  const compareNodes = useMemo(
    () => nodes.filter((n) => compareNodeIds.includes(n.node_id)),
    [nodes, compareNodeIds]
  );

  // Handle node selection (supports compare mode multi-select)
  const handleNodeSelect = useCallback(
    (nodeId: string, shiftKey?: boolean) => {
      if (compareMode || shiftKey) {
        // Compare mode: toggle node in selection (max 4)
        setCompareNodeIds((prev) => {
          if (prev.includes(nodeId)) {
            // Remove from selection
            const next = prev.filter((id) => id !== nodeId);
            // Clear pinned if removed
            if (pinnedNodeId === nodeId) {
              setPinnedNodeId(null);
            }
            return next;
          } else if (prev.length < 4) {
            // Add to selection
            return [...prev, nodeId];
          }
          return prev;
        });
        // Enable compare mode if shift-clicking
        if (shiftKey && !compareMode) {
          setCompareMode(true);
        }
      } else {
        // Normal mode: single selection
        setSelectedNodeId(nodeId);
        onNodeSelect?.(nodeId);
      }
    },
    [compareMode, pinnedNodeId, onNodeSelect]
  );

  // Toggle compare mode
  const handleToggleCompareMode = useCallback(() => {
    if (compareMode) {
      // Exit compare mode
      setCompareMode(false);
      setCompareNodeIds([]);
      setPinnedNodeId(null);
    } else {
      // Enter compare mode, start with current selected node if any
      setCompareMode(true);
      if (selectedNodeId) {
        setCompareNodeIds([selectedNodeId]);
      }
    }
  }, [compareMode, selectedNodeId]);

  // Add node to compare selection
  const handleAddCompareNode = useCallback(() => {
    // Just enable multi-select mode hint
  }, []);

  // Remove node from compare selection
  const handleRemoveCompareNode = useCallback((nodeId: string) => {
    setCompareNodeIds((prev) => prev.filter((id) => id !== nodeId));
    if (pinnedNodeId === nodeId) {
      setPinnedNodeId(null);
    }
  }, [pinnedNodeId]);

  // Close compare view
  const handleCloseCompare = useCallback(() => {
    setCompareMode(false);
    setCompareNodeIds([]);
    setPinnedNodeId(null);
  }, []);

  // Handle fork
  // Open fork drawer for variable tuning
  const handleFork = useCallback(
    (nodeId: string) => {
      setForkNodeId(nodeId);
      setForkDrawerOpen(true);
    },
    []
  );

  // Handle path analysis
  const handlePathAnalysis = useCallback(async () => {
    if (!rootNode || !selectedNodeId || rootNode.node_id === selectedNodeId) return;

    try {
      const result = await analyzeNodePath.mutateAsync({
        start_node_id: rootNode.node_id,
        end_node_id: selectedNodeId,
      });
      setHighlightedPath(result);
    } catch {
      // Error handled by mutation
    }
  }, [rootNode, selectedNodeId, analyzeNodePath]);

  // Handle view run
  const handleViewRun = useCallback(
    (runId: string) => {
      onRunSelect?.(runId);
      router.push(`/dashboard/runs/${runId}`);
    },
    [router, onRunSelect]
  );

  // Handle refresh
  const handleRefresh = useCallback(() => {
    refetchMap();
    refetchNodes();
  }, [refetchMap, refetchNodes]);

  // Loading state
  const isLoading = mapLoading || nodesLoading;

  // Error state
  if (mapError) {
    return (
      <div className={cn('flex items-center justify-center p-12 bg-black border border-white/10', className)}>
        <div className="text-center">
          <AlertCircle className="w-8 h-8 text-red-400 mx-auto mb-3" />
          <p className="text-sm font-mono text-red-400 mb-2">
            Failed to load Universe Map
          </p>
          <Button variant="secondary" size="sm" onClick={handleRefresh}>
            <RefreshCw className="w-3 h-3 mr-1" />
            Retry
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-black border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-purple-500/10">
            <GitMerge className="w-5 h-5 text-purple-400" />
          </div>
          <div>
            <h2 className="text-lg font-mono font-bold text-white">
              Universe Map
            </h2>
            <p className="text-xs font-mono text-white/40">
              Project: {projectId.slice(0, 12)}...
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Ask What If Button */}
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setAskDrawerOpen(true)}
          >
            <HelpCircle className="w-3 h-3 mr-1" />
            Ask
          </Button>

          {/* Compare Mode Toggle */}
          <Button
            variant={compareMode ? 'primary' : 'secondary'}
            size="sm"
            onClick={handleToggleCompareMode}
            disabled={nodes.length < 2}
          >
            {compareMode ? (
              <>
                <Check className="w-3 h-3 mr-1" />
                Exit Compare
              </>
            ) : (
              <>
                <BarChart3 className="w-3 h-3 mr-1" />
                Compare
              </>
            )}
          </Button>
          {mostLikelyPaths && mostLikelyPaths.length > 0 && (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setHighlightedPath(mostLikelyPaths[0])}
            >
              <Target className="w-3 h-3 mr-1" />
              Most Likely Path
            </Button>
          )}
        </div>
      </div>

      {/* Compare Mode Indicator */}
      {compareMode && (
        <div className="px-4 py-2 bg-cyan-500/10 border-b border-cyan-500/20">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-cyan-400" />
              <span className="text-xs font-mono text-cyan-400">
                Compare Mode Active
              </span>
              <span className="text-xs font-mono text-white/40">
                — Click or Shift+click nodes to select (max 4)
              </span>
            </div>
            <span className="text-xs font-mono text-cyan-400">
              {compareNodeIds.length}/4 selected
            </span>
          </div>
        </div>
      )}

      {/* Controls */}
      <UniverseMapControls
        onRefresh={handleRefresh}
        onShowClusters={setShowClusters}
        showClusters={showClusters}
        onShowPathAnalysis={handlePathAnalysis}
        isLoading={isLoading}
        nodeCount={nodes.length}
        edgeCount={edges.length}
      />

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Canvas */}
        <div className="flex-1 relative">
          {isLoading ? (
            <div className="absolute inset-0 flex items-center justify-center bg-black">
              <div className="flex items-center gap-3 text-white/40">
                <Loader2 className="w-5 h-5 animate-spin" />
                <span className="text-sm font-mono">Loading map...</span>
              </div>
            </div>
          ) : nodes.length === 0 ? (
            <div className="absolute inset-0 flex items-center justify-center bg-black">
              <div className="text-center">
                <GitBranch className="w-8 h-8 text-white/20 mx-auto mb-3" />
                <p className="text-sm font-mono text-white/40 mb-4">
                  No simulation runs yet
                </p>
                <p className="text-xs font-mono text-white/30">
                  Run a simulation to see the Universe Map
                </p>
              </div>
            </div>
          ) : (
            <UniverseMapCanvas
              nodes={nodes as unknown as SpecNode[]}
              edges={edges}
              clusters={undefined}
              highlightedPath={highlightedPath || undefined}
              selectedNodeId={selectedNodeId || undefined}
              compareNodeIds={compareMode ? compareNodeIds : undefined}
              onNodeSelect={handleNodeSelect}
              width={800}
              height={600}
              className="w-full h-full"
            />
          )}
        </div>

        {/* Sidebar */}
        {showSidebar && (
          <div className="w-80 border-l border-white/10 bg-black overflow-y-auto">
            {selectedNode ? (
              <div className="p-4 space-y-4">
                {/* Selected Node */}
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <Target className="w-4 h-4 text-cyan-400" />
                    <span className="text-xs font-mono text-white/40 uppercase tracking-wider">
                      Selected Node
                    </span>
                  </div>
                  <NodeCard
                    node={selectedNode}
                    isSelected
                    onFork={handleFork}
                    onViewRun={handleViewRun}
                  />
                </div>

                {/* Children */}
                {selectedNodeChildren && selectedNodeChildren.length > 0 && (
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <GitBranch className="w-3.5 h-3.5 text-white/40" />
                        <span className="text-xs font-mono text-white/40 uppercase tracking-wider">
                          Forks ({selectedNodeChildren.length})
                        </span>
                      </div>
                    </div>
                    <div className="space-y-1">
                      {selectedNodeChildren.map((child) => (
                        <NodeCard
                          key={child.node_id}
                          node={child}
                          onSelect={handleNodeSelect}
                          compact
                        />
                      ))}
                    </div>
                  </div>
                )}

                {/* Path Analysis */}
                {highlightedPath && (
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <Route className="w-3.5 h-3.5 text-white/40" />
                      <span className="text-xs font-mono text-white/40 uppercase tracking-wider">
                        Path Analysis
                      </span>
                    </div>
                    <div className="p-3 bg-white/5 border border-white/10 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono text-white/60">Length</span>
                        <span className="text-xs font-mono text-white">
                          {highlightedPath.node_sequence?.length || 0} nodes
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono text-white/60">Probability</span>
                        <span className="text-xs font-mono text-cyan-400">
                          {((highlightedPath.path_probability || 0) * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="pt-4 border-t border-white/10 space-y-2">
                  <Button
                    variant="primary"
                    size="sm"
                    className="w-full"
                    onClick={() => handleFork(selectedNode.node_id)}
                  >
                    <GitBranch className="w-3 h-3 mr-1" />
                    Fork This Node
                  </Button>
                  {fullSelectedNode?.run_refs && fullSelectedNode.run_refs.length > 0 && (
                    <Button
                      variant="secondary"
                      size="sm"
                      className="w-full"
                      onClick={() => handleViewRun(getRunId(fullSelectedNode.run_refs![0]))}
                    >
                      <Play className="w-3 h-3 mr-1" />
                      View Run Details
                    </Button>
                  )}
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-full">
                <div className="text-center p-4">
                  <GitBranch className="w-6 h-6 text-white/20 mx-auto mb-2" />
                  <p className="text-xs font-mono text-white/40">
                    Select a node to view details
                  </p>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Compare View Tray */}
      {compareMode && (
        <CompareView
          selectedNodes={compareNodes}
          onAddNode={handleAddCompareNode}
          onRemoveNode={handleRemoveCompareNode}
          onClose={handleCloseCompare}
          pinnedNodeId={pinnedNodeId || undefined}
          onPinNode={setPinnedNodeId}
        />
      )}

      {/* Ask Drawer */}
      <AskDrawer
        projectId={projectId}
        nodeId={selectedNodeId || undefined}
        open={askDrawerOpen}
        onOpenChange={setAskDrawerOpen}
        onScenarioExecuted={(nodeId) => {
          setSelectedNodeId(nodeId);
          refetchNodes();
        }}
      />

      {/* Fork Tune Drawer */}
      {forkNodeId && (
        <ForkTuneDrawer
          nodeId={forkNodeId}
          projectId={projectId}
          open={forkDrawerOpen}
          onOpenChange={(open) => {
            setForkDrawerOpen(open);
            if (!open) setForkNodeId(null);
          }}
          onForkCreated={(newNodeId: string) => {
            setSelectedNodeId(newNodeId);
            setForkDrawerOpen(false);
            setForkNodeId(null);
            refetchNodes();
          }}
        />
      )}
    </div>
  );
});

export default UniverseMap;

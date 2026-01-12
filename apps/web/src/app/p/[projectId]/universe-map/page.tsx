'use client';

/**
 * Universe Map Page
 * Visualize the simulation universe and agent relationships
 */

import { useState, useMemo } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  Globe,
  ArrowLeft,
  ArrowRight,
  Terminal,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Filter,
  Download,
  RefreshCw,
  Loader2,
  AlertCircle,
  X,
  Eye,
  EyeOff,
  Users,
  GitBranch,
  TrendingUp,
  Clock,
  CheckCircle,
  Circle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  useUniverseMapFull,
  useNodes,
  useTargetPersonas,
  usePersonaTemplates,
} from '@/hooks/useApi';
import type { SpecNode, NodeSummary } from '@/lib/api';

// Format probability as percentage
function formatProbability(prob: number): string {
  return `${(prob * 100).toFixed(1)}%`;
}

// Format date for display
function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

// Confidence badge component
function ConfidenceBadge({ level }: { level?: string }) {
  const config: Record<string, { color: string; label: string }> = {
    high: { color: 'text-green-400 bg-green-400/10', label: 'HIGH' },
    medium: { color: 'text-yellow-400 bg-yellow-400/10', label: 'MED' },
    low: { color: 'text-red-400 bg-red-400/10', label: 'LOW' },
  };

  const c = config[level || 'medium'] || config.medium;

  return (
    <span className={cn('inline-flex items-center px-1.5 py-0.5 text-[9px] font-mono uppercase', c.color)}>
      {c.label}
    </span>
  );
}

// Filter Panel Component
function FilterPanel({
  open,
  onClose,
  filters,
  onFiltersChange,
}: {
  open: boolean;
  onClose: () => void;
  filters: {
    showLowConfidence: boolean;
    probabilityThreshold: number;
    nodeTypes: string[];
  };
  onFiltersChange: (filters: {
    showLowConfidence: boolean;
    probabilityThreshold: number;
    nodeTypes: string[];
  }) => void;
}) {
  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="bg-black border border-white/10 max-w-sm">
        <DialogHeader>
          <DialogTitle className="text-white font-mono flex items-center gap-2">
            <Filter className="w-5 h-5 text-cyan-400" />
            Filter Universe Map
          </DialogTitle>
          <DialogDescription className="text-white/50 font-mono text-xs">
            Adjust visibility settings for nodes
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={filters.showLowConfidence}
                onChange={(e) =>
                  onFiltersChange({ ...filters, showLowConfidence: e.target.checked })
                }
                className="w-4 h-4 bg-white/5 border border-white/20 rounded"
              />
              <span className="text-xs font-mono text-white/80">Show low confidence nodes</span>
            </label>
          </div>

          <div>
            <label className="block text-xs font-mono text-white/60 mb-2">
              Probability Threshold: {(filters.probabilityThreshold * 100).toFixed(0)}%
            </label>
            <input
              type="range"
              min={0}
              max={100}
              value={filters.probabilityThreshold * 100}
              onChange={(e) =>
                onFiltersChange({ ...filters, probabilityThreshold: Number(e.target.value) / 100 })
              }
              className="w-full h-1 bg-white/10 rounded appearance-none cursor-pointer"
            />
            <div className="flex justify-between text-[10px] font-mono text-white/40 mt-1">
              <span>0%</span>
              <span>100%</span>
            </div>
          </div>

          <div>
            <label className="block text-xs font-mono text-white/60 mb-2">Node Types</label>
            <div className="space-y-2">
              {['baseline', 'fork', 'cluster'].map((type) => (
                <label key={type} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={filters.nodeTypes.includes(type)}
                    onChange={(e) => {
                      const newTypes = e.target.checked
                        ? [...filters.nodeTypes, type]
                        : filters.nodeTypes.filter((t) => t !== type);
                      onFiltersChange({ ...filters, nodeTypes: newTypes });
                    }}
                    className="w-4 h-4 bg-white/5 border border-white/20 rounded"
                  />
                  <span className="text-xs font-mono text-white/80 capitalize">{type}</span>
                </label>
              ))}
            </div>
          </div>
        </div>

        <DialogFooter className="flex justify-end gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() =>
              onFiltersChange({
                showLowConfidence: true,
                probabilityThreshold: 0,
                nodeTypes: ['baseline', 'fork', 'cluster'],
              })
            }
          >
            Reset
          </Button>
          <Button size="sm" onClick={onClose} className="bg-cyan-500 hover:bg-cyan-600">
            Apply Filters
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Node Inspector Modal
function NodeInspectorModal({
  node,
  open,
  onClose,
  projectId,
}: {
  node: SpecNode | NodeSummary | null;
  open: boolean;
  onClose: () => void;
  projectId: string;
}) {
  if (!node) return null;

  const isFullNode = 'depth' in node;

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="bg-black border border-white/10 max-w-lg">
        <DialogHeader>
          <DialogTitle className="text-white font-mono flex items-center gap-2">
            <GitBranch className="w-5 h-5 text-cyan-400" />
            Node Inspector
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-white/60">Node ID</span>
            <span className="text-xs font-mono text-white/80">{node.node_id.slice(0, 12)}...</span>
          </div>

          {node.label && (
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-white/60">Label</span>
              <span className="text-xs font-mono text-white/80">{node.label}</span>
            </div>
          )}

          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-white/60">Probability</span>
            <span className="text-xs font-mono text-white/80">{formatProbability(node.probability)}</span>
          </div>

          {'confidence_level' in node && (
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-white/60">Confidence</span>
              <ConfidenceBadge level={node.confidence_level} />
            </div>
          )}

          {isFullNode && (
            <>
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono text-white/60">Depth</span>
                <span className="text-xs font-mono text-white/80">{(node as SpecNode).depth}</span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-xs font-mono text-white/60">Cumulative Probability</span>
                <span className="text-xs font-mono text-white/80">
                  {formatProbability((node as SpecNode).cumulative_probability)}
                </span>
              </div>

              {(node as SpecNode).run_refs && (node as SpecNode).run_refs!.length > 0 && (
                <div>
                  <span className="text-xs font-mono text-white/60 block mb-2">
                    Associated Runs ({(node as SpecNode).run_refs!.length})
                  </span>
                  <div className="bg-white/5 border border-white/10 p-2 max-h-24 overflow-y-auto">
                    {(node as SpecNode).run_refs!.map((ref, i) => (
                      <div key={i} className="text-[10px] font-mono text-white/60">
                        {typeof ref === 'string' ? ref.slice(0, 16) + '...' : ref.artifact_id.slice(0, 16) + '...'}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {(node as SpecNode).aggregated_outcome && (
                <div>
                  <span className="text-xs font-mono text-white/60 block mb-2">Outcome</span>
                  <div className="bg-white/5 border border-white/10 p-2 text-[10px] font-mono text-white/60">
                    {(node as SpecNode).aggregated_outcome?.primary_outcome || 'N/A'}
                  </div>
                </div>
              )}
            </>
          )}

          {'is_baseline' in node && (
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-white/60">Type</span>
              <span className={cn(
                'text-xs font-mono',
                (node as NodeSummary).is_baseline ? 'text-cyan-400' : 'text-purple-400'
              )}>
                {(node as NodeSummary).is_baseline ? 'Baseline' : 'Fork'}
              </span>
            </div>
          )}

          {'child_count' in node && (
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-white/60">Children</span>
              <span className="text-xs font-mono text-white/80">{(node as NodeSummary).child_count}</span>
            </div>
          )}

          {'created_at' in node && (
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-white/60">Created</span>
              <span className="text-xs font-mono text-white/80">{formatDate((node as NodeSummary).created_at)}</span>
            </div>
          )}
        </div>

        <DialogFooter className="flex justify-end gap-2">
          {'has_outcome' in node && (node as NodeSummary).has_outcome && (
            <Link href={`/p/${projectId}/results?node=${node.node_id}`}>
              <Button size="sm" className="bg-cyan-500 hover:bg-cyan-600">
                <TrendingUp className="w-3 h-3 mr-2" />
                View Results
              </Button>
            </Link>
          )}
          <Link href={`/p/${projectId}/replay?node=${node.node_id}`}>
            <Button size="sm" variant="outline">
              <Eye className="w-3 h-3 mr-2" />
              Open in Replay
            </Button>
          </Link>
          <Button variant="ghost" size="sm" onClick={onClose}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Export Modal
function ExportModal({
  open,
  onClose,
  nodes,
  projectId,
}: {
  open: boolean;
  onClose: () => void;
  nodes: (SpecNode | NodeSummary)[];
  projectId: string;
}) {
  const [format, setFormat] = useState<'json' | 'csv'>('json');

  const handleExport = () => {
    let content: string;
    let filename: string;
    let mimeType: string;

    if (format === 'json') {
      content = JSON.stringify({ project_id: projectId, nodes, exported_at: new Date().toISOString() }, null, 2);
      filename = `universe-map-${projectId}-${Date.now()}.json`;
      mimeType = 'application/json';
    } else {
      const headers = ['node_id', 'label', 'probability', 'parent_node_id'];
      const rows = nodes.map((n) => [
        n.node_id,
        n.label || '',
        n.probability.toString(),
        n.parent_node_id || '',
      ]);
      content = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
      filename = `universe-map-${projectId}-${Date.now()}.csv`;
      mimeType = 'text/csv';
    }

    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="bg-black border border-white/10 max-w-sm">
        <DialogHeader>
          <DialogTitle className="text-white font-mono flex items-center gap-2">
            <Download className="w-5 h-5 text-cyan-400" />
            Export Universe Map
          </DialogTitle>
          <DialogDescription className="text-white/50 font-mono text-xs">
            Export {nodes.length} nodes to file
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div>
            <label className="block text-xs font-mono text-white/60 mb-2">Format</label>
            <div className="flex gap-2">
              <button
                onClick={() => setFormat('json')}
                className={cn(
                  'flex-1 p-3 border text-xs font-mono transition-colors',
                  format === 'json'
                    ? 'bg-cyan-500/10 border-cyan-500/50 text-cyan-400'
                    : 'bg-white/5 border-white/10 text-white/60 hover:bg-white/10'
                )}
              >
                JSON
              </button>
              <button
                onClick={() => setFormat('csv')}
                className={cn(
                  'flex-1 p-3 border text-xs font-mono transition-colors',
                  format === 'csv'
                    ? 'bg-cyan-500/10 border-cyan-500/50 text-cyan-400'
                    : 'bg-white/5 border-white/10 text-white/60 hover:bg-white/10'
                )}
              >
                CSV
              </button>
            </div>
          </div>
        </div>

        <DialogFooter className="flex justify-end gap-2">
          <Button variant="ghost" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button size="sm" onClick={handleExport} className="bg-cyan-500 hover:bg-cyan-600">
            <Download className="w-3 h-3 mr-2" />
            Export
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function UniverseMapPage() {
  const params = useParams();
  const projectId = params.projectId as string;

  // UI state
  const [zoomLevel, setZoomLevel] = useState(1);
  const [filterPanelOpen, setFilterPanelOpen] = useState(false);
  const [exportModalOpen, setExportModalOpen] = useState(false);
  const [selectedNode, setSelectedNode] = useState<SpecNode | NodeSummary | null>(null);
  const [nodeInspectorOpen, setNodeInspectorOpen] = useState(false);
  const [filters, setFilters] = useState({
    showLowConfidence: true,
    probabilityThreshold: 0,
    nodeTypes: ['baseline', 'fork', 'cluster'],
  });

  // API hooks
  const { data: universeMapData, isLoading: mapLoading, refetch: refetchMap, error: mapError } = useUniverseMapFull(projectId);
  const { data: nodesList, isLoading: nodesLoading, refetch: refetchNodes } = useNodes({ project_id: projectId, limit: 100 });
  const { data: personas } = useTargetPersonas({ project_id: projectId });
  const { data: personaTemplates } = usePersonaTemplates();

  // Combine data sources - prefer full map data, fall back to node list
  const nodes = useMemo(() => {
    if (universeMapData?.nodes && universeMapData.nodes.length > 0) {
      return universeMapData.nodes;
    }
    return nodesList || [];
  }, [universeMapData, nodesList]);

  // Filter nodes based on settings
  const filteredNodes = useMemo(() => {
    return nodes.filter((node) => {
      if (node.probability < filters.probabilityThreshold) return false;
      if (!filters.showLowConfidence) {
        const confidence = 'confidence' in node ? (node as SpecNode).confidence?.level :
                          'confidence_level' in node ? (node as NodeSummary).confidence_level : 'medium';
        if (confidence === 'low') return false;
      }
      return true;
    });
  }, [nodes, filters]);

  // Count personas
  const personaCount = (personas?.length || 0) + (personaTemplates?.length || 0);

  // Loading state
  const isLoading = mapLoading || nodesLoading;

  // Check if data is available
  const hasData = filteredNodes.length > 0;

  // Refresh handler
  const handleRefresh = () => {
    refetchMap();
    refetchNodes();
  };

  // Zoom handlers
  const handleZoomIn = () => setZoomLevel((z) => Math.min(z + 0.25, 3));
  const handleZoomOut = () => setZoomLevel((z) => Math.max(z - 0.25, 0.25));
  const handleFitView = () => setZoomLevel(1);

  return (
    <div className="min-h-screen bg-black p-4 md:p-6">
      {/* Header */}
      <div className="mb-6 md:mb-8">
        <div className="flex items-center gap-2 mb-3">
          <Link href={`/p/${projectId}/run-center`}>
            <Button variant="ghost" size="sm" className="text-[10px] md:text-xs">
              <ArrowLeft className="w-3 h-3 mr-1 md:mr-2" />
              BACK TO RUN CENTER
            </Button>
          </Link>
        </div>
        <div className="flex items-center gap-2 mb-1">
          <Globe className="w-3.5 h-3.5 md:w-4 md:h-4 text-blue-400" />
          <span className="text-[10px] md:text-xs font-mono text-white/40 uppercase tracking-wider">
            Universe Map
          </span>
        </div>
        <h1 className="text-lg md:text-xl font-mono font-bold text-white">Simulation Universe</h1>
        <p className="text-xs md:text-sm font-mono text-white/50 mt-1">
          Visualize your simulation universe, agents, and their relationships
        </p>
      </div>

      {/* Toolbar */}
      <div className="max-w-5xl mb-4">
        <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-white/5 border border-white/10">
          <div className="flex items-center gap-2">
            <Button variant="secondary" size="sm" className="text-xs" onClick={handleZoomIn}>
              <ZoomIn className="w-3 h-3 mr-1" />
              ZOOM IN
            </Button>
            <Button variant="secondary" size="sm" className="text-xs" onClick={handleZoomOut}>
              <ZoomOut className="w-3 h-3 mr-1" />
              ZOOM OUT
            </Button>
            <Button variant="secondary" size="sm" className="text-xs" onClick={handleFitView}>
              <Maximize2 className="w-3 h-3 mr-1" />
              FIT VIEW
            </Button>
            <span className="text-[10px] font-mono text-white/40 ml-2">{(zoomLevel * 100).toFixed(0)}%</span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="text-xs"
              onClick={() => setFilterPanelOpen(true)}
            >
              <Filter className="w-3 h-3 mr-1" />
              FILTER
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="text-xs"
              onClick={handleRefresh}
              disabled={isLoading}
            >
              <RefreshCw className={cn('w-3 h-3 mr-1', isLoading && 'animate-spin')} />
              REFRESH
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="text-xs"
              onClick={() => setExportModalOpen(true)}
              disabled={!hasData}
            >
              <Download className="w-3 h-3 mr-1" />
              EXPORT
            </Button>
          </div>
        </div>
      </div>

      {/* Map Viewport */}
      <div className="max-w-5xl">
        <div
          className="relative bg-white/5 border border-white/10 aspect-[16/10] min-h-[400px] overflow-hidden"
          style={{ transform: `scale(${zoomLevel})`, transformOrigin: 'center center' }}
        >
          {/* Grid Background */}
          <div
            className="absolute inset-0 opacity-20"
            style={{
              backgroundImage: `
                linear-gradient(to right, rgba(255,255,255,0.05) 1px, transparent 1px),
                linear-gradient(to bottom, rgba(255,255,255,0.05) 1px, transparent 1px)
              `,
              backgroundSize: '40px 40px',
            }}
          />

          {/* Loading State */}
          {isLoading && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/50 z-10">
              <div className="text-center">
                <Loader2 className="w-8 h-8 text-cyan-400 animate-spin mx-auto mb-2" />
                <p className="text-xs font-mono text-white/60">Loading universe map...</p>
              </div>
            </div>
          )}

          {/* Error State */}
          {mapError && !isLoading && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <AlertCircle className="w-8 h-8 text-yellow-400 mx-auto mb-2" />
                <p className="text-xs font-mono text-white/60 mb-2">Failed to load universe map</p>
                <p className="text-[10px] font-mono text-white/40 max-w-xs">
                  The universe map endpoint may not be available. Showing node list instead.
                </p>
              </div>
            </div>
          )}

          {/* Empty State */}
          {!isLoading && !hasData && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <div className="w-20 h-20 bg-white/5 flex items-center justify-center mx-auto mb-4 rounded-full">
                  <Globe className="w-10 h-10 text-white/20" />
                </div>
                <h3 className="text-sm font-mono text-white/60 mb-2">Universe is empty</h3>
                <p className="text-xs font-mono text-white/40 mb-4 max-w-xs">
                  Add personas and run simulations to populate your universe
                </p>
                <div className="flex items-center justify-center gap-3">
                  <Link href={`/p/${projectId}/data-personas`}>
                    <Button size="sm" variant="secondary" className="text-xs">
                      ADD PERSONAS
                    </Button>
                  </Link>
                  <Link href={`/p/${projectId}/run-center`}>
                    <Button size="sm" variant="secondary" className="text-xs">
                      RUN SIMULATION
                    </Button>
                  </Link>
                </div>
              </div>
            </div>
          )}

          {/* Node Visualization */}
          {hasData && !isLoading && (
            <div className="absolute inset-0 p-8">
              <div className="relative w-full h-full">
                {/* Simple grid layout for nodes */}
                <div className="flex flex-wrap gap-4 justify-center items-start content-start">
                  {filteredNodes.slice(0, 20).map((node, index) => {
                    const isBaseline = 'is_baseline' in node ? (node as NodeSummary).is_baseline :
                                      'depth' in node && (node as SpecNode).depth === 0;
                    const confidenceLevel = 'confidence_level' in node ? (node as NodeSummary).confidence_level :
                                           'confidence' in node ? (node as SpecNode).confidence?.level : 'medium';

                    return (
                      <button
                        key={node.node_id}
                        onClick={() => {
                          setSelectedNode(node);
                          setNodeInspectorOpen(true);
                        }}
                        className={cn(
                          'relative w-24 h-24 border-2 flex flex-col items-center justify-center p-2 transition-all hover:scale-105',
                          isBaseline
                            ? 'bg-cyan-500/10 border-cyan-500/50 hover:border-cyan-400'
                            : 'bg-purple-500/10 border-purple-500/50 hover:border-purple-400'
                        )}
                      >
                        <div className={cn(
                          'w-6 h-6 rounded-full mb-1',
                          isBaseline ? 'bg-cyan-500' : 'bg-purple-500'
                        )} />
                        <span className="text-[10px] font-mono text-white/80 truncate w-full text-center">
                          {node.label || node.node_id.slice(0, 8)}
                        </span>
                        <span className="text-[9px] font-mono text-white/50">
                          {formatProbability(node.probability)}
                        </span>
                        <div className="absolute -top-1 -right-1">
                          <ConfidenceBadge level={confidenceLevel} />
                        </div>
                      </button>
                    );
                  })}
                </div>

                {filteredNodes.length > 20 && (
                  <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2">
                    <span className="text-xs font-mono text-white/40 bg-black/80 px-3 py-1">
                      Showing 20 of {filteredNodes.length} nodes
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Coordinate Display */}
          <div className="absolute bottom-3 left-3 px-2 py-1 bg-black/80 text-[10px] font-mono text-white/40 z-20">
            Zoom: {(zoomLevel * 100).toFixed(0)}%
          </div>

          {/* Agent Count */}
          <div className="absolute bottom-3 right-3 px-2 py-1 bg-black/80 text-[10px] font-mono text-white/40 z-20">
            {filteredNodes.length} nodes | {personaCount} personas
          </div>
        </div>
      </div>

      {/* Legend */}
      <div className="max-w-5xl mt-4">
        <div className="flex flex-wrap items-center gap-4 p-3 bg-white/5 border border-white/10">
          <span className="text-[10px] font-mono text-white/40 uppercase">Legend:</span>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-cyan-500 rounded-full" />
            <span className="text-xs font-mono text-white/60">Baseline Nodes</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-purple-500 rounded-full" />
            <span className="text-xs font-mono text-white/60">Fork Nodes</span>
          </div>
          <div className="flex items-center gap-2">
            <ConfidenceBadge level="high" />
            <span className="text-xs font-mono text-white/60">High Confidence</span>
          </div>
          <div className="flex items-center gap-2">
            <ConfidenceBadge level="low" />
            <span className="text-xs font-mono text-white/60">Low Confidence</span>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <div className="max-w-5xl mt-6">
        <div className="flex items-center justify-between gap-4">
          <Link href={`/p/${projectId}/run-center`}>
            <Button variant="outline" size="sm" className="text-xs font-mono">
              <ArrowLeft className="w-3 h-3 mr-2" />
              Back to Run Center
            </Button>
          </Link>
          <Link href={`/p/${projectId}/replay`}>
            <Button size="sm" className="text-xs font-mono bg-cyan-500 hover:bg-cyan-600">
              Next: Replay
              <ArrowRight className="w-3 h-3 ml-2" />
            </Button>
          </Link>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-8 pt-4 border-t border-white/5 max-w-5xl">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-1">
            <Terminal className="w-3 h-3" />
            <span>UNIVERSE MAP</span>
          </div>
          <span>AGENTVERSE v1.0</span>
        </div>
      </div>

      {/* Modals */}
      <FilterPanel
        open={filterPanelOpen}
        onClose={() => setFilterPanelOpen(false)}
        filters={filters}
        onFiltersChange={setFilters}
      />

      <NodeInspectorModal
        node={selectedNode}
        open={nodeInspectorOpen}
        onClose={() => {
          setNodeInspectorOpen(false);
          setSelectedNode(null);
        }}
        projectId={projectId}
      />

      <ExportModal
        open={exportModalOpen}
        onClose={() => setExportModalOpen(false)}
        nodes={filteredNodes}
        projectId={projectId}
      />
    </div>
  );
}

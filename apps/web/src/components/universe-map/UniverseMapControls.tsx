'use client';

/**
 * UniverseMapControls Component
 * Controls for the Universe Map visualization (zoom, filter, etc.)
 * Reference: project.md §6.7 (Node navigation)
 */

import { memo, useState, useCallback } from 'react';
import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  Home,
  Filter,
  GitBranch,
  Target,
  Route,
  Layers,
  ChevronDown,
  Search,
  RefreshCw,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

interface UniverseMapControlsProps {
  onZoomIn?: () => void;
  onZoomOut?: () => void;
  onResetView?: () => void;
  onFitView?: () => void;
  onRefresh?: () => void;
  onFilterChange?: (filter: FilterState) => void;
  onShowPathAnalysis?: () => void;
  onShowClusters?: (show: boolean) => void;
  showClusters?: boolean;
  isLoading?: boolean;
  nodeCount?: number;
  edgeCount?: number;
  className?: string;
}

interface FilterState {
  showOnlyRoots: boolean;
  showOnlyLeaves: boolean;
  minProbability: number;
  maxLevel: number | null;
}

export const UniverseMapControls = memo(function UniverseMapControls({
  onZoomIn,
  onZoomOut,
  onResetView,
  onFitView,
  onRefresh,
  onFilterChange,
  onShowPathAnalysis,
  onShowClusters,
  showClusters = false,
  isLoading = false,
  nodeCount = 0,
  edgeCount = 0,
  className,
}: UniverseMapControlsProps) {
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<FilterState>({
    showOnlyRoots: false,
    showOnlyLeaves: false,
    minProbability: 0,
    maxLevel: null,
  });

  const handleFilterChange = useCallback(
    (key: keyof FilterState, value: boolean | number | null) => {
      const newFilters = { ...filters, [key]: value };
      setFilters(newFilters);
      onFilterChange?.(newFilters);
    },
    [filters, onFilterChange]
  );

  return (
    <div className={cn('space-y-2', className)}>
      {/* Main Controls Bar */}
      <div className="flex items-center justify-between p-2 bg-black border border-white/10">
        {/* Left: Stats */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-2 py-1 bg-white/5 border border-white/10">
            <GitBranch className="w-3 h-3 text-white/40" />
            <span className="text-[10px] font-mono text-white/60">
              {nodeCount} nodes
            </span>
          </div>
          <div className="flex items-center gap-2 px-2 py-1 bg-white/5 border border-white/10">
            <Route className="w-3 h-3 text-white/40" />
            <span className="text-[10px] font-mono text-white/60">
              {edgeCount} edges
            </span>
          </div>
        </div>

        {/* Center: View Controls */}
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={onZoomOut}
            title="Zoom Out"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={onZoomIn}
            title="Zoom In"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </Button>
          <div className="w-px h-4 bg-white/10 mx-1" />
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={onResetView}
            title="Reset View"
          >
            <Home className="w-3.5 h-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={onFitView}
            title="Fit to View"
          >
            <Maximize2 className="w-3.5 h-3.5" />
          </Button>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-1">
          <Button
            variant={showClusters ? 'secondary' : 'ghost'}
            size="sm"
            onClick={() => onShowClusters?.(!showClusters)}
            title="Show Clusters"
          >
            <Layers className="w-3.5 h-3.5 mr-1" />
            Clusters
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={onShowPathAnalysis}
            title="Analyze Paths"
          >
            <Route className="w-3.5 h-3.5 mr-1" />
            Paths
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowFilters(!showFilters)}
            title="Filters"
          >
            <Filter className="w-3.5 h-3.5 mr-1" />
            Filter
            <ChevronDown
              className={cn(
                'w-3 h-3 ml-1 transition-transform',
                showFilters && 'rotate-180'
              )}
            />
          </Button>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={onRefresh}
            disabled={isLoading}
            title="Refresh"
          >
            <RefreshCw className={cn('w-3.5 h-3.5', isLoading && 'animate-spin')} />
          </Button>
        </div>
      </div>

      {/* Filter Panel */}
      {showFilters && (
        <div className="p-3 bg-black border border-white/10 space-y-3">
          <div className="flex items-center gap-2 mb-2">
            <Filter className="w-3.5 h-3.5 text-white/40" />
            <span className="text-xs font-mono text-white/40 uppercase tracking-wider">
              Filters
            </span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {/* Show Only Roots */}
            <label className="flex items-center gap-2 cursor-pointer group">
              <input
                type="checkbox"
                checked={filters.showOnlyRoots}
                onChange={(e) => handleFilterChange('showOnlyRoots', e.target.checked)}
                className="w-4 h-4 bg-black border border-white/20 checked:bg-cyan-500 checked:border-cyan-500"
              />
              <span className="text-xs font-mono text-white/60 group-hover:text-white">
                Root nodes only
              </span>
            </label>

            {/* Show Only Leaves */}
            <label className="flex items-center gap-2 cursor-pointer group">
              <input
                type="checkbox"
                checked={filters.showOnlyLeaves}
                onChange={(e) => handleFilterChange('showOnlyLeaves', e.target.checked)}
                className="w-4 h-4 bg-black border border-white/20 checked:bg-cyan-500 checked:border-cyan-500"
              />
              <span className="text-xs font-mono text-white/60 group-hover:text-white">
                Leaf nodes only
              </span>
            </label>

            {/* Min Probability */}
            <div className="flex items-center gap-2">
              <Target className="w-3.5 h-3.5 text-white/40" />
              <span className="text-xs font-mono text-white/60">Min prob:</span>
              <input
                type="number"
                value={filters.minProbability}
                onChange={(e) =>
                  handleFilterChange('minProbability', parseFloat(e.target.value) || 0)
                }
                min={0}
                max={1}
                step={0.1}
                className="w-16 h-6 px-2 text-xs font-mono bg-black border border-white/20 text-white"
              />
            </div>

            {/* Max Level */}
            <div className="flex items-center gap-2">
              <Layers className="w-3.5 h-3.5 text-white/40" />
              <span className="text-xs font-mono text-white/60">Max level:</span>
              <input
                type="number"
                value={filters.maxLevel || ''}
                onChange={(e) =>
                  handleFilterChange(
                    'maxLevel',
                    e.target.value ? parseInt(e.target.value) : null
                  )
                }
                min={0}
                placeholder="All"
                className="w-16 h-6 px-2 text-xs font-mono bg-black border border-white/20 text-white placeholder:text-white/30"
              />
            </div>
          </div>

          {/* Quick Filter Buttons */}
          <div className="flex items-center gap-2 pt-2 border-t border-white/10">
            <span className="text-[10px] font-mono text-white/40">Quick:</span>
            <button
              onClick={() => {
                const newFilters = {
                  showOnlyRoots: false,
                  showOnlyLeaves: false,
                  minProbability: 0,
                  maxLevel: null,
                };
                setFilters(newFilters);
                onFilterChange?.(newFilters);
              }}
              className="px-2 py-1 text-[10px] font-mono text-white/60 hover:text-white bg-white/5 hover:bg-white/10 transition-colors"
            >
              Clear All
            </button>
            <button
              onClick={() => {
                const newFilters = {
                  ...filters,
                  minProbability: 0.1,
                };
                setFilters(newFilters);
                onFilterChange?.(newFilters);
              }}
              className="px-2 py-1 text-[10px] font-mono text-white/60 hover:text-white bg-white/5 hover:bg-white/10 transition-colors"
            >
              High Prob Only
            </button>
            <button
              onClick={() => {
                const newFilters = {
                  ...filters,
                  maxLevel: 3,
                };
                setFilters(newFilters);
                onFilterChange?.(newFilters);
              }}
              className="px-2 py-1 text-[10px] font-mono text-white/60 hover:text-white bg-white/5 hover:bg-white/10 transition-colors"
            >
              First 3 Levels
            </button>
          </div>
        </div>
      )}
    </div>
  );
});

export default UniverseMapControls;

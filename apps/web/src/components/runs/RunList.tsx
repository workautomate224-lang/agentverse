'use client';

/**
 * RunList Component
 * Displays a filterable list of simulation runs.
 * Reference: project.md §6.6 (Run management)
 */

import { memo, useState, useMemo, useCallback } from 'react';
import {
  Filter,
  Search,
  RefreshCw,
  Plus,
  List,
  Grid,
  ArrowUpDown,
  ChevronDown,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { RunCard } from './RunCard';
import { RunStatusBadge } from './RunStatusBadge';
import type { SpecRun, RunSummary, SpecRunStatus } from '@/lib/api';

interface RunListProps {
  runs: (SpecRun | RunSummary)[];
  projectId?: string;
  isLoading?: boolean;
  onRefresh?: () => void;
  onCreate?: () => void;
  onStartRun?: (runId: string) => void;
  onCancelRun?: (runId: string) => void;
  onDuplicateRun?: (runId: string) => void;
  onDeleteRun?: (runId: string) => void;
  showFilters?: boolean;
  showSearch?: boolean;
  defaultView?: 'list' | 'grid';
  className?: string;
}

type SortField = 'created_at' | 'status' | 'progress';
type SortDirection = 'asc' | 'desc';

const statusFilters: { label: string; value: SpecRunStatus | 'all' }[] = [
  { label: 'All', value: 'all' },
  { label: 'Queued', value: 'queued' },
  { label: 'Running', value: 'running' },
  { label: 'Succeeded', value: 'succeeded' },
  { label: 'Failed', value: 'failed' },
  { label: 'Cancelled', value: 'cancelled' },
];

export const RunList = memo(function RunList({
  runs,
  projectId,
  isLoading,
  onRefresh,
  onCreate,
  onStartRun,
  onCancelRun,
  onDuplicateRun,
  onDeleteRun,
  showFilters = true,
  showSearch = true,
  defaultView = 'list',
  className,
}: RunListProps) {
  // State
  const [view, setView] = useState<'list' | 'grid'>(defaultView);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<SpecRunStatus | 'all'>('all');
  const [sortField, setSortField] = useState<SortField>('created_at');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [showFilterDropdown, setShowFilterDropdown] = useState(false);

  // Filter and sort runs
  const filteredRuns = useMemo(() => {
    let result = [...runs];

    // Filter by status
    if (statusFilter !== 'all') {
      result = result.filter((run) => run.status === statusFilter);
    }

    // Filter by search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter((run) =>
        run.run_id.toLowerCase().includes(query) ||
        ('label' in run && run.label?.toLowerCase().includes(query))
      );
    }

    // Sort
    result.sort((a, b) => {
      let comparison = 0;
      switch (sortField) {
        case 'created_at':
          comparison = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
          break;
        case 'status':
          comparison = a.status.localeCompare(b.status);
          break;
        case 'progress':
          // Calculate progress from timing
          const getProgress = (run: typeof a) => {
            if (run.status === 'succeeded') return 100;
            if (run.status === 'queued') return 0;
            const current = run.timing?.current_tick ?? 0;
            const total = run.timing?.total_ticks ?? 0;
            return total > 0 ? (current / total) * 100 : 0;
          };
          comparison = getProgress(a) - getProgress(b);
          break;
      }
      return sortDirection === 'asc' ? comparison : -comparison;
    });

    return result;
  }, [runs, statusFilter, searchQuery, sortField, sortDirection]);

  // Toggle sort
  const toggleSort = useCallback((field: SortField) => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  }, [sortField]);

  // Status counts
  const statusCounts = useMemo(() => {
    const counts: Record<string, number> = { all: runs.length };
    runs.forEach((run) => {
      counts[run.status] = (counts[run.status] || 0) + 1;
    });
    return counts;
  }, [runs]);

  return (
    <div className={cn('space-y-4', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-mono font-bold text-white">
            Runs
          </h2>
          <span className="text-xs font-mono text-white/40 px-2 py-0.5 bg-white/5 border border-white/10">
            {filteredRuns.length} of {runs.length}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {onRefresh && (
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={onRefresh}
              disabled={isLoading}
              title="Refresh"
            >
              <RefreshCw className={cn('w-3.5 h-3.5', isLoading && 'animate-spin')} />
            </Button>
          )}
          {onCreate && (
            <Button variant="primary" size="sm" onClick={onCreate}>
              <Plus className="w-3.5 h-3.5 mr-1" />
              New Run
            </Button>
          )}
        </div>
      </div>

      {/* Filters & Search */}
      {(showFilters || showSearch) && (
        <div className="flex items-center gap-3 flex-wrap">
          {/* Search */}
          {showSearch && (
            <div className="relative flex-1 min-w-[200px] max-w-[300px]">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-white/40" />
              <input
                type="text"
                placeholder="Search runs..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full h-8 pl-8 pr-3 text-xs font-mono bg-black border border-white/10 text-white placeholder:text-white/30 focus:outline-none focus:border-white/30"
              />
            </div>
          )}

          {/* Status Filter */}
          {showFilters && (
            <div className="relative">
              <button
                onClick={() => setShowFilterDropdown(!showFilterDropdown)}
                className="flex items-center gap-2 h-8 px-3 text-xs font-mono bg-black border border-white/10 text-white/60 hover:text-white hover:border-white/20 transition-colors"
              >
                <Filter className="w-3.5 h-3.5" />
                <span>{statusFilter === 'all' ? 'All Status' : statusFilter}</span>
                <ChevronDown className="w-3 h-3" />
              </button>

              {showFilterDropdown && (
                <div className="absolute top-full left-0 mt-1 w-40 bg-black border border-white/20 shadow-lg z-10">
                  {statusFilters.map((filter) => (
                    <button
                      key={filter.value}
                      onClick={() => {
                        setStatusFilter(filter.value);
                        setShowFilterDropdown(false);
                      }}
                      className={cn(
                        'w-full flex items-center justify-between px-3 py-2 text-xs font-mono transition-colors',
                        statusFilter === filter.value
                          ? 'bg-white text-black'
                          : 'text-white/60 hover:text-white hover:bg-white/5'
                      )}
                    >
                      <span>{filter.label}</span>
                      <span className="text-[10px] opacity-60">
                        {statusCounts[filter.value] || 0}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Sort */}
          <button
            onClick={() => toggleSort('created_at')}
            className="flex items-center gap-1.5 h-8 px-3 text-xs font-mono bg-black border border-white/10 text-white/60 hover:text-white hover:border-white/20 transition-colors"
          >
            <ArrowUpDown className="w-3.5 h-3.5" />
            <span>Sort</span>
          </button>

          {/* View Toggle */}
          <div className="flex items-center border border-white/10">
            <button
              onClick={() => setView('list')}
              className={cn(
                'p-1.5 transition-colors',
                view === 'list' ? 'bg-white text-black' : 'text-white/40 hover:text-white'
              )}
            >
              <List className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setView('grid')}
              className={cn(
                'p-1.5 transition-colors',
                view === 'grid' ? 'bg-white text-black' : 'text-white/40 hover:text-white'
              )}
            >
              <Grid className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* Active Runs Summary */}
      {statusCounts.running > 0 && (
        <div className="flex items-center gap-2 p-3 bg-cyan-500/5 border border-cyan-500/20">
          <div className="w-2 h-2 bg-cyan-500 rounded-full animate-pulse" />
          <span className="text-xs font-mono text-cyan-400">
            {statusCounts.running} run{statusCounts.running > 1 ? 's' : ''} in progress
          </span>
        </div>
      )}

      {/* Loading State */}
      {isLoading && runs.length === 0 && (
        <div className="flex items-center justify-center py-12">
          <div className="flex items-center gap-3 text-white/40">
            <RefreshCw className="w-5 h-5 animate-spin" />
            <span className="text-sm font-mono">Loading runs...</span>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && filteredRuns.length === 0 && (
        <div className="flex flex-col items-center justify-center py-12 border border-white/10 border-dashed">
          <p className="text-sm font-mono text-white/40 mb-4">
            {runs.length === 0 ? 'No runs yet' : 'No runs match your filters'}
          </p>
          {onCreate && runs.length === 0 && (
            <Button variant="primary" size="sm" onClick={onCreate}>
              <Plus className="w-3.5 h-3.5 mr-1" />
              Create First Run
            </Button>
          )}
        </div>
      )}

      {/* Run List/Grid */}
      {filteredRuns.length > 0 && (
        <div
          className={cn(
            view === 'grid'
              ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'
              : 'space-y-2'
          )}
        >
          {filteredRuns.map((run) => (
            <RunCard
              key={run.run_id}
              run={run}
              projectId={projectId}
              onStart={onStartRun}
              onCancel={onCancelRun}
              onDuplicate={onDuplicateRun}
              onDelete={onDeleteRun}
              compact={view === 'list'}
            />
          ))}
        </div>
      )}
    </div>
  );
});

export default RunList;

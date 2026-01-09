'use client';

/**
 * ProjectList Component
 * Filterable list of project specs.
 * Reference: project.md §6.1 (ProjectSpec)
 */

import { memo, useState, useCallback, useMemo } from 'react';
import {
  FolderKanban,
  Search,
  Filter,
  Grid3X3,
  List,
  Plus,
  RefreshCw,
  ChevronDown,
  SortAsc,
  SortDesc,
  Loader2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { ProjectCard } from './ProjectCard';
import { useProjectSpecs } from '@/hooks/useApi';
import type { ProjectSpec } from '@/lib/api';

interface ProjectListProps {
  onProjectSelect?: (projectId: string) => void;
  onCreateProject?: () => void;
  onCreateRun?: (projectId: string) => void;
  onViewMap?: (projectId: string) => void;
  selectedProjectId?: string;
  className?: string;
}

type SortField = 'created_at' | 'updated_at' | 'name' | 'runs_count';
type SortOrder = 'asc' | 'desc';
type StatusFilter = 'all' | 'draft' | 'active' | 'archived';

export const ProjectList = memo(function ProjectList({
  onProjectSelect,
  onCreateProject,
  onCreateRun,
  onViewMap,
  selectedProjectId,
  className,
}: ProjectListProps) {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [sortField, setSortField] = useState<SortField>('updated_at');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [showFilters, setShowFilters] = useState(false);

  // Fetch projects
  const {
    data: projects = [],
    isLoading,
    error,
    refetch,
  } = useProjectSpecs();

  // Filter and sort projects
  const filteredProjects = useMemo(() => {
    let result = [...projects];

    // Search filter
    if (search) {
      const searchLower = search.toLowerCase();
      result = result.filter(
        (p) =>
          p.name.toLowerCase().includes(searchLower) ||
          p.description?.toLowerCase().includes(searchLower)
      );
    }

    // Status filter
    if (statusFilter !== 'all') {
      result = result.filter((p) => {
        if (statusFilter === 'archived') return false; // No archived support in API
        if (statusFilter === 'active') return (p.run_count || 0) > 0;
        if (statusFilter === 'draft') return (p.run_count || 0) === 0;
        return true;
      });
    }

    // Sort
    result.sort((a, b) => {
      let aVal: string | number;
      let bVal: string | number;

      switch (sortField) {
        case 'name':
          aVal = a.name.toLowerCase();
          bVal = b.name.toLowerCase();
          break;
        case 'runs_count':
          aVal = a.run_count || 0;
          bVal = b.run_count || 0;
          break;
        case 'updated_at':
          aVal = new Date(a.updated_at || a.created_at).getTime();
          bVal = new Date(b.updated_at || b.created_at).getTime();
          break;
        default:
          aVal = new Date(a.created_at).getTime();
          bVal = new Date(b.created_at).getTime();
      }

      if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });

    return result;
  }, [projects, search, statusFilter, sortField, sortOrder]);

  // Toggle sort order
  const handleSortChange = useCallback((field: SortField) => {
    if (field === sortField) {
      setSortOrder((o) => (o === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
  }, [sortField]);

  return (
    <div className={cn('flex flex-col', className)}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 bg-black border-b border-white/10">
        <div className="flex items-center gap-3">
          <FolderKanban className="w-5 h-5 text-cyan-400" />
          <div>
            <h2 className="text-lg font-mono font-bold text-white">Projects</h2>
            <p className="text-xs font-mono text-white/40">
              {filteredProjects.length} of {projects.length} projects
            </p>
          </div>
        </div>

        <Button variant="primary" size="sm" onClick={onCreateProject}>
          <Plus className="w-3 h-3 mr-1" />
          New Project
        </Button>
      </div>

      {/* Search & Filters */}
      <div className="p-4 bg-black/50 border-b border-white/10 space-y-3">
        {/* Search */}
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search projects..."
              className="w-full pl-10 pr-4 py-2 text-sm font-mono bg-black border border-white/20 text-white placeholder:text-white/30 focus:border-white/40 focus:outline-none"
            />
          </div>
          <Button
            variant={showFilters ? 'secondary' : 'ghost'}
            size="sm"
            onClick={() => setShowFilters(!showFilters)}
          >
            <Filter className="w-3 h-3 mr-1" />
            Filters
            <ChevronDown
              className={cn('w-3 h-3 ml-1 transition-transform', showFilters && 'rotate-180')}
            />
          </Button>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => refetch()}
            disabled={isLoading}
            title="Refresh"
          >
            <RefreshCw className={cn('w-3.5 h-3.5', isLoading && 'animate-spin')} />
          </Button>
        </div>

        {/* Filter Panel */}
        {showFilters && (
          <div className="flex items-center gap-4 pt-3 border-t border-white/10">
            {/* Status Filter */}
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-white/40">Status:</span>
              <div className="flex items-center bg-white/5 border border-white/10">
                {(['all', 'draft', 'active', 'archived'] as StatusFilter[]).map((status) => (
                  <button
                    key={status}
                    onClick={() => setStatusFilter(status)}
                    className={cn(
                      'px-2 py-1 text-[10px] font-mono uppercase transition-colors',
                      statusFilter === status
                        ? 'bg-white text-black'
                        : 'text-white/60 hover:text-white'
                    )}
                  >
                    {status}
                  </button>
                ))}
              </div>
            </div>

            {/* Sort */}
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-white/40">Sort:</span>
              <div className="flex items-center gap-1">
                {[
                  { field: 'updated_at' as SortField, label: 'Updated' },
                  { field: 'created_at' as SortField, label: 'Created' },
                  { field: 'name' as SortField, label: 'Name' },
                  { field: 'runs_count' as SortField, label: 'Runs' },
                ].map(({ field, label }) => (
                  <button
                    key={field}
                    onClick={() => handleSortChange(field)}
                    className={cn(
                      'flex items-center gap-1 px-2 py-1 text-[10px] font-mono transition-colors',
                      sortField === field
                        ? 'bg-white/10 text-white'
                        : 'text-white/40 hover:text-white/60'
                    )}
                  >
                    {label}
                    {sortField === field &&
                      (sortOrder === 'asc' ? (
                        <SortAsc className="w-2.5 h-2.5" />
                      ) : (
                        <SortDesc className="w-2.5 h-2.5" />
                      ))}
                  </button>
                ))}
              </div>
            </div>

            {/* View Mode */}
            <div className="flex items-center gap-1 ml-auto">
              <Button
                variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
                size="icon-sm"
                onClick={() => setViewMode('grid')}
                title="Grid View"
              >
                <Grid3X3 className="w-3 h-3" />
              </Button>
              <Button
                variant={viewMode === 'list' ? 'secondary' : 'ghost'}
                size="icon-sm"
                onClick={() => setViewMode('list')}
                title="List View"
              >
                <List className="w-3 h-3" />
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Project List */}
      <div className="flex-1 overflow-y-auto p-4">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="flex items-center gap-3 text-white/40">
              <Loader2 className="w-5 h-5 animate-spin" />
              <span className="text-sm font-mono">Loading projects...</span>
            </div>
          </div>
        ) : error ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <FolderKanban className="w-8 h-8 text-red-400/50 mx-auto mb-3" />
              <p className="text-sm font-mono text-red-400">Failed to load projects</p>
              <Button variant="secondary" size="sm" onClick={() => refetch()} className="mt-3">
                Retry
              </Button>
            </div>
          </div>
        ) : filteredProjects.length === 0 ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <FolderKanban className="w-8 h-8 text-white/20 mx-auto mb-3" />
              <p className="text-sm font-mono text-white/40 mb-2">
                {projects.length === 0 ? 'No projects yet' : 'No matching projects'}
              </p>
              {projects.length === 0 && (
                <Button variant="primary" size="sm" onClick={onCreateProject}>
                  <Plus className="w-3 h-3 mr-1" />
                  Create First Project
                </Button>
              )}
            </div>
          </div>
        ) : viewMode === 'grid' ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredProjects.map((project) => (
              <ProjectCard
                key={project.id}
                project={project}
                isSelected={project.id === selectedProjectId}
                onSelect={onProjectSelect}
                onCreateRun={onCreateRun}
                onViewMap={onViewMap}
              />
            ))}
          </div>
        ) : (
          <div className="space-y-2">
            {filteredProjects.map((project) => (
              <ProjectCard
                key={project.id}
                project={project}
                isSelected={project.id === selectedProjectId}
                onSelect={onProjectSelect}
                compact
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
});

export default ProjectList;

'use client';

/**
 * Project List Page
 *
 * Slice 2-0 Hotfix Updates:
 * 1. Cross-tab sync via invalidation bus
 * 2. Dropdown menu uses Radix Portal (no clipping)
 * 3. Proper draft cleanup on publish (same project_id, no duplicates)
 */

import { useState, useCallback } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';
import {
  Plus,
  FolderKanban,
  MoreVertical,
  Search,
  Terminal,
  ExternalLink,
  Pencil,
  Copy,
  Archive,
  Trash2,
  X,
  CheckCircle,
  XCircle,
  Clock,
  Users,
  Target,
  Layers,
  Loader2,
  AlertTriangle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  useProjectSpecs,
  useUpdateProjectSpec,
  useDuplicateProjectSpec,
  useDeleteProjectSpec,
} from '@/hooks/useApi';
import { useProjectsInvalidation, useInvalidationEmit } from '@/hooks/useInvalidationBus';
import type { ProjectSpec } from '@/lib/api';

type CoreType = 'collective' | 'target' | 'hybrid';
type ProjectStatus = 'DRAFT' | 'ACTIVE' | 'ARCHIVED';
type RunStatus = 'success' | 'failed' | 'running' | null;

// Extended project type that combines API data with UI needs
interface ProjectView {
  id: string;
  name: string;
  description?: string;
  domain: string;
  coreType: CoreType;
  status: ProjectStatus;
  lastUpdated: string;
  lastRunStatus: RunStatus;
  nodeCount: number;
  runCount: number;
  tags: string[];
  isDraft: boolean;
}

// Map domain to core type (best guess based on domain name)
function deriveCoreType(domain: string): CoreType {
  const d = domain.toLowerCase();
  if (d.includes('target') || d.includes('planner') || d.includes('individual')) {
    return 'target';
  }
  if (d.includes('hybrid') || d.includes('combined') || d.includes('mixed')) {
    return 'hybrid';
  }
  return 'collective'; // default
}

// Transform API ProjectSpec to UI ProjectView
function transformProjectSpec(spec: ProjectSpec): ProjectView {
  // Slice 1C: Use actual status from API, default to ACTIVE for backwards compatibility
  const status = (spec.status as ProjectStatus) || 'ACTIVE';
  return {
    id: spec.id,
    name: spec.name,
    description: spec.description,
    domain: spec.domain,
    coreType: deriveCoreType(spec.domain),
    status,
    lastUpdated: spec.updated_at,
    lastRunStatus: spec.run_count > 0 ? 'success' : null, // Simplified - real impl would check actual run status
    nodeCount: spec.node_count,
    runCount: spec.run_count,
    tags: spec.domain ? [spec.domain] : [],
    isDraft: status === 'DRAFT',
  };
}

const coreTypeConfig: Record<CoreType, { label: string; icon: React.ElementType; color: string }> = {
  collective: { label: 'Collective', icon: Users, color: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30' },
  target: { label: 'Target', icon: Target, color: 'bg-purple-500/20 text-purple-400 border-purple-500/30' },
  hybrid: { label: 'Hybrid', icon: Layers, color: 'bg-amber-500/20 text-amber-400 border-amber-500/30' },
};

const runStatusConfig: Record<string, { label: string; icon: React.ElementType; color: string }> = {
  success: { label: 'Success', icon: CheckCircle, color: 'text-green-400' },
  failed: { label: 'Failed', icon: XCircle, color: 'text-red-400' },
  running: { label: 'Running', icon: Loader2, color: 'text-cyan-400' },
  none: { label: 'None', icon: Clock, color: 'text-white/30' },
};

export default function ProjectsPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<ProjectStatus | ''>('');
  const [coreFilter, setCoreFilter] = useState<CoreType | ''>('');

  // Use real API data
  const { data: projectSpecs, isLoading, error, refetch } = useProjectSpecs({
    search: searchQuery || undefined,
  });

  // Slice 2-0: Cross-tab sync - auto-revalidate on invalidation events
  useProjectsInvalidation(refetch);

  // Slice 2-0: Emit invalidation events on mutations
  const { emitProjectsDeleted, emitProjectsUpdated, emitProjectsCreated } = useInvalidationEmit();

  // Mutations
  const updateProject = useUpdateProjectSpec();
  const duplicateProject = useDuplicateProjectSpec();
  const deleteProject = useDeleteProjectSpec();

  // Modal states
  const [renameModal, setRenameModal] = useState<{ open: boolean; project: ProjectView | null }>({ open: false, project: null });
  const [duplicateModal, setDuplicateModal] = useState<{ open: boolean; project: ProjectView | null }>({ open: false, project: null });
  const [archiveModal, setArchiveModal] = useState<{ open: boolean; project: ProjectView | null }>({ open: false, project: null });
  const [deleteModal, setDeleteModal] = useState<{ open: boolean; project: ProjectView | null }>({ open: false, project: null });
  const [newName, setNewName] = useState('');

  // Transform API data to UI format
  const projects: ProjectView[] = (projectSpecs || []).map(transformProjectSpec);

  // Filter projects
  const filteredProjects = projects.filter(project => {
    const matchesSearch = !searchQuery ||
      project.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      project.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchesStatus = !statusFilter || project.status === statusFilter;
    const matchesCore = !coreFilter || project.coreType === coreFilter;
    return matchesSearch && matchesStatus && matchesCore;
  });

  // Action handlers - use real API mutations
  const handleRename = useCallback(async () => {
    if (renameModal.project && newName.trim()) {
      try {
        await updateProject.mutateAsync({
          projectId: renameModal.project.id,
          data: { name: newName.trim() }
        });
        // Slice 2-0: Emit invalidation for cross-tab sync
        emitProjectsUpdated([renameModal.project.id]);
        setRenameModal({ open: false, project: null });
        setNewName('');
      } catch {
        // Error handled by React Query
      }
    }
  }, [renameModal.project, newName, updateProject, emitProjectsUpdated]);

  const handleDuplicate = useCallback(async () => {
    if (duplicateModal.project) {
      try {
        const result = await duplicateProject.mutateAsync({
          projectId: duplicateModal.project.id,
          newName: `${duplicateModal.project.name} (Copy)`
        });
        // Slice 2-0: Emit invalidation for cross-tab sync
        emitProjectsCreated([result.id]);
        setDuplicateModal({ open: false, project: null });
      } catch {
        // Error handled by React Query
      }
    }
  }, [duplicateModal.project, duplicateProject, emitProjectsCreated]);

  const handleArchive = useCallback(() => {
    // Archive functionality not yet in API - show coming soon
    if (archiveModal.project) {
      setArchiveModal({ open: false, project: null });
    }
  }, [archiveModal.project]);

  const handleDelete = useCallback(async () => {
    if (deleteModal.project) {
      const projectId = deleteModal.project.id;
      try {
        await deleteProject.mutateAsync(projectId);
        // Slice 2-0: Emit invalidation for cross-tab sync
        emitProjectsDeleted([projectId]);
        setDeleteModal({ open: false, project: null });
      } catch {
        // Error handled by React Query
      }
    }
  }, [deleteModal.project, deleteProject, emitProjectsDeleted]);

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-black p-4 md:p-6 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-cyan-400 animate-spin mx-auto mb-4" />
          <p className="text-sm font-mono text-white/60">Loading projects...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="min-h-screen bg-black p-4 md:p-6 flex items-center justify-center">
        <div className="text-center max-w-md">
          <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-4" />
          <p className="text-sm font-mono text-white/60 mb-4">Failed to load projects</p>
          <Button size="sm" onClick={() => refetch()}>
            Try Again
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black p-4 md:p-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-xl md:text-2xl font-mono font-bold text-white">Projects</h1>
          <p className="text-xs md:text-sm font-mono text-white/50 mt-1">
            Manage your prediction projects
          </p>
        </div>
        <Link href="/dashboard/projects/new">
          <Button size="sm" className="w-full sm:w-auto">
            <Plus className="w-3.5 h-3.5 mr-2" />
            New Project
          </Button>
        </Link>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2 md:gap-3 mb-6">
        <div className="relative flex-1 min-w-[150px] max-w-xs">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-white/30" />
          <input
            type="text"
            placeholder="Search projects..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-3 py-2 bg-white/5 border border-white/10 text-xs font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/30"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as ProjectStatus | '')}
          className="px-3 py-2 bg-white/5 border border-white/10 text-xs font-mono text-white appearance-none focus:outline-none focus:border-white/30 cursor-pointer"
        >
          <option value="">All Status</option>
          <option value="DRAFT">Draft</option>
          <option value="ACTIVE">Active</option>
          <option value="ARCHIVED">Archived</option>
        </select>
        <select
          value={coreFilter}
          onChange={(e) => setCoreFilter(e.target.value as CoreType | '')}
          className="px-3 py-2 bg-white/5 border border-white/10 text-xs font-mono text-white appearance-none focus:outline-none focus:border-white/30 cursor-pointer"
        >
          <option value="">All Cores</option>
          <option value="collective">Collective</option>
          <option value="target">Target</option>
          <option value="hybrid">Hybrid</option>
        </select>
      </div>

      {/* Projects List */}
      {filteredProjects.length === 0 ? (
        <EmptyState hasProjects={projects.length > 0} />
      ) : (
        <div className="bg-white/5 border border-white/10 overflow-hidden">
          {/* Table Header - Desktop */}
          <div className="hidden md:grid md:grid-cols-[1fr,120px,120px,100px,80px,100px] gap-4 px-4 py-3 border-b border-white/10 bg-white/5">
            <span className="text-[10px] font-mono text-white/40 uppercase tracking-wider">Project</span>
            <span className="text-[10px] font-mono text-white/40 uppercase tracking-wider">Core</span>
            <span className="text-[10px] font-mono text-white/40 uppercase tracking-wider">Last Updated</span>
            <span className="text-[10px] font-mono text-white/40 uppercase tracking-wider">Runs</span>
            <span className="text-[10px] font-mono text-white/40 uppercase tracking-wider">Nodes</span>
            <span className="text-[10px] font-mono text-white/40 uppercase tracking-wider text-right">Actions</span>
          </div>

          {/* Project Rows */}
          <div className="divide-y divide-white/5">
            {filteredProjects.map((project) => (
              <ProjectRow
                key={project.id}
                project={project}
                onRename={() => { setRenameModal({ open: true, project }); setNewName(project.name); }}
                onDuplicate={() => setDuplicateModal({ open: true, project })}
                onArchive={() => setArchiveModal({ open: true, project })}
                onDelete={() => setDeleteModal({ open: true, project })}
              />
            ))}
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="mt-6 pt-4 border-t border-white/5">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-1">
            <Terminal className="w-3 h-3" />
            <span>PROJECTS MODULE</span>
          </div>
          <span>{filteredProjects.length} of {projects.length} projects</span>
        </div>
      </div>

      {/* Rename Modal */}
      {renameModal.open && (
        <Modal
          title="Rename Project"
          onClose={() => { setRenameModal({ open: false, project: null }); setNewName(''); }}
        >
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-mono text-white/60 mb-2">Project Name</label>
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                className="w-full px-3 py-2 bg-white/5 border border-white/20 text-sm font-mono text-white focus:outline-none focus:border-white/40"
                autoFocus
              />
            </div>
            <div className="flex gap-2 justify-end">
              <Button variant="outline" size="sm" onClick={() => { setRenameModal({ open: false, project: null }); setNewName(''); }}>
                Cancel
              </Button>
              <Button size="sm" onClick={handleRename} disabled={!newName.trim() || updateProject.isPending}>
                {updateProject.isPending ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : null}
                Save
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Duplicate Modal */}
      {duplicateModal.open && duplicateModal.project && (
        <Modal
          title="Duplicate Project"
          onClose={() => setDuplicateModal({ open: false, project: null })}
        >
          <div className="space-y-4">
            <p className="text-sm font-mono text-white/60">
              Create a copy of <span className="text-white">&quot;{duplicateModal.project.name}&quot;</span>?
            </p>
            <p className="text-xs font-mono text-white/40">
              The new project will have no run history.
            </p>
            <div className="flex gap-2 justify-end">
              <Button variant="outline" size="sm" onClick={() => setDuplicateModal({ open: false, project: null })}>
                Cancel
              </Button>
              <Button size="sm" onClick={handleDuplicate} disabled={duplicateProject.isPending}>
                {duplicateProject.isPending ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : null}
                Duplicate
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Archive Modal */}
      {archiveModal.open && archiveModal.project && (
        <Modal
          title={archiveModal.project.status === 'ACTIVE' ? 'Archive Project' : 'Restore Project'}
          onClose={() => setArchiveModal({ open: false, project: null })}
        >
          <div className="space-y-4">
            <p className="text-sm font-mono text-white/60">
              {archiveModal.project.status === 'ACTIVE'
                ? <>Archive <span className="text-white">&quot;{archiveModal.project.name}&quot;</span>?</>
                : <>Restore <span className="text-white">&quot;{archiveModal.project.name}&quot;</span> to active projects?</>
              }
            </p>
            <p className="text-xs font-mono text-yellow-400/60">
              Archive functionality coming soon.
            </p>
            <div className="flex gap-2 justify-end">
              <Button variant="outline" size="sm" onClick={() => setArchiveModal({ open: false, project: null })}>
                Close
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Delete Modal */}
      {deleteModal.open && deleteModal.project && (
        <Modal
          title="Delete Project"
          onClose={() => setDeleteModal({ open: false, project: null })}
          danger
        >
          <div className="space-y-4">
            <p className="text-sm font-mono text-white/60">
              Are you sure you want to delete <span className="text-white">&quot;{deleteModal.project.name}&quot;</span>?
            </p>
            <p className="text-xs font-mono text-red-400">
              This action cannot be undone. All data will be permanently lost.
            </p>
            <div className="flex gap-2 justify-end">
              <Button variant="outline" size="sm" onClick={() => setDeleteModal({ open: false, project: null })}>
                Cancel
              </Button>
              <Button size="sm" variant="destructive" onClick={handleDelete} disabled={deleteProject.isPending}>
                {deleteProject.isPending ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : null}
                Delete Project
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

function ProjectRow({
  project,
  onRename,
  onDuplicate,
  onArchive,
  onDelete
}: {
  project: ProjectView;
  onRename: () => void;
  onDuplicate: () => void;
  onArchive: () => void;
  onDelete: () => void;
}) {
  const core = coreTypeConfig[project.coreType];
  const runStatus = project.lastRunStatus ? runStatusConfig[project.lastRunStatus] : runStatusConfig.none;
  const CoreIcon = core.icon;
  const StatusIcon = runStatus.icon;

  return (
    <div className="group hover:bg-white/[0.03] transition-colors">
      {/* Desktop View */}
      <div className="hidden md:grid md:grid-cols-[1fr,120px,120px,100px,80px,100px] gap-4 px-4 py-3 items-center">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-8 h-8 bg-white/5 flex items-center justify-center flex-shrink-0">
            <FolderKanban className="w-4 h-4 text-white/40" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-mono font-medium text-white truncate">{project.name}</h3>
              {/* Slice 1C: Draft badge */}
              {project.isDraft && (
                <span className="px-1.5 py-0.5 text-[9px] font-mono uppercase bg-amber-500/20 text-amber-400 border border-amber-500/30">
                  Draft
                </span>
              )}
            </div>
            <div className="flex gap-1 mt-0.5">
              {project.tags.slice(0, 2).map(tag => (
                <span key={tag} className="text-[9px] font-mono text-white/30 uppercase">{tag}</span>
              ))}
            </div>
          </div>
        </div>
        <div>
          <span className={cn('inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-mono uppercase border', core.color)}>
            <CoreIcon className="w-2.5 h-2.5" />
            {core.label}
          </span>
        </div>
        <div className="text-xs font-mono text-white/50">
          {new Date(project.lastUpdated).toLocaleDateString()}
        </div>
        <div className="flex items-center gap-1">
          <span className="text-xs font-mono text-white">{project.runCount}</span>
          {project.runCount > 0 && (
            <StatusIcon className={cn('w-3 h-3', runStatus.color)} />
          )}
        </div>
        <div className="text-xs font-mono text-white">
          {project.nodeCount}
        </div>
        <div className="flex items-center justify-end gap-2">
          {/* Slice 1C: Draft projects go to wizard, active projects go to overview */}
          <Link href={project.isDraft ? `/dashboard/projects/new?resume=${project.id}` : `/p/${project.id}/overview`}>
            <Button variant="outline" size="sm" className="h-7 px-2 text-[10px]">
              <ExternalLink className="w-3 h-3 mr-1" />
              {project.isDraft ? 'Resume' : 'Open'}
            </Button>
          </Link>
          {/* Slice 2-0: Use Radix DropdownMenu with portal to prevent clipping */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                className="p-1.5 hover:bg-white/10 transition-colors focus:outline-none focus:bg-white/10"
                aria-label="Project actions"
              >
                <MoreVertical className="w-3.5 h-3.5 text-white/40" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={onRename}>
                <Pencil className="w-3 h-3 mr-2" />
                Rename
              </DropdownMenuItem>
              <DropdownMenuItem onClick={onDuplicate}>
                <Copy className="w-3 h-3 mr-2" />
                Duplicate
              </DropdownMenuItem>
              <DropdownMenuItem onClick={onArchive}>
                <Archive className="w-3 h-3 mr-2" />
                {project.status === 'ACTIVE' ? 'Archive' : 'Restore'}
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={onDelete} destructive>
                <Trash2 className="w-3 h-3 mr-2" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Mobile View */}
      <div className="md:hidden p-3">
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-7 h-7 bg-white/5 flex items-center justify-center flex-shrink-0">
              <FolderKanban className="w-3.5 h-3.5 text-white/40" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-1.5">
                <h3 className="text-xs font-mono font-medium text-white truncate">{project.name}</h3>
                {/* Slice 1C: Draft badge (mobile) */}
                {project.isDraft && (
                  <span className="px-1 py-0.5 text-[8px] font-mono uppercase bg-amber-500/20 text-amber-400 border border-amber-500/30">
                    Draft
                  </span>
                )}
              </div>
              <span className={cn('inline-flex items-center gap-1 px-1 py-0.5 text-[9px] font-mono uppercase border mt-1', core.color)}>
                <CoreIcon className="w-2 h-2" />
                {core.label}
              </span>
            </div>
          </div>
          {/* Slice 2-0: Mobile dropdown with portal */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                className="p-1 hover:bg-white/10 transition-colors focus:outline-none focus:bg-white/10"
                aria-label="Project actions"
              >
                <MoreVertical className="w-3 h-3 text-white/40" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={onRename}>
                <Pencil className="w-3 h-3 mr-2" />
                Rename
              </DropdownMenuItem>
              <DropdownMenuItem onClick={onDuplicate}>
                <Copy className="w-3 h-3 mr-2" />
                Duplicate
              </DropdownMenuItem>
              <DropdownMenuItem onClick={onArchive}>
                <Archive className="w-3 h-3 mr-2" />
                {project.status === 'ACTIVE' ? 'Archive' : 'Restore'}
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={onDelete} destructive>
                <Trash2 className="w-3 h-3 mr-2" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        <div className="grid grid-cols-3 gap-2 text-[9px] font-mono mb-2">
          <div>
            <span className="text-white/30">Updated</span>
            <p className="text-white/50">{new Date(project.lastUpdated).toLocaleDateString()}</p>
          </div>
          <div>
            <span className="text-white/30">Runs</span>
            <p className="text-white">{project.runCount}</p>
          </div>
          <div>
            <span className="text-white/30">Nodes</span>
            <p className="text-white">{project.nodeCount}</p>
          </div>
        </div>
        {/* Slice 1C: Draft projects go to wizard, active projects go to overview */}
        <Link href={project.isDraft ? `/dashboard/projects/new?resume=${project.id}` : `/p/${project.id}/overview`}>
          <Button variant="outline" size="sm" className="w-full h-7 text-[10px]">
            <ExternalLink className="w-3 h-3 mr-1" />
            {project.isDraft ? 'Resume Draft' : 'Open Project'}
          </Button>
        </Link>
      </div>
    </div>
  );
}

function EmptyState({ hasProjects }: { hasProjects: boolean }) {
  return (
    <div className="bg-white/5 border border-white/10">
      <div className="p-12 text-center">
        <div className="w-12 h-12 bg-white/5 flex items-center justify-center mx-auto mb-4">
          <FolderKanban className="w-6 h-6 text-white/30" />
        </div>
        {hasProjects ? (
          <>
            <p className="text-sm font-mono text-white/60 mb-1">No matching projects</p>
            <p className="text-xs font-mono text-white/30">Try adjusting your search or filters</p>
          </>
        ) : (
          <>
            <p className="text-sm font-mono text-white/60 mb-1">No projects yet</p>
            <p className="text-xs font-mono text-white/30 mb-4">
              Create your first project to start making predictions
            </p>
            <Link href="/dashboard/projects/new">
              <Button size="sm">
                <Plus className="w-3.5 h-3.5 mr-2" />
                Create your first project
              </Button>
            </Link>
          </>
        )}
      </div>
    </div>
  );
}

function Modal({
  title,
  children,
  onClose,
  danger = false
}: {
  title: string;
  children: React.ReactNode;
  onClose: () => void;
  danger?: boolean;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-md bg-black border border-white/20 shadow-2xl">
        <div className={cn('flex items-center justify-between px-4 py-3 border-b', danger ? 'border-red-500/30' : 'border-white/10')}>
          <h2 className={cn('text-sm font-mono font-bold', danger ? 'text-red-400' : 'text-white')}>{title}</h2>
          <button onClick={onClose} className="p-1 hover:bg-white/10 transition-colors">
            <X className="w-4 h-4 text-white/40" />
          </button>
        </div>
        <div className="p-4">
          {children}
        </div>
      </div>
    </div>
  );
}

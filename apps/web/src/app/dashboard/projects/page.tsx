'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
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
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Mock data for projects
const mockProjects = [
  {
    id: 'proj_001',
    name: 'GE2026 Malaysia Election Analysis',
    coreType: 'collective' as const,
    status: 'active' as const,
    lastUpdated: '2026-01-10T14:30:00Z',
    lastRunStatus: 'success' as const,
    reliability: 87,
    tags: ['politics', 'malaysia'],
  },
  {
    id: 'proj_002',
    name: 'Nike Campaign Backlash Risk',
    coreType: 'target' as const,
    status: 'active' as const,
    lastUpdated: '2026-01-08T09:15:00Z',
    lastRunStatus: 'failed' as const,
    reliability: 62,
    tags: ['marketing', 'brand'],
  },
  {
    id: 'proj_003',
    name: 'Inflation Policy Impact Study',
    coreType: 'hybrid' as const,
    status: 'active' as const,
    lastUpdated: '2026-01-05T16:45:00Z',
    lastRunStatus: null,
    reliability: null,
    tags: ['economics', 'policy'],
  },
  {
    id: 'proj_004',
    name: 'Q4 Product Launch Sentiment',
    coreType: 'collective' as const,
    status: 'archived' as const,
    lastUpdated: '2025-12-20T11:00:00Z',
    lastRunStatus: 'success' as const,
    reliability: 91,
    tags: ['product'],
  },
];

type CoreType = 'collective' | 'target' | 'hybrid';
type ProjectStatus = 'active' | 'archived';
type RunStatus = 'success' | 'failed' | null;

interface Project {
  id: string;
  name: string;
  coreType: CoreType;
  status: ProjectStatus;
  lastUpdated: string;
  lastRunStatus: RunStatus;
  reliability: number | null;
  tags: string[];
}

const coreTypeConfig: Record<CoreType, { label: string; icon: React.ElementType; color: string }> = {
  collective: { label: 'Collective', icon: Users, color: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30' },
  target: { label: 'Target', icon: Target, color: 'bg-purple-500/20 text-purple-400 border-purple-500/30' },
  hybrid: { label: 'Hybrid', icon: Layers, color: 'bg-amber-500/20 text-amber-400 border-amber-500/30' },
};

const runStatusConfig: Record<string, { label: string; icon: React.ElementType; color: string }> = {
  success: { label: 'Success', icon: CheckCircle, color: 'text-green-400' },
  failed: { label: 'Failed', icon: XCircle, color: 'text-red-400' },
  none: { label: 'None', icon: Clock, color: 'text-white/30' },
};

export default function ProjectsPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<ProjectStatus | ''>('');
  const [coreFilter, setCoreFilter] = useState<CoreType | ''>('');
  const [projects, setProjects] = useState<Project[]>(mockProjects);

  // Modal states
  const [renameModal, setRenameModal] = useState<{ open: boolean; project: Project | null }>({ open: false, project: null });
  const [duplicateModal, setDuplicateModal] = useState<{ open: boolean; project: Project | null }>({ open: false, project: null });
  const [archiveModal, setArchiveModal] = useState<{ open: boolean; project: Project | null }>({ open: false, project: null });
  const [deleteModal, setDeleteModal] = useState<{ open: boolean; project: Project | null }>({ open: false, project: null });
  const [newName, setNewName] = useState('');

  // Filter projects
  const filteredProjects = projects.filter(project => {
    const matchesSearch = !searchQuery ||
      project.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      project.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchesStatus = !statusFilter || project.status === statusFilter;
    const matchesCore = !coreFilter || project.coreType === coreFilter;
    return matchesSearch && matchesStatus && matchesCore;
  });

  // Action handlers
  const handleRename = () => {
    if (renameModal.project && newName.trim()) {
      setProjects(prev => prev.map(p =>
        p.id === renameModal.project!.id ? { ...p, name: newName.trim() } : p
      ));
      setRenameModal({ open: false, project: null });
      setNewName('');
    }
  };

  const handleDuplicate = () => {
    if (duplicateModal.project) {
      const newProject: Project = {
        ...duplicateModal.project,
        id: `proj_${Date.now()}`,
        name: `${duplicateModal.project.name} (Copy)`,
        lastUpdated: new Date().toISOString(),
        lastRunStatus: null,
        reliability: null,
      };
      setProjects(prev => [newProject, ...prev]);
      setDuplicateModal({ open: false, project: null });
    }
  };

  const handleArchive = () => {
    if (archiveModal.project) {
      setProjects(prev => prev.map(p =>
        p.id === archiveModal.project!.id
          ? { ...p, status: p.status === 'active' ? 'archived' : 'active' }
          : p
      ));
      setArchiveModal({ open: false, project: null });
    }
  };

  const handleDelete = () => {
    if (deleteModal.project) {
      setProjects(prev => prev.filter(p => p.id !== deleteModal.project!.id));
      setDeleteModal({ open: false, project: null });
    }
  };

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
          <option value="active">Active</option>
          <option value="archived">Archived</option>
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
            <span className="text-[10px] font-mono text-white/40 uppercase tracking-wider">Last Run</span>
            <span className="text-[10px] font-mono text-white/40 uppercase tracking-wider">Reliability</span>
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
              <Button size="sm" onClick={handleRename} disabled={!newName.trim()}>
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
              <Button size="sm" onClick={handleDuplicate}>
                Duplicate
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Archive Modal */}
      {archiveModal.open && archiveModal.project && (
        <Modal
          title={archiveModal.project.status === 'active' ? 'Archive Project' : 'Restore Project'}
          onClose={() => setArchiveModal({ open: false, project: null })}
        >
          <div className="space-y-4">
            <p className="text-sm font-mono text-white/60">
              {archiveModal.project.status === 'active'
                ? <>Archive <span className="text-white">&quot;{archiveModal.project.name}&quot;</span>?</>
                : <>Restore <span className="text-white">&quot;{archiveModal.project.name}&quot;</span> to active projects?</>
              }
            </p>
            <div className="flex gap-2 justify-end">
              <Button variant="outline" size="sm" onClick={() => setArchiveModal({ open: false, project: null })}>
                Cancel
              </Button>
              <Button size="sm" onClick={handleArchive}>
                {archiveModal.project.status === 'active' ? 'Archive' : 'Restore'}
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
              <Button size="sm" variant="destructive" onClick={handleDelete}>
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
  project: Project;
  onRename: () => void;
  onDuplicate: () => void;
  onArchive: () => void;
  onDelete: () => void;
}) {
  const [showMenu, setShowMenu] = useState(false);
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
            <h3 className="text-sm font-mono font-medium text-white truncate">{project.name}</h3>
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
          <StatusIcon className={cn('w-3 h-3', runStatus.color)} />
          <span className={cn('text-xs font-mono', runStatus.color)}>{runStatus.label}</span>
        </div>
        <div className="text-xs font-mono text-white">
          {project.reliability !== null ? `${project.reliability}%` : '—'}
        </div>
        <div className="flex items-center justify-end gap-2">
          <Link href={`/p/${project.id}/overview`}>
            <Button variant="outline" size="sm" className="h-7 px-2 text-[10px]">
              <ExternalLink className="w-3 h-3 mr-1" />
              Open
            </Button>
          </Link>
          <div className="relative">
            <button
              onClick={() => setShowMenu(!showMenu)}
              className="p-1.5 hover:bg-white/10 transition-colors"
            >
              <MoreVertical className="w-3.5 h-3.5 text-white/40" />
            </button>
            {showMenu && (
              <ActionMenu
                project={project}
                onClose={() => setShowMenu(false)}
                onRename={onRename}
                onDuplicate={onDuplicate}
                onArchive={onArchive}
                onDelete={onDelete}
              />
            )}
          </div>
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
              <h3 className="text-xs font-mono font-medium text-white truncate">{project.name}</h3>
              <span className={cn('inline-flex items-center gap-1 px-1 py-0.5 text-[9px] font-mono uppercase border mt-1', core.color)}>
                <CoreIcon className="w-2 h-2" />
                {core.label}
              </span>
            </div>
          </div>
          <div className="relative">
            <button
              onClick={() => setShowMenu(!showMenu)}
              className="p-1 hover:bg-white/10 transition-colors"
            >
              <MoreVertical className="w-3 h-3 text-white/40" />
            </button>
            {showMenu && (
              <ActionMenu
                project={project}
                onClose={() => setShowMenu(false)}
                onRename={onRename}
                onDuplicate={onDuplicate}
                onArchive={onArchive}
                onDelete={onDelete}
              />
            )}
          </div>
        </div>
        <div className="grid grid-cols-3 gap-2 text-[9px] font-mono mb-2">
          <div>
            <span className="text-white/30">Updated</span>
            <p className="text-white/50">{new Date(project.lastUpdated).toLocaleDateString()}</p>
          </div>
          <div>
            <span className="text-white/30">Last Run</span>
            <div className="flex items-center gap-1">
              <StatusIcon className={cn('w-2.5 h-2.5', runStatus.color)} />
              <span className={runStatus.color}>{runStatus.label}</span>
            </div>
          </div>
          <div>
            <span className="text-white/30">Reliability</span>
            <p className="text-white">{project.reliability !== null ? `${project.reliability}%` : '—'}</p>
          </div>
        </div>
        <Link href={`/p/${project.id}/overview`}>
          <Button variant="outline" size="sm" className="w-full h-7 text-[10px]">
            <ExternalLink className="w-3 h-3 mr-1" />
            Open Project
          </Button>
        </Link>
      </div>
    </div>
  );
}

function ActionMenu({
  project,
  onClose,
  onRename,
  onDuplicate,
  onArchive,
  onDelete
}: {
  project: Project;
  onClose: () => void;
  onRename: () => void;
  onDuplicate: () => void;
  onArchive: () => void;
  onDelete: () => void;
}) {
  return (
    <>
      <div className="fixed inset-0 z-10" onClick={onClose} />
      <div className="absolute right-0 mt-1 w-36 bg-black border border-white/20 py-1 z-20">
        <button
          onClick={() => { onClose(); onRename(); }}
          className="flex items-center gap-2 w-full px-3 py-1.5 text-xs font-mono text-white/60 hover:bg-white/10"
        >
          <Pencil className="w-3 h-3" />
          Rename
        </button>
        <button
          onClick={() => { onClose(); onDuplicate(); }}
          className="flex items-center gap-2 w-full px-3 py-1.5 text-xs font-mono text-white/60 hover:bg-white/10"
        >
          <Copy className="w-3 h-3" />
          Duplicate
        </button>
        <button
          onClick={() => { onClose(); onArchive(); }}
          className="flex items-center gap-2 w-full px-3 py-1.5 text-xs font-mono text-white/60 hover:bg-white/10"
        >
          <Archive className="w-3 h-3" />
          {project.status === 'active' ? 'Archive' : 'Restore'}
        </button>
        <div className="border-t border-white/10 my-1" />
        <button
          onClick={() => { onClose(); onDelete(); }}
          className="flex items-center gap-2 w-full px-3 py-1.5 text-xs font-mono text-red-400 hover:bg-red-500/10"
        >
          <Trash2 className="w-3 h-3" />
          Delete
        </button>
      </div>
    </>
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

'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  Plus,
  FolderKanban,
  MoreVertical,
  Play,
  Trash2,
  Eye,
  Search,
  Loader2,
  Copy,
  Terminal,
} from 'lucide-react';
import { useProjects, useDeleteProject, useDuplicateProject } from '@/hooks/useApi';
import { Project } from '@/lib/api';

export default function ProjectsPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const { data: projects, isLoading, error, refetch } = useProjects({ search: searchQuery || undefined });

  return (
    <div className="min-h-screen bg-black p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <FolderKanban className="w-4 h-4 text-white/60" />
            <span className="text-xs font-mono text-white/40 uppercase tracking-wider">Project Module</span>
          </div>
          <h1 className="text-xl font-mono font-bold text-white">Projects</h1>
          <p className="text-sm font-mono text-white/50 mt-1">
            Manage simulation projects
          </p>
        </div>
        <Link href="/dashboard/projects/new">
          <Button size="sm">
            <Plus className="w-3 h-3 mr-2" />
            NEW PROJECT
          </Button>
        </Link>
      </div>

      {/* Search */}
      <div className="mb-6">
        <div className="relative max-w-xs">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-white/30" />
          <input
            type="text"
            placeholder="Search..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-7 pr-3 py-1.5 bg-white/5 border border-white/10 text-xs font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/30"
          />
        </div>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-4 h-4 animate-spin text-white/40" />
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 p-4">
          <p className="text-sm font-mono text-red-400">Failed to load projects</p>
          <Button
            variant="outline"
            onClick={() => refetch()}
            className="mt-2 font-mono text-xs border-white/20 text-white/60 hover:bg-white/5"
          >
            RETRY
          </Button>
        </div>
      )}

      {/* Projects List */}
      {!isLoading && !error && (
        <>
          {(!projects || projects.length === 0) ? (
            <div className="bg-white/5 border border-white/10">
              <div className="p-12 text-center">
                <div className="w-12 h-12 bg-white/5 flex items-center justify-center mx-auto mb-4">
                  <FolderKanban className="w-5 h-5 text-white/30" />
                </div>
                <p className="text-sm font-mono text-white/60 mb-1">No projects</p>
                <p className="text-xs font-mono text-white/30 mb-4">
                  Create your first project
                </p>
                <Link href="/dashboard/projects/new">
                  <Button size="sm">
                    CREATE PROJECT
                  </Button>
                </Link>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {projects.map((project) => (
                <ProjectCard key={project.id} project={project} onDelete={() => refetch()} />
              ))}
            </div>
          )}
        </>
      )}

      {/* Footer Status */}
      <div className="mt-8 pt-4 border-t border-white/5">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1">
              <Terminal className="w-3 h-3" />
              <span>PROJECT MODULE</span>
            </div>
          </div>
          <span>AGENTVERSE v1.0.0</span>
        </div>
      </div>
    </div>
  );
}

function ProjectCard({ project, onDelete }: { project: Project; onDelete: () => void }) {
  const [showMenu, setShowMenu] = useState(false);
  const deleteProject = useDeleteProject();
  const duplicateProject = useDuplicateProject();

  const handleDelete = async () => {
    if (confirm('Delete this project?')) {
      try {
        await deleteProject.mutateAsync(project.id);
        onDelete();
      } catch {
        // Delete failed - mutation error is handled by react-query
      }
    }
    setShowMenu(false);
  };

  const handleDuplicate = async () => {
    try {
      await duplicateProject.mutateAsync({ projectId: project.id });
      onDelete(); // Refresh the list
    } catch {
      // Duplicate failed - mutation error is handled by react-query
    }
    setShowMenu(false);
  };

  return (
    <div className="bg-white/5 border border-white/10 hover:bg-white/[0.07] hover:border-white/20 transition-all">
      <div className="p-4">
        <div className="flex items-start justify-between mb-3">
          <div className="w-8 h-8 bg-white/5 flex items-center justify-center">
            <FolderKanban className="w-4 h-4 text-white/60" />
          </div>
          <div className="relative">
            <button
              onClick={() => setShowMenu(!showMenu)}
              className="p-1.5 hover:bg-white/10 transition-colors"
            >
              <MoreVertical className="w-3 h-3 text-white/40" />
            </button>
            {showMenu && (
              <>
                <div
                  className="fixed inset-0 z-10"
                  onClick={() => setShowMenu(false)}
                />
                <div className="absolute right-0 mt-1 w-32 bg-black border border-white/20 py-1 z-20">
                  <Link
                    href={`/dashboard/projects/${project.id}`}
                    className="flex items-center gap-2 px-3 py-1.5 text-xs font-mono text-white/60 hover:bg-white/10"
                    onClick={() => setShowMenu(false)}
                  >
                    <Eye className="w-3 h-3" />
                    View
                  </Link>
                  <Link
                    href={`/dashboard/projects/${project.id}/scenarios/new`}
                    className="flex items-center gap-2 px-3 py-1.5 text-xs font-mono text-white/60 hover:bg-white/10"
                    onClick={() => setShowMenu(false)}
                  >
                    <Play className="w-3 h-3" />
                    Scenario
                  </Link>
                  <button
                    onClick={handleDuplicate}
                    disabled={duplicateProject.isPending}
                    className="flex items-center gap-2 w-full px-3 py-1.5 text-xs font-mono text-white/60 hover:bg-white/10 disabled:opacity-50"
                  >
                    <Copy className="w-3 h-3" />
                    Duplicate
                  </button>
                  <button
                    onClick={handleDelete}
                    disabled={deleteProject.isPending}
                    className="flex items-center gap-2 w-full px-3 py-1.5 text-xs font-mono text-red-400 hover:bg-white/10 disabled:opacity-50"
                  >
                    <Trash2 className="w-3 h-3" />
                    Delete
                  </button>
                </div>
              </>
            )}
          </div>
        </div>

        <Link href={`/dashboard/projects/${project.id}`}>
          <h3 className="text-sm font-mono font-bold text-white mb-1 hover:text-white/80">
            {project.name}
          </h3>
        </Link>
        <p className="text-xs font-mono text-white/40 mb-3 line-clamp-2">
          {project.description || 'No description'}
        </p>

        <div className="flex items-center justify-between pt-3 border-t border-white/5">
          <span className="text-[10px] font-mono text-white/40 uppercase px-1.5 py-0.5 bg-white/5">
            {project.domain}
          </span>
          <span className="text-[10px] font-mono text-white/30">
            {new Date(project.created_at).toLocaleDateString()}
          </span>
        </div>
      </div>
    </div>
  );
}

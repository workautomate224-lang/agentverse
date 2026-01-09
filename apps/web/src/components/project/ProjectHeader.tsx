'use client';

import Link from 'next/link';
import { ArrowLeft, Folder, Network, PlayCircle, Clock } from 'lucide-react';
import { useProject } from './ProjectContext';

export function ProjectHeader() {
  const { project, stats, isLoading } = useProject();

  if (isLoading) {
    return (
      <div className="border-b border-white/10 bg-black/50 px-6 py-4">
        <div className="flex items-center gap-4">
          <div className="h-8 w-64 animate-pulse bg-white/10" />
        </div>
      </div>
    );
  }

  if (!project) {
    return null;
  }

  const formatDate = (dateString: string | undefined) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="border-b border-white/10 bg-black/50 px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          {/* Back link */}
          <Link
            href="/dashboard/projects"
            className="flex items-center gap-2 text-white/50 hover:text-white/80 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            <span className="text-sm">Projects</span>
          </Link>

          {/* Divider */}
          <span className="text-white/20">/</span>

          {/* Project name and domain */}
          <div className="flex items-center gap-3">
            <Folder className="h-5 w-5 text-cyan-400" />
            <h1 className="text-lg font-semibold text-white">{project.name}</h1>
            {project.domain && (
              <span className="px-2 py-0.5 text-xs font-medium bg-purple-500/20 text-purple-300 border border-purple-500/30">
                {project.domain}
              </span>
            )}
          </div>
        </div>

        {/* Quick stats */}
        {stats && (
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2 text-white/60">
              <Network className="h-4 w-4" />
              <span className="text-sm">{stats.node_count ?? 0} nodes</span>
            </div>
            <div className="flex items-center gap-2 text-white/60">
              <PlayCircle className="h-4 w-4" />
              <span className="text-sm">{stats.run_count ?? 0} runs</span>
            </div>
            <div className="flex items-center gap-2 text-white/60">
              <Clock className="h-4 w-4" />
              <span className="text-sm">Last run: {formatDate(stats.last_run_at)}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

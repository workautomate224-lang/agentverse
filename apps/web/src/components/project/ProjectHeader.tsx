'use client';

import Link from 'next/link';
import { ArrowLeft, Folder, Network, PlayCircle, Clock } from 'lucide-react';
import { useProject } from './ProjectContext';

export function ProjectHeader() {
  const { project, stats, isLoading } = useProject();

  if (isLoading) {
    return (
      <div className="border-b border-white/10 bg-black/50 px-4 md:px-6 py-3 md:py-4">
        <div className="flex items-center gap-4">
          <div className="h-6 md:h-8 w-48 md:w-64 animate-pulse bg-white/10" />
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
    <div className="border-b border-white/10 bg-black/50 px-4 md:px-6 py-3 md:py-4">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 md:gap-4">
        <div className="flex items-center gap-2 md:gap-4 min-w-0">
          {/* Back link */}
          <Link
            href="/dashboard/projects"
            className="flex items-center gap-1 md:gap-2 text-white/50 hover:text-white/80 transition-colors flex-shrink-0"
          >
            <ArrowLeft className="h-3.5 w-3.5 md:h-4 md:w-4" />
            <span className="text-xs md:text-sm hidden sm:inline">Projects</span>
          </Link>

          {/* Divider */}
          <span className="text-white/20 hidden sm:inline">/</span>

          {/* Project name and domain */}
          <div className="flex items-center gap-2 md:gap-3 min-w-0">
            <Folder className="h-4 w-4 md:h-5 md:w-5 text-cyan-400 flex-shrink-0" />
            <h1 className="text-sm md:text-lg font-semibold text-white truncate">{project.name}</h1>
            {project.domain && (
              <span className="px-1.5 md:px-2 py-0.5 text-[10px] md:text-xs font-medium bg-purple-500/20 text-purple-300 border border-purple-500/30 flex-shrink-0">
                {project.domain}
              </span>
            )}
          </div>
        </div>

        {/* Quick stats */}
        {stats && (
          <div className="flex items-center gap-3 md:gap-6 text-[10px] md:text-sm overflow-x-auto">
            <div className="flex items-center gap-1.5 md:gap-2 text-white/60 flex-shrink-0">
              <Network className="h-3.5 w-3.5 md:h-4 md:w-4" />
              <span>{stats.node_count ?? 0} nodes</span>
            </div>
            <div className="flex items-center gap-1.5 md:gap-2 text-white/60 flex-shrink-0">
              <PlayCircle className="h-3.5 w-3.5 md:h-4 md:w-4" />
              <span>{stats.run_count ?? 0} runs</span>
            </div>
            <div className="hidden sm:flex items-center gap-1.5 md:gap-2 text-white/60 flex-shrink-0">
              <Clock className="h-3.5 w-3.5 md:h-4 md:w-4" />
              <span>Last: {formatDate(stats.last_run_at)}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

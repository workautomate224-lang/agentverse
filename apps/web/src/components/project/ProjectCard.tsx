'use client';

/**
 * ProjectCard Component
 * Displays individual project spec information.
 * Reference: project.md §6.1 (ProjectSpec)
 */

import { memo, useCallback } from 'react';
import {
  FolderKanban,
  Play,
  GitBranch,
  Users,
  Clock,
  ChevronRight,
  Copy,
  Archive,
  MoreHorizontal,
  Activity,
  Map,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { ProjectStatusBadge } from './ProjectStatusBadge';
import type { ProjectSpec } from '@/lib/api';

interface ProjectCardProps {
  project: ProjectSpec;
  onSelect?: (projectId: string) => void;
  onCreateRun?: (projectId: string) => void;
  onDuplicate?: (projectId: string) => void;
  onArchive?: (projectId: string) => void;
  onViewMap?: (projectId: string) => void;
  isSelected?: boolean;
  compact?: boolean;
  className?: string;
}

export const ProjectCard = memo(function ProjectCard({
  project,
  onSelect,
  onCreateRun,
  onDuplicate,
  onArchive,
  onViewMap,
  isSelected = false,
  compact = false,
  className,
}: ProjectCardProps) {
  const handleClick = useCallback(() => {
    onSelect?.(project.id);
  }, [project.id, onSelect]);

  // Format date
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: date.getFullYear() !== new Date().getFullYear() ? 'numeric' : undefined,
    });
  };

  // Calculate project status
  const status = project.run_count && project.run_count > 0
    ? 'active'
    : 'draft';

  if (compact) {
    return (
      <button
        onClick={handleClick}
        className={cn(
          'w-full flex items-center gap-3 p-3 bg-white/5 border border-white/10 text-left transition-colors',
          isSelected
            ? 'border-cyan-500/50 bg-cyan-500/10'
            : 'hover:bg-white/[0.07] hover:border-white/20',
          className
        )}
      >
        <FolderKanban className="w-4 h-4 text-white/40 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-mono text-white truncate">{project.name}</p>
          <p className="text-[10px] font-mono text-white/40">
            {project.node_count || 0} nodes • {project.run_count || 0} runs
          </p>
        </div>
        <ProjectStatusBadge status={status} size="sm" showIcon={false} />
        <ChevronRight className="w-3 h-3 text-white/30" />
      </button>
    );
  }

  return (
    <div
      className={cn(
        'bg-white/5 border border-white/10 transition-all',
        isSelected
          ? 'border-cyan-500/50 bg-cyan-500/5'
          : 'hover:bg-white/[0.07] hover:border-white/20',
        className
      )}
    >
      {/* Header */}
      <div className="p-4 border-b border-white/5">
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-white/5">
              <FolderKanban className="w-4 h-4 text-cyan-400" />
            </div>
            <div>
              <button
                onClick={handleClick}
                className="text-left group"
              >
                <h3 className="text-sm font-mono font-medium text-white group-hover:text-cyan-400 transition-colors">
                  {project.name}
                </h3>
              </button>
              <p className="text-[10px] font-mono text-white/40">
                ID: {project.id.slice(0, 12)}...
              </p>
            </div>
          </div>
          <ProjectStatusBadge status={status} size="sm" />
        </div>

        {project.description && (
          <p className="text-xs font-mono text-white/50 line-clamp-2 mt-2">
            {project.description}
          </p>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 divide-x divide-white/5">
        <div className="p-3 text-center">
          <Activity className="w-3 h-3 text-white/30 mx-auto mb-1" />
          <p className="text-sm font-mono font-bold text-white">
            {project.run_count || 0}
          </p>
          <p className="text-[10px] font-mono text-white/40">Runs</p>
        </div>
        <div className="p-3 text-center">
          <GitBranch className="w-3 h-3 text-white/30 mx-auto mb-1" />
          <p className="text-sm font-mono font-bold text-white">
            {project.node_count || 0}
          </p>
          <p className="text-[10px] font-mono text-white/40">Nodes</p>
        </div>
      </div>

      {/* Metadata */}
      <div className="px-4 py-2 bg-black/30 border-t border-white/5">
        <div className="flex items-center justify-between text-[10px] font-mono text-white/40">
          <div className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            <span>Created {formatDate(project.created_at)}</span>
          </div>
          {project.updated_at && (
            <span>Updated {formatDate(project.updated_at)}</span>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1 p-2 border-t border-white/5">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onCreateRun?.(project.id)}
          className="flex-1"
        >
          <Play className="w-3 h-3 mr-1" />
          Run
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onViewMap?.(project.id)}
          className="flex-1"
        >
          <Map className="w-3 h-3 mr-1" />
          Map
        </Button>
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => onDuplicate?.(project.id)}
          title="Duplicate"
        >
          <Copy className="w-3 h-3" />
        </Button>
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => onArchive?.(project.id)}
          title="Archive"
        >
          <Archive className="w-3 h-3" />
        </Button>
      </div>
    </div>
  );
});

export default ProjectCard;

'use client';

/**
 * ProjectStatusBadge Component
 * Status indicator for project specs.
 * Reference: project.md §6.1 (ProjectSpec)
 */

import { memo } from 'react';
import {
  FileEdit,
  CheckCircle,
  Archive,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import { cva, type VariantProps } from 'class-variance-authority';

const statusBadgeVariants = cva(
  'inline-flex items-center gap-1.5 px-2 py-0.5 text-xs font-mono uppercase tracking-wider border',
  {
    variants: {
      status: {
        draft: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
        active: 'bg-green-500/10 text-green-400 border-green-500/20',
        archived: 'bg-white/5 text-white/40 border-white/10',
        error: 'bg-red-500/10 text-red-400 border-red-500/20',
      },
      size: {
        sm: 'text-[10px] px-1.5 py-0.5',
        md: 'text-xs px-2 py-1',
        lg: 'text-sm px-3 py-1.5',
      },
    },
    defaultVariants: {
      status: 'draft',
      size: 'md',
    },
  }
);

type ProjectStatus = 'draft' | 'active' | 'archived' | 'error';

interface ProjectStatusBadgeProps extends VariantProps<typeof statusBadgeVariants> {
  status: ProjectStatus;
  showIcon?: boolean;
  animated?: boolean;
  className?: string;
}

const STATUS_CONFIG: Record<ProjectStatus, { icon: LucideIcon; label: string }> = {
  draft: { icon: FileEdit, label: 'Draft' },
  active: { icon: CheckCircle, label: 'Active' },
  archived: { icon: Archive, label: 'Archived' },
  error: { icon: AlertCircle, label: 'Error' },
};

export const ProjectStatusBadge = memo(function ProjectStatusBadge({
  status,
  size,
  showIcon = true,
  animated = false,
  className,
}: ProjectStatusBadgeProps) {
  const config = STATUS_CONFIG[status];
  const Icon = animated && status === 'active' ? Loader2 : config.icon;

  return (
    <span className={cn(statusBadgeVariants({ status, size }), className)}>
      {showIcon && (
        <Icon
          className={cn(
            'w-3 h-3',
            animated && status === 'active' && 'animate-spin'
          )}
        />
      )}
      {config.label}
    </span>
  );
});

export default ProjectStatusBadge;

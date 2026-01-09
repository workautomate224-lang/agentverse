'use client';

/**
 * RunStatusBadge Component
 * Displays spec-compliant run status with appropriate styling.
 * Reference: project.md §6.6 (Run statuses)
 */

import { memo } from 'react';
import {
  Clock,
  Loader2,
  Play,
  CheckCircle,
  XCircle,
  Ban,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { SpecRunStatus } from '@/lib/api';

interface RunStatusBadgeProps {
  status: SpecRunStatus;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  className?: string;
}

const statusConfig: Record<SpecRunStatus, {
  label: string;
  color: string;
  bgColor: string;
  icon: React.ComponentType<{ className?: string }>;
  animate?: boolean;
}> = {
  queued: {
    label: 'Queued',
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-500/10 border-yellow-500/30',
    icon: Clock,
  },
  starting: {
    label: 'Starting',
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/10 border-blue-500/30',
    icon: Loader2,
    animate: true,
  },
  running: {
    label: 'Running',
    color: 'text-cyan-400',
    bgColor: 'bg-cyan-500/10 border-cyan-500/30',
    icon: Play,
    animate: true,
  },
  succeeded: {
    label: 'Succeeded',
    color: 'text-green-400',
    bgColor: 'bg-green-500/10 border-green-500/30',
    icon: CheckCircle,
  },
  failed: {
    label: 'Failed',
    color: 'text-red-400',
    bgColor: 'bg-red-500/10 border-red-500/30',
    icon: XCircle,
  },
  cancelled: {
    label: 'Cancelled',
    color: 'text-white/40',
    bgColor: 'bg-white/5 border-white/10',
    icon: Ban,
  },
};

const sizeStyles = {
  sm: {
    badge: 'px-2 py-0.5 text-[10px]',
    icon: 'w-3 h-3',
    gap: 'gap-1',
  },
  md: {
    badge: 'px-2.5 py-1 text-xs',
    icon: 'w-3.5 h-3.5',
    gap: 'gap-1.5',
  },
  lg: {
    badge: 'px-3 py-1.5 text-sm',
    icon: 'w-4 h-4',
    gap: 'gap-2',
  },
};

export const RunStatusBadge = memo(function RunStatusBadge({
  status,
  size = 'md',
  showLabel = true,
  className,
}: RunStatusBadgeProps) {
  const config = statusConfig[status] || statusConfig.queued;
  const sizeStyle = sizeStyles[size];
  const Icon = config.icon;

  return (
    <span
      className={cn(
        'inline-flex items-center font-mono border',
        config.bgColor,
        config.color,
        sizeStyle.badge,
        sizeStyle.gap,
        className
      )}
    >
      <Icon
        className={cn(
          sizeStyle.icon,
          config.animate && 'animate-spin'
        )}
      />
      {showLabel && <span>{config.label}</span>}
    </span>
  );
});

export default RunStatusBadge;

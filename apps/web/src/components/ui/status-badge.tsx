'use client';

import { memo } from 'react';
import { cn } from '@/lib/utils';
import {
  CheckCircle,
  AlertTriangle,
  XCircle,
  Info,
  Clock,
  Loader2,
} from 'lucide-react';
import type { StatusType } from '@/lib/accessibility';
import { STATUS_INDICATORS } from '@/lib/accessibility';

interface StatusBadgeProps {
  status: StatusType;
  label?: string;
  showIcon?: boolean;
  showLabel?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const ICONS = {
  CheckCircle,
  AlertTriangle,
  XCircle,
  Info,
  Clock,
  Loader2,
};

const SIZES = {
  sm: { icon: 12, text: 'text-xs', padding: 'px-1.5 py-0.5' },
  md: { icon: 14, text: 'text-sm', padding: 'px-2 py-1' },
  lg: { icon: 16, text: 'text-base', padding: 'px-3 py-1.5' },
};

/**
 * Accessible status badge component
 * Uses color + icon + text for accessibility (Interaction_design.md §9)
 */
export const StatusBadge = memo(function StatusBadge({
  status,
  label,
  showIcon = true,
  showLabel = true,
  size = 'md',
  className,
}: StatusBadgeProps) {
  const indicator = STATUS_INDICATORS[status];
  const Icon = ICONS[indicator.icon as keyof typeof ICONS];
  const sizeConfig = SIZES[size];

  // Pattern styles for color-blind accessibility
  const patternStyles = {
    solid: 'border-current',
    dashed: 'border-dashed border-current',
    dotted: 'border-dotted border-current',
    animated: 'border-current',
  };

  // Default labels if not provided
  const defaultLabels: Record<StatusType, string> = {
    success: 'Success',
    warning: 'Warning',
    error: 'Error',
    info: 'Info',
    pending: 'Pending',
    running: 'Running',
  };

  const displayLabel = label || defaultLabels[status];

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 border font-mono',
        indicator.color,
        patternStyles[indicator.pattern],
        sizeConfig.padding,
        sizeConfig.text,
        className
      )}
      role="status"
      aria-label={displayLabel}
    >
      {showIcon && (
        <Icon
          size={sizeConfig.icon}
          className={cn(status === 'running' && 'animate-spin')}
          aria-hidden="true"
        />
      )}
      {showLabel && <span>{displayLabel}</span>}
    </span>
  );
});

/**
 * Compact status indicator (icon only with tooltip)
 */
export const StatusIndicator = memo(function StatusIndicator({
  status,
  label,
  size = 'md',
  className,
}: Omit<StatusBadgeProps, 'showIcon' | 'showLabel'>) {
  const indicator = STATUS_INDICATORS[status];
  const Icon = ICONS[indicator.icon as keyof typeof ICONS];
  const sizeConfig = SIZES[size];

  const defaultLabels: Record<StatusType, string> = {
    success: 'Success',
    warning: 'Warning',
    error: 'Error',
    info: 'Info',
    pending: 'Pending',
    running: 'Running',
  };

  const displayLabel = label || defaultLabels[status];

  return (
    <span
      className={cn('inline-flex items-center', indicator.color, className)}
      role="status"
      aria-label={displayLabel}
      title={displayLabel}
    >
      <Icon
        size={sizeConfig.icon}
        className={cn(status === 'running' && 'animate-spin')}
        aria-hidden="true"
      />
      <span className="sr-only">{displayLabel}</span>
    </span>
  );
});

'use client';

/**
 * Save Draft Indicator Component
 * Reference: blueprint.md §4.3
 *
 * Shows the current save status for draft data (saving, saved, error).
 * Used with ClarifyPanel and other forms that auto-save.
 */

import { useMemo } from 'react';
import { Check, Loader2, AlertCircle, Cloud, CloudOff } from 'lucide-react';
import { cn } from '@/lib/utils';

export type SaveStatus = 'idle' | 'saving' | 'saved' | 'error' | 'offline';

interface SaveDraftIndicatorProps {
  /** Current save status */
  status: SaveStatus;
  /** Last saved timestamp */
  lastSavedAt?: Date | string | null;
  /** Error message if status is 'error' */
  errorMessage?: string;
  /** Additional CSS classes */
  className?: string;
  /** Whether to show in compact mode */
  compact?: boolean;
}

export function SaveDraftIndicator({
  status,
  lastSavedAt,
  errorMessage,
  className,
  compact = false,
}: SaveDraftIndicatorProps) {
  const formattedTime = useMemo(() => {
    if (!lastSavedAt) return null;
    const date = typeof lastSavedAt === 'string' ? new Date(lastSavedAt) : lastSavedAt;
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);

    if (diffSec < 5) return 'just now';
    if (diffSec < 60) return `${diffSec}s ago`;
    if (diffMin < 60) return `${diffMin}m ago`;
    if (diffHour < 24) return `${diffHour}h ago`;
    return date.toLocaleDateString();
  }, [lastSavedAt]);

  const config = useMemo(() => {
    switch (status) {
      case 'saving':
        return {
          icon: Loader2,
          label: 'Saving...',
          color: 'text-cyan-400',
          bgColor: 'bg-cyan-400/10',
          animate: true,
        };
      case 'saved':
        return {
          icon: Check,
          label: formattedTime ? `Saved ${formattedTime}` : 'Saved',
          color: 'text-green-400',
          bgColor: 'bg-green-400/10',
          animate: false,
        };
      case 'error':
        return {
          icon: AlertCircle,
          label: errorMessage || 'Save failed',
          color: 'text-red-400',
          bgColor: 'bg-red-400/10',
          animate: false,
        };
      case 'offline':
        return {
          icon: CloudOff,
          label: 'Offline',
          color: 'text-yellow-400',
          bgColor: 'bg-yellow-400/10',
          animate: false,
        };
      default:
        return {
          icon: Cloud,
          label: 'Draft',
          color: 'text-gray-400',
          bgColor: 'bg-white/5',
          animate: false,
        };
    }
  }, [status, formattedTime, errorMessage]);

  const Icon = config.icon;

  if (compact) {
    return (
      <div
        className={cn(
          'flex items-center gap-1.5 px-2 py-1 rounded text-xs font-mono',
          config.bgColor,
          config.color,
          className
        )}
        title={config.label}
      >
        <Icon className={cn('h-3 w-3', config.animate && 'animate-spin')} />
      </div>
    );
  }

  return (
    <div
      className={cn(
        'flex items-center gap-2 px-3 py-1.5 rounded border',
        config.bgColor,
        status === 'error' ? 'border-red-400/30' : 'border-white/10',
        className
      )}
    >
      <Icon className={cn('h-3.5 w-3.5', config.color, config.animate && 'animate-spin')} />
      <span className={cn('text-xs font-mono', config.color)}>{config.label}</span>
    </div>
  );
}

export default SaveDraftIndicator;

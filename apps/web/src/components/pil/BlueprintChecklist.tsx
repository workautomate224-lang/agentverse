'use client';

/**
 * Blueprint Checklist Component
 * Reference: blueprint.md §7
 *
 * Displays a dynamic checklist based on blueprint slots and tasks.
 * Shows real-time status, missing items, and next actions.
 */

import { useMemo } from 'react';
import Link from 'next/link';
import {
  CheckCircle,
  Circle,
  AlertCircle,
  XCircle,
  ArrowRight,
  Loader2,
  Sparkles,
  HelpCircle,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { useProjectChecklist, useActiveBlueprint } from '@/hooks/useApi';
import type { ChecklistItem, ProjectChecklist, AlertState } from '@/lib/api';

// Status configuration for display - maps AlertState to visual styles
const STATUS_CONFIG: Record<AlertState, {
  icon: React.ElementType;
  color: string;
  bgColor: string;
  label: string;
}> = {
  ready: {
    icon: CheckCircle,
    color: 'text-green-400',
    bgColor: 'bg-green-400/10 border-green-400/30',
    label: 'Ready',
  },
  needs_attention: {
    icon: AlertCircle,
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-400/10 border-yellow-400/30',
    label: 'Needs Attention',
  },
  blocked: {
    icon: XCircle,
    color: 'text-red-400',
    bgColor: 'bg-red-400/10 border-red-400/30',
    label: 'Blocked',
  },
  not_started: {
    icon: Circle,
    color: 'text-gray-400',
    bgColor: 'bg-white/5 border-white/10',
    label: 'Not Started',
  },
};

// Section ID to route mapping
const SECTION_ROUTES: Record<string, string> = {
  'data': 'data-personas',
  'personas': 'data-personas',
  'data-personas': 'data-personas',
  'rules': 'rules',
  'scenarios': 'event-lab',
  'universe': 'universe-map',
  'run': 'run-center',
  'run-center': 'run-center',
};

interface BlueprintChecklistProps {
  /** Project ID */
  projectId: string;
  /** Whether to show in compact mode */
  compact?: boolean;
  /** Whether to show the header */
  showHeader?: boolean;
  /** Additional CSS classes */
  className?: string;
}

interface ChecklistItemCardProps {
  item: ChecklistItem;
  projectId: string;
  compact?: boolean;
}

function ChecklistItemCard({ item, projectId, compact }: ChecklistItemCardProps) {
  const config = STATUS_CONFIG[item.status] || STATUS_CONFIG.not_started;
  const Icon = config.icon;
  const route = SECTION_ROUTES[item.section_id] || item.section_id;

  return (
    <Link href={`/p/${projectId}/${route}`}>
      <div
        className={cn(
          'p-4 border transition-all group cursor-pointer hover:bg-white/5',
          config.bgColor
        )}
      >
        <div className="flex items-start gap-3">
          <div className={cn('p-1.5 rounded', config.bgColor)}>
            <Icon className={cn('h-4 w-4', config.color)} />
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <h4 className="text-sm font-mono font-medium text-white group-hover:text-cyan-400 transition-colors">
                {item.title}
              </h4>
              {item.match_score !== null && item.match_score > 0 && (
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-purple-400/10 text-purple-400 border border-purple-400/30">
                  {Math.round(item.match_score * 100)}% aligned
                </span>
              )}
            </div>

            {item.status_reason && !compact && (
              <p className="text-xs text-gray-400 font-mono mb-2">
                {item.status_reason}
              </p>
            )}

            {item.why_it_matters && !compact && (
              <p className="text-xs text-gray-500 font-mono mb-2 italic">
                {item.why_it_matters}
              </p>
            )}

            {/* Missing items */}
            {item.missing_items && item.missing_items.length > 0 && !compact && (
              <div className="mb-2">
                <p className="text-[10px] text-gray-500 font-mono mb-1">Missing:</p>
                <ul className="space-y-0.5">
                  {item.missing_items.slice(0, 3).map((missing, idx) => (
                    <li key={idx} className="text-xs text-yellow-400/80 font-mono flex items-center gap-1">
                      <span className="w-1 h-1 rounded-full bg-yellow-400/60" />
                      {missing}
                    </li>
                  ))}
                  {item.missing_items.length > 3 && (
                    <li className="text-xs text-gray-500 font-mono">
                      +{item.missing_items.length - 3} more
                    </li>
                  )}
                </ul>
              </div>
            )}

            {/* Next action */}
            {item.next_action && !compact && (
              <div className="flex items-center gap-1.5 text-xs text-cyan-400 font-mono">
                <ArrowRight className="h-3 w-3" />
                <span>{item.next_action.label || item.next_action.action}</span>
              </div>
            )}

            {/* Latest summary */}
            {item.latest_summary && !compact && (
              <p className="text-xs text-gray-500 font-mono mt-2 line-clamp-2">
                {item.latest_summary}
              </p>
            )}
          </div>

          <ArrowRight className="h-4 w-4 text-white/20 group-hover:text-cyan-400 group-hover:translate-x-1 transition-all flex-shrink-0" />
        </div>
      </div>
    </Link>
  );
}

export function BlueprintChecklist({
  projectId,
  compact = false,
  showHeader = true,
  className,
}: BlueprintChecklistProps) {
  const { data: checklist, isLoading: checklistLoading } = useProjectChecklist(projectId);
  const { data: blueprint, isLoading: blueprintLoading } = useActiveBlueprint(projectId);

  const isLoading = checklistLoading || blueprintLoading;

  // Calculate progress
  const progress = useMemo(() => {
    if (!checklist) return { percent: 0, ready: 0, total: 0 };
    const total = checklist.items.length;
    const ready = checklist.ready_count;
    return {
      percent: total > 0 ? Math.round((ready / total) * 100) : 0,
      ready,
      total,
    };
  }, [checklist]);

  // Group items by status for summary
  const statusSummary = useMemo(() => {
    if (!checklist) return null;
    return {
      ready: checklist.ready_count,
      needsAttention: checklist.needs_attention_count,
      blocked: checklist.blocked_count,
      notStarted: checklist.not_started_count,
    };
  }, [checklist]);

  if (isLoading) {
    return (
      <div className={cn('flex items-center justify-center p-8', className)}>
        <Loader2 className="h-6 w-6 animate-spin text-cyan-400" />
        <span className="ml-3 text-sm text-gray-400 font-mono">Loading checklist...</span>
      </div>
    );
  }

  // No blueprint available
  if (!blueprint) {
    return (
      <div className={cn('p-6 border border-white/10 bg-white/5', className)}>
        <div className="flex items-start gap-3">
          <HelpCircle className="h-5 w-5 text-gray-400 mt-0.5" />
          <div>
            <h3 className="text-sm font-mono font-medium text-white mb-1">
              No Blueprint Yet
            </h3>
            <p className="text-xs text-gray-400 font-mono">
              Complete the goal clarification to generate your project blueprint.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // No checklist items
  if (!checklist || checklist.items.length === 0) {
    return (
      <div className={cn('p-6 border border-white/10 bg-white/5', className)}>
        <div className="flex items-start gap-3">
          <Sparkles className="h-5 w-5 text-cyan-400 mt-0.5" />
          <div>
            <h3 className="text-sm font-mono font-medium text-white mb-1">
              Building Checklist...
            </h3>
            <p className="text-xs text-gray-400 font-mono">
              Your project checklist will appear once the blueprint is finalized.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={cn('space-y-4', className)}>
      {/* Header with progress */}
      {showHeader && (
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded bg-cyan-400/10 border border-cyan-400/30">
              <Sparkles className="h-5 w-5 text-cyan-400" />
            </div>
            <div>
              <h3 className="text-sm font-mono font-medium text-white">
                Project Setup
              </h3>
              <p className="text-xs text-gray-400 font-mono">
                {checklist.overall_readiness}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Status summary pills */}
            {statusSummary && (
              <div className="flex items-center gap-2">
                {statusSummary.ready > 0 && (
                  <span className="text-[10px] font-mono px-2 py-1 rounded bg-green-400/10 text-green-400 border border-green-400/30">
                    {statusSummary.ready} ready
                  </span>
                )}
                {statusSummary.needsAttention > 0 && (
                  <span className="text-[10px] font-mono px-2 py-1 rounded bg-yellow-400/10 text-yellow-400 border border-yellow-400/30">
                    {statusSummary.needsAttention} needs work
                  </span>
                )}
                {statusSummary.blocked > 0 && (
                  <span className="text-[10px] font-mono px-2 py-1 rounded bg-red-400/10 text-red-400 border border-red-400/30">
                    {statusSummary.blocked} blocked
                  </span>
                )}
              </div>
            )}

            {/* Progress bar */}
            <div className="text-right">
              <div className="text-xs text-gray-400 font-mono mb-1">
                {progress.ready}/{progress.total} complete
              </div>
              <Progress value={progress.percent} className="w-24 h-1.5" />
            </div>
          </div>
        </div>
      )}

      {/* Checklist items */}
      <div className="space-y-2">
        {checklist.items.map((item) => (
          <ChecklistItemCard
            key={item.id}
            item={item}
            projectId={projectId}
            compact={compact}
          />
        ))}
      </div>

      {/* Blueprint version info */}
      <div className="flex items-center justify-between text-[10px] font-mono text-gray-500 pt-2 border-t border-white/5">
        <span>Blueprint v{checklist.blueprint_version}</span>
        <span className={cn(
          progress.percent === 100 ? 'text-green-400' : 'text-gray-400'
        )}>
          {progress.percent === 100 ? 'Ready to run' : `${100 - progress.percent}% remaining`}
        </span>
      </div>
    </div>
  );
}

export default BlueprintChecklist;

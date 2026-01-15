'use client';

/**
 * Guidance Panel Component
 * Reference: blueprint.md §4, §7
 *
 * Displays contextual guidance and tips based on blueprint status.
 * Shows relevant slots, tasks, and suggested next actions for a section.
 */

import { useMemo, useState } from 'react';
import Link from 'next/link';
import {
  Lightbulb,
  ChevronDown,
  ChevronUp,
  CheckCircle,
  AlertCircle,
  XCircle,
  Circle,
  ArrowRight,
  Sparkles,
  Loader2,
  HelpCircle,
  Target,
  Zap,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { useProjectChecklist, useActiveBlueprint } from '@/hooks/useApi';
import type { ChecklistItem, AlertState } from '@/lib/api';

// Section configuration for guidance
const SECTION_CONFIG: Record<string, {
  title: string;
  description: string;
  tips: string[];
}> = {
  'data-personas': {
    title: 'Data & Personas',
    description: 'Configure your simulation population and data sources.',
    tips: [
      'Upload demographic data to generate realistic personas',
      'Define behavioral archetypes for different customer segments',
      'Connect external data sources for enrichment',
    ],
  },
  'rules': {
    title: 'Rules & Logic',
    description: 'Define decision-making rules and behavioral patterns.',
    tips: [
      'Create decision trees for common customer journeys',
      'Define trigger conditions for behavioral changes',
      'Set up rule priorities and conflict resolution',
    ],
  },
  'event-lab': {
    title: 'Event Lab',
    description: 'Create and test scenarios for your simulation.',
    tips: [
      'Use "What if" questions to generate scenarios',
      'Test edge cases and unexpected events',
      'Chain multiple scenarios for complex simulations',
    ],
  },
  'universe-map': {
    title: 'Universe Map',
    description: 'Visualize your simulation nodes and forks.',
    tips: [
      'Click nodes to view detailed state',
      'Compare different fork branches',
      'Track how scenarios diverge from baseline',
    ],
  },
  'run-center': {
    title: 'Run Center',
    description: 'Configure and launch simulation runs.',
    tips: [
      'Start with a baseline run before testing scenarios',
      'Monitor running simulations in real-time',
      'Compare results across different runs',
    ],
  },
};

// Status icons based on AlertState
const STATUS_ICONS: Record<AlertState, React.ElementType> = {
  ready: CheckCircle,
  needs_attention: AlertCircle,
  blocked: XCircle,
  not_started: Circle,
};

const STATUS_COLORS: Record<AlertState, string> = {
  ready: 'text-green-400',
  needs_attention: 'text-yellow-400',
  blocked: 'text-red-400',
  not_started: 'text-gray-400',
};

interface GuidancePanelProps {
  /** Current section ID */
  sectionId: string;
  /** Project ID */
  projectId: string;
  /** Whether to show in compact mode */
  compact?: boolean;
  /** Whether to start expanded */
  defaultExpanded?: boolean;
  /** Additional CSS classes */
  className?: string;
}

export function GuidancePanel({
  sectionId,
  projectId,
  compact = false,
  defaultExpanded = true,
  className,
}: GuidancePanelProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const { data: checklist, isLoading: checklistLoading } = useProjectChecklist(projectId);
  const { data: blueprint, isLoading: blueprintLoading } = useActiveBlueprint(projectId);

  const isLoading = checklistLoading || blueprintLoading;

  // Get section-specific checklist items
  const sectionItems = useMemo(() => {
    if (!checklist) return [];
    return checklist.items.filter(
      (item) => item.section_id === sectionId ||
                item.section_id.includes(sectionId) ||
                sectionId.includes(item.section_id)
    );
  }, [checklist, sectionId]);

  // Get section config
  const sectionConfig = SECTION_CONFIG[sectionId] || {
    title: 'Section Guidance',
    description: 'Tips and guidance for this section.',
    tips: [],
  };

  // Calculate section status
  const sectionStatus = useMemo((): AlertState => {
    if (sectionItems.length === 0) return 'not_started';
    const statuses = sectionItems.map(item => item.status);
    if (statuses.includes('blocked')) return 'blocked';
    if (statuses.includes('needs_attention')) return 'needs_attention';
    if (statuses.every(s => s === 'ready')) return 'ready';
    return 'not_started';
  }, [sectionItems]);

  const StatusIcon = STATUS_ICONS[sectionStatus];
  const statusColor = STATUS_COLORS[sectionStatus];

  // Get next action for this section
  const nextAction = useMemo(() => {
    const needsWork = sectionItems.find(
      item => item.status !== 'ready' && item.next_action
    );
    return needsWork?.next_action;
  }, [sectionItems]);

  if (isLoading) {
    return (
      <div className={cn('p-4 bg-white/5 border border-white/10', className)}>
        <div className="flex items-center gap-2 text-gray-400">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span className="text-xs font-mono">Loading guidance...</span>
        </div>
      </div>
    );
  }

  // No blueprint yet
  if (!blueprint) {
    return (
      <div className={cn('p-4 bg-white/5 border border-white/10', className)}>
        <div className="flex items-start gap-3">
          <HelpCircle className="h-5 w-5 text-gray-400 flex-shrink-0" />
          <div>
            <h3 className="text-sm font-mono font-medium text-white mb-1">
              {sectionConfig.title}
            </h3>
            <p className="text-xs text-gray-400 font-mono">
              Complete goal clarification to get personalized guidance for this section.
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (compact) {
    return (
      <div className={cn('p-3 bg-white/5 border border-white/10', className)}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <StatusIcon className={cn('h-4 w-4', statusColor)} />
            <span className="text-xs font-mono text-white">{sectionConfig.title}</span>
          </div>
          {nextAction && (
            <Button
              size="sm"
              variant="ghost"
              className="text-xs font-mono text-cyan-400 hover:bg-cyan-500/10 h-7 px-2"
            >
              <Zap className="h-3 w-3 mr-1" />
              {nextAction.label || nextAction.action}
            </Button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className={cn('bg-white/5 border border-white/10', className)}>
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full p-4 flex items-center justify-between hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="p-1.5 rounded bg-purple-400/10 border border-purple-400/30">
            <Lightbulb className="h-4 w-4 text-purple-400" />
          </div>
          <div className="text-left">
            <h3 className="text-sm font-mono font-medium text-white">
              {sectionConfig.title} Guidance
            </h3>
            <p className="text-xs text-gray-400 font-mono">
              {sectionConfig.description}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <StatusIcon className={cn('h-4 w-4', statusColor)} />
          {isExpanded ? (
            <ChevronUp className="h-4 w-4 text-gray-400" />
          ) : (
            <ChevronDown className="h-4 w-4 text-gray-400" />
          )}
        </div>
      </button>

      {/* Content */}
      {isExpanded && (
        <div className="px-4 pb-4 space-y-4">
          {/* Section items from checklist */}
          {sectionItems.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-[10px] font-mono text-gray-500 uppercase tracking-wider">
                Checklist Items
              </h4>
              {sectionItems.map((item) => {
                const ItemIcon = STATUS_ICONS[item.status];
                const itemColor = STATUS_COLORS[item.status];
                return (
                  <div
                    key={item.id}
                    className="p-3 bg-black/50 border border-white/5"
                  >
                    <div className="flex items-start gap-2">
                      <ItemIcon className={cn('h-4 w-4 mt-0.5 flex-shrink-0', itemColor)} />
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-mono text-white">
                          {item.title}
                        </div>
                        {item.status_reason && (
                          <p className="text-[10px] font-mono text-gray-500 mt-1">
                            {item.status_reason}
                          </p>
                        )}
                        {/* Missing items */}
                        {item.missing_items && item.missing_items.length > 0 && (
                          <div className="mt-2">
                            <span className="text-[10px] font-mono text-yellow-400/80">
                              Missing: {item.missing_items.slice(0, 2).join(', ')}
                              {item.missing_items.length > 2 && ` +${item.missing_items.length - 2} more`}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Tips */}
          {sectionConfig.tips.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-[10px] font-mono text-gray-500 uppercase tracking-wider">
                Quick Tips
              </h4>
              <ul className="space-y-1.5">
                {sectionConfig.tips.map((tip, idx) => (
                  <li
                    key={idx}
                    className="flex items-start gap-2 text-xs font-mono text-gray-400"
                  >
                    <Sparkles className="h-3 w-3 text-purple-400 mt-0.5 flex-shrink-0" />
                    <span>{tip}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Next action */}
          {nextAction && (
            <div className="pt-2 border-t border-white/5">
              <Button
                variant="outline"
                size="sm"
                className="w-full text-xs font-mono border-cyan-400/30 text-cyan-400 hover:bg-cyan-500/10"
              >
                <Target className="h-3 w-3 mr-2" />
                {nextAction.label || nextAction.action}
                <ArrowRight className="h-3 w-3 ml-auto" />
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default GuidancePanel;

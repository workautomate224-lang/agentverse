'use client';

/**
 * Guidance Panel Component (Blueprint v2)
 *
 * Displays blueprint-driven tasks and progress for each section.
 * Reference: blueprint_v2.md §4.4 (Section Task Map)
 *
 * Usage:
 *   <GuidancePanel projectId={projectId} section="inputs" />
 */

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Target,
  CheckCircle2,
  Circle,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  Lightbulb,
  Loader2,
  ExternalLink,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { useActiveBlueprint } from '@/hooks/useApi';
import type { BlueprintTask, AlertState } from '@/lib/api';

// Section display names
const SECTION_NAMES: Record<string, string> = {
  overview: 'Overview',
  inputs: 'Data & Personas',
  rules: 'Rules & Assumptions',
  runs: 'Run Center',
  universe: 'Universe Map',
  events: 'Event Lab',
  society: 'Society Simulation',
  target: 'Target Planner',
  reliability: 'Reliability',
  telemetry: 'Telemetry & Replay',
  reports: 'Reports',
  settings: 'Settings',
};

interface GuidancePanelProps {
  /** Project ID */
  projectId: string;
  /** Current section key (e.g., 'inputs', 'rules', 'runs') */
  section: string;
  /** Callback when a task is clicked */
  onTaskClick?: (task: BlueprintTask) => void;
  /** Additional CSS classes */
  className?: string;
  /** Whether to show collapsed by default */
  defaultCollapsed?: boolean;
}

export function GuidancePanel({
  projectId,
  section,
  onTaskClick,
  className,
  defaultCollapsed = false,
}: GuidancePanelProps) {
  const [expanded, setExpanded] = useState(!defaultCollapsed);
  const { data: blueprint, isLoading, error } = useActiveBlueprint(projectId);

  // Filter tasks by section_id
  const sectionTasks: BlueprintTask[] = blueprint?.tasks?.filter(
    (task) => task.section_id === section
  ) || [];

  // Calculate progress based on task status
  const totalTasks = sectionTasks.length;
  const completedCount = sectionTasks.filter(
    (task) => task.status === 'ready'
  ).length;
  const progressPercent = totalTasks > 0 ? Math.round((completedCount / totalTasks) * 100) : 0;

  // Loading state
  if (isLoading) {
    return (
      <div className={cn('bg-white/5 border border-white/10 p-4', className)}>
        <div className="flex items-center gap-2 text-gray-400">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span className="text-sm font-mono">Loading guidance...</span>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className={cn('bg-white/5 border border-yellow-500/30 p-4', className)}>
        <div className="flex items-center gap-2 text-yellow-400">
          <AlertTriangle className="h-4 w-4" />
          <span className="text-sm font-mono">Failed to load guidance</span>
        </div>
      </div>
    );
  }

  // No tasks for this section
  if (sectionTasks.length === 0) {
    return (
      <div className={cn('bg-white/5 border border-white/10 p-4', className)}>
        <div className="flex items-center gap-2 text-gray-400">
          <Target className="h-4 w-4" />
          <span className="text-sm font-mono">No blueprint tasks for {SECTION_NAMES[section] || section}</span>
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'bg-gradient-to-r from-cyan-500/5 via-transparent to-purple-500/5',
        'border border-cyan-400/20',
        className
      )}
    >
      {/* Header */}
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="relative">
            <Target className="h-5 w-5 text-cyan-400" />
          </div>
          <div className="text-left">
            <h3 className="text-sm font-mono font-semibold text-white">
              Blueprint Guidance
            </h3>
            <p className="text-xs font-mono text-gray-400">
              {SECTION_NAMES[section] || section} • {completedCount}/{totalTasks} tasks
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Progress bar */}
          <div className="hidden sm:flex items-center gap-2">
            <div className="w-20 h-1.5 bg-white/10 rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-gradient-to-r from-cyan-400 to-purple-400"
                initial={{ width: 0 }}
                animate={{ width: `${progressPercent}%` }}
                transition={{ duration: 0.5, ease: 'easeOut' }}
              />
            </div>
            <span className="text-xs font-mono text-gray-400">{progressPercent}%</span>
          </div>

          {/* Expand/collapse icon */}
          {expanded ? (
            <ChevronUp className="h-4 w-4 text-gray-400" />
          ) : (
            <ChevronDown className="h-4 w-4 text-gray-400" />
          )}
        </div>
      </button>

      {/* Task list */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 space-y-2">
              {sectionTasks.map((task, index) => {
                const isCompleted = task.status === 'ready';
                const isBlocked = task.status === 'blocked';
                const needsAttention = task.status === 'needs_attention';
                return (
                  <motion.div
                    key={task.task_id}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className={cn(
                      'group flex items-start gap-3 p-3 rounded border transition-colors',
                      isCompleted
                        ? 'border-green-500/20 bg-green-500/5'
                        : isBlocked
                        ? 'border-red-500/20 bg-red-500/5'
                        : needsAttention
                        ? 'border-yellow-500/20 bg-yellow-500/5'
                        : 'border-white/10 bg-white/5 hover:bg-white/10 hover:border-cyan-400/30'
                    )}
                  >
                    {/* Status icon */}
                    <div className="pt-0.5">
                      {isCompleted ? (
                        <CheckCircle2 className="h-4 w-4 text-green-400" />
                      ) : isBlocked ? (
                        <AlertTriangle className="h-4 w-4 text-red-400" />
                      ) : needsAttention ? (
                        <AlertTriangle className="h-4 w-4 text-yellow-400" />
                      ) : (
                        <Circle className="h-4 w-4 text-gray-500" />
                      )}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h4
                          className={cn(
                            'text-sm font-mono font-medium',
                            isCompleted ? 'text-green-400' : isBlocked ? 'text-red-400' : 'text-white'
                          )}
                        >
                          {task.title}
                        </h4>
                        {task.linked_slot_ids && task.linked_slot_ids.length > 0 && (
                          <span className="text-[10px] font-mono text-cyan-400/60 bg-cyan-400/10 px-1.5 py-0.5 rounded">
                            {task.linked_slot_ids.length} slot{task.linked_slot_ids.length !== 1 ? 's' : ''}
                          </span>
                        )}
                      </div>

                      {/* Why it matters */}
                      {task.why_it_matters && (
                        <div className="flex items-start gap-1.5 mt-1.5">
                          <Lightbulb className="h-3 w-3 text-yellow-400/60 mt-0.5 flex-shrink-0" />
                          <p className="text-xs text-gray-400">{task.why_it_matters}</p>
                        </div>
                      )}

                      {/* Status reason */}
                      {task.status_reason && (
                        <p className="text-[10px] font-mono text-gray-500 mt-1">
                          {task.status_reason}
                        </p>
                      )}
                    </div>

                    {/* Action button */}
                    {!isCompleted && onTaskClick && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="opacity-0 group-hover:opacity-100 transition-opacity h-7 text-xs text-cyan-400 hover:text-white hover:bg-cyan-400/10"
                        onClick={() => onTaskClick(task)}
                      >
                        <ExternalLink className="h-3 w-3 mr-1" />
                        Start
                      </Button>
                    )}
                  </motion.div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default GuidancePanel;

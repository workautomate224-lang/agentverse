'use client';

/**
 * Guidance Panel Component
 * Reference: blueprint.md §4, §7
 *
 * Displays contextual guidance and tips based on blueprint status.
 * Shows relevant slots, tasks, and suggested next actions for a section.
 *
 * Slice 2C Enhancement: Now integrates with ProjectGuidance for AI-generated,
 * project-specific guidance when available.
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
  RefreshCw,
  ExternalLink,
  BookOpen,
  FileText,
  Database,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  useProjectChecklist,
  useActiveBlueprint,
  useSectionGuidance,
  useTriggerProjectGenesis,
  useGenesisJobStatus,
  useRegenerateProjectGuidance,
} from '@/hooks/useApi';
import type { ChecklistItem, AlertState, GuidanceSection } from '@/lib/api';

// Section configuration for guidance
// Reference: blueprint_v3.md §4 - All sections requiring GuidancePanel
const SECTION_CONFIG: Record<string, {
  title: string;
  description: string;
  tips: string[];
}> = {
  'overview': {
    title: 'Project Overview',
    description: 'Blueprint summary and project health at a glance.',
    tips: [
      'Review your blueprint summary to ensure alignment with goals',
      'Check the alignment score for configuration quality',
      'Monitor overall project readiness via the checklist',
    ],
  },
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
  'run-center': {
    title: 'Run Center',
    description: 'Configure and launch simulation runs.',
    tips: [
      'Start with a baseline run before testing scenarios',
      'Monitor running simulations in real-time',
      'Compare results across different runs',
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
  'event-lab': {
    title: 'Event Lab',
    description: 'Create and test scenarios for your simulation.',
    tips: [
      'Use "What if" questions to generate scenarios',
      'Test edge cases and unexpected events',
      'Chain multiple scenarios for complex simulations',
    ],
  },
  'society': {
    title: 'Society Simulation',
    description: 'Configure social dynamics and opinion spread patterns.',
    tips: [
      'Define influence networks between persona segments',
      'Set opinion propagation parameters for realistic spread',
      'Configure social friction and resistance factors',
    ],
  },
  'target': {
    title: 'Target Planner',
    description: 'Define prediction targets and intervention strategies.',
    tips: [
      'Set clear outcome targets for your predictions',
      'Use AI to generate intervention plans',
      'Test interventions across different scenarios',
    ],
  },
  'reliability': {
    title: 'Reliability & Calibration',
    description: 'Validate predictions and improve accuracy.',
    tips: [
      'Run calibration against historical data',
      'Review confidence intervals and uncertainty bounds',
      'Track prediction accuracy over time',
    ],
  },
  'calibration': {
    title: 'Calibration Lab',
    description: 'Fine-tune simulation parameters for accuracy.',
    tips: [
      'Compare simulation outputs with historical data',
      'Adjust model parameters to reduce prediction error',
      'Run sensitivity analysis on key variables',
    ],
  },
  'replay': {
    title: 'Telemetry & Replay',
    description: 'Review simulation telemetry and replay past runs.',
    tips: [
      'Replay is read-only—no new simulations triggered',
      'Analyze decision points and branching events',
      'Export telemetry data for external analysis',
    ],
  },
  'world': {
    title: '2D World',
    description: 'Visualize personas and interactions in 2D space.',
    tips: [
      'Zoom and pan to explore different regions',
      'Click personas to view detailed profiles',
      'Use filters to focus on specific segments',
    ],
  },
  'world-viewer': {
    title: '2D World Viewer',
    description: 'Interactive visualization of simulation state.',
    tips: [
      'View real-time persona positions and states',
      'Filter by attributes to highlight patterns',
      'Compare across different simulation runs',
    ],
  },
  'reports': {
    title: 'Reports',
    description: 'Generate and export simulation reports.',
    tips: [
      'Select report templates for different audiences',
      'Include key metrics and visualizations',
      'Schedule automated report generation',
    ],
  },
  'settings': {
    title: 'Project Settings',
    description: 'Configure project-level settings and preferences.',
    tips: [
      'Update project name and description',
      'Configure notification preferences',
      'Manage project access and permissions',
    ],
  },
};

// Map sectionId to GuidanceSection enum for API calls
// Reference: Slice 2C - Project Genesis
const SECTION_TO_GUIDANCE: Record<string, GuidanceSection> = {
  'overview': 'data', // Overview uses data guidance
  'data-personas': 'personas',
  'rules': 'rules',
  'run-center': 'run',
  'universe-map': 'universe_map',
  'event-lab': 'event_lab',
  'society': 'personas',
  'target': 'predict',
  'reliability': 'reliability',
  'calibration': 'calibrate',
  'replay': 'run',
  'world': 'universe_map',
  'world-viewer': 'universe_map',
  'reports': 'reports',
  'settings': 'data', // Settings uses data guidance as fallback
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

// Guidance status colors
const GUIDANCE_STATUS_COLORS: Record<string, string> = {
  ready: 'border-green-500/30 bg-green-500/5',
  generating: 'border-amber-500/30 bg-amber-500/5',
  pending: 'border-white/10 bg-white/5',
  stale: 'border-yellow-500/30 bg-yellow-500/5',
  failed: 'border-red-500/30 bg-red-500/5',
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

  // Slice 2C: Fetch project-specific guidance
  const guidanceSection = SECTION_TO_GUIDANCE[sectionId];
  const {
    data: projectGuidance,
    isLoading: guidanceLoading,
    error: guidanceError,
  } = useSectionGuidance(projectId, guidanceSection, {
    enabled: !!guidanceSection && !!projectId,
  });

  // Check genesis job status for generating state
  const {
    data: genesisStatus,
  } = useGenesisJobStatus(projectId, {
    enabled: !!projectId && projectGuidance?.status === 'generating',
  });

  // Regeneration mutation
  const { mutate: regenerateGuidance, isPending: isRegenerating } = useRegenerateProjectGuidance();

  const isLoading = checklistLoading || blueprintLoading || guidanceLoading;
  const hasProjectGuidance = projectGuidance && projectGuidance.status === 'ready';
  const isStale = projectGuidance?.status === 'stale';

  // Handle regeneration
  const handleRegenerate = () => {
    if (projectId && !isRegenerating) {
      regenerateGuidance(projectId);
    }
  };

  // Get section-specific checklist items
  const sectionItems = useMemo(() => {
    if (!checklist) return [];
    return checklist.items.filter(
      (item) => item.section_id === sectionId ||
                item.section_id.includes(sectionId) ||
                sectionId.includes(item.section_id)
    );
  }, [checklist, sectionId]);

  // Get section config - use project guidance if available, otherwise static
  const sectionConfig = useMemo(() => {
    if (hasProjectGuidance && projectGuidance) {
      return {
        title: projectGuidance.section_title || SECTION_CONFIG[sectionId]?.title || 'Section Guidance',
        description: projectGuidance.section_description || SECTION_CONFIG[sectionId]?.description || 'Tips and guidance for this section.',
        tips: projectGuidance.tips || SECTION_CONFIG[sectionId]?.tips || [],
        // Project-specific fields
        whatToInput: projectGuidance.what_to_input,
        recommendedSources: projectGuidance.recommended_sources,
        checklist: projectGuidance.checklist,
        suggestedActions: projectGuidance.suggested_actions,
        isProjectSpecific: true,
        blueprintVersion: projectGuidance.blueprint_version,
      };
    }
    return {
      ...SECTION_CONFIG[sectionId] || {
        title: 'Section Guidance',
        description: 'Tips and guidance for this section.',
        tips: [],
      },
      isProjectSpecific: false,
    };
  }, [hasProjectGuidance, projectGuidance, sectionId]);

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

  // Determine panel styling based on guidance status
  const panelBorderClass = useMemo(() => {
    if (projectGuidance?.status === 'generating') return 'border-amber-500/30';
    if (hasProjectGuidance) return 'border-green-500/30';
    if (projectGuidance?.status === 'stale') return 'border-yellow-500/30';
    return 'border-white/10';
  }, [projectGuidance, hasProjectGuidance]);

  return (
    <div className={cn('bg-white/5 border', panelBorderClass, className)}>
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full p-4 flex items-center justify-between hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className={cn(
            'p-1.5 rounded border',
            hasProjectGuidance
              ? 'bg-cyan-400/10 border-cyan-400/30'
              : 'bg-purple-400/10 border-purple-400/30'
          )}>
            {hasProjectGuidance ? (
              <Sparkles className="h-4 w-4 text-cyan-400" />
            ) : (
              <Lightbulb className="h-4 w-4 text-purple-400" />
            )}
          </div>
          <div className="text-left">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-mono font-medium text-white">
                {sectionConfig.title} Guidance
              </h3>
              {hasProjectGuidance && (
                <span className="px-1.5 py-0.5 text-[9px] font-mono bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                  AI
                </span>
              )}
              {projectGuidance?.status === 'generating' && (
                <span className="flex items-center gap-1 px-1.5 py-0.5 text-[9px] font-mono bg-amber-500/10 text-amber-400 border border-amber-500/20">
                  <Loader2 className="h-2.5 w-2.5 animate-spin" />
                  GENERATING
                </span>
              )}
              {projectGuidance?.status === 'stale' && (
                <span className="px-1.5 py-0.5 text-[9px] font-mono bg-yellow-500/10 text-yellow-400 border border-yellow-500/20">
                  STALE
                </span>
              )}
            </div>
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
          {/* Provenance indicator for project-specific guidance */}
          {sectionConfig.isProjectSpecific && (
            <div className="flex items-center gap-2 text-[10px] font-mono text-cyan-400/70">
              <Sparkles className="h-3 w-3" />
              <span>AI-generated from your Blueprint v{sectionConfig.blueprintVersion}</span>
            </div>
          )}

          {/* Stale guidance warning with regenerate button */}
          {isStale && (
            <div className="p-3 bg-yellow-500/10 border border-yellow-500/30">
              <div className="flex items-start gap-3">
                <AlertCircle className="h-4 w-4 text-yellow-400 flex-shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-mono text-yellow-400 mb-2">
                    Guidance is out of date. Your Blueprint has been updated since this guidance was generated.
                  </p>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleRegenerate}
                    disabled={isRegenerating}
                    className="text-xs font-mono border-yellow-500/30 text-yellow-400 hover:bg-yellow-500/10"
                  >
                    {isRegenerating ? (
                      <>
                        <Loader2 className="h-3 w-3 mr-2 animate-spin" />
                        Regenerating...
                      </>
                    ) : (
                      <>
                        <RefreshCw className="h-3 w-3 mr-2" />
                        Regenerate Guidance
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </div>
          )}

          {/* What to Input - Project-specific */}
          {sectionConfig.isProjectSpecific && sectionConfig.whatToInput && (
            <div className="space-y-2">
              <h4 className="text-[10px] font-mono text-gray-500 uppercase tracking-wider flex items-center gap-1">
                <FileText className="h-3 w-3" />
                What to Input
              </h4>
              <div className="p-3 bg-black/50 border border-white/5">
                <p className="text-[10px] font-mono text-gray-400 mb-2">
                  {sectionConfig.whatToInput.description}
                </p>
                {sectionConfig.whatToInput.required_items && sectionConfig.whatToInput.required_items.length > 0 && (
                  <div className="mt-2">
                    <span className="text-[9px] font-mono text-red-400 uppercase">Required:</span>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {sectionConfig.whatToInput.required_items.map((item: string, i: number) => (
                        <span key={i} className="px-1.5 py-0.5 bg-red-500/10 text-[10px] font-mono text-red-400 border border-red-500/20">
                          {item}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {sectionConfig.whatToInput.optional_items && sectionConfig.whatToInput.optional_items.length > 0 && (
                  <div className="mt-2">
                    <span className="text-[9px] font-mono text-purple-400 uppercase">Optional:</span>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {sectionConfig.whatToInput.optional_items.map((item: string, i: number) => (
                        <span key={i} className="px-1.5 py-0.5 bg-purple-500/10 text-[10px] font-mono text-purple-400 border border-purple-500/20">
                          {item}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Recommended Sources - Project-specific */}
          {sectionConfig.isProjectSpecific && sectionConfig.recommendedSources && sectionConfig.recommendedSources.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-[10px] font-mono text-gray-500 uppercase tracking-wider flex items-center gap-1">
                <Database className="h-3 w-3" />
                Recommended Sources
              </h4>
              <div className="space-y-1.5">
                {sectionConfig.recommendedSources.map((source, idx: number) => (
                  <div key={idx} className="p-2 bg-black/50 border border-white/5">
                    <div className="flex items-start gap-2">
                      <ExternalLink className="h-3 w-3 text-cyan-400 flex-shrink-0 mt-0.5" />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono text-white">{source.name}</span>
                          <span className={`px-1 py-0.5 text-[8px] font-mono uppercase ${
                            source.priority === 'required'
                              ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                              : source.priority === 'recommended'
                                ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20'
                                : 'bg-white/5 text-gray-400 border border-white/10'
                          }`}>
                            {source.priority}
                          </span>
                        </div>
                        <p className="text-[10px] font-mono text-gray-400 mt-0.5">
                          {source.description}
                        </p>
                        <span className="text-[9px] font-mono text-gray-500">
                          Type: {source.type}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Project-specific Checklist */}
          {sectionConfig.isProjectSpecific && sectionConfig.checklist && sectionConfig.checklist.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-[10px] font-mono text-gray-500 uppercase tracking-wider flex items-center gap-1">
                <CheckCircle className="h-3 w-3" />
                Checklist
              </h4>
              <ul className="space-y-1.5">
                {sectionConfig.checklist.map((item, idx: number) => (
                  <li
                    key={item.id || idx}
                    className="flex items-start gap-2 text-xs font-mono"
                  >
                    {item.completed ? (
                      <CheckCircle className="h-3 w-3 text-green-400 mt-0.5 flex-shrink-0" />
                    ) : (
                      <Circle className="h-3 w-3 text-white/30 mt-0.5 flex-shrink-0" />
                    )}
                    <div className="flex-1">
                      <span className={item.completed ? 'text-gray-500 line-through' : 'text-gray-300'}>
                        {item.label}
                      </span>
                      {item.required && !item.completed && (
                        <span className="ml-1 text-[9px] text-red-400">*</span>
                      )}
                      {item.description && (
                        <p className="text-[10px] text-gray-500 mt-0.5">{item.description}</p>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Suggested Actions - Project-specific */}
          {sectionConfig.isProjectSpecific && sectionConfig.suggestedActions && sectionConfig.suggestedActions.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-[10px] font-mono text-gray-500 uppercase tracking-wider flex items-center gap-1">
                <Zap className="h-3 w-3" />
                Suggested Actions
              </h4>
              <div className="flex flex-wrap gap-2">
                {sectionConfig.suggestedActions.map((action, idx: number) => (
                  <Button
                    key={idx}
                    size="sm"
                    variant="outline"
                    className="text-xs font-mono border-cyan-400/30 text-cyan-400 hover:bg-cyan-500/10 h-7"
                  >
                    {action.label}
                  </Button>
                ))}
              </div>
            </div>
          )}

          {/* Section items from checklist (fallback/additional) */}
          {sectionItems.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-[10px] font-mono text-gray-500 uppercase tracking-wider">
                Project Checklist Items
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

          {/* Tips - show for both static and project guidance */}
          {sectionConfig.tips && sectionConfig.tips.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-[10px] font-mono text-gray-500 uppercase tracking-wider">
                Quick Tips
              </h4>
              <ul className="space-y-1.5">
                {sectionConfig.tips.map((tip: string, idx: number) => (
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

'use client';

/**
 * ForkTuneDrawer Component
 * Variable tuning drawer for forking nodes with modified parameters.
 * Reference: Interaction_design.md §5.10, project.md §6.7 (Node), C1 (fork-not-mutate)
 */

import { useState, useCallback, useMemo } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import {
  X,
  GitBranch,
  ChevronDown,
  ChevronRight,
  RotateCcw,
  AlertTriangle,
  Play,
  Sparkles,
  Settings2,
  Loader2,
  Info,
  TrendingUp,
  TrendingDown,
  Minus,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { cn } from '@/lib/utils';
import { useForkNode, useCreateRun } from '@/hooks/useApi';
import type { SpecNode, ScenarioPatch, InterventionType } from '@/lib/api';

// Variable definition
interface Variable {
  key: string;
  label: string;
  description?: string;
  defaultValue: number;
  min: number;
  max: number;
  step: number;
  unit?: string;
}

// Variable groups
interface VariableGroup {
  id: string;
  label: string;
  description: string;
  variables: Variable[];
}

// Default variable groups based on simulation domains
const DEFAULT_VARIABLE_GROUPS: VariableGroup[] = [
  {
    id: 'economy',
    label: 'Economy',
    description: 'Economic factors and market conditions',
    variables: [
      { key: 'gdp_growth', label: 'GDP Growth Rate', defaultValue: 0.02, min: -0.1, max: 0.15, step: 0.005, unit: '%' },
      { key: 'inflation_rate', label: 'Inflation Rate', defaultValue: 0.03, min: 0, max: 0.2, step: 0.005, unit: '%' },
      { key: 'unemployment', label: 'Unemployment Rate', defaultValue: 0.05, min: 0, max: 0.3, step: 0.01, unit: '%' },
      { key: 'consumer_confidence', label: 'Consumer Confidence', defaultValue: 100, min: 50, max: 150, step: 1, unit: '' },
    ],
  },
  {
    id: 'media',
    label: 'Media & Information',
    description: 'Media influence and information flow',
    variables: [
      { key: 'media_reach', label: 'Media Reach', defaultValue: 0.7, min: 0, max: 1, step: 0.05, unit: '' },
      { key: 'misinformation_rate', label: 'Misinformation Rate', defaultValue: 0.1, min: 0, max: 0.5, step: 0.01, unit: '' },
      { key: 'social_media_activity', label: 'Social Media Activity', defaultValue: 0.5, min: 0, max: 1, step: 0.05, unit: '' },
    ],
  },
  {
    id: 'social',
    label: 'Social Cohesion',
    description: 'Social dynamics and community factors',
    variables: [
      { key: 'social_cohesion', label: 'Social Cohesion Index', defaultValue: 0.6, min: 0, max: 1, step: 0.05, unit: '' },
      { key: 'polarization', label: 'Polarization Level', defaultValue: 0.4, min: 0, max: 1, step: 0.05, unit: '' },
      { key: 'community_trust', label: 'Community Trust', defaultValue: 0.5, min: 0, max: 1, step: 0.05, unit: '' },
    ],
  },
  {
    id: 'trust',
    label: 'Trust & Authority',
    description: 'Trust in institutions and authorities',
    variables: [
      { key: 'govt_trust', label: 'Government Trust', defaultValue: 0.4, min: 0, max: 1, step: 0.05, unit: '' },
      { key: 'expert_trust', label: 'Expert Trust', defaultValue: 0.6, min: 0, max: 1, step: 0.05, unit: '' },
      { key: 'media_trust', label: 'Media Trust', defaultValue: 0.45, min: 0, max: 1, step: 0.05, unit: '' },
    ],
  },
];

// Calculate intervention magnitude
function calculateInterventionMagnitude(
  changes: Record<string, number>,
  groups: VariableGroup[]
): { magnitude: number; level: 'small' | 'medium' | 'large' | 'extreme' } {
  let totalDeviation = 0;
  let variableCount = 0;

  for (const group of groups) {
    for (const variable of group.variables) {
      if (changes[variable.key] !== undefined) {
        const deviation = Math.abs(changes[variable.key] - variable.defaultValue);
        const range = variable.max - variable.min;
        const normalizedDeviation = deviation / range;
        totalDeviation += normalizedDeviation;
        variableCount++;
      }
    }
  }

  const magnitude = variableCount > 0 ? totalDeviation / variableCount : 0;

  if (magnitude < 0.1) return { magnitude, level: 'small' };
  if (magnitude < 0.25) return { magnitude, level: 'medium' };
  if (magnitude < 0.5) return { magnitude, level: 'large' };
  return { magnitude, level: 'extreme' };
}

interface ForkTuneDrawerProps {
  nodeId: string;
  projectId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onForkCreated?: (nodeId: string, runId?: string) => void;
  variableGroups?: VariableGroup[];
}

export function ForkTuneDrawer({
  nodeId,
  projectId,
  open,
  onOpenChange,
  onForkCreated,
  variableGroups = DEFAULT_VARIABLE_GROUPS,
}: ForkTuneDrawerProps) {
  // State for variable values
  const [values, setValues] = useState<Record<string, number>>(() => {
    const initial: Record<string, number> = {};
    for (const group of variableGroups) {
      for (const variable of group.variables) {
        initial[variable.key] = variable.defaultValue;
      }
    }
    return initial;
  });

  // State for expanded groups
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set(['economy']));

  // State for fork configuration
  const [forkLabel, setForkLabel] = useState('');
  const [autoStartRun, setAutoStartRun] = useState(true);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Advanced settings
  const [seedStrategy, setSeedStrategy] = useState<'random' | 'fixed' | 'derived'>('derived');

  // API mutations
  const forkNode = useForkNode();
  const createRun = useCreateRun();

  // Calculate which values have changed from defaults
  const changedValues = useMemo(() => {
    const changed: Record<string, number> = {};
    for (const group of variableGroups) {
      for (const variable of group.variables) {
        if (values[variable.key] !== variable.defaultValue) {
          changed[variable.key] = values[variable.key];
        }
      }
    }
    return changed;
  }, [values, variableGroups]);

  // Calculate intervention magnitude
  const intervention = useMemo(
    () => calculateInterventionMagnitude(values, variableGroups),
    [values, variableGroups]
  );

  // Count changes
  const changeCount = Object.keys(changedValues).length;

  // Toggle group expansion
  const toggleGroup = (groupId: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(groupId)) {
        next.delete(groupId);
      } else {
        next.add(groupId);
      }
      return next;
    });
  };

  // Update variable value
  const updateValue = (key: string, value: number) => {
    setValues((prev) => ({ ...prev, [key]: value }));
  };

  // Reset single variable
  const resetVariable = (key: string, defaultValue: number) => {
    setValues((prev) => ({ ...prev, [key]: defaultValue }));
  };

  // Reset all variables
  const resetAll = () => {
    const initial: Record<string, number> = {};
    for (const group of variableGroups) {
      for (const variable of group.variables) {
        initial[variable.key] = variable.defaultValue;
      }
    }
    setValues(initial);
  };

  // Handle fork creation
  const handleFork = useCallback(async () => {
    // Build scenario patch from changed values
    const scenarioPatch: ScenarioPatch = {
      environment_overrides: changedValues,
      patch_description: forkLabel || `Variable tuning fork from ${nodeId.slice(0, 8)}`,
    };

    // Determine intervention type based on changes
    // variable_delta: for parameter changes, nl_query: for large interventions
    const interventionType: InterventionType = Object.keys(changedValues).length > 0
      ? 'variable_delta'
      : 'expansion';

    try {
      // Create the fork
      const newNode = await forkNode.mutateAsync({
        parent_node_id: nodeId,
        label: forkLabel || undefined,
        description: `Fork with ${changeCount} variable change(s)`,
        scenario_patch: Object.keys(changedValues).length > 0 ? scenarioPatch : undefined,
        intervention_type: interventionType,
      });

      // Auto-start run if enabled
      if (autoStartRun && newNode?.node?.node_id) {
        const run = await createRun.mutateAsync({
          project_id: projectId,
          node_id: newNode.node.node_id,
          label: forkLabel || `Run from fork ${newNode.node.node_id.slice(0, 8)}`,
          auto_start: true,
        });

        onForkCreated?.(newNode.node.node_id, run?.run_id);
      } else if (newNode?.node?.node_id) {
        onForkCreated?.(newNode.node.node_id);
      }

      onOpenChange(false);
    } catch {
      // Error handled by mutation
    }
  }, [
    changedValues,
    forkLabel,
    nodeId,
    intervention.level,
    changeCount,
    autoStartRun,
    projectId,
    seedStrategy,
    forkNode,
    createRun,
    onForkCreated,
    onOpenChange,
  ]);

  const isPending = forkNode.isPending || createRun.isPending;

  // Get change indicator for a variable
  const getChangeIndicator = (key: string, defaultValue: number) => {
    const current = values[key];
    if (current === defaultValue) return null;
    if (current > defaultValue) {
      return <TrendingUp className="w-3 h-3 text-green-400" />;
    }
    return <TrendingDown className="w-3 h-3 text-red-400" />;
  };

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/80 z-50" />
        <Dialog.Content className="fixed right-0 top-0 h-full w-full max-w-md bg-black border-l border-white/10 z-50 overflow-hidden flex flex-col">
          {/* Header */}
          <div className="flex-shrink-0 border-b border-white/10 p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-purple-500/20 border border-purple-500/50 flex items-center justify-center">
                  <GitBranch className="w-4 h-4 text-purple-400" />
                </div>
                <div>
                  <Dialog.Title className="text-sm font-mono font-bold text-white">
                    Fork & Tune
                  </Dialog.Title>
                  <Dialog.Description className="text-[10px] font-mono text-white/40">
                    Forking from Node {nodeId.slice(0, 8)}
                  </Dialog.Description>
                </div>
              </div>
              <Dialog.Close asChild>
                <Button variant="ghost" size="icon-sm">
                  <X className="w-4 h-4" />
                </Button>
              </Dialog.Close>
            </div>
          </div>

          {/* Scrollable Content */}
          <div className="flex-1 overflow-y-auto">
            {/* Fork Label */}
            <div className="p-4 border-b border-white/5">
              <label className="text-[10px] font-mono text-white/40 uppercase tracking-wider block mb-2">
                Fork Label (optional)
              </label>
              <input
                type="text"
                value={forkLabel}
                onChange={(e) => setForkLabel(e.target.value)}
                placeholder="e.g., High inflation scenario..."
                className="w-full px-3 py-2 bg-white/5 border border-white/10 text-sm font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/20"
              />
            </div>

            {/* Intervention Warning */}
            {(intervention.level === 'large' || intervention.level === 'extreme') && (
              <div className="mx-4 mt-4 p-3 bg-yellow-500/10 border border-yellow-500/30">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 text-yellow-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-xs font-mono font-bold text-yellow-400">
                      Large Intervention
                    </p>
                    <p className="text-[10px] font-mono text-white/60 mt-1">
                      Significant parameter changes may increase uncertainty in predictions.
                      Consider running multiple simulations for better confidence.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Change Summary */}
            {changeCount > 0 && (
              <div className="mx-4 mt-4 p-3 bg-cyan-500/10 border border-cyan-500/30">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Info className="w-3.5 h-3.5 text-cyan-400" />
                    <span className="text-xs font-mono text-cyan-400">
                      {changeCount} variable{changeCount !== 1 ? 's' : ''} modified
                    </span>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={resetAll}
                    className="text-[10px]"
                  >
                    <RotateCcw className="w-3 h-3 mr-1" />
                    Reset All
                  </Button>
                </div>
              </div>
            )}

            {/* Variable Groups */}
            <div className="p-4 space-y-2">
              <div className="flex items-center gap-2 mb-3">
                <Settings2 className="w-3.5 h-3.5 text-white/40" />
                <span className="text-[10px] font-mono text-white/40 uppercase tracking-wider">
                  Variable Groups
                </span>
              </div>

              {variableGroups.map((group) => {
                const isExpanded = expandedGroups.has(group.id);
                const groupChanges = group.variables.filter(
                  (v) => values[v.key] !== v.defaultValue
                ).length;

                return (
                  <div
                    key={group.id}
                    className="border border-white/10 bg-white/[0.02]"
                  >
                    {/* Group Header */}
                    <button
                      onClick={() => toggleGroup(group.id)}
                      className="w-full flex items-center justify-between p-3 hover:bg-white/5 transition-colors"
                    >
                      <div className="flex items-center gap-2">
                        {isExpanded ? (
                          <ChevronDown className="w-3.5 h-3.5 text-white/40" />
                        ) : (
                          <ChevronRight className="w-3.5 h-3.5 text-white/40" />
                        )}
                        <span className="text-xs font-mono font-medium text-white">
                          {group.label}
                        </span>
                        {groupChanges > 0 && (
                          <span className="px-1.5 py-0.5 bg-cyan-500/20 text-[10px] font-mono text-cyan-400">
                            {groupChanges}
                          </span>
                        )}
                      </div>
                      <span className="text-[10px] font-mono text-white/30">
                        {group.variables.length} vars
                      </span>
                    </button>

                    {/* Group Variables */}
                    {isExpanded && (
                      <div className="border-t border-white/5 p-3 space-y-4">
                        {group.variables.map((variable) => {
                          const currentValue = values[variable.key];
                          const isChanged = currentValue !== variable.defaultValue;

                          return (
                            <div key={variable.key} className="space-y-2">
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                  {getChangeIndicator(variable.key, variable.defaultValue)}
                                  <label className="text-xs font-mono text-white/80">
                                    {variable.label}
                                  </label>
                                </div>
                                <div className="flex items-center gap-2">
                                  <input
                                    type="number"
                                    value={
                                      variable.unit === '%'
                                        ? (currentValue * 100).toFixed(1)
                                        : currentValue.toFixed(2)
                                    }
                                    onChange={(e) => {
                                      const val = parseFloat(e.target.value);
                                      if (!isNaN(val)) {
                                        updateValue(
                                          variable.key,
                                          variable.unit === '%' ? val / 100 : val
                                        );
                                      }
                                    }}
                                    step={variable.unit === '%' ? variable.step * 100 : variable.step}
                                    className="w-16 px-2 py-1 bg-white/5 border border-white/10 text-xs font-mono text-white text-right focus:outline-none focus:border-white/20"
                                  />
                                  {variable.unit && (
                                    <span className="text-[10px] font-mono text-white/40 w-4">
                                      {variable.unit}
                                    </span>
                                  )}
                                  {isChanged && (
                                    <Button
                                      variant="ghost"
                                      size="icon-sm"
                                      onClick={() => resetVariable(variable.key, variable.defaultValue)}
                                      className="h-6 w-6"
                                      title="Reset to default"
                                    >
                                      <RotateCcw className="w-3 h-3" />
                                    </Button>
                                  )}
                                </div>
                              </div>
                              <Slider
                                value={[currentValue]}
                                onValueChange={([val]) => updateValue(variable.key, val)}
                                min={variable.min}
                                max={variable.max}
                                step={variable.step}
                                className={cn(isChanged && '[&_[data-part=range]]:bg-cyan-500')}
                              />
                              <div className="flex justify-between text-[10px] font-mono text-white/30">
                                <span>{variable.unit === '%' ? `${(variable.min * 100).toFixed(0)}%` : variable.min}</span>
                                <span>{variable.unit === '%' ? `${(variable.max * 100).toFixed(0)}%` : variable.max}</span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Advanced Settings */}
            <div className="p-4 border-t border-white/5">
              <button
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="flex items-center gap-2 text-xs font-mono text-white/50 hover:text-white/70 transition-colors"
              >
                {showAdvanced ? (
                  <ChevronDown className="w-3.5 h-3.5" />
                ) : (
                  <ChevronRight className="w-3.5 h-3.5" />
                )}
                Advanced Settings
              </button>

              {showAdvanced && (
                <div className="mt-4 space-y-4">
                  {/* Auto-start run */}
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={autoStartRun}
                      onChange={(e) => setAutoStartRun(e.target.checked)}
                      className="w-4 h-4 bg-white/5 border border-white/20"
                    />
                    <span className="text-xs font-mono text-white/70">
                      Auto-start simulation run
                    </span>
                  </label>

                  {/* Seed strategy */}
                  <div>
                    <label className="text-[10px] font-mono text-white/40 uppercase tracking-wider block mb-2">
                      Seed Strategy
                    </label>
                    <div className="flex gap-2">
                      {(['derived', 'random', 'fixed'] as const).map((strategy) => (
                        <button
                          key={strategy}
                          onClick={() => setSeedStrategy(strategy)}
                          className={cn(
                            'flex-1 px-3 py-2 text-xs font-mono border transition-colors',
                            seedStrategy === strategy
                              ? 'bg-white/10 border-white/30 text-white'
                              : 'bg-white/5 border-white/10 text-white/50 hover:text-white/70'
                          )}
                        >
                          {strategy}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Footer Actions */}
          <div className="flex-shrink-0 border-t border-white/10 p-4">
            <div className="flex items-center gap-3">
              <Button
                variant="secondary"
                onClick={() => onOpenChange(false)}
                disabled={isPending}
                className="flex-1"
              >
                Cancel
              </Button>
              <Button
                onClick={handleFork}
                disabled={isPending}
                className="flex-1"
              >
                {isPending ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 mr-2 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5 mr-2" />
                    {autoStartRun ? 'Run Fork' : 'Create Fork'}
                  </>
                )}
              </Button>
            </div>

            {/* Sensitivity Scan Button (optional feature) */}
            <Button
              variant="ghost"
              className="w-full mt-2 text-xs"
              disabled={changeCount === 0 || isPending}
            >
              <Sparkles className="w-3.5 h-3.5 mr-2" />
              Sensitivity Scan (Pre-analysis)
            </Button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export default ForkTuneDrawer;

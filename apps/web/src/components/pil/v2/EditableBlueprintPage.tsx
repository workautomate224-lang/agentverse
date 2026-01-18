'use client';

/**
 * Editable Blueprint Page Component
 * Slice 2B: Blueprint Page becomes editable + strong constraints + auto-fill
 *
 * Features:
 * - Show sections with recommended values vs selected values
 * - Allow user to edit: project name, tags, core strategy, temporal settings
 * - Run validation on every edit (client-side + server-side)
 * - Block invalid combinations with inline error messages
 * - Store override metadata (who/when/why)
 */

import { useState, useCallback, useMemo, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Edit3,
  Check,
  X,
  AlertTriangle,
  AlertCircle,
  Info,
  Sparkles,
  Target,
  Clock,
  Users,
  Layers,
  Calendar,
  Lock,
  ChevronDown,
  ChevronUp,
  HelpCircle,
  RotateCcw,
  Save,
  Loader2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  useValidateBlueprintV2Fields,
  useSaveBlueprintV2Edits,
  useBlueprintV2ByProject,
} from '@/hooks/useApi';
import {
  BlueprintEditableFields,
  BlueprintV2Recommendations,
  CoreType,
  TemporalMode,
  IsolationLevel,
  ValidationError,
  ValidationResult,
  validateBlueprintFields,
  extractRecommendationsFromBlueprint,
  hasOverride,
  createOverrideMetadata,
  OverrideMetadata,
} from '@/lib/blueprintConstraints';
import type { BlueprintV2Response } from '@/lib/api';

// =============================================================================
// TYPES
// =============================================================================

interface EditableBlueprintPageProps {
  /** Project ID to load blueprint for */
  projectId: string;
  /** Goal text used for extraction */
  goalText?: string;
  /** Pre-loaded blueprint data */
  blueprint?: BlueprintV2Response;
  /** Callback when fields are saved */
  onSave?: (fields: BlueprintEditableFields, overrides: OverrideMetadata[]) => void;
  /** Callback when validation state changes */
  onValidationChange?: (result: ValidationResult) => void;
  /** Additional CSS classes */
  className?: string;
}

interface EditableSectionProps {
  title: string;
  icon: typeof Target;
  description: string;
  children: React.ReactNode;
  hasOverride?: boolean;
  onReset?: () => void;
}

// =============================================================================
// CORE TYPE DISPLAY CONFIG
// =============================================================================

const CORE_TYPE_CONFIG: Record<
  CoreType,
  { label: string; description: string; icon: typeof Target }
> = {
  collective: {
    label: 'Collective',
    description: 'Population-level dynamics and aggregate behavior patterns',
    icon: Users,
  },
  targeted: {
    label: 'Targeted',
    description: 'Individual persona tracking and micro-level predictions',
    icon: Target,
  },
  hybrid: {
    label: 'Hybrid',
    description: 'Combines collective dynamics with targeted persona analysis',
    icon: Layers,
  },
};

const TEMPORAL_MODE_CONFIG: Record<
  TemporalMode,
  { label: string; description: string }
> = {
  live: {
    label: 'Live',
    description: 'Real-time predictions using latest available data',
  },
  backtest: {
    label: 'Backtest',
    description: 'Historical validation with isolated data access',
  },
};

const ISOLATION_LEVEL_CONFIG: Record<
  IsolationLevel,
  { label: string; description: string }
> = {
  1: {
    label: 'Level 1 - Basic',
    description: 'Standard isolation, suitable for exploratory analysis',
  },
  2: {
    label: 'Level 2 - Strict',
    description: 'Enhanced isolation for publishable results',
  },
  3: {
    label: 'Level 3 - Audit-First',
    description: 'Maximum isolation with full audit trail',
  },
};

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export function EditableBlueprintPage({
  projectId,
  goalText = '',
  blueprint: preloadedBlueprint,
  onSave,
  onValidationChange,
  className,
}: EditableBlueprintPageProps) {
  // Fetch blueprint if not provided
  const { data: fetchedBlueprint, isLoading } = useBlueprintV2ByProject(
    !preloadedBlueprint ? projectId : undefined
  );
  const blueprint = preloadedBlueprint || fetchedBlueprint;

  // Mutations
  const validateMutation = useValidateBlueprintV2Fields();
  const saveMutation = useSaveBlueprintV2Edits();

  // Extract recommendations from blueprint
  const recommendations = useMemo<BlueprintV2Recommendations | null>(() => {
    if (!blueprint) return null;
    return extractRecommendationsFromBlueprint(
      {
        intent: blueprint.intent || undefined,
        prediction_target: blueprint.prediction_target || undefined,
        horizon: blueprint.horizon || undefined,
        required_inputs: blueprint.required_inputs || undefined,
      },
      goalText
    );
  }, [blueprint, goalText]);

  // Editable fields state - initialized from recommendations
  const [fields, setFields] = useState<BlueprintEditableFields>({
    projectName: '',
    tags: [],
    coreType: 'collective',
    temporalMode: 'live',
  });

  // Override tracking
  const [overrides, setOverrides] = useState<OverrideMetadata[]>([]);
  const [showOverrideReason, setShowOverrideReason] = useState<string | null>(null);
  const [overrideReason, setOverrideReason] = useState('');

  // Validation state
  const [validation, setValidation] = useState<ValidationResult>({
    valid: true,
    errors: [],
    warnings: [],
  });

  // Initialize fields from recommendations
  useEffect(() => {
    if (recommendations) {
      setFields({
        projectName: recommendations.projectName,
        tags: recommendations.tags,
        coreType: recommendations.recommendedCore,
        temporalMode: recommendations.temporalMode,
        asOfDate: recommendations.suggestedCutoffDate,
        isolationLevel: recommendations.suggestedIsolationLevel,
      });
    }
  }, [recommendations]);

  // Run validation whenever fields change
  useEffect(() => {
    if (!recommendations) return;

    const result = validateBlueprintFields(fields, recommendations);
    setValidation(result);
    onValidationChange?.(result);
  }, [fields, recommendations, onValidationChange]);

  // Field update handler with override tracking
  const updateField = useCallback(
    <K extends keyof BlueprintEditableFields>(
      field: K,
      value: BlueprintEditableFields[K]
    ) => {
      if (!recommendations) return;

      // Track override if value differs from recommendation
      const isOverride = hasOverride(field, value, recommendations);
      if (isOverride) {
        const recommendedValue =
          field === 'coreType'
            ? recommendations.recommendedCore
            : field === 'temporalMode'
            ? recommendations.temporalMode
            : field === 'projectName'
            ? recommendations.projectName
            : field === 'tags'
            ? recommendations.tags
            : undefined;

        // Check if override already exists for this field
        const existingIndex = overrides.findIndex((o) => o.field === field);
        if (existingIndex >= 0) {
          // Update existing override
          const updated = [...overrides];
          updated[existingIndex] = createOverrideMetadata(
            field,
            recommendedValue,
            value
          );
          setOverrides(updated);
        } else {
          // Add new override
          setOverrides((prev) => [
            ...prev,
            createOverrideMetadata(field, recommendedValue, value),
          ]);
        }
      } else {
        // Remove override if value matches recommendation
        setOverrides((prev) => prev.filter((o) => o.field !== field));
      }

      setFields((prev) => ({ ...prev, [field]: value }));
    },
    [recommendations, overrides]
  );

  // Reset field to recommendation
  const resetField = useCallback(
    <K extends keyof BlueprintEditableFields>(field: K) => {
      if (!recommendations) return;

      const recommendedValue =
        field === 'coreType'
          ? recommendations.recommendedCore
          : field === 'temporalMode'
          ? recommendations.temporalMode
          : field === 'projectName'
          ? recommendations.projectName
          : field === 'tags'
          ? recommendations.tags
          : undefined;

      if (recommendedValue !== undefined) {
        setFields((prev) => ({
          ...prev,
          [field]: recommendedValue as BlueprintEditableFields[K],
        }));
        setOverrides((prev) => prev.filter((o) => o.field !== field));
      }
    },
    [recommendations]
  );

  // Handle save
  const handleSave = useCallback(async () => {
    if (!validation.valid || !recommendations) return;

    try {
      // Server-side validation
      const serverValidation = await validateMutation.mutateAsync({
        fields,
        recommendations,
      });

      if (!serverValidation.valid) {
        setValidation(serverValidation);
        return;
      }

      // Save with override tracking
      await saveMutation.mutateAsync({
        projectId,
        fields,
        overrides: overrides.map((o) => ({
          ...o,
          reason: o.reason || undefined,
        })),
      });

      onSave?.(fields, overrides);
    } catch {
      // Error handled by mutation
    }
  }, [
    fields,
    recommendations,
    validation.valid,
    overrides,
    projectId,
    validateMutation,
    saveMutation,
    onSave,
  ]);

  // Get errors/warnings for a specific field
  const getFieldErrors = useCallback(
    (field: string) => validation.errors.filter((e) => e.field === field),
    [validation.errors]
  );

  const getFieldWarnings = useCallback(
    (field: string) => validation.warnings.filter((w) => w.field === field),
    [validation.warnings]
  );

  // Loading state
  if (isLoading) {
    return (
      <div className={cn('flex items-center justify-center p-8', className)}>
        <Loader2 className="h-8 w-8 animate-spin text-cyan-400" />
      </div>
    );
  }

  // No blueprint state
  if (!blueprint || !recommendations) {
    return (
      <div className={cn('p-6 text-center', className)}>
        <Info className="h-12 w-12 text-gray-500 mx-auto mb-4" />
        <h3 className="text-lg font-mono text-white mb-2">
          No Blueprint Available
        </h3>
        <p className="text-sm text-gray-400 font-mono">
          Generate a Blueprint v2 first to configure your simulation.
        </p>
      </div>
    );
  }

  return (
    <TooltipProvider>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className={cn('space-y-6', className)}
      >
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded bg-cyan-500/20 border border-cyan-500/30">
              <Edit3 className="h-5 w-5 text-cyan-400" />
            </div>
            <div>
              <h2 className="text-xl font-mono text-white">
                Configure Simulation
              </h2>
              <p className="text-sm text-gray-400 font-mono">
                Review and customize your simulation settings
              </p>
            </div>
          </div>

          {/* Validation status badge */}
          <ValidationStatusBadge validation={validation} />
        </div>

        {/* Global validation errors */}
        {validation.errors.length > 0 && (
          <ValidationMessages errors={validation.errors} type="error" />
        )}

        {/* Global warnings */}
        {validation.warnings.length > 0 && (
          <ValidationMessages errors={validation.warnings} type="warning" />
        )}

        {/* Project Name Section */}
        <EditableSection
          title="Project Name"
          icon={Edit3}
          description="Identifier for this simulation project"
          hasOverride={overrides.some((o) => o.field === 'projectName')}
          onReset={() => resetField('projectName')}
        >
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Input
                value={fields.projectName}
                onChange={(e) => updateField('projectName', e.target.value)}
                placeholder="Enter project name..."
                className={cn(
                  'bg-black/40 border-white/10 text-white font-mono',
                  getFieldErrors('projectName').length > 0 && 'border-red-500'
                )}
              />
              {hasOverride('projectName', fields.projectName, recommendations) && (
                <OverrideIndicator
                  original={recommendations.projectName}
                  current={fields.projectName}
                />
              )}
            </div>
            <FieldMessages
              errors={getFieldErrors('projectName')}
              warnings={getFieldWarnings('projectName')}
            />
            {recommendations.projectNameRationale && (
              <RecommendationHint text={recommendations.projectNameRationale} />
            )}
          </div>
        </EditableSection>

        {/* Tags Section */}
        <EditableSection
          title="Tags"
          icon={Sparkles}
          description="Keywords for categorization (max 5)"
          hasOverride={overrides.some((o) => o.field === 'tags')}
          onReset={() => resetField('tags')}
        >
          <div className="space-y-3">
            <TagsEditor
              tags={fields.tags}
              onChange={(tags) => updateField('tags', tags)}
              maxTags={5}
            />
            <FieldMessages
              errors={getFieldErrors('tags')}
              warnings={getFieldWarnings('tags')}
            />
            {recommendations.tagsRationale && (
              <RecommendationHint text={recommendations.tagsRationale} />
            )}
          </div>
        </EditableSection>

        {/* Core Strategy Section */}
        <EditableSection
          title="Core Strategy"
          icon={Target}
          description="Simulation approach and agent model"
          hasOverride={overrides.some((o) => o.field === 'coreType')}
          onReset={() => resetField('coreType')}
        >
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-3">
              {(['collective', 'targeted', 'hybrid'] as CoreType[]).map(
                (type) => (
                  <CoreTypeOption
                    key={type}
                    type={type}
                    selected={fields.coreType === type}
                    recommended={type === recommendations.recommendedCore}
                    allowed={recommendations.allowedCores.includes(type)}
                    onClick={() => updateField('coreType', type)}
                  />
                )
              )}
            </div>
            <FieldMessages
              errors={getFieldErrors('coreType')}
              warnings={getFieldWarnings('coreType')}
            />
            {recommendations.coreRationale && (
              <RecommendationHint text={recommendations.coreRationale} />
            )}
          </div>
        </EditableSection>

        {/* Temporal Settings Section */}
        <EditableSection
          title="Temporal Mode"
          icon={Clock}
          description="Time settings for the simulation"
          hasOverride={overrides.some((o) => o.field === 'temporalMode')}
          onReset={() => resetField('temporalMode')}
        >
          <div className="space-y-4">
            {/* Mode Selection */}
            <div className="grid grid-cols-2 gap-3">
              {(['live', 'backtest'] as TemporalMode[]).map((mode) => (
                <TemporalModeOption
                  key={mode}
                  mode={mode}
                  selected={fields.temporalMode === mode}
                  recommended={mode === recommendations.temporalMode}
                  onClick={() => updateField('temporalMode', mode)}
                />
              ))}
            </div>

            {/* Backtest-specific fields */}
            <AnimatePresence>
              {fields.temporalMode === 'backtest' && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="space-y-4 overflow-hidden"
                >
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <label className="text-xs text-gray-500 font-mono uppercase tracking-wider flex items-center gap-2">
                        <Calendar className="h-3 w-3" />
                        As-of Date
                      </label>
                      <Input
                        type="date"
                        value={fields.asOfDate || ''}
                        onChange={(e) => updateField('asOfDate', e.target.value)}
                        className={cn(
                          'bg-black/40 border-white/10 text-white font-mono',
                          getFieldErrors('asOfDate').length > 0 &&
                            'border-red-500'
                        )}
                      />
                      <FieldMessages
                        errors={getFieldErrors('asOfDate')}
                        warnings={getFieldWarnings('asOfDate')}
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-xs text-gray-500 font-mono uppercase tracking-wider flex items-center gap-2">
                        <Clock className="h-3 w-3" />
                        As-of Time
                      </label>
                      <Input
                        type="time"
                        value={fields.asOfTime || ''}
                        onChange={(e) => updateField('asOfTime', e.target.value)}
                        className={cn(
                          'bg-black/40 border-white/10 text-white font-mono',
                          getFieldErrors('asOfTime').length > 0 &&
                            'border-red-500'
                        )}
                      />
                      <FieldMessages
                        errors={getFieldErrors('asOfTime')}
                        warnings={getFieldWarnings('asOfTime')}
                      />
                    </div>
                  </div>

                  {/* Isolation Level */}
                  <div className="space-y-2">
                    <label className="text-xs text-gray-500 font-mono uppercase tracking-wider flex items-center gap-2">
                      <Lock className="h-3 w-3" />
                      Isolation Level
                    </label>
                    <Select
                      value={fields.isolationLevel?.toString() || ''}
                      onValueChange={(v: string) =>
                        updateField('isolationLevel', parseInt(v) as IsolationLevel)
                      }
                    >
                      <SelectTrigger
                        className={cn(
                          'bg-black/40 border-white/10 text-white font-mono',
                          getFieldErrors('isolationLevel').length > 0 &&
                            'border-red-500'
                        )}
                      >
                        <SelectValue placeholder="Select isolation level..." />
                      </SelectTrigger>
                      <SelectContent className="bg-black border-white/10">
                        {([1, 2, 3] as IsolationLevel[]).map((level) => (
                          <SelectItem
                            key={level}
                            value={level.toString()}
                            className="text-white font-mono"
                          >
                            {ISOLATION_LEVEL_CONFIG[level].label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FieldMessages
                      errors={getFieldErrors('isolationLevel')}
                      warnings={getFieldWarnings('isolationLevel')}
                    />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            <FieldMessages
              errors={getFieldErrors('temporalMode')}
              warnings={getFieldWarnings('temporalMode')}
            />
            {recommendations.temporalRationale && (
              <RecommendationHint text={recommendations.temporalRationale} />
            )}
          </div>
        </EditableSection>

        {/* Override Summary */}
        {overrides.length > 0 && (
          <OverrideSummary
            overrides={overrides}
            onAddReason={(field) => setShowOverrideReason(field)}
          />
        )}

        {/* Save Button */}
        <div className="flex items-center justify-end gap-4 pt-4 border-t border-white/10">
          <span className="text-sm text-gray-400 font-mono">
            {validation.valid
              ? 'All settings are valid'
              : `${validation.errors.length} error(s) to fix`}
          </span>
          <Button
            onClick={handleSave}
            disabled={!validation.valid || saveMutation.isPending}
            className={cn(
              'gap-2 font-mono',
              validation.valid
                ? 'bg-cyan-500 hover:bg-cyan-600 text-black'
                : 'bg-gray-700 text-gray-400 cursor-not-allowed'
            )}
          >
            {saveMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            Save Configuration
          </Button>
        </div>
      </motion.div>
    </TooltipProvider>
  );
}

// =============================================================================
// SUB-COMPONENTS
// =============================================================================

function EditableSection({
  title,
  icon: Icon,
  description,
  children,
  hasOverride,
  onReset,
}: EditableSectionProps) {
  return (
    <Card className="bg-black/40 border-white/10">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded bg-white/5 border border-white/10">
              <Icon className="h-4 w-4 text-cyan-400" />
            </div>
            <div>
              <CardTitle className="text-base font-mono text-white flex items-center gap-2">
                {title}
                {hasOverride && (
                  <Badge
                    variant="outline"
                    className="border-yellow-500/30 text-yellow-400 text-xs font-mono"
                  >
                    Modified
                  </Badge>
                )}
              </CardTitle>
              <p className="text-xs text-gray-500 font-mono">{description}</p>
            </div>
          </div>
          {hasOverride && onReset && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onReset}
                  className="text-gray-400 hover:text-cyan-400"
                >
                  <RotateCcw className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p className="font-mono text-xs">Reset to recommendation</p>
              </TooltipContent>
            </Tooltip>
          )}
        </div>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

function ValidationStatusBadge({ validation }: { validation: ValidationResult }) {
  if (validation.valid && validation.warnings.length === 0) {
    return (
      <Badge className="bg-green-500/20 text-green-400 border-green-500/30 font-mono">
        <Check className="h-3 w-3 mr-1" />
        Ready
      </Badge>
    );
  }

  if (!validation.valid) {
    return (
      <Badge className="bg-red-500/20 text-red-400 border-red-500/30 font-mono">
        <AlertCircle className="h-3 w-3 mr-1" />
        {validation.errors.length} Error(s)
      </Badge>
    );
  }

  return (
    <Badge className="bg-yellow-500/20 text-yellow-400 border-yellow-500/30 font-mono">
      <AlertTriangle className="h-3 w-3 mr-1" />
      {validation.warnings.length} Warning(s)
    </Badge>
  );
}

function ValidationMessages({
  errors,
  type,
}: {
  errors: ValidationError[];
  type: 'error' | 'warning';
}) {
  if (errors.length === 0) return null;

  const isError = type === 'error';

  return (
    <div
      className={cn(
        'p-3 rounded border',
        isError
          ? 'bg-red-500/10 border-red-500/30'
          : 'bg-yellow-500/10 border-yellow-500/30'
      )}
    >
      <div className="flex items-start gap-2">
        {isError ? (
          <AlertCircle className="h-4 w-4 text-red-400 mt-0.5 flex-shrink-0" />
        ) : (
          <AlertTriangle className="h-4 w-4 text-yellow-400 mt-0.5 flex-shrink-0" />
        )}
        <div className="space-y-1">
          {errors.map((err, i) => (
            <p
              key={i}
              className={cn(
                'text-sm font-mono',
                isError ? 'text-red-300' : 'text-yellow-300'
              )}
            >
              {err.message}
            </p>
          ))}
        </div>
      </div>
    </div>
  );
}

function FieldMessages({
  errors,
  warnings,
}: {
  errors: ValidationError[];
  warnings: ValidationError[];
}) {
  if (errors.length === 0 && warnings.length === 0) return null;

  return (
    <div className="space-y-1">
      {errors.map((err, i) => (
        <p key={`e-${i}`} className="text-xs text-red-400 font-mono flex items-center gap-1">
          <AlertCircle className="h-3 w-3" />
          {err.message}
        </p>
      ))}
      {warnings.map((warn, i) => (
        <p
          key={`w-${i}`}
          className="text-xs text-yellow-400 font-mono flex items-center gap-1"
        >
          <AlertTriangle className="h-3 w-3" />
          {warn.message}
        </p>
      ))}
    </div>
  );
}

function RecommendationHint({ text }: { text: string }) {
  return (
    <p className="text-xs text-gray-500 font-mono flex items-center gap-1">
      <Sparkles className="h-3 w-3 text-purple-400" />
      <span className="text-purple-400">Recommendation:</span> {text}
    </p>
  );
}

function OverrideIndicator({
  original,
  current,
}: {
  original: unknown;
  current: unknown;
}) {
  return (
    <Tooltip>
      <TooltipTrigger>
        <Badge
          variant="outline"
          className="border-yellow-500/30 text-yellow-400 text-xs font-mono"
        >
          <Edit3 className="h-3 w-3" />
        </Badge>
      </TooltipTrigger>
      <TooltipContent className="max-w-xs">
        <p className="text-xs font-mono">
          <span className="text-gray-400">Original:</span>{' '}
          <span className="text-cyan-400">{String(original)}</span>
        </p>
        <p className="text-xs font-mono">
          <span className="text-gray-400">Current:</span>{' '}
          <span className="text-yellow-400">{String(current)}</span>
        </p>
      </TooltipContent>
    </Tooltip>
  );
}

function CoreTypeOption({
  type,
  selected,
  recommended,
  allowed,
  onClick,
}: {
  type: CoreType;
  selected: boolean;
  recommended: boolean;
  allowed: boolean;
  onClick: () => void;
}) {
  const config = CORE_TYPE_CONFIG[type];
  const Icon = config.icon;

  return (
    <button
      onClick={onClick}
      disabled={!allowed}
      className={cn(
        'p-4 rounded border text-left transition-all relative',
        selected
          ? 'bg-cyan-500/20 border-cyan-500 ring-1 ring-cyan-500/30'
          : allowed
          ? 'bg-black/40 border-white/10 hover:border-white/30'
          : 'bg-black/20 border-white/5 opacity-50 cursor-not-allowed'
      )}
    >
      {recommended && (
        <div className="absolute top-2 right-2">
          <Badge className="bg-purple-500/20 text-purple-400 border-purple-500/30 text-[10px] font-mono">
            Recommended
          </Badge>
        </div>
      )}
      <Icon
        className={cn(
          'h-5 w-5 mb-2',
          selected ? 'text-cyan-400' : 'text-gray-500'
        )}
      />
      <h4 className={cn('font-mono text-sm', selected ? 'text-white' : 'text-gray-300')}>
        {config.label}
      </h4>
      <p className="text-xs text-gray-500 font-mono mt-1">{config.description}</p>
    </button>
  );
}

function TemporalModeOption({
  mode,
  selected,
  recommended,
  onClick,
}: {
  mode: TemporalMode;
  selected: boolean;
  recommended: boolean;
  onClick: () => void;
}) {
  const config = TEMPORAL_MODE_CONFIG[mode];

  return (
    <button
      onClick={onClick}
      className={cn(
        'p-4 rounded border text-left transition-all relative',
        selected
          ? 'bg-cyan-500/20 border-cyan-500 ring-1 ring-cyan-500/30'
          : 'bg-black/40 border-white/10 hover:border-white/30'
      )}
    >
      {recommended && (
        <div className="absolute top-2 right-2">
          <Badge className="bg-purple-500/20 text-purple-400 border-purple-500/30 text-[10px] font-mono">
            Recommended
          </Badge>
        </div>
      )}
      <Clock
        className={cn(
          'h-5 w-5 mb-2',
          selected ? 'text-cyan-400' : 'text-gray-500'
        )}
      />
      <h4 className={cn('font-mono text-sm', selected ? 'text-white' : 'text-gray-300')}>
        {config.label}
      </h4>
      <p className="text-xs text-gray-500 font-mono mt-1">{config.description}</p>
    </button>
  );
}

function TagsEditor({
  tags,
  onChange,
  maxTags,
}: {
  tags: string[];
  onChange: (tags: string[]) => void;
  maxTags: number;
}) {
  const [inputValue, setInputValue] = useState('');

  const addTag = () => {
    if (inputValue.trim() && tags.length < maxTags && !tags.includes(inputValue.trim())) {
      onChange([...tags, inputValue.trim()]);
      setInputValue('');
    }
  };

  const removeTag = (index: number) => {
    onChange(tags.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        {tags.map((tag, i) => (
          <Badge
            key={i}
            variant="outline"
            className="border-cyan-500/30 text-cyan-400 font-mono text-xs gap-1"
          >
            {tag}
            <button
              onClick={() => removeTag(i)}
              className="ml-1 hover:text-red-400"
            >
              <X className="h-3 w-3" />
            </button>
          </Badge>
        ))}
      </div>
      {tags.length < maxTags && (
        <div className="flex gap-2">
          <Input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTag())}
            placeholder="Add a tag..."
            className="bg-black/40 border-white/10 text-white font-mono text-sm"
          />
          <Button
            variant="outline"
            size="sm"
            onClick={addTag}
            disabled={!inputValue.trim()}
            className="border-white/10"
          >
            Add
          </Button>
        </div>
      )}
    </div>
  );
}

function OverrideSummary({
  overrides,
  onAddReason,
}: {
  overrides: OverrideMetadata[];
  onAddReason: (field: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);

  if (overrides.length === 0) return null;

  return (
    <Card className="bg-yellow-500/5 border-yellow-500/20">
      <CardHeader className="pb-2">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center justify-between w-full"
        >
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-yellow-400" />
            <span className="text-sm font-mono text-yellow-400">
              {overrides.length} Override(s) from Recommendations
            </span>
          </div>
          {expanded ? (
            <ChevronUp className="h-4 w-4 text-yellow-400" />
          ) : (
            <ChevronDown className="h-4 w-4 text-yellow-400" />
          )}
        </button>
      </CardHeader>
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
          >
            <CardContent className="pt-0">
              <div className="space-y-2">
                {overrides.map((override, i) => (
                  <div
                    key={i}
                    className="p-2 rounded bg-black/40 border border-white/10 flex items-center justify-between"
                  >
                    <div>
                      <span className="text-xs text-gray-400 font-mono">
                        {override.field}:
                      </span>
                      <span className="text-xs text-gray-500 font-mono ml-2 line-through">
                        {String(override.originalValue)}
                      </span>
                      <span className="text-xs text-cyan-400 font-mono mx-2">→</span>
                      <span className="text-xs text-white font-mono">
                        {String(override.newValue)}
                      </span>
                    </div>
                    {!override.reason && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onAddReason(override.field)}
                        className="text-xs text-gray-400 hover:text-cyan-400"
                      >
                        <HelpCircle className="h-3 w-3 mr-1" />
                        Add reason
                      </Button>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}

export default EditableBlueprintPage;

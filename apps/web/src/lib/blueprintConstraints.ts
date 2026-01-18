/**
 * Blueprint v2 Constraint Validation Engine
 * Slice 2B: Strong constraints + validation
 *
 * This module provides client-side validation for Blueprint v2 edits.
 * Server-side validation mirrors these rules for security.
 */

// =============================================================================
// TYPES
// =============================================================================

export type CoreType = 'collective' | 'targeted' | 'hybrid';
export type TemporalMode = 'live' | 'backtest';
export type IsolationLevel = 1 | 2 | 3;

export interface BlueprintV2Recommendations {
  // From blueprint intent/analysis
  projectName: string;
  projectNameRationale?: string;
  tags: string[];
  tagsRationale?: string;

  // Core strategy recommendation
  recommendedCore: CoreType;
  coreRationale?: string;
  allowedCores: CoreType[]; // Cores that are valid for this blueprint

  // Temporal recommendations
  temporalMode: TemporalMode;
  temporalRationale?: string;
  suggestedCutoffDate?: string; // ISO date if backtest recommended
  suggestedIsolationLevel?: IsolationLevel;

  // Required inputs from blueprint
  requiredInputs: {
    name: string;
    type: string;
    required: boolean;
    description: string;
  }[];
}

export interface BlueprintEditableFields {
  projectName: string;
  tags: string[];
  coreType: CoreType;
  temporalMode: TemporalMode;
  asOfDate?: string;
  asOfTime?: string;
  timezone?: string;
  isolationLevel?: IsolationLevel;
}

export interface ValidationError {
  field: string;
  code: string;
  message: string;
  severity: 'error' | 'warning';
}

export interface ValidationResult {
  valid: boolean;
  errors: ValidationError[];
  warnings: ValidationError[];
}

export interface OverrideMetadata {
  field: string;
  originalValue: unknown;
  newValue: unknown;
  timestamp: string;
  reason?: string;
}

// =============================================================================
// CONSTRAINT RULES
// =============================================================================

/**
 * Required field validation rules
 */
const REQUIRED_FIELDS: (keyof BlueprintEditableFields)[] = [
  'projectName',
  'coreType',
  'temporalMode',
];

/**
 * Field length constraints
 */
const FIELD_CONSTRAINTS = {
  projectName: { minLength: 3, maxLength: 100 },
  tags: { maxCount: 5, maxLength: 30 },
} as const;

/**
 * Core type conflict rules based on required inputs
 */
function validateCoreTypeConflicts(
  coreType: CoreType,
  requiredInputs: BlueprintV2Recommendations['requiredInputs']
): ValidationError[] {
  const errors: ValidationError[] = [];

  // Check if personas are required
  const personasRequired = requiredInputs.some(
    input => input.type === 'PERSONA_SET' && input.required
  );

  // If personas are required, targeted-only is not allowed (must be hybrid or collective with personas)
  if (personasRequired && coreType === 'targeted') {
    errors.push({
      field: 'coreType',
      code: 'CORE_REQUIRES_HYBRID',
      message: 'Blueprint requires personas. Use "Hybrid" mode to include both collective dynamics and targeted personas.',
      severity: 'error',
    });
  }

  // Check if events are required
  const eventsRequired = requiredInputs.some(
    input => input.type === 'EVENT_SCRIPT_SET' && input.required
  );

  // If events are required, pure collective without events capability may need hybrid
  if (eventsRequired && coreType === 'collective') {
    errors.push({
      field: 'coreType',
      code: 'CORE_MISSING_EVENTS',
      message: 'Blueprint includes required event simulations. Consider "Hybrid" mode for full event support.',
      severity: 'warning',
    });
  }

  return errors;
}

/**
 * Temporal validation rules
 */
function validateTemporalSettings(
  fields: BlueprintEditableFields,
  recommendations: BlueprintV2Recommendations
): ValidationError[] {
  const errors: ValidationError[] = [];

  // Backtest mode requires date/time
  if (fields.temporalMode === 'backtest') {
    if (!fields.asOfDate) {
      errors.push({
        field: 'asOfDate',
        code: 'BACKTEST_REQUIRES_DATE',
        message: 'Backtest mode requires an as-of date.',
        severity: 'error',
      });
    }

    if (!fields.asOfTime) {
      errors.push({
        field: 'asOfTime',
        code: 'BACKTEST_REQUIRES_TIME',
        message: 'Backtest mode requires an as-of time.',
        severity: 'error',
      });
    }

    // Validate date is not in future
    if (fields.asOfDate && fields.asOfTime) {
      const asOfDateTime = new Date(`${fields.asOfDate}T${fields.asOfTime}`);
      if (asOfDateTime > new Date()) {
        errors.push({
          field: 'asOfDate',
          code: 'FUTURE_DATE_NOT_ALLOWED',
          message: 'As-of date cannot be in the future for backtesting.',
          severity: 'error',
        });
      }
    }

    // Isolation level must be set for backtest
    if (!fields.isolationLevel) {
      errors.push({
        field: 'isolationLevel',
        code: 'BACKTEST_REQUIRES_ISOLATION',
        message: 'Backtest mode requires an isolation level.',
        severity: 'error',
      });
    }
  }

  // Warn if changing from recommended temporal mode
  if (fields.temporalMode !== recommendations.temporalMode) {
    errors.push({
      field: 'temporalMode',
      code: 'TEMPORAL_MODE_OVERRIDE',
      message: `Blueprint recommended "${recommendations.temporalMode}" mode. ${recommendations.temporalRationale || ''}`,
      severity: 'warning',
    });
  }

  return errors;
}

// =============================================================================
// MAIN VALIDATION FUNCTION
// =============================================================================

/**
 * Validate blueprint editable fields against constraints and recommendations.
 *
 * @param fields - Current field values
 * @param recommendations - Blueprint recommendations to validate against
 * @returns ValidationResult with errors and warnings
 */
export function validateBlueprintFields(
  fields: BlueprintEditableFields,
  recommendations: BlueprintV2Recommendations
): ValidationResult {
  const errors: ValidationError[] = [];
  const warnings: ValidationError[] = [];

  // 1. Required field validation
  for (const field of REQUIRED_FIELDS) {
    const value = fields[field];
    if (!value || (typeof value === 'string' && !value.trim())) {
      errors.push({
        field,
        code: 'FIELD_REQUIRED',
        message: `${field} is required.`,
        severity: 'error',
      });
    }
  }

  // 2. Project name validation
  if (fields.projectName) {
    const { minLength, maxLength } = FIELD_CONSTRAINTS.projectName;
    if (fields.projectName.length < minLength) {
      errors.push({
        field: 'projectName',
        code: 'NAME_TOO_SHORT',
        message: `Project name must be at least ${minLength} characters.`,
        severity: 'error',
      });
    }
    if (fields.projectName.length > maxLength) {
      errors.push({
        field: 'projectName',
        code: 'NAME_TOO_LONG',
        message: `Project name cannot exceed ${maxLength} characters.`,
        severity: 'error',
      });
    }
  }

  // 3. Tags validation
  if (fields.tags.length > FIELD_CONSTRAINTS.tags.maxCount) {
    errors.push({
      field: 'tags',
      code: 'TOO_MANY_TAGS',
      message: `Maximum ${FIELD_CONSTRAINTS.tags.maxCount} tags allowed.`,
      severity: 'error',
    });
  }
  for (const tag of fields.tags) {
    if (tag.length > FIELD_CONSTRAINTS.tags.maxLength) {
      errors.push({
        field: 'tags',
        code: 'TAG_TOO_LONG',
        message: `Tag "${tag}" exceeds ${FIELD_CONSTRAINTS.tags.maxLength} characters.`,
        severity: 'error',
      });
    }
  }

  // 4. Core type validation
  if (fields.coreType && !recommendations.allowedCores.includes(fields.coreType)) {
    errors.push({
      field: 'coreType',
      code: 'CORE_NOT_ALLOWED',
      message: `"${fields.coreType}" is not compatible with this blueprint. Allowed: ${recommendations.allowedCores.join(', ')}.`,
      severity: 'error',
    });
  }

  // 5. Core type conflict validation
  const coreConflicts = validateCoreTypeConflicts(fields.coreType, recommendations.requiredInputs);
  for (const conflict of coreConflicts) {
    if (conflict.severity === 'error') {
      errors.push(conflict);
    } else {
      warnings.push(conflict);
    }
  }

  // 6. Warn if core differs from recommendation
  if (fields.coreType !== recommendations.recommendedCore) {
    warnings.push({
      field: 'coreType',
      code: 'CORE_OVERRIDE',
      message: `Blueprint recommended "${recommendations.recommendedCore}". ${recommendations.coreRationale || ''}`,
      severity: 'warning',
    });
  }

  // 7. Temporal settings validation
  const temporalErrors = validateTemporalSettings(fields, recommendations);
  for (const err of temporalErrors) {
    if (err.severity === 'error') {
      errors.push(err);
    } else {
      warnings.push(err);
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
  };
}

// =============================================================================
// AUTO-FILL HELPERS
// =============================================================================

/**
 * Extract recommendations from a Blueprint v2 response.
 * This maps the blueprint structure to our recommendations format.
 */
export function extractRecommendationsFromBlueprint(
  blueprint: {
    intent?: {
      business_question?: string;
      decision_context?: string;
      success_criteria?: string[];
    };
    prediction_target?: {
      primary_metric?: string;
      target_population?: string;
    };
    horizon?: {
      prediction_window?: string;
      data_freshness_requirement?: string;
    };
    required_inputs?: Array<{
      input_name: string;
      input_type: string;
      required: boolean;
      description: string;
    }>;
  },
  goalText: string
): BlueprintV2Recommendations {
  // Generate project name from goal or business question
  const projectName = generateProjectName(
    blueprint.intent?.business_question || goalText
  );

  // Extract tags from intent and prediction target
  const tags = extractTags(blueprint);

  // Determine recommended core based on blueprint structure
  const { recommendedCore, allowedCores, coreRationale } = analyzeRecommendedCore(blueprint);

  // Analyze temporal requirements
  const { temporalMode, temporalRationale, suggestedCutoffDate, suggestedIsolationLevel } =
    analyzeTemporalRequirements(blueprint);

  // Map required inputs
  const requiredInputs = (blueprint.required_inputs || []).map(input => ({
    name: input.input_name,
    type: input.input_type,
    required: input.required,
    description: input.description,
  }));

  return {
    projectName,
    projectNameRationale: 'Generated from blueprint business question',
    tags,
    tagsRationale: 'Extracted from blueprint intent and prediction target',
    recommendedCore,
    coreRationale,
    allowedCores,
    temporalMode,
    temporalRationale,
    suggestedCutoffDate,
    suggestedIsolationLevel,
    requiredInputs,
  };
}

/**
 * Generate a project name from text
 */
function generateProjectName(text: string): string {
  if (!text.trim()) return '';
  const name = text.slice(0, 50).trim();
  return name.charAt(0).toUpperCase() + name.slice(1) + (text.length > 50 ? '...' : '');
}

/**
 * Extract tags from blueprint content
 */
function extractTags(blueprint: {
  intent?: { business_question?: string; decision_context?: string };
  prediction_target?: { primary_metric?: string; target_population?: string };
}): string[] {
  const tags: string[] = [];
  const text = [
    blueprint.intent?.business_question,
    blueprint.intent?.decision_context,
    blueprint.prediction_target?.primary_metric,
    blueprint.prediction_target?.target_population,
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();

  // Extract domain-specific keywords as tags
  const keywordMap: Record<string, string> = {
    election: 'politics',
    vote: 'politics',
    voting: 'politics',
    political: 'politics',
    market: 'market',
    brand: 'branding',
    product: 'product',
    consumer: 'consumer',
    campaign: 'campaign',
    social: 'social',
    sentiment: 'sentiment',
    perception: 'perception',
    forecast: 'forecast',
    prediction: 'prediction',
  };

  for (const [keyword, tag] of Object.entries(keywordMap)) {
    if (text.includes(keyword) && !tags.includes(tag)) {
      tags.push(tag);
      if (tags.length >= 5) break;
    }
  }

  return tags;
}

/**
 * Analyze blueprint to determine recommended core type
 */
function analyzeRecommendedCore(blueprint: {
  required_inputs?: Array<{ input_type: string; required: boolean }>;
  intent?: { decision_context?: string };
}): { recommendedCore: CoreType; allowedCores: CoreType[]; coreRationale: string } {
  const hasPersonas = blueprint.required_inputs?.some(
    input => input.input_type === 'PERSONA_SET'
  );
  const hasEvents = blueprint.required_inputs?.some(
    input => input.input_type === 'EVENT_SCRIPT_SET'
  );
  const requiresPersonas = blueprint.required_inputs?.some(
    input => input.input_type === 'PERSONA_SET' && input.required
  );

  // Determine allowed cores
  const allowedCores: CoreType[] = ['collective', 'hybrid'];
  if (!requiresPersonas) {
    allowedCores.push('targeted');
  }

  // Determine recommendation
  let recommendedCore: CoreType = 'collective';
  let coreRationale = 'Collective dynamics is suitable for population-level predictions.';

  if (hasPersonas && hasEvents) {
    recommendedCore = 'hybrid';
    coreRationale = 'Blueprint requires both personas and events. Hybrid mode provides full support.';
  } else if (hasPersonas) {
    recommendedCore = 'hybrid';
    coreRationale = 'Blueprint includes personas. Hybrid mode combines collective and targeted approaches.';
  } else if (
    blueprint.intent?.decision_context?.toLowerCase().includes('individual') ||
    blueprint.intent?.decision_context?.toLowerCase().includes('persona')
  ) {
    recommendedCore = 'hybrid';
    coreRationale = 'Decision context suggests individual-level analysis. Hybrid mode recommended.';
  }

  return { recommendedCore, allowedCores, coreRationale };
}

/**
 * Analyze blueprint for temporal requirements
 */
function analyzeTemporalRequirements(blueprint: {
  horizon?: { prediction_window?: string; data_freshness_requirement?: string };
  intent?: { decision_context?: string };
}): {
  temporalMode: TemporalMode;
  temporalRationale: string;
  suggestedCutoffDate?: string;
  suggestedIsolationLevel?: IsolationLevel;
} {
  const context = blueprint.intent?.decision_context?.toLowerCase() || '';
  const horizon = blueprint.horizon;

  // Check for backtest indicators
  const backtestKeywords = ['historical', 'backtest', 'past', 'retrospective', 'validate'];
  const needsBacktest = backtestKeywords.some(k => context.includes(k));

  if (needsBacktest) {
    return {
      temporalMode: 'backtest',
      temporalRationale: 'Decision context suggests historical validation is needed.',
      suggestedIsolationLevel: 2, // Strict for publishable results
    };
  }

  // Check data freshness requirements
  if (horizon?.data_freshness_requirement?.toLowerCase().includes('historical')) {
    return {
      temporalMode: 'backtest',
      temporalRationale: 'Blueprint requires historical data access.',
      suggestedIsolationLevel: 2,
    };
  }

  return {
    temporalMode: 'live',
    temporalRationale: 'Real-time predictions using latest data.',
  };
}

// =============================================================================
// OVERRIDE TRACKING
// =============================================================================

/**
 * Create override metadata for tracking field changes
 */
export function createOverrideMetadata(
  field: string,
  originalValue: unknown,
  newValue: unknown,
  reason?: string
): OverrideMetadata {
  return {
    field,
    originalValue,
    newValue,
    timestamp: new Date().toISOString(),
    reason,
  };
}

/**
 * Check if a field value differs from the recommendation
 */
export function hasOverride(
  field: keyof BlueprintEditableFields,
  currentValue: unknown,
  recommendations: BlueprintV2Recommendations
): boolean {
  switch (field) {
    case 'projectName':
      return currentValue !== recommendations.projectName;
    case 'tags':
      return JSON.stringify(currentValue) !== JSON.stringify(recommendations.tags);
    case 'coreType':
      return currentValue !== recommendations.recommendedCore;
    case 'temporalMode':
      return currentValue !== recommendations.temporalMode;
    default:
      return false;
  }
}

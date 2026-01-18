'use client';

/**
 * Blueprint V2 Preview Component
 * Reference: Slice 2A - Blueprint v2
 *
 * Read-only display of the Blueprint v2 structured data.
 * Shows all sections: intent, prediction target, horizon, output format,
 * evaluation plan, and required inputs.
 */

import { motion } from 'framer-motion';
import {
  Target,
  Clock,
  FileOutput,
  CheckSquare,
  Database,
  Sparkles,
  Brain,
  AlertCircle,
  Loader2,
  ExternalLink,
  Info,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useBlueprintV2ByProject, useBlueprintV2 } from '@/hooks/useApi';
import type {
  BlueprintV2Response,
  BlueprintV2Intent,
  BlueprintV2PredictionTarget,
  BlueprintV2Horizon,
  BlueprintV2OutputFormat,
  BlueprintV2EvaluationPlan,
  BlueprintV2RequiredInput,
  BlueprintV2Provenance,
} from '@/lib/api';

interface BlueprintV2PreviewProps {
  /** Project ID to fetch Blueprint v2 for */
  projectId?: string;
  /** Or provide Blueprint ID directly */
  blueprintId?: string;
  /** Pre-loaded data (optional) */
  data?: BlueprintV2Response;
  /** Additional CSS classes */
  className?: string;
}

export function BlueprintV2Preview({
  projectId,
  blueprintId,
  data: preloadedData,
  className,
}: BlueprintV2PreviewProps) {
  // Fetch data if not preloaded
  const byProjectQuery = useBlueprintV2ByProject(
    !preloadedData && !blueprintId ? projectId : undefined
  );
  const byIdQuery = useBlueprintV2(
    !preloadedData && blueprintId ? blueprintId : undefined
  );

  const data = preloadedData || byProjectQuery.data || byIdQuery.data;
  const isLoading = byProjectQuery.isLoading || byIdQuery.isLoading;
  const error = byProjectQuery.error || byIdQuery.error;

  // Loading state
  if (isLoading) {
    return (
      <div className={cn('flex items-center justify-center p-8', className)}>
        <Loader2 className="h-8 w-8 animate-spin text-cyan-400" />
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className={cn('p-6 text-center', className)}>
        <AlertCircle className="h-12 w-12 text-red-400 mx-auto mb-4" />
        <h3 className="text-lg font-mono text-white mb-2">
          Unable to Load Blueprint
        </h3>
        <p className="text-sm text-gray-400 font-mono">
          {error instanceof Error ? error.message : 'An error occurred'}
        </p>
      </div>
    );
  }

  // No data state
  if (!data) {
    return (
      <div className={cn('p-6 text-center', className)}>
        <Info className="h-12 w-12 text-gray-500 mx-auto mb-4" />
        <h3 className="text-lg font-mono text-white mb-2">
          No Blueprint Available
        </h3>
        <p className="text-sm text-gray-400 font-mono">
          Generate a Blueprint v2 to see the preview here.
        </p>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn('space-y-6', className)}
    >
      {/* Header with provenance */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded bg-cyan-500/20 border border-cyan-500/30">
            <Sparkles className="h-5 w-5 text-cyan-400" />
          </div>
          <div>
            <h2 className="text-xl font-mono text-white">Blueprint v2</h2>
            <p className="text-sm text-gray-400 font-mono">
              AI-Generated Simulation Blueprint
            </p>
          </div>
        </div>
        {data.provenance && (
          <ProvenanceBadge provenance={data.provenance} />
        )}
      </div>

      {/* Intent Section */}
      {data.intent && (
        <SectionCard
          icon={Brain}
          title="Intent"
          description="What you're trying to understand or decide"
        >
          <IntentSection intent={data.intent} />
        </SectionCard>
      )}

      {/* Prediction Target Section */}
      {data.prediction_target && (
        <SectionCard
          icon={Target}
          title="Prediction Target"
          description="What the simulation will predict"
        >
          <PredictionTargetSection target={data.prediction_target} />
        </SectionCard>
      )}

      {/* Horizon Section */}
      {data.horizon && (
        <SectionCard
          icon={Clock}
          title="Time Horizon"
          description="Timing and freshness requirements"
        >
          <HorizonSection horizon={data.horizon} />
        </SectionCard>
      )}

      {/* Output Format Section */}
      {data.output_format && (
        <SectionCard
          icon={FileOutput}
          title="Output Format"
          description="How results will be delivered"
        >
          <OutputFormatSection format={data.output_format} />
        </SectionCard>
      )}

      {/* Evaluation Plan Section */}
      {data.evaluation_plan && (
        <SectionCard
          icon={CheckSquare}
          title="Evaluation Plan"
          description="How accuracy will be measured"
        >
          <EvaluationPlanSection plan={data.evaluation_plan} />
        </SectionCard>
      )}

      {/* Required Inputs Section */}
      {data.required_inputs && data.required_inputs.length > 0 && (
        <SectionCard
          icon={Database}
          title="Required Inputs"
          description="Data needed for the simulation"
        >
          <RequiredInputsSection inputs={data.required_inputs} />
        </SectionCard>
      )}
    </motion.div>
  );
}

// Sub-components

interface SectionCardProps {
  icon: typeof Target;
  title: string;
  description: string;
  children: React.ReactNode;
}

function SectionCard({ icon: Icon, title, description, children }: SectionCardProps) {
  return (
    <Card className="bg-black/40 border-white/10">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded bg-white/5 border border-white/10">
            <Icon className="h-4 w-4 text-cyan-400" />
          </div>
          <div>
            <CardTitle className="text-base font-mono text-white">
              {title}
            </CardTitle>
            <p className="text-xs text-gray-500 font-mono">{description}</p>
          </div>
        </div>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

function ProvenanceBadge({ provenance }: { provenance: BlueprintV2Provenance }) {
  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded bg-white/5 border border-white/10">
      <Sparkles className="h-3 w-3 text-purple-400" />
      <span className="text-xs font-mono text-gray-400">
        {provenance.model || 'AI Generated'}
      </span>
      {provenance.generated_at && (
        <span className="text-xs font-mono text-gray-500">
          {new Date(provenance.generated_at).toLocaleDateString()}
        </span>
      )}
    </div>
  );
}

function IntentSection({ intent }: { intent: BlueprintV2Intent }) {
  return (
    <div className="space-y-4">
      <div>
        <label className="text-xs text-gray-500 font-mono uppercase tracking-wider">
          Business Question
        </label>
        <p className="text-sm text-white font-mono mt-1">
          {intent.business_question}
        </p>
      </div>
      <div>
        <label className="text-xs text-gray-500 font-mono uppercase tracking-wider">
          Decision Context
        </label>
        <p className="text-sm text-gray-300 font-mono mt-1">
          {intent.decision_context}
        </p>
      </div>
      {intent.success_criteria && intent.success_criteria.length > 0 && (
        <div>
          <label className="text-xs text-gray-500 font-mono uppercase tracking-wider">
            Success Criteria
          </label>
          <ul className="mt-2 space-y-1">
            {intent.success_criteria.map((criterion, i) => (
              <li key={i} className="flex items-start gap-2">
                <CheckSquare className="h-3 w-3 text-green-400 mt-1 flex-shrink-0" />
                <span className="text-sm text-gray-300 font-mono">{criterion}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function PredictionTargetSection({ target }: { target: BlueprintV2PredictionTarget }) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="text-xs text-gray-500 font-mono uppercase tracking-wider">
            Primary Metric
          </label>
          <p className="text-sm text-cyan-400 font-mono mt-1 font-medium">
            {target.primary_metric}
          </p>
        </div>
        <div>
          <label className="text-xs text-gray-500 font-mono uppercase tracking-wider">
            Target Population
          </label>
          <p className="text-sm text-white font-mono mt-1">
            {target.target_population}
          </p>
        </div>
      </div>
      <div>
        <label className="text-xs text-gray-500 font-mono uppercase tracking-wider">
          Metric Definition
        </label>
        <p className="text-sm text-gray-300 font-mono mt-1">
          {target.metric_definition}
        </p>
      </div>
      {target.segmentation && target.segmentation.length > 0 && (
        <div>
          <label className="text-xs text-gray-500 font-mono uppercase tracking-wider">
            Segmentation
          </label>
          <div className="flex flex-wrap gap-2 mt-2">
            {target.segmentation.map((segment, i) => (
              <Badge
                key={i}
                variant="outline"
                className="border-cyan-500/30 text-cyan-400 font-mono text-xs"
              >
                {segment}
              </Badge>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function HorizonSection({ horizon }: { horizon: BlueprintV2Horizon }) {
  return (
    <div className="grid grid-cols-3 gap-4">
      <div>
        <label className="text-xs text-gray-500 font-mono uppercase tracking-wider">
          Prediction Window
        </label>
        <p className="text-sm text-white font-mono mt-1">
          {horizon.prediction_window}
        </p>
      </div>
      <div>
        <label className="text-xs text-gray-500 font-mono uppercase tracking-wider">
          Data Freshness
        </label>
        <p className="text-sm text-white font-mono mt-1">
          {horizon.data_freshness_requirement}
        </p>
      </div>
      <div>
        <label className="text-xs text-gray-500 font-mono uppercase tracking-wider">
          Update Frequency
        </label>
        <p className="text-sm text-white font-mono mt-1">
          {horizon.update_frequency}
        </p>
      </div>
    </div>
  );
}

function OutputFormatSection({ format }: { format: BlueprintV2OutputFormat }) {
  return (
    <div className="grid grid-cols-2 gap-4">
      <div>
        <label className="text-xs text-gray-500 font-mono uppercase tracking-wider">
          Format Type
        </label>
        <p className="text-sm text-white font-mono mt-1">
          {format.format_type}
        </p>
      </div>
      <div>
        <label className="text-xs text-gray-500 font-mono uppercase tracking-wider">
          Granularity
        </label>
        <p className="text-sm text-white font-mono mt-1">
          {format.granularity}
        </p>
      </div>
      <div>
        <label className="text-xs text-gray-500 font-mono uppercase tracking-wider">
          Confidence Intervals
        </label>
        <p className="text-sm text-white font-mono mt-1">
          {format.confidence_intervals ? 'Yes' : 'No'}
        </p>
      </div>
      <div>
        <label className="text-xs text-gray-500 font-mono uppercase tracking-wider">
          Explanation Depth
        </label>
        <p className="text-sm text-white font-mono mt-1">
          {format.explanation_depth}
        </p>
      </div>
    </div>
  );
}

function EvaluationPlanSection({ plan }: { plan: BlueprintV2EvaluationPlan }) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="text-xs text-gray-500 font-mono uppercase tracking-wider">
            Validation Approach
          </label>
          <p className="text-sm text-white font-mono mt-1">
            {plan.validation_approach}
          </p>
        </div>
        {plan.backtesting_period && (
          <div>
            <label className="text-xs text-gray-500 font-mono uppercase tracking-wider">
              Backtesting Period
            </label>
            <p className="text-sm text-white font-mono mt-1">
              {plan.backtesting_period}
            </p>
          </div>
        )}
      </div>
      {plan.accuracy_thresholds && Object.keys(plan.accuracy_thresholds).length > 0 && (
        <div>
          <label className="text-xs text-gray-500 font-mono uppercase tracking-wider">
            Accuracy Thresholds
          </label>
          <div className="flex flex-wrap gap-2 mt-2">
            {Object.entries(plan.accuracy_thresholds).map(([key, value]) => (
              <Badge
                key={key}
                variant="outline"
                className="border-green-500/30 text-green-400 font-mono text-xs"
              >
                {key}: {typeof value === 'number' ? `${(value * 100).toFixed(0)}%` : value}
              </Badge>
            ))}
          </div>
        </div>
      )}
      {plan.comparison_benchmarks && plan.comparison_benchmarks.length > 0 && (
        <div>
          <label className="text-xs text-gray-500 font-mono uppercase tracking-wider">
            Comparison Benchmarks
          </label>
          <div className="flex flex-wrap gap-2 mt-2">
            {plan.comparison_benchmarks.map((benchmark, i) => (
              <Badge
                key={i}
                variant="outline"
                className="border-purple-500/30 text-purple-400 font-mono text-xs"
              >
                {benchmark}
              </Badge>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function RequiredInputsSection({ inputs }: { inputs: BlueprintV2RequiredInput[] }) {
  return (
    <div className="space-y-3">
      {inputs.map((input, i) => (
        <div
          key={i}
          className={cn(
            'p-3 rounded border',
            input.required
              ? 'border-cyan-500/30 bg-cyan-500/5'
              : 'border-white/10 bg-white/5'
          )}
        >
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm font-mono text-white font-medium">
              {input.input_name}
            </span>
            <div className="flex items-center gap-2">
              <Badge
                variant="outline"
                className={cn(
                  'text-xs font-mono',
                  input.required
                    ? 'border-cyan-500/30 text-cyan-400'
                    : 'border-gray-500/30 text-gray-400'
                )}
              >
                {input.input_type}
              </Badge>
              {input.required && (
                <Badge
                  variant="outline"
                  className="border-red-500/30 text-red-400 text-xs font-mono"
                >
                  Required
                </Badge>
              )}
            </div>
          </div>
          <p className="text-xs text-gray-400 font-mono">
            {input.description}
          </p>
          {input.source_suggestion && (
            <p className="text-xs text-gray-500 font-mono mt-2 flex items-center gap-1">
              <ExternalLink className="h-3 w-3" />
              Suggested source: {input.source_suggestion}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

export default BlueprintV2Preview;

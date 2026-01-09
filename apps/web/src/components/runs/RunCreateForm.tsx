'use client';

/**
 * RunCreateForm Component
 * Form for creating new simulation runs with spec-compliant configuration.
 * Reference: project.md §6.5 (RunConfig)
 */

import { memo, useState, useCallback } from 'react';
import {
  Play,
  Settings,
  Shuffle,
  Clock,
  Hash,
  ChevronDown,
  ChevronUp,
  Info,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import type { SubmitRunInput, SeedStrategy } from '@/lib/api';

// Form-specific input type (maps to SubmitRunInput + config_overrides)
export interface RunFormInput {
  nodeId: string;
  label?: string;
  seed?: number;
  seedStrategy: SeedStrategy;
  horizon: number;
  tickRate: number;
  loggingLevel: 'minimal' | 'standard' | 'detailed' | 'debug';
  autoStart: boolean;
}

interface RunCreateFormProps {
  projectId: string;
  nodeId?: string;
  onSubmit: (input: SubmitRunInput) => void;
  onCancel?: () => void;
  isSubmitting?: boolean;
  className?: string;
}

const seedStrategies: { value: SeedStrategy; label: string; description: string }[] = [
  {
    value: 'single',
    label: 'Single Seed',
    description: 'Use one seed for deterministic reproduction',
  },
  {
    value: 'multi',
    label: 'Multi Seed',
    description: 'Run multiple times with different seeds',
  },
  {
    value: 'adaptive',
    label: 'Adaptive',
    description: 'Automatically adjust based on variance',
  },
];

const loggingLevels = [
  { value: 'minimal', label: 'Minimal', description: 'Only final results' },
  { value: 'standard', label: 'Standard', description: 'Key events and outcomes' },
  { value: 'detailed', label: 'Detailed', description: 'Full telemetry data' },
  { value: 'debug', label: 'Debug', description: 'Everything (large output)' },
];

export const RunCreateForm = memo(function RunCreateForm({
  projectId,
  nodeId,
  onSubmit,
  onCancel,
  isSubmitting,
  className,
}: RunCreateFormProps) {
  // Form state
  const [label, setLabel] = useState('');
  const [seed, setSeed] = useState<number | undefined>(undefined);
  const [seedStrategy, setSeedStrategy] = useState<SeedStrategy>('single');
  const [horizon, setHorizon] = useState(100);
  const [tickRate, setTickRate] = useState(1000);
  const [loggingLevel, setLoggingLevel] = useState<'minimal' | 'standard' | 'detailed' | 'debug'>('standard');
  const [autoStart, setAutoStart] = useState(true);

  // UI state
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Validation
  const validate = useCallback(() => {
    const newErrors: Record<string, string> = {};

    if (horizon < 1 || horizon > 10000) {
      newErrors.horizon = 'Horizon must be between 1 and 10000 ticks';
    }
    if (tickRate < 100 || tickRate > 60000) {
      newErrors.tickRate = 'Tick rate must be between 100ms and 60000ms';
    }
    if (seed !== undefined && (seed < 0 || seed > Number.MAX_SAFE_INTEGER)) {
      newErrors.seed = 'Invalid seed value';
    }
    if (!nodeId) {
      newErrors.nodeId = 'Node ID is required to create a run';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [horizon, tickRate, seed, nodeId]);

  // Handle submit
  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();

      if (!validate() || !nodeId) return;

      // Build SubmitRunInput matching backend CreateRunRequest
      const input: SubmitRunInput = {
        project_id: projectId,
        node_id: nodeId,
        label: label || undefined,
        config: {
          run_mode: 'society',
          max_ticks: horizon,
          agent_batch_size: 100,
          society_mode: {
            tick_rate: tickRate,
            logging_level: loggingLevel,
          },
        },
        seeds: [seed ?? Math.floor(Math.random() * 1000000000)],
        auto_start: autoStart,
      };

      onSubmit(input);
    },
    [
      projectId,
      nodeId,
      label,
      seed,
      horizon,
      tickRate,
      loggingLevel,
      autoStart,
      validate,
      onSubmit,
    ]
  );

  // Generate random seed
  const generateSeed = () => {
    setSeed(Math.floor(Math.random() * 1000000000));
  };

  return (
    <form onSubmit={handleSubmit} className={cn('space-y-6', className)}>
      {/* Header */}
      <div className="flex items-center gap-3 pb-4 border-b border-white/10">
        <div className="p-2 bg-cyan-500/10">
          <Play className="w-5 h-5 text-cyan-400" />
        </div>
        <div>
          <h3 className="text-lg font-mono font-bold text-white">
            Create New Run
          </h3>
          <p className="text-xs font-mono text-white/40">
            Configure simulation parameters
          </p>
        </div>
      </div>

      {/* Node ID Warning */}
      {!nodeId && (
        <div className="flex items-start gap-2 p-3 bg-yellow-500/10 border border-yellow-500/30">
          <Info className="w-4 h-4 text-yellow-400 flex-shrink-0 mt-0.5" />
          <p className="text-xs font-mono text-yellow-400">
            No node selected. Please select a node in the Universe Map to create a run.
          </p>
        </div>
      )}

      {/* Basic Configuration */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 mb-3">
          <Settings className="w-4 h-4 text-white/40" />
          <span className="text-xs font-mono text-white/40 uppercase tracking-wider">
            Basic Configuration
          </span>
        </div>

        {/* Label */}
        <div className="space-y-2">
          <label className="block text-xs font-mono text-white/60">
            Run Label (optional)
          </label>
          <input
            type="text"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="e.g., Baseline scenario v1"
            className="w-full h-9 px-3 text-sm font-mono bg-black border border-white/10 text-white placeholder:text-white/30 focus:outline-none focus:border-cyan-500/50"
          />
        </div>

        {/* Horizon (simulation steps) */}
        <div className="space-y-2">
          <label className="flex items-center gap-2 text-xs font-mono text-white/60">
            <Clock className="w-3.5 h-3.5" />
            Horizon (simulation ticks)
          </label>
          <input
            type="number"
            value={horizon}
            onChange={(e) => setHorizon(parseInt(e.target.value) || 100)}
            min={1}
            max={10000}
            className={cn(
              'w-full h-9 px-3 text-sm font-mono bg-black border text-white focus:outline-none',
              errors.horizon
                ? 'border-red-500/50 focus:border-red-500'
                : 'border-white/10 focus:border-cyan-500/50'
            )}
          />
          {errors.horizon && (
            <p className="text-xs font-mono text-red-400">{errors.horizon}</p>
          )}
        </div>
      </div>

      {/* Seed Configuration */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 mb-3">
          <Shuffle className="w-4 h-4 text-white/40" />
          <span className="text-xs font-mono text-white/40 uppercase tracking-wider">
            Seed Configuration
          </span>
        </div>

        {/* Seed Strategy */}
        <div className="space-y-2">
          <label className="text-xs font-mono text-white/60">Strategy</label>
          <div className="grid grid-cols-3 gap-2">
            {seedStrategies.map((strategy) => (
              <button
                key={strategy.value}
                type="button"
                onClick={() => setSeedStrategy(strategy.value)}
                className={cn(
                  'p-3 text-left border transition-colors',
                  seedStrategy === strategy.value
                    ? 'bg-cyan-500/10 border-cyan-500/50 text-white'
                    : 'bg-black border-white/10 text-white/60 hover:border-white/20'
                )}
              >
                <span className="block text-xs font-mono font-bold mb-1">
                  {strategy.label}
                </span>
                <span className="block text-[10px] font-mono opacity-60">
                  {strategy.description}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Seed Value */}
        <div className="space-y-2">
          <label className="flex items-center gap-2 text-xs font-mono text-white/60">
            <Hash className="w-3.5 h-3.5" />
            Seed Value
          </label>
          <div className="flex gap-2">
            <input
              type="number"
              value={seed || ''}
              onChange={(e) => setSeed(e.target.value ? parseInt(e.target.value) : undefined)}
              placeholder="Auto-generate if empty"
              className={cn(
                'flex-1 h-9 px-3 text-sm font-mono bg-black border text-white placeholder:text-white/30 focus:outline-none',
                errors.seed
                  ? 'border-red-500/50 focus:border-red-500'
                  : 'border-white/10 focus:border-cyan-500/50'
              )}
            />
            <Button
              type="button"
              variant="secondary"
              size="default"
              onClick={generateSeed}
            >
              <Shuffle className="w-3.5 h-3.5" />
            </Button>
          </div>
          {errors.seed && (
            <p className="text-xs font-mono text-red-400">{errors.seed}</p>
          )}
          <p className="flex items-start gap-1.5 text-[10px] font-mono text-white/30">
            <Info className="w-3 h-3 flex-shrink-0 mt-0.5" />
            Same seed + config = same results (deterministic)
          </p>
        </div>
      </div>

      {/* Advanced Settings (Collapsible) */}
      <div className="border border-white/10">
        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="w-full flex items-center justify-between p-3 text-xs font-mono text-white/60 hover:text-white transition-colors"
        >
          <span className="uppercase tracking-wider">Advanced Settings</span>
          {showAdvanced ? (
            <ChevronUp className="w-4 h-4" />
          ) : (
            <ChevronDown className="w-4 h-4" />
          )}
        </button>

        {showAdvanced && (
          <div className="p-4 pt-0 space-y-4 border-t border-white/10">
            {/* Tick Rate */}
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-xs font-mono text-white/60">
                <Clock className="w-3.5 h-3.5" />
                Tick Rate (ms)
              </label>
              <input
                type="number"
                value={tickRate}
                onChange={(e) => setTickRate(parseInt(e.target.value) || 1000)}
                min={100}
                max={60000}
                className={cn(
                  'w-full h-9 px-3 text-sm font-mono bg-black border text-white focus:outline-none',
                  errors.tickRate
                    ? 'border-red-500/50 focus:border-red-500'
                    : 'border-white/10 focus:border-cyan-500/50'
                )}
              />
              {errors.tickRate && (
                <p className="text-xs font-mono text-red-400">{errors.tickRate}</p>
              )}
            </div>

            {/* Logging Level */}
            <div className="space-y-2">
              <label className="text-xs font-mono text-white/60">
                Logging Level
              </label>
              <div className="grid grid-cols-2 gap-2">
                {loggingLevels.map((level) => (
                  <button
                    key={level.value}
                    type="button"
                    onClick={() => setLoggingLevel(level.value as typeof loggingLevel)}
                    className={cn(
                      'p-2 text-left border transition-colors',
                      loggingLevel === level.value
                        ? 'bg-white/5 border-white/30 text-white'
                        : 'bg-black border-white/10 text-white/60 hover:border-white/20'
                    )}
                  >
                    <span className="block text-xs font-mono font-bold">
                      {level.label}
                    </span>
                    <span className="block text-[10px] font-mono opacity-60">
                      {level.description}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {/* Auto Start */}
            <div className="flex items-center justify-between p-3 bg-white/5 border border-white/10">
              <div>
                <span className="block text-xs font-mono text-white">
                  Auto-start after creation
                </span>
                <span className="block text-[10px] font-mono text-white/40">
                  Run will start immediately
                </span>
              </div>
              <button
                type="button"
                onClick={() => setAutoStart(!autoStart)}
                className={cn(
                  'w-10 h-5 rounded-full transition-colors',
                  autoStart ? 'bg-cyan-500' : 'bg-white/20'
                )}
              >
                <div
                  className={cn(
                    'w-4 h-4 bg-white rounded-full transition-transform',
                    autoStart ? 'translate-x-5' : 'translate-x-0.5'
                  )}
                />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Context Info */}
      <div className="flex items-start gap-2 p-3 bg-white/5 border border-white/10">
        <Info className="w-4 h-4 text-white/40 flex-shrink-0 mt-0.5" />
        <div className="text-[10px] font-mono text-white/40 space-y-1">
          <p>Project: {projectId.slice(0, 12)}...</p>
          {nodeId && <p>Node: {nodeId.slice(0, 12)}...</p>}
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-end gap-3 pt-4 border-t border-white/10">
        {onCancel && (
          <Button
            type="button"
            variant="secondary"
            onClick={onCancel}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
        )}
        <Button
          type="submit"
          variant="primary"
          disabled={isSubmitting || !nodeId}
        >
          {isSubmitting ? (
            <>
              <Settings className="w-3.5 h-3.5 mr-1.5 animate-spin" />
              Creating...
            </>
          ) : (
            <>
              <Play className="w-3.5 h-3.5 mr-1.5" />
              {autoStart ? 'Create & Start' : 'Create Run'}
            </>
          )}
        </Button>
      </div>
    </form>
  );
});

export default RunCreateForm;

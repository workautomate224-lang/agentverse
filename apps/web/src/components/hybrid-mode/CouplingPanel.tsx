'use client';

/**
 * Coupling Panel Component
 * Reference: Interaction_design.md §5.14
 *
 * Configure coupling settings between key actors and society.
 */

import { Settings2, ArrowRight, ArrowLeft, ArrowLeftRight, Timer } from 'lucide-react';
import { CouplingConfig, CouplingDirection, CouplingStrength } from '@/lib/api';
import { Slider } from '@/components/ui/slider';
import { cn } from '@/lib/utils';

interface CouplingPanelProps {
  config: CouplingConfig;
  onChange: (config: CouplingConfig) => void;
  numTicks: number;
  onNumTicksChange: (ticks: number) => void;
}

const DIRECTIONS: { value: CouplingDirection; label: string; icon: typeof ArrowRight; description: string }[] = [
  { value: 'actor_to_society', label: 'Actor → Society', icon: ArrowRight, description: 'Actors influence society' },
  { value: 'society_to_actor', label: 'Society → Actor', icon: ArrowLeft, description: 'Society influences actors' },
  { value: 'bidirectional', label: 'Bidirectional', icon: ArrowLeftRight, description: 'Mutual influence' },
];

const STRENGTHS: { value: CouplingStrength; label: string; color: string }[] = [
  { value: 'none', label: 'None', color: 'bg-white/20' },
  { value: 'weak', label: 'Weak', color: 'bg-green-500/50' },
  { value: 'moderate', label: 'Moderate', color: 'bg-yellow-500/50' },
  { value: 'strong', label: 'Strong', color: 'bg-orange-500/50' },
  { value: 'dominant', label: 'Dominant', color: 'bg-red-500/50' },
];

export function CouplingPanel({
  config,
  onChange,
  numTicks,
  onNumTicksChange,
}: CouplingPanelProps) {
  const handleDirectionChange = (direction: CouplingDirection) => {
    onChange({ ...config, direction });
  };

  const handleActorStrengthChange = (strength: CouplingStrength) => {
    onChange({ ...config, actor_influence_strength: strength });
  };

  const handleSocietyStrengthChange = (strength: CouplingStrength) => {
    onChange({ ...config, society_feedback_strength: strength });
  };

  const handleDecayRateChange = (value: number[]) => {
    onChange({ ...config, influence_decay_rate: value[0] });
  };

  const handleAmplificationChange = (value: number[]) => {
    onChange({ ...config, actor_action_amplification: value[0] });
  };

  const handlePressureWeightChange = (value: number[]) => {
    onChange({ ...config, society_pressure_weight: value[0] });
  };

  const handleSyncIntervalChange = (value: number[]) => {
    onChange({ ...config, synchronization_interval: value[0] });
  };

  return (
    <div className="p-4 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Settings2 className="h-4 w-4 text-purple-400" />
        <h3 className="text-sm font-medium">Coupling Settings</h3>
      </div>

      {/* Direction */}
      <div>
        <span className="text-xs text-white/60 block mb-2">Coupling Direction</span>
        <div className="grid grid-cols-3 gap-1">
          {DIRECTIONS.map((dir) => {
            const Icon = dir.icon;
            const isSelected = config.direction === dir.value;
            return (
              <button
                key={dir.value}
                onClick={() => handleDirectionChange(dir.value)}
                className={cn(
                  'p-2 border text-center transition-all',
                  isSelected
                    ? 'bg-purple-500/20 border-purple-500/50'
                    : 'bg-white/5 border-white/10 hover:border-white/30'
                )}
                title={dir.description}
              >
                <Icon className={cn('h-4 w-4 mx-auto mb-1', isSelected ? 'text-purple-400' : 'text-white/40')} />
                <span className={cn('text-xs', isSelected ? 'text-purple-300' : 'text-white/60')}>
                  {dir.label.split(' ')[0]}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Actor Influence Strength */}
      {(config.direction === 'actor_to_society' || config.direction === 'bidirectional') && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-white/60">Actor Influence</span>
            <span className="text-xs text-purple-400 capitalize">{config.actor_influence_strength}</span>
          </div>
          <div className="flex gap-1">
            {STRENGTHS.map((str) => (
              <button
                key={str.value}
                onClick={() => handleActorStrengthChange(str.value)}
                className={cn(
                  'flex-1 py-1.5 text-xs border transition-all',
                  config.actor_influence_strength === str.value
                    ? `${str.color} border-purple-500/50`
                    : 'bg-white/5 border-white/10 hover:border-white/30'
                )}
              >
                {str.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Society Feedback Strength */}
      {(config.direction === 'society_to_actor' || config.direction === 'bidirectional') && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-white/60">Society Feedback</span>
            <span className="text-xs text-cyan-400 capitalize">{config.society_feedback_strength}</span>
          </div>
          <div className="flex gap-1">
            {STRENGTHS.map((str) => (
              <button
                key={str.value}
                onClick={() => handleSocietyStrengthChange(str.value)}
                className={cn(
                  'flex-1 py-1.5 text-xs border transition-all',
                  config.society_feedback_strength === str.value
                    ? `${str.color} border-cyan-500/50`
                    : 'bg-white/5 border-white/10 hover:border-white/30'
                )}
              >
                {str.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Advanced Settings */}
      <div className="pt-4 border-t border-white/10 space-y-4">
        <span className="text-xs text-white/40 block">Advanced Settings</span>

        {/* Influence Decay */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-white/60">Influence Decay Rate</span>
            <span className="text-xs font-mono text-white/40">{config.influence_decay_rate.toFixed(2)}</span>
          </div>
          <Slider
            value={[config.influence_decay_rate]}
            onValueChange={handleDecayRateChange}
            min={0}
            max={1}
            step={0.05}
            className="w-full"
          />
        </div>

        {/* Actor Amplification */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-white/60">Actor Amplification</span>
            <span className="text-xs font-mono text-white/40">{config.actor_action_amplification.toFixed(1)}x</span>
          </div>
          <Slider
            value={[config.actor_action_amplification]}
            onValueChange={handleAmplificationChange}
            min={0.5}
            max={5}
            step={0.1}
            className="w-full"
          />
        </div>

        {/* Society Pressure Weight */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-white/60">Society Pressure Weight</span>
            <span className="text-xs font-mono text-white/40">{config.society_pressure_weight.toFixed(2)}</span>
          </div>
          <Slider
            value={[config.society_pressure_weight]}
            onValueChange={handlePressureWeightChange}
            min={0}
            max={1}
            step={0.05}
            className="w-full"
          />
        </div>

        {/* Sync Interval */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-white/60">Sync Interval (ticks)</span>
            <span className="text-xs font-mono text-white/40">{config.synchronization_interval}</span>
          </div>
          <Slider
            value={[config.synchronization_interval]}
            onValueChange={handleSyncIntervalChange}
            min={1}
            max={20}
            step={1}
            className="w-full"
          />
        </div>
      </div>

      {/* Simulation Duration */}
      <div className="pt-4 border-t border-white/10">
        <div className="flex items-center gap-2 mb-3">
          <Timer className="h-4 w-4 text-white/40" />
          <span className="text-xs text-white/60">Simulation Duration</span>
        </div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-white/60">Number of Ticks</span>
          <span className="text-sm font-mono text-cyan-400">{numTicks}</span>
        </div>
        <Slider
          value={[numTicks]}
          onValueChange={(v) => onNumTicksChange(v[0])}
          min={10}
          max={500}
          step={10}
          className="w-full"
        />
      </div>
    </div>
  );
}

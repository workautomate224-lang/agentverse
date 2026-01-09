'use client';

/**
 * Run Controls Panel Component
 * Reference: Interaction_design.md §5.12
 *
 * Configure horizon, scheduler profile, rule pack selection.
 */

import {
  Settings,
  Clock,
  Cpu,
  FileCode,
  ChevronDown,
  ChevronUp,
  Shuffle,
  Layers,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { SpecRunConfig } from '@/lib/api';
import { cn } from '@/lib/utils';
import { SocietyRunConfig } from './SocietyModeStudio';

interface RunControlsPanelProps {
  config: SocietyRunConfig;
  onConfigChange: (config: SocietyRunConfig) => void;
  showAdvanced: boolean;
  onToggleAdvanced: () => void;
  runConfigs: SpecRunConfig[];
}

const RULE_PACKS = [
  { id: 'default', name: 'Default Rules', description: 'Conformity, Media, Loss Aversion' },
  { id: 'social_network', name: 'Social Network', description: 'Heavy network effects' },
  { id: 'media_dominant', name: 'Media Dominant', description: 'High media influence' },
  { id: 'minimal', name: 'Minimal', description: 'Basic conformity only' },
];

const SCHEDULER_TYPES = [
  { id: 'synchronous', name: 'Synchronous', description: 'All agents process each tick together' },
  { id: 'async_random', name: 'Async Random', description: 'Agents process in random order' },
  { id: 'event_driven', name: 'Event Driven', description: 'Agents respond to events' },
  { id: 'priority', name: 'Priority', description: 'High-priority agents process first' },
];

export function RunControlsPanel({
  config,
  onConfigChange,
  showAdvanced,
  onToggleAdvanced,
  runConfigs,
}: RunControlsPanelProps) {
  const updateConfig = (updates: Partial<SocietyRunConfig>) => {
    onConfigChange({ ...config, ...updates });
  };

  return (
    <div className="flex-1 overflow-y-auto">
      {/* Header */}
      <div className="p-4 border-b border-white/10">
        <div className="flex items-center gap-2">
          <Settings className="h-4 w-4 text-cyan-400" />
          <h3 className="text-sm font-medium">Run Configuration</h3>
        </div>
      </div>

      <div className="p-4 space-y-6">
        {/* Horizon */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Clock className="h-3.5 w-3.5 text-white/40" />
              <span className="text-sm text-white/80">Horizon (Ticks)</span>
            </div>
            <span className="text-sm font-mono text-cyan-400">{config.horizon}</span>
          </div>
          <Slider
            value={[config.horizon]}
            onValueChange={([val]) => updateConfig({ horizon: val })}
            min={10}
            max={500}
            step={10}
            className="w-full"
          />
          <div className="flex justify-between mt-1 text-xs text-white/40">
            <span>10</span>
            <span>Quick</span>
            <span>Medium</span>
            <span>Long</span>
            <span>500</span>
          </div>
        </div>

        {/* Tick Rate */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Cpu className="h-3.5 w-3.5 text-white/40" />
              <span className="text-sm text-white/80">Tick Rate</span>
            </div>
            <span className="text-sm font-mono text-cyan-400">{config.tick_rate}/sec</span>
          </div>
          <Slider
            value={[config.tick_rate]}
            onValueChange={([val]) => updateConfig({ tick_rate: val })}
            min={1}
            max={100}
            step={1}
            className="w-full"
          />
        </div>

        {/* Max Agents */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Layers className="h-3.5 w-3.5 text-white/40" />
              <span className="text-sm text-white/80">Max Agents</span>
            </div>
            <span className="text-sm font-mono text-cyan-400">{config.max_agents.toLocaleString()}</span>
          </div>
          <Slider
            value={[config.max_agents]}
            onValueChange={([val]) => updateConfig({ max_agents: val })}
            min={100}
            max={10000}
            step={100}
            className="w-full"
          />
          <div className="flex justify-between mt-1">
            {[100, 500, 1000, 5000, 10000].map((preset) => (
              <button
                key={preset}
                onClick={() => updateConfig({ max_agents: preset })}
                className={cn(
                  'text-xs px-2 py-0.5 transition-colors',
                  config.max_agents === preset
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                    : 'text-white/40 hover:text-white/60'
                )}
              >
                {preset >= 1000 ? `${preset / 1000}k` : preset}
              </button>
            ))}
          </div>
        </div>

        {/* Rule Pack */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <FileCode className="h-3.5 w-3.5 text-white/40" />
            <span className="text-sm text-white/80">Rule Pack</span>
          </div>
          <div className="space-y-2">
            {RULE_PACKS.map((pack) => (
              <button
                key={pack.id}
                onClick={() => updateConfig({ rule_pack: pack.id })}
                className={cn(
                  'w-full text-left p-2 border transition-colors',
                  config.rule_pack === pack.id
                    ? 'bg-cyan-500/10 border-cyan-500/30 text-cyan-300'
                    : 'bg-white/5 border-white/10 text-white/60 hover:border-white/20'
                )}
              >
                <div className="text-sm font-medium">{pack.name}</div>
                <div className="text-xs text-white/40">{pack.description}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Advanced Toggle */}
        <Button
          variant="ghost"
          size="sm"
          onClick={onToggleAdvanced}
          className="w-full justify-between text-white/60 hover:text-white/90"
        >
          <span>Advanced Settings</span>
          {showAdvanced ? (
            <ChevronUp className="h-4 w-4" />
          ) : (
            <ChevronDown className="h-4 w-4" />
          )}
        </Button>

        {/* Advanced Settings */}
        {showAdvanced && (
          <div className="space-y-4 pt-2 border-t border-white/10">
            {/* Scheduler Type */}
            <div>
              <div className="flex items-center gap-2 mb-2">
                <Cpu className="h-3.5 w-3.5 text-white/40" />
                <span className="text-sm text-white/80">Scheduler Type</span>
              </div>
              <div className="space-y-1">
                {SCHEDULER_TYPES.map((sched) => (
                  <button
                    key={sched.id}
                    onClick={() =>
                      updateConfig({
                        scheduler_profile: {
                          ...config.scheduler_profile,
                          scheduler_type: sched.id as 'synchronous' | 'async_random' | 'event_driven' | 'priority',
                        },
                      })
                    }
                    className={cn(
                      'w-full text-left p-2 border transition-colors',
                      config.scheduler_profile.scheduler_type === sched.id
                        ? 'bg-purple-500/10 border-purple-500/30 text-purple-300'
                        : 'bg-white/5 border-white/10 text-white/60 hover:border-white/20'
                    )}
                  >
                    <div className="text-xs font-medium">{sched.name}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* Activation Probability */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-white/80">Activation Probability</span>
                <span className="text-sm font-mono text-purple-400">
                  {((config.scheduler_profile.activation_probability ?? 1) * 100).toFixed(0)}%
                </span>
              </div>
              <Slider
                value={[(config.scheduler_profile.activation_probability ?? 1) * 100]}
                onValueChange={([val]) =>
                  updateConfig({
                    scheduler_profile: {
                      ...config.scheduler_profile,
                      activation_probability: val / 100,
                    },
                  })
                }
                min={10}
                max={100}
                step={5}
                className="w-full"
              />
            </div>

            {/* Seed */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Shuffle className="h-3.5 w-3.5 text-white/40" />
                  <span className="text-sm text-white/80">Seed</span>
                </div>
                <input
                  type="number"
                  value={config.seed ?? ''}
                  onChange={(e) =>
                    updateConfig({
                      seed: e.target.value ? parseInt(e.target.value) : null,
                    })
                  }
                  placeholder="Random"
                  className="w-24 px-2 py-1 text-sm bg-white/5 border border-white/10 text-white/90 font-mono placeholder:text-white/40"
                />
              </div>
              <p className="text-xs text-white/40">
                Leave empty for random. Set for reproducibility.
              </p>
            </div>
          </div>
        )}

        {/* Template Configs */}
        {runConfigs.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs text-white/40">Load from Template</span>
            </div>
            <div className="space-y-1">
              {runConfigs.slice(0, 3).map((rc) => (
                <button
                  key={rc.config_id}
                  onClick={() =>
                    updateConfig({
                      horizon: rc.horizon,
                      tick_rate: rc.tick_rate,
                      scheduler_profile: rc.scheduler_profile,
                      max_agents: rc.max_agents ?? 1000,
                    })
                  }
                  className="w-full text-left p-2 bg-white/5 border border-white/10 hover:border-white/20 transition-colors"
                >
                  <div className="text-xs text-white/80">{rc.label ?? rc.config_id}</div>
                  <div className="text-xs text-white/40">
                    {rc.horizon} ticks • {rc.max_agents ?? 1000} agents
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

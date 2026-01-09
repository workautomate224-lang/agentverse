'use client';

/**
 * Population Panel Component
 * Reference: Interaction_design.md §5.14
 *
 * Configure population context for hybrid simulation.
 */

import { Users, Sliders } from 'lucide-react';
import { PopulationContext } from '@/lib/api';
import { Slider } from '@/components/ui/slider';

interface PopulationPanelProps {
  context: PopulationContext;
  onChange: (context: PopulationContext) => void;
}

// Preset configurations
const PRESETS = [
  { name: 'Small', agents: 50 },
  { name: 'Medium', agents: 100 },
  { name: 'Large', agents: 500 },
  { name: 'XL', agents: 1000 },
];

export function PopulationPanel({ context, onChange }: PopulationPanelProps) {
  const handleAgentCountChange = (value: number[]) => {
    onChange({
      ...context,
      agent_count: value[0],
    });
  };

  const handlePresetClick = (agents: number) => {
    onChange({
      ...context,
      agent_count: agents,
    });
  };

  return (
    <div className="p-4">
      <div className="flex items-center gap-2 mb-4">
        <Users className="h-4 w-4 text-cyan-400" />
        <h3 className="text-sm font-medium">Population Context</h3>
      </div>

      <p className="text-xs text-white/50 mb-4">
        Configure the society agents that will interact with key actors.
      </p>

      {/* Agent Count */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs text-white/60">Population Size</span>
          <span className="text-sm font-mono text-cyan-400">
            {context.agent_count.toLocaleString()}
          </span>
        </div>

        <Slider
          value={[context.agent_count]}
          onValueChange={handleAgentCountChange}
          min={10}
          max={2000}
          step={10}
          className="w-full"
        />

        {/* Presets */}
        <div className="flex items-center gap-2">
          {PRESETS.map((preset) => (
            <button
              key={preset.name}
              onClick={() => handlePresetClick(preset.agents)}
              className={`px-2 py-1 text-xs border transition-colors ${
                context.agent_count === preset.agents
                  ? 'bg-cyan-500/20 border-cyan-500/50 text-cyan-300'
                  : 'bg-white/5 border-white/10 text-white/60 hover:border-white/30'
              }`}
            >
              {preset.name}
            </button>
          ))}
        </div>
      </div>

      {/* Segment Filter (optional) */}
      <div className="mt-4 pt-4 border-t border-white/10">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-white/60">Segment Filter</span>
          <span className="text-xs text-white/30">(optional)</span>
        </div>
        <div className="text-xs text-white/40 bg-white/5 border border-white/10 p-2">
          {context.segment_filter && context.segment_filter.length > 0 ? (
            <div className="flex flex-wrap gap-1">
              {context.segment_filter.map((seg) => (
                <span key={seg} className="px-1.5 py-0.5 bg-cyan-500/20 text-cyan-300">
                  {seg}
                </span>
              ))}
            </div>
          ) : (
            <span>All segments included</span>
          )}
        </div>
      </div>

      {/* Region Filter (optional) */}
      <div className="mt-3">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-white/60">Region Filter</span>
          <span className="text-xs text-white/30">(optional)</span>
        </div>
        <div className="text-xs text-white/40 bg-white/5 border border-white/10 p-2">
          {context.region_filter && context.region_filter.length > 0 ? (
            <div className="flex flex-wrap gap-1">
              {context.region_filter.map((reg) => (
                <span key={reg} className="px-1.5 py-0.5 bg-cyan-500/20 text-cyan-300">
                  {reg}
                </span>
              ))}
            </div>
          ) : (
            <span>All regions included</span>
          )}
        </div>
      </div>
    </div>
  );
}

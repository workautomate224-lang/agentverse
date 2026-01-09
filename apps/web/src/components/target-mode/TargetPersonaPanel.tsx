'use client';

import { User, Plus, ChevronRight, Target, Shield, Heart } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { TargetPersona, UtilityDimension } from '@/lib/api';
import { cn } from '@/lib/utils';

interface TargetPersonaPanelProps {
  projectId: string;
  personas: TargetPersona[];
  selectedTargetId: string | null;
  onSelectTarget: (targetId: string | null) => void;
  onCreateTarget: () => void;
  isLoading: boolean;
}

// Map utility dimensions to icons and colors
const dimensionConfig: Record<UtilityDimension, { icon: typeof Target; color: string }> = {
  wealth: { icon: Target, color: 'text-yellow-400' },
  status: { icon: Target, color: 'text-purple-400' },
  security: { icon: Shield, color: 'text-blue-400' },
  freedom: { icon: Target, color: 'text-cyan-400' },
  relationships: { icon: Heart, color: 'text-pink-400' },
  health: { icon: Target, color: 'text-green-400' },
  achievement: { icon: Target, color: 'text-orange-400' },
  comfort: { icon: Target, color: 'text-amber-400' },
  power: { icon: Target, color: 'text-red-400' },
  knowledge: { icon: Target, color: 'text-indigo-400' },
  pleasure: { icon: Target, color: 'text-rose-400' },
  reputation: { icon: Target, color: 'text-violet-400' },
  custom: { icon: Target, color: 'text-white/60' },
};

function UtilityBar({ dimension, weight }: { dimension: UtilityDimension; weight: number }) {
  const config = dimensionConfig[dimension] ?? dimensionConfig.custom;
  const percentage = Math.round(weight * 100);

  return (
    <div className="flex items-center gap-2 text-xs">
      <span className={cn('w-20 truncate capitalize', config.color)}>{dimension}</span>
      <div className="flex-1 h-1.5 bg-white/10 rounded-full overflow-hidden">
        <div
          className={cn('h-full rounded-full', config.color.replace('text-', 'bg-'))}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className="w-8 text-right text-white/40">{percentage}%</span>
    </div>
  );
}

export function TargetPersonaPanel({
  projectId,
  personas,
  selectedTargetId,
  onSelectTarget,
  onCreateTarget,
  isLoading,
}: TargetPersonaPanelProps) {
  const selectedPersona = personas.find((p) => p.target_id === selectedTargetId);

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <User className="h-4 w-4 text-cyan-400" />
          <span className="text-sm font-medium">Target Persona</span>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={onCreateTarget}
          className="h-7 text-xs"
        >
          <Plus className="h-3 w-3 mr-1" />
          Create
        </Button>
      </div>

      {/* Persona List */}
      {isLoading ? (
        <div className="text-sm text-white/40 text-center py-4">Loading...</div>
      ) : personas.length === 0 ? (
        <div className="text-sm text-white/40 text-center py-4 border border-dashed border-white/20 rounded">
          No target personas yet.
          <br />
          Create one to start planning.
        </div>
      ) : (
        <div className="space-y-2 max-h-48 overflow-y-auto">
          {personas.map((persona) => (
            <button
              key={persona.target_id}
              onClick={() => onSelectTarget(persona.target_id)}
              className={cn(
                'w-full p-3 text-left border transition-all',
                selectedTargetId === persona.target_id
                  ? 'border-cyan-500/50 bg-cyan-500/10'
                  : 'border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/10'
              )}
            >
              <div className="flex items-center justify-between">
                <span className="font-medium text-sm">{persona.name}</span>
                <ChevronRight
                  className={cn(
                    'h-4 w-4 transition-transform',
                    selectedTargetId === persona.target_id ? 'rotate-90' : ''
                  )}
                />
              </div>
              {persona.description && (
                <p className="text-xs text-white/50 mt-1 line-clamp-1">
                  {persona.description}
                </p>
              )}
            </button>
          ))}
        </div>
      )}

      {/* Selected Persona Details */}
      {selectedPersona && (
        <div className="pt-4 border-t border-white/10 space-y-3">
          <div className="text-xs text-white/60 uppercase tracking-wider">
            Utility Profile
          </div>
          <div className="space-y-2">
            {/* Handle both utility_function.weights (full) and utility_dimensions (simplified) */}
            {selectedPersona.utility_function?.weights?.map((w) => (
              <UtilityBar
                key={w.dimension}
                dimension={w.dimension}
                weight={w.weight}
              />
            )) ?? selectedPersona.utility_dimensions?.map((dim: string) => (
              <UtilityBar
                key={dim}
                dimension={dim as UtilityDimension}
                weight={0.25}
              />
            )) ?? (
              <div className="text-xs text-white/40">No utility profile defined</div>
            )}
          </div>
          {selectedPersona.utility_function && (
            <div className="grid grid-cols-3 gap-2 text-xs mt-3">
              <div className="p-2 bg-white/5 border border-white/10">
                <div className="text-white/40">Risk Aversion</div>
                <div className="font-medium">
                  {Math.round((selectedPersona.utility_function.risk_aversion ?? 0.5) * 100)}%
                </div>
              </div>
              <div className="p-2 bg-white/5 border border-white/10">
                <div className="text-white/40">Time Pref</div>
                <div className="font-medium">
                  {Math.round((selectedPersona.utility_function.time_preference ?? 0.5) * 100)}%
                </div>
              </div>
              <div className="p-2 bg-white/5 border border-white/10">
                <div className="text-white/40">Loss Aversion</div>
                <div className="font-medium">
                  {(selectedPersona.utility_function.loss_aversion ?? 2.0).toFixed(1)}x
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

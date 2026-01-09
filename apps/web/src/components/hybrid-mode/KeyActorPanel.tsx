'use client';

/**
 * Key Actor Panel Component
 * Reference: Interaction_design.md §5.14
 *
 * Select target personas to act as key actors in hybrid simulation.
 */

import { User, Target, Check, Loader2 } from 'lucide-react';
import { TargetPersona } from '@/lib/api';
import { cn } from '@/lib/utils';

interface KeyActorPanelProps {
  personas: TargetPersona[];
  selectedIds: string[];
  onToggleActor: (targetId: string) => void;
  isLoading: boolean;
}

export function KeyActorPanel({
  personas,
  selectedIds,
  onToggleActor,
  isLoading,
}: KeyActorPanelProps) {
  if (isLoading) {
    return (
      <div className="p-4 flex items-center justify-center h-40">
        <Loader2 className="h-5 w-5 text-white/40 animate-spin" />
      </div>
    );
  }

  if (personas.length === 0) {
    return (
      <div className="p-4">
        <div className="flex items-center gap-2 mb-4">
          <Target className="h-4 w-4 text-purple-400" />
          <h3 className="text-sm font-medium">Key Actors</h3>
        </div>
        <div className="text-center py-8 text-white/40 text-sm">
          <User className="h-8 w-8 mx-auto mb-2 opacity-40" />
          <p>No target personas found.</p>
          <p className="mt-1 text-xs">Create targets in Target Mode first.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Target className="h-4 w-4 text-purple-400" />
          <h3 className="text-sm font-medium">Key Actors</h3>
        </div>
        <span className="text-xs text-white/40">
          {selectedIds.length} of {personas.length} selected
        </span>
      </div>

      <p className="text-xs text-white/50 mb-3">
        Select target personas to act as key actors in the hybrid simulation.
      </p>

      <div className="space-y-2">
        {personas.map((persona) => {
          const isSelected = selectedIds.includes(persona.target_id);
          const topDimensions = persona.utility_function?.weights
            ?.sort((a, b) => b.weight - a.weight)
            .slice(0, 2)
            .map(w => w.dimension) ?? persona.utility_dimensions?.slice(0, 2) ?? [];

          return (
            <button
              key={persona.target_id}
              onClick={() => onToggleActor(persona.target_id)}
              className={cn(
                'w-full text-left p-3 border transition-all',
                isSelected
                  ? 'bg-purple-500/10 border-purple-500/50'
                  : 'bg-white/5 border-white/10 hover:border-white/30'
              )}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <User className={cn('h-4 w-4', isSelected ? 'text-purple-400' : 'text-white/40')} />
                    <span className={cn('text-sm font-medium truncate', isSelected && 'text-purple-300')}>
                      {persona.name}
                    </span>
                  </div>
                  {persona.description && (
                    <p className="text-xs text-white/40 mt-1 line-clamp-1">
                      {persona.description}
                    </p>
                  )}
                  <div className="flex items-center gap-1 mt-2">
                    {topDimensions.map((dim) => (
                      <span
                        key={dim}
                        className="text-xs px-1.5 py-0.5 bg-white/10 text-white/60"
                      >
                        {dim}
                      </span>
                    ))}
                    <span className="text-xs text-white/30 ml-1">
                      H:{persona.planning_horizon}
                    </span>
                  </div>
                </div>
                <div
                  className={cn(
                    'w-5 h-5 border flex items-center justify-center flex-shrink-0 ml-2',
                    isSelected
                      ? 'bg-purple-500 border-purple-500'
                      : 'border-white/30'
                  )}
                >
                  {isSelected && <Check className="h-3 w-3 text-white" />}
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

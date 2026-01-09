'use client';

import { useState } from 'react';
import { Zap, Plus, Sparkles, ChevronDown, ChevronRight, Tag } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { TargetPersona, ActionDefinition, ActionCategory } from '@/lib/api';
import { cn } from '@/lib/utils';

interface ActionSetPanelProps {
  target: TargetPersona | null;
}

// Category colors
const categoryColors: Record<ActionCategory, string> = {
  financial: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30',
  social: 'text-pink-400 bg-pink-500/10 border-pink-500/30',
  professional: 'text-blue-400 bg-blue-500/10 border-blue-500/30',
  personal: 'text-green-400 bg-green-500/10 border-green-500/30',
  consumption: 'text-purple-400 bg-purple-500/10 border-purple-500/30',
  communication: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30',
  movement: 'text-orange-400 bg-orange-500/10 border-orange-500/30',
  legal: 'text-red-400 bg-red-500/10 border-red-500/30',
  health: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
  custom: 'text-white/60 bg-white/5 border-white/20',
};

interface ActionCardProps {
  action: ActionDefinition;
  isExpanded: boolean;
  onToggle: () => void;
}

function ActionCard({ action, isExpanded, onToggle }: ActionCardProps) {
  const colorClass = categoryColors[action.category] ?? categoryColors.custom;

  return (
    <div className="border border-white/10 bg-white/5">
      <button
        onClick={onToggle}
        className="w-full p-2 flex items-center gap-2 text-left hover:bg-white/5"
      >
        {isExpanded ? (
          <ChevronDown className="h-3 w-3 text-white/40" />
        ) : (
          <ChevronRight className="h-3 w-3 text-white/40" />
        )}
        <span className="flex-1 text-sm font-medium truncate">{action.name}</span>
        <span
          className={cn('px-1.5 py-0.5 text-xs capitalize border', colorClass)}
        >
          {action.category}
        </span>
      </button>
      {isExpanded && (
        <div className="px-2 pb-2 space-y-2">
          {action.description && (
            <p className="text-xs text-white/60">{action.description}</p>
          )}
          <div className="grid grid-cols-3 gap-1 text-xs">
            <div className="p-1 bg-black/20">
              <div className="text-white/40">Cost</div>
              <div className="font-medium">${action.monetary_cost}</div>
            </div>
            <div className="p-1 bg-black/20">
              <div className="text-white/40">Time</div>
              <div className="font-medium">{action.time_cost}h</div>
            </div>
            <div className="p-1 bg-black/20">
              <div className="text-white/40">Risk</div>
              <div
                className={cn(
                  'font-medium',
                  action.risk_level > 0.5 ? 'text-red-400' : 'text-green-400'
                )}
              >
                {Math.round(action.risk_level * 100)}%
              </div>
            </div>
          </div>
          {action.preconditions.length > 0 && (
            <div className="text-xs">
              <span className="text-white/40">Preconditions: </span>
              <span className="text-white/60">
                {action.preconditions.map((p) => p.variable).join(', ')}
              </span>
            </div>
          )}
          {action.tags && action.tags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {action.tags.map((tag) => (
                <span
                  key={tag}
                  className="px-1 py-0.5 text-xs bg-white/5 border border-white/10 text-white/50"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function ActionSetPanel({ target }: ActionSetPanelProps) {
  const [expandedActions, setExpandedActions] = useState<Set<string>>(new Set());
  const [categoryFilter, setCategoryFilter] = useState<ActionCategory | 'all'>('all');

  // Get all available actions
  const actions = target?.custom_actions ?? [];

  // Filter by category
  const filteredActions = categoryFilter === 'all'
    ? actions
    : actions.filter((a) => a.category === categoryFilter);

  // Get unique categories
  const categories = [...new Set(actions.map((a) => a.category))];

  const toggleAction = (actionId: string) => {
    setExpandedActions((prev) => {
      const next = new Set(prev);
      if (next.has(actionId)) {
        next.delete(actionId);
      } else {
        next.add(actionId);
      }
      return next;
    });
  };

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Zap className="h-4 w-4 text-cyan-400" />
          <span className="text-sm font-medium">Action Set</span>
          <span className="text-xs text-white/40">({actions.length})</span>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            size="sm"
            className="h-7 text-xs"
            disabled={!target}
          >
            <Plus className="h-3 w-3 mr-1" />
            Add
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="h-7 text-xs"
            disabled={!target}
          >
            <Sparkles className="h-3 w-3 mr-1" />
            Ask AI
          </Button>
        </div>
      </div>

      {!target ? (
        <div className="text-sm text-white/40 text-center py-8 border border-dashed border-white/20 rounded">
          Select a target persona to view actions
        </div>
      ) : actions.length === 0 ? (
        <div className="text-sm text-white/40 text-center py-8 border border-dashed border-white/20 rounded">
          No actions defined.
          <br />
          Add actions or use AI to generate them.
        </div>
      ) : (
        <>
          {/* Category Filter */}
          {categories.length > 1 && (
            <div className="flex flex-wrap gap-1">
              <button
                onClick={() => setCategoryFilter('all')}
                className={cn(
                  'px-2 py-1 text-xs border transition-colors',
                  categoryFilter === 'all'
                    ? 'border-cyan-500/50 bg-cyan-500/10 text-cyan-300'
                    : 'border-white/10 bg-white/5 text-white/60 hover:border-white/20'
                )}
              >
                All
              </button>
              {categories.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setCategoryFilter(cat)}
                  className={cn(
                    'px-2 py-1 text-xs border transition-colors capitalize',
                    categoryFilter === cat
                      ? 'border-cyan-500/50 bg-cyan-500/10 text-cyan-300'
                      : 'border-white/10 bg-white/5 text-white/60 hover:border-white/20'
                  )}
                >
                  {cat}
                </button>
              ))}
            </div>
          )}

          {/* Action List */}
          <div className="space-y-1 max-h-64 overflow-y-auto">
            {filteredActions.map((action) => (
              <ActionCard
                key={action.action_id}
                action={action}
                isExpanded={expandedActions.has(action.action_id)}
                onToggle={() => toggleAction(action.action_id)}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

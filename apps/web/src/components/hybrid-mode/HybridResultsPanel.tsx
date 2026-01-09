'use client';

/**
 * Hybrid Results Panel Component
 * Reference: Interaction_design.md §5.14
 *
 * Display joint outcomes and key decisions from hybrid simulation.
 */

import {
  BarChart3,
  User,
  Users,
  ArrowRight,
  GitBranch,
  PlayCircle,
  Loader2,
  TrendingUp,
  TrendingDown,
  Minus,
  Zap,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { HybridRunResult, TargetPersona, HybridActorOutcome, HybridCouplingEffect } from '@/lib/api';
import { cn } from '@/lib/utils';

interface HybridResultsPanelProps {
  runResult: HybridRunResult | null;
  isLoading: boolean;
  selectedActors: TargetPersona[];
  onBranchToNode: () => void;
  isBranching: boolean;
}

function TrendIcon({ value }: { value: number }) {
  if (value > 0.01) return <TrendingUp className="h-3 w-3 text-green-400" />;
  if (value < -0.01) return <TrendingDown className="h-3 w-3 text-red-400" />;
  return <Minus className="h-3 w-3 text-white/40" />;
}

function ActorOutcomeCard({ outcome }: { outcome: HybridActorOutcome }) {
  return (
    <div className="border border-white/10 bg-white/5 p-3">
      <div className="flex items-center gap-2 mb-2">
        <User className="h-4 w-4 text-purple-400" />
        <span className="text-sm font-medium text-purple-300">{outcome.target_name}</span>
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs">
        <div>
          <span className="text-white/40">Utility</span>
          <span className="block text-sm font-mono text-white/90">{outcome.total_utility.toFixed(2)}</span>
        </div>
        <div>
          <span className="text-white/40">Path Prob</span>
          <span className="block text-sm font-mono text-white/90">{(outcome.path_probability * 100).toFixed(1)}%</span>
        </div>
        <div>
          <span className="text-white/40">Influence Out</span>
          <span className="block text-sm font-mono text-cyan-400">{outcome.influence_exerted.toFixed(2)}</span>
        </div>
        <div>
          <span className="text-white/40">Pressure In</span>
          <span className="block text-sm font-mono text-yellow-400">{outcome.society_pressure_received.toFixed(2)}</span>
        </div>
      </div>

      {outcome.actions_taken.length > 0 && (
        <div className="mt-2 pt-2 border-t border-white/10">
          <span className="text-xs text-white/40 block mb-1">Key Actions</span>
          <div className="flex flex-wrap gap-1">
            {outcome.actions_taken.slice(0, 4).map((action, i) => (
              <span key={i} className="text-xs px-1.5 py-0.5 bg-purple-500/20 text-purple-300">
                {action}
              </span>
            ))}
            {outcome.actions_taken.length > 4 && (
              <span className="text-xs text-white/40">+{outcome.actions_taken.length - 4} more</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function CouplingEffectRow({ effect }: { effect: HybridCouplingEffect }) {
  return (
    <div className="flex items-center gap-2 py-1.5 text-xs">
      <span className="font-mono text-white/40 w-10">t{effect.tick}</span>
      <Zap className={cn(
        'h-3 w-3',
        effect.source_type === 'actor' ? 'text-purple-400' : 'text-cyan-400'
      )} />
      <span className={cn(
        'px-1.5 py-0.5',
        effect.source_type === 'actor' ? 'bg-purple-500/20 text-purple-300' : 'bg-cyan-500/20 text-cyan-300'
      )}>
        {effect.source_type}
      </span>
      <ArrowRight className="h-3 w-3 text-white/30" />
      <span className="text-white/60 flex-1">{effect.effect_type}</span>
      <span className="text-white/40">{effect.affected_count} affected</span>
    </div>
  );
}

export function HybridResultsPanel({
  runResult,
  isLoading,
  selectedActors,
  onBranchToNode,
  isBranching,
}: HybridResultsPanelProps) {
  // Empty state
  if (!runResult && !isLoading) {
    return (
      <div className="h-full flex items-center justify-center p-8">
        <div className="text-center max-w-xs">
          <BarChart3 className="h-10 w-10 mx-auto mb-3 text-white/20" />
          <h3 className="text-sm font-medium text-white/60 mb-2">No Results Yet</h3>
          <p className="text-xs text-white/40">
            Select key actors and configure population, then run a hybrid simulation to see joint outcomes.
          </p>
        </div>
      </div>
    );
  }

  // Loading state
  if (isLoading && !runResult) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-6 w-6 mx-auto mb-3 text-purple-400 animate-spin" />
          <p className="text-sm text-white/60">Loading results...</p>
        </div>
      </div>
    );
  }

  if (!runResult) return null;

  const { actor_outcomes, society_outcome, coupling_effects } = runResult;

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex-none p-4 border-b border-white/10">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-green-400" />
            <h3 className="text-sm font-medium">Hybrid Results</h3>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={onBranchToNode}
              disabled={isBranching || runResult.status !== 'completed'}
              className="h-7 text-xs"
            >
              {isBranching ? (
                <Loader2 className="h-3 w-3 mr-1 animate-spin" />
              ) : (
                <GitBranch className="h-3 w-3 mr-1" />
              )}
              Branch to Map
            </Button>
            {runResult.telemetry_ref && (
              <Button variant="outline" size="sm" className="h-7 text-xs" disabled>
                <PlayCircle className="h-3 w-3 mr-1" />
                Replay
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {/* Summary Stats */}
        <div className="grid grid-cols-3 gap-3">
          <div className="border border-white/10 bg-white/5 p-3 text-center">
            <span className="text-xs text-white/40 block mb-1">Total Ticks</span>
            <span className="text-lg font-mono text-white/90">{runResult.total_ticks}</span>
          </div>
          <div className="border border-white/10 bg-white/5 p-3 text-center">
            <span className="text-xs text-white/40 block mb-1">Seed</span>
            <span className="text-lg font-mono text-white/90">{runResult.seed_used}</span>
          </div>
          <div className="border border-white/10 bg-white/5 p-3 text-center">
            <span className="text-xs text-white/40 block mb-1">Duration</span>
            <span className="text-lg font-mono text-white/90">{(runResult.execution_time_ms / 1000).toFixed(1)}s</span>
          </div>
        </div>

        {/* Actor Outcomes */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <User className="h-4 w-4 text-purple-400" />
            <h4 className="text-sm font-medium">Key Actor Outcomes</h4>
            <span className="text-xs text-white/40">({actor_outcomes.length})</span>
          </div>
          <div className="space-y-2">
            {actor_outcomes.map((outcome) => (
              <ActorOutcomeCard key={outcome.target_id} outcome={outcome} />
            ))}
          </div>
        </div>

        {/* Society Outcome */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Users className="h-4 w-4 text-cyan-400" />
            <h4 className="text-sm font-medium">Society Outcome</h4>
          </div>
          <div className="border border-white/10 bg-white/5 p-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <span className="text-xs text-white/40 block mb-1">Final Avg Stance</span>
                <div className="flex items-center gap-2">
                  <span className="text-xl font-mono text-white/90">
                    {society_outcome.final_avg_stance.toFixed(2)}
                  </span>
                  <TrendIcon value={society_outcome.stance_shift} />
                  <span className={cn(
                    'text-xs font-mono',
                    society_outcome.stance_shift > 0 ? 'text-green-400' :
                    society_outcome.stance_shift < 0 ? 'text-red-400' : 'text-white/40'
                  )}>
                    {society_outcome.stance_shift >= 0 ? '+' : ''}{society_outcome.stance_shift.toFixed(2)}
                  </span>
                </div>
              </div>
              <div>
                <span className="text-xs text-white/40 block mb-1">Influenced Agents</span>
                <span className="text-xl font-mono text-cyan-400">
                  {society_outcome.influenced_agent_count.toLocaleString()}
                </span>
              </div>
              <div>
                <span className="text-xs text-white/40 block mb-1">Total Influence Received</span>
                <span className="text-sm font-mono text-white/90">
                  {society_outcome.total_influence_received.toFixed(2)}
                </span>
              </div>
            </div>

            {/* Segment Distribution */}
            <div className="mt-4 pt-4 border-t border-white/10">
              <span className="text-xs text-white/40 block mb-2">Final Segment Distribution</span>
              <div className="flex flex-wrap gap-2">
                {Object.entries(society_outcome.final_segment_distribution).map(([seg, pct]) => (
                  <div key={seg} className="text-xs">
                    <span className="px-1.5 py-0.5 bg-cyan-500/20 text-cyan-300 mr-1">{seg}</span>
                    <span className="text-white/60">{(pct * 100).toFixed(1)}%</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Key Events */}
            {society_outcome.key_events.length > 0 && (
              <div className="mt-4 pt-4 border-t border-white/10">
                <span className="text-xs text-white/40 block mb-2">Key Events</span>
                <div className="space-y-1">
                  {society_outcome.key_events.slice(0, 5).map((event, i) => (
                    <div key={i} className="text-xs text-white/60 flex items-center gap-1">
                      <span className="text-white/30">•</span>
                      {event}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Coupling Effects */}
        {coupling_effects.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Zap className="h-4 w-4 text-yellow-400" />
              <h4 className="text-sm font-medium">Coupling Effects</h4>
              <span className="text-xs text-white/40">({coupling_effects.length})</span>
            </div>
            <div className="border border-white/10 bg-white/5 p-3 max-h-48 overflow-y-auto">
              {coupling_effects.slice(0, 20).map((effect, i) => (
                <CouplingEffectRow key={i} effect={effect} />
              ))}
              {coupling_effects.length > 20 && (
                <p className="text-xs text-white/40 mt-2">
                  + {coupling_effects.length - 20} more effects...
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

'use client';

/**
 * 2D Replay Inspector Component
 * Reference: project.md §11 Phase 8, Interaction_design.md §5.17
 *
 * Right panel showing details when clicking an agent or zone:
 * - Current state
 * - Recent events affecting it
 * - Metric references
 */

import React from 'react';
import {
  X,
  User,
  TrendingUp,
  TrendingDown,
  Minus,
  Heart,
  Users,
  Radio,
  Clock,
  Zap,
  Brain,
  History,
  MapPin,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { AgentState } from './ReplayCanvas';

interface AgentEvent {
  tick: number;
  event_type: string;
  event_name: string;
  intensity: number;
  variables_affected: string[];
}

interface AgentHistoryPoint {
  tick: number;
  stance: number;
  emotion: number;
  influence: number;
}

interface ReplayInspectorProps {
  selectedAgent: AgentState | null;
  agentHistory: AgentHistoryPoint[];
  agentEvents: AgentEvent[];
  onClose: () => void;
  onViewHistory?: (agentId: string) => void;
  currentTick: number;
  className?: string;
}

// Helper to get trend icon
function TrendIcon({ current, previous }: { current: number; previous?: number }) {
  if (previous === undefined) return <Minus className="h-3 w-3 text-white/40" />;
  const diff = current - previous;
  if (Math.abs(diff) < 0.01) return <Minus className="h-3 w-3 text-white/40" />;
  if (diff > 0) return <TrendingUp className="h-3 w-3 text-green-400" />;
  return <TrendingDown className="h-3 w-3 text-red-400" />;
}

// Helper to format value as percentage
function formatPercent(value: number): string {
  const percent = value * 100;
  return `${percent > 0 ? '+' : ''}${percent.toFixed(1)}%`;
}

// Helper to get stance color
function getStanceColor(stance: number): string {
  if (stance < -0.3) return 'text-red-400';
  if (stance > 0.3) return 'text-green-400';
  return 'text-gray-400';
}

export function ReplayInspector({
  selectedAgent,
  agentHistory,
  agentEvents,
  onClose,
  onViewHistory,
  currentTick,
  className,
}: ReplayInspectorProps) {
  // Get previous state for trend comparison
  const previousState = agentHistory.length > 1 ? agentHistory[agentHistory.length - 2] : undefined;

  if (!selectedAgent) {
    return (
      <div className={cn(
        'w-72 bg-black/80 border-l border-white/10 flex items-center justify-center',
        className
      )}>
        <div className="text-center text-white/40 p-4">
          <User className="h-8 w-8 mx-auto mb-2 opacity-40" />
          <p className="text-sm">Click an agent to inspect</p>
        </div>
      </div>
    );
  }

  // Filter events to recent ones (within 10 ticks)
  const recentEvents = agentEvents.filter(e => Math.abs(currentTick - e.tick) <= 10);

  return (
    <div className={cn(
      'w-72 bg-black/80 border-l border-white/10 flex flex-col',
      className
    )}>
      {/* Header */}
      <div className="p-3 border-b border-white/10 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <User className="h-4 w-4 text-cyan-400" />
          <span className="font-mono text-sm text-white/90">
            Agent {selectedAgent.agent_id.slice(0, 8)}
          </span>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={onClose}
          className="h-6 w-6 p-0 text-white/40 hover:text-white"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* Agent info */}
      <div className="p-3 border-b border-white/10 space-y-2 text-xs">
        <div className="flex items-center gap-2">
          <MapPin className="h-3 w-3 text-white/40" />
          <span className="text-white/60">Segment:</span>
          <span className="text-cyan-400">{selectedAgent.segment}</span>
        </div>
        {selectedAgent.region && (
          <div className="flex items-center gap-2">
            <MapPin className="h-3 w-3 text-white/40" />
            <span className="text-white/60">Region:</span>
            <span className="text-cyan-400">{selectedAgent.region}</span>
          </div>
        )}
        <div className="flex items-center gap-2">
          <Clock className="h-3 w-3 text-white/40" />
          <span className="text-white/60">At tick:</span>
          <span className="text-white/80">{selectedAgent.tick}</span>
        </div>
      </div>

      {/* Current state */}
      <div className="p-3 border-b border-white/10">
        <h4 className="text-xs font-medium text-white/60 mb-3">CURRENT STATE</h4>

        {/* Stance */}
        <div className="flex items-center justify-between py-1">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-3 w-3 text-green-400" />
            <span className="text-sm text-white/80">Stance</span>
          </div>
          <div className="flex items-center gap-2">
            <span className={cn('text-sm font-mono', getStanceColor(selectedAgent.stance))}>
              {formatPercent(selectedAgent.stance)}
            </span>
            <TrendIcon current={selectedAgent.stance} previous={previousState?.stance} />
          </div>
        </div>

        {/* Emotion */}
        <div className="flex items-center justify-between py-1">
          <div className="flex items-center gap-2">
            <Heart className="h-3 w-3 text-yellow-400" />
            <span className="text-sm text-white/80">Emotion</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-mono text-yellow-400">
              {(selectedAgent.emotion * 100).toFixed(0)}%
            </span>
            <TrendIcon current={selectedAgent.emotion} previous={previousState?.emotion} />
          </div>
        </div>

        {/* Influence */}
        <div className="flex items-center justify-between py-1">
          <div className="flex items-center gap-2">
            <Users className="h-3 w-3 text-blue-400" />
            <span className="text-sm text-white/80">Influence</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-mono text-blue-400">
              {(selectedAgent.influence * 100).toFixed(0)}%
            </span>
            <TrendIcon current={selectedAgent.influence} previous={previousState?.influence} />
          </div>
        </div>

        {/* Exposure */}
        <div className="flex items-center justify-between py-1">
          <div className="flex items-center gap-2">
            <Radio className="h-3 w-3 text-orange-400" />
            <span className="text-sm text-white/80">Exposure</span>
          </div>
          <span className="text-sm font-mono text-orange-400">
            {(selectedAgent.exposure * 100).toFixed(0)}%
          </span>
        </div>
      </div>

      {/* Beliefs (if any) */}
      {selectedAgent.beliefs && Object.keys(selectedAgent.beliefs).length > 0 && (
        <div className="p-3 border-b border-white/10">
          <h4 className="text-xs font-medium text-white/60 mb-2">
            <Brain className="h-3 w-3 inline mr-1" />
            BELIEFS
          </h4>
          <div className="space-y-1">
            {Object.entries(selectedAgent.beliefs).slice(0, 5).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between text-xs">
                <span className="text-white/60 truncate max-w-[120px]">{key}</span>
                <span className={cn(
                  'font-mono',
                  value > 0.5 ? 'text-green-400' : value < -0.5 ? 'text-red-400' : 'text-white/60'
                )}>
                  {(value * 100).toFixed(0)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent events */}
      <div className="flex-1 overflow-auto p-3">
        <h4 className="text-xs font-medium text-white/60 mb-2">
          <Zap className="h-3 w-3 inline mr-1" />
          RECENT EVENTS
        </h4>
        {recentEvents.length === 0 ? (
          <div className="text-xs text-white/40">No recent events</div>
        ) : (
          <div className="space-y-2">
            {recentEvents.map((event, idx) => (
              <div
                key={idx}
                className="bg-white/5 border border-white/10 rounded p-2 text-xs"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-purple-400">{event.event_name}</span>
                  <span className="text-white/40">T{event.tick}</span>
                </div>
                <div className="text-white/60">
                  {event.event_type} • Intensity: {(event.intensity * 100).toFixed(0)}%
                </div>
                {event.variables_affected.length > 0 && (
                  <div className="mt-1 flex flex-wrap gap-1">
                    {event.variables_affected.slice(0, 3).map((v, i) => (
                      <span key={i} className="bg-purple-900/50 px-1 rounded text-purple-300">
                        {v}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Last action */}
      {selectedAgent.last_action && (
        <div className="p-3 border-t border-white/10">
          <div className="text-xs">
            <span className="text-white/40">Last action:</span>
            <span className="text-cyan-400 ml-1">{selectedAgent.last_action}</span>
          </div>
        </div>
      )}

      {/* View history button */}
      {onViewHistory && (
        <div className="p-3 border-t border-white/10">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onViewHistory(selectedAgent.agent_id)}
            className="w-full text-xs"
          >
            <History className="h-3 w-3 mr-1" />
            View Full History
          </Button>
        </div>
      )}
    </div>
  );
}

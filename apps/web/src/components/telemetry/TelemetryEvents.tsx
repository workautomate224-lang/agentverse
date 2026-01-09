'use client';

/**
 * TelemetryEvents Component
 * Displays event timeline/log for simulation telemetry.
 * Reference: project.md §6.8 (Telemetry), C3 (read-only replay)
 *
 * IMPORTANT: This is READ-ONLY. It must NEVER trigger new simulations.
 */

import { memo, useMemo, useState, useCallback, useRef, useEffect } from 'react';
import {
  MessageSquare,
  AlertTriangle,
  AlertCircle,
  Info,
  CheckCircle,
  Filter,
  ChevronDown,
  ChevronRight,
  Search,
  Clock,
  User,
  Zap,
  Target,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

type EventType = 'info' | 'warning' | 'error' | 'success' | 'action' | 'decision' | 'state_change';

interface TelemetryEvent {
  id: string;
  tick: number;
  type: EventType;
  source: string; // agent_id or 'system'
  message: string;
  details?: Record<string, unknown>;
  timestamp?: string;
}

interface TelemetryEventsProps {
  events: TelemetryEvent[];
  currentTick: number;
  onEventClick?: (event: TelemetryEvent) => void;
  onJumpToTick?: (tick: number) => void;
  className?: string;
}

// Event type configuration
const EVENT_CONFIG: Record<EventType, { icon: typeof Info; color: string; label: string }> = {
  info: { icon: Info, color: 'text-blue-400', label: 'Info' },
  warning: { icon: AlertTriangle, color: 'text-yellow-400', label: 'Warning' },
  error: { icon: AlertCircle, color: 'text-red-400', label: 'Error' },
  success: { icon: CheckCircle, color: 'text-green-400', label: 'Success' },
  action: { icon: Zap, color: 'text-cyan-400', label: 'Action' },
  decision: { icon: Target, color: 'text-purple-400', label: 'Decision' },
  state_change: { icon: MessageSquare, color: 'text-orange-400', label: 'State' },
};

// Individual event item
const EventItem = memo(function EventItem({
  event,
  isCurrentTick,
  isPast,
  onEventClick,
  onJumpToTick,
}: {
  event: TelemetryEvent;
  isCurrentTick: boolean;
  isPast: boolean;
  onEventClick?: (event: TelemetryEvent) => void;
  onJumpToTick?: (tick: number) => void;
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  const config = EVENT_CONFIG[event.type] || EVENT_CONFIG.info;
  const Icon = config.icon;

  return (
    <div
      className={cn(
        'group border-l-2 pl-3 py-2 transition-colors',
        isCurrentTick
          ? 'border-cyan-400 bg-cyan-500/10'
          : isPast
          ? 'border-white/10 opacity-60'
          : 'border-white/20',
        'hover:bg-white/5'
      )}
    >
      <div className="flex items-start gap-2">
        {/* Event icon */}
        <Icon className={cn('w-3.5 h-3.5 mt-0.5 flex-shrink-0', config.color)} />

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            {/* Tick badge */}
            <button
              onClick={() => onJumpToTick?.(event.tick)}
              className="px-1.5 py-0.5 text-[10px] font-mono bg-white/5 hover:bg-white/10 text-white/60 transition-colors"
              title="Jump to this tick"
            >
              T{event.tick}
            </button>

            {/* Source */}
            <div className="flex items-center gap-1 text-[10px] font-mono text-white/40">
              {event.source === 'system' ? (
                <span className="text-white/30">SYSTEM</span>
              ) : (
                <>
                  <User className="w-2.5 h-2.5" />
                  <span>{event.source.slice(0, 8)}</span>
                </>
              )}
            </div>

            {/* Type label */}
            <span className={cn('text-[10px] font-mono uppercase', config.color)}>
              {config.label}
            </span>
          </div>

          {/* Message */}
          <p
            className="text-xs font-mono text-white/80 cursor-pointer"
            onClick={() => onEventClick?.(event)}
          >
            {event.message}
          </p>

          {/* Details (expandable) */}
          {event.details && Object.keys(event.details).length > 0 && (
            <div className="mt-1">
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="flex items-center gap-1 text-[10px] font-mono text-white/40 hover:text-white/60"
              >
                {isExpanded ? (
                  <ChevronDown className="w-3 h-3" />
                ) : (
                  <ChevronRight className="w-3 h-3" />
                )}
                Details
              </button>

              {isExpanded && (
                <pre className="mt-1 p-2 bg-black/50 border border-white/10 text-[10px] font-mono text-white/60 overflow-x-auto">
                  {JSON.stringify(event.details, null, 2)}
                </pre>
              )}
            </div>
          )}
        </div>

        {/* Timestamp */}
        {event.timestamp && (
          <div className="flex items-center gap-1 text-[10px] font-mono text-white/30">
            <Clock className="w-2.5 h-2.5" />
            {new Date(event.timestamp).toLocaleTimeString()}
          </div>
        )}
      </div>
    </div>
  );
});

export const TelemetryEvents = memo(function TelemetryEvents({
  events,
  currentTick,
  onEventClick,
  onJumpToTick,
  className,
}: TelemetryEventsProps) {
  const listRef = useRef<HTMLDivElement>(null);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState<EventType | 'all'>('all');
  const [showFilters, setShowFilters] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);

  // Filter events
  const filteredEvents = useMemo(() => {
    return events.filter((event) => {
      if (typeFilter !== 'all' && event.type !== typeFilter) return false;
      if (search) {
        const searchLower = search.toLowerCase();
        return (
          event.message.toLowerCase().includes(searchLower) ||
          event.source.toLowerCase().includes(searchLower)
        );
      }
      return true;
    });
  }, [events, typeFilter, search]);

  // Sort by tick (most recent first or by tick order)
  const sortedEvents = useMemo(() => {
    return [...filteredEvents].sort((a, b) => a.tick - b.tick);
  }, [filteredEvents]);

  // Auto-scroll to current tick events
  useEffect(() => {
    if (autoScroll && listRef.current) {
      const currentTickEvent = sortedEvents.findIndex((e) => e.tick >= currentTick);
      if (currentTickEvent !== -1) {
        const items = listRef.current.querySelectorAll('[data-event-item]');
        items[currentTickEvent]?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  }, [currentTick, autoScroll, sortedEvents]);

  // Count events by type
  const eventCounts = useMemo(() => {
    const counts: Record<string, number> = { all: events.length };
    events.forEach((e) => {
      counts[e.type] = (counts[e.type] || 0) + 1;
    });
    return counts;
  }, [events]);

  return (
    <div className={cn('flex flex-col', className)}>
      {/* Header */}
      <div className="flex items-center justify-between p-3 bg-black border border-white/10 border-b-0">
        <div className="flex items-center gap-2">
          <MessageSquare className="w-4 h-4 text-white/40" />
          <span className="text-xs font-mono text-white/40 uppercase tracking-wider">
            Events
          </span>
          <span className="text-[10px] font-mono text-white/30">
            ({filteredEvents.length} / {events.length})
          </span>
        </div>

        <div className="flex items-center gap-1">
          <Button
            variant={autoScroll ? 'secondary' : 'ghost'}
            size="icon-sm"
            onClick={() => setAutoScroll(!autoScroll)}
            title={autoScroll ? 'Auto-scroll enabled' : 'Auto-scroll disabled'}
          >
            <Target className="w-3 h-3" />
          </Button>
          <Button
            variant={showFilters ? 'secondary' : 'ghost'}
            size="icon-sm"
            onClick={() => setShowFilters(!showFilters)}
            title="Toggle filters"
          >
            <Filter className="w-3 h-3" />
          </Button>
        </div>
      </div>

      {/* Filters */}
      {showFilters && (
        <div className="p-3 bg-black/50 border border-white/10 border-b-0 space-y-3">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-white/40" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search events..."
              className="w-full pl-8 pr-3 py-1.5 text-xs font-mono bg-black border border-white/20 text-white placeholder:text-white/30 focus:border-white/40 focus:outline-none"
            />
          </div>

          {/* Type filter */}
          <div className="flex flex-wrap gap-1">
            <button
              onClick={() => setTypeFilter('all')}
              className={cn(
                'px-2 py-1 text-[10px] font-mono transition-colors',
                typeFilter === 'all'
                  ? 'bg-white text-black'
                  : 'bg-white/5 text-white/60 hover:text-white'
              )}
            >
              All ({eventCounts.all || 0})
            </button>
            {(Object.keys(EVENT_CONFIG) as EventType[]).map((type) => {
              const config = EVENT_CONFIG[type];
              return (
                <button
                  key={type}
                  onClick={() => setTypeFilter(type)}
                  className={cn(
                    'px-2 py-1 text-[10px] font-mono transition-colors',
                    typeFilter === type
                      ? 'bg-white text-black'
                      : 'bg-white/5 text-white/60 hover:text-white'
                  )}
                >
                  {config.label} ({eventCounts[type] || 0})
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Event List */}
      <div
        ref={listRef}
        className="flex-1 overflow-y-auto bg-black border border-white/10"
        style={{ maxHeight: 400 }}
      >
        {sortedEvents.length > 0 ? (
          <div className="divide-y divide-white/5">
            {sortedEvents.map((event) => (
              <div key={event.id} data-event-item>
                <EventItem
                  event={event}
                  isCurrentTick={event.tick === currentTick}
                  isPast={event.tick < currentTick}
                  onEventClick={onEventClick}
                  onJumpToTick={onJumpToTick}
                />
              </div>
            ))}
          </div>
        ) : (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <MessageSquare className="w-6 h-6 text-white/20 mx-auto mb-2" />
              <p className="text-xs font-mono text-white/40">
                {events.length === 0 ? 'No events recorded' : 'No matching events'}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Read-Only Notice */}
      <div className="px-3 py-2 bg-blue-500/10 border border-blue-500/20 border-t-0">
        <span className="text-[10px] font-mono text-blue-400">
          READ-ONLY - Events are historical records
        </span>
      </div>
    </div>
  );
});

export default TelemetryEvents;

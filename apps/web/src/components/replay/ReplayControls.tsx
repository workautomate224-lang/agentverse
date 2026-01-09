'use client';

/**
 * 2D Replay Controls Component
 * Reference: project.md §11 Phase 8, Interaction_design.md §5.17
 *
 * Top controls bar with play/pause, speed, seek bar, and tick indicator.
 */

import React, { useCallback, useMemo } from 'react';
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  FastForward,
  Rewind,
  Maximize2,
  Minimize2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { cn } from '@/lib/utils';

export interface TimelineMarker {
  tick: number;
  type: string;
  label: string;
  event_types: string[];
}

interface ReplayControlsProps {
  currentTick: number;
  totalTicks: number;
  isPlaying: boolean;
  playbackSpeed: number;
  keyframeTicks: number[];
  eventMarkers: TimelineMarker[];
  onPlayPause: () => void;
  onSeek: (tick: number) => void;
  onSpeedChange: (speed: number) => void;
  onJumpToKeyframe: (direction: 'prev' | 'next') => void;
  isFullscreen?: boolean;
  onToggleFullscreen?: () => void;
  className?: string;
}

const SPEED_OPTIONS = [0.25, 0.5, 1, 2, 4, 8];

export function ReplayControls({
  currentTick,
  totalTicks,
  isPlaying,
  playbackSpeed,
  keyframeTicks,
  eventMarkers,
  onPlayPause,
  onSeek,
  onSpeedChange,
  onJumpToKeyframe,
  isFullscreen,
  onToggleFullscreen,
  className,
}: ReplayControlsProps) {
  // Format tick as time display (assuming 10 ticks = 1 day in simulation)
  const formatTick = useCallback((tick: number): string => {
    const days = Math.floor(tick / 10);
    const hours = Math.floor((tick % 10) * 2.4);
    return `D${days}:${hours.toString().padStart(2, '0')}h`;
  }, []);

  // Calculate progress percentage
  const progress = totalTicks > 0 ? (currentTick / totalTicks) * 100 : 0;

  // Find nearby markers for tooltip
  const nearbyMarkers = useMemo(() => {
    return eventMarkers.filter(m => Math.abs(m.tick - currentTick) < 5);
  }, [eventMarkers, currentTick]);

  // Handle slider change
  const handleSliderChange = useCallback((value: number[]) => {
    const tick = Math.round((value[0] / 100) * totalTicks);
    onSeek(tick);
  }, [totalTicks, onSeek]);

  // Cycle through speed options
  const cycleSpeed = useCallback(() => {
    const currentIndex = SPEED_OPTIONS.indexOf(playbackSpeed);
    const nextIndex = (currentIndex + 1) % SPEED_OPTIONS.length;
    onSpeedChange(SPEED_OPTIONS[nextIndex]);
  }, [playbackSpeed, onSpeedChange]);

  return (
    <div className={cn(
      'bg-black/80 border-b border-white/10 px-4 py-2',
      className
    )}>
      <div className="flex items-center gap-4">
        {/* Playback controls */}
        <div className="flex items-center gap-1">
          {/* Skip to start */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onSeek(0)}
            className="h-8 w-8 p-0 text-white/60 hover:text-cyan-400"
            title="Jump to start"
          >
            <SkipBack className="h-4 w-4" />
          </Button>

          {/* Previous keyframe */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onJumpToKeyframe('prev')}
            className="h-8 w-8 p-0 text-white/60 hover:text-cyan-400"
            title="Previous keyframe"
          >
            <Rewind className="h-4 w-4" />
          </Button>

          {/* Play/Pause */}
          <Button
            variant="ghost"
            size="sm"
            onClick={onPlayPause}
            className="h-10 w-10 p-0 text-cyan-400 hover:text-cyan-300"
            title={isPlaying ? 'Pause' : 'Play'}
          >
            {isPlaying ? (
              <Pause className="h-6 w-6" />
            ) : (
              <Play className="h-6 w-6" />
            )}
          </Button>

          {/* Next keyframe */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onJumpToKeyframe('next')}
            className="h-8 w-8 p-0 text-white/60 hover:text-cyan-400"
            title="Next keyframe"
          >
            <FastForward className="h-4 w-4" />
          </Button>

          {/* Skip to end */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onSeek(totalTicks)}
            className="h-8 w-8 p-0 text-white/60 hover:text-cyan-400"
            title="Jump to end"
          >
            <SkipForward className="h-4 w-4" />
          </Button>
        </div>

        {/* Time display */}
        <div className="flex items-center gap-2 min-w-[180px] font-mono text-sm">
          <span className="text-cyan-400">{formatTick(currentTick)}</span>
          <span className="text-white/40">/</span>
          <span className="text-white/60">{formatTick(totalTicks)}</span>
          <span className="text-white/30 text-xs">({currentTick}/{totalTicks})</span>
        </div>

        {/* Timeline slider */}
        <div className="flex-1 relative">
          <Slider
            value={[progress]}
            min={0}
            max={100}
            step={0.1}
            onValueChange={handleSliderChange}
            className="cursor-pointer"
          />

          {/* Keyframe markers */}
          <div className="absolute top-1/2 left-0 right-0 -translate-y-1/2 pointer-events-none">
            {keyframeTicks.map(tick => {
              const position = (tick / totalTicks) * 100;
              return (
                <div
                  key={tick}
                  className="absolute w-0.5 h-2 bg-cyan-500/50"
                  style={{ left: `${position}%` }}
                  title={`Keyframe at tick ${tick}`}
                />
              );
            })}
          </div>

          {/* Event markers */}
          <div className="absolute top-1/2 left-0 right-0 -translate-y-1/2 pointer-events-none">
            {eventMarkers.map((marker, idx) => {
              const position = (marker.tick / totalTicks) * 100;
              const isEvent = marker.type === 'event';
              return (
                <div
                  key={`${marker.tick}-${idx}`}
                  className={cn(
                    'absolute w-1 h-3 -translate-y-1',
                    isEvent ? 'bg-purple-500' : 'bg-yellow-500/50'
                  )}
                  style={{ left: `${position}%` }}
                  title={marker.label}
                />
              );
            })}
          </div>
        </div>

        {/* Speed control */}
        <Button
          variant="ghost"
          size="sm"
          onClick={cycleSpeed}
          className="h-8 px-2 text-white/60 hover:text-cyan-400 font-mono text-sm min-w-[60px]"
          title="Change playback speed"
        >
          {playbackSpeed}x
        </Button>

        {/* Fullscreen toggle */}
        {onToggleFullscreen && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onToggleFullscreen}
            className="h-8 w-8 p-0 text-white/60 hover:text-cyan-400"
            title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
          >
            {isFullscreen ? (
              <Minimize2 className="h-4 w-4" />
            ) : (
              <Maximize2 className="h-4 w-4" />
            )}
          </Button>
        )}
      </div>

      {/* Active markers tooltip */}
      {nearbyMarkers.length > 0 && (
        <div className="mt-1 flex items-center gap-2 text-xs text-purple-300">
          <span className="text-white/40">Events:</span>
          {nearbyMarkers.slice(0, 3).map((m, i) => (
            <span key={i} className="bg-purple-900/50 px-1 rounded">
              {m.label}
            </span>
          ))}
          {nearbyMarkers.length > 3 && (
            <span className="text-white/40">+{nearbyMarkers.length - 3} more</span>
          )}
        </div>
      )}
    </div>
  );
}

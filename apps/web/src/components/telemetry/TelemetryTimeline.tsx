'use client';

/**
 * TelemetryTimeline Component
 * Time scrubber for navigating simulation telemetry.
 * Reference: project.md §6.8 (Telemetry), C3 (read-only replay)
 *
 * IMPORTANT: This is READ-ONLY. It must NEVER trigger new simulations.
 */

import { memo, useState, useCallback, useRef, useEffect } from 'react';
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  ChevronLeft,
  ChevronRight,
  Clock,
  Maximize2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

interface TelemetryTimelineProps {
  currentTick: number;
  totalTicks: number;
  onTickChange: (tick: number) => void;
  isPlaying?: boolean;
  onPlayPause?: () => void;
  playbackSpeed?: number;
  onSpeedChange?: (speed: number) => void;
  tickInterval?: number; // ms between tick marks
  markers?: { tick: number; label: string; color?: string }[];
  className?: string;
}

const PLAYBACK_SPEEDS = [0.5, 1, 2, 4, 8];

export const TelemetryTimeline = memo(function TelemetryTimeline({
  currentTick,
  totalTicks,
  onTickChange,
  isPlaying = false,
  onPlayPause,
  playbackSpeed = 1,
  onSpeedChange,
  tickInterval = 100,
  markers = [],
  className,
}: TelemetryTimelineProps) {
  const timelineRef = useRef<HTMLDivElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [showSpeedMenu, setShowSpeedMenu] = useState(false);

  // Calculate progress percentage
  const progress = totalTicks > 0 ? (currentTick / totalTicks) * 100 : 0;

  // Handle timeline click/drag
  const handleTimelineInteraction = useCallback(
    (clientX: number) => {
      if (!timelineRef.current || totalTicks === 0) return;

      const rect = timelineRef.current.getBoundingClientRect();
      const x = clientX - rect.left;
      const percentage = Math.max(0, Math.min(1, x / rect.width));
      const newTick = Math.round(percentage * totalTicks);

      onTickChange(newTick);
    },
    [totalTicks, onTickChange]
  );

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      setIsDragging(true);
      handleTimelineInteraction(e.clientX);
    },
    [handleTimelineInteraction]
  );

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (isDragging) {
        handleTimelineInteraction(e.clientX);
      }
    },
    [isDragging, handleTimelineInteraction]
  );

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  // Global mouse event listeners for drag
  useEffect(() => {
    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
      return () => {
        window.removeEventListener('mousemove', handleMouseMove);
        window.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, handleMouseMove, handleMouseUp]);

  // Step forward/backward
  const stepForward = useCallback(() => {
    onTickChange(Math.min(totalTicks, currentTick + 1));
  }, [currentTick, totalTicks, onTickChange]);

  const stepBackward = useCallback(() => {
    onTickChange(Math.max(0, currentTick - 1));
  }, [currentTick, onTickChange]);

  const jumpToStart = useCallback(() => {
    onTickChange(0);
  }, [onTickChange]);

  const jumpToEnd = useCallback(() => {
    onTickChange(totalTicks);
  }, [totalTicks, onTickChange]);

  // Format time display
  const formatTick = (tick: number) => {
    const seconds = Math.floor((tick * tickInterval) / 1000);
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className={cn('space-y-2', className)}>
      {/* Controls Bar */}
      <div className="flex items-center gap-2">
        {/* Playback Controls */}
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={jumpToStart}
            title="Jump to Start"
          >
            <SkipBack className="w-3.5 h-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={stepBackward}
            title="Step Backward"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
          </Button>
          <Button
            variant={isPlaying ? 'secondary' : 'primary'}
            size="icon-sm"
            onClick={onPlayPause}
            title={isPlaying ? 'Pause' : 'Play'}
          >
            {isPlaying ? (
              <Pause className="w-3.5 h-3.5" />
            ) : (
              <Play className="w-3.5 h-3.5" />
            )}
          </Button>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={stepForward}
            title="Step Forward"
          >
            <ChevronRight className="w-3.5 h-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={jumpToEnd}
            title="Jump to End"
          >
            <SkipForward className="w-3.5 h-3.5" />
          </Button>
        </div>

        {/* Time Display */}
        <div className="flex items-center gap-2 px-3 py-1 bg-white/5 border border-white/10">
          <Clock className="w-3 h-3 text-white/40" />
          <span className="text-xs font-mono text-white">
            {formatTick(currentTick)}
          </span>
          <span className="text-xs font-mono text-white/40">/</span>
          <span className="text-xs font-mono text-white/60">
            {formatTick(totalTicks)}
          </span>
        </div>

        {/* Tick Counter */}
        <div className="px-2 py-1 bg-white/5 border border-white/10">
          <span className="text-xs font-mono text-white/60">
            Tick: <span className="text-white">{currentTick}</span>
            <span className="text-white/40"> / {totalTicks}</span>
          </span>
        </div>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Speed Control */}
        <div className="relative">
          <button
            onClick={() => setShowSpeedMenu(!showSpeedMenu)}
            className="flex items-center gap-1 px-2 py-1 text-xs font-mono bg-white/5 border border-white/10 text-white/60 hover:text-white hover:border-white/20 transition-colors"
          >
            <span>{playbackSpeed}x</span>
          </button>

          {showSpeedMenu && (
            <div className="absolute bottom-full right-0 mb-1 bg-black border border-white/20 shadow-lg z-10">
              {PLAYBACK_SPEEDS.map((speed) => (
                <button
                  key={speed}
                  onClick={() => {
                    onSpeedChange?.(speed);
                    setShowSpeedMenu(false);
                  }}
                  className={cn(
                    'w-full px-3 py-1.5 text-xs font-mono text-left transition-colors',
                    speed === playbackSpeed
                      ? 'bg-white text-black'
                      : 'text-white/60 hover:text-white hover:bg-white/5'
                  )}
                >
                  {speed}x
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Timeline Track */}
      <div
        ref={timelineRef}
        className="relative h-8 bg-white/5 border border-white/10 cursor-pointer"
        onMouseDown={handleMouseDown}
      >
        {/* Progress Fill */}
        <div
          className="absolute top-0 left-0 h-full bg-gradient-to-r from-cyan-500/30 to-cyan-500/10"
          style={{ width: `${progress}%` }}
        />

        {/* Markers */}
        {markers.map((marker, index) => {
          const markerPosition = (marker.tick / totalTicks) * 100;
          return (
            <div
              key={index}
              className="absolute top-0 w-0.5 h-full"
              style={{
                left: `${markerPosition}%`,
                backgroundColor: marker.color || 'rgba(255,255,255,0.3)',
              }}
              title={`${marker.label} (Tick ${marker.tick})`}
            />
          );
        })}

        {/* Current Position Indicator */}
        <div
          className="absolute top-0 h-full w-0.5 bg-cyan-400 shadow-[0_0_8px_rgba(6,182,212,0.5)]"
          style={{ left: `${progress}%` }}
        >
          {/* Handle */}
          <div className="absolute -top-1 -translate-x-1/2 w-3 h-3 bg-cyan-400 rotate-45" />
        </div>

        {/* Hover Time Display */}
        <div className="absolute bottom-full mb-1 left-1/2 -translate-x-1/2 px-2 py-0.5 bg-black border border-white/20 text-[10px] font-mono text-white opacity-0 hover:opacity-100 transition-opacity pointer-events-none">
          {formatTick(currentTick)}
        </div>
      </div>

      {/* Tick Marks */}
      <div className="relative h-3">
        {Array.from({ length: 11 }).map((_, i) => {
          const tickMark = Math.round((i / 10) * totalTicks);
          const position = (i / 10) * 100;
          return (
            <div
              key={i}
              className="absolute flex flex-col items-center"
              style={{ left: `${position}%`, transform: 'translateX(-50%)' }}
            >
              <div className="w-px h-1.5 bg-white/20" />
              <span className="text-[8px] font-mono text-white/30">
                {tickMark}
              </span>
            </div>
          );
        })}
      </div>

      {/* Read-Only Notice */}
      <div className="flex items-center gap-1.5 px-2 py-1 bg-blue-500/10 border border-blue-500/20">
        <span className="text-[10px] font-mono text-blue-400">
          READ-ONLY REPLAY - This view does not trigger new simulations
        </span>
      </div>
    </div>
  );
});

export default TelemetryTimeline;

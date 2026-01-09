'use client';

/**
 * 2D Replay Canvas Component
 * Reference: project.md §11 Phase 8, Interaction_design.md §5.17
 *
 * Main visualization canvas with semantic zones and agent sprites.
 * Uses layout profiles for positioning and rendering mappings for visual properties.
 */

import React, { useRef, useEffect, useMemo, useCallback } from 'react';
import { cn } from '@/lib/utils';

// Agent state at a specific tick
export interface AgentState {
  agent_id: string;
  tick: number;
  position: { x: number; y: number };
  segment: string;
  region?: string;
  stance: number;
  emotion: number;
  influence: number;
  exposure: number;
  last_action?: string;
  last_event?: string;
  beliefs?: Record<string, number>;
}

// Environment state at a specific tick
export interface EnvironmentState {
  tick: number;
  variables: Record<string, unknown>;
  active_events: string[];
  metrics: Record<string, number>;
}

// Complete world state at a tick
export interface WorldState {
  tick: number;
  timestamp: string;
  agents: Record<string, AgentState>;
  environment: EnvironmentState;
  event_log: Array<Record<string, unknown>>;
}

// Zone definition for layout
export interface ZoneDefinition {
  zone_id: string;
  name: string;
  bounds: { x: number; y: number; width: number; height: number };
  segments: string[];
  color: string;
}

// Layer visibility settings
export interface LayerVisibility {
  stance: boolean;
  emotion: boolean;
  influence: boolean;
  exposure: boolean;
  events: boolean;
  trails: boolean;
}

interface ReplayCanvasProps {
  worldState: WorldState | null;
  zones: ZoneDefinition[];
  layerVisibility: LayerVisibility;
  selectedAgentId: string | null;
  onAgentClick: (agentId: string) => void;
  onZoneClick?: (zoneId: string) => void;
  zoom: number;
  pan: { x: number; y: number };
  onPanChange?: (pan: { x: number; y: number }) => void;
  className?: string;
}

// Color utilities
function stanceToColor(stance: number): string {
  // -1 (negative) = red, 0 = neutral/gray, +1 (positive) = green
  if (stance < 0) {
    const intensity = Math.abs(stance);
    return `rgb(${Math.round(255 * intensity)}, ${Math.round(80 * (1 - intensity))}, ${Math.round(80 * (1 - intensity))})`;
  } else if (stance > 0) {
    const intensity = stance;
    return `rgb(${Math.round(80 * (1 - intensity))}, ${Math.round(255 * intensity)}, ${Math.round(80 * (1 - intensity))})`;
  }
  return 'rgb(128, 128, 128)';
}

function emotionToGlow(emotion: number): string {
  // 0 = no glow, 1 = strong glow
  const alpha = Math.max(0, Math.min(1, emotion)) * 0.5;
  return `rgba(255, 215, 0, ${alpha})`; // Gold glow
}

function influenceToSize(influence: number, baseSize: number): number {
  // influence 0-1 maps to baseSize to 2x baseSize
  return baseSize * (1 + Math.max(0, Math.min(1, influence)));
}

export function ReplayCanvas({
  worldState,
  zones,
  layerVisibility,
  selectedAgentId,
  onAgentClick,
  onZoneClick,
  zoom,
  pan,
  onPanChange,
  className,
}: ReplayCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const isDragging = useRef(false);
  const lastMousePos = useRef({ x: 0, y: 0 });

  // Canvas dimensions
  const CANVAS_WIDTH = 800;
  const CANVAS_HEIGHT = 600;
  const BASE_AGENT_SIZE = 8;

  // Get agent positions based on their segment/region and zone layout
  const getAgentPosition = useCallback((agent: AgentState, index: number): { x: number; y: number } => {
    // Find zone for this agent's segment
    const zone = zones.find(z => z.segments.includes(agent.segment));

    if (zone) {
      // Position within zone using stored position or grid
      if (agent.position.x !== 0 && agent.position.y !== 0) {
        // Scale to zone bounds
        return {
          x: zone.bounds.x + agent.position.x * zone.bounds.width,
          y: zone.bounds.y + agent.position.y * zone.bounds.height,
        };
      }
      // Grid layout within zone
      const zoneAgents = Object.values(worldState?.agents || {}).filter(
        a => zones.find(z => z.segments.includes(a.segment))?.zone_id === zone.zone_id
      );
      const agentIndex = zoneAgents.findIndex(a => a.agent_id === agent.agent_id);
      const cols = Math.ceil(Math.sqrt(zoneAgents.length));
      const row = Math.floor(agentIndex / cols);
      const col = agentIndex % cols;
      const cellWidth = zone.bounds.width / (cols + 1);
      const cellHeight = zone.bounds.height / (Math.ceil(zoneAgents.length / cols) + 1);

      return {
        x: zone.bounds.x + (col + 1) * cellWidth,
        y: zone.bounds.y + (row + 1) * cellHeight,
      };
    }

    // Default: grid in center
    const cols = Math.ceil(Math.sqrt(Object.keys(worldState?.agents || {}).length));
    const row = Math.floor(index / cols);
    const col = index % cols;
    return {
      x: 100 + col * 25,
      y: 100 + row * 25,
    };
  }, [zones, worldState?.agents]);

  // Draw canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!canvas || !ctx) return;

    // Clear canvas
    ctx.fillStyle = '#0a0a0f';
    ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);

    // Apply zoom and pan
    ctx.save();
    ctx.translate(pan.x, pan.y);
    ctx.scale(zoom, zoom);

    // Draw zones
    zones.forEach(zone => {
      ctx.fillStyle = zone.color + '33'; // 20% opacity
      ctx.strokeStyle = zone.color + '88';
      ctx.lineWidth = 1 / zoom;

      ctx.beginPath();
      ctx.rect(zone.bounds.x, zone.bounds.y, zone.bounds.width, zone.bounds.height);
      ctx.fill();
      ctx.stroke();

      // Zone label
      ctx.fillStyle = zone.color + 'cc';
      ctx.font = `${12 / zoom}px monospace`;
      ctx.fillText(zone.name, zone.bounds.x + 5, zone.bounds.y + 15);
    });

    // Draw agents
    if (worldState?.agents) {
      const agents = Object.values(worldState.agents);

      agents.forEach((agent, index) => {
        const pos = getAgentPosition(agent, index);
        const isSelected = agent.agent_id === selectedAgentId;
        const size = layerVisibility.influence
          ? influenceToSize(agent.influence, BASE_AGENT_SIZE)
          : BASE_AGENT_SIZE;

        // Glow effect for emotion
        if (layerVisibility.emotion && agent.emotion > 0.3) {
          const glowSize = size * 2;
          const gradient = ctx.createRadialGradient(pos.x, pos.y, size / 2, pos.x, pos.y, glowSize);
          gradient.addColorStop(0, emotionToGlow(agent.emotion));
          gradient.addColorStop(1, 'transparent');
          ctx.fillStyle = gradient;
          ctx.beginPath();
          ctx.arc(pos.x, pos.y, glowSize, 0, Math.PI * 2);
          ctx.fill();
        }

        // Agent circle
        ctx.fillStyle = layerVisibility.stance ? stanceToColor(agent.stance) : '#00ffff';
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, size / zoom, 0, Math.PI * 2);
        ctx.fill();

        // Selection ring
        if (isSelected) {
          ctx.strokeStyle = '#ff00ff';
          ctx.lineWidth = 2 / zoom;
          ctx.beginPath();
          ctx.arc(pos.x, pos.y, size / zoom + 4 / zoom, 0, Math.PI * 2);
          ctx.stroke();
        }

        // Exposure indicator (outer ring)
        if (layerVisibility.exposure && agent.exposure > 0.5) {
          ctx.strokeStyle = `rgba(255, 165, 0, ${agent.exposure * 0.8})`;
          ctx.lineWidth = 2 / zoom;
          ctx.beginPath();
          ctx.arc(pos.x, pos.y, size / zoom + 2 / zoom, 0, Math.PI * 2);
          ctx.stroke();
        }

        // Event indicator (pulse animation would need requestAnimationFrame)
        if (layerVisibility.events && agent.last_event) {
          ctx.strokeStyle = '#ff00ff';
          ctx.lineWidth = 1 / zoom;
          ctx.setLineDash([2 / zoom, 2 / zoom]);
          ctx.beginPath();
          ctx.arc(pos.x, pos.y, size / zoom + 8 / zoom, 0, Math.PI * 2);
          ctx.stroke();
          ctx.setLineDash([]);
        }
      });
    }

    // Draw active events overlay
    if (worldState?.environment.active_events.length) {
      ctx.fillStyle = 'rgba(255, 0, 255, 0.1)';
      ctx.font = `${10 / zoom}px monospace`;
      ctx.fillText(
        `Events: ${worldState.environment.active_events.join(', ')}`,
        10,
        CANVAS_HEIGHT / zoom - 10
      );
    }

    ctx.restore();
  }, [worldState, zones, layerVisibility, selectedAgentId, zoom, pan, getAgentPosition]);

  // Handle mouse interactions
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    isDragging.current = true;
    lastMousePos.current = { x: e.clientX, y: e.clientY };
  }, []);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isDragging.current || !onPanChange) return;

    const dx = e.clientX - lastMousePos.current.x;
    const dy = e.clientY - lastMousePos.current.y;
    lastMousePos.current = { x: e.clientX, y: e.clientY };

    onPanChange({ x: pan.x + dx, y: pan.y + dy });
  }, [pan, onPanChange]);

  const handleMouseUp = useCallback(() => {
    isDragging.current = false;
  }, []);

  const handleClick = useCallback((e: React.MouseEvent) => {
    if (!worldState?.agents || !canvasRef.current) return;

    const rect = canvasRef.current.getBoundingClientRect();
    const clickX = (e.clientX - rect.left - pan.x) / zoom;
    const clickY = (e.clientY - rect.top - pan.y) / zoom;

    // Find clicked agent
    const agents = Object.values(worldState.agents);
    for (let i = 0; i < agents.length; i++) {
      const agent = agents[i];
      const pos = getAgentPosition(agent, i);
      const size = layerVisibility.influence
        ? influenceToSize(agent.influence, BASE_AGENT_SIZE)
        : BASE_AGENT_SIZE;

      const distance = Math.sqrt(Math.pow(clickX - pos.x, 2) + Math.pow(clickY - pos.y, 2));
      if (distance <= size / zoom + 5) {
        onAgentClick(agent.agent_id);
        return;
      }
    }

    // Check zone clicks
    if (onZoneClick) {
      const zone = zones.find(z =>
        clickX >= z.bounds.x &&
        clickX <= z.bounds.x + z.bounds.width &&
        clickY >= z.bounds.y &&
        clickY <= z.bounds.y + z.bounds.height
      );
      if (zone) {
        onZoneClick(zone.zone_id);
      }
    }
  }, [worldState?.agents, pan, zoom, getAgentPosition, layerVisibility.influence, onAgentClick, onZoneClick, zones]);

  // Tick and agent count display
  const tickDisplay = worldState?.tick ?? 0;
  const agentCount = Object.keys(worldState?.agents || {}).length;

  return (
    <div
      ref={containerRef}
      className={cn('relative bg-black border border-white/10 overflow-hidden', className)}
    >
      <canvas
        ref={canvasRef}
        width={CANVAS_WIDTH}
        height={CANVAS_HEIGHT}
        className="w-full h-full cursor-move"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onClick={handleClick}
      />

      {/* Tick indicator overlay */}
      <div className="absolute top-2 left-2 bg-black/80 border border-white/20 px-2 py-1 font-mono text-xs">
        <span className="text-white/60">TICK:</span>{' '}
        <span className="text-cyan-400">{tickDisplay}</span>
        <span className="text-white/40 ml-2">|</span>
        <span className="text-white/60 ml-2">AGENTS:</span>{' '}
        <span className="text-cyan-400">{agentCount}</span>
      </div>

      {/* Active events overlay */}
      {worldState?.environment.active_events.length ? (
        <div className="absolute bottom-2 left-2 bg-purple-900/80 border border-purple-500/50 px-2 py-1 font-mono text-xs text-purple-300">
          {worldState.environment.active_events.length} active event(s)
        </div>
      ) : null}

      {/* Loading state */}
      {!worldState && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/50">
          <div className="text-white/60 font-mono text-sm animate-pulse">
            Loading world state...
          </div>
        </div>
      )}
    </div>
  );
}

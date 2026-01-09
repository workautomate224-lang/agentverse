// useNPCMovement - NPC Movement AI and Pathfinding
// Handles random waypoint selection, collision detection, and movement

import { useCallback, useRef } from 'react';
import { NPCData, WorldData, Position, Direction } from '../types';
import { isWalkable } from '../utils/worldGenerator';

interface UseNPCMovementOptions {
  minWaitTime?: number;  // Minimum time before selecting new target (ms)
  maxWaitTime?: number;  // Maximum time before selecting new target (ms)
  minSpeed?: number;     // Minimum walking speed (pixels/second)
  maxSpeed?: number;     // Maximum walking speed (pixels/second)
  collisionRadius?: number; // Collision detection radius
}

const DEFAULT_OPTIONS: UseNPCMovementOptions = {
  minWaitTime: 2000,
  maxWaitTime: 6000,
  minSpeed: 30,
  maxSpeed: 60,
  collisionRadius: 16,
};

export function useNPCMovement(options: UseNPCMovementOptions = {}) {
  const config = { ...DEFAULT_OPTIONS, ...options };
  const lastUpdateRef = useRef<number>(Date.now());

  // Calculate direction from position to target
  const getDirection = useCallback((from: Position, to: Position): Direction => {
    const dx = to.x - from.x;
    const dy = to.y - from.y;

    if (Math.abs(dx) > Math.abs(dy)) {
      return dx > 0 ? 'right' : 'left';
    } else {
      return dy > 0 ? 'down' : 'up';
    }
  }, []);

  // Check if path between two points is clear
  const isPathClear = useCallback((
    from: Position,
    to: Position,
    worldData: WorldData,
    npcs: NPCData[],
    currentNpcId?: string
  ): boolean => {
    // Check destination is walkable
    if (!isWalkable(worldData, to.x, to.y)) {
      return false;
    }

    // Check for NPC collisions at destination
    for (const npc of npcs) {
      if (npc.config.id === currentNpcId) continue;

      const distance = Math.hypot(
        npc.position.x - to.x,
        npc.position.y - to.y
      );

      if (distance < config.collisionRadius!) {
        return false;
      }
    }

    // Simple line-of-sight check (sample points along path)
    const steps = Math.ceil(Math.hypot(to.x - from.x, to.y - from.y) / worldData.config.tileSize);
    for (let i = 1; i < steps; i++) {
      const t = i / steps;
      const checkX = from.x + (to.x - from.x) * t;
      const checkY = from.y + (to.y - from.y) * t;

      if (!isWalkable(worldData, checkX, checkY)) {
        return false;
      }
    }

    return true;
  }, [config.collisionRadius]);

  // Select a new random target position
  const selectNewTarget = useCallback((
    npc: NPCData,
    worldData: WorldData,
    npcs: NPCData[]
  ): Position | null => {
    const { tileSize, width, height } = worldData.config;
    const maxAttempts = 20;

    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      // Random direction and distance
      const angle = Math.random() * Math.PI * 2;
      const distance = 50 + Math.random() * 150; // 50-200 pixels

      const targetX = npc.position.x + Math.cos(angle) * distance;
      const targetY = npc.position.y + Math.sin(angle) * distance;

      // Clamp to world bounds
      const clampedX = Math.max(tileSize, Math.min(targetX, (width - 1) * tileSize));
      const clampedY = Math.max(tileSize, Math.min(targetY, (height - 1) * tileSize));

      const target = { x: clampedX, y: clampedY };

      // Check if path is valid
      if (isPathClear(npc.position, target, worldData, npcs, npc.config.id)) {
        return target;
      }
    }

    return null; // No valid target found
  }, [isPathClear]);

  // Update NPC position based on target
  const updateNPCPosition = useCallback((
    npc: NPCData,
    delta: number,
    worldData: WorldData,
    npcs: NPCData[]
  ): NPCData => {
    const now = Date.now();
    const timeSinceLastAction = now - npc.lastActionTime;

    // If idle and enough time has passed, select new target
    if (npc.state === 'idle' && !npc.targetPosition) {
      const waitTime = config.minWaitTime! + Math.random() * (config.maxWaitTime! - config.minWaitTime!);

      if (timeSinceLastAction > waitTime) {
        const newTarget = selectNewTarget(npc, worldData, npcs);

        if (newTarget) {
          return {
            ...npc,
            targetPosition: newTarget,
            state: 'walking',
            direction: getDirection(npc.position, newTarget),
            lastActionTime: now,
          };
        }
      }

      return npc;
    }

    // If walking, move towards target
    if (npc.state === 'walking' && npc.targetPosition) {
      const dx = npc.targetPosition.x - npc.position.x;
      const dy = npc.targetPosition.y - npc.position.y;
      const distance = Math.hypot(dx, dy);

      // Reached target
      if (distance < 5) {
        return {
          ...npc,
          position: npc.targetPosition,
          targetPosition: null,
          state: 'idle',
          lastActionTime: now,
        };
      }

      // Calculate movement
      const moveDistance = npc.speed * (delta / 60); // Normalize for 60fps
      const ratio = Math.min(moveDistance / distance, 1);

      const newX = npc.position.x + dx * ratio;
      const newY = npc.position.y + dy * ratio;

      // Check if new position is valid
      if (isWalkable(worldData, newX, newY)) {
        return {
          ...npc,
          position: { x: newX, y: newY },
          direction: getDirection(npc.position, npc.targetPosition),
        };
      } else {
        // Hit obstacle, stop
        return {
          ...npc,
          targetPosition: null,
          state: 'idle',
          lastActionTime: now,
        };
      }
    }

    return npc;
  }, [config.minWaitTime, config.maxWaitTime, selectNewTarget, getDirection]);

  // Generate random speed for NPC
  const getRandomSpeed = useCallback((): number => {
    return config.minSpeed! + Math.random() * (config.maxSpeed! - config.minSpeed!);
  }, [config.minSpeed, config.maxSpeed]);

  return {
    updateNPCPosition,
    selectNewTarget,
    isPathClear,
    getDirection,
    getRandomSpeed,
  };
}

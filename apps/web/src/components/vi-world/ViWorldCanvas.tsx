'use client';

// ViWorldCanvas - PixiJS Canvas Component with Camera System
// Manages the PixiJS application, world rendering, NPCs, camera, and game loop

import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import * as PIXI from 'pixi.js';
import { usePixiApp, useGameLoop } from './hooks/usePixiApp';
import { useNPCMovement } from './hooks/useNPCMovement';
import { useNPCChat } from './hooks/useNPCChat';
import { WorldRenderer, createDecorations } from './WorldRenderer';
import { NPC, createNPCFromPersona } from './NPC';
import { ChatBubble, createChatBubble } from './ChatBubble';
import { Camera } from './Camera';
import { Minimap } from './Minimap';
import { generateWorld, getRandomSpawnPoint } from './utils/worldGenerator';
import { getCharacterColors } from './utils/colors';
import { WorldData, NPCConfig, NPCData, WorldStats, Position } from './types';

interface ViWorldCanvasProps {
  npcs: NPCConfig[];
  onStatsUpdate?: (stats: WorldStats) => void;
  width?: number;
  height?: number;
  seed?: number;
}

// World size multiplier - creates a 10x larger world
const WORLD_SIZE_MULTIPLIER = 3; // 150x114 tiles = ~9x original

export function ViWorldCanvas({
  npcs,
  onStatsUpdate,
  width = 800,
  height = 608,
  seed,
}: ViWorldCanvasProps) {
  // PixiJS app
  const { app, containerRef, isReady } = usePixiApp({
    width,
    height,
    backgroundColor: 0x87CEEB,
  });

  // State
  const [worldData, setWorldData] = useState<WorldData | null>(null);
  const [npcPositions, setNpcPositions] = useState<Position[]>([]);
  const worldRendererRef = useRef<WorldRenderer | null>(null);
  const npcInstancesRef = useRef<Map<string, NPC>>(new Map());
  const chatBubblesRef = useRef<Map<string, ChatBubble>>(new Map());
  const npcContainerRef = useRef<PIXI.Container | null>(null);
  const chatContainerRef = useRef<PIXI.Container | null>(null);
  const worldContainerRef = useRef<PIXI.Container | null>(null);
  const cameraRef = useRef<Camera | null>(null);

  // Hooks
  const movement = useNPCMovement();
  const chat = useNPCChat();

  // Stats
  const statsRef = useRef<WorldStats>({
    population: 0,
    activeChats: 0,
    totalMessages: 0,
  });

  // Calculate world dimensions
  const worldWidth = useMemo(() => 150 * 16, []); // 150 tiles * 16px
  const worldHeight = useMemo(() => 114 * 16, []); // 114 tiles * 16px

  // Initialize world
  useEffect(() => {
    const world = generateWorld({
      width: 150,
      height: 114,
      tileSize: 16,
      seed: seed || Date.now(),
    });
    setWorldData(world);
  }, [seed]);

  // Initialize PixiJS scene with camera
  useEffect(() => {
    if (!app || !isReady || !worldData) return;

    // Clear existing scene
    app.stage.removeChildren();

    // Create main world container (will be transformed by camera)
    const worldContainer = new PIXI.Container();
    worldContainer.sortableChildren = true;
    worldContainerRef.current = worldContainer;
    app.stage.addChild(worldContainer);

    // Create world renderer
    const worldRenderer = new WorldRenderer(worldData);
    worldRendererRef.current = worldRenderer;
    worldContainer.addChild(worldRenderer.container);

    // Add decorations
    const decorations = createDecorations(worldData);
    worldContainer.addChild(decorations);

    // Create NPC container
    const npcContainer = new PIXI.Container();
    npcContainer.sortableChildren = true;
    npcContainer.zIndex = 20;
    npcContainerRef.current = npcContainer;
    worldContainer.addChild(npcContainer);

    // Create chat bubble container
    const chatContainer = new PIXI.Container();
    chatContainer.zIndex = 100;
    chatContainerRef.current = chatContainer;
    worldContainer.addChild(chatContainer);

    // Initialize camera
    const camera = new Camera(worldContainer, {
      viewportWidth: width,
      viewportHeight: height,
      worldWidth: worldData.config.width * worldData.config.tileSize,
      worldHeight: worldData.config.height * worldData.config.tileSize,
      minZoom: 0.5,
      maxZoom: 2,
    });
    cameraRef.current = camera;

    // Cleanup
    return () => {
      worldRenderer.destroy();
      npcContainer.destroy({ children: true });
      chatContainer.destroy({ children: true });
      cameraRef.current = null;
    };
  }, [app, isReady, worldData, width, height]);

  // Initialize NPCs
  useEffect(() => {
    if (!app || !isReady || !worldData || !npcContainerRef.current) return;

    const npcContainer = npcContainerRef.current;
    const npcInstances = npcInstancesRef.current;

    // Clear existing NPCs
    for (const npc of npcInstances.values()) {
      npc.destroy();
    }
    npcInstances.clear();

    // Create new NPCs
    for (const npcConfig of npcs) {
      // Use backend position if available, otherwise generate random spawn
      const position = npcConfig.initialPosition || getRandomSpawnPoint(worldData);
      const speed = movement.getRandomSpeed();
      const colors = getCharacterColors(npcConfig.id);

      const npc = createNPCFromPersona(
        npcConfig.id,
        npcConfig.name,
        npcConfig.gender,
        npcConfig.traits || [],
        position,
        speed,
        colors
      );

      // Apply backend state if available
      if (npcConfig.initialState) {
        npc.data.state = npcConfig.initialState;
      }
      if (npcConfig.initialDirection) {
        npc.data.direction = npcConfig.initialDirection;
      }

      npcContainer.addChild(npc.container);
      npcInstances.set(npcConfig.id, npc);
    }

    // Update stats
    statsRef.current.population = npcs.length;
    onStatsUpdate?.(statsRef.current);

    // Cleanup
    return () => {
      for (const npc of npcInstances.values()) {
        npcContainer.removeChild(npc.container);
      }
    };
  }, [app, isReady, worldData, npcs, movement, onStatsUpdate]);

  // Handle mouse/touch events for camera control
  useEffect(() => {
    const container = containerRef.current;
    if (!container || !cameraRef.current) return;

    const camera = cameraRef.current;
    let isPointerDown = false;

    const handlePointerDown = (e: PointerEvent) => {
      isPointerDown = true;
      const rect = container.getBoundingClientRect();
      camera.startDrag(e.clientX - rect.left, e.clientY - rect.top);
      container.style.cursor = 'grabbing';
    };

    const handlePointerMove = (e: PointerEvent) => {
      if (!isPointerDown) return;
      const rect = container.getBoundingClientRect();
      camera.updateDrag(e.clientX - rect.left, e.clientY - rect.top);
    };

    const handlePointerUp = () => {
      isPointerDown = false;
      camera.endDrag();
      container.style.cursor = 'grab';
    };

    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      const rect = container.getBoundingClientRect();
      camera.handleWheel(e.deltaY, e.clientX - rect.left, e.clientY - rect.top);
    };

    // Add event listeners
    container.addEventListener('pointerdown', handlePointerDown);
    container.addEventListener('pointermove', handlePointerMove);
    container.addEventListener('pointerup', handlePointerUp);
    container.addEventListener('pointerleave', handlePointerUp);
    container.addEventListener('wheel', handleWheel, { passive: false });

    // Set initial cursor
    container.style.cursor = 'grab';

    return () => {
      container.removeEventListener('pointerdown', handlePointerDown);
      container.removeEventListener('pointermove', handlePointerMove);
      container.removeEventListener('pointerup', handlePointerUp);
      container.removeEventListener('pointerleave', handlePointerUp);
      container.removeEventListener('wheel', handleWheel);
    };
  }, [containerRef, isReady, worldData]);

  // Handle minimap navigation
  const handleMinimapNavigate = useCallback((x: number, y: number) => {
    if (cameraRef.current) {
      cameraRef.current.panTo(x, y, true);
    }
  }, []);

  // Game loop
  useGameLoop(app, (delta) => {
    if (!worldData) return;

    const npcInstances = npcInstancesRef.current;
    const chatBubbles = chatBubblesRef.current;
    const chatContainer = chatContainerRef.current;
    const camera = cameraRef.current;

    // Update camera
    if (camera) {
      camera.update(delta);
    }

    // Get all NPC data for collision/chat checks
    const allNpcData: NPCData[] = [];
    const positions: Position[] = [];
    for (const npc of npcInstances.values()) {
      const data = npc.getData();
      allNpcData.push(data);
      positions.push(data.position);
    }

    // Update NPC positions for minimap (throttled)
    if (Math.random() < 0.1) {
      setNpcPositions(positions);
    }

    // Update each NPC
    for (const npc of npcInstances.values()) {
      if (npc.data.state === 'chatting') continue;

      const updatedData = movement.updateNPCPosition(
        npc.getData(),
        delta,
        worldData,
        allNpcData
      );
      npc.update(updatedData);
    }

    // Check for new chats (every ~60 frames)
    if (Math.random() < 0.016) {
      const newChat = chat.checkForChat(allNpcData);

      if (newChat) {
        const senderNpc = npcInstances.get(newChat.senderId);
        if (senderNpc && chatContainer) {
          // Create chat bubble
          const bubble = createChatBubble(
            newChat.senderId,
            newChat.message,
            senderNpc.getPosition(),
            chat.chatDuration
          );

          chatContainer.addChild(bubble.container);
          chatBubbles.set(newChat.id, bubble);

          // Set NPC to chatting state
          senderNpc.startChat();

          // Update stats
          statsRef.current.activeChats++;
          statsRef.current.totalMessages++;
          onStatsUpdate?.(statsRef.current);

          // Schedule chat end
          setTimeout(() => {
            senderNpc.endChat();
            statsRef.current.activeChats = Math.max(0, statsRef.current.activeChats - 1);
            onStatsUpdate?.(statsRef.current);
          }, chat.chatDuration);
        }
      }
    }

    // Update chat bubbles
    const elapsed = delta * (1000 / 60);
    for (const [id, bubble] of chatBubbles.entries()) {
      const senderNpc = npcInstances.get(bubble.data.npcId);
      if (senderNpc) {
        bubble.updatePosition(senderNpc.getPosition());
      }

      const isActive = bubble.update(delta, elapsed);
      if (!isActive) {
        chatContainer?.removeChild(bubble.container);
        bubble.destroy();
        chatBubbles.delete(id);
      }
    }

    // Sort NPC container by y position for depth sorting
    if (npcContainerRef.current) {
      npcContainerRef.current.children.sort((a, b) => a.y - b.y);
    }
  });

  return (
    <div className="relative">
      <div
        ref={containerRef}
        className="w-full h-full flex items-center justify-center bg-slate-900 rounded-lg overflow-hidden"
        style={{ minHeight: height }}
      />
      {/* Minimap */}
      {worldData && (
        <Minimap
          camera={cameraRef.current}
          npcPositions={npcPositions}
          worldWidth={worldWidth}
          worldHeight={worldHeight}
          size={150}
          onNavigate={handleMinimapNavigate}
        />
      )}
      {/* Camera controls hint */}
      <div className="absolute bottom-4 left-4 bg-slate-900/80 backdrop-blur-sm rounded-lg px-3 py-2 text-xs text-slate-400">
        <div className="flex items-center gap-2">
          <span>Drag to pan</span>
          <span className="text-slate-600">|</span>
          <span>Scroll to zoom</span>
        </div>
      </div>
    </div>
  );
}

'use client';

// Minimap - Shows overview of the world with camera viewport and NPC positions
// Allows clicking to navigate to different areas

import React, { useRef, useEffect, useCallback } from 'react';
import { Camera } from './Camera';
import { Position } from './types';

interface MinimapProps {
  camera: Camera | null;
  npcPositions: Position[];
  worldWidth: number;
  worldHeight: number;
  size?: number;
  onNavigate?: (x: number, y: number) => void;
}

export function Minimap({
  camera,
  npcPositions,
  worldWidth,
  worldHeight,
  size = 150,
  onNavigate,
}: MinimapProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Calculate minimap dimensions maintaining aspect ratio
  const aspectRatio = worldWidth / worldHeight;
  const minimapWidth = aspectRatio >= 1 ? size : size * aspectRatio;
  const minimapHeight = aspectRatio >= 1 ? size / aspectRatio : size;

  // Scale factors
  const scaleX = minimapWidth / worldWidth;
  const scaleY = minimapHeight / worldHeight;

  // Draw minimap
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !camera) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear
    ctx.clearRect(0, 0, minimapWidth, minimapHeight);

    // Draw world background
    ctx.fillStyle = '#2D5016';
    ctx.fillRect(0, 0, minimapWidth, minimapHeight);

    // Draw simple grid pattern to suggest terrain
    ctx.fillStyle = '#3D6B1E';
    const gridSize = minimapWidth / 10;
    for (let x = 0; x < minimapWidth; x += gridSize * 2) {
      for (let y = 0; y < minimapHeight; y += gridSize * 2) {
        ctx.fillRect(x, y, gridSize, gridSize);
        ctx.fillRect(x + gridSize, y + gridSize, gridSize, gridSize);
      }
    }

    // Draw NPCs as dots
    ctx.fillStyle = '#FFCC00';
    for (const pos of npcPositions) {
      const x = pos.x * scaleX;
      const y = pos.y * scaleY;
      ctx.beginPath();
      ctx.arc(x, y, 2, 0, Math.PI * 2);
      ctx.fill();
    }

    // Draw viewport rectangle
    const minimapData = camera.getMinimapData();
    const viewRect = minimapData.viewportRect;

    ctx.strokeStyle = '#FFFFFF';
    ctx.lineWidth = 2;
    ctx.strokeRect(
      viewRect.x * scaleX,
      viewRect.y * scaleY,
      viewRect.width * scaleX,
      viewRect.height * scaleY
    );

    // Draw viewport center crosshair
    ctx.fillStyle = '#FFFFFF';
    const centerX = (viewRect.x + viewRect.width / 2) * scaleX;
    const centerY = (viewRect.y + viewRect.height / 2) * scaleY;
    ctx.fillRect(centerX - 1, centerY - 4, 2, 8);
    ctx.fillRect(centerX - 4, centerY - 1, 8, 2);
  }, [camera, npcPositions, minimapWidth, minimapHeight, scaleX, scaleY, worldWidth, worldHeight]);

  // Handle click navigation
  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (!canvas || !onNavigate) return;

      const rect = canvas.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const clickY = e.clientY - rect.top;

      // Convert to world coordinates
      const worldX = clickX / scaleX;
      const worldY = clickY / scaleY;

      onNavigate(worldX, worldY);
    },
    [scaleX, scaleY, onNavigate]
  );

  return (
    <div
      className="absolute bottom-4 right-4 rounded-lg overflow-hidden shadow-lg border-2 border-slate-700/50 bg-slate-900/80 backdrop-blur-sm"
      style={{ width: minimapWidth + 8, height: minimapHeight + 8, padding: 4 }}
    >
      <canvas
        ref={canvasRef}
        width={minimapWidth}
        height={minimapHeight}
        onClick={handleClick}
        className="cursor-pointer rounded"
        style={{ width: minimapWidth, height: minimapHeight }}
      />
      {/* Minimap label */}
      <div className="absolute top-1 left-2 text-[9px] text-white/60 font-mono uppercase tracking-wider">
        Map
      </div>
    </div>
  );
}

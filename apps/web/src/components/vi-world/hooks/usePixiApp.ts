// usePixiApp - PixiJS Application lifecycle hook
// Manages PixiJS app creation, mounting, and cleanup

import { useEffect, useRef, useState, useCallback } from 'react';
import * as PIXI from 'pixi.js';
import { UsePixiAppReturn } from '../types';

interface UsePixiAppOptions {
  width?: number;
  height?: number;
  backgroundColor?: number;
  antialias?: boolean;
  resolution?: number;
}

const DEFAULT_OPTIONS: UsePixiAppOptions = {
  width: 800,
  height: 608,
  backgroundColor: 0x87CEEB, // Sky blue
  antialias: false, // Pixel art looks better without antialiasing
  resolution: typeof window !== 'undefined' ? (window.devicePixelRatio || 1) : 1,
};

export function usePixiApp(options: UsePixiAppOptions = {}): UsePixiAppReturn {
  const containerRef = useRef<HTMLDivElement>(null);
  const appRef = useRef<PIXI.Application | null>(null);
  const [isReady, setIsReady] = useState(false);

  const config = { ...DEFAULT_OPTIONS, ...options };

  useEffect(() => {
    let mounted = true;

    const initApp = async () => {
      if (!containerRef.current || appRef.current) return;

      try {
        // Create PixiJS application
        const app = new PIXI.Application();

        await app.init({
          width: config.width,
          height: config.height,
          backgroundColor: config.backgroundColor,
          antialias: config.antialias,
          resolution: config.resolution,
          autoDensity: true,
        });

        if (!mounted) {
          app.destroy(true);
          return;
        }

        // Configure for pixel art rendering (PixiJS v8)
        // Set default scale mode for textures (pixel art - nearest neighbor)
        PIXI.TextureSource.defaultOptions.scaleMode = 'nearest';

        // Mount canvas to container
        containerRef.current.appendChild(app.canvas);

        // Store reference
        appRef.current = app;
        setIsReady(true);
      } catch {
        // PixiJS initialization failed - setIsReady remains false
      }
    };

    initApp();

    // Cleanup
    return () => {
      mounted = false;
      if (appRef.current) {
        appRef.current.destroy(true, { children: true });
        appRef.current = null;
      }
      setIsReady(false);
    };
  }, [config.width, config.height, config.backgroundColor]);

  // Handle window resize
  useEffect(() => {
    if (!appRef.current || !containerRef.current) return;

    const handleResize = () => {
      if (!containerRef.current || !appRef.current) return;

      const container = containerRef.current;
      const { clientWidth, clientHeight } = container;

      // Calculate scale to fit while maintaining aspect ratio
      const scaleX = clientWidth / (config.width || 800);
      const scaleY = clientHeight / (config.height || 608);
      const scale = Math.min(scaleX, scaleY, 1);

      // Center the canvas
      const canvas = appRef.current.canvas;
      canvas.style.width = `${(config.width || 800) * scale}px`;
      canvas.style.height = `${(config.height || 608) * scale}px`;
    };

    // Initial resize
    handleResize();

    // Add listener
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [isReady, config.width, config.height]);

  return {
    app: appRef.current,
    containerRef,
    isReady,
  };
}

// Helper hook for game loop
export function useGameLoop(
  app: PIXI.Application | null,
  callback: (delta: number) => void
): void {
  const callbackRef = useRef(callback);
  callbackRef.current = callback;

  useEffect(() => {
    if (!app) return;

    const ticker = (ticker: PIXI.Ticker) => {
      callbackRef.current(ticker.deltaTime);
    };

    app.ticker.add(ticker);

    return () => {
      // Check if app and ticker still exist before removing
      if (app?.ticker) {
        app.ticker.remove(ticker);
      }
    };
  }, [app]);
}

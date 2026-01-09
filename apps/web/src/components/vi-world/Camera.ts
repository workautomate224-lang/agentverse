// Camera - Viewport management for large worlds
// Handles panning, zooming, and following entities

import * as PIXI from 'pixi.js';
import { Position } from './types';

export interface CameraConfig {
  viewportWidth: number;
  viewportHeight: number;
  worldWidth: number;
  worldHeight: number;
  minZoom?: number;
  maxZoom?: number;
  initialPosition?: Position;
}

export interface CameraBounds {
  left: number;
  top: number;
  right: number;
  bottom: number;
}

export class Camera {
  private config: CameraConfig;
  private container: PIXI.Container;

  // Camera state
  private _x: number = 0;
  private _y: number = 0;
  private _zoom: number = 1;

  // Drag state
  private isDragging: boolean = false;
  private dragStartX: number = 0;
  private dragStartY: number = 0;
  private cameraDragStartX: number = 0;
  private cameraDragStartY: number = 0;

  // Smooth movement
  private targetX: number = 0;
  private targetY: number = 0;
  private smoothing: number = 0.1;

  // Following
  private followTarget: Position | null = null;
  private followDeadzone: number = 100;

  constructor(container: PIXI.Container, config: CameraConfig) {
    this.container = container;
    this.config = {
      minZoom: 0.5,
      maxZoom: 2,
      ...config,
    };

    // Set initial position (center of viewport on the world center by default)
    if (config.initialPosition) {
      this._x = config.initialPosition.x;
      this._y = config.initialPosition.y;
    } else {
      this._x = config.worldWidth / 2;
      this._y = config.worldHeight / 2;
    }
    this.targetX = this._x;
    this.targetY = this._y;

    this.updateContainerPosition();
  }

  // Getters
  get x(): number { return this._x; }
  get y(): number { return this._y; }
  get zoom(): number { return this._zoom; }

  get viewportWidth(): number { return this.config.viewportWidth; }
  get viewportHeight(): number { return this.config.viewportHeight; }
  get worldWidth(): number { return this.config.worldWidth; }
  get worldHeight(): number { return this.config.worldHeight; }

  // Get visible bounds in world coordinates
  getBounds(): CameraBounds {
    const halfWidth = (this.config.viewportWidth / 2) / this._zoom;
    const halfHeight = (this.config.viewportHeight / 2) / this._zoom;

    return {
      left: this._x - halfWidth,
      top: this._y - halfHeight,
      right: this._x + halfWidth,
      bottom: this._y + halfHeight,
    };
  }

  // Check if a position is visible
  isVisible(position: Position, padding: number = 50): boolean {
    const bounds = this.getBounds();
    return (
      position.x >= bounds.left - padding &&
      position.x <= bounds.right + padding &&
      position.y >= bounds.top - padding &&
      position.y <= bounds.bottom + padding
    );
  }

  // Move camera to position (instant)
  moveTo(x: number, y: number): void {
    this._x = this.clampX(x);
    this._y = this.clampY(y);
    this.targetX = this._x;
    this.targetY = this._y;
    this.updateContainerPosition();
  }

  // Pan camera to position (smooth)
  panTo(x: number, y: number, instant: boolean = false): void {
    this.targetX = this.clampX(x);
    this.targetY = this.clampY(y);

    if (instant) {
      this._x = this.targetX;
      this._y = this.targetY;
      this.updateContainerPosition();
    }
  }

  // Pan by offset
  panBy(dx: number, dy: number): void {
    this.panTo(this._x + dx, this._y + dy, true);
  }

  // Set zoom level
  setZoom(zoom: number, centerX?: number, centerY?: number): void {
    const oldZoom = this._zoom;
    this._zoom = Math.max(this.config.minZoom!, Math.min(this.config.maxZoom!, zoom));

    // Zoom towards center point if provided
    if (centerX !== undefined && centerY !== undefined) {
      const zoomRatio = this._zoom / oldZoom;
      const dx = centerX - this._x;
      const dy = centerY - this._y;
      this._x = centerX - dx * zoomRatio;
      this._y = centerY - dy * zoomRatio;
    }

    this._x = this.clampX(this._x);
    this._y = this.clampY(this._y);
    this.targetX = this._x;
    this.targetY = this._y;

    this.updateContainerPosition();
  }

  // Zoom by factor
  zoomBy(factor: number, centerX?: number, centerY?: number): void {
    this.setZoom(this._zoom * factor, centerX, centerY);
  }

  // Follow a target position
  follow(position: Position | null): void {
    this.followTarget = position;
  }

  // Drag handling
  startDrag(screenX: number, screenY: number): void {
    this.isDragging = true;
    this.dragStartX = screenX;
    this.dragStartY = screenY;
    this.cameraDragStartX = this._x;
    this.cameraDragStartY = this._y;
    this.followTarget = null; // Stop following when user drags
  }

  updateDrag(screenX: number, screenY: number): void {
    if (!this.isDragging) return;

    const dx = (this.dragStartX - screenX) / this._zoom;
    const dy = (this.dragStartY - screenY) / this._zoom;

    this._x = this.clampX(this.cameraDragStartX + dx);
    this._y = this.clampY(this.cameraDragStartY + dy);
    this.targetX = this._x;
    this.targetY = this._y;

    this.updateContainerPosition();
  }

  endDrag(): void {
    this.isDragging = false;
  }

  // Handle mouse wheel zoom
  handleWheel(deltaY: number, screenX: number, screenY: number): void {
    const zoomFactor = deltaY > 0 ? 0.9 : 1.1;

    // Convert screen position to world position
    const worldX = this._x + (screenX - this.config.viewportWidth / 2) / this._zoom;
    const worldY = this._y + (screenY - this.config.viewportHeight / 2) / this._zoom;

    this.zoomBy(zoomFactor, worldX, worldY);
  }

  // Update camera each frame
  update(delta: number): void {
    // Handle following
    if (this.followTarget) {
      const dx = this.followTarget.x - this._x;
      const dy = this.followTarget.y - this._y;
      const distance = Math.sqrt(dx * dx + dy * dy);

      if (distance > this.followDeadzone) {
        this.targetX = this.followTarget.x;
        this.targetY = this.followTarget.y;
      }
    }

    // Smooth movement
    if (!this.isDragging) {
      const dx = this.targetX - this._x;
      const dy = this.targetY - this._y;

      if (Math.abs(dx) > 0.1 || Math.abs(dy) > 0.1) {
        this._x += dx * this.smoothing;
        this._y += dy * this.smoothing;
        this.updateContainerPosition();
      }
    }
  }

  // Convert screen coordinates to world coordinates
  screenToWorld(screenX: number, screenY: number): Position {
    return {
      x: this._x + (screenX - this.config.viewportWidth / 2) / this._zoom,
      y: this._y + (screenY - this.config.viewportHeight / 2) / this._zoom,
    };
  }

  // Convert world coordinates to screen coordinates
  worldToScreen(worldX: number, worldY: number): Position {
    return {
      x: (worldX - this._x) * this._zoom + this.config.viewportWidth / 2,
      y: (worldY - this._y) * this._zoom + this.config.viewportHeight / 2,
    };
  }

  // Clamp camera position within world bounds
  private clampX(x: number): number {
    const halfWidth = (this.config.viewportWidth / 2) / this._zoom;
    const minX = halfWidth;
    const maxX = this.config.worldWidth - halfWidth;
    return Math.max(minX, Math.min(maxX, x));
  }

  private clampY(y: number): number {
    const halfHeight = (this.config.viewportHeight / 2) / this._zoom;
    const minY = halfHeight;
    const maxY = this.config.worldHeight - halfHeight;
    return Math.max(minY, Math.min(maxY, y));
  }

  // Update the container position based on camera state
  private updateContainerPosition(): void {
    this.container.scale.set(this._zoom);
    this.container.x = this.config.viewportWidth / 2 - this._x * this._zoom;
    this.container.y = this.config.viewportHeight / 2 - this._y * this._zoom;
  }

  // Get minimap data for rendering
  getMinimapData(): {
    viewportRect: { x: number; y: number; width: number; height: number };
    worldSize: { width: number; height: number };
  } {
    const bounds = this.getBounds();
    return {
      viewportRect: {
        x: bounds.left,
        y: bounds.top,
        width: bounds.right - bounds.left,
        height: bounds.bottom - bounds.top,
      },
      worldSize: {
        width: this.config.worldWidth,
        height: this.config.worldHeight,
      },
    };
  }
}

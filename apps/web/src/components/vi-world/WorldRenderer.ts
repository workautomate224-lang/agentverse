// WorldRenderer - Tile-based world rendering
// Manages world tilemap and renders it to PixiJS

import * as PIXI from 'pixi.js';
import { WorldData, Position } from './types';
import { generateTileTextures, getTileTextureKey } from './utils/worldGenerator';
import { TILE_COLORS } from './utils/colors';

export class WorldRenderer {
  public container: PIXI.Container;
  private tileContainer: PIXI.Container;
  private roofContainer: PIXI.Container;
  private worldData: WorldData;
  private tileTextures: Map<string, PIXI.Texture>;
  private tiles: PIXI.Sprite[][] = [];

  constructor(worldData: WorldData) {
    this.worldData = worldData;

    // Create containers
    this.container = new PIXI.Container();
    this.tileContainer = new PIXI.Container();
    this.roofContainer = new PIXI.Container();

    // Set z-index for proper layering
    this.tileContainer.zIndex = 0;
    this.roofContainer.zIndex = 50; // Roofs above NPCs

    this.container.addChild(this.tileContainer);
    this.container.addChild(this.roofContainer);

    this.container.sortableChildren = true;

    // Generate tile textures
    this.tileTextures = generateTileTextures();

    // Render the world
    this.renderWorld();
  }

  private renderWorld(): void {
    const { tiles, config, buildingPositions } = this.worldData;
    const { tileSize } = config;

    // Create tile sprites
    for (let y = 0; y < tiles.length; y++) {
      this.tiles[y] = [];
      for (let x = 0; x < tiles[y].length; x++) {
        const tile = tiles[y][x];
        const textureKey = getTileTextureKey(tile, x, y);
        const texture = this.tileTextures.get(textureKey);

        if (texture) {
          const sprite = new PIXI.Sprite(texture);
          sprite.x = x * tileSize;
          sprite.y = y * tileSize;
          sprite.width = tileSize;
          sprite.height = tileSize;

          this.tileContainer.addChild(sprite);
          this.tiles[y][x] = sprite;
        }
      }
    }

    // Add roofs over buildings
    for (const building of buildingPositions) {
      this.addBuildingRoof(building, tileSize);
    }
  }

  private addBuildingRoof(position: Position, tileSize: number): void {
    const roofTexture = this.tileTextures.get('roof');
    if (!roofTexture) return;

    // Building is 5x4 tiles, roof covers top
    const roofWidth = 5;
    const roofHeight = 2;

    for (let dy = 0; dy < roofHeight; dy++) {
      for (let dx = 0; dx < roofWidth; dx++) {
        const sprite = new PIXI.Sprite(roofTexture);
        sprite.x = (position.x + dx) * tileSize;
        sprite.y = (position.y + dy - 1) * tileSize; // Roof sits above building
        sprite.width = tileSize;
        sprite.height = tileSize;

        this.roofContainer.addChild(sprite);
      }
    }

    // Add roof peak (triangular top)
    this.addRoofPeak(position, tileSize, roofWidth);
  }

  private addRoofPeak(position: Position, tileSize: number, roofWidth: number): void {
    const peakGraphics = new PIXI.Graphics();

    const baseX = position.x * tileSize;
    const baseY = (position.y - 2) * tileSize;
    const width = roofWidth * tileSize;

    // Draw triangular peak
    peakGraphics.moveTo(baseX, baseY + tileSize);
    peakGraphics.lineTo(baseX + width / 2, baseY);
    peakGraphics.lineTo(baseX + width, baseY + tileSize);
    peakGraphics.closePath();
    peakGraphics.fill({ color: Number(TILE_COLORS.roof.replace('#', '0x')) });

    // Add outline
    peakGraphics.moveTo(baseX, baseY + tileSize);
    peakGraphics.lineTo(baseX + width / 2, baseY);
    peakGraphics.lineTo(baseX + width, baseY + tileSize);
    peakGraphics.stroke({ color: 0x1A1A2E, width: 1 });

    this.roofContainer.addChild(peakGraphics);
  }

  // Get world dimensions in pixels
  public getWorldSize(): { width: number; height: number } {
    const { config } = this.worldData;
    return {
      width: config.width * config.tileSize,
      height: config.height * config.tileSize,
    };
  }

  // Check if position is within world bounds
  public isInBounds(x: number, y: number): boolean {
    const size = this.getWorldSize();
    return x >= 0 && x < size.width && y >= 0 && y < size.height;
  }

  // Get tile at pixel position
  public getTileAt(x: number, y: number) {
    const { config, tiles } = this.worldData;
    const tileX = Math.floor(x / config.tileSize);
    const tileY = Math.floor(y / config.tileSize);

    if (tileX >= 0 && tileX < config.width && tileY >= 0 && tileY < config.height) {
      return tiles[tileY][tileX];
    }
    return null;
  }

  // Update tile at position (for dynamic world changes)
  public updateTile(x: number, y: number): void {
    const { config, tiles } = this.worldData;
    const tileX = Math.floor(x / config.tileSize);
    const tileY = Math.floor(y / config.tileSize);

    if (tileX >= 0 && tileX < config.width && tileY >= 0 && tileY < config.height) {
      const tile = tiles[tileY][tileX];
      const textureKey = getTileTextureKey(tile, tileX, tileY);
      const texture = this.tileTextures.get(textureKey);

      if (texture && this.tiles[tileY]?.[tileX]) {
        this.tiles[tileY][tileX].texture = texture;
      }
    }
  }

  // Cleanup resources
  public destroy(): void {
    // Destroy textures
    for (const texture of this.tileTextures.values()) {
      texture.destroy(true);
    }
    this.tileTextures.clear();

    // Destroy containers
    this.container.destroy({ children: true });
  }
}

// Create decorative elements (optional)
export function createDecorations(worldData: WorldData): PIXI.Container {
  const container = new PIXI.Container();
  container.zIndex = 10;

  // Add some decorative elements like flowers, rocks, etc.
  const decorations = generateDecorationPositions(worldData);

  for (const deco of decorations) {
    const graphics = new PIXI.Graphics();

    // Simple flower
    if (deco.type === 'flower') {
      // Stem
      graphics.rect(deco.x + 2, deco.y + 4, 2, 6);
      graphics.fill({ color: 0x228B22 });

      // Petals
      graphics.circle(deco.x + 3, deco.y + 3, 3);
      graphics.fill({ color: deco.color });

      // Center
      graphics.circle(deco.x + 3, deco.y + 3, 1);
      graphics.fill({ color: 0xFFFF00 });
    }

    // Simple rock
    if (deco.type === 'rock') {
      graphics.ellipse(deco.x + 4, deco.y + 4, 4, 3);
      graphics.fill({ color: 0x808080 });
    }

    container.addChild(graphics);
  }

  return container;
}

interface DecorationData {
  x: number;
  y: number;
  type: 'flower' | 'rock';
  color: number;
}

function generateDecorationPositions(worldData: WorldData): DecorationData[] {
  const decorations: DecorationData[] = [];
  const { tiles, config } = worldData;
  const flowerColors = [0xFF69B4, 0xFF6347, 0x9370DB, 0xFFD700, 0x87CEEB];

  // Add decorations on grass tiles
  for (let y = 0; y < tiles.length; y++) {
    for (let x = 0; x < tiles[y].length; x++) {
      if (tiles[y][x].type === 'grass' && Math.random() < 0.05) {
        const pixelX = x * config.tileSize + Math.random() * 8;
        const pixelY = y * config.tileSize + Math.random() * 8;

        decorations.push({
          x: pixelX,
          y: pixelY,
          type: Math.random() < 0.7 ? 'flower' : 'rock',
          color: flowerColors[Math.floor(Math.random() * flowerColors.length)],
        });
      }
    }
  }

  return decorations;
}

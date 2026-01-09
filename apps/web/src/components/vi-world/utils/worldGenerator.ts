// World Generator - Creates tile-based procedural worlds
// Generates a town layout with buildings, paths, grass, trees, and water features

import * as PIXI from 'pixi.js';
import { WorldConfig, WorldData, Tile, TileType, Position } from '../types';
import { TILE_COLORS, darkenColor, lightenColor } from './colors';

// Default world configuration - 10x larger for expansive world
const DEFAULT_CONFIG: WorldConfig = {
  width: 150,    // 150 tiles wide (was 50)
  height: 114,   // 114 tiles tall (was 38)
  tileSize: 16,
  seed: Date.now(),
};

// Seeded random number generator for consistent worlds
class SeededRandom {
  private seed: number;

  constructor(seed: number) {
    this.seed = seed;
  }

  next(): number {
    this.seed = (this.seed * 1103515245 + 12345) & 0x7fffffff;
    return this.seed / 0x7fffffff;
  }

  nextInt(min: number, max: number): number {
    return Math.floor(this.next() * (max - min + 1)) + min;
  }

  nextFloat(min: number, max: number): number {
    return this.next() * (max - min) + min;
  }

  pick<T>(array: T[]): T {
    return array[Math.floor(this.next() * array.length)];
  }

  chance(probability: number): boolean {
    return this.next() < probability;
  }
}

// Generate a tile texture
function generateTileTexture(type: TileType, variant: number = 0): PIXI.Texture {
  const canvas = document.createElement('canvas');
  const size = 16;
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d')!;

  switch (type) {
    case 'grass':
      drawGrassTile(ctx, size, variant);
      break;
    case 'path':
      drawPathTile(ctx, size);
      break;
    case 'building':
      drawBuildingTile(ctx, size, variant);
      break;
    case 'tree':
      drawTreeTile(ctx, size, variant);
      break;
    case 'water':
      drawWaterTile(ctx, size, variant);
      break;
    case 'door':
      drawDoorTile(ctx, size);
      break;
  }

  return PIXI.Texture.from(canvas);
}

function drawGrassTile(ctx: CanvasRenderingContext2D, size: number, variant: number): void {
  const grassColors = TILE_COLORS.grass;
  ctx.fillStyle = grassColors[variant % grassColors.length];
  ctx.fillRect(0, 0, size, size);

  // Add texture variation
  ctx.fillStyle = darkenColor(grassColors[variant % grassColors.length], 0.08);
  for (let i = 0; i < 4; i++) {
    const x = (variant * 3 + i * 4) % size;
    const y = (variant * 7 + i * 3) % size;
    ctx.fillRect(x, y, 1, 1);
  }

  // Add grass blades
  ctx.fillStyle = lightenColor(grassColors[variant % grassColors.length], 0.12);
  for (let i = 0; i < 2; i++) {
    const x = (variant * 5 + i * 7) % (size - 2);
    const y = (variant * 11 + i * 5) % (size - 3);
    ctx.fillRect(x, y, 1, 2);
  }
}

function drawPathTile(ctx: CanvasRenderingContext2D, size: number): void {
  ctx.fillStyle = TILE_COLORS.path;
  ctx.fillRect(0, 0, size, size);

  // Subtle texture
  ctx.fillStyle = darkenColor(TILE_COLORS.path, 0.08);
  ctx.fillRect(2, 3, 2, 2);
  ctx.fillRect(10, 8, 2, 2);
  ctx.fillRect(6, 12, 2, 2);

  ctx.fillStyle = lightenColor(TILE_COLORS.path, 0.08);
  ctx.fillRect(8, 2, 2, 2);
  ctx.fillRect(3, 10, 2, 2);
}

function drawBuildingTile(ctx: CanvasRenderingContext2D, size: number, variant: number): void {
  ctx.fillStyle = TILE_COLORS.building;
  ctx.fillRect(0, 0, size, size);

  // Brick pattern
  ctx.fillStyle = darkenColor(TILE_COLORS.building, 0.12);
  for (let y = 0; y < size; y += 4) {
    const offset = (y / 4) % 2 === 0 ? 0 : 4;
    for (let x = offset; x < size; x += 8) {
      ctx.fillRect(x, y, 7, 3);
    }
  }

  // Mortar lines
  ctx.fillStyle = lightenColor(TILE_COLORS.building, 0.15);
  for (let y = 3; y < size; y += 4) {
    ctx.fillRect(0, y, size, 1);
  }
}

function drawTreeTile(ctx: CanvasRenderingContext2D, size: number, variant: number): void {
  const grassColors = TILE_COLORS.grass;
  ctx.fillStyle = grassColors[0];
  ctx.fillRect(0, 0, size, size);

  // Trunk
  ctx.fillStyle = '#4A3728';
  ctx.fillRect(6, 10, 4, 6);

  // Canopy
  const treeColors = TILE_COLORS.tree;
  ctx.fillStyle = treeColors[variant % treeColors.length];
  ctx.fillRect(4, 2, 8, 3);
  ctx.fillRect(2, 5, 12, 3);
  ctx.fillRect(3, 8, 10, 2);
}

function drawWaterTile(ctx: CanvasRenderingContext2D, size: number, variant: number): void {
  const waterColors = TILE_COLORS.water;
  ctx.fillStyle = waterColors[variant % waterColors.length];
  ctx.fillRect(0, 0, size, size);

  // Wave pattern
  ctx.fillStyle = lightenColor(waterColors[variant % waterColors.length], 0.15);
  const waveOffset = (variant * 3) % size;
  ctx.fillRect(waveOffset, 4, 4, 1);
  ctx.fillRect((waveOffset + 8) % size, 10, 4, 1);
}

function drawDoorTile(ctx: CanvasRenderingContext2D, size: number): void {
  ctx.fillStyle = TILE_COLORS.building;
  ctx.fillRect(0, 0, size, size);

  // Door
  ctx.fillStyle = TILE_COLORS.door;
  ctx.fillRect(2, 2, 12, 14);

  // Frame
  ctx.fillStyle = darkenColor(TILE_COLORS.door, 0.3);
  ctx.fillRect(2, 2, 12, 2);
  ctx.fillRect(2, 2, 2, 14);
  ctx.fillRect(12, 2, 2, 14);

  // Handle
  ctx.fillStyle = '#FFD700';
  ctx.fillRect(10, 9, 2, 2);
}

// Generate roof tile
function generateRoofTexture(): PIXI.Texture {
  const canvas = document.createElement('canvas');
  const size = 16;
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d')!;

  ctx.fillStyle = TILE_COLORS.roof;
  ctx.fillRect(0, 0, size, size);

  ctx.fillStyle = darkenColor(TILE_COLORS.roof, 0.2);
  for (let y = 0; y < size; y += 4) {
    const offset = (y / 4) % 2 === 0 ? 0 : 4;
    for (let x = offset; x < size; x += 8) {
      ctx.fillRect(x + 1, y + 1, 6, 2);
    }
  }

  return PIXI.Texture.from(canvas);
}

// Main world generation function - enhanced for larger worlds
export function generateWorld(config: Partial<WorldConfig> = {}): WorldData {
  const worldConfig: WorldConfig = { ...DEFAULT_CONFIG, ...config };
  const { width, height, seed } = worldConfig;
  const random = new SeededRandom(seed || Date.now());

  // Initialize tiles with grass
  const tiles: Tile[][] = [];
  for (let y = 0; y < height; y++) {
    tiles[y] = [];
    for (let x = 0; x < width; x++) {
      tiles[y][x] = {
        type: 'grass',
        walkable: true,
      };
    }
  }

  const buildingPositions: Position[] = [];
  const spawnPoints: Position[] = [];

  // Create main road network (grid pattern)
  const roadSpacing = 25; // Distance between major roads
  const roadWidth = 2;

  // Horizontal roads
  for (let roadY = roadSpacing; roadY < height - roadSpacing; roadY += roadSpacing) {
    for (let x = 0; x < width; x++) {
      for (let dy = 0; dy < roadWidth; dy++) {
        if (roadY + dy < height) {
          tiles[roadY + dy][x] = { type: 'path', walkable: true };
        }
      }
    }
  }

  // Vertical roads
  for (let roadX = roadSpacing; roadX < width - roadSpacing; roadX += roadSpacing) {
    for (let y = 0; y < height; y++) {
      for (let dx = 0; dx < roadWidth; dx++) {
        if (roadX + dx < width) {
          tiles[y][roadX + dx] = { type: 'path', walkable: true };
        }
      }
    }
  }

  // Add secondary winding paths
  const numSecondaryPaths = random.nextInt(8, 15);
  for (let i = 0; i < numSecondaryPaths; i++) {
    let pathX = random.nextInt(10, width - 10);
    let pathY = random.nextInt(10, height - 10);
    const pathLength = random.nextInt(15, 40);
    let direction = random.nextInt(0, 3); // 0: right, 1: down, 2: left, 3: up

    for (let step = 0; step < pathLength; step++) {
      if (pathX >= 0 && pathX < width && pathY >= 0 && pathY < height) {
        if (tiles[pathY][pathX].type === 'grass') {
          tiles[pathY][pathX] = { type: 'path', walkable: true };
        }
      }

      // Move in current direction with occasional turns
      if (random.chance(0.2)) {
        direction = (direction + random.pick([-1, 1]) + 4) % 4;
      }

      switch (direction) {
        case 0: pathX++; break;
        case 1: pathY++; break;
        case 2: pathX--; break;
        case 3: pathY--; break;
      }
    }
  }

  // Generate buildings in districts
  const buildingConfigs = [
    { minX: 5, maxX: 20, minY: 5, maxY: 20, count: 4 },
    { minX: 30, maxX: 45, minY: 5, maxY: 20, count: 4 },
    { minX: 55, maxX: 70, minY: 5, maxY: 20, count: 3 },
    { minX: 5, maxX: 20, minY: 30, maxY: 45, count: 3 },
    { minX: 30, maxX: 45, minY: 30, maxY: 45, count: 4 },
    { minX: 55, maxX: 70, minY: 30, maxY: 45, count: 3 },
    { minX: 80, maxX: 95, minY: 10, maxY: 35, count: 3 },
    { minX: 100, maxX: 120, minY: 15, maxY: 40, count: 4 },
    { minX: 5, maxX: 25, minY: 55, maxY: 80, count: 3 },
    { minX: 35, maxX: 55, minY: 55, maxY: 80, count: 4 },
    { minX: 65, maxX: 85, minY: 55, maxY: 80, count: 3 },
    { minX: 95, maxX: 115, minY: 55, maxY: 80, count: 3 },
    { minX: 125, maxX: 140, minY: 20, maxY: 50, count: 2 },
    { minX: 125, maxX: 140, minY: 60, maxY: 90, count: 2 },
  ];

  for (const district of buildingConfigs) {
    if (district.maxX >= width || district.maxY >= height) continue;

    for (let b = 0; b < district.count; b++) {
      const attempts = 10;
      for (let attempt = 0; attempt < attempts; attempt++) {
        const spotX = random.nextInt(district.minX, district.maxX - 6);
        const spotY = random.nextInt(district.minY, district.maxY - 5);

        if (spotX + 5 >= width || spotY + 4 >= height) continue;

        // Check if area is clear
        let canPlace = true;
        for (let dy = -1; dy <= 5 && canPlace; dy++) {
          for (let dx = -1; dx <= 6 && canPlace; dx++) {
            const ty = spotY + dy;
            const tx = spotX + dx;
            if (ty >= 0 && ty < height && tx >= 0 && tx < width) {
              if (tiles[ty][tx].type !== 'grass') {
                canPlace = false;
              }
            }
          }
        }

        if (canPlace) {
          // Place building (5x4 tiles)
          for (let dy = 0; dy < 4; dy++) {
            for (let dx = 0; dx < 5; dx++) {
              const ty = spotY + dy;
              const tx = spotX + dx;
              if (ty < height && tx < width) {
                tiles[ty][tx] = { type: 'building', walkable: false };
              }
            }
          }

          // Add door
          const doorX = spotX + 2;
          const doorY = spotY + 3;
          if (doorY < height && doorX < width) {
            tiles[doorY][doorX] = { type: 'door', walkable: false };
          }

          // Path from door (downward)
          for (let py = doorY + 1; py < height && py < doorY + 8; py++) {
            if (tiles[py][doorX].type === 'grass') {
              tiles[py][doorX] = { type: 'path', walkable: true };
            } else {
              break;
            }
          }

          buildingPositions.push({ x: spotX, y: spotY });
          break;
        }
      }
    }
  }

  // Add trees in clusters
  const numTreeClusters = random.nextInt(20, 35);
  for (let c = 0; c < numTreeClusters; c++) {
    const clusterX = random.nextInt(5, width - 10);
    const clusterY = random.nextInt(5, height - 10);
    const clusterSize = random.nextInt(3, 8);

    for (let t = 0; t < clusterSize; t++) {
      const tx = clusterX + random.nextInt(-4, 4);
      const ty = clusterY + random.nextInt(-4, 4);

      if (tx >= 2 && tx < width - 2 && ty >= 2 && ty < height - 2) {
        if (tiles[ty][tx].type === 'grass') {
          tiles[ty][tx] = { type: 'tree', walkable: false };
        }
      }
    }
  }

  // Add water features (ponds and a small lake)
  const numPonds = random.nextInt(4, 8);
  for (let p = 0; p < numPonds; p++) {
    const pondX = random.nextInt(10, width - 15);
    const pondY = random.nextInt(10, height - 15);
    const pondWidth = random.nextInt(4, 10);
    const pondHeight = random.nextInt(3, 7);

    // Check if area is mostly grass
    let canPlace = true;
    for (let dy = -1; dy <= pondHeight && canPlace; dy++) {
      for (let dx = -1; dx <= pondWidth && canPlace; dx++) {
        const ty = pondY + dy;
        const tx = pondX + dx;
        if (ty >= 0 && ty < height && tx >= 0 && tx < width) {
          if (tiles[ty][tx].type !== 'grass') {
            canPlace = false;
          }
        }
      }
    }

    if (canPlace) {
      // Create organic pond shape
      for (let dy = 0; dy < pondHeight; dy++) {
        for (let dx = 0; dx < pondWidth; dx++) {
          const ty = pondY + dy;
          const tx = pondX + dx;

          // Skip corners for organic shape
          const isCorner = (dx === 0 || dx === pondWidth - 1) &&
                          (dy === 0 || dy === pondHeight - 1);
          if (isCorner && random.chance(0.5)) continue;

          if (ty < height && tx < width && tiles[ty][tx].type === 'grass') {
            tiles[ty][tx] = { type: 'water', walkable: false };
          }
        }
      }
    }
  }

  // Generate spawn points along paths
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      if (tiles[y][x].type === 'path' && random.chance(0.02)) {
        spawnPoints.push({ x, y });
      }
    }
  }

  // Ensure minimum spawn points
  if (spawnPoints.length < 20) {
    for (let y = 0; y < height; y += 10) {
      for (let x = 0; x < width; x += 10) {
        if (tiles[y]?.[x]?.walkable) {
          spawnPoints.push({ x, y });
        }
      }
    }
  }

  return {
    tiles,
    spawnPoints,
    buildingPositions,
    config: worldConfig,
  };
}

// Generate all tile textures
export function generateTileTextures(): Map<string, PIXI.Texture> {
  const textures = new Map<string, PIXI.Texture>();

  for (let i = 0; i < 3; i++) {
    textures.set(`grass_${i}`, generateTileTexture('grass', i));
  }

  textures.set('path', generateTileTexture('path'));

  for (let i = 0; i < 2; i++) {
    textures.set(`building_${i}`, generateTileTexture('building', i));
  }

  for (let i = 0; i < 3; i++) {
    textures.set(`tree_${i}`, generateTileTexture('tree', i));
  }

  for (let i = 0; i < 3; i++) {
    textures.set(`water_${i}`, generateTileTexture('water', i));
  }

  textures.set('door', generateTileTexture('door'));
  textures.set('roof', generateRoofTexture());

  return textures;
}

// Get texture key for a tile
export function getTileTextureKey(tile: Tile, x: number, y: number): string {
  const variant = ((x * 7 + y * 13) % 3);

  switch (tile.type) {
    case 'grass':
      return `grass_${variant}`;
    case 'path':
      return 'path';
    case 'building':
      return `building_${variant % 2}`;
    case 'tree':
      return `tree_${variant}`;
    case 'water':
      return `water_${variant}`;
    case 'door':
      return 'door';
    default:
      return 'grass_0';
  }
}

// Check if a position is walkable
export function isWalkable(worldData: WorldData, x: number, y: number): boolean {
  const tileX = Math.floor(x / worldData.config.tileSize);
  const tileY = Math.floor(y / worldData.config.tileSize);

  if (tileX < 0 || tileX >= worldData.config.width ||
      tileY < 0 || tileY >= worldData.config.height) {
    return false;
  }

  return worldData.tiles[tileY]?.[tileX]?.walkable ?? false;
}

// Get a random spawn point
export function getRandomSpawnPoint(worldData: WorldData): Position {
  const idx = Math.floor(Math.random() * worldData.spawnPoints.length);
  const spawn = worldData.spawnPoints[idx];
  return {
    x: spawn.x * worldData.config.tileSize + worldData.config.tileSize / 2,
    y: spawn.y * worldData.config.tileSize + worldData.config.tileSize / 2,
  };
}

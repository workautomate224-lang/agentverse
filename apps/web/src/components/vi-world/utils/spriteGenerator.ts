// Procedural Pixel Art Sprite Generator v2
// Creates cute chibi-style character sprites with better proportions and shading

import * as PIXI from 'pixi.js';
import { Gender, Direction, NPCConfig } from '../types';
import { darkenColor, lightenColor } from './colors';

// Improved sprite dimensions - larger for more detail
const SPRITE_WIDTH = 24;
const SPRITE_HEIGHT = 32;
const SCALE = 2; // Scale up for crisp display

// Animation frames per direction
const FRAMES_PER_DIRECTION = 4;

// Color codes for sprite template:
// 0 = transparent
// 1 = hair main
// 2 = hair highlight
// 3 = hair shadow
// 4 = skin main
// 5 = skin highlight
// 6 = skin shadow
// 7 = eyes
// 8 = eye highlight
// 9 = mouth/blush
// 10 = shirt main
// 11 = shirt highlight
// 12 = shirt shadow
// 13 = pants main
// 14 = pants shadow
// 15 = shoes
// 16 = outline

// Improved chibi-style body template with shading
const BODY_TEMPLATE_MALE: number[][] = [
  // Row 0-1: Hair top
  [0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0],
  [0,0,0,0,0,0,1,1,2,2,1,1,1,1,1,1,1,1,0,0,0,0,0,0],
  // Row 2-3: Hair upper
  [0,0,0,0,0,1,1,2,2,2,1,1,1,1,1,1,1,1,1,0,0,0,0,0],
  [0,0,0,0,1,1,1,2,1,1,1,1,1,1,1,1,1,3,1,1,0,0,0,0],
  // Row 4-5: Hair/forehead
  [0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,3,3,1,0,0,0,0],
  [0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,3,3,3,1,0,0,0,0],
  // Row 6-7: Face upper - eyes
  [0,0,0,0,1,4,4,4,4,4,4,4,4,4,4,4,4,4,4,1,0,0,0,0],
  [0,0,0,0,0,4,5,4,4,4,4,4,4,4,4,4,4,4,4,0,0,0,0,0],
  // Row 8-9: Eyes row
  [0,0,0,0,0,4,5,4,7,7,4,4,4,4,7,7,4,4,6,0,0,0,0,0],
  [0,0,0,0,0,4,4,4,7,8,4,4,4,4,7,8,4,4,6,0,0,0,0,0],
  // Row 10-11: Cheeks and nose
  [0,0,0,0,0,4,4,9,4,4,4,4,4,4,4,4,9,4,6,0,0,0,0,0],
  [0,0,0,0,0,4,4,4,4,4,4,4,4,4,4,4,4,4,6,0,0,0,0,0],
  // Row 12-13: Mouth
  [0,0,0,0,0,4,4,4,4,4,4,9,9,4,4,4,4,4,6,0,0,0,0,0],
  [0,0,0,0,0,0,4,4,4,4,4,4,4,4,4,4,4,0,0,0,0,0,0,0],
  // Row 14: Neck
  [0,0,0,0,0,0,0,0,4,4,4,4,4,4,4,4,0,0,0,0,0,0,0,0],
  // Row 15-18: Torso
  [0,0,0,0,0,10,10,10,10,10,10,10,10,10,10,10,10,10,10,0,0,0,0,0],
  [0,0,0,0,10,10,11,11,10,10,10,10,10,10,10,10,10,12,10,10,0,0,0,0],
  [0,0,0,0,10,10,11,10,10,10,10,10,10,10,10,10,10,12,10,10,0,0,0,0],
  [0,0,0,0,10,10,10,10,10,10,10,10,10,10,10,10,10,12,10,10,0,0,0,0],
  [0,0,0,0,0,10,10,10,10,10,10,10,10,10,10,10,10,10,0,0,0,0,0,0],
  // Row 20-21: Belt/waist
  [0,0,0,0,0,0,13,13,13,13,13,13,13,13,13,13,13,0,0,0,0,0,0,0],
  [0,0,0,0,0,0,13,13,13,13,13,13,13,13,13,13,13,0,0,0,0,0,0,0],
  // Row 22-25: Legs
  [0,0,0,0,0,0,13,13,13,13,0,0,0,0,13,13,13,13,0,0,0,0,0,0],
  [0,0,0,0,0,0,13,13,13,14,0,0,0,0,14,13,13,13,0,0,0,0,0,0],
  [0,0,0,0,0,0,13,13,13,14,0,0,0,0,14,13,13,13,0,0,0,0,0,0],
  [0,0,0,0,0,0,13,13,13,14,0,0,0,0,14,13,13,13,0,0,0,0,0,0],
  // Row 26-27: Lower legs
  [0,0,0,0,0,0,13,13,14,14,0,0,0,0,14,14,13,13,0,0,0,0,0,0],
  [0,0,0,0,0,0,13,13,14,14,0,0,0,0,14,14,13,13,0,0,0,0,0,0],
  // Row 28-29: Ankles
  [0,0,0,0,0,0,13,13,14,14,0,0,0,0,14,14,13,13,0,0,0,0,0,0],
  [0,0,0,0,0,0,13,14,14,14,0,0,0,0,14,14,14,13,0,0,0,0,0,0],
  // Row 30-31: Feet
  [0,0,0,0,0,15,15,15,15,15,0,0,0,0,15,15,15,15,15,0,0,0,0,0],
  [0,0,0,0,0,15,15,15,15,15,0,0,0,0,15,15,15,15,15,0,0,0,0,0],
];

const BODY_TEMPLATE_FEMALE: number[][] = [
  // Row 0-1: Hair top (longer/more volume)
  [0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0],
  [0,0,0,0,0,1,1,2,2,2,1,1,1,1,1,1,1,1,1,0,0,0,0,0],
  // Row 2-3: Hair upper
  [0,0,0,0,1,1,2,2,2,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0],
  [0,0,0,1,1,1,2,1,1,1,1,1,1,1,1,1,1,1,3,1,1,0,0,0],
  // Row 4-5: Hair sides
  [0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,3,3,1,1,0,0,0],
  [0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,3,3,3,1,1,0,0,0],
  // Row 6-7: Face upper
  [0,0,0,1,1,4,4,4,4,4,4,4,4,4,4,4,4,4,4,1,1,0,0,0],
  [0,0,0,1,0,4,5,4,4,4,4,4,4,4,4,4,4,4,4,0,1,0,0,0],
  // Row 8-9: Eyes row
  [0,0,0,1,0,4,5,4,7,7,4,4,4,4,7,7,4,4,6,0,1,0,0,0],
  [0,0,0,1,0,4,4,4,7,8,4,4,4,4,7,8,4,4,6,0,1,0,0,0],
  // Row 10-11: Cheeks (more blush for female)
  [0,0,0,1,0,4,4,9,4,4,4,4,4,4,4,4,9,4,6,0,1,0,0,0],
  [0,0,0,1,0,4,4,4,4,4,4,4,4,4,4,4,4,4,6,0,1,0,0,0],
  // Row 12-13: Mouth
  [0,0,0,1,0,4,4,4,4,4,4,9,9,4,4,4,4,4,6,0,1,0,0,0],
  [0,0,0,1,0,0,4,4,4,4,4,4,4,4,4,4,4,0,0,0,1,0,0,0],
  // Row 14: Neck (with hair on sides)
  [0,0,0,1,0,0,0,0,4,4,4,4,4,4,4,4,0,0,0,0,1,0,0,0],
  // Row 15-18: Torso (slimmer)
  [0,0,0,1,0,0,10,10,10,10,10,10,10,10,10,10,10,10,0,0,1,0,0,0],
  [0,0,0,0,1,10,10,11,10,10,10,10,10,10,10,10,12,10,10,1,0,0,0,0],
  [0,0,0,0,1,10,10,11,10,10,10,10,10,10,10,10,12,10,10,1,0,0,0,0],
  [0,0,0,0,0,10,10,10,10,10,10,10,10,10,10,10,10,10,10,0,0,0,0,0],
  [0,0,0,0,0,0,10,10,10,10,10,10,10,10,10,10,10,10,0,0,0,0,0,0],
  // Row 20-21: Waist (narrower)
  [0,0,0,0,0,0,0,13,13,13,13,13,13,13,13,13,13,0,0,0,0,0,0,0],
  [0,0,0,0,0,0,0,13,13,13,13,13,13,13,13,13,13,0,0,0,0,0,0,0],
  // Row 22-25: Legs (slimmer)
  [0,0,0,0,0,0,0,13,13,13,0,0,0,0,13,13,13,0,0,0,0,0,0,0],
  [0,0,0,0,0,0,0,13,13,14,0,0,0,0,14,13,13,0,0,0,0,0,0,0],
  [0,0,0,0,0,0,0,13,13,14,0,0,0,0,14,13,13,0,0,0,0,0,0,0],
  [0,0,0,0,0,0,0,13,13,14,0,0,0,0,14,13,13,0,0,0,0,0,0,0],
  // Row 26-27: Lower legs
  [0,0,0,0,0,0,0,13,14,14,0,0,0,0,14,14,13,0,0,0,0,0,0,0],
  [0,0,0,0,0,0,0,13,14,14,0,0,0,0,14,14,13,0,0,0,0,0,0,0],
  // Row 28-29: Ankles
  [0,0,0,0,0,0,0,13,14,14,0,0,0,0,14,14,13,0,0,0,0,0,0,0],
  [0,0,0,0,0,0,0,14,14,14,0,0,0,0,14,14,14,0,0,0,0,0,0,0],
  // Row 30-31: Feet (smaller)
  [0,0,0,0,0,0,15,15,15,15,0,0,0,0,15,15,15,15,0,0,0,0,0,0],
  [0,0,0,0,0,0,15,15,15,15,0,0,0,0,15,15,15,15,0,0,0,0,0,0],
];

const BODY_TEMPLATES: Record<Gender, number[][]> = {
  male: BODY_TEMPLATE_MALE,
  female: BODY_TEMPLATE_FEMALE,
};

interface SpriteColorPalette {
  hairMain: string;
  hairHighlight: string;
  hairShadow: string;
  skinMain: string;
  skinHighlight: string;
  skinShadow: string;
  eyes: string;
  eyeHighlight: string;
  blush: string;
  shirtMain: string;
  shirtHighlight: string;
  shirtShadow: string;
  pantsMain: string;
  pantsShadow: string;
  shoes: string;
  outline: string;
}

function createColorPalette(config: NPCConfig): SpriteColorPalette {
  return {
    hairMain: config.hairColor,
    hairHighlight: lightenColor(config.hairColor, 0.3),
    hairShadow: darkenColor(config.hairColor, 0.25),
    skinMain: config.skinColor,
    skinHighlight: lightenColor(config.skinColor, 0.15),
    skinShadow: darkenColor(config.skinColor, 0.15),
    eyes: '#2C3E50',
    eyeHighlight: '#FFFFFF',
    blush: '#FFB6C1',
    shirtMain: config.shirtColor,
    shirtHighlight: lightenColor(config.shirtColor, 0.25),
    shirtShadow: darkenColor(config.shirtColor, 0.2),
    pantsMain: config.pantsColor,
    pantsShadow: darkenColor(config.pantsColor, 0.2),
    shoes: '#3D3D3D',
    outline: darkenColor(config.hairColor, 0.5),
  };
}

function getColorForIndex(index: number, palette: SpriteColorPalette): string | null {
  switch (index) {
    case 0: return null; // Transparent
    case 1: return palette.hairMain;
    case 2: return palette.hairHighlight;
    case 3: return palette.hairShadow;
    case 4: return palette.skinMain;
    case 5: return palette.skinHighlight;
    case 6: return palette.skinShadow;
    case 7: return palette.eyes;
    case 8: return palette.eyeHighlight;
    case 9: return palette.blush;
    case 10: return palette.shirtMain;
    case 11: return palette.shirtHighlight;
    case 12: return palette.shirtShadow;
    case 13: return palette.pantsMain;
    case 14: return palette.pantsShadow;
    case 15: return palette.shoes;
    case 16: return palette.outline;
    default: return null;
  }
}

// Walking animation offsets - smoother 4-frame cycle
function getWalkingAnimation(frame: number): {
  leftLegY: number;
  rightLegY: number;
  bodyBob: number;
  armSwingLeft: number;
  armSwingRight: number;
} {
  switch (frame) {
    case 0: return { leftLegY: 0, rightLegY: 0, bodyBob: 0, armSwingLeft: 0, armSwingRight: 0 };
    case 1: return { leftLegY: -1, rightLegY: 1, bodyBob: -1, armSwingLeft: 1, armSwingRight: -1 };
    case 2: return { leftLegY: 0, rightLegY: 0, bodyBob: 0, armSwingLeft: 0, armSwingRight: 0 };
    case 3: return { leftLegY: 1, rightLegY: -1, bodyBob: -1, armSwingLeft: -1, armSwingRight: 1 };
    default: return { leftLegY: 0, rightLegY: 0, bodyBob: 0, armSwingLeft: 0, armSwingRight: 0 };
  }
}

// Generate a single sprite frame with improved rendering
function generateSpriteFrame(
  config: NPCConfig,
  direction: Direction,
  frame: number
): HTMLCanvasElement {
  const canvas = document.createElement('canvas');
  canvas.width = SPRITE_WIDTH * SCALE;
  canvas.height = SPRITE_HEIGHT * SCALE;
  const ctx = canvas.getContext('2d')!;

  // Enable image smoothing for cleaner scaling
  ctx.imageSmoothingEnabled = false;

  const template = BODY_TEMPLATES[config.gender];
  const palette = createColorPalette(config);
  const anim = getWalkingAnimation(frame);

  // First pass: Draw the base sprite
  for (let y = 0; y < SPRITE_HEIGHT; y++) {
    for (let x = 0; x < SPRITE_WIDTH; x++) {
      let sourceX = x;
      let sourceY = y;

      // Mirror for left direction
      if (direction === 'left') {
        sourceX = SPRITE_WIDTH - 1 - x;
      }

      const colorIndex = template[sourceY]?.[sourceX] ?? 0;
      let color = getColorForIndex(colorIndex, palette);

      if (color) {
        let drawY = y;

        // Apply body bob for walking animation
        if (y >= 6 && y <= 19) {
          drawY = y + anim.bodyBob;
        }

        // Apply leg animation
        const isLeftLeg = x < SPRITE_WIDTH / 2;
        if (y >= 22 && y <= 31) {
          if (isLeftLeg) {
            drawY = y + anim.leftLegY;
          } else {
            drawY = y + anim.rightLegY;
          }
        }

        // Clamp draw position
        drawY = Math.max(0, Math.min(SPRITE_HEIGHT - 1, drawY));

        ctx.fillStyle = color;
        ctx.fillRect(x * SCALE, drawY * SCALE, SCALE, SCALE);
      }
    }
  }

  // Second pass: Add direction-specific modifications
  applyDirectionModifications(ctx, direction, palette, template, config.gender);

  // Third pass: Add soft outline for depth
  addSoftOutline(ctx, palette.outline);

  return canvas;
}

// Apply modifications based on facing direction
function applyDirectionModifications(
  ctx: CanvasRenderingContext2D,
  direction: Direction,
  palette: SpriteColorPalette,
  template: number[][],
  gender: Gender
): void {
  if (direction === 'up') {
    // Show back of head - cover face with hair
    ctx.fillStyle = palette.hairMain;
    for (let y = 6; y <= 13; y++) {
      for (let x = 5; x <= 18; x++) {
        if (template[y]?.[x] !== 0) {
          ctx.fillRect(x * SCALE, y * SCALE, SCALE, SCALE);
        }
      }
    }
    // Add hair highlight on back
    ctx.fillStyle = palette.hairHighlight;
    ctx.fillRect(8 * SCALE, 6 * SCALE, 3 * SCALE, 2 * SCALE);

    // Hair shadow at bottom
    ctx.fillStyle = palette.hairShadow;
    for (let x = 6; x <= 17; x++) {
      ctx.fillRect(x * SCALE, 13 * SCALE, SCALE, SCALE);
    }
  }

  if (direction === 'left' || direction === 'right') {
    // Add slight side profile depth - shadow on far side
    const shadowX = direction === 'right' ? 5 : 18;
    ctx.fillStyle = palette.skinShadow;
    for (let y = 7; y <= 12; y++) {
      const templateCheck = template[y]?.[shadowX];
      if (templateCheck === 4 || templateCheck === 5) {
        ctx.fillRect(
          (direction === 'left' ? SPRITE_WIDTH - 1 - shadowX : shadowX) * SCALE,
          y * SCALE,
          SCALE,
          SCALE
        );
      }
    }
  }
}

// Add soft outline around non-transparent pixels
function addSoftOutline(ctx: CanvasRenderingContext2D, outlineColor: string): void {
  const imageData = ctx.getImageData(0, 0, SPRITE_WIDTH * SCALE, SPRITE_HEIGHT * SCALE);
  const data = imageData.data;
  const outlinePixels: Array<{x: number, y: number}> = [];

  // Find edge pixels
  for (let y = 0; y < SPRITE_HEIGHT * SCALE; y++) {
    for (let x = 0; x < SPRITE_WIDTH * SCALE; x++) {
      const idx = (y * SPRITE_WIDTH * SCALE + x) * 4;
      const alpha = data[idx + 3];

      if (alpha === 0) {
        // Check if any neighbor has content
        const neighbors = [
          [x - 1, y], [x + 1, y], [x, y - 1], [x, y + 1]
        ];

        for (const [nx, ny] of neighbors) {
          if (nx >= 0 && nx < SPRITE_WIDTH * SCALE && ny >= 0 && ny < SPRITE_HEIGHT * SCALE) {
            const nIdx = (ny * SPRITE_WIDTH * SCALE + nx) * 4;
            if (data[nIdx + 3] > 0) {
              outlinePixels.push({ x, y });
              break;
            }
          }
        }
      }
    }
  }

  // Draw outline pixels with reduced opacity
  ctx.fillStyle = outlineColor;
  ctx.globalAlpha = 0.4;
  for (const pixel of outlinePixels) {
    ctx.fillRect(pixel.x, pixel.y, 1, 1);
  }
  ctx.globalAlpha = 1.0;
}

// Generate all sprite textures for an NPC
export function generateCharacterSprites(
  config: NPCConfig
): { [key in Direction]: PIXI.Texture[] } {
  const directions: Direction[] = ['down', 'up', 'left', 'right'];
  const sprites: { [key in Direction]: PIXI.Texture[] } = {
    down: [],
    up: [],
    left: [],
    right: [],
  };

  for (const direction of directions) {
    for (let frame = 0; frame < FRAMES_PER_DIRECTION; frame++) {
      const canvas = generateSpriteFrame(config, direction, frame);
      const texture = PIXI.Texture.from(canvas);
      sprites[direction].push(texture);
    }
  }

  return sprites;
}

// Generate an improved shadow sprite
export function generateShadowSprite(): PIXI.Texture {
  const canvas = document.createElement('canvas');
  const shadowWidth = SPRITE_WIDTH * SCALE;
  const shadowHeight = 8 * SCALE;
  canvas.width = shadowWidth;
  canvas.height = shadowHeight;
  const ctx = canvas.getContext('2d')!;

  // Create gradient for softer shadow
  const gradient = ctx.createRadialGradient(
    shadowWidth / 2, shadowHeight / 2, 0,
    shadowWidth / 2, shadowHeight / 2, shadowWidth / 2.5
  );
  gradient.addColorStop(0, 'rgba(0, 0, 0, 0.35)');
  gradient.addColorStop(0.6, 'rgba(0, 0, 0, 0.15)');
  gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');

  ctx.fillStyle = gradient;
  ctx.beginPath();
  ctx.ellipse(
    shadowWidth / 2,
    shadowHeight / 2,
    shadowWidth / 2.5,
    shadowHeight / 3,
    0,
    0,
    Math.PI * 2
  );
  ctx.fill();

  return PIXI.Texture.from(canvas);
}

// Generate an improved name label texture
export function generateNameLabel(name: string): PIXI.Texture {
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d')!;

  // Use better font sizing
  const fontSize = 11;
  ctx.font = `bold ${fontSize}px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace`;
  const metrics = ctx.measureText(name);
  const padding = 6;
  const borderRadius = 4;

  canvas.width = Math.ceil(metrics.width) + padding * 2;
  canvas.height = fontSize + padding * 2;

  // Draw rounded background
  ctx.fillStyle = 'rgba(30, 30, 40, 0.85)';
  roundRect(ctx, 0, 0, canvas.width, canvas.height, borderRadius);
  ctx.fill();

  // Add subtle border
  ctx.strokeStyle = 'rgba(100, 100, 120, 0.5)';
  ctx.lineWidth = 1;
  roundRect(ctx, 0.5, 0.5, canvas.width - 1, canvas.height - 1, borderRadius);
  ctx.stroke();

  // Draw text with slight shadow
  ctx.font = `bold ${fontSize}px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace`;
  ctx.textBaseline = 'middle';

  // Text shadow
  ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
  ctx.fillText(name, padding + 1, canvas.height / 2 + 1);

  // Main text
  ctx.fillStyle = '#FFFFFF';
  ctx.fillText(name, padding, canvas.height / 2);

  return PIXI.Texture.from(canvas);
}

// Helper for rounded rectangles
function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  width: number,
  height: number,
  radius: number
): void {
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.lineTo(x + width - radius, y);
  ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
  ctx.lineTo(x + width, y + height - radius);
  ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
  ctx.lineTo(x + radius, y + height);
  ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
  ctx.lineTo(x, y + radius);
  ctx.quadraticCurveTo(x, y, x + radius, y);
  ctx.closePath();
}

// Get sprite dimensions for positioning
export function getSpriteSize(): { width: number; height: number } {
  return {
    width: SPRITE_WIDTH * SCALE,
    height: SPRITE_HEIGHT * SCALE,
  };
}

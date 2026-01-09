// Vi World Color Palettes
// Simple pixel art colors with limited palette for retro aesthetic

import { ColorPalette, TileColors } from '../types';

// Character color palette
export const CHARACTER_COLORS: ColorPalette = {
  skin: [
    '#FFE4C4', // Light
    '#DEB887', // Medium light
    '#D2691E', // Medium
    '#8B4513', // Medium dark
    '#654321', // Dark
  ],
  hair: [
    '#2C1810', // Black
    '#4A3728', // Dark brown
    '#8B4513', // Brown
    '#DAA520', // Golden
    '#CD853F', // Sandy
    '#A0522D', // Auburn
    '#696969', // Gray
    '#C0C0C0', // Silver
  ],
  shirt: [
    '#E74C3C', // Red
    '#3498DB', // Blue
    '#2ECC71', // Green
    '#9B59B6', // Purple
    '#F39C12', // Orange
    '#1ABC9C', // Teal
    '#E91E63', // Pink
    '#607D8B', // Gray blue
    '#8E44AD', // Deep purple
    '#16A085', // Dark teal
  ],
  pants: [
    '#2C3E50', // Dark blue
    '#34495E', // Navy
    '#1B4F72', // Denim
    '#4A4A4A', // Dark gray
    '#5D4E37', // Brown
    '#2E4A3F', // Forest green
    '#3D3D3D', // Charcoal
    '#483D8B', // Dark slate blue
  ],
};

// Tile color palette
export const TILE_COLORS: TileColors = {
  grass: [
    '#4A7C23', // Dark grass
    '#5B8C33', // Medium grass
    '#6B9C43', // Light grass
  ],
  path: '#C4A35A', // Sandy path
  building: '#8B7355', // Wood/stone
  roof: '#8B0000', // Dark red roof
  tree: [
    '#2D5016', // Dark leaves
    '#3D6026', // Medium leaves
    '#4D7036', // Light leaves
  ],
  water: [
    '#1E90FF', // Light blue
    '#1873CC', // Medium blue
    '#1156A0', // Dark blue
  ],
  door: '#4A3728', // Dark wood
};

// Outline color for pixel art
export const OUTLINE_COLOR = '#1A1A2E';

// Shadow color
export const SHADOW_COLOR = 'rgba(0, 0, 0, 0.3)';

// UI Colors
export const UI_COLORS = {
  chatBubbleBg: '#FFFFFF',
  chatBubbleBorder: '#333333',
  chatBubbleText: '#1A1A2E',
  nameLabelBg: 'rgba(0, 0, 0, 0.7)',
  nameLabelText: '#FFFFFF',
};

// Helper to get deterministic color from palette based on seed
export function getColorFromSeed(palette: string[], seed: string): string {
  let hash = 0;
  for (let i = 0; i < seed.length; i++) {
    hash = ((hash << 5) - hash) + seed.charCodeAt(i);
    hash = hash & hash;
  }
  return palette[Math.abs(hash) % palette.length];
}

// Generate consistent character colors from ID
export function getCharacterColors(id: string): {
  skinColor: string;
  hairColor: string;
  shirtColor: string;
  pantsColor: string;
} {
  return {
    skinColor: getColorFromSeed(CHARACTER_COLORS.skin, id + 'skin'),
    hairColor: getColorFromSeed(CHARACTER_COLORS.hair, id + 'hair'),
    shirtColor: getColorFromSeed(CHARACTER_COLORS.shirt, id + 'shirt'),
    pantsColor: getColorFromSeed(CHARACTER_COLORS.pants, id + 'pants'),
  };
}

// Convert hex to RGB
export function hexToRgb(hex: string): { r: number; g: number; b: number } {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result
    ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16),
      }
    : { r: 0, g: 0, b: 0 };
}

// Darken a color for shadows
export function darkenColor(hex: string, amount: number = 0.2): string {
  const rgb = hexToRgb(hex);
  const r = Math.max(0, Math.floor(rgb.r * (1 - amount)));
  const g = Math.max(0, Math.floor(rgb.g * (1 - amount)));
  const b = Math.max(0, Math.floor(rgb.b * (1 - amount)));
  return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
}

// Lighten a color for highlights
export function lightenColor(hex: string, amount: number = 0.2): string {
  const rgb = hexToRgb(hex);
  const r = Math.min(255, Math.floor(rgb.r + (255 - rgb.r) * amount));
  const g = Math.min(255, Math.floor(rgb.g + (255 - rgb.g) * amount));
  const b = Math.min(255, Math.floor(rgb.b + (255 - rgb.b) * amount));
  return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
}

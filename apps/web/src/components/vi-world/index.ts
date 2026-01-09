// Vi World - Public exports

export { ViWorld } from './ViWorld';
export { ViWorldCanvas } from './ViWorldCanvas';
export { NPC, createNPCFromPersona } from './NPC';
export { ChatBubble, createChatBubble } from './ChatBubble';
export { WorldRenderer } from './WorldRenderer';
export { Camera } from './Camera';
export { Minimap } from './Minimap';

// Hooks
export { usePixiApp, useGameLoop } from './hooks/usePixiApp';
export { useNPCMovement } from './hooks/useNPCMovement';
export { useNPCChat } from './hooks/useNPCChat';

// Utils
export { generateWorld, generateTileTextures, isWalkable, getRandomSpawnPoint } from './utils/worldGenerator';
export { generateCharacterSprites, generateShadowSprite, generateNameLabel } from './utils/spriteGenerator';
export { CHARACTER_COLORS, TILE_COLORS, getCharacterColors } from './utils/colors';

// Types
export type {
  Position,
  Size,
  TileType,
  Tile,
  WorldConfig,
  WorldData,
  NPCState,
  Direction,
  Gender,
  NPCConfig,
  NPCData,
  ChatMessage,
  ChatBubbleData,
  ViWorldProps,
  ViWorldCanvasProps,
  WorldStats,
} from './types';

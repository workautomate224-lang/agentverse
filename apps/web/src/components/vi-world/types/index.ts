// Vi World Type Definitions

import * as PIXI from 'pixi.js';

// ============ Core Types ============

export interface Position {
  x: number;
  y: number;
}

export interface Size {
  width: number;
  height: number;
}

// ============ World Types ============

export type TileType = 'grass' | 'path' | 'building' | 'tree' | 'water' | 'door';

export interface Tile {
  type: TileType;
  walkable: boolean;
  sprite?: PIXI.Sprite;
}

export interface WorldConfig {
  width: number;
  height: number;
  tileSize: number;
  seed?: number;
}

export interface WorldData {
  tiles: Tile[][];
  spawnPoints: Position[];
  buildingPositions: Position[];
  config: WorldConfig;
}

// ============ NPC Types ============

export type NPCState = 'idle' | 'walking' | 'chatting';

export type Direction = 'down' | 'up' | 'left' | 'right';

export type Gender = 'male' | 'female';

export interface NPCConfig {
  id: string;
  name: string;
  gender: Gender;
  skinColor: string;
  shirtColor: string;
  pantsColor: string;
  hairColor: string;
  traits?: string[];
  // Optional backend sync fields
  initialPosition?: Position;
  initialState?: NPCState;
  initialDirection?: Direction;
}

export interface NPCData {
  config: NPCConfig;
  position: Position;
  targetPosition: Position | null;
  state: NPCState;
  direction: Direction;
  speed: number;
  lastActionTime: number;
  chatCooldown: number;
}

// ============ Chat Types ============

export interface ChatMessage {
  id: string;
  senderId: string;
  senderName: string;
  message: string;
  timestamp: number;
  duration: number;
}

export interface ChatBubbleData {
  npcId: string;
  message: string;
  position: Position;
  opacity: number;
  timeRemaining: number;
}

// ============ Sprite Types ============

export interface SpriteFrame {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface SpriteSheet {
  texture: PIXI.Texture;
  frames: {
    [key in Direction]: SpriteFrame[];
  };
}

export interface CharacterSprites {
  idle: { [key in Direction]: PIXI.Texture[] };
  walk: { [key in Direction]: PIXI.Texture[] };
}

// ============ Game State Types ============

export interface ViWorldState {
  isLoading: boolean;
  isPaused: boolean;
  npcs: Map<string, NPCData>;
  activeChatBubbles: ChatBubbleData[];
  stats: WorldStats;
}

export interface WorldStats {
  population: number;
  activeChats: number;
  totalMessages: number;
}

// ============ Props Types ============

export interface ViWorldProps {
  templateId: string;
}

export interface ViWorldCanvasProps {
  worldData: WorldData;
  npcs: NPCConfig[];
  onReady?: () => void;
}

// ============ Hook Return Types ============

export interface UsePixiAppReturn {
  app: PIXI.Application | null;
  containerRef: React.RefObject<HTMLDivElement>;
  isReady: boolean;
}

export interface UseNPCMovementReturn {
  updateNPCPosition: (npc: NPCData, delta: number, worldData: WorldData) => NPCData;
  selectNewTarget: (npc: NPCData, worldData: WorldData) => Position;
  isPathClear: (from: Position, to: Position, worldData: WorldData) => boolean;
}

export interface UseNPCChatReturn {
  checkForChat: (npcs: NPCData[]) => ChatMessage | null;
  getRandomMessage: (npc: NPCConfig) => string;
}

// ============ Color Palette Types ============

export interface ColorPalette {
  skin: string[];
  hair: string[];
  shirt: string[];
  pants: string[];
}

export interface TileColors {
  grass: string[];
  path: string;
  building: string;
  roof: string;
  tree: string[];
  water: string[];
  door: string;
}

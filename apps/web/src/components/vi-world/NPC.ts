// NPC Entity Class
// Manages individual NPC sprite, animation, and state

import * as PIXI from 'pixi.js';
import { NPCConfig, NPCData, Direction, NPCState, Position } from './types';
import { generateCharacterSprites, generateShadowSprite, generateNameLabel, getSpriteSize } from './utils/spriteGenerator';

const ANIMATION_SPEED = 0.15;

export class NPC {
  public readonly config: NPCConfig;
  public data: NPCData;

  // PixiJS display objects
  public container: PIXI.Container;
  private sprite: PIXI.AnimatedSprite | null = null;
  private shadow: PIXI.Sprite | null = null;
  private nameLabel: PIXI.Sprite | null = null;
  private textures: { [key in Direction]: PIXI.Texture[] };

  // Animation state
  private currentDirection: Direction = 'down';
  private isAnimating: boolean = false;

  constructor(config: NPCConfig, initialPosition: Position, speed: number) {
    this.config = config;
    this.data = {
      config,
      position: initialPosition,
      targetPosition: null,
      state: 'idle',
      direction: 'down',
      speed,
      lastActionTime: Date.now(),
      chatCooldown: 0,
    };

    // Create container for all NPC visuals
    this.container = new PIXI.Container();
    this.container.x = initialPosition.x;
    this.container.y = initialPosition.y;

    // Generate textures
    this.textures = generateCharacterSprites(config);

    // Initialize visuals
    this.initializeSprite();
    this.initializeShadow();
    this.initializeNameLabel();

    // Sort children by y for proper layering
    this.container.sortableChildren = true;
  }

  private initializeSprite(): void {
    // Create animated sprite with down-facing textures
    const downTextures = this.textures.down;
    this.sprite = new PIXI.AnimatedSprite(downTextures);

    // Configure sprite
    this.sprite.anchor.set(0.5, 1); // Anchor at feet
    this.sprite.animationSpeed = ANIMATION_SPEED;
    this.sprite.loop = true;
    this.sprite.zIndex = 2;

    // Position relative to container
    this.sprite.y = 0;

    this.container.addChild(this.sprite);
  }

  private initializeShadow(): void {
    const shadowTexture = generateShadowSprite();
    this.shadow = new PIXI.Sprite(shadowTexture);

    this.shadow.anchor.set(0.5, 0.5);
    this.shadow.y = 2; // Just below feet
    this.shadow.zIndex = 1;
    this.shadow.alpha = 0.5;

    this.container.addChild(this.shadow);
  }

  private initializeNameLabel(): void {
    const labelTexture = generateNameLabel(this.config.name);
    this.nameLabel = new PIXI.Sprite(labelTexture);

    this.nameLabel.anchor.set(0.5, 1);
    this.nameLabel.y = -getSpriteSize().height - 2;
    this.nameLabel.zIndex = 3;
    this.nameLabel.alpha = 0.8;

    this.container.addChild(this.nameLabel);
  }

  // Update NPC state and animation
  public update(newData: NPCData): void {
    // Safety check - container might be destroyed during regeneration
    if (!this.container || this.container.destroyed) return;

    this.data = newData;

    // Update position
    this.container.x = newData.position.x;
    this.container.y = newData.position.y;

    // Update direction and animation
    this.updateAnimation(newData.direction, newData.state);
  }

  private updateAnimation(direction: Direction, state: NPCState): void {
    if (!this.sprite) return;

    // Change texture set if direction changed
    if (direction !== this.currentDirection) {
      this.currentDirection = direction;
      this.sprite.textures = this.textures[direction];
    }

    // Control animation based on state
    if (state === 'walking') {
      if (!this.isAnimating) {
        this.sprite.play();
        this.isAnimating = true;
      }
    } else {
      if (this.isAnimating) {
        this.sprite.stop();
        this.sprite.currentFrame = 0;
        this.isAnimating = false;
      }
    }
  }

  // Set NPC to chatting state
  public startChat(): void {
    this.data = {
      ...this.data,
      state: 'chatting',
      targetPosition: null,
      chatCooldown: Date.now(),
    };

    // Stop movement animation
    if (this.sprite) {
      this.sprite.stop();
      this.sprite.currentFrame = 0;
    }
    this.isAnimating = false;
  }

  // End chat state
  public endChat(): void {
    this.data = {
      ...this.data,
      state: 'idle',
      lastActionTime: Date.now(),
    };
  }

  // Show/hide name label
  public setNameVisible(visible: boolean): void {
    if (this.nameLabel) {
      this.nameLabel.visible = visible;
    }
  }

  // Get current position
  public getPosition(): Position {
    return { ...this.data.position };
  }

  // Get data for movement/chat hooks
  public getData(): NPCData {
    return { ...this.data };
  }

  // Check if NPC is at a specific position (within threshold)
  public isAt(position: Position, threshold: number = 5): boolean {
    const dx = this.data.position.x - position.x;
    const dy = this.data.position.y - position.y;
    return Math.hypot(dx, dy) < threshold;
  }

  // Get distance to another NPC
  public distanceTo(other: NPC): number {
    const dx = this.data.position.x - other.data.position.x;
    const dy = this.data.position.y - other.data.position.y;
    return Math.hypot(dx, dy);
  }

  // Cleanup resources
  public destroy(): void {
    // Destroy textures
    for (const direction of Object.keys(this.textures) as Direction[]) {
      for (const texture of this.textures[direction]) {
        texture.destroy(true);
      }
    }

    // Destroy container and children
    this.container.destroy({ children: true });
  }
}

// Factory function to create NPC from persona data
export function createNPCFromPersona(
  id: string,
  name: string,
  gender: 'male' | 'female',
  traits: string[],
  position: Position,
  speed: number,
  colors: {
    skinColor: string;
    hairColor: string;
    shirtColor: string;
    pantsColor: string;
  }
): NPC {
  const config: NPCConfig = {
    id,
    name: name.split(' ')[0], // Use first name only for label
    gender,
    skinColor: colors.skinColor,
    hairColor: colors.hairColor,
    shirtColor: colors.shirtColor,
    pantsColor: colors.pantsColor,
    traits,
  };

  return new NPC(config, position, speed);
}

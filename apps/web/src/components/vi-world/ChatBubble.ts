// ChatBubble - Speech bubble display for NPC conversations
// Creates and manages chat bubble sprites

import * as PIXI from 'pixi.js';
import { Position, ChatBubbleData } from './types';
import { UI_COLORS } from './utils/colors';

const BUBBLE_PADDING = 8;
const BUBBLE_MAX_WIDTH = 150;
const BUBBLE_BORDER_RADIUS = 8;
const FONT_SIZE = 10;
const TAIL_SIZE = 8;

export class ChatBubble {
  public readonly data: ChatBubbleData;
  public container: PIXI.Container;

  private background: PIXI.Graphics;
  private textSprite: PIXI.Text;
  private fadeStartTime: number = 0;
  private fadeDuration: number = 500; // ms

  constructor(data: ChatBubbleData) {
    this.data = data;

    // Create container
    this.container = new PIXI.Container();
    this.container.x = data.position.x;
    this.container.y = data.position.y;
    this.container.zIndex = 100; // Always on top

    // Create background
    this.background = new PIXI.Graphics();
    this.container.addChild(this.background);

    // Create text
    this.textSprite = new PIXI.Text({
      text: data.message,
      style: {
        fontFamily: '"Press Start 2P", monospace, Arial',
        fontSize: FONT_SIZE,
        fill: UI_COLORS.chatBubbleText,
        wordWrap: true,
        wordWrapWidth: BUBBLE_MAX_WIDTH - BUBBLE_PADDING * 2,
        align: 'left',
      },
    });
    this.textSprite.x = BUBBLE_PADDING;
    this.textSprite.y = BUBBLE_PADDING;
    this.container.addChild(this.textSprite);

    // Draw bubble background
    this.drawBubble();

    // Center the container above the anchor point
    this.container.pivot.x = this.container.width / 2;
    this.container.pivot.y = this.container.height;
  }

  private drawBubble(): void {
    const textWidth = this.textSprite.width;
    const textHeight = this.textSprite.height;

    const bubbleWidth = Math.min(textWidth + BUBBLE_PADDING * 2, BUBBLE_MAX_WIDTH);
    const bubbleHeight = textHeight + BUBBLE_PADDING * 2;

    this.background.clear();

    // Draw shadow
    this.background.roundRect(
      2, 2,
      bubbleWidth,
      bubbleHeight,
      BUBBLE_BORDER_RADIUS
    );
    this.background.fill({ color: 0x000000, alpha: 0.2 });

    // Draw bubble background
    this.background.roundRect(
      0, 0,
      bubbleWidth,
      bubbleHeight,
      BUBBLE_BORDER_RADIUS
    );
    this.background.fill({ color: 0xFFFFFF });
    this.background.stroke({ color: 0x333333, width: 2 });

    // Draw tail (triangle pointing down)
    const tailX = bubbleWidth / 2;
    const tailY = bubbleHeight;

    this.background.moveTo(tailX - TAIL_SIZE / 2, tailY);
    this.background.lineTo(tailX, tailY + TAIL_SIZE);
    this.background.lineTo(tailX + TAIL_SIZE / 2, tailY);
    this.background.closePath();
    this.background.fill({ color: 0xFFFFFF });
    this.background.stroke({ color: 0x333333, width: 2 });

    // Cover the tail border overlap with white
    this.background.rect(tailX - TAIL_SIZE / 2 + 2, tailY - 1, TAIL_SIZE - 4, 2);
    this.background.fill({ color: 0xFFFFFF });
  }

  // Update position to follow NPC
  public updatePosition(position: Position): void {
    this.container.x = position.x;
    this.container.y = position.y - 40; // Above NPC
  }

  // Update bubble state (fade out, etc.)
  public update(delta: number, elapsed: number): boolean {
    const timeRemaining = this.data.timeRemaining - elapsed;

    // Start fading in last 500ms
    if (timeRemaining < this.fadeDuration) {
      const fadeProgress = 1 - (timeRemaining / this.fadeDuration);
      this.container.alpha = Math.max(0, 1 - fadeProgress);

      if (timeRemaining <= 0) {
        return false; // Bubble should be removed
      }
    }

    // Update remaining time
    (this.data as { timeRemaining: number }).timeRemaining = timeRemaining;

    return true; // Bubble still active
  }

  // Set opacity directly
  public setOpacity(opacity: number): void {
    this.container.alpha = opacity;
  }

  // Cleanup resources
  public destroy(): void {
    this.container.destroy({ children: true });
  }
}

// Factory function to create chat bubble from message
export function createChatBubble(
  npcId: string,
  message: string,
  position: Position,
  duration: number
): ChatBubble {
  const data: ChatBubbleData = {
    npcId,
    message,
    position,
    opacity: 1,
    timeRemaining: duration,
  };

  return new ChatBubble(data);
}

// Generate chat bubble texture (alternative static approach)
export function generateChatBubbleTexture(message: string): PIXI.Texture {
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d')!;

  // Measure text
  ctx.font = `${FONT_SIZE}px "Press Start 2P", monospace, Arial`;

  // Word wrap
  const words = message.split(' ');
  const lines: string[] = [];
  let currentLine = '';

  for (const word of words) {
    const testLine = currentLine ? `${currentLine} ${word}` : word;
    const metrics = ctx.measureText(testLine);

    if (metrics.width > BUBBLE_MAX_WIDTH - BUBBLE_PADDING * 2 && currentLine) {
      lines.push(currentLine);
      currentLine = word;
    } else {
      currentLine = testLine;
    }
  }
  if (currentLine) lines.push(currentLine);

  // Calculate dimensions
  const lineHeight = FONT_SIZE + 4;
  const textWidth = Math.min(
    Math.max(...lines.map(line => ctx.measureText(line).width)),
    BUBBLE_MAX_WIDTH - BUBBLE_PADDING * 2
  );
  const textHeight = lines.length * lineHeight;

  const bubbleWidth = textWidth + BUBBLE_PADDING * 2;
  const bubbleHeight = textHeight + BUBBLE_PADDING * 2;

  canvas.width = bubbleWidth + 4;
  canvas.height = bubbleHeight + TAIL_SIZE + 4;

  // Draw shadow
  ctx.fillStyle = 'rgba(0, 0, 0, 0.2)';
  drawRoundedRect(ctx, 2, 2, bubbleWidth, bubbleHeight, BUBBLE_BORDER_RADIUS);
  ctx.fill();

  // Draw bubble
  ctx.fillStyle = UI_COLORS.chatBubbleBg;
  ctx.strokeStyle = UI_COLORS.chatBubbleBorder;
  ctx.lineWidth = 2;
  drawRoundedRect(ctx, 0, 0, bubbleWidth, bubbleHeight, BUBBLE_BORDER_RADIUS);
  ctx.fill();
  ctx.stroke();

  // Draw tail
  ctx.beginPath();
  ctx.moveTo(bubbleWidth / 2 - TAIL_SIZE / 2, bubbleHeight);
  ctx.lineTo(bubbleWidth / 2, bubbleHeight + TAIL_SIZE);
  ctx.lineTo(bubbleWidth / 2 + TAIL_SIZE / 2, bubbleHeight);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();

  // Draw text
  ctx.fillStyle = UI_COLORS.chatBubbleText;
  ctx.font = `${FONT_SIZE}px "Press Start 2P", monospace, Arial`;
  ctx.textBaseline = 'top';

  for (let i = 0; i < lines.length; i++) {
    ctx.fillText(lines[i], BUBBLE_PADDING, BUBBLE_PADDING + i * lineHeight);
  }

  return PIXI.Texture.from(canvas);
}

// Helper to draw rounded rectangle
function drawRoundedRect(
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

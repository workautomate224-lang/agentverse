// useNPCChat - NPC Chat System
// Handles random chat triggers between nearby NPCs

import { useCallback, useRef } from 'react';
import { NPCData, ChatMessage, NPCConfig } from '../types';

interface UseNPCChatOptions {
  chatDistance?: number;       // Distance threshold for starting chat (pixels)
  chatCooldown?: number;       // Minimum time between chats (ms)
  chatDuration?: number;       // How long chat bubble displays (ms)
  chatProbability?: number;    // Chance to start chat when in range (0-1)
}

const DEFAULT_OPTIONS: UseNPCChatOptions = {
  chatDistance: 50,
  chatCooldown: 10000, // 10 seconds
  chatDuration: 4000,  // 4 seconds
  chatProbability: 0.3,
};

// Predefined chat messages categorized by type
const CHAT_MESSAGES = {
  greeting: [
    'Hello there!',
    'Hey!',
    'Hi!',
    'Good day!',
    'Nice to see you!',
  ],
  weather: [
    'Nice weather today!',
    'Lovely day, isn\'t it?',
    'Perfect day for a walk.',
    'Hope it doesn\'t rain.',
  ],
  general: [
    'How\'s it going?',
    'What\'s new?',
    'Taking a stroll?',
    'Beautiful place!',
    'I love this area.',
    'Have you been here long?',
    'Nice running into you!',
    'See you around!',
  ],
  work: [
    'Busy day today.',
    'Got lots to do!',
    'Back to work soon.',
    'Taking a break.',
  ],
  mood: [
    'Feeling great!',
    'Could use some coffee.',
    'What a day!',
    'Life is good.',
    'Just enjoying the view.',
  ],
  farewell: [
    'See ya!',
    'Take care!',
    'Bye bye!',
    'Gotta go!',
    'Later!',
  ],
};

// Get trait-based message modifier
function getTraitModifier(traits?: string[]): string | null {
  if (!traits || traits.length === 0) return null;

  const trait = traits[Math.floor(Math.random() * traits.length)].toLowerCase();

  // Return trait-influenced phrases occasionally
  if (Math.random() < 0.3) {
    if (trait.includes('friendly') || trait.includes('social')) {
      return 'It\'s so nice chatting!';
    }
    if (trait.includes('busy') || trait.includes('workaholic')) {
      return 'Can\'t stay long, lots to do!';
    }
    if (trait.includes('curious')) {
      return 'Have you noticed anything interesting?';
    }
    if (trait.includes('happy') || trait.includes('optimist')) {
      return 'What a wonderful day!';
    }
    if (trait.includes('shy') || trait.includes('introvert')) {
      return '...hello.';
    }
  }

  return null;
}

export function useNPCChat(options: UseNPCChatOptions = {}) {
  const config = { ...DEFAULT_OPTIONS, ...options };
  const lastChatIdRef = useRef<number>(0);

  // Get a random message for an NPC
  const getRandomMessage = useCallback((npc: NPCConfig): string => {
    // Check for trait-based message first
    const traitMessage = getTraitModifier(npc.traits);
    if (traitMessage) {
      return traitMessage;
    }

    // Otherwise pick random category and message
    const categories = Object.keys(CHAT_MESSAGES) as (keyof typeof CHAT_MESSAGES)[];
    const category = categories[Math.floor(Math.random() * categories.length)];
    const messages = CHAT_MESSAGES[category];

    return messages[Math.floor(Math.random() * messages.length)];
  }, []);

  // Check if two NPCs can chat
  const canChat = useCallback((npc1: NPCData, npc2: NPCData): boolean => {
    // Both must be idle
    if (npc1.state !== 'idle' || npc2.state !== 'idle') {
      return false;
    }

    // Check distance
    const distance = Math.hypot(
      npc1.position.x - npc2.position.x,
      npc1.position.y - npc2.position.y
    );

    if (distance > config.chatDistance!) {
      return false;
    }

    // Check cooldowns
    const now = Date.now();
    if (now - npc1.chatCooldown < config.chatCooldown! ||
        now - npc2.chatCooldown < config.chatCooldown!) {
      return false;
    }

    return true;
  }, [config.chatDistance, config.chatCooldown]);

  // Check for potential chat between NPCs
  const checkForChat = useCallback((npcs: NPCData[]): ChatMessage | null => {
    // Find pairs of NPCs that can chat
    for (let i = 0; i < npcs.length; i++) {
      for (let j = i + 1; j < npcs.length; j++) {
        const npc1 = npcs[i];
        const npc2 = npcs[j];

        if (canChat(npc1, npc2)) {
          // Random chance to actually start chat
          if (Math.random() < config.chatProbability!) {
            lastChatIdRef.current++;

            // Randomly pick which NPC speaks
            const speaker = Math.random() < 0.5 ? npc1 : npc2;
            const message = getRandomMessage(speaker.config);

            return {
              id: `chat_${lastChatIdRef.current}`,
              senderId: speaker.config.id,
              senderName: speaker.config.name,
              message,
              timestamp: Date.now(),
              duration: config.chatDuration!,
            };
          }
        }
      }
    }

    return null;
  }, [canChat, config.chatProbability, config.chatDuration, getRandomMessage]);

  // Create chat bubble data from message
  const createChatBubble = useCallback((
    message: ChatMessage,
    npc: NPCData
  ) => {
    return {
      npcId: message.senderId,
      message: message.message,
      position: {
        x: npc.position.x,
        y: npc.position.y - 40, // Above NPC head
      },
      opacity: 1,
      timeRemaining: message.duration,
    };
  }, []);

  // Update chat bubble (fade out animation)
  const updateChatBubble = useCallback((
    bubble: {
      opacity: number;
      timeRemaining: number;
    },
    delta: number
  ) => {
    const elapsed = delta * (1000 / 60); // Convert delta to ms
    const newTimeRemaining = bubble.timeRemaining - elapsed;

    // Start fading in last second
    let newOpacity = bubble.opacity;
    if (newTimeRemaining < 1000) {
      newOpacity = newTimeRemaining / 1000;
    }

    return {
      ...bubble,
      opacity: newOpacity,
      timeRemaining: newTimeRemaining,
    };
  }, []);

  return {
    checkForChat,
    getRandomMessage,
    createChatBubble,
    updateChatBubble,
    canChat,
    chatDuration: config.chatDuration!,
    chatCooldown: config.chatCooldown!,
  };
}

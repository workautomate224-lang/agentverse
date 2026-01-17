/**
 * UI Invalidation Bus - Cross-tab / Cross-browser UI Sync
 *
 * Slice 2-0 Hotfix: Implements real-time UI sync across browser tabs.
 *
 * Architecture:
 * - Primary: BroadcastChannel API (preferred, fast, native)
 * - Fallback: localStorage events (for older browsers)
 *
 * Event Types:
 * - projects:deleted - Project(s) deleted
 * - projects:updated - Project(s) modified (renamed, etc.)
 * - projects:published - Draft project published to ACTIVE
 * - projects:created - New project created
 *
 * Usage in components:
 * ```typescript
 * import { subscribeToInvalidations, emitInvalidation } from '@/lib/invalidationBus';
 *
 * // Subscribe to events
 * useEffect(() => {
 *   return subscribeToInvalidations(['projects:deleted', 'projects:updated'], () => {
 *     queryClient.invalidateQueries({ queryKey: ['projectSpecs'] });
 *   });
 * }, [queryClient]);
 *
 * // Emit events after mutations
 * emitInvalidation('projects:deleted', { ids: [projectId] });
 * ```
 */

export type InvalidationEventType =
  | 'projects:deleted'
  | 'projects:updated'
  | 'projects:published'
  | 'projects:created';

export interface InvalidationEvent {
  type: InvalidationEventType;
  ids?: string[];
  timestamp: number;
  tabId: string;
}

// Unique tab identifier (avoids self-notifications)
const TAB_ID = typeof window !== 'undefined'
  ? `${Date.now()}-${Math.random().toString(36).slice(2)}`
  : 'server';

// BroadcastChannel name
const CHANNEL_NAME = 'agentverse:invalidation';

// localStorage key for fallback
const STORAGE_KEY = 'agentverse:invalidation:event';

// Event listeners
type InvalidationCallback = (event: InvalidationEvent) => void;
const listeners = new Map<string, Set<InvalidationCallback>>();

// BroadcastChannel instance (if available)
let channel: BroadcastChannel | null = null;

/**
 * Initialize the invalidation bus.
 * Called automatically when first listener is registered.
 */
function initialize(): void {
  if (typeof window === 'undefined') return;

  // Try BroadcastChannel first (preferred)
  if ('BroadcastChannel' in window && !channel) {
    channel = new BroadcastChannel(CHANNEL_NAME);
    channel.onmessage = (event: MessageEvent<InvalidationEvent>) => {
      handleIncomingEvent(event.data);
    };
  }

  // Set up localStorage fallback listener
  window.addEventListener('storage', handleStorageEvent);
}

/**
 * Handle incoming event from BroadcastChannel or localStorage.
 */
function handleIncomingEvent(event: InvalidationEvent): void {
  // Ignore events from this same tab
  if (event.tabId === TAB_ID) return;

  // Notify all listeners for this event type
  const typeListeners = listeners.get(event.type);
  if (typeListeners) {
    typeListeners.forEach((callback) => {
      try {
        callback(event);
      } catch {
        // Silently ignore callback errors
      }
    });
  }

  // Also notify wildcard listeners (subscribes to all)
  const wildcardListeners = listeners.get('*');
  if (wildcardListeners) {
    wildcardListeners.forEach((callback) => {
      try {
        callback(event);
      } catch {
        // Silently ignore callback errors
      }
    });
  }
}

/**
 * Handle localStorage 'storage' event (fallback for browsers without BroadcastChannel).
 */
function handleStorageEvent(event: StorageEvent): void {
  if (event.key !== STORAGE_KEY || !event.newValue) return;

  try {
    const invalidationEvent: InvalidationEvent = JSON.parse(event.newValue);
    handleIncomingEvent(invalidationEvent);
  } catch {
    // Invalid JSON, ignore
  }
}

/**
 * Emit an invalidation event to all other tabs.
 *
 * @param type - The event type (e.g., 'projects:deleted')
 * @param data - Optional data (e.g., { ids: ['project-123'] })
 */
export function emitInvalidation(
  type: InvalidationEventType,
  data?: { ids?: string[] }
): void {
  if (typeof window === 'undefined') return;

  const event: InvalidationEvent = {
    type,
    ids: data?.ids,
    timestamp: Date.now(),
    tabId: TAB_ID,
  };

  // Emit via BroadcastChannel if available
  if (channel) {
    channel.postMessage(event);
  }

  // Also emit via localStorage (for fallback and cross-browser sync)
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(event));
    // Immediately remove to allow rapid consecutive events
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // localStorage may be unavailable
  }
}

/**
 * Subscribe to invalidation events.
 *
 * @param types - Event types to listen for (use '*' for all events)
 * @param callback - Function called when matching event is received
 * @returns Unsubscribe function
 *
 * @example
 * ```typescript
 * const unsubscribe = subscribeToInvalidations(['projects:deleted'], (event) => {
 *   refetch();
 * });
 *
 * // Later, when component unmounts
 * unsubscribe();
 * ```
 */
export function subscribeToInvalidations(
  types: (InvalidationEventType | '*')[],
  callback: InvalidationCallback
): () => void {
  // Initialize on first subscription
  if (listeners.size === 0) {
    initialize();
  }

  // Register callback for each event type
  types.forEach((type) => {
    if (!listeners.has(type)) {
      listeners.set(type, new Set());
    }
    listeners.get(type)!.add(callback);
  });

  // Return unsubscribe function
  return () => {
    types.forEach((type) => {
      const typeListeners = listeners.get(type);
      if (typeListeners) {
        typeListeners.delete(callback);
        if (typeListeners.size === 0) {
          listeners.delete(type);
        }
      }
    });
  };
}

/**
 * Hook for easy integration with React components.
 * Automatically subscribes on mount and unsubscribes on unmount.
 *
 * @example
 * ```typescript
 * useInvalidationSubscription(['projects:deleted', 'projects:updated'], () => {
 *   queryClient.invalidateQueries({ queryKey: ['projectSpecs'] });
 * });
 * ```
 */
export function createInvalidationHandler(
  types: (InvalidationEventType | '*')[],
  callback: InvalidationCallback
): () => void {
  return subscribeToInvalidations(types, callback);
}

// =============================================================================
// Entity-specific helpers
// =============================================================================

/**
 * Emit a projects:deleted event.
 */
export function emitProjectsDeleted(ids: string[]): void {
  emitInvalidation('projects:deleted', { ids });
}

/**
 * Emit a projects:updated event (for rename, etc.).
 */
export function emitProjectsUpdated(ids: string[]): void {
  emitInvalidation('projects:updated', { ids });
}

/**
 * Emit a projects:published event (draft -> active).
 */
export function emitProjectsPublished(ids: string[]): void {
  emitInvalidation('projects:published', { ids });
}

/**
 * Emit a projects:created event.
 */
export function emitProjectsCreated(ids: string[]): void {
  emitInvalidation('projects:created', { ids });
}

// =============================================================================
// Auto-revalidation on visibility/focus
// =============================================================================

type AutoRevalidateCallback = () => void;
const autoRevalidateCallbacks = new Set<AutoRevalidateCallback>();
let lastFocusTime = Date.now();
const STALE_THRESHOLD_MS = 30000; // Consider data stale after 30 seconds

/**
 * Register a callback for auto-revalidation on focus/visibility change.
 *
 * @param callback - Function to call when page gains focus (and data may be stale)
 * @returns Unsubscribe function
 */
export function subscribeToAutoRevalidate(callback: AutoRevalidateCallback): () => void {
  if (typeof window === 'undefined') {
    return () => {};
  }

  autoRevalidateCallbacks.add(callback);

  // Initialize focus/visibility listeners if first subscriber
  if (autoRevalidateCallbacks.size === 1) {
    initializeAutoRevalidate();
  }

  return () => {
    autoRevalidateCallbacks.delete(callback);
  };
}

function initializeAutoRevalidate(): void {
  if (typeof window === 'undefined') return;

  // Handle visibility change (tab becomes visible)
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
      const now = Date.now();
      if (now - lastFocusTime > STALE_THRESHOLD_MS) {
        notifyAutoRevalidate();
      }
      lastFocusTime = now;
    }
  });

  // Handle window focus
  window.addEventListener('focus', () => {
    const now = Date.now();
    if (now - lastFocusTime > STALE_THRESHOLD_MS) {
      notifyAutoRevalidate();
    }
    lastFocusTime = now;
  });
}

function notifyAutoRevalidate(): void {
  autoRevalidateCallbacks.forEach((callback) => {
    try {
      callback();
    } catch {
      // Silently ignore errors
    }
  });
}

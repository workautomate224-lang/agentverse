/**
 * React hooks for UI Invalidation Bus
 *
 * Slice 2-0 Hotfix: Provides easy integration of cross-tab sync with React components.
 *
 * @example
 * ```typescript
 * // In Project List component
 * function ProjectList() {
 *   const { refetch } = useProjectSpecs();
 *
 *   // Auto-revalidate on cross-tab events + focus/visibility
 *   useProjectsInvalidation(refetch);
 *
 *   // ...
 * }
 * ```
 */

import { useEffect, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import {
  subscribeToInvalidations,
  subscribeToAutoRevalidate,
  emitProjectsDeleted,
  emitProjectsUpdated,
  emitProjectsPublished,
  emitProjectsCreated,
  type InvalidationEventType,
} from '@/lib/invalidationBus';

/**
 * Hook to subscribe to invalidation events and auto-revalidate on focus.
 *
 * @param eventTypes - Event types to listen for
 * @param onInvalidate - Callback when invalidation occurs
 * @param options - Additional options
 */
export function useInvalidationSubscription(
  eventTypes: (InvalidationEventType | '*')[],
  onInvalidate: () => void,
  options: {
    autoRevalidateOnFocus?: boolean;
  } = {}
): void {
  const { autoRevalidateOnFocus = true } = options;

  useEffect(() => {
    // Subscribe to cross-tab events
    const unsubscribeEvents = subscribeToInvalidations(eventTypes, () => {
      onInvalidate();
    });

    // Subscribe to focus/visibility revalidation
    let unsubscribeFocus: (() => void) | null = null;
    if (autoRevalidateOnFocus) {
      unsubscribeFocus = subscribeToAutoRevalidate(() => {
        onInvalidate();
      });
    }

    return () => {
      unsubscribeEvents();
      if (unsubscribeFocus) {
        unsubscribeFocus();
      }
    };
  }, [eventTypes, onInvalidate, autoRevalidateOnFocus]);
}

/**
 * Hook specifically for project list components.
 * Automatically invalidates React Query cache on cross-tab events.
 *
 * @param refetchFn - Optional custom refetch function (uses queryClient.invalidateQueries if not provided)
 */
export function useProjectsInvalidation(refetchFn?: () => void): void {
  const queryClient = useQueryClient();

  const handleInvalidate = useCallback(() => {
    if (refetchFn) {
      refetchFn();
    } else {
      // Invalidate all project-related queries
      queryClient.invalidateQueries({ queryKey: ['projectSpecs'] });
    }
  }, [queryClient, refetchFn]);

  useInvalidationSubscription(
    ['projects:deleted', 'projects:updated', 'projects:published', 'projects:created'],
    handleInvalidate
  );
}

/**
 * Hook to emit invalidation events.
 * Returns memoized emit functions to avoid unnecessary re-renders.
 */
export function useInvalidationEmit() {
  return {
    emitProjectsDeleted: useCallback((ids: string[]) => {
      emitProjectsDeleted(ids);
    }, []),
    emitProjectsUpdated: useCallback((ids: string[]) => {
      emitProjectsUpdated(ids);
    }, []),
    emitProjectsPublished: useCallback((ids: string[]) => {
      emitProjectsPublished(ids);
    }, []),
    emitProjectsCreated: useCallback((ids: string[]) => {
      emitProjectsCreated(ids);
    }, []),
  };
}

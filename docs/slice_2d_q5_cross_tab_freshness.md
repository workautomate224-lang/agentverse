# Q5: Cross-Tab/Cross-Browser State Freshness

**Date:** 2026-01-19
**Status:** ALREADY IMPLEMENTED ✅

---

## Summary

Cross-tab and cross-browser state freshness is already implemented via the **UI Invalidation Bus** system. This was added in Slice 2-0 Hotfix.

---

## Architecture

### Primary Mechanism: BroadcastChannel API

**Location:** `apps/web/src/lib/invalidationBus.ts`

```typescript
// BroadcastChannel for same-browser, cross-tab communication
const CHANNEL_NAME = 'agentverse:invalidation';
channel = new BroadcastChannel(CHANNEL_NAME);
channel.onmessage = (event: MessageEvent<InvalidationEvent>) => {
  handleIncomingEvent(event.data);
};
```

### Fallback Mechanism: localStorage Events

For older browsers without BroadcastChannel support:

```typescript
// localStorage key for fallback
const STORAGE_KEY = 'agentverse:invalidation:event';

// Listen for storage events
window.addEventListener('storage', handleStorageEvent);

// Emit via localStorage (cross-browser sync)
localStorage.setItem(STORAGE_KEY, JSON.stringify(event));
localStorage.removeItem(STORAGE_KEY); // Immediate removal for rapid events
```

---

## Event Types

| Event Type | Description |
|------------|-------------|
| `projects:deleted` | Project(s) deleted |
| `projects:updated` | Project(s) modified (renamed, etc.) |
| `projects:published` | Draft project published to ACTIVE |
| `projects:created` | New project created |

---

## Auto-Revalidation on Focus

**Location:** `apps/web/src/lib/invalidationBus.ts` (lines 264-324)

```typescript
const STALE_THRESHOLD_MS = 30000; // Consider data stale after 30 seconds

// Handle visibility change (tab becomes visible)
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') {
    const now = Date.now();
    if (now - lastFocusTime > STALE_THRESHOLD_MS) {
      notifyAutoRevalidate();  // Refresh data
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
```

**Behavior:**
- When a tab becomes visible after being hidden for 30+ seconds, data is refreshed
- When a window gains focus after 30+ seconds, data is refreshed
- Prevents unnecessary refetches for quick tab switches

---

## React Query Integration

**Location:** `apps/web/src/components/providers.tsx`

```typescript
new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      gcTime: 30 * 60 * 1000, // 30 minutes garbage collection
      refetchOnWindowFocus: false, // Disabled - handled by invalidation bus
      refetchOnReconnect: false,   // Disabled - handled by invalidation bus
    },
  },
})
```

**Note:** React Query's built-in `refetchOnWindowFocus` is disabled because the Invalidation Bus provides more granular control with the 30-second stale threshold.

---

## React Hooks

**Location:** `apps/web/src/hooks/useInvalidationBus.ts`

### useProjectsInvalidation

```typescript
// Automatically invalidates React Query cache on cross-tab events
export function useProjectsInvalidation(refetchFn?: () => void): void {
  const queryClient = useQueryClient();

  const handleInvalidate = useCallback(() => {
    if (refetchFn) {
      refetchFn();
    } else {
      queryClient.invalidateQueries({ queryKey: ['projectSpecs'] });
    }
  }, [queryClient, refetchFn]);

  useInvalidationSubscription(
    ['projects:deleted', 'projects:updated', 'projects:published', 'projects:created'],
    handleInvalidate
  );
}
```

### useInvalidationEmit

```typescript
// Emit events from components
export function useInvalidationEmit() {
  return {
    emitProjectsDeleted: useCallback((ids: string[]) => {
      emitProjectsDeleted(ids);
    }, []),
    emitProjectsUpdated: useCallback((ids: string[]) => {
      emitProjectsUpdated(ids);
    }, []),
    // ... etc
  };
}
```

---

## Usage Example

```typescript
// In Project List component
function ProjectList() {
  const { data, refetch } = useProjectSpecs();

  // Auto-revalidate on cross-tab events + focus/visibility
  useProjectsInvalidation(refetch);

  return (
    <ul>
      {data?.map((project) => (
        <li key={project.id}>{project.name}</li>
      ))}
    </ul>
  );
}

// In Delete Project mutation
const { mutate: deleteProject } = useMutation({
  mutationFn: api.deleteProject,
  onSuccess: () => {
    emitProjectsDeleted([projectId]); // Notify other tabs
    queryClient.invalidateQueries({ queryKey: ['projectSpecs'] });
  },
});
```

---

## Flow Diagram

```
Tab A: User deletes project
  │
  ├─► 1. Delete mutation succeeds
  │
  ├─► 2. emitProjectsDeleted([id]) called
  │       │
  │       ├─► BroadcastChannel.postMessage(event)
  │       │       │
  │       │       └─► Tab B: channel.onmessage
  │       │               │
  │       │               └─► queryClient.invalidateQueries(['projectSpecs'])
  │       │                       │
  │       │                       └─► UI re-renders with fresh data
  │       │
  │       └─► localStorage.setItem(event) → localStorage.removeItem()
  │               │
  │               └─► Other browsers: window.storage event
  │                       │
  │                       └─► queryClient.invalidateQueries(['projectSpecs'])
  │
  └─► 3. Local queryClient.invalidateQueries(['projectSpecs'])
          │
          └─► Tab A UI re-renders
```

---

## Files

| File | Purpose |
|------|---------|
| `apps/web/src/lib/invalidationBus.ts` | Core invalidation bus implementation |
| `apps/web/src/hooks/useInvalidationBus.ts` | React hooks for easy integration |
| `apps/web/src/components/providers.tsx` | QueryClient configuration |

---

## Verification

To verify cross-tab sync is working:

1. Open project list in two browser tabs
2. In Tab A, delete a project
3. Tab B should immediately update without manual refresh
4. Leave Tab B hidden for 30+ seconds
5. In Tab A, create a new project
6. Switch to Tab B - data should refresh automatically

---

## Summary

**ALREADY IMPLEMENTED** - No changes needed. The system provides:

- ✅ Cross-tab sync via BroadcastChannel API
- ✅ Cross-browser sync via localStorage events
- ✅ Auto-revalidation on focus after 30-second stale threshold
- ✅ React Query integration with query key invalidation
- ✅ React hooks for easy component integration
- ✅ Support for project CRUD operations

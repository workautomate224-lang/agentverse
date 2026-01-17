# Slice 2-0 Hotfix Report

## Overview

This hotfix addresses three critical UI/UX issues in the Project List and wizard flow:

1. **Cross-tab/cross-browser auto-refresh** - Project list now syncs across browser tabs
2. **Dropdown menu clipping** - Action menus on last rows are now fully visible
3. **Draft cleanup on publish** - No duplicate draft + active projects after publish

---

## 1. Realtime UI Sync (Cross-Tab Invalidation Bus)

### Problem
When a user deleted, renamed, or published a project in one tab, other open tabs showing the project list would not update, leading to stale data and potential user confusion.

### Solution Architecture

Implemented a two-layer **UI Invalidation Bus**:

```
┌─────────────────────────────────────────────────────────────────┐
│                     UI Invalidation Bus                          │
├─────────────────────────────────────────────────────────────────┤
│  Primary Layer: BroadcastChannel API                             │
│  - Native browser API for cross-tab communication                │
│  - Fast, no network overhead                                     │
│  - Channel name: 'agentverse:invalidation'                       │
├─────────────────────────────────────────────────────────────────┤
│  Fallback Layer: localStorage Events                             │
│  - For older browsers without BroadcastChannel                   │
│  - Uses 'storage' event listener                                 │
│  - Key: 'agentverse:invalidation:event'                          │
├─────────────────────────────────────────────────────────────────┤
│  Auto-Revalidate Layer                                           │
│  - Focus/visibility change detection                             │
│  - 30-second stale threshold                                     │
│  - Automatic cache refresh when tab becomes visible              │
└─────────────────────────────────────────────────────────────────┘
```

### Event Types

| Event | Trigger | Payload |
|-------|---------|---------|
| `projects:deleted` | User deletes project(s) | `{ ids: string[] }` |
| `projects:updated` | User renames/modifies project | `{ ids: string[] }` |
| `projects:published` | Draft promoted to ACTIVE | `{ ids: string[] }` |
| `projects:created` | New project created | `{ ids: string[] }` |

### Files Changed

| File | Purpose |
|------|---------|
| `apps/web/src/lib/invalidationBus.ts` | Core bus utility (NEW) |
| `apps/web/src/hooks/useInvalidationBus.ts` | React hooks for components (NEW) |
| `apps/web/src/app/dashboard/projects/page.tsx` | Project list integration |
| `apps/web/src/app/dashboard/projects/new/page.tsx` | Wizard publish integration |

### Integration Guide

```typescript
// 1. In your component, import the hook
import { useProjectsInvalidation, useInvalidationEmit } from '@/hooks/useInvalidationBus';

// 2. Subscribe to invalidation events (auto-refetch on events)
function ProjectList() {
  const { refetch } = useProjectSpecs();

  // Auto-revalidate on cross-tab events + focus/visibility
  useProjectsInvalidation(refetch);

  // ...
}

// 3. Emit events after mutations
function DeleteButton({ projectId }) {
  const { emitProjectsDeleted } = useInvalidationEmit();

  const handleDelete = async () => {
    await deleteProject(projectId);
    emitProjectsDeleted([projectId]); // Notify other tabs
  };
}
```

### Behavior

- **On mutation (delete/rename/publish):** Event emitted via BroadcastChannel + localStorage
- **On receiving event in another tab:** React Query cache invalidated, list auto-refreshes
- **On tab focus/visibility:** If >30 seconds since last update, auto-revalidate
- **Self-filtering:** Events from the same tab are ignored (no redundant refreshes)

---

## 2. Dropdown Menu Clipping Fix

### Problem
Action menus on the last few rows of the project table were clipped by the table container's `overflow: hidden`, making options inaccessible.

### Solution

Replaced custom ActionMenu component with **Radix UI Dropdown Menu** using **Portal rendering**:

```tsx
// Menu content renders in a portal to document.body
// This prevents clipping by any parent overflow settings

<DropdownMenuPrimitive.Portal>
  <DropdownMenuPrimitive.Content
    className="z-50 min-w-[8rem] bg-black border border-white/20 ..."
    sideOffset={4}
  >
    {/* Menu items */}
  </DropdownMenuPrimitive.Content>
</DropdownMenuPrimitive.Portal>
```

### Files Changed

| File | Purpose |
|------|---------|
| `apps/web/src/components/ui/dropdown-menu.tsx` | Radix dropdown component (NEW) |
| `apps/web/src/app/dashboard/projects/page.tsx` | Replaced ActionMenu with DropdownMenu |

### Features

- **Portal rendering:** Menu content rendered in `document.body`, outside table
- **Proper z-index:** Uses `z-50` to ensure menu appears above all content
- **Keyboard accessible:** Full arrow key navigation, Enter to select, Escape to close
- **Animation:** Smooth fade/slide animations on open/close
- **Positioning:** Automatic positioning with collision detection

### Styling

The dropdown maintains the cyberpunk aesthetic:
- Black background with white/20 border
- Monospace font, 10-12px text
- Hover state: white/10 background
- Destructive items: red-400 text with red/10 hover background

---

## 3. Draft Cleanup on Publish

### Problem
After publishing a draft project, both the draft and the active project would appear in the list momentarily, causing confusion.

### Root Cause
The project list wasn't receiving notification to refresh when a draft was published in the wizard.

### Solution

1. **Emit invalidation event on publish:**
   ```typescript
   // In wizard handlePublish:
   await api.publishProject(projectId);
   emitProjectsPublished([projectId]); // Notify other tabs
   ```

2. **Project list subscribes to published events:**
   ```typescript
   // In project list:
   useProjectsInvalidation(refetch);
   // This listens to: projects:deleted, projects:updated,
   //                  projects:published, projects:created
   ```

3. **Backend already handles status transition:**
   - Same `project_id` transitions from `status: DRAFT` to `status: ACTIVE`
   - No duplicate entries in database
   - UI refresh shows only the active project

### Files Changed

| File | Purpose |
|------|---------|
| `apps/web/src/app/dashboard/projects/new/page.tsx` | Emit events on publish/create |
| `apps/web/src/app/dashboard/projects/page.tsx` | Subscribe to published events |

### Flow Diagram

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Wizard Tab     │     │  Invalidation   │     │  Projects Tab   │
│                 │     │      Bus        │     │                 │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         │ 1. Publish draft      │                       │
         │ ──────────────────>   │                       │
         │                       │                       │
         │ 2. API call succeeds  │                       │
         │                       │                       │
         │ 3. emitProjectsPublished([id])                │
         │ ───────────────────────────────────────────>  │
         │                       │                       │
         │                       │ 4. BroadcastChannel   │
         │                       │    message received   │
         │                       │ ────────────────────> │
         │                       │                       │
         │                       │     5. queryClient    │
         │                       │        .invalidate()  │
         │                       │                       │
         │                       │     6. refetch()      │
         │                       │     shows only ACTIVE │
         │                       │                       │
```

---

## Testing Checklist

### Cross-Tab Sync
- [ ] Open project list in Tab A and Tab B
- [ ] Delete a project in Tab A
- [ ] Verify Tab B updates within ~1-3 seconds
- [ ] Rename a project in Tab A
- [ ] Verify Tab B shows new name

### Dropdown Visibility
- [ ] Navigate to project list with 5+ projects
- [ ] Click "..." menu on the last row
- [ ] Verify menu appears fully visible (not clipped)
- [ ] Test keyboard navigation (arrow keys, Enter, Escape)

### Draft Publish Flow
- [ ] Create a new draft project (start wizard, save and exit)
- [ ] Open project list in another tab
- [ ] Resume and publish the draft
- [ ] Verify only ACTIVE project appears (no duplicate draft)

---

## Acceptance Criteria Met

| Criteria | Status |
|----------|--------|
| Cross-tab deletion syncs within 3 seconds | ✅ Implemented |
| Dropdown on last row fully visible | ✅ Implemented |
| Keyboard navigation works | ✅ Implemented |
| After publish, only active project shown | ✅ Implemented |
| No duplicate draft + active entries | ✅ Implemented |

---

## Dependencies Added

- `@radix-ui/react-dropdown-menu` (already installed in the project)

---

## Related Documentation

- [BroadcastChannel API (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/BroadcastChannel)
- [Radix UI Dropdown Menu](https://www.radix-ui.com/primitives/docs/components/dropdown-menu)
- [React Query Invalidation](https://tanstack.com/query/latest/docs/framework/react/guides/query-invalidation)

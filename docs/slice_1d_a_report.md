# Slice 1D-A Implementation Report

**Date:** 2026-01-17
**Slice:** 1D-A (Draft Persistence & Blueprint Input)
**Status:** ✅ Complete

## Overview

Slice 1D-A delivers endpoint naming consolidation, enhanced autosave UX, project-scoped localStorage, and the blueprint_input assembly for LLM generation.

## Deliverables

### 1. Endpoint Naming Consolidation

**Canonical API:** `/api/v1/project-specs`
**Deprecated API:** `/api/v1/projects` (sunset: 2026-04-01)

#### Backend Changes (`apps/api/app/api/v1/endpoints/projects.py`)
- Added RFC 8594 deprecation headers to all legacy endpoints
- All 7 endpoints marked with `deprecated=True` in FastAPI decorator
- Response headers include:
  - `Deprecation: 2026-01-17`
  - `Sunset: 2026-04-01`
  - `Link: </api/v1/project-specs>; rel="successor-version"`

```python
def add_deprecation_headers(response: Response) -> None:
    """Add RFC 8594 deprecation headers to response."""
    response.headers["Deprecation"] = DEPRECATION_DATE
    response.headers["Sunset"] = SUNSET_DATE
    response.headers["Link"] = f'<{MIGRATION_URL}>; rel="successor-version"'
```

**Deprecated Endpoints:**
| Endpoint | Replacement |
|----------|-------------|
| `GET /api/v1/projects` | `GET /api/v1/project-specs` |
| `POST /api/v1/projects` | `POST /api/v1/project-specs` |
| `GET /api/v1/projects/{id}` | `GET /api/v1/project-specs/{id}` |
| `PUT /api/v1/projects/{id}` | `PATCH /api/v1/project-specs/{id}` |
| `DELETE /api/v1/projects/{id}` | `DELETE /api/v1/project-specs/{id}` |
| `POST /api/v1/projects/{id}/duplicate` | `POST /api/v1/project-specs/{id}/duplicate` |
| `GET /api/v1/projects/{id}/stats` | `GET /api/v1/project-specs/{id}/stats` |

---

### 2. Enhanced Autosave UX (Slice 1C Nits)

#### File: `apps/web/src/components/pil/SaveDraftIndicator.tsx`

**New SaveStatus type:**
```typescript
export type SaveStatus = 'idle' | 'saving' | 'saved' | 'error' | 'offline' | 'conflict';
```

**New Props:**
- `onRetry?: () => void` - Callback for retry button (shown on 'error' status)
- `onReload?: () => void` - Callback for reload button (shown on 'conflict' status)

**UI States:**
| Status | Icon | Color | Actions |
|--------|------|-------|---------|
| `idle` | Cloud | Gray | - |
| `saving` | Loader2 (spin) | Cyan | - |
| `saved` | Check | Green | Shows timestamp |
| `error` | AlertCircle | Red | Retry button |
| `offline` | CloudOff | Yellow | - |
| `conflict` | AlertTriangle | Orange | Reload button |

#### File: `apps/web/src/lib/wizardPersistence.ts`

**New AutosaveResult type:**
```typescript
export type AutosaveResult = {
  success: boolean;
  status: 'saved' | 'conflict' | 'error' | 'offline' | 'no_project';
  message?: string;
};
```

**New Functions:**
- `onAutosaveResult(callback)` - Register callback for autosave status updates
- `forceSaveToServer()` - Immediate save (for retry)
- `reloadAfterConflict()` - Reload fresh state after 409

**Conflict Handling (409):**
1. On 409 response, sets status to 'conflict'
2. Shows "This draft was updated elsewhere. Reload to continue."
3. Reload button calls `reloadAfterConflict()` which:
   - Fetches latest wizard_state from server
   - Updates local version tracking
   - Caches to localStorage
   - Notifies callback of success

---

### 3. localStorage Scoping by ProjectId

#### Storage Key Pattern:
```typescript
const STORAGE_KEY_PREFIX = 'agentverse:wizard:project:';
const STORAGE_KEY_SUFFIX = ':v1';
const LEGACY_STORAGE_KEY = 'agentverse:wizard:new_project:v1';

// Example: agentverse:wizard:project:abc-123:v1
```

**Migration Logic:**
When a draft project is created, `migrateToProjectStorage(projectId)` automatically:
1. Checks for data in legacy key
2. Copies to project-scoped key
3. Removes legacy key

**Cleanup Functions:**
```typescript
// Clean up when project becomes ACTIVE or is deleted
export function cleanupProjectLocalStorage(projectId: string): void

// Clean up all wizard entries (for dev/testing)
export function cleanupAllWizardLocalStorage(): void
```

**Integration with promoteDraftToActive:**
```typescript
export async function promoteDraftToActive(projectId: string): Promise<boolean> {
  await api.patchProjectStatus(projectId, 'ACTIVE');
  cleanupProjectLocalStorage(projectId);  // Slice 1D-A cleanup
  setDraftProjectId(null, 0);
  return true;
}
```

---

### 4. Blueprint Input Assembly

#### New Interface: `BlueprintInput`
```typescript
export interface BlueprintInput {
  goal_text: string;
  goal_summary: string;
  domain_guess: string;
  clarifying_questions: Array<{
    id: string;
    question: string;
    answer: string | null;
  }>;
  user_skipped_clarify: boolean;
  generation_context: {
    schema_version: number;
    timestamp: string;
  };
}
```

#### New Field: `userDidSkipClarify`
Added to `WizardPersistedState`:
```typescript
export interface WizardPersistedState {
  // ... existing fields
  userDidSkipClarify: boolean;  // Slice 1D-A: Track if user skipped clarification
  // ...
}
```

#### New Functions:
```typescript
/**
 * Build the canonical BlueprintInput from wizard state.
 * Combines goal_text + answers (or null answers if skipped).
 */
export function buildBlueprintInput(state: WizardPersistedState): BlueprintInput

/**
 * Get the BlueprintInput for the current wizard state.
 */
export function getCurrentBlueprintInput(): BlueprintInput | null
```

#### GoalAssistantPanel Integration:
- `userDidSkipClarify` state variable added
- Set to `true` in `handleSkipClarify()`
- Persisted with autosave via `stateToSave`
- Restored from localStorage on component mount

---

## Files Modified

| File | Changes |
|------|---------|
| `apps/api/app/api/v1/endpoints/projects.py` | Added deprecation headers to all endpoints |
| `apps/web/src/components/pil/SaveDraftIndicator.tsx` | Added conflict status, retry/reload buttons |
| `apps/web/src/lib/wizardPersistence.ts` | Project-scoped localStorage, AutosaveResult, BlueprintInput, cleanup functions |
| `apps/web/src/components/pil/v2/GoalAssistantPanel.tsx` | userDidSkipClarify tracking, autosave callback integration |

---

## Testing Checklist

### Autosave UX
- [ ] Save indicator shows "Saving..." when debounce timer starts
- [ ] Save indicator shows "Saved" with timestamp on success
- [ ] Save indicator shows error with "Retry" button on failure
- [ ] Retry button triggers immediate save without debounce
- [ ] 409 conflict shows "Reload" button with appropriate message
- [ ] Reload button fetches fresh state from server

### localStorage Scoping
- [ ] New drafts use project-scoped keys (`agentverse:wizard:project:{id}:v1`)
- [ ] Legacy key data migrates to project-scoped key on first project creation
- [ ] `cleanupProjectLocalStorage()` removes project-specific key
- [ ] Promoting draft to ACTIVE cleans up localStorage

### Blueprint Input
- [ ] `buildBlueprintInput()` returns correct structure
- [ ] Skipped clarification sets `user_skipped_clarify: true`
- [ ] Questions have null answers when clarification was skipped
- [ ] Questions have actual answers when clarification was completed

### Deprecation Headers
- [ ] Legacy `/api/v1/projects` endpoints return deprecation headers
- [ ] `Deprecation`, `Sunset`, and `Link` headers present in response

---

## Architecture Notes

1. **Server as Source of Truth:** localStorage is a fallback only; server state is authoritative
2. **Optimistic Concurrency:** 409 on version mismatch prevents silent data loss
3. **Non-blocking Errors:** Save failures don't block user workflow; manual retry available
4. **Graceful Degradation:** Offline mode continues with localStorage; syncs when online

---

## Next Steps (Slice 1D-B)

- Add `user_skipped_clarify` field to server WizardState schema
- Implement server-side blueprint_input assembly
- Add metrics for autosave success/failure rates

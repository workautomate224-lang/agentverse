# Q6: Draft Lifecycle Correctness

**Date:** 2026-01-19
**Status:** VERIFIED ✅

---

## Summary

The draft lifecycle is implemented correctly. When a DRAFT project is published, it transforms **in-place** to ACTIVE status - there is no duplicate/copy. The draft "disappears" because the same project record changes status.

---

## Lifecycle Flow

```
┌─────────────┐     ┌───────────────┐     ┌─────────────┐
│   CREATE    │────►│    DRAFT      │────►│   ACTIVE    │
│ (wizard)    │     │ (incomplete)  │     │ (published) │
└─────────────┘     └───────────────┘     └─────────────┘
                           │                     │
                           │                     │
                           ▼                     ▼
                    ┌─────────────┐       ┌─────────────┐
                    │  ARCHIVED   │◄──────│  ARCHIVED   │
                    │ (cancelled) │       │ (archived)  │
                    └─────────────┘       └─────────────┘
```

---

## Valid Status Transitions

From `apps/api/app/api/v1/endpoints/project_specs.py` (lines 1069-1079):

```python
valid_transitions = {
    ("DRAFT", "ACTIVE"),    # wizard complete → publish
    ("DRAFT", "ARCHIVED"),  # cancel wizard
    ("ACTIVE", "ARCHIVED"), # archive project
    ("ARCHIVED", "ACTIVE"), # restore project
}
```

---

## Publish Endpoint Behavior

**Endpoint:** `POST /api/v1/project-specs/{project_id}/publish`

**What happens on publish:**

1. **Validates** project is in DRAFT status
2. **Validates** wizard_state.step is 'blueprint_preview' or 'blueprint_ready'
3. **Validates** active blueprint exists (Slice 2D requirement)
4. **Updates in-place:**
   - `status = 'ACTIVE'`
   - `published_at = current timestamp`
   - `wizard_state.step = 'complete'`
5. **Triggers** PROJECT_GENESIS job for guidance generation

**SQL (line 1241):**
```sql
UPDATE project_specs
SET status = 'ACTIVE',
    published_at = :published_at,
    wizard_state = :wizard_state,
    updated_at = :updated_at
WHERE id = :project_id AND tenant_id = :tenant_id
```

---

## UI Indicators

### Projects List View

| Status | Badge | Button | Behavior |
|--------|-------|--------|----------|
| DRAFT (incomplete) | "DRAFT" | "Resume" | Opens wizard to continue |
| ACTIVE | None | "Open" | Opens project workspace |
| ARCHIVED | "ARCHIVED" | "Restore" | Can restore to ACTIVE |

### Example from Testing

| Project ID | Name | Status | UI Indicator |
|------------|------|--------|--------------|
| `c40af2ef` | "Draft: GE2026..." | DRAFT | Shows "DRAFT" badge + "Resume" button |
| `0851bad6` | "Draft: GE2026..." | ACTIVE | Shows "Open" button only |

**Key Insight:** The "Draft:" prefix in project names is user-entered text, NOT the status indicator. A project named "Draft: X" can be ACTIVE if it was published.

---

## Verification Evidence

### Projects List Screenshot Analysis

1. **DRAFT project (c40af2ef):**
   - Shows "DRAFT" badge explicitly
   - Shows "Resume" button (not "Open")
   - Last updated: 18/01/2026

2. **ACTIVE project (0851bad6):**
   - NO status badge shown
   - Shows "Open" button
   - Has blueprint-driven guidance (verified in Q1)
   - Last updated: 19/01/2026

---

## Code Flow Verification

### 1. Create Project (DRAFT)

```typescript
// Frontend: POST /api/v1/project-specs
{
  "name": "Draft: My Project",
  "status": "DRAFT",
  "wizard_state": { "step": "goal" }
}
```

### 2. Complete Wizard

```typescript
// Frontend: PATCH /api/v1/project-specs/{id}/wizard-state
{
  "step": "blueprint_ready",
  // ... other wizard fields
}
```

### 3. Publish

```typescript
// Frontend: POST /api/v1/project-specs/{id}/publish
// Backend: Updates status to ACTIVE in-place
// Result: Same project ID, status changed
```

### 4. Project List Refresh

```typescript
// Frontend: GET /api/v1/project-specs
// Returns same project with status: "ACTIVE"
// UI shows "Open" button instead of "Resume"
```

---

## Conclusion

**The draft lifecycle is correct:**

- ✅ DRAFT projects show "DRAFT" badge and "Resume" button
- ✅ When published, status changes to ACTIVE **in-place** (same project ID)
- ✅ Published projects show "Open" button, no DRAFT badge
- ✅ The draft "disappears" because it becomes the active project
- ✅ No duplicate records created during publish
- ✅ Published_at timestamp is set on publish

**Important Distinction:**
- Project **name** can contain "Draft:" as user text
- Project **status** is the actual DRAFT/ACTIVE/ARCHIVED field
- These are independent - a project named "Draft: X" can have status = ACTIVE

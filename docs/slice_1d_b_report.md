# Slice 1D-B Implementation Report

**Date:** 2026-01-17
**Slice:** 1D-B (Blueprint Ready + Publish)
**Status:** ✅ Complete

## Overview

Slice 1D-B delivers the publish functionality for draft projects, enabling users to promote DRAFT projects to ACTIVE status after completing the blueprint configuration. This slice includes server-side validation, publish endpoint, published_at tracking, and UI controls for publishing or editing.

## Deliverables

### 1. Server-Side Wizard Stage Validation

#### File: `apps/api/app/api/v1/endpoints/project_specs.py`

**Valid Wizard Steps for Publish:**
```python
# Slice 1D-B: 'blueprint_ready' is the server-side canonical step for publish validation
# Allow publish from blueprint_preview or blueprint_ready
valid_steps = ["blueprint_preview", "blueprint_ready"]
```

The publish endpoint validates that the wizard is at an appropriate stage before allowing the transition from DRAFT to ACTIVE.

---

### 2. Publish Endpoint

#### Endpoint: `POST /api/v1/project-specs/{project_id}/publish`

**Location:** `apps/api/app/api/v1/endpoints/project_specs.py:1121-1236`

**Request:** Empty body (project_id in URL path)

**Response Schema:**
```python
class PublishProjectResponse(BaseModel):
    """Response from publishing a draft project."""
    id: str
    status: str
    published_at: str
    message: str
```

**Response Example:**
```json
{
  "id": "abc-123-uuid",
  "status": "ACTIVE",
  "published_at": "2026-01-17T12:00:00+00:00",
  "message": "Project published successfully"
}
```

**Validation Rules:**
1. Project must exist
2. User must own the project (tenant match)
3. Project status must be `DRAFT`
4. Wizard state must be present
5. Wizard step must be one of: `["blueprint_preview", "blueprint_ready"]`

**Error Responses:**
| Code | Condition |
|------|-----------|
| 400 | Status is not DRAFT |
| 400 | Wizard state missing |
| 400 | Wizard step not in valid_steps |
| 404 | Project not found |

**State Transition:**
```python
# Update to ACTIVE with published_at and set wizard step to complete
UPDATE project_specs SET
    status = 'ACTIVE',
    wizard_state = jsonb_set(wizard_state, '{step}', '"complete"'),
    updated_at = :now,
    published_at = :published_at,
    wizard_state_version = wizard_state_version + 1
WHERE id = :project_id
```

---

### 3. Published Timestamp Field

#### Model: `apps/api/app/models/project_spec.py`

```python
# ==========================================================================
# Slice 1D-B: Published timestamp
# ==========================================================================
# Set when DRAFT is promoted to ACTIVE via /publish endpoint
published_at: Mapped[Optional[datetime]] = mapped_column(
    DateTime(timezone=True), nullable=True
)
```

#### Migration: `apps/api/alembic/versions/2026_01_17_0003_add_published_at.py`

```python
revision = 'slice_1d_b_published_at_001'
down_revision = 'slice_1c_wizard_state_001'

def upgrade() -> None:
    op.add_column(
        'project_specs',
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index('ix_project_specs_published_at', 'project_specs', ['published_at'])

def downgrade() -> None:
    op.drop_index('ix_project_specs_published_at', table_name='project_specs')
    op.drop_column('project_specs', 'published_at')
```

**Schema Response:**
```python
published_at: Optional[str] = Field(
    default=None,
    description="ISO timestamp when DRAFT was promoted to ACTIVE"
)
```

---

### 4. Frontend API Client

#### File: `apps/web/src/lib/api.ts`

```typescript
async publishProject(projectId: string): Promise<{
  id: string;
  status: string;
  published_at: string;
  message: string;
}> {
  return this.request(`/api/v1/project-specs/${projectId}/publish`, {
    method: 'POST',
  });
}
```

---

### 5. Blueprint Preview UI

#### File: `apps/web/src/components/pil/v2/GoalAssistantPanel.tsx`

**New Props:**
```typescript
/** Slice 1D-B: Callback when user clicks Publish Project */
onPublish?: () => Promise<void>;
/** Slice 1D-B: Callback when user clicks Edit Answers */
onEditAnswers?: () => void;
```

**UI Component (lines 1084-1177):**
- "Publish Project" button (cyan, primary CTA)
- "Edit Answers" button (outline variant, returns to clarify step)
- Loading state during publish
- Error handling with toast notifications

**Edit Answers Handler:**
```typescript
// Slice 1D-B: Handle "Edit Answers" from blueprint preview
const handleEditAnswers = useCallback(() => {
  if (readOnly) return;
  setStage('clarify');
  onEditAnswers?.();
}, [readOnly, onEditAnswers]);
```

---

### 6. Wizard Page Integration

#### File: `apps/web/src/app/dashboard/projects/new/page.tsx`

**Publish Handler:**
```typescript
const handlePublish = useCallback(async () => {
  const projectId = draftProjectId || getDraftProjectId()?.projectId;
  if (!projectId) {
    setCreateError('No draft project to publish. Please complete the wizard first.');
    return;
  }
  setIsPublishing(true);
  setCreateError(null);
  try {
    await api.publishProject(projectId);
    clearAllWizardState();
    router.push(`/p/${projectId}/overview`);
  } catch (error) {
    setCreateError(error instanceof Error ? error.message : 'Failed to publish project');
  } finally {
    setIsPublishing(false);
  }
}, [draftProjectId, router]);
```

**Component Usage:**
```tsx
<GoalAssistantPanel
  goalText={formData.goal}
  onBlueprintReady={handleBlueprintReady}
  onAnalysisStart={() => setIsAnalyzing(true)}
  onGoalTextRestore={(restoredGoal) => {...}}
  onStateCleared={() => {...}}
  onDraftCreate={createDraftProject}
  onPublish={handlePublish}
  onEditAnswers={handleEditAnswers}
  className="mt-4"
/>
```

---

### 7. Post-Publish Read-Only Mode

#### File: `apps/web/src/app/dashboard/projects/new/page.tsx`

When a user attempts to resume an ACTIVE project, they are redirected to the overview page:

```typescript
useEffect(() => {
  const resumeProjectId = searchParams.get('resume');
  if (!resumeProjectId) return;

  const loadResumeState = async () => {
    setIsLoadingResume(true);
    try {
      // First, check if the project is ACTIVE - if so, redirect to overview
      const project = await api.getProjectSpec(resumeProjectId);
      if (project.status === 'ACTIVE') {
        // Project was already published - redirect to overview page
        router.replace(`/p/${resumeProjectId}/overview`);
        return;
      }
      // ... continue with DRAFT resume logic
    } catch (error) {
      // Handle error
    }
  };
  loadResumeState();
}, [searchParams, router]);
```

This prevents users from accessing the wizard for already-published projects.

---

### 8. Project List Behavior (Verified from Slice 1C)

#### File: `apps/web/src/app/dashboard/projects/page.tsx`

| Project Status | Badge | Button | Navigation |
|----------------|-------|--------|------------|
| DRAFT | "Draft" badge | "Resume" | `/dashboard/projects/new?resume={id}` |
| ACTIVE | None | "Open" | `/p/{id}/overview` |

---

## Files Modified

| File | Changes |
|------|---------|
| `apps/api/app/api/v1/endpoints/project_specs.py` | Added `/publish` endpoint with validation |
| `apps/api/app/models/project_spec.py` | Added `published_at` field |
| `apps/api/alembic/versions/2026_01_17_0003_add_published_at.py` | Migration for published_at |
| `apps/web/src/lib/api.ts` | Added `publishProject()` method |
| `apps/web/src/components/pil/v2/GoalAssistantPanel.tsx` | Added onPublish/onEditAnswers props and UI |
| `apps/web/src/app/dashboard/projects/new/page.tsx` | Added publish handler and ACTIVE redirect |

---

## Testing Checklist

### Publish Endpoint
- [ ] POST /api/v1/project-specs/{id}/publish returns 200 for valid DRAFT
- [ ] Returns 400 if status is not DRAFT
- [ ] Returns 400 if wizard_state is missing
- [ ] Returns 400 if wizard step is not in valid_steps
- [ ] Returns 404 if project not found
- [ ] Sets status to ACTIVE
- [ ] Sets published_at to current timestamp
- [ ] Sets wizard step to 'complete'
- [ ] Increments wizard_state_version

### Frontend Integration
- [ ] "Publish Project" button visible in blueprint_preview stage
- [ ] Button shows loading state during publish
- [ ] Successful publish navigates to `/p/{id}/overview`
- [ ] Failed publish shows error toast
- [ ] "Edit Answers" button returns to clarify stage
- [ ] localStorage cleaned up after successful publish

### Post-Publish Protection
- [ ] Navigating to `/dashboard/projects/new?resume={active_id}` redirects to overview
- [ ] ACTIVE projects cannot re-enter wizard

### Project List
- [ ] DRAFT projects show "Draft" badge and "Resume" button
- [ ] ACTIVE projects show "Open" button
- [ ] Navigation matches project status

---

## Architecture Notes

1. **Atomic Publish:** Single endpoint handles validation and state transition atomically
2. **Wizard Step Validation:** Server validates wizard progress before allowing publish
3. **Post-Publish Protection:** Frontend redirects prevent accidental wizard access
4. **localStorage Cleanup:** `clearAllWizardState()` removes persistence on publish
5. **Version Increment:** `wizard_state_version` incremented to track state changes

---

## User Flow

```
[DRAFT Project in Wizard]
         ↓
[Complete Clarification]
         ↓
[Blueprint Preview Stage]
         ↓
   ┌─────┴─────┐
   ↓           ↓
[Edit Answers] [Publish Project]
   ↓           ↓
[Clarify Stage] [ACTIVE Status]
               ↓
         [Overview Page]
```

---

## Next Steps (Future Slices)

- Add analytics for publish conversion rate
- Implement bulk publish for multiple drafts
- Add publish confirmation modal with project summary
- Implement unpublish/archive functionality

# Comprehensive Platform Testing Bug Report

**Date**: January 14, 2026
**Tester**: Claude Opus 4.5
**Test Project**: 2024 US Presidential Election Simulation
**Project UUID**: `0656917d-4939-4527-b1a1-5063d0a509be`

## Executive Summary

Completed comprehensive testing of all 13 project workspace pages. Found **5 bugs** total, with **2 critical bugs** that block core simulation functionality.

### Bugs by Severity

| Severity | Count | Description |
|----------|-------|-------------|
| 🔴 CRITICAL | 2 | Block simulation execution |
| 🟡 MEDIUM | 2 | Incorrect data display |
| 🟢 LOW | 1 | UI/UX issue |

---

## Critical Bugs

### BUG #1: ✅ FIXED - Project Wizard Uses Mock ID
**Status**: Fixed
**Location**: `apps/web/src/app/dashboard/projects/new/page.tsx`
**Issue**: Project creation wizard generated mock project IDs instead of using API response
**Fix**: Updated to use `data.id` from POST `/api/v1/project-specs/` response

### BUG #2: ✅ FIXED - Domain Validation Error
**Status**: Fixed
**Location**: `apps/web/src/app/dashboard/projects/new/page.tsx`
**Issue**: Schema expected `domain` field but frontend sent `coreType`
**Fix**: Added `detectDomain()` function to map coreType to valid domain values

### BUG #3: 🔴 PENDING - Layout Uses Mock Project Data
**Status**: NOT FIXED
**Location**: `apps/web/src/app/p/[projectId]/layout.tsx:38-43`
**Issue**: Project workspace sidebar shows "Sample Project" instead of actual project name from API

```typescript
// Current problematic code (line 38-43)
const getMockProject = (projectId: string) => ({
  id: projectId,
  name: projectId.startsWith('proj_') ? 'New Project' : 'Sample Project',
  coreType: 'collective' as const,
});
```

**Impact**:
- Sidebar always shows "Sample Project" regardless of actual project name
- Project coreType badge always shows "Collective"
- User confusion about which project they're viewing

**Fix Required**: Replace `getMockProject()` with API call to `GET /api/v1/project-specs/{projectId}`

### BUG #4: 🔴 CRITICAL - FK Constraint Error in Run Execution
**Status**: NOT FIXED
**Location**: Backend database schema
**Issue**: `run_outcomes` table has FK to `projects` table, but projects are created in `project_specs`

**Error from Celery worker**:
```
sqlalchemy.exc.IntegrityError: (psycopg2.errors.ForeignKeyViolation)
insert or update on table "run_outcomes" violates foreign key constraint "run_outcomes_project_id_fkey"
DETAIL: Key (project_id)=(0656917d-4939-4527-b1a1-5063d0a509be) is not present in table "projects".
```

**Impact**:
- ALL simulation runs fail immediately
- Run Center shows perpetual "RUNNING" state then fails
- Society Simulation cannot analyze runs (none complete)
- Reliability page cannot show metrics (no completed runs)
- Telemetry & Replay cannot play back (no data)
- 2D World Viewer cannot visualize (no run data)
- Reports show 0% success rate

**Fix Required**: Either:
1. Update FK in `run_outcomes` to reference `project_specs` instead of `projects`
2. OR create corresponding record in `projects` table when creating project_spec

### BUG #5: 🟡 MEDIUM - Settings Page Uses Mock Data
**Status**: NOT FIXED
**Location**: `apps/web/src/app/p/[projectId]/settings/page.tsx`
**Issue**: Settings page loads hardcoded default values, not actual project data. SAVE button doesn't persist.

**Observations**:
- PROJECT NAME shows "New Project" instead of actual name
- DESCRIPTION is empty despite project having description
- SAVE CHANGES button shows no feedback (no toast, no API call)
- Settings not actually saved to database

**Impact**: Users cannot update project settings

**Fix Required**: Connect Settings page to API endpoints for GET/PATCH project data

---

## Pages Tested - Status Summary

### Working Correctly ✅

| Page | URL | Status | Notes |
|------|-----|--------|-------|
| Overview | `/p/{id}/overview` | ✅ Works | Shows project summary |
| Data & Personas | `/p/{id}/data-personas` | ✅ Works | Created 100 AI personas |
| Rules & Assumptions | `/p/{id}/rules` | ✅ Works | Created 2 rules |
| Event Lab | `/p/{id}/event-lab` | ✅ Works | Generated 5 AI scenarios |
| Universe Map | `/p/{id}/universe-map` | ✅ Works | Manual + AI forks working |
| Target Planner | `/p/{id}/target` | ✅ Works | Plan creation functional |

### Blocked by BUG #4 (No Completed Runs) ⚠️

| Page | URL | Status | Notes |
|------|-----|--------|-------|
| Run Center | `/p/{id}/run-center` | ⚠️ Blocked | Runs start but fail immediately |
| Society Simulation | `/p/{id}/society` | ⚠️ Blocked | "No completed runs" |
| Reliability | `/p/{id}/reliability` | ⚠️ Blocked | "No runs available" |
| Telemetry & Replay | `/p/{id}/replay` | ⚠️ Blocked | "No completed runs available" |
| 2D World Viewer | `/p/{id}/world-viewer` | ⚠️ Blocked | "Select a Run to Visualize" |
| Reports | `/p/{id}/reports` | ⚠️ Partial | Shows stats but 0% success |

### Has Bug ❌

| Page | URL | Status | Bug |
|------|-----|--------|-----|
| Settings | `/p/{id}/settings` | ❌ Mock | BUG #5 - No API integration |

---

## Test Data Created

### Project
- **Name**: 2024 US Election Simulation
- **UUID**: `0656917d-4939-4527-b1a1-5063d0a509be`
- **Core Type**: Collective
- **Domain**: Political

### Personas (100 total)
- AI-generated US voter personas with demographics
- Age distribution: 18-75
- Political affiliations: Democrat, Republican, Independent
- Various education levels and income brackets

### Rules (2 total)
1. **Voter Sentiment Shift Rule** - Economic news affects voter behavior
2. **Debate Impact Rule** - Debate performance affects candidate support

### Event Lab Scenarios (5 total)
AI-generated "What-if" scenarios for election simulation

### Universe Map Nodes (5 total)
- 1 Baseline node
- 1 Manual fork ("Trump Rally Surge")
- 3 AI-generated forks ("Optimistic", "Conservative", "Alternative")

---

## Recommended Fix Priority

### Priority 1 (Critical - Must Fix)
1. **BUG #4**: FK constraint error - This blocks ALL simulation functionality

### Priority 2 (High - Should Fix)
2. **BUG #3**: Layout mock data - Confusing UX, wrong project names displayed

### Priority 3 (Medium - Nice to Fix)
3. **BUG #5**: Settings mock data - Cannot update project settings

---

## Technical Details for Fixes

### BUG #3 Fix - Layout API Integration

```typescript
// apps/web/src/app/p/[projectId]/layout.tsx

// Replace getMockProject with API hook
import { useProject } from '@/hooks/useApi';

// In component:
const { data: project, isLoading } = useProject(projectId);

if (isLoading || !project) {
  return <ProjectWorkspaceSkeleton />;
}

// Use project.name, project.coreType, etc.
```

### BUG #4 Fix - Database Schema

Option A: Migration to fix FK reference
```python
# New migration
def upgrade():
    op.drop_constraint('run_outcomes_project_id_fkey', 'run_outcomes', type_='foreignkey')
    op.create_foreign_key(
        'run_outcomes_project_id_fkey',
        'run_outcomes', 'project_specs',
        ['project_id'], ['id']
    )
```

Option B: Create projects record when creating project_spec
```python
# In project_spec creation service
async def create_project_spec(...):
    # Create in project_specs
    spec = ProjectSpec(...)
    db.add(spec)

    # Also create matching record in projects (if needed for legacy FK)
    project = Project(id=spec.id, ...)
    db.add(project)

    await db.commit()
```

### BUG #5 Fix - Settings API Integration

```typescript
// apps/web/src/app/p/[projectId]/settings/page.tsx

// Add API hooks
const { data: project } = useProject(projectId);
const updateProject = useUpdateProject();

// Form submission
const onSave = async (data) => {
  await updateProject.mutateAsync({
    projectId,
    ...data
  });
  toast.success('Settings saved');
};
```

---

## Conclusion

The platform has solid frontend infrastructure with well-designed pages. The critical blocker is **BUG #4** - once the FK constraint is fixed, all run-dependent features will work. BUG #3 and #5 are quality-of-life issues that should be addressed for proper UX.

**Next Steps**:
1. Fix BUG #4 (FK constraint) in backend
2. Re-test Run Center to confirm simulations complete
3. Fix BUG #3 (layout) and BUG #5 (settings) in frontend
4. Run complete election simulation backtest

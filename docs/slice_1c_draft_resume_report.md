# Slice 1C: Draft/Resume - Implementation Report

## Status: Complete

**Date:** 2026-01-17

## Summary

Slice 1C implements project-level persistence for the Goal → Clarify → Blueprint wizard, enabling draft projects that can be resumed across sessions.

## Features Implemented

### Backend (FastAPI)

1. **Database Schema Changes**
   - Added `status` column to `project_specs` (DRAFT, ACTIVE, ARCHIVED)
   - Added `wizard_state` JSONB column for storing wizard progress
   - Added `wizard_state_version` for optimistic concurrency control
   - Created indexes for efficient tenant+status queries

2. **API Endpoints**
   - `PATCH /api/v1/projects/{id}/wizard-state` - Update wizard state with version checking (returns 409 on conflict)
   - `GET /api/v1/projects/{id}/wizard-state` - Load wizard state from server
   - `PATCH /api/v1/projects/{id}/status` - Update project status (promote DRAFT → ACTIVE)

3. **Migration Improvements**
   - Added database readiness check with retry loop (30 attempts, 2s wait)
   - Fixed migration chain dependencies for clean upgrades

### Frontend (Next.js)

1. **Draft Creation**
   - Creates draft project when goal analysis starts
   - `onDraftCreate` callback in GoalAssistantPanel
   - Draft projects have `status: 'DRAFT'`

2. **Autosave**
   - 500ms debounced autosave to server
   - localStorage as fallback
   - Server is source of truth

3. **Resume Flow**
   - `?resume=<projectId>` query parameter support
   - Loading state while resuming from server
   - Restores goal text, blueprint draft, and wizard stage

4. **Projects List**
   - "DRAFT" badge on draft projects
   - "Resume" button instead of "Open" for drafts
   - Proper status type comparisons (uppercase)

## Key Files Modified

### Backend
- `apps/api/alembic/versions/2026_01_17_0002_add_wizard_state_to_projects.py` - Migration
- `apps/api/app/models/project.py` - Model updates
- `apps/api/app/schemas/project.py` - Schema updates
- `apps/api/app/api/v1/projects.py` - API endpoints
- `apps/api/start.sh` - Database readiness check

### Frontend
- `apps/web/src/lib/api.ts` - API client methods
- `apps/web/src/lib/wizardPersistence.ts` - Server sync utilities
- `apps/web/src/components/pil/GoalAssistantPanel.tsx` - Draft creation callback
- `apps/web/src/app/dashboard/projects/new/page.tsx` - Resume query param handling
- `apps/web/src/app/dashboard/projects/page.tsx` - Draft badge and resume button

## Acceptance Tests

| Test | Description | Status |
|------|-------------|--------|
| A | Draft projects exist in DB with DRAFT status | ✅ Ready |
| B | Drafts appear in Projects list with "Draft" badge | ✅ Ready |
| C | Resume works across sessions without re-running goal_analysis | ✅ Ready |
| D | Autosave with 500ms debounce to server | ✅ Ready |
| E | Server returns 409 Conflict on version mismatch | ✅ Ready |

## Deployment

- **API Staging:** https://api.mad2.ai
- **Web Staging:** https://www.mad2.ai

## Testing Instructions

1. Navigate to `/dashboard/projects/new`
2. Enter a goal and click "Analyze"
3. Observe a draft project is created (check DB or Projects list)
4. Close the browser and reopen
5. Go to Projects list, see DRAFT badge
6. Click "Resume" to continue where you left off

## Architecture Notes

- **Fork-not-mutate (C1):** Wizard state is stored as a version-controlled JSONB, not overwritten
- **On-demand (C2):** No background saves - autosave triggered by user actions
- **Auditable (C4):** All wizard state changes are versioned with `wizard_state_version`
- **Multi-tenant (C6):** All queries filtered by `tenant_id`

## Known Issues

None at this time.

## Related Documentation

- [Blueprint Specification](./blueprint.md)
- [Project Specification](./project.md)
- [Tech Stack](./techstack.md)

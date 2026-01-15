# Blueprint v3 Implementation Plan

> **Created**: 2026-01-16
> **Branch**: `fix/blueprint-v3-enforcement`
> **Status**: COMPLETED (Frontend) - Backend integration pending for PHASE 5

---

## Executive Summary

This document outlines the implementation plan to bring the AgentVerse platform into full compliance with `docs/blueprint_v3.md`. The goal is to enforce the "Wizard-only Blueprint" pattern where all goal clarification and blueprint generation happens ONLY in the Create Project wizard.

---

## Current Violations Found

### V1: Feature Flag Not Enforced in Production
**Location**: `apps/web/src/lib/feature-flags.ts:23-24`
```typescript
BLUEPRINT_V2_WIZARD: process.env.NEXT_PUBLIC_BLUEPRINT_V2_WIZARD === 'true' ||
  process.env.NODE_ENV === 'development'
```
**Issue**: In production, `NODE_ENV !== 'development'`, so the flag requires explicit `NEXT_PUBLIC_BLUEPRINT_V2_WIZARD=true` in environment variables. If not set, production users see legacy Step 1 (plain textarea).

### V2: Overview Page Has "Start Goal Analysis" Button
**Location**: `apps/web/src/app/p/[projectId]/overview/page.tsx:296-338`
- Lines 296-338: Renders "Start Goal Analysis" CTA when no blueprint exists
- Line 319: Button triggers `handleStartGoalAnalysis` function
- Lines 138-152: `handleStartGoalAnalysis` creates blueprint and starts goal analysis from Overview

### V3: Overview Page Renders ClarifyPanel
**Location**: `apps/web/src/app/p/[projectId]/overview/page.tsx:350-355`
```tsx
{blueprint && blueprint.is_draft && (
  <div className="max-w-2xl mb-6">
    <ClarifyPanel projectId={projectId} />
  </div>
)}
```
**Issue**: Q&A/clarification should NEVER happen on Overview page per blueprint_v3.

### V4: Project Can Be Created Without Finalized Blueprint
**Location**: `apps/web/src/app/dashboard/projects/new/page.tsx:432-493`
- Project is created first (`createProjectMutation.mutateAsync`)
- Blueprint creation is attempted after and wrapped in try/catch that continues on failure
- No validation that blueprint exists and is finalized before project creation

### V5: Job Deduplication Missing
**Issue**: No idempotent job keys or duplicate job prevention visible in the API routes or hooks. Multiple clicks on "Analyze Goal" can potentially create duplicate jobs.

### V6: GuidancePanel Coverage Incomplete
**Issue**: GuidancePanel exists in v2 components but may not be rendered across ALL project sections listed in blueprint_v3.

---

## Implementation Phases

### PHASE 0 — PREPARATION ✅ COMPLETED
- [x] Read `docs/blueprint_v3.md` fully
- [x] Create branch `fix/blueprint-v3-enforcement`
- [x] Create this implementation plan

---

### PHASE 1 — P0 FIXES ✅ COMPLETED

#### Task 1.1: Enforce v3 Wizard in Production
**Files to modify**:
- `apps/web/src/lib/feature-flags.ts`

**Changes**:
1. Remove the feature flag entirely OR make v2 wizard always-on
2. Add production guardrail that logs/blocks if legacy path is attempted

**Acceptance Test**:
- [ ] In production, Step 1 shows GoalAssistantPanel after 10+ chars

---

#### Task 1.2: Remove Overview Violations
**Files to modify**:
- `apps/web/src/app/p/[projectId]/overview/page.tsx`

**Changes**:
1. Remove "Start Goal Analysis" button block (lines 296-338)
2. Remove ClarifyPanel rendering (lines 350-355)
3. Remove `handleStartGoalAnalysis` callback function (lines 138-152)
4. Remove `createBlueprintMutation` hook import and usage
5. Keep only read-only content: summary, checklist, alignment score, stats

**Acceptance Test**:
- [ ] Overview has no "Start Goal Analysis" CTA
- [ ] Overview has no ClarifyPanel
- [ ] Overview shows read-only blueprint summary when available

---

#### Task 1.3: Enforce Blueprint Requirement for Project Creation
**Files to modify**:
- `apps/web/src/app/dashboard/projects/new/page.tsx`

**Changes**:
1. Modify `handleCreate` to validate `blueprintDraft` exists before creating project
2. Show clear error if blueprint is missing in Step 4
3. Ensure wizard cannot proceed to Step 4 unless blueprint preview is ready
4. Update validation logic in `isStepValid` if needed

**Backend Changes** (if needed):
- `apps/api/app/api/v1/endpoints/project_specs.py` - Add validation that blueprint exists

**Acceptance Test**:
- [ ] Attempting create without blueprint shows error
- [ ] Normal path creates project with blueprint v1 finalized

---

### PHASE 2 — JOB DEDUPLICATION ✅ COMPLETED

#### Task 2.1: Implement Idempotent Job Keys
**Files to modify**:
- `apps/web/src/app/api/goal-analysis/route.ts`
- `apps/web/src/app/api/blueprint-draft/route.ts`
- `apps/web/src/components/pil/v2/GoalAssistantPanel.tsx`

**Changes**:
1. Add job deduplication logic using `projectId + jobType` as key
2. Check if existing job is queued/running before creating new one
3. Store job reference in component state to prevent duplicate triggers

**Acceptance Test**:
- [ ] Multiple clicks on "Analyze Goal" creates only one job
- [ ] Returning to wizard shows existing job status

---

### PHASE 3 — WIZARD STEP 1 STATE MACHINE ✅ COMPLETED

#### Task 3.1: Implement Resume Behavior
**Files to modify**:
- `apps/web/src/components/pil/v2/GoalAssistantPanel.tsx`
- `apps/web/src/app/dashboard/projects/new/page.tsx`

**Changes**:
1. Add state persistence for wizard step 1 (localStorage or session)
2. Check for existing job/analysis on component mount
3. Show current status instead of restarting
4. Add exit confirmation modal with "Save Draft" option

**Acceptance Test**:
- [ ] Refresh page shows current job status
- [ ] Navigate away and back shows current state
- [ ] Exit modal appears if analysis in progress

---

### PHASE 4 — GUIDANCE PANEL COVERAGE ✅ COMPLETED

#### Task 4.1: Add GuidancePanel to All Project Sections
**Files to modify**:
- All project section pages in `apps/web/src/app/p/[projectId]/`

**Sections requiring GuidancePanel**:
1. Overview (read-only summary - optional)
2. Data & Personas (`data-personas/page.tsx`)
3. Rules & Assumptions (`rules/page.tsx`)
4. Run Center (`run-center/page.tsx`)
5. Universe Map (`universe-map/page.tsx`)
6. Event Lab (`event-lab/page.tsx`)
7. Society Simulation (`society/page.tsx`)
8. Target Planner (`target-planner/page.tsx`)
9. Reliability (`reliability/page.tsx`)
10. Telemetry & Replay (`telemetry/page.tsx`)
11. 2D World Viewer (`vi-world/page.tsx`)
12. Reports (`reports/page.tsx`)
13. Settings (`settings/page.tsx`)
14. Calibration Lab (`calibration-lab/page.tsx`)

**Acceptance Test**:
- [ ] Navigate to each section and GuidancePanel is visible
- [ ] GuidancePanel shows section-specific tasks from blueprint

---

### PHASE 5 — CHECKLIST WITH ALERTS ✅ FRONTEND COMPLETE (Backend pending)

#### Task 5.1: Implement Real Checklist Status
**Files to modify**:
- `apps/web/src/components/pil/BlueprintChecklist.tsx` ✅ (Frontend ready)
- Backend slot pipeline endpoints ⏳ (Pending backend implementation)

**Frontend Status (COMPLETE)**:
- BlueprintChecklist component fully supports AlertState (ready, needs_attention, blocked, not_started)
- Status summary pills show counts per state
- Progress bar and completion tracking
- Missing items display with visual indicators
- Next action suggestions with navigation links
- Match score display for alignment

**Backend Work Required**:
1. Connect checklist items to real artifact/job outputs
2. Implement status transitions: NOT_STARTED → PROCESSING → READY/NEEDS_ATTENTION/BLOCKED
3. Trigger slot pipeline jobs on artifact upload

**Acceptance Test**:
- [x] Frontend displays checklist with all status states (mock data works)
- [ ] Checklist items show real status from job outputs (needs backend)
- [ ] Upload artifact triggers automatic status transition (needs backend)

---

### PHASE 6 — LOADING ARCHITECTURE ✅ COMPLETED

#### Task 6.1: Global Active Jobs Widget
**Files modified**:
- `apps/web/src/components/pil/ActiveJobsBanner.tsx` ✅
- `apps/web/src/app/dashboard/layout.tsx` ✅ (Already had banner)
- `apps/web/src/app/p/[projectId]/layout.tsx` ✅ (Banner added)

**Changes Implemented**:
1. ActiveJobsBanner visible in dashboard layout
2. ActiveJobsBanner added to project workspace layout
3. Shows active jobs with progress indicators
4. Links to Job Center for details

**Acceptance Test**:
- [x] Active jobs visible while navigating dashboard
- [x] Active jobs visible while navigating project workspace
- [x] Jobs persist across page refreshes

---

## Test Checkpoints

### Checkpoint 1: P0 Fixes Complete ✅
- [x] Feature flag removed or always-on (BLUEPRINT_V2_WIZARD hardcoded to true)
- [x] Overview is read-only (no Q&A, no Start Analysis)
- [x] Project creation requires blueprint (enforced in wizard Step 4)

### Checkpoint 2: Job System Robust ✅
- [x] No duplicate jobs created (deduplication via localStorage tracking)
- [x] Jobs resume after navigation (state machine in GoalAssistantPanel)

### Checkpoint 3: Full Coverage ✅
- [x] GuidancePanel in all 15 project sections
- [ ] Checklist driven by real data (pending backend)

### Checkpoint 4: Production Ready
- [ ] Chrome console shows 0 errors (pending staging test)
- [ ] No 4xx/5xx bursts (pending staging test)
- [ ] All smoke tests pass in staging (pending staging test)

---

## Rollback Strategy

If issues arise:
1. Feature flag can be re-enabled temporarily
2. Overview violations can be restored from git history
3. All changes are on a separate branch until verified

---

## Files Summary

| File | Changes |
|------|---------|
| `apps/web/src/lib/feature-flags.ts` | Remove/modify flag |
| `apps/web/src/app/p/[projectId]/overview/page.tsx` | Remove violations |
| `apps/web/src/app/dashboard/projects/new/page.tsx` | Enforce blueprint |
| `apps/web/src/components/pil/v2/GoalAssistantPanel.tsx` | Job dedup, resume |
| `apps/web/src/app/api/goal-analysis/route.ts` | Job dedup |
| All project section pages | Add GuidancePanel |
| `apps/web/src/components/pil/BlueprintChecklist.tsx` | Real status |
| `apps/web/src/app/p/[projectId]/layout.tsx` | Add ActiveJobsBanner |
| `apps/web/src/components/pil/GuidancePanel.tsx` | Add all 16 section configs |

---

## Completion Summary

**Date Completed**: 2026-01-16
**Branch**: `fix/blueprint-v3-enforcement`

### Frontend Work Complete

| Phase | Status | Notes |
|-------|--------|-------|
| PHASE 0 | ✅ Complete | Planning & branch setup |
| PHASE 1 | ✅ Complete | P0 fixes - wizard enforced, overview read-only |
| PHASE 2 | ✅ Complete | Job deduplication with localStorage tracking |
| PHASE 3 | ✅ Complete | Wizard Step 1 state machine with resume |
| PHASE 4 | ✅ Complete | GuidancePanel in all 15 project pages |
| PHASE 5 | ✅ Frontend | Backend integration pending |
| PHASE 6 | ✅ Complete | ActiveJobsBanner in layouts |

### Files Modified (Summary)

**Core Feature Flags**:
- `feature-flags.ts` - BLUEPRINT_V2_WIZARD hardcoded true

**Overview Page**:
- Removed "Start Goal Analysis" CTA
- Removed ClarifyPanel
- Removed createBlueprintMutation
- Added GuidancePanel

**Project Wizard**:
- Enforced blueprint requirement in Step 4
- Job deduplication in GoalAssistantPanel
- State persistence with localStorage

**GuidancePanel Coverage**:
- 15 project pages with GuidancePanel
- 16 section configurations in SECTION_CONFIG

**Loading Architecture**:
- ActiveJobsBanner in dashboard layout
- ActiveJobsBanner in project layout

### Next Steps (Backend)

1. Implement real checklist status from job outputs
2. Implement slot pipeline status transitions
3. Connect artifact uploads to automatic status updates

# Blueprint v2 Migration Progress

**Started:** 2026-01-16
**Status:** In Progress (Phase A, B, C, D, E Complete)
**Feature Flag:** `BLUEPRINT_V2_WIZARD`

---

## Phase A — Fix the Misplacement (MUST DO FIRST) ✅ COMPLETE

| Task | Status | Notes |
|------|--------|-------|
| Create `/api/goal-analysis` route (no project_id required) | ✅ DONE | `apps/web/src/app/api/goal-analysis/route.ts` |
| Create `/api/blueprint-draft` route | ✅ DONE | `apps/web/src/app/api/blueprint-draft/route.ts` |
| Create feature flags configuration | ✅ DONE | `apps/web/src/lib/feature-flags.ts` |
| Create GoalAssistantPanel v2 component | ✅ DONE | `apps/web/src/components/pil/v2/GoalAssistantPanel.tsx` |
| Create shared Blueprint v2 types | ✅ DONE | `apps/web/src/types/blueprint-v2.ts` |
| Update wizard page to use v2 flow | ✅ DONE | `apps/web/src/app/dashboard/projects/new/page.tsx` |
| Ensure Step 1 Goal wizard owns flow end-to-end (Analyze → Clarify → Blueprint Preview) | ✅ DONE | GoalAssistantPanel handles full flow |
| Add anti-misplacement constraint: Overview must never host initial clarification | ✅ DONE | v2 flag skips clarification on Overview |

**Files Created/Modified in Phase A:**
- `apps/web/src/app/api/goal-analysis/route.ts` - NEW
- `apps/web/src/app/api/blueprint-draft/route.ts` - NEW
- `apps/web/src/lib/feature-flags.ts` - NEW
- `apps/web/src/components/pil/v2/GoalAssistantPanel.tsx` - NEW
- `apps/web/src/components/pil/v2/index.ts` - NEW
- `apps/web/src/types/blueprint-v2.ts` - NEW
- `apps/web/src/app/dashboard/projects/new/page.tsx` - MODIFIED

---

## Phase B — Draft + Blueprint Models + Versioning ✅ COMPLETE

| Task | Status | Notes |
|------|--------|-------|
| DraftProject model: stores goal text, clarification answers, cutoff draft, chosen core draft, blueprint_draft content | ✅ DONE | Using localStorage for now (B.3) |
| Blueprint model: versioned, auditable | ✅ DONE | Existing model at `apps/api/app/models/blueprint.py` |
| Project links to Blueprint v1 at creation | ✅ DONE | Via `skip_clarification` flag in v2 flow |
| Exit/cancel confirmation modal with Save Draft/Discard Draft | ✅ DONE | Radix Dialog modal in wizard page |
| Draft persistence to localStorage | ✅ DONE | Saves on "Save Draft & Exit" |
| Browser beforeunload warning | ✅ DONE | Warns if unsaved draft state |

**Files Created/Modified in Phase B:**
- `apps/web/src/app/dashboard/projects/new/page.tsx` - MODIFIED (exit modal, draft persistence)

---

## Phase C — Background Jobs + Progress + Job Center ✅ COMPLETE

| Task | Status | Notes |
|------|--------|-------|
| Job queue, job logs, progress reporting | ✅ DONE | Existing PILJob model + Celery tasks |
| Inline loading widget + global notifications | ✅ DONE | PILJobProgress component + toast notifications |
| Runs & Jobs becomes Job Center | ✅ DONE | Tabbed page at `/dashboard/runs` |
| Jobs persist across refresh | ✅ DONE | React Query auto-polling every 3s |
| Filter by project works | ✅ DONE | Project dropdown filter for PIL jobs |
| Artifacts accessible from jobs | ✅ DONE | View Artifacts button in job rows |

**Files Created/Modified in Phase C:**
- `apps/web/src/app/dashboard/runs/page.tsx` - MODIFIED (transformed to Job Center with tabs)
- `apps/web/src/app/dashboard/layout.tsx` - MODIFIED (added ActiveJobsBanner to layout)
- Uses existing: `apps/web/src/components/pil/PILJobProgress.tsx` (inline progress)
- Uses existing: `apps/web/src/components/pil/ActiveJobsBanner.tsx` (global banner)
- Uses existing: `apps/web/src/hooks/useApi.ts` (usePILJobs, useActivePILJobs hooks)

---

## Phase D — Blueprint-Driven Guidance Across ALL Sections ✅ MOSTLY COMPLETE

| Task | Status | Notes |
|------|--------|-------|
| Guidance Panel component used in every section | ✅ DONE | `apps/web/src/components/pil/v2/GuidancePanel.tsx` |
| Section tasks come from blueprint section map | ✅ DONE | Uses `useActiveBlueprint` + filters by `section_id` |
| Checklist updates reflect real artifacts | ✅ DONE | Status colors: ready=green, blocked=red, needs_attention=yellow |

**Sections implemented with GuidancePanel:**
- [x] Overview - `/projects/[id]/page.tsx` (section="overview")
- [x] Data & Personas (Inputs) - `/projects/[id]/personas/page.tsx` (section="inputs")
- [x] Run Center / Hybrid Mode - `/projects/[id]/hybrid-mode/page.tsx` (section="runs")
- [x] Universe Map - `/projects/[id]/universe-map/page.tsx` (section="universe")
- [x] Society Simulation - `/projects/[id]/society-mode/page.tsx` (section="society")
- [x] Target Planner - `/projects/[id]/target-mode/page.tsx` (section="target")
- [x] Reliability - `/projects/[id]/reliability/page.tsx` (section="reliability")
- [x] Telemetry & Replay - `/projects/[id]/replay/page.tsx` (section="telemetry")
- [x] Reports / Exports - `/projects/[id]/exports/page.tsx` (section="reports")
- [x] Settings - `/projects/[id]/settings/page.tsx` (section="settings")
- [ ] Event Lab (scenarios) - Not a dedicated page, handled within scenarios flow
- [ ] Rules & Assumptions - Not a dedicated page yet
- [ ] 2D World Viewer - Embedded in replay/universe components
- [ ] Library pages - Separate from project context
- [ ] Calibration Lab - Separate from project context

**Files Modified in Phase D:**
- `apps/web/src/components/pil/v2/GuidancePanel.tsx` - NEW
- `apps/web/src/components/pil/v2/index.ts` - MODIFIED (added export)
- `apps/web/src/app/dashboard/projects/[id]/page.tsx` - MODIFIED
- `apps/web/src/app/dashboard/projects/[id]/personas/page.tsx` - MODIFIED
- `apps/web/src/app/dashboard/projects/[id]/hybrid-mode/page.tsx` - MODIFIED
- `apps/web/src/app/dashboard/projects/[id]/universe-map/page.tsx` - MODIFIED
- `apps/web/src/app/dashboard/projects/[id]/society-mode/page.tsx` - MODIFIED
- `apps/web/src/app/dashboard/projects/[id]/target-mode/page.tsx` - MODIFIED
- `apps/web/src/app/dashboard/projects/[id]/reliability/page.tsx` - MODIFIED
- `apps/web/src/app/dashboard/projects/[id]/replay/page.tsx` - MODIFIED
- `apps/web/src/app/dashboard/projects/[id]/exports/page.tsx` - MODIFIED
- `apps/web/src/app/dashboard/projects/[id]/settings/page.tsx` - MODIFIED

---

## Phase E — Slot Pipeline (validate → summarize → fit → compile) ✅ COMPLETE

| Task | Status | Notes |
|------|--------|-------|
| Implement slot artifacts store | ✅ DONE | Using existing PILArtifact model with ArtifactType enum |
| Every slot update triggers jobs and persists results | ✅ DONE | `fulfill_slot` endpoint triggers all 4 pipeline jobs |
| Programmatic validation job | ✅ DONE | `slot_validation_task` in `pil_tasks.py` |
| AI Summary job | ✅ DONE | `slot_summarization_task` with LLMRouter |
| Fit Score job | ✅ DONE | `slot_alignment_scoring_task` with multi-factor scoring |
| Compilation job | ✅ DONE | `slot_compilation_task` for data transformation |

**Files Modified in Phase E:**
- `apps/api/app/tasks/pil_tasks.py` - Added slot_summarization_task, slot_alignment_scoring_task, slot_compilation_task + updated dispatch function
- `apps/api/app/api/v1/endpoints/blueprints.py` - Updated fulfill_slot to trigger full pipeline

---

## Phase F — Chrome Testing + Deployment Readiness

### 9.1 Create Project (MUST)
| Test | Status | Notes |
|------|--------|-------|
| Step 1 Analyze triggers background job, UI shows progress, no blocking | PENDING | |
| Clarify Q&A is shown in Step 1 and produces Blueprint Preview | PENDING | |
| Skip Clarify generates blueprint draft and allows Next | PENDING | |
| Exiting wizard shows confirm modal; discard removes draft | PENDING | |
| Project creation produces Blueprint v1 (versioned) + locks temporal context | PENDING | |

### 9.2 Overview (MUST)
| Test | Status | Notes |
|------|--------|-------|
| Overview shows blueprint summary (read-only) | PENDING | |
| Overview does NOT ask clarifying questions for initial blueprint | PENDING | |
| Checklist reflects blueprint tasks and alert statuses | PENDING | |

### 9.3 Sections (MUST)
| Test | Status | Notes |
|------|--------|-------|
| Every section displays a Guidance Panel and task status | PENDING | |
| Any slot update triggers validation + summary + fit + compile jobs | PENDING | |
| Inline progress widgets update during processing | PENDING | |

### 9.4 Job Center (MUST)
| Test | Status | Notes |
|------|--------|-------|
| Jobs persist after refresh | PENDING | |
| Filter by project works | PENDING | |
| Artifacts accessible from jobs | PENDING | |

### 9.5 Deployment Readiness
| Test | Status | Notes |
|------|--------|-------|
| No Chrome console errors on core flows | PENDING | |
| Background jobs stable under concurrency | PENDING | |
| All acceptance tests pass | PENDING | |

---

## Decisions & Rationale

| Decision | Rationale | Date |
|----------|-----------|------|
| Use feature flag `BLUEPRINT_V2_WIZARD` | Controlled migration, no breaking changes to production | 2026-01-16 |
| Keep v1 code in `legacy_blueprint_v1/` | Safe rollback path if issues arise | 2026-01-16 |

---

## Known Risks

| Risk | Mitigation |
|------|------------|
| Database migrations may affect existing projects | Create migrations that preserve existing data |
| Background jobs may fail mid-wizard | Implement robust draft persistence |
| Concurrent job execution issues | Use proper job locking and state management |

---

## Evidence for Acceptance Criteria

### 1) Step 1 Goal shows progress + Q&A + Blueprint Preview
- Screenshot: PENDING
- Notes: PENDING

### 2) Overview contains NO initial Q&A/clarification flow
- Screenshot: PENDING
- Notes: PENDING

### 3) Jobs persist across refresh and show progress in Job Center
- Screenshot: PENDING
- Notes: PENDING

### 4) Section Guidance Panel appears across ALL sections
- Screenshot: PENDING
- Notes: PENDING

---

## Chrome Console Error Log

| Page | Errors | Status |
|------|--------|--------|
| Create Project Wizard | PENDING | |
| Overview | PENDING | |
| Inputs | PENDING | |
| Rules | PENDING | |
| Event Lab | PENDING | |
| Job Center | PENDING | |

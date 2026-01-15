# Blueprint v2 Migration Progress

**Started:** 2026-01-16
**Status:** In Progress (Phase A Complete)
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

## Phase B — Draft + Blueprint Models + Versioning

| Task | Status | Notes |
|------|--------|-------|
| DraftProject model: stores goal text, clarification answers, cutoff draft, chosen core draft, blueprint_draft content | PENDING | |
| Blueprint model: versioned, auditable | PENDING | Existing model at `apps/api/app/models/blueprint.py` |
| Project links to Blueprint v1 at creation | PENDING | |
| Exit/cancel confirmation modal with Save Draft/Discard Draft | PENDING | |

---

## Phase C — Background Jobs + Progress + Job Center

| Task | Status | Notes |
|------|--------|-------|
| Job queue, job logs, progress reporting | PENDING | Existing PILJob model |
| Inline loading widget + global notifications | PENDING | |
| Runs & Jobs becomes Job Center | PENDING | |
| Jobs persist across refresh | PENDING | |
| Filter by project works | PENDING | |
| Artifacts accessible from jobs | PENDING | |

---

## Phase D — Blueprint-Driven Guidance Across ALL Sections

| Task | Status | Notes |
|------|--------|-------|
| Guidance Panel component used in every section | PENDING | |
| Section tasks come from blueprint section map | PENDING | |
| Checklist updates reflect real artifacts | PENDING | |

**Sections to implement guidance:**
- [ ] Overview
- [ ] Data & Personas (Inputs)
- [ ] Rules & Assumptions
- [ ] Run Center
- [ ] Universe Map
- [ ] Event Lab
- [ ] Society Simulation
- [ ] Target Planner
- [ ] Reliability
- [ ] Telemetry & Replay
- [ ] 2D World Viewer
- [ ] Reports
- [ ] Settings
- [ ] Library (Personas Library, Templates, Rulesets, Evidence Source)
- [ ] Calibration Lab

---

## Phase E — Slot Pipeline (validate → summarize → fit → compile)

| Task | Status | Notes |
|------|--------|-------|
| Implement slot artifacts store | PENDING | |
| Every slot update triggers jobs and persists results | PENDING | |
| Programmatic validation job | PENDING | |
| AI Summary job | PENDING | |
| Fit Score job | PENDING | |
| Compilation job | PENDING | |

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

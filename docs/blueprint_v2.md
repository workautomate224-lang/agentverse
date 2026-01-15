# blueprint_v2.md — Goal-to-Blueprint Wizard + Blueprint-Orchestrated Project (Production Spec)
Version: v2.0 (Fixes: **Goal/Clarify/Blueprint MUST happen inside Create Project wizard Step 1** — never on Overview)

> This document defines the **exact** user-visible behavior + backend logic for a blueprint-driven predictive/simulation platform.
> It is written to prevent “wrong placement” implementations (e.g., moving goal clarification to Overview).

---

## 0) Definition of Terms (So the build cannot drift)
### 0.1 Draft Project vs Project
- **Draft Project**: a temporary, not-yet-created project state while the user is in the Create Project wizard.
  - Can store partially completed inputs (goal text, clarification answers, cutoff date).
  - Can run AI jobs (goal analysis/blueprint draft) in the background.
  - Can be saved as “Draft” or discarded.

- **Project**: a fully created project record that users see in Projects list and can run simulations on.
  - **Must have**: a **finalized Blueprint v1** (blueprint_version=1) and a **Temporal Context** set.
  - A Project can later have Blueprint v2/v3… via explicit “Rebuild Blueprint” actions.

**Hard Rule:** A Project cannot be created without a Blueprint v1.

### 0.2 Blueprint
A **Blueprint** is a versioned, auditable plan that:
- Defines what inputs are required/recommended
- Defines tasks per section
- Defines validations, summaries, and readiness criteria
- Drives UI guidance and checklist statuses

---

## 1) The Big Guarantee (What the user should feel)
Users type a goal once. The system then:
1) Asks structured clarifying questions (optional, skippable)
2) Produces a Blueprint draft preview
3) Finalizes Blueprint v1 during Create Project wizard
4) After creation, each section shows **task guidance** + **AI-powered validation & summaries** + **progress**—without blocking navigation.

---

## 2) FRONTEND UX — Exact Screens & Where They Must Live
## 2.1 Create Project Wizard (Where Goal/Clarify/Blueprint MUST happen)
Wizard steps (fixed positions):
1) **Goal**  ✅ (goal analysis + clarification + blueprint preview happens HERE)
2) **Temporal** ✅ (cutoff date set here; updates blueprint constraints)
3) **Pick Core** ✅ (manual selection; blueprint stores chosen core)
4) **Setup** ✅ (name/tags; final “Create Project” commit)

### 2.1.1 Step 1: Goal — REQUIRED behavior
UI elements:
- Goal text box (existing)
- Buttons:
  - **Analyze Goal** (starts background Goal Analysis job)
  - **Skip Clarify & Generate Blueprint** (forces blueprint draft from goal text alone)
  - **Save Draft** (optional)
  - Next (disabled until Blueprint Preview is available OR user used Skip)

**What happens when user clicks Analyze Goal**
- Start background job: `job.goal_analysis`
- Show a right-side or inline **Goal Assistant panel**:
  - “Understanding your goal… [progress bar + stage]”
  - then show **Clarifying Questions** (structured)

**Clarifying Questions rules**
- 3–8 questions max unless user explicitly requests “ask me more”
- Each question is structured (single-select/multi-select/short text)
- Each question includes: “Why we ask this”

After answers:
- Start background job: `job.blueprint_draft_build`
- Show **Blueprint Preview** (must render before leaving Step 1):
  - Goal Summary
  - Domain Guess
  - Output Type
  - Required Slots (top 3–7)
  - Recommended Slots (collapsed)
  - Section Task Preview (high-level)

**Hard Rule (Anti-misplacement):**
- Step 1 is the only place where the user is asked clarifying questions for initial blueprint generation.
- Overview must never contain the initial clarification flow.

### 2.1.2 Step 1 Exit/Cancel modal (non-saving)
If user tries to leave the wizard while:
- there is unsaved draft state, or
- any goal/blueprint job is running

Show confirmation modal:
- “Leave setup? Your draft will not be saved unless you click Save Draft.”
Options:
- Save Draft & Exit
- Discard Draft & Exit (cancels/marks jobs as cancelled)
- Continue Setup

### 2.1.3 Step 2: Temporal (cutoff date)
- User sets cutoff date (already implemented).
- On save, start background job: `job.temporal_apply`:
  - updates blueprint constraints (e.g., data windows required)
  - validates all future AI research uses this cutoff

### 2.1.4 Step 3: Pick Core
- Keep existing manual selection UI.
- On selection, start background job: `job.blueprint_finalize_core`:
  - stores the chosen core into the blueprint draft
  - updates section tasks if needed

### 2.1.5 Step 4: Setup (final commit)
- User sets project name/tags etc.
- Clicking **Create Project** commits:
  - create Project record
  - create Blueprint v1 record (finalized) from the draft
  - link: project.blueprint_version = 1
  - lock temporal context for the project

---

## 2.2 Project Overview (After creation) — what it is and what it is NOT
**Overview is NOT** where initial goal clarification or blueprint creation happens.

Overview MUST show:
- Blueprint Summary card (read-only):
  - goal_summary, domain_guess, output_type, horizon/scope
  - blueprint_version + created_at
- Dynamic Setup Checklist (from blueprint tasks)
- Global health metrics:
  - “Inputs readiness”
  - “Calibration readiness”
  - “Runs status”
- CTA buttons:
  - “Go to Inputs”
  - “Run Baseline”

Optional: “Rebuild Blueprint” action (explicit, versioned, audited).

---

## 2.3 All Project Sections (Blueprint-driven guidance everywhere)
Every section page must have:
1) **Guidance Panel** (from blueprint section tasks)
2) **Slot Status** (required/recommended/optional)
3) **Action Buttons** (AI Research / AI Generate / Manual Add / Connect Source)
4) **AI Artifacts** (Summary + Fit Score + Validation results)
5) **Inline Loading Widget** for any running job (progress bar + stage)

Sections that MUST be covered (match your nav):
- Overview
- Data & Personas (Inputs)
- Rules & Assumptions
- Run Center
- Universe Map
- Event Lab
- Society Simulation
- Target Planner
- Reliability
- Telemetry & Replay
- 2D World Viewer
- Reports
- Settings
- Library (Personas Library, Templates, Rulesets, Evidence Source)
- Calibration Lab (if present)

---

## 3) NON-BLOCKING LOADING ARCHITECTURE (Background AI Jobs)
### 3.1 User requirement
When AI is processing:
- user can navigate anywhere
- progress is visible
- results appear when ready
- nothing is “frozen” behind a blocking modal

### 3.2 Required UI elements
- Inline loading widget per section/task:
  - progress bar (0–100)
  - stage label
  - last update time
- Global notifications:
  - “Blueprint ready”
  - “Slot validated”
  - “Needs attention: weak match”
- “Runs & Jobs” acts as the Job Center:
  - filter by project
  - view job logs
  - view artifacts
  - retry/cancel when safe

### 3.3 Job state machine
- queued → running → succeeded | failed | cancelled
- Each job stores:
  - progress_percent
  - stage_name
  - artifact pointers (summary/validation/compiled outputs)

---

## 4) BLUEPRINT CONTENT (Must be executable, not decorative)
Blueprint is structured JSON (versioned) with these minimum blocks:

### 4.1 Project Profile
- goal_text, goal_summary
- domain_guess
- output_type (distribution/point/ranked/paths)
- horizon (time window + granularity)
- scope (geography/entity)
- success_metrics (what to evaluate)

### 4.2 Strategy
- chosen_core (collective/targeted/hybrid)
- primary_drivers (population/timeseries/constraints/events/network/sentiment/mixed)
- required_modules (population synthesis, timeseries forecaster, scenario engine, calibration suite, universe map, etc.)

### 4.3 Input Slots Contract
Each slot defines:
- required_level: required / recommended / optional
- schema_requirements (fields/types)
- temporal_requirements (timestamp required? must be <= cutoff?)
- quality_requirements (coverage thresholds)
- acquisition methods (manual/API/research/generate/snapshot)
- validation_plan
- derived_artifacts

### 4.4 Section Task Map (ALL sections)
For each section_id, blueprint provides tasks:
- title, why_it_matters
- linked_slots
- action buttons to fulfill
- completion criteria (artifact must exist)
- alert rules

### 4.5 Calibration Plan
- labels needed
- backtest windows
- evaluation metrics

### 4.6 Universe/Branch Plan
- branchable variables
- probability aggregation policy
- node metadata requirements

### 4.7 Policy + Audit
- blueprint_version
- created_at/by
- policy_version
- clarification_answers

---

## 5) INPUTS & PROCESSING (Every input triggers AI processing)
### 5.1 Inputs are “Slots”
Even if UI says “Personas”, internally it’s a slot.

### 5.2 Mandatory pipeline when user adds/updates slot data
Every slot update triggers background jobs:
1) **Programmatic Validation** (schema/timestamps/dedupe/coverage)
2) **AI Summary** (“what is this data?”)
3) **Fit Score** (“how well does it match project goal + blueprint requirements?”)
4) **Compilation** (feature store/persona store/graph/time series transforms)

**Hard Rule:** Checklist cannot mark a slot/task complete without artifacts from steps 1–4.

---

## 6) CHECKLIST + ALERTS (Not just yes/no)
Checklist status for each section task:
- ✅ Ready
- 🟡 Needs Attention (weak fit/low coverage)
- 🔴 Blocked (missing required slot or failed validation)
- ⚪ Not Started
- 🔵 Processing (jobs running)

Each checklist item shows:
- current status + reason
- latest AI summary snippet
- fit score
- next action button

---

## 7) STRONG PROMPTS (LLM usage; no code here, but strict behavior)
### 7.1 Goal Analyzer (Clarification)
- Role: Project Formulation Expert
- Ask only questions that change blueprint structure.
- Prefer structured answers.
- Must output:
  - goal_summary
  - domain_guess
  - output_type, horizon, scope
  - drivers guess
  - missing critical inputs list

### 7.2 Blueprint Draft Builder
- Takes goal + clarifications + cutoff + chosen core
- Produces blueprint draft with slot contract + section tasks for ALL sections.

### 7.3 Slot Summarizer + Fit Scorer
- Summarize input data/evidence.
- Compare against blueprint slot requirements and project goal.
- Return:
  - summary
  - fit_score (0–100) + reasons
  - missing fields/coverage gaps
  - recommended next slot(s)

### 7.4 Section Guidance Generator
- Converts blueprint tasks into UI-ready guidance cards (short, actionable).

---

## 8) WORK BREAKDOWN CHECKLIST (Engineering Tasks)
### Phase A — Fix the misplacement (must do first)
- [ ] Remove/disable any “Goal clarification / blueprint generation” flow from Project Overview.
- [ ] Ensure Step 1 Goal wizard owns the flow end-to-end (Analyze → Clarify → Blueprint Preview).

### Phase B — Draft + Blueprint models + versioning
- [ ] DraftProject model: stores goal text, clarification answers, cutoff draft, chosen core draft, blueprint_draft content
- [ ] Blueprint model: versioned, auditable
- [ ] Project links to Blueprint v1 at creation

### Phase C — Background jobs + progress + Job Center
- [ ] Job queue, job logs, progress reporting
- [ ] Inline loading widget + global notifications
- [ ] Runs & Jobs becomes Job Center

### Phase D — Blueprint-driven guidance across ALL sections
- [ ] Guidance Panel component used in every section
- [ ] Section tasks come from blueprint section map
- [ ] Checklist updates reflect real artifacts

### Phase E — Slot pipeline (validate → summarize → fit → compile)
- [ ] Implement slot artifacts store
- [ ] Ensure every slot update triggers jobs and persists results

### Phase F — Chrome testing + deployment readiness
(see section 9)

---

## 9) TESTING (Chrome-first) — Acceptance Criteria
### 9.1 Create Project (must)
- [ ] Step 1 Analyze triggers background job, UI shows progress, no blocking
- [ ] Clarify Q&A is shown in Step 1 and produces Blueprint Preview
- [ ] Skip Clarify generates blueprint draft and allows Next
- [ ] Exiting wizard shows confirm modal; discard removes draft
- [ ] Project creation produces Blueprint v1 (versioned) + locks temporal context

### 9.2 Overview (must)
- [ ] Overview shows blueprint summary (read-only)
- [ ] Overview does NOT ask clarifying questions for initial blueprint
- [ ] Checklist reflects blueprint tasks and alert statuses

### 9.3 Sections (must)
- [ ] Every section listed in 2.3 displays a Guidance Panel and task status
- [ ] Any slot update triggers validation + summary + fit + compile jobs
- [ ] Inline progress widgets update during processing

### 9.4 Job Center (must)
- [ ] Jobs persist after refresh
- [ ] Filter by project works
- [ ] Artifacts accessible from jobs

### 9.5 Deployment readiness
- [ ] No Chrome console errors on core flows
- [ ] Background jobs stable under concurrency
- [ ] All acceptance tests pass

---
End of blueprint_v2.md

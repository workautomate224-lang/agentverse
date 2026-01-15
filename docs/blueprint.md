# blueprint.md — Blueprint-Driven Project Orchestration (Production Spec)
**Scope:** Implement a **goal-driven, blueprint-orchestrated** workflow across the entire platform, including async AI loading architecture, dynamic per-section guidance, alerting checklist, and full Chrome-based testing & deployment validation.

> This is a **production-level** specification. It assumes the platform is already running in production and will be upgraded (not rebuilt).

---

## 0) Core Idea (Plain English)
Users should be able to type **one goal** (e.g., “GE2026 Malaysia election outcome” or “Forecast next year production volume”), and the platform will:

1. **Clarify the goal** (optional Q&A).
2. **Generate a Project Blueprint** (a versioned, auditable “construction plan”).
3. **Auto-distribute tasks** and AI guidance to **every project section**, not just Data/Personas.
4. Provide **AI-powered validation + summaries** for each input.
5. Run everything using a **non-blocking asynchronous loading system** so users can switch pages while AI work continues.

---

## 1) Non-Negotiable Requirements
### 1.1 Blueprint is the “single source of truth”
- Every project has a **Blueprint (versioned)**.
- Every run references a specific blueprint version.
- Any blueprint change creates a new version and is audit-tracked.

### 1.2 No blocking UI during AI processing
- AI work must run as **background jobs**.
- UI shows **loading widgets with progress** and allows navigation.
- Completed jobs create **summaries + match scores + next-step suggestions**.

### 1.3 Every step is real (not dummy)
- Each checklist item and section “completion” must be backed by a real AI analysis, validation, or data processing job.
- “Complete” status requires the job to finish successfully and produce artifacts (summary, validation report, or compiled outputs).

### 1.4 Exit/Cancel safety on Create Project
- During Goal Clarification, if user exits/cancels, show a confirmation modal.
- If they confirm cancel, discard temporary state (draft) unless explicitly saved.

---

## 2) New Platform Capability: Project Intelligence Layer (PIL)
Implement a production-grade orchestration layer that includes:

1. **Blueprint Builder**
2. **Guidance Generator**
3. **Slot Validator**
4. **Artifact Summarizer**
5. **Checklist/Alert Engine**
6. **Async Job System (Queue + Progress + Notifications)**

Think of PIL as the “brain” that generates and enforces the blueprint.

---

## 3) The Blueprint: What It Must Contain
Blueprint should be stored as a structured object (JSON) with a schema and versioning.

### 3.1 Blueprint fields (minimum)
**A) Project Profile**
- `goal_text`: raw user goal
- `goal_summary`: concise AI-written summary
- `domain_guess`: election / market demand / production forecast / policy impact / perception risk / crime route / personal decision / generic
- `target_outputs`: what outputs are required (distribution, point estimate, ranked outcomes, paths, recommendations)
- `horizon`: time range + granularity (daily/weekly/monthly/event-based)
- `scope`: geography or entity scope (country/state/city/market/product/person)
- `success_metrics`: what “good prediction” means + evaluation metrics

**B) Strategy**
- `recommended_core`: collective / targeted / hybrid (keep existing “Recommended Core” UI; blueprint can store recommendation but UI may remain unchanged for now)
- `primary_drivers`: population / timeseries / network / constraints / events / sentiment / mixed
- `required_modules`: list of enabled engine modules (population synthesis, time series, scenario engine, calibration, universe map, etc.)

**C) Input Slots (Contract)**
A list of slots, each with:
- `slot_id`, `slot_name`, `slot_type` (TimeSeries, Table, EntitySet, Graph, TextCorpus, Labels, Ruleset, AssumptionSet)
- `required_level`: required / recommended / optional
- `schema_requirements`: minimum fields, types, allowed values
- `temporal_requirements`: must have timestamps? must be <= cutoff? required time window?
- `quality_requirements`: missing thresholds, dedupe rules, minimum coverage
- `allowed_acquisition_methods`: manual upload / connect API / AI research / AI generation / snapshot import
- `validation_plan`: how we validate it (AI + programmatic checks)
- `derived_artifacts`: what compiled outputs it produces (features, persona store, graphs, etc.)

**D) Section Task Map**
For every platform section, define:
- `section_id`: overview, inputs, personas, data, rules, run_params, run_center, event_lab, universe_map, reliability, telemetry_replay, 2d_world_viewer, reports, settings (include ALL existing sections)
- `tasks`: a list of tasks:
  - `task_id`, `title`, `why_it_matters`
  - `linked_slots`: which input slots complete this
  - `actions`: AI generate / AI research / manual add / connect source
  - `completion_criteria`: what artifact must exist for completion
  - `alerts`: what to warn about if incomplete or low quality

**E) Calibration + Backtest Plan**
- required historical windows
- labels needed
- evaluation metrics (Brier, MAE/MAPE, calibration curves, rank correlation)
- minimum test suite needed for “ready”

**F) Universe Map / Branching Plan**
- which variables are branchable
- event template suggestions
- probability aggregation policy
- node metadata requirements

**G) Policy + Audit Metadata**
- `blueprint_version`
- `policy_version`
- `created_at`, `created_by`
- `clarification_answers` (if used)
- `constraints_applied` (what policy rules forced)

---

## 4) Create Project Flow Upgrade (Goal Clarification + Blueprint Generation)
### 4.1 Current Create Project steps
1) Goal (text)
2) Temporal (cutoff)
3) Pick Core
4) Setup

### 4.2 Updated behavior for Step 1 (Goal)
When user clicks **Next**:
- Start **Background Job: Goal Analysis**
- Show a **Goal Assistant panel** that can:
  - Ask clarifying questions (optional)
  - Offer “Skip & Generate Blueprint Now”
  - Offer “Answer & Continue”

#### 4.2.1 Clarifying Questions Design
- Questions must be **structured**: single select / multi select / short input.
- Limit to 3–8 questions unless the user keeps asking for more.
- Each question must have a clear reason (“We ask this to determine output format / time horizon / scope.”)

#### 4.2.2 Strong “Goal Analyzer Prompt” (for professional questioning)
**System Prompt Pattern (no code):**
- You are a Project Formulation Expert.
- Your job is to infer the prediction structure and ask only questions that materially change the blueprint.
- Ask about:
  1) Output type (distribution/point/ranked/paths)
  2) Time horizon + granularity
  3) Scope (entity/geography)
  4) Primary drivers (population vs time series vs constraints vs events)
  5) Availability of historical labels (backtest viability)
  6) Data collection preference (auto research allowed?)
- Avoid vague questions; prefer options.
- After user answers, generate:
  - goal_summary
  - blueprint preview (required slots + section tasks)
  - risk notes (what’s missing)
- Respect temporal isolation constraints in any suggested sources.

### 4.3 Save behavior & Cancel confirmation
- During Step 1, store user work in a **draft** state.
- If user tries to exit:
  - show confirm modal:
    - “Leave setup? Your draft will not be saved unless you click Save Draft.”
  - Options:
    - Save Draft & Exit
    - Discard & Exit
    - Continue Setup

---

## 5) Async AI Loading Architecture (Non-Blocking)
### 5.1 Problem to solve
Users must not be forced to wait on a blocking spinner and must be able to navigate away.

### 5.2 Solution components
1) **Job Queue**
2) **Job State Machine**
3) **Progress Reporting**
4) **UI Loading Widgets**
5) **Notifications + Job Center**

### 5.3 Job state machine (minimum)
- `queued` → `running` → `succeeded` / `failed` / `cancelled`
- Add `partial` if streaming incremental results is supported.

### 5.4 Progress model
- Each job provides:
  - `progress_percent` (0–100)
  - `stage_name` (e.g., “Validating schema”, “Summarizing evidence”, “Compiling features”)
  - `eta_hint` (optional, best-effort)
- If exact progress is unknown:
  - use staged progress (e.g., 10/30/60/90/100) based on pipeline phases.

### 5.5 UI widgets (must)
- Per-section inline loading widget:
  - spinner + stage + progress bar
- Global top-right notification bell:
  - “Blueprint ready”
  - “Personas compiled”
  - “Data validation failed”
- A **Runs & Jobs** page exists in your nav; expand it into the “Job Center”:
  - filter by project
  - show job logs + artifacts
  - allow retry/cancel where safe

### 5.6 Persistence requirements
- Job status must persist across refresh.
- Job artifacts must be saved and linked to:
  - project_id
  - blueprint_version
  - slot_id / task_id (if applicable)

---

## 6) Inputs System: Unified “Input Slots” (Not just Personas)
### 6.1 Change mindset
Your UI can keep the same pages, but internally everything is an **Input Slot**:
- Personas are one slot type.
- Data sources are one or many slot types.
- Evidence documents, time series, labels, rulesets are all slots.

### 6.2 Inputs acquisition methods
Each slot can be fulfilled via:
- Manual upload (CSV/JSON/docs)
- Connect API source
- Snapshot import
- AI Research (subject to temporal cutoff)
- AI Generation (synthetic, with explicit labeling)

### 6.3 After input is added: mandatory processing
Every time a slot receives new data, trigger:
1) Programmatic validation (schema/timestamps/dedup)
2) AI summarization
3) Goal alignment scoring (does this match the project goal and blueprint needs?)
4) Artifact compilation (feature store, persona store, graph build, etc.)
All these run as background jobs with progress.

---

## 7) Checklist + Alerts (Not just “done/not done”)
### 7.1 Overview checklist becomes dynamic
Checklist items come from the blueprint’s Section Task Map.

### 7.2 Each item has alert states
Each checklist item must have one of:
- ✅ Ready
- 🟡 Needs attention (low coverage, partial slot, weak match)
- 🔴 Blocked (missing required slot or failed validation)
- ⚪ Not started

### 7.3 Each item must show:
- What is missing
- Why it matters
- The next action button (AI generate / AI research / manual add)
- The latest AI summary & match score

---

## 8) Per-Section Behavior (Blueprint-driven)
For each section below, the UI should render:
- **Guidance Panel** (from blueprint tasks)
- **Slot status** (required/recommended)
- **Actions** (AI/Manual)
- **Latest artifacts** (summary, validation, compiled outputs)

### 8.1 Sections to cover (must include all)
- Overview
- Data & Personas (Inputs)
- Rules & Assumptions
- Run Parameters
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
- Library (personas library, templates, rulesets, evidence source)
- Calibration Lab (if present)

> If any section is currently “static”, blueprint should still be able to attach tasks and readiness status to it.

---

## 9) AI Suggestion & Research (Production guardrails)
### 9.1 AI suggestions must be actionable
Every suggestion must include:
- required fields
- recommended source types
- expected effect on prediction accuracy
- a button to execute (AI Research / Generate) or manual guidance

### 9.2 Temporal compliance
All research must respect project cutoff:
- sources without timestamps are blocked in strict backtest
- store manifests for any retrieved data

### 9.3 Avoid hallucinated “facts”
AI can recommend what to collect, but must not invent the collected data.
All evidence must be stored and referenced.

---

## 10) Engineering Tasks Checklist (Implementation Work Breakdown)
### Phase A — Data Model + Versioning
- [ ] Add Blueprint storage model: `project_id`, `blueprint_version`, `policy_version`, `content`, `created_at`, `created_by`
- [ ] Add Blueprint-to-Run linking: every run references `blueprint_version`
- [ ] Add Slot model (or extend existing): `slot_id`, `slot_type`, `required_level`, `schema`, `status`, `artifacts`
- [ ] Add Task model: `task_id`, `section_id`, `linked_slots`, `status`, `alerts`, `last_summary_ref`

### Phase B — Job System & Loading UI
- [ ] Implement background job queue for AI work (analysis, summarization, validation, compilation)
- [ ] Implement job persistence + progress reporting + retry logic
- [ ] Add inline loading widgets with progress bar on relevant sections
- [ ] Expand Runs & Jobs into a Job Center (filter/search, logs, artifacts)

### Phase C — Goal Clarification & Blueprint Builder
- [ ] Add Goal Analysis job triggered on Next
- [ ] Add Clarify UI panel + structured Q&A
- [ ] Add “Skip & Generate Blueprint” option
- [ ] Add “Save Draft” behavior + exit confirmation modal
- [ ] Implement Blueprint Builder prompt + policy constraints

### Phase D — Blueprint-driven Sections
- [ ] Overview checklist becomes blueprint-driven with alert levels
- [ ] Data & Personas page becomes unified Inputs experience:
  - show required slots for this project
  - show personas as one slot among others
- [ ] Add Guidance Panel to Rules, Run Params, Event Lab, Universe Map, Reliability, Reports
- [ ] Ensure each slot triggers validation + AI summary + match scoring jobs

### Phase E — Quality, Calibration, and Readiness
- [ ] Implement alignment scoring (goal match) and show it in UI
- [ ] Implement minimum backtest plan artifacts (labels required, evaluation metrics)
- [ ] Implement reliability indicators per project (data completeness, model consistency, drift warnings)

### Phase F — Documentation & Ops
- [ ] Update docs: where blueprint lives, how to debug job failures
- [ ] Add admin tools: view blueprint versions, roll back blueprint version (audited)

---

## 11) Testing & Debugging (Chrome-first, production readiness)
### 11.1 Local + staging prerequisites
- Ensure Chrome DevTools is used for:
  - Network inspection (job polling, API calls)
  - Console errors (React/Next, API errors)
  - Performance tab (job UI renders, re-render loops)
- Ensure logs are accessible for:
  - Job failures
  - Blueprint generation errors
  - Slot validation errors

### 11.2 Test plan (must pass)
**A) Create Project flow**
- [ ] Enter goal → trigger Goal Analysis job → user can navigate away and return
- [ ] Clarify Q&A works; skip works
- [ ] Exit during clarify shows confirm modal; discard removes draft
- [ ] Blueprint is generated and stored with version
- [ ] Temporal cutoff is still enforced in later AI research

**B) Blueprint distribution**
- [ ] Overview checklist reflects blueprint tasks
- [ ] Each section shows correct Guidance Panel tasks for that project type
- [ ] Required vs recommended slots display correctly

**C) Async loading**
- [ ] During AI processing, user can switch pages without losing state
- [ ] Inline loading widgets show progress stages
- [ ] Notification triggers when job completes
- [ ] Job Center shows accurate status + artifacts

**D) Slot processing**
- [ ] Add data/personas → validation runs → summary artifact created
- [ ] Alignment scoring shows “match” and reasons
- [ ] Low-quality input triggers “Needs attention” state
- [ ] Failed validation triggers “Blocked” with clear error

**E) Reliability & calibration**
- [ ] Backtest readiness requires labels where applicable
- [ ] Metrics computed where possible
- [ ] Reports show data manifest references and blueprint version for traceability

### 11.3 Deployment checklist
- [ ] No console errors in Chrome on key flows
- [ ] Job queue stable under multiple concurrent jobs
- [ ] Blueprint versioning visible and consistent
- [ ] All “required” slots can reach ✅ Ready
- [ ] No section is left without blueprint coverage
- [ ] Monitoring/metrics for job failures and blueprint errors are enabled
- [ ] Production deploy with feature flag if needed; rollout plan documented

---
End of blueprint.md

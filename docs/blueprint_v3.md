# Blueprint v3 — Enforce “Wizard-only Blueprint” + Section Guidance System (Production)

> **Purpose**: This document is a corrective, production-grade implementation plan to bring the current codebase into **full compliance** with the intended Blueprint v2 behavior:
>
> - **All initial goal clarification + blueprint generation happens ONLY in Create Project → Step 1 (Goal)**  
> - **Project Overview is read-only** (no Q&A, no “Start Goal Analysis”, no draft blueprint interaction)  
> - **Every project section** has a GuidancePanel driven by the blueprint tasks/slots  
> - **All AI work runs as background jobs** with progress UI and can be resumed after navigation/refresh  
> - **A project cannot be created unless Blueprint v1 is committed** (blueprint is finalized at creation time)

---

## 0) Current Reality (from audit) — Why v2 “looks wrong” in production

The audit report shows three root causes:

1. **The v2 wizard is feature-flag gated and disabled in production** → users only see a plain textarea in Step 1.  
2. **Overview violates the spec** by hosting goal analysis actions + draft clarify UI.  
3. **GuidancePanel coverage is incomplete** across project sections.

**The code for the correct flow already exists**, but it is not reliably active in production and the old/legacy entry points remain.

---

## 1) Non‑Negotiable UX Rules (Acceptance Criteria)

### 1.1 Create Project Wizard
**Step 1: Goal**
- User types goal (≥ 10 chars) → **GoalAssistantPanel appears**.
- User can click:
  - **Analyze Goal** → starts background job (progress visible)
  - **Skip Clarify** → generates blueprint draft directly (still background job)
- Panel then shows:
  - Clarifying questions (if applicable)
  - Blueprint preview (human-readable)
  - “Proceed” gating behavior (see 1.3)

**Step 2: Temporal**
- Temporal cutoff is configured here (already implemented in your system).

**Step 3: Pick Core**
- The selected core strategy (Collective / Targeted / Hybrid) is recorded in the blueprint & project.

**Step 4: Setup**
- Final confirmation shows:
  - Goal summary
  - Temporal cutoff
  - Core selection
  - Blueprint preview summary
- Create Project commits blueprint **v1 finalized**.

### 1.2 Project Overview (Read-only)
- Overview **must never** include:
  - “Start Goal Analysis”
  - ClarifyPanel / Q&A
  - any “Generate Blueprint” or “Continue Blueprint” flows
- Overview shows:
  - Blueprint summary
  - Checklist status
  - Alignment score
  - Recent runs & key metrics

### 1.3 Blueprint Existence Rules
- A Project **cannot be created without a finalized Blueprint v1**.
- After project creation:
  - There should never be a state where `blueprint.is_draft=true` is required for the user to proceed.
  - “Draft blueprints” may exist transiently in the **wizard**, but once the project is created, the committed blueprint must be **final**.

---

## 2) Required Platform Behavior (Backend + Jobs)

### 2.1 Blueprint Pipeline (Wizard → Commit)
**Input**: goal text + optional answers + temporal cutoff + chosen core  
**Output**: a versioned blueprint containing:
- goal_summary, domain_guess, target_output, horizon, scope
- slots: DATA_SOURCE / PERSONA_DEFINITION / RULE_SET / SCENARIO / CALIBRATION / EVIDENCE
- tasks: per section, each task linked to required slots

**Jobs**:
- Goal Analysis Job → produces clarifying question set + initial blueprint draft (or intermediate result)
- Blueprint Draft Job → turns goal (+ answers) into structured blueprint draft
- Commit Blueprint Job (optional, can be part of Create Project) → writes blueprint v1 finalized to DB

### 2.2 Slot Pipeline (Per Section, after user provides artifacts)
Whenever user uploads/creates/edits an artifact for a slot:
1. Slot Validation Job  
2. Slot Summarization Job  
3. Slot Alignment Scoring Job  
4. Slot Compilation Job  

**Outputs**:
- validation_result, summary, fit_score, compiled_artifact
- task alert state (READY / NEEDS_ATTENTION / BLOCKED / PROCESSING)

**UI effect**:
- Checklist items update automatically.
- GuidancePanel shows the most important tasks and “what to do next”.

### 2.3 Idempotency + Duplicate Job Prevention
For any job triggered from UI:
- If the same job is already queued/running for the same project + purpose, do not enqueue another.
- All jobs must have:
  - deterministic `job_key` or equivalent (project_id + job_type + slot_id/blueprint_version)
  - safe retry behavior

---

## 3) Priority Fixes (Do these FIRST)

### P0 — Make the correct wizard visible in production
- Ensure **v2 wizard is enabled in production**.
- Decide one of:
  1) **Remove the flag** and make v2 wizard always on, OR  
  2) Keep the flag but set it in **both staging + production** and add monitoring so it can’t silently turn off.

**Acceptance**: In production, after 10+ chars in Step 1, the GoalAssistantPanel renders.

### P0 — Remove Overview violations (hard block)
- Remove “Start Goal Analysis” button from overview.
- Remove any rendering of ClarifyPanel from overview.
- Remove any overview event handlers that start goal analysis jobs.

**Acceptance**: Overview has no Q&A, no goal-analysis CTA, no draft-blueprint actions.

### P0 — Enforce “project requires blueprint v1”
- Update project creation so it fails loudly if blueprint draft is missing.
- Ensure the wizard cannot proceed to project creation without:
  - a valid blueprint preview state, OR
  - “Skip Clarify” path that still creates a blueprint draft

**Acceptance**: Attempting to create a project without blueprint returns a clear error and UI blocks.

---

## 4) Implement the Correct Flow (Step-by-step Tasks)

> Engineer must complete tasks in order and check each acceptance test before moving on.

### 4.1 Refactor Entry Points
- **Single source of truth** for “initial blueprint generation” is the wizard Step 1.
- Remove/disable legacy analysis triggers elsewhere (overview, random panels, etc.).
- Ensure deep links do not expose the legacy flow.

### 4.2 Wizard Step 1: “Analyze → Clarify → Preview”
Implement a robust state machine that:
- starts job
- persists job reference so user can refresh/navigate away and resume
- renders:
  - queued/running progress widget
  - clarifying Q&A once available
  - blueprint preview once ready

**Resume behavior**
- If the user returns to the wizard page and the job already exists, the UI should show current status instead of restarting.

### 4.3 Commit Blueprint at Create Time
- On Step 4 “Create Project”, the API must:
  - take the finalized blueprint draft
  - create project
  - write blueprint v1 in DB as **finalized**
  - return projectId + blueprintId + version

### 4.4 GuidancePanel Coverage (ALL sections)
Add GuidancePanel to every project section route, with a consistent location and behavior:
- Overview (read-only summary + checklist; GuidancePanel optional but recommended)
- Data & Personas
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
- Calibration Lab (if present)
- Library pages are out of scope unless they affect a project directly

**Acceptance**: Navigate to each section and GuidancePanel is visible and shows section tasks.

### 4.5 Checklist With Alerts (not dummy)
For each checklist item:
- “NOT_STARTED” until the user provides required slots
- “PROCESSING” while jobs run
- “READY” when validation + summary + fit score are ok
- “NEEDS_ATTENTION” when fit score low/coverage weak
- “BLOCKED” when required slot missing or invalid

**Acceptance**: Each item status is driven by real job outputs, not hardcoded.

---

## 5) Loading Architecture (Background work without blocking navigation)

### 5.1 Global Active Jobs Widget
- Active jobs must show in a global widget (banner/toast/panel) across the app.
- Each job shows:
  - name
  - status (queued/running/succeeded/failed)
  - percent progress
  - “view details” link (Job Center)
  - safe cancel UX (optional)

### 5.2 Local Inline Progress Widgets
- In the section where the job is initiated, show an inline progress card that:
  - matches the global job
  - provides context (“what is being computed and why”)

### 5.3 Navigation Safety
- Users can move around while jobs run.
- If they leave during **Create Project Step 1 goal analysis**, show a confirmation modal:
  - “Leave without saving draft?” (Discard)
  - “Save draft and leave” (if supported)
  - “Stay”

---

## 6) Observability + Reliability (Production-grade)

- Log every job creation with:
  - project_id, blueprint_version, slot_id (if any), job_key
- Log every job completion and artifact outputs.
- Add error surfaces in UI:
  - failed jobs show actionable message and retry button
- Add a “Diagnostics” section inside Job Center:
  - recent failures
  - last successful blueprint generation
  - last slot compilation summary

---

## 7) Testing + Debugging (Chrome-first)

### 7.1 Pre-flight
- Use Chrome stable
- Open DevTools:
  - Console
  - Network (Preserve log)
  - Application → Local Storage (verify wizard draft state)

### 7.2 Mandatory Smoke Tests (Staging FIRST)
**Create Project Wizard**
1. Go to `/dashboard/projects/new`
2. Enter goal (≥10 chars) → GoalAssistantPanel appears
3. Click “Analyze Goal”
   - inline progress shows
   - Active jobs widget shows job
4. Wait → clarifying questions appear
5. Answer → blueprint preview appears
6. Complete temporal + pick core + setup
7. Create project
8. Confirm:
   - project overview is read-only
   - blueprint v1 exists and is finalized
   - checklist is not dummy

**Overview Rules**
- Confirm there is NO “Start Goal Analysis” CTA
- Confirm NO ClarifyPanel

**GuidancePanel Coverage**
- Visit all sections listed in 4.4 and confirm GuidancePanel visible

**Slot Pipeline**
- Upload a data/persona artifact in Data & Personas
- Confirm slot pipeline jobs run and update checklist states

### 7.3 Production Rollout
- Only deploy to production after staging passes all tests with:
  - no console errors
  - no 4xx/5xx bursts during wizard flow
  - jobs complete and persist across refresh

---

## 8) “Done” Definition (What the engineer must deliver)

Engineer must deliver the following artifacts in the repo:

1. `docs/blueprint_v3.md` (this doc placed in repo, updated with any repo-specific details)
2. `docs/blueprint_v3_completion_report.md` containing:
   - commits / PR links
   - screenshots or screen recordings of:
     - wizard Step 1 with GoalAssistantPanel active in production
     - overview page read-only
     - guidance panels across sections
   - Chrome console screenshots showing no errors
3. Deployed staging + production URLs and a short checklist confirming all acceptance criteria

---

# End

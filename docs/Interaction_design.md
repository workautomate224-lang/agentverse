# Future Predictive AI Platform — Interaction Design Specification (Interaction_design.md)

**Document type:** Interaction Design + UI-to-Backend execution map (no code)  
**Audience:** Frontend + Backend engineers and AI coding agents implementing the UI exactly  
**Scope:** Every page, panel, control, and button with backend flow references aligned to **project.md**  
**Date:** 2026-01-08 (Asia/Kuala_Lumpur)  
**Version:** v1.0 (living document; version all changes)

---

## 0) How to use this document

This document is the **room-by-room interior plan + operating manual** for the platform:
- It specifies **layout**, **controls**, **interaction patterns**, **states**, and **edge cases**.
- It maps each interaction to backend artifacts defined in **project.md**:
  - **ProjectSpec** (project.md §6.1)
  - **Persona** (project.md §6.2)
  - **Event Script** (project.md §6.4)
  - **RunConfig / Run** (project.md §6.5–§6.6)
  - **Node / Edge** (project.md §6.7)
  - **Telemetry** (project.md §6.8)
  - **Reliability Report** (project.md §7)

> **Non-negotiable UX constraint:** The platform is **powerful in the backend** but **simple in the frontend**.  
> Default user flows should be **“no-brain”**: Ask → Run → Result + Confidence.  
> Advanced controls must be hidden behind progressive disclosure.

---

## 1) Global UX principles (must apply everywhere)

### G1 — Truth is persisted artifacts, not UI state
- UI should never maintain “the source of truth” for simulation results.
- UI reads from persisted artifacts: Node/Run/Telemetry/Reports (project.md §3.2).

### G2 — Reversible operations are forks, never edits
- Any change that affects simulation creates a **new Node** (fork) and a new Run artifact.
- UI must communicate this clearly: “Forking from Node X” (project.md §1 P1, §11 Phase 2).

### G3 — Progressive disclosure
- Hide 90% parameters by default.
- Show “Advanced” only when needed:
  - experts, debugging, calibration, template authoring.

### G4 — Fast feedback
- Any action that starts computation must immediately return:
  - Run submitted → `run_id` → progress UI.
- Avoid blocking UI on long compute.

### G5 — No hard caps on futures; use clustering + progressive expansion
- Never present “only 3–7 futures” as a system limit.
- UI should show **clusters** first; expand on demand (project.md §11 Phase 4).

### G6 — Visualization is read-only
- 2D world and replay views are read-only telemetry renderers (project.md §1 P4, §11 Phase 8).
- “Replay” must not trigger simulation.

### G7 — Safety, ethical gating, and auditability
- Sensitive projects require policy flags and additional confirmations.
- Every run/action must be auditable (project.md §8.5).

---

## 2) Information architecture (navigation + page map)

### 2.1 Primary navigation (left sidebar)
1. **Dashboard**
2. **Projects**
3. **Templates** (domain templates, rule packs)
4. **Calibration Lab**
5. **Runs & Jobs** (queue, failures)
6. **Admin** (tenancy, quotas, audit logs) *(role-gated)*
7. **Settings** (profile, API keys, billing placeholders if needed)

### 2.2 Project-level navigation (within a project)
Tabs (top bar or secondary sidebar):
1. **Overview**
2. **Universe Map**
3. **Personas**
4. **Society Mode**
5. **Target Mode**
6. **Reliability**
7. **2D Replay**
8. **Exports**
9. **Project Settings** *(role-gated)*

> All project tabs reference the same underlying artifact set (project.md §6).

---

## 3) Shared UI components (design system contracts)

> Keep your existing MVP **visual style** unchanged. This spec defines *structure and behavior*, not aesthetics.

### 3.1 Global components
- **TopBar**
  - Project switcher
  - Global search (projects/nodes/runs)
  - Notifications (run completion, failures)
  - User menu (profile/logout)
- **SideNav**
  - collapsible, remembers state
- **Toast system**
  - success/info/error with actionable links (e.g., “Open Run”)
- **Modal**
  - confirm destructive actions, policy acknowledgements
- **Drawer**
  - used for “Ask”, Node Inspector, Advanced settings
- **Inline validation**
  - for forms; show errors next to fields

### 3.2 Data display primitives
- **ArtifactCard**: shows Node/Run/Report summaries with badges
- **MetricChip**: small chips for probability/confidence/drift
- **ComparisonTable**: side-by-side metrics for nodes/runs
- **TimelineScrubber**: used in 2D replay and telemetry charts
- **VirtualizedList**: for personas, runs, nodes (performance)

### 3.3 Loading/performance patterns
- **Skeleton loaders** for lists/cards
- **Lazy fetch** of heavy data:
  - telemetry blobs, large persona sets, deep node details
- **Incremental rendering**:
  - Universe Map graph, cluster expansions
- **Optimistic UI**:
  - submit run → show pending node placeholder immediately

---

## 4) Backend interaction conventions (UI → API → artifacts)

### 4.1 Naming conventions (no code, just consistency)
- Create resources: `POST /...`
- Read details: `GET /.../{id}`
- Update settings: `PATCH /.../{id}`
- Submit compute: `POST /runs`
- Stream progress: `GET /runs/{run_id}/events` (SSE) or `WS /runs`

### 4.2 Artifact lifecycle patterns
- **User action → Run submitted → Run succeeds → Node created/updated → UI refresh**
- Failures:
  - Run becomes `failed`
  - Node remains unchanged
  - UI provides failure reason and retry link

### 4.3 Determinism exposure
Advanced panels should show:
- engine_version, ruleset_version, dataset_version, seed strategy (project.md §6.5).

---

## 5) Page specifications (page-by-page)

> Each page includes:
> - Purpose
> - Layout (regions)
> - Controls (buttons, inputs)
> - Backend flow (artifact interactions)
> - States (empty/loading/error)
> - Performance notes

---

# 5.1 Dashboard

## Purpose
Quickly return to ongoing projects, recent nodes, recent runs, and alerts.

## Layout
- **Header:** “Dashboard”
- **Section A:** Recent Projects (cards)
- **Section B:** Recent Runs (table)
- **Section C:** Alerts (failed runs, drift warnings)
- **Section D:** Quick Actions

## Controls
- **New Project** (primary)
- **Resume Last Project**
- **View Failed Runs**
- **Search**

## Backend flow
- `GET /projects?sort=recent`
- `GET /runs?sort=recent`
- `GET /alerts` (failed runs, drift)

## States
- Empty dashboard: show “Create your first project”
- Failed runs: show retry actions and logs link

---

# 5.2 Projects List

## Purpose
Browse and manage all projects.

## Layout
- Search bar + filters (core type, last updated, confidence)
- Project grid/list with badges:
  - Prediction Core badge (Collective/Target/Hybrid)
  - Last run status
  - Drift warning indicator

## Controls
- **Create Project**
- Filters: Core, Domain template, Owner, Privacy
- Bulk actions (Admin/Owner): archive, delete *(confirm modal)*

## Backend flow
- `GET /projects`
- `PATCH /projects/{id}` for archive
- `DELETE /projects/{id}` (hard-delete role-gated; audit log required)

---

# 5.3 Create Project (Wizard)

## Purpose
Convert a natural-language goal into a ProjectSpec, select default prediction core, and create a baseline plan.

## Layout (Wizard steps)
1. **Goal**
2. **Core Recommendation**
3. **Data & Personas**
4. **Outputs**
5. **Review & Create**

### Step 1 — Goal
- Input: “What do you want to predict?” (multiline)
- Optional: domain hints (dropdown)
- Optional: “Sensitive domain” checkbox (shows policy warnings)

**Button:** `Next`

### Step 2 — Core Recommendation
- Shows recommended core:
  - **Collective Dynamics** (Society Mode)
  - **Targeted Decision** (Target Mode)
  - **Hybrid Strategic** (Hybrid)
- Allow override (radio)

**Buttons:** `Back`, `Next`

### Step 3 — Data & Personas
- Minimal: choose persona source:
  - Upload
  - Use templates
  - Deep Search (optional; can be enabled later)
- Shows estimated persona count and uncertainty tag

**Buttons:** `Back`, `Next`

### Step 4 — Outputs
- Choose output metrics:
  - “Outcome probability distribution”
  - “Trend over time”
  - “Key drivers”
  - “Reliability report”
- Default on: reliability report

**Buttons:** `Back`, `Next`

### Step 5 — Review & Create
- Summary card of ProjectSpec
- Confirm policy if flagged

**Buttons:** `Create Project`

## Backend flow
- `POST /projects` creates **ProjectSpec** (project.md §6.1)
- Optional: `POST /personas/import` (stubs)
- Creates initial “Root Plan” record but **does not run** until user clicks Run Baseline.

## States
- Validation errors: required fields highlight
- Policy gating: modal acknowledgement required

---

# 5.4 Project Overview

## Purpose
Project home: baseline status, latest node, confidence summary, next suggested actions.

## Layout
- **Top summary:** goal + core + template + last updated
- **Baseline block:** “Run Baseline” call-to-action if missing
- **Latest node block:** latest node card
- **Reliability block:** calibration/stability/drift summary
- **Suggested actions:** “Ask a what-if”, “Add Personas”, “Calibrate”

## Controls
- **Run Baseline** (primary if none)
- **Ask** (opens Ask drawer; available after baseline)
- **Open Universe Map**
- **Open Personas Studio**
- **Open Reliability Report**

## Backend flow
- `GET /projects/{id}`
- `GET /nodes?project_id=...&sort=latest`
- `GET /reliability?project_id=...&node_id=...`

---

# 5.5 Personas Studio

## Purpose
Create, import, curate, and segment personas. Provide both “no-brain” import and expert controls.

## Layout
- **Left:** Persona sources and segments
- **Center:** Persona list (virtualized)
- **Right drawer:** Persona inspector/editor

### Persona list row shows:
- persona label
- source badge (upload/generated/deep_search)
- uncertainty indicator
- segment tags
- last updated

## Primary controls
- **Import Personas** (button)
- **Deep Search Personas** (button)
- **Generate Personas from Goal** (button)
- **Create Segment** (button)
- **Validate Persona Set** (button)

## Secondary controls
- filters: region, demographic buckets, uncertainty range
- bulk tag, bulk remove (confirm)

## Backend flow
- Import:
  - `POST /personas/import` → persists Personas (project.md §6.2)
- Deep Search:
  - `POST /personas/deep_search` → returns candidates + evidence refs
  - `POST /personas/approve` → persist selected
- Segments:
  - `POST /segments` / `PATCH /segments/{id}`

## Validation (critical)
**Validate Persona Set** runs checks:
- coverage: missing key regions?
- conflicts: impossible combinations?
- data quality: missing required fields?

Backend:
- `POST /personas/validate` → report + suggested fixes

## States
- Empty: show quick-start import buttons
- Loading deep search: show progress + cancel
- Errors: show field-level errors and evidence links if available

## Performance notes
- persona list is virtualized
- persona details fetched on demand (lazy)

---

# 5.6 Templates & Rule Packs

## Purpose
Manage domain templates and rule packs (behavioral economics rules and mappings).

## Layout
- List of templates (cards) with:
  - domain name
  - last updated
  - compatibility badges (Collective/Target/Hybrid)
- Rule pack detail view:
  - rule list (insertion point indicated)
  - parameter ranges
  - version history

## Controls
- **New Template**
- **Clone Template**
- **Publish Version** (role-gated)
- **Rollback Version** (role-gated)
- **Attach to Project**

## Backend flow
- `GET /templates`
- `POST /templates`
- `POST /rulesets`
- Versioning: `POST /rulesets/{id}/versions`

## Notes
- Rules must declare insertion point: Observe/Evaluate/Decide/Update (project.md §11 Phase 1–3).

---

# 5.7 Universe Map (Core)

## Purpose
Operate and explore parallel futures as a branching graph.

## Layout regions
- **Top bar:** Run controls and modes
- **Center:** Graph canvas (clusters + nodes + edges)
- **Right:** Node Inspector drawer (contextual)
- **Left:** Filters / search / branch controls
- **Bottom:** Comparison tray + timeline mini charts (optional)

## Top bar controls
- **Ask** (opens Ask drawer)  
- **Fork & Tune** (opens Variable Tuning drawer for selected node)  
- **Expand Cluster** (if cluster node selected)  
- **Compare** (toggle compare mode)  
- **Reset View** (graph)  
- **Graph Settings** (advanced: layout mode, cluster thresholds)

## Graph interactions (canvas)
- Click node → open Node Inspector
- Drag canvas / zoom
- Hover edge → show intervention summary
- Multi-select nodes (shift-click) → compare tray

## Node types & visuals (behavioral spec)
- **Root Node:** baseline, probability 100%, special badge
- **Regular Node:** has conditional probability and confidence badge
- **Cluster Node:** shows aggregated probability + “contains N branches”
- **Pending Node:** created but run still in progress (spinner)
- **Failed Node:** run failed; node not materialized (warning icon)

## Backend flow
- Initial load:
  - `GET /graph?project_id=...` returns nodes/edges (lightweight)
- Node details (lazy):
  - `GET /nodes/{node_id}` returns full details + refs
- Create fork (variable delta):
  - `POST /nodes/{node_id}/fork` creates child node placeholder + run request
  - `POST /runs` with RunConfig (project.md §6.5–§6.6)
- Expand cluster:
  - `POST /clusters/{cluster_id}/expand` (progressive expansion)
- Subscribe to progress:
  - `GET /runs/{run_id}/events` (SSE) or websocket

## States
- Empty graph (no baseline): show CTA “Run Baseline”
- Loading graph: skeleton nodes
- Large graph: default to cluster-only view

## Performance notes
- Graph must load in layers:
  1) clusters + root
  2) visible neighborhood
  3) expanded branches on demand
- Avoid full relayout every update; incremental layout

---

# 5.8 Node Inspector (Drawer)

## Purpose
Explain and operate on a selected node without leaving Universe Map.

## Layout
Tabs inside drawer:
1. **Summary**
2. **Drivers**
3. **Variables**
4. **Runs**
5. **Reliability**
6. **Replay**

### Summary tab (must-have)
- Outcome summary
- Probability (conditional)
- Confidence badge
- Key events applied
- “Fork origin” (parent node reference)

Buttons:
- **Fork from here**
- **Open Compare** (adds to tray)
- **Open Replay**

### Drivers tab
- Top drivers list:
  - variable name, direction, impact
- “Why” explanation (causal chain)
- Uncertainty notes

### Variables tab
- Show current node variable state
- “Tune variables” button (forks, does not edit)

### Runs tab
- list runs aggregated into node
- each run shows: config versions + seed + status
- “Re-run with new seed set” (fork or rerun policy configurable)

### Reliability tab
- Show reliability report summary:
  - calibration score, stability, drift, sensitivity
- Link to full report

### Replay tab
- Quick preview chart + “Open 2D Replay”

## Backend flow
- `GET /nodes/{node_id}`
- `GET /runs?node_id=...`
- `GET /reliability?node_id=...`

---

# 5.9 Ask Drawer (Event Compiler UI)

## Purpose
Convert natural-language questions into **branching scenario clusters**.

## Layout
- Prompt input (multiline)
- “Context grounding” section (optional):
  - choose scope region/segment/time window
- Output preview:
  - recognized intent: Event / Variable / Query
  - proposed decomposed sub-effects (expandable)
- Run controls:
  - **Generate Branches** (primary)
  - Advanced: scenario breadth slider (default safe)
  - Advanced: time horizon override

## Primary buttons
- **Generate Branches**
- **Generate + Expand Top Cluster** (optional convenience)
- **Cancel** (stops further expansions; doesn’t cancel already running jobs unless supported)

## Backend flow
- `POST /ask` with:
  - `node_id` (context), `prompt`, optional scope
- Response returns:
  - `cluster_id`, `child_node_placeholders`, `run_ids`
- UI adds a cluster node to Universe Map and shows progress.

## States
- Prompt empty: disable submit
- Running: show progress + partial results
- Failure: show error reason + “try narrower scope”

## Key constraints
- Must not hard-cap branches; use clustering + progressive expansion (project.md §11 Phase 4).

---

# 5.10 Fork & Tune (Variable Tuning Drawer)

## Purpose
Let user tweak variables safely by forking a new node.

## Layout
- Shows “Forking from Node X”
- Variable groups (accordion):
  - economy, media, social cohesion, trust, etc. (domain-specific)
- Each variable: slider + numeric input + “reset”
- “Sensitivity scan” button (optional)
- Run settings (advanced):
  - run count, seed strategy, horizon

## Buttons
- **Run Fork**
- **Sensitivity Scan** (pre-run analysis)
- **Reset Changes**

## Backend flow
- `POST /nodes/{node_id}/fork` with scenario_patch
- `POST /runs` enqueued with RunConfig

## States
- Show warning if changes are huge: “Large intervention may increase uncertainty”

---

# 5.11 Compare View (Nodes)

## Purpose
Side-by-side comparison of outcomes, drivers, and reliability.

## Layout
- Compare tray at bottom or dedicated page:
  - select 2–4 nodes
- Sections:
  - outcomes comparison
  - driver deltas
  - reliability deltas
  - timeline metrics comparison

## Controls
- Add/remove nodes
- Pin baseline
- Export compare summary

## Backend flow
- `GET /compare?node_ids=...` returns precomputed diffs (or computed server-side)
- Lazy fetch telemetry-derived time series if requested

---

# 5.12 Society Mode Studio

## Purpose
Run and inspect multi-agent emergent simulations directly (expert view). Most users won’t need it.

## Layout
- Run controls panel:
  - horizon, scheduler profile, rule pack selection
- Population panel:
  - segment composition, persona coverage
- Output panels:
  - trend charts, distribution charts
- Link: “Send result to Universe Map” (creates root/child node)

## Buttons
- **Run Society Simulation**
- **Save as Baseline Node**
- **Export Metrics**
- **Open 2D Replay**

## Backend flow
- `POST /runs` with Society Mode RunConfig
- Results become a Node if saved:
  - `POST /nodes/from_run`

## States
- Show warnings for missing personas or poor coverage
- Show run progress and partial metric updates

---

# 5.13 Target Mode Studio

## Purpose
Single-object planning with multiple possible event sequences (paths).

## Layout
- Target persona panel:
  - choose/create target
  - shows utility profile + risk
- Context panel:
  - constraints, environment, resources
- Action set panel:
  - candidate actions, events, “Ask to generate actions”
- Planner panel:
  - run, pruning settings (advanced)
- Results:
  - path clusters with probabilities
  - expand paths
  - “Branch to Universe Map”

## Buttons
- **Run Planner**
- **Add Constraint**
- **Add Candidate Actions**
- **Ask (generate actions)**
- **Branch Selected Path to Universe Map**
- **Replay Path** (2D or timeline)

## Backend flow
- `POST /target/plans` (planner run)
- `GET /target/plans/{id}`
- `POST /nodes/from_target_path` (bridge to graph)

## States
- If constraints impossible: show explanation “No feasible paths”
- Expand path clusters progressively

---

# 5.14 Hybrid Mode Studio (optional)

## Purpose
Model key actors inside a population context when needed.

## Layout
- Key actor selection (targets)
- Population context (personas/segments)
- Coupling settings (advanced)
- Outputs: joint outcomes + key decisions

## Buttons
- **Run Hybrid**
- **Branch to Universe Map**
- **Replay**

## Backend flow
- `POST /runs` with Hybrid config

---

# 5.15 Reliability (Project-level)

## Purpose
Provide confidence, calibration, stability, sensitivity, drift.

## Layout
- Summary dashboard:
  - overall reliability grade
  - drift warnings
- Node selector:
  - pick node to view report
- Report sections:
  - calibration
  - stability
  - sensitivity
  - drift
  - data gaps

## Buttons
- **Run Calibration** (go to Calibration Lab)
- **Recompute Stability** (advanced)
- **Export Report** (PDF later if needed)

## Backend flow
- `GET /reliability?project_id=...`
- `GET /reliability?node_id=...`
- `POST /reliability/recompute` (role-gated)

---

# 5.16 Calibration Lab

## Purpose
Run historical replays and bounded tuning; prevent leakage.

## Layout
- Historical scenario selector
- Time cutoff indicator (non-editable)
- Parameter tuning panel (bounded)
- Metrics panel
- Results comparison to ground truth

## Buttons
- **Run Calibration**
- **Auto-Tune (bounded)**
- **Rollback Tune**
- **Publish Calibration Profile** *(admin/owner)*

## Backend flow
- `POST /calibration/run`
- `POST /calibration/tune`
- `POST /calibration/rollback`

## States
- If leakage risk detected: hard stop + explanation
- If overfit detected: warning + rollback suggestion

---

# 5.17 2D Replay (Telemetry Renderer)

## Purpose
Watch “what happened” in a node/run, using telemetry only.

## Layout
- Top controls:
  - Play/Pause, speed, seek bar
  - Tick indicator (logical time)
- Left panel:
  - Layer toggles (emotion, stance, influence, exposure)
  - Region/segment filter
- Main canvas:
  - Farm-story-like tile map with semantic zones
  - agents as sprites/icons
- Right inspector:
  - click agent/zone shows:
    - current state
    - recent events affecting it
    - metric references
- Bottom:
  - mini charts synced to playback

## Buttons
- **Open Node**
- **Open Reliability**
- **Export Snapshot** (image)
- **Share Replay Link** *(role-gated, privacy aware)*

## Backend flow
- `GET /telemetry?node_id=...&tick_from=...&tick_to=...`
- `GET /telemetry/index?node_id=...` (for fast seeking)
- No simulation triggers allowed.

## States
- If telemetry missing: show “Replay unavailable; rerun with logging profile”
- Large telemetry: stream chunks; don’t download all at once

---

# 5.18 Runs & Jobs

## Purpose
Operational visibility: queue health, failures, retries.

## Layout
- Runs table with filters:
  - status, project, mode, time
- Run detail view:
  - logs, config, artifact refs
- Retry controls (role-gated)

## Buttons
- **Retry Run**
- **Cancel Run** (if supported)
- **Open Node**
- **Download Logs**

## Backend flow
- `GET /runs`
- `GET /runs/{id}`
- `POST /runs/{id}/retry`
- `POST /runs/{id}/cancel` (optional)

---

# 5.19 Exports

## Purpose
Export node summaries, compare results, reliability reports, telemetry snapshots.

## Layout
- Export types:
  - Node summary
  - Compare pack
  - Reliability report
  - Telemetry snapshot pack (limited)
- Privacy selector

## Buttons
- **Generate Export**
- **Download**
- **Copy Share Link** (signed URL)

## Backend flow
- `POST /exports`
- `GET /exports/{id}`

---

# 5.20 Admin & Settings (role-gated)

## Admin
- Tenants, quotas, concurrency, audit logs, policy flags

## Settings
- Profile, tokens, API keys, project defaults, privacy options

---

## 6) Button-to-backend “reference map” (quick index)

> Use this to ensure UI wiring matches **project.md** artifacts.

- **Run Baseline** → creates RunConfig (project.md §6.5) → Run (project.md §6.6) → Root Node (project.md §6.7)
- **Ask** → compiles Event Scripts (project.md §6.4) + scenarios → Cluster Node + child placeholders → progressive expansion (project.md §11 Phase 4)
- **Fork & Tune** → scenario_patch + new Node + Run (project.md §11 Phase 2)
- **Expand Cluster** → progressive expansion endpoints (project.md §11 Phase 4)
- **Run Planner (Target)** → plan artifact → path clusters → bridge to Node (project.md §11 Phase 5)
- **Run Calibration** → historical replay + reliability report (project.md §11 Phase 7)
- **Play 2D Replay** → telemetry query only (project.md §11 Phase 8)

---

## 7) UX edge cases (must design explicitly)

### 7.1 No baseline yet
- Universe Map should display a single empty state card:
  - “Run Baseline to create Root Node”
- Ask button disabled until baseline exists (or allow Ask but it triggers baseline implicitly with clear notice).

### 7.2 Runs in progress
- Show pending node placeholders with progress indicators.
- Allow user to leave page; run continues; notify on completion.

### 7.3 Run failures
- Node should not be mutated.
- UI should show:
  - run error summary
  - link to logs
  - “retry with safe settings” button

### 7.4 Telemetry insufficient for replay
- Offer rerun with a “Replay logging profile” (more keyframes/deltas).
- Do not automatically rerun without confirmation.

### 7.5 Graph explosion
- Force clustering when node count exceeds threshold.
- Provide “Search nodes” and “Filter by probability/confidence”.

### 7.6 Reliability is low
- UI should show:
  - Low confidence badge
  - Reasons (drift, instability, data gaps)
  - Suggested actions (calibrate, add personas, reduce scope)

---

## 8) Frontend performance checklist (production)

### 8.1 Universe Map
- Progressive data loading:
  - fetch graph skeleton first
  - node details lazy
- Canvas-based rendering preferred for large graphs
- Avoid full layout recompute on every node update

### 8.2 Lists (personas, runs, nodes)
- Virtualization required
- Prefetch next page on scroll
- Debounced search inputs

### 8.3 Telemetry replay
- Chunked streaming
- Seek uses telemetry index, not full scan
- Decouple playback FPS from tick rate

### 8.4 General
- Route-level code splitting
- Image and asset optimization
- Avoid blocking render on large JSON parsing; use workers if needed

---

## 9) Accessibility & usability requirements

- Keyboard navigation for key actions (Ask, Run, Compare)
- Color is not the only indicator (badges + icons + text)
- Clear action confirmations for destructive operations
- Tooltips for advanced parameters with plain-language explanations

---

## 10) MVP UI scope vs later expansions

### Must ship in MVP
- Create Project
- Run Baseline
- Universe Map core (clusters + node inspector)
- Ask drawer (branch cluster creation)
- Fork & Tune
- Compare 2 nodes
- Reliability summary (basic)
- 2D replay (basic timeline + layers)
- Runs & Jobs

### Can ship later
- Full template authoring UI
- Hybrid mode studio
- Advanced calibration tuning UI
- Rich exports (PDF packs)
- Collaboration (comments, annotations)

---

## 11) “Never break” invariants (UI must enforce)

- Forking creates new node, never modifies parent.
- Replay never triggers simulation.
- Every displayed result is tied to:
  - node_id + run_ids + versions + seed strategy
- Any “confidence” shown must reference a persisted reliability report.

---

**End of Interaction_design.md**

# Thought Expansion Graph (TEG) – Universe Map Replacement Execution Plan
> **Doc purpose:** Implement a **more intuitive “parallel universe / probability mind-map”** for AgentVerse by replacing the current Universe Map with a **Thought Expansion Graph (TEG)** UI + backend.  
> **Audience:** Engineering team implementing production-grade features (FastAPI + Celery + Postgres + Next.js).  
> **Non-goal:** This document does **not** include code. It defines **what** to build, **how** it should behave, and **how** to test/ship.

---

## 0) Product Goal (What “done” means)

### 0.1 One-sentence outcome
After the user finishes Create Project + blueprint, they can open **Universe Map** and see a **simple graph of possible events** (branches) with **probabilities and deltas**, run a branch with one click, and export an auditable report.

### 0.2 Why this is necessary
The current Demo2 MVP still feels “not direct” to normal users because outcomes are not presented as a clear **baseline + what-if choices**. TEG turns the platform into a **decision map** that ordinary users can understand.

---

## 1) Scope: What we will build in this iteration

### 1.1 We WILL build
1) **TEG UI** on the existing Universe Map route:
   - View toggles: **Graph / Table / RAW**
   - Right-side **Node Details** panel
   - Node actions: **Expand / Run / Edit (optional)**
2) **TEG backend model & APIs**:
   - Graph nodes/edges that can represent:
     - Verified outcomes (from real runs)
     - Draft scenarios (un-run, estimated)
     - Evidence references
3) **Draft vs Verified** two-layer probability system:
   - Draft nodes show **estimated impact** (cheap)
   - Verified nodes show **actual outcomes** (from runs)
4) **Scenario expansion**:
   - Natural language → multiple scenario candidates (draft nodes)
   - No hard limit on generation, but default UI shows Top-K
5) **Branch execution**:
   - Click Run on a draft scenario → creates a fork run and yields a verified outcome node
6) **Auditability**:
   - Every verified node links to run manifest, persona version, cutoff, evidence
   - Every LLM call is recorded and respects temporal cutoff

### 1.2 We will NOT build (explicitly out of scope)
- Full “Universe Map” graph of the entire simulation DAG (engineering node-edge)
- 2D world visualizer / replay
- Reliability/calibration dashboards
- Open web discovery (beyond user-provided URLs) if it’s not already stable

---

## 2) UX Spec (How it should look and feel)

### 2.1 Universe Map becomes “Thought Expansion Graph”
Universe Map should become a **mind-map** where each node is:
- A **possible event** that may happen (scenario)
- Or a **verified result** (baseline / branch outcome)

### 2.2 Views
#### A) Graph view (default)
- Force-directed/graph layout
- Zoom/pan
- Search
- “Show more” for hidden nodes
- Node styles:
  - **Draft scenario node**: dashed outline + “Estimated”
  - **Verified outcome node**: solid outline + “Verified”
  - **Failed node**: red indicator + error icon
- Edge styles:
  - “EXPANDS_TO” (parent → draft scenario)
  - “RUNS_TO” (draft scenario → verified outcome)
  - “FORKS_FROM” (baseline outcome → branch outcome)

#### B) Table view
- Sorted list of nodes (default sort: **impact magnitude**)
- Filters:
  - Draft vs Verified
  - Status (Queued/Running/Done/Failed)
  - Confidence
- Columns:
  - Title
  - Type
  - Probability (primary metric)
  - ΔImpact vs parent (if applicable)
  - Confidence
  - Status

#### C) RAW view
- JSON payload of selected node + manifest references
- Intended for debugging / audit checks

### 2.3 Node details panel (right side)
For selected node, show:

**Always**
- Title
- Node Type (Draft Scenario / Verified Outcome / Evidence)
- Status
- Created time
- Parent reference

**For Draft Scenario**
- Natural-language “scenario description”
- Estimated delta (direction + magnitude)
- Confidence (low/med/high + numeric)
- Rationale (short bullet)
- Evidence refs (if any)
- Buttons:
  - Expand (more sibling ideas)
  - Run (verify)

**For Verified Outcome**
- Primary outcome (e.g., probability distribution)
- Actual delta vs parent verified node
- Uncertainty / dispersion metric
- Top drivers (top 3–7)
- Persona segment shifts (top 3 segments)
- Evidence refs (if used)
- RunManifest link + RunID + PersonaSetVersion + cutoff snapshot
- Buttons:
  - Expand (generate next-layer scenarios based on this outcome)

**For Failed**
- Stage + error message + correlation id
- “Retry” (optional; safe retry only)
- Guidance: likely reason (worker down, missing personas, evidence cutoff failure)

---

## 3) System Design (Backend)

### 3.1 Important design principle
Do not replace the existing run/node/edge system.  
Implement TEG as a **presentation graph layer** that can reference existing run outputs.

### 3.2 Entities (conceptual model)
> Use Postgres tables or JSONB fields in existing models—choose the least disruptive approach that remains production-grade.

#### A) `TEGGraph`
- graph_id
- project_id
- created_at, updated_at
- active_baseline_node_id (reference)

#### B) `TEGNode`
- node_id (UUID)
- project_id
- type: `OUTCOME_VERIFIED` | `SCENARIO_DRAFT` | `EVIDENCE`
- status: `DRAFT` | `QUEUED` | `RUNNING` | `DONE` | `FAILED`
- title
- summary
- created_at, updated_at
- parent_node_id (nullable)
- payload (JSONB) – type-dependent details
- links (JSONB) – references to run ids, manifests, persona versions, evidence ids

#### C) `TEGEdge`
- edge_id
- project_id
- from_node_id
- to_node_id
- relation: `EXPANDS_TO` | `RUNS_TO` | `FORKS_FROM` | `SUPPORTS` | `CONFLICTS`
- weight/confidence (optional)

#### D) `ScenarioPatch` (may be embedded in TEGNode payload)
- patch_id
- natural_language
- structured_patch (JSON) – “event script”
- estimated_delta, estimated_confidence
- rationale bullets
- evidence_refs
- cutoff_snapshot_id

#### E) Evidence references (already exist or minimal stub)
- evidence_pack_id
- source_url
- snapshot_time
- hash
- temporal_compliance: PASS/WARN/FAIL

### 3.3 Two-layer probability rule (critical)
- `SCENARIO_DRAFT` nodes **must not** pretend to be verified.
- They store estimated delta + confidence, but **no “actual outcome distribution”**.
- Verified nodes must include:
  - outcome distribution/intervals
  - actual delta
  - run manifest linkage
  - persona set version linkage

### 3.4 Mapping from existing system (compatibility)
When a project has baseline & branch runs already:
- Create a verified baseline outcome node referencing the latest baseline run.
- For each completed branch run, create a verified outcome node and connect:
  - baseline → branch with relation `FORKS_FROM`
- For each scenario created in Event Lab (if stored), create draft nodes and connect with `EXPANDS_TO`.

---

## 4) APIs (Backend contracts)

### 4.1 Required endpoints
1) `GET /api/projects/{projectId}/teg`
   - Returns all nodes/edges required for Graph + Table view (paged if needed)

2) `GET /api/teg/nodes/{nodeId}`
   - Returns node payload + enriched details for right panel

3) `POST /api/teg/nodes/{nodeId}/expand`
   - Input: expansion instructions (optional), limits (display limit), user URLs (optional)
   - Output: created draft nodes + edges

4) `POST /api/teg/scenarios/{scenarioNodeId}/run`
   - Converts a draft scenario into a forked run:
     - parent must be a verified outcome node (baseline or verified branch)
     - creates run record, enqueues worker
     - updates node status to QUEUED/RUNNING
   - Output: run id + updated node status

5) `POST /api/teg/nodes/{nodeId}/attach-evidence`
   - Input: list of URLs
   - Output: evidence pack refs + compliance statuses

### 4.2 Non-negotiable backend rules
- All LLM calls must:
  - enforce project cutoff date (temporal isolation)
  - log LLMCall (project_id, purpose, model, tokens, cost)
  - never be executed in tick loops (compiler-only)
- Any failures must be persisted with:
  - `stage`, `exception_class`, `message`, `correlation_id`, `retryable`
  - The UI must surface these details.

---

## 5) LLM Workflows (Planner/Compiler)

### 5.1 Expansion (Draft scenario generation)
Input:
- Project goal + blueprint summary
- Selected parent node’s outcome summary
- Optional user URLs/evidence pack excerpts

Output:
- A set of scenario candidates (no hard limit in generation)
- Each scenario includes:
  - title
  - natural language description
  - structured patch (event script)
  - estimated delta + confidence
  - rationale bullets
  - optional evidence refs

### 5.2 Edit scenario (optional, but recommended)
User edits scenario text:
- “Make this scenario more specific to tariffs + consumer prices”
System:
- recompile scenario patch
- version it (keep prior patch revisions)

### 5.3 Cost control
- Generate many candidates internally if needed
- Persist all candidates, but only return/show Top-K by default
- Provide “Show more” and filters

---

## 6) Frontend Implementation Plan (Next.js)

### 6.1 Route
Re-enable or create Universe Map route in MVP mode:
- `/p/[projectId]/universe-map`
But it must render **TEG** rather than old map.

### 6.2 Components (recommended)
- `TEGCanvas` – graph view container
- `TEGTable` – table view
- `TEGRaw` – raw JSON view
- `TEGNodeDetails` – right panel
- `TEGActions` – Expand/Run/Edit controls
- `TEGFilters` – status/type/confidence filters
- `TEGSearch` – search nodes by title/tags

### 6.3 Visual cues (must have)
- Draft vs Verified styling
- Status badges (Queued/Running/Done/Failed)
- Edge labels (toggleable)
- Loading states and error states

---

## 7) Engineering Tasks (Ordered, testable)

> Implement in order. Each task has a QA gate.

### Task 1 — Product gating update
- In MVP_DEMO2 mode, Universe Map should be visible again, but as TEG.
- Old Universe Map graph (if exists) should not be reachable.

**QA**
- Navigation shows Universe Map.
- Visiting Universe Map loads TEG (Graph/Table/RAW).

---

### Task 2 — Backend: TEG data model + read endpoints
- Implement minimal TEG storage (tables or JSONB).
- Implement:
  - `GET /api/projects/{projectId}/teg`
  - `GET /api/teg/nodes/{nodeId}`
- Implement mapping from existing baseline/branch runs into verified nodes.

**QA**
- Existing projects show at least:
  - Root / Baseline verified node
  - Any existing branch verified nodes
- Right panel loads accurate node details.

---

### Task 3 — Frontend: Graph/Table/RAW + Node Details
- Implement UI with:
  - view toggles
  - graph view + node selection
  - right panel fields
- Show Draft vs Verified styles, statuses.

**QA**
- User can click nodes and see right panel update.
- Table view sorts by impact/confidence.
- RAW shows full payload.

---

### Task 4 — Expand: create draft scenarios (LLM compiler)
- Implement:
  - `POST /api/teg/nodes/{nodeId}/expand`
- Generate scenario candidates and store as draft nodes.
- Return Top-K for UI display.

**QA**
- From baseline verified node, clicking Expand creates draft child nodes.
- Draft nodes show estimated delta/confidence/rationale in right panel.

---

### Task 5 — Run scenario: draft → verified outcome
- Implement:
  - `POST /api/teg/scenarios/{scenarioNodeId}/run`
- Enqueue run (Celery), enforce fork-not-mutate.
- On completion:
  - Create a verified outcome node
  - Connect edges: scenario → outcome (`RUNS_TO`) and baseline → outcome (`FORKS_FROM`)
- Ensure failure state persists with error payload.

**QA**
- Clicking Run moves status: QUEUED → RUNNING → DONE/FAILED.
- DONE produces verified outcome with actual distribution + actual delta.
- FAILED shows error details in right panel (stage/message/correlation id).

---

### Task 6 — Compare UX (make it “obvious”)
Add a compare panel (either in Node Details or a small lower panel):
- Baseline vs selected outcome:
  - probability delta
  - top drivers changed
  - persona segment shifts

**QA**
- Selecting a verified branch clearly shows “Baseline X → Branch Y (ΔZ)”.
- User does not need to leave Universe Map to understand impact.

---

### Task 7 — Evidence attach (optional for this iteration; recommended if available)
Implement:
- `POST /api/teg/nodes/{nodeId}/attach-evidence`
Show PASS/WARN/FAIL badges in Node Details.

**QA**
- User pastes URLs and sees compliance statuses.
- Evidence refs appear in RAW and node details.

---

## 8) Acceptance Test (End-to-end)
Use this exact test script:

1) Create project (goal + cutoff).
2) Generate personas (existing Demo2 flow).
3) Run baseline (existing).
4) Open Universe Map (TEG):
   - baseline verified node is visible
5) Click baseline → Expand:
   - 5–10 draft scenarios appear
6) Select one draft scenario → Run:
   - status transitions and verified outcome appears
7) Compare baseline vs verified outcome:
   - delta is shown clearly
8) Export report:
   - report references manifests and node ids

**Pass criteria**
- A normal user can understand baseline + options + impact within 2 minutes.
- A developer can reproduce results via RAW/manifest.

---

## 9) Deliverables Required From Engineer

### 9.1 Engineering report file
Create at repo root:
- `REPORT_TEG_UNIVERSE_MAP.md`

Must include:
- Task checklist (1–7)
- Screenshots/GIF:
  - Graph view + node details
  - Table view sorting
  - Draft vs verified nodes
  - Run scenario transition
- API changes list
- DB migrations (if any)
- Temporal isolation verification notes (where enforced)
- QA results using Acceptance Test
- Known issues & next steps

---

## 10) Next Enhancements (post-TEG)
- “Show more” with pagination for scenario candidates
- Relationship edges like SUPPORTS/CONFLICTS
- Stronger evidence-to-claim linking
- Full Universe Map (engineering DAG) as an advanced toggle (not default)
- 2D world viewer (future)

---

*End of document.*

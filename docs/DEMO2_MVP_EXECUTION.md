# DEMO2 MVP Execution Plan (Collective / Persona-Driven Predictions)
> **Doc purpose:** This file is an **engineering execution plan** to simplify the current AgentVerse product into a **Demo2-first MVP** that users can run **immediately** without being overwhelmed.  
> **Primary goal:** “User can create a project → generate/import personas via natural language → run a baseline simulation → ask a what-if question → run a branch → compare probability deltas → export a report.”

---

## 0) MVP Definition (What we are building)

### 0.1 MVP user promise (one sentence)
A non-technical user can **predict group decisions** by chatting in a few boxes, without touching complex configuration.

### 0.2 Demo2 scope (KEEP)
This MVP focuses on **Collective / Persona-driven** simulations (e.g., election outcomes, ad reaction, policy impact).

- **Create Project** (goal + temporal cutoff date)  
- **Inputs (Personas + optional Evidence URLs)**  
- **Baseline Run (one-click)**  
- **What-if Scenarios** (natural language → event script → branch run)  
- **Results Compare** (baseline vs branch, probability deltas)  
- **Report Export** (auditable: includes versions, cutoff, sources)

### 0.3 Out of scope for Demo2 MVP (HIDE / DISABLE)
Hide these to remove cognitive load and reduce engineering noise:

- Universe Map graph visualization (`/p/[projectId]/universe-map`)
- World viewer (`/p/[projectId]/world`)
- Replay viewer (`/p/[projectId]/replay`)
- Rules configuration (`/p/[projectId]/rules`)
- Reliability dashboard (`/p/[projectId]/reliability`)
- Any advanced planning pages (society-mode, target-mode, etc.)
- Any “continuous simulation” features (MVP remains **on-demand** only; aligns with constraint C2)

> **Important:** Prefer **Feature Gating** (MVP Mode) over hard deletion in this phase.  
> Deletions happen later once the Demo2 loop is stable.

---

## 1) Current System Anchors (Do not break these)

### 1.1 Architecture (already in repo)
- Frontend: Next.js 14 (App Router)
- Backend: FastAPI
- DB: PostgreSQL
- Queue: Redis + Celery workers
- LLM: OpenRouter
- Real-time: WebSocket updates

### 1.2 Existing routes (project-specific)
Keep these routes **visible** in MVP mode:
- `/p/[projectId]/overview`
- `/p/[projectId]/data-personas`
- `/p/[projectId]/event-lab`
- `/p/[projectId]/run-center`
- `/p/[projectId]/reports`
- `/p/[projectId]/settings`

Routes to **hide/disable** in MVP mode:
- `/p/[projectId]/universe-map`
- `/p/[projectId]/rules`
- `/p/[projectId]/reliability`
- `/p/[projectId]/replay`
- `/p/[projectId]/world`

### 1.3 Core constraints (must remain true)
- **C1 Fork-not-mutate:** Any changes create new Nodes/Edges; never mutate existing nodes.
- **C2 On-demand:** No background “always running” world simulation.
- **C4 Auditable:** Every run is reproducible with a manifest & stored artifacts.
- **C5 LLMs as compilers:** LLM used to plan/compile (e.g., event scripts, persona specs) — **not** inside tick loops.
- **Temporal knowledge isolation:** Enforce cutoff date everywhere that touches data/LLM.

---

## 2) MVP Mode (“减法”) — Feature Gating Plan

### 2.1 Add a single “Product Mode” switch
Add an environment-driven mode, e.g.:

- `PRODUCT_MODE=MVP_DEMO2` (backend)
- `NEXT_PUBLIC_PRODUCT_MODE=MVP_DEMO2` (frontend)

**MVP_DEMO2 behavior:**
- Frontend nav only shows Demo2 pages.
- Disabled routes render a friendly “Disabled in MVP Mode” screen with link back to Overview.
- Backend endpoints for disabled features should return a clear error (FeatureDisabled) to prevent accidental coupling.

### 2.2 Feature matrix (MVP_DEMO2)
| Area | Status | Notes |
|------|--------|------|
| Create Project + Temporal cutoff | ✅ Keep | Must remain production-grade |
| Blueprint/PIL suggestions | ✅ Keep (light) | Show recommendations, but do not force complex wizard flows |
| Personas page | ✅ Keep | Upgrade to natural-language “Generate personas” |
| Data input (separate section) | ❌ Not separate in MVP | For Demo2, allow “evidence URLs” inside Personas workflow |
| Event Lab (what-if) | ✅ Keep | Must create runnable scenario branches |
| Run Center | ✅ Keep | One-click baseline + run scenario branches |
| Universe Map | ❌ Hide | Later stage |
| World / Replay | ❌ Hide | Later stage |
| Rules / Reliability | ❌ Hide | Later stage |
| Reports | ✅ Keep (minimal) | Export summary + manifest + evidence refs |

---

## 3) MVP UX: Minimal Pages and Their “One Job”

### 3.1 Overview (`/p/[projectId]/overview`) — “Home Hub”
**Purpose:** A user should never feel lost; they see exactly what to do next.

**Required UI blocks:**
1) **Goal Card**
   - Shows project goal + mode (Collective) + cutoff date.
2) **Readiness Checklist** (3 lights)
   - Inputs ready? (persona set present + passes validation)
   - Baseline run done? (last baseline run completed)
   - What-if scenarios created? (at least 1 scenario or 0 is ok)
3) **Primary Actions**
   - `Go to Inputs` (Data & Personas)
   - `Run Baseline`
   - `Ask What-if`
4) **Command Bar (optional in MVP, recommended)**
   - A single input that redirects to the correct page:
     - “Generate 1000 personas for US voters…” → Personas page action
     - “Run baseline now” → triggers baseline run
     - “What if gas prices increase 50%?” → Event Lab action

> **Acceptance:** A first-time user can finish a baseline run in ≤ 3 clicks from Overview.

---

### 3.2 Inputs: Data & Personas (`/p/[projectId]/data-personas`) — “Generate / Import Personas”
**Purpose:** Convert vague natural language into a usable persona set and (optional) evidence pack.

#### MVP input types (keep it simple)
- **Natural language request:** “Generate 1000 US white-collar female personas”
- **Optional URLs:** user can paste links to reduce noise (preferred)
- **Optional seed / count:** advanced small control (default to 1000)

#### Behind-the-scenes pipeline (MVP version)
This is the minimum “production-worthy” pipeline the backend must execute:

1) **Interpret Request**
   - Produce a **PopulationSpec** (distribution recipe):
     - region(s), demographics, key traits, constraints
     - a “coverage checklist” (what traits are needed for this domain)
2) **Evidence (optional but recommended)**
   - If URLs provided:
     - fetch → snapshot → extract key signals (stats/claims)
     - record provenance (hash, timestamp, URL)
     - apply temporal compliance check vs cutoff
3) **Generate PersonaSet**
   - Create personas that satisfy PopulationSpec
   - Store as a versioned artifact (PersonaSetVersion)
4) **Validate PersonaSet**
   - coverage (traits completeness)
   - distribution sanity checks
   - size checks (target count)
   - temporal compliance summary (if evidence used)
5) **Persist and Display**
   - show preview of personas (cards)
   - show summary (coverage %, warnings)
   - store manifest links so runs can be reproducible

#### What “Personas” should look like in MVP (schema guidance)
Keep the persona structure **generic** (domain-agnostic), but rich enough for collective simulations:

- `id`, `name` (synthetic)
- `demographics`: age, gender, location, education, income bracket
- `preferences`: values, risk tolerance, openness to change
- `constraints`: language, media channels, mobility (optional)
- `latent`: ideology/affinity vectors (optional)
- `tags`: any domain tags (e.g., “urban”, “rural”, “swing-voter”)
- `provenance`: references to EvidencePack / generation method
- `version`: PersonaSetVersion id

> **Note:** Do not overfit persona fields to elections; keep it universal.

**Acceptance:**
- User can generate 1000 personas with one natural-language instruction.
- Personas are stored versioned and can be re-used by multiple runs.
- A “Data noise reduction” path exists: user-supplied URLs.

---

### 3.3 Event Lab (`/p/[projectId]/event-lab`) — “What-if → Scenario Patch”
**Purpose:** Convert natural language events into **EventScript(s)** that can be run as branches.

#### MVP: Keep the UI extremely small
- One input: “What if government raises tariffs by 10%?”
- Output: an **EventScript** preview (structured)
- Button: **Run as Branch** (fork baseline node)

#### Important production rule
**All LLM calls must honor Temporal Cutoff.**  
If any frontend route calls OpenRouter directly, it must be refactored to a backend-controlled call path that applies LeakageGuard and logs LLMCall.

**Acceptance:**
- EventLab produces EventScript reliably for a few canonical prompts.
- Running a branch is one click after script is generated.

---

### 3.4 Run Center (`/p/[projectId]/run-center`) — “Run Baseline + Run Branches”
**Purpose:** Orchestrate runs and show progress/results.

#### MVP run types
1) **Baseline Run**
   - uses latest PersonaSetVersion + baseline scenario (no event scripts)
2) **Branch Run**
   - forks from the latest completed baseline node
   - applies EventScript(s) and creates a new node

#### Behind-the-scenes mechanics (already in architecture)
- Create Run record + RunManifest
- Enqueue Celery task
- WebSocket progress updates
- Create Node (immutable) + Edge (baseline→branch)
- Generate OutcomeReport (probability distribution)

**Acceptance:**
- Run creation is stable; run completes and produces a node result
- WebSocket progress updates show in UI
- Branch runs always reference a parent node (no mutation)

---

### 3.5 Results Compare (MVP style) — “Cards, not a graph”
Do **not** build a Universe Map UI yet.  
Instead, implement a simple compare view:

- Baseline outcome card (probabilities)
- Branch outcome card(s)
- Delta summary (difference from baseline)
- Link to the evidence / manifest used

You can place this compare panel either in:
- Run Center (recommended), or
- Event Lab (as “Scenario Results”), or
- Reports

**Acceptance:**
- A user can see “Baseline 70% → Branch 62% (-8)” clearly.

---

### 3.6 Reports (`/p/[projectId]/reports`) — “Export with audit”
MVP report should include:

- Project goal + mode + cutoff date
- PersonaSetVersion used (id + summary)
- Evidence summary (URLs + compliance status)
- Baseline result + branch results
- RunManifest ids for all runs
- LLMCall summaries (profile keys, token/cost totals)
- Warnings (coverage gaps, temporal WARN/FAIL)

Export formats:
- On-screen report view + “Download JSON” or “Download Markdown” (either is fine)

---

## 4) Data & Evidence: Minimal “Auditable” Implementation

### 4.1 EvidencePack (MVP version)
Even if not fully modeled yet, the system must store:
- URL list
- snapshot timestamps
- content hash
- extracted excerpts used
- temporal compliance status per source

Storage:
- Use existing storage backend (S3 bucket) patterns (similar to telemetry JSONL approach).
- DB stores references; content stored as object blobs.

### 4.2 Temporal compliance (MVP rules)
For each source:
- **PASS:** publish_time <= cutoff (or archived snapshot <= cutoff)
- **WARN:** unknown publish_time (allowed only if user overrides)
- **FAIL:** publish_time > cutoff (blocked in strict backtest)

**MVP recommendation:** default to “PASS/WARN allowed”, but show warnings prominently.  
Later you can add strict backtest mode.

---

## 5) Engineering Tasks (Ordered, small, testable)

> **Process requirement:** Implement tasks in order. Each task must have a QA check before moving on.

### Task 1 — MVP Mode gates (Frontend + Backend)
- Add `MVP_DEMO2` product mode config
- Remove hidden features from navigation
- Add disabled-route UX
- Enforce backend “feature disabled” for hidden modules

**QA:**
- In MVP mode, only MVP routes appear.
- Visiting a hidden route shows “disabled” page.
- Hidden feature APIs return FeatureDisabled.

---

### Task 2 — Overview becomes the “hub”
- Add readiness checklist + primary CTA buttons
- Make `Run Baseline` available from Overview (or deep link to Run Center with action)

**QA:**
- New project: checklist shows “Inputs missing”
- After personas generated: checklist flips to ready
- Baseline completes: checklist shows done

---

### Task 3 — Personas: Natural Language generation (MVP)
- Add “Generate personas” NL input
- Support optional URL list input (user-provided)
- Generate and persist PersonaSetVersion
- Add validation summary + preview list

**QA:**
- Generate 1000 personas with one instruction
- Personas preview renders
- PersonaSetVersion is persisted and selectable as “Active”

---

### Task 4 — Evidence URL ingestion (MVP)
- Fetch + snapshot URLs (user-provided)
- Record provenance + hash
- Extract minimal signals used by personas generation (even simple is ok)
- Apply temporal compliance status per source

**QA:**
- Evidence list shows PASS/WARN/FAIL
- Evidence refs show in PersonaSet provenance

---

### Task 5 — Baseline run “one click”
- Add/confirm a “baseline scenario” concept (may be implicit)
- `Run Baseline` uses:
  - latest Active PersonaSetVersion
  - default RunConfig
  - no event scripts
- Store baseline node reference for later branching

**QA:**
- Baseline run completes and yields an immutable Node result
- WebSocket progress works
- Baseline node is retrievable for branching

---

### Task 6 — What-if (Event Lab) → Run as Branch
- Ensure Event Lab generates EventScript (existing)
- Add `Run as Branch` button:
  - forks from baseline node
  - creates new run + node + edge
- Show scenario results card and delta vs baseline

**QA:**
- “What if gas prices increase 50%?” generates an EventScript
- Branch run completes
- Compare view shows delta vs baseline

---

### Task 7 — Minimal report export
- Create a report builder that assembles:
  - goal, cutoff, personas summary, evidence summary
  - baseline + branch results
  - manifest ids
  - LLMCall summary & cost totals
- Export as Markdown or JSON

**QA:**
- Download works
- Report includes evidence provenance + cutoff info

---

## 6) Acceptance Test: Demo2 “Happy Path” Script
Use this exact script for QA each time:

1) Create a new project:
   - Goal: “Predict Malaysia 2026 election outcome”
   - Mode: Collective Dynamics
   - Cutoff: set a realistic backtest cutoff (or today for live)
2) Go to Data & Personas:
   - Instruction: “Generate 1000 Malaysian voters personas across states, age, ethnicity, income”
   - (Optional URLs pasted)
3) Confirm personas generated, preview appears, validation summary shows
4) Run Baseline:
   - Baseline completes and shows outcome probabilities
5) Event Lab:
   - “What if government raises tariffs by 10%?”
   - Run as Branch
6) Compare baseline vs branch:
   - confirm delta display
7) Export report:
   - confirm cutoff + evidence + manifest present

**Pass criteria:** A non-technical tester can do the above in < 10 minutes without guessing.

---

## 7) Deliverables Required From Engineer (at end of work)
Engineer must provide a single report file:

- `REPORT_DEMO2_MVP.md`

It must include:
- Completed task checklist (Task 1–7)
- Implementation notes (key decisions, tradeoffs)
- API changes (new endpoints / changed endpoints)
- DB migrations added (if any)
- Screenshots/GIFs (Overview, Personas, Event Lab, Run Center, Compare, Report)
- QA results using the “Happy Path” script
- Known issues + next recommended tasks (for Demo1 later)

---

## 8) Next (after Demo2 MVP is stable)
- Demo1 (data-heavy prediction) using the same artifact pipeline
- Open web discovery (beyond user-provided URLs) with guardrails
- Universe Map visualization (graph) once compare cards are stable
- Reliability/calibration once enough backtests exist

---

*End of file.*

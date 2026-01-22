# Goal Assistant + Blueprint Restoration & TEG Integration (Production Execution Plan)
> **Doc purpose:** Restore **Goal Assistant** and **Blueprint (PIL)** as first-class product features, and integrate them with the **TEG Universe Map** so the platform stays **smart + flexible** (topic-adaptive) while keeping UI simple.  
> **Audience:** Engineering team (Next.js + FastAPI + Postgres + Redis + Celery + OpenRouter).  
> **Constraint:** No code in this doc—only build instructions, contracts, and acceptance tests.

---

## 0) Context: What went wrong
The latest TEG rollout made Universe Map more intuitive, but **Goal Assistant and Blueprint are missing/disabled** in the Create Project flow. That breaks the core promise of a **general predictive platform**, because:
- Without Goal Assistant: user intent is under-specified → wrong inputs → weak simulation setup.
- Without Blueprint: the app cannot dynamically adapt each section to the domain/topic → users must manually guess what to provide.

**This plan restores both and makes them the “brain” that powers TEG and all downstream pages.**

---

## 1) Outcome (Definition of Done)
After implementing this plan:

1) **Create Project** includes:
   - **Goal Assistant (clarifying Q&A)**: turns a user’s initial prompt into a structured Goal Spec.
   - **Blueprint Builder (PIL)**: compiles Goal Spec into a persisted Blueprint Spec with slot guidance & recommended actions.

2) Every project has a **Blueprint Snapshot** that drives:
   - Data & Personas guidance
   - Rules & Assumptions guidance
   - Run Parameters defaults
   - TEG Universe Map seeding + relevant expansions

3) The system is resilient:
   - If LLM/worker fails, it **degrades gracefully** (manual minimal blueprint), never “disappears”.

---

## 2) Product/UX Spec

### 2.1 Create Project flow (new canonical flow)
**Step A — Goal (Goal Assistant)**
- UI: conversational panel
- User enters: “What do you want to predict?”
- System asks 3–8 clarifying questions **one at a time** (or in a compact list).
- User can:
  - Answer
  - Skip a question (use defaults)
  - Attach URLs (optional evidence input)
- Output: `goal_spec` (structured object)

**Step B — Blueprint Preview**
- UI: blueprint summary card + expandable sections
- Show:
  - Domain guess + simulation mode recommendation (collective/targeted/hybrid)
  - Required inputs checklist (minimum viable + high accuracy)
  - Suggested persona segments (if relevant)
  - Candidate outcome metrics + success criteria
  - Suggested first run plan (baseline + expansions)
- User can:
  - Accept blueprint
  - Edit key assumptions (natural language)
  - “Use Minimal Blueprint” (fallback)
- Output: `blueprint_spec` + `blueprint_version`

**Step C — Project Setup**
- After creation, Overview shows Setup Checklist with a top item:
  - ✅ Goal & Blueprint (completed)
  - then Data & Personas → Rules & Logic → Run Parameters → Universe Map

> Note: The UI layout can remain simple; the key is that the project now has a persisted “brain” (blueprint).

---

### 2.2 Downstream pages become “Blueprint-guided”
Each section page should show a **Guidance Panel** at top:

- “Recommended inputs for *this* project”
- “Why these inputs matter”
- One-click actions:
  - “Generate personas that match these segments”
  - “Attach evidence URLs”
  - “Auto-fill defaults from blueprint”

**Important:** The guidance content must come from the stored `blueprint_spec` (not ad-hoc LLM every page load).

---

### 2.3 TEG Universe Map integration
Universe Map (TEG) must have a stable root:

- **Root node:** project goal summary (from goal_spec)
- **Baseline verified node:** latest baseline run outcome (if exists)
- If no baseline run yet:
  - Show a “Baseline not run” placeholder node with a CTA: “Run Baseline”

**TEG Expand uses Blueprint**
- The Expand prompt context must include:
  - goal_spec summary
  - blueprint_spec slots (drivers, uncertainties, constraints)
  - evidence excerpts (if any)
  - selected parent node outcome summary (if verified)

This ensures expansions are **domain-relevant** and not random.

---

## 3) Data Contracts (Persisted objects)

### 3.1 Goal Spec (persisted on project)
Minimum required fields:
- `goal_text` (original user prompt)
- `time_horizon` (when the prediction is about)
- `region/context` (if applicable)
- `entities` (actors/objects in scope)
- `target_metric` (what outcome means)
- `evaluation_method` (how we judge correctness, if backtest)
- `assumptions` (user-confirmed)
- `attachments` (URLs, files if supported)
- `temporal_cutoff_snapshot` (already implemented)

### 3.2 Blueprint Spec (persisted & versioned)
Minimum required fields:
- `domain` + confidence
- `recommended_mode`: collective / targeted / hybrid
- `required_inputs`:
  - `data_inputs`: list (min viable + high accuracy)
  - `persona_inputs`: list (optional)
  - `environment_inputs`: list
  - `policy_levers`: list (variables the user can tweak)
- `slot_guidance`: per section instructions + acceptance criteria
- `initial_run_plan`: baseline + recommended expansions
- `teg_seed_rules`: what the first-layer branches should represent
- `audit`: blueprint creation model + tokens + cost + cutoff compliance

---

## 4) Backend Implementation Plan

### 4.1 Restore/ensure Blueprint endpoints & PIL flow
Your repo already describes Blueprint + PIL flow and endpoints. The task is to:
- Ensure endpoints are reachable in production routes
- Ensure Create Project UI calls them
- Ensure PIL jobs run reliably and statuses are surfaced to UI

**Must-have statuses**
- Blueprint: `CREATED → ANALYZING → SLOTS_READY → FINALIZED` (or similar)
- PILJob: `PENDING → RUNNING → COMPLETED/FAILED`
- Failures must store `{stage, message, correlation_id, retryable}`

### 4.2 New/updated endpoints (only if needed)
Prefer reusing existing endpoints. If missing, add minimal wrappers:
- `GET /api/v1/projects/{id}/goal_spec`
- `GET /api/v1/projects/{id}/blueprint`
- `POST /api/v1/projects/{id}/blueprint/regenerate` (version bump)
- `POST /api/v1/projects/{id}/goal_assistant/questions` (generate clarifying Qs)

### 4.3 TEG should reference blueprint
- TEG expand endpoint must accept `blueprint_version` or be able to load blueprint by project_id
- Store the blueprint_version used for each draft scenario node (auditability)

### 4.4 Degrade gracefully (never remove features)
If:
- OpenRouter key missing/invalid
- Worker down
- PIL job fails

Then:
- Goal Assistant shows fallback: “Manual Goal Spec” form (minimal)
- Blueprint step shows fallback: “Minimal Blueprint” template (editable)
- System stores the fallback blueprint version so the project is still consistent

---

## 5) Frontend Implementation Plan (Next.js)

### 5.1 Create Project Wizard: restore + improve
Add two steps before existing settings:
1) Goal Assistant (Q&A)
2) Blueprint Preview (accept/edit)

Then proceed to:
- mode selection (if still needed) BUT:
  - default should be blueprint-recommended
  - user may override (logged)

### 5.2 Overview: Setup Checklist must reflect Goal/Blueprint
- Add a checklist item “Goal & Blueprint”
- Make it open the blueprint preview panel (read-only + regenerate)

### 5.3 Guidance Panels on section pages
At minimum implement on:
- Data & Personas
- Rules & Assumptions
- Run Center (run parameter suggestions)

Guidance Panel pulls from blueprint_spec.

### 5.4 Universe Map: show seed context
In Node Details for root/baseline:
- show blueprint summary (collapsed)
- show “recommended first expansions” based on blueprint

---

## 6) Engineering Tasks (Ordered, testable)

### Task 1 — Audit current regression
- Identify why Goal Assistant/Blueprint disappeared:
  - feature flags / gating / route removal / nav removal
- Document the exact regression cause in the final report.

**QA**
- Confirm current production build lacks these steps (baseline).

---

### Task 2 — Restore Create Project steps
- Implement Goal Assistant step UI
- Implement Blueprint Preview step UI
- Persist goal_spec and blueprint_spec to backend

**QA**
- Create Project requires Goal step completion OR manual fallback.
- Blueprint preview always appears (even in fallback mode).

---

### Task 3 — Wire to existing Blueprint + PIL endpoints
- Ensure frontend triggers blueprint creation and monitors job status
- Ensure backend returns blueprint slots/guidance to UI

**QA**
- Blueprint reaches FINALIZED (or equivalent) on a healthy env.
- If job fails, UI shows fail reason + “Use Minimal Blueprint” option.

---

### Task 4 — Guidance Panel (Data & Personas first)
- Read blueprint_spec.required_inputs and show:
  - “What to provide”
  - “Why it matters”
  - action buttons for common tasks

**QA**
- For an election-like goal, personas guidance emphasizes demographics/segments.
- For a supply forecast goal, data guidance emphasizes time series + constraints.

---

### Task 5 — TEG integration with blueprint
- Universe Map root node shows goal summary
- Expand uses blueprint context
- Store blueprint_version used for draft nodes

**QA**
- Expansions are relevant to the domain and not generic.
- RAW view shows blueprint_version reference.

---

### Task 6 — Regenerate / Versioning
- Allow user to regenerate blueprint (new version) and keep history
- TEG nodes created under prior version remain auditable

**QA**
- Blueprint version increments.
- Old nodes retain their version reference.

---

### Task 7 — Fallback reliability mode
- If LLM key missing or job fails:
  - manual goal spec + minimal blueprint
  - user can still run baseline and use TEG with limited guidance

**QA**
- No flow becomes blocked by “feature missing”.
- UI never hides Goal/Blueprint; only switches to fallback.

---

## 7) Acceptance Tests (E2E)

### Test A — Election-like project (persona-heavy)
1) Create Project → Goal Assistant Q&A completes
2) Blueprint preview shows:
   - recommended mode = collective/hybrid
   - persona segments needed
3) Data & Personas guidance instructs which segments to generate
4) Universe Map root shows goal + blueprint summary
5) Expand generates draft scenarios relevant to election context

**Pass**
- User can reach Universe Map with a coherent tree in < 3 minutes.

### Test B — Production output forecast (data-heavy)
1) Create Project: “Predict next year production output for Product X”
2) Blueprint emphasizes time series inputs, constraints, cost drivers
3) Data guidance shows required dataset categories
4) Universe Map expands into data-driven scenarios (cost shocks, demand changes)

**Pass**
- Personas are optional; data guidance is dominant.

### Test C — LLM outage fallback
1) Disable OpenRouter key / simulate failure
2) Create Project still possible via manual goal + minimal blueprint
3) Universe Map still usable (limited expand if no LLM; baseline run remains)

**Pass**
- No missing pages; clear fallback messaging.

---

## 8) Deliverables (Engineer must produce)

Create a repo-root report:
- `REPORT_GOAL_BLUEPRINT_TEG_RESTORE.md`

Must include:
- Task checklist (1–7)
- Regression root cause summary
- Screenshots/GIF:
  - Goal Assistant step
  - Blueprint preview
  - Data & Personas guidance panel
  - Universe Map showing goal-root + blueprint-driven expand
- API changes list
- DB/migrations if any
- QA results for Tests A/B/C
- Known issues & next steps

---

*End of document.*

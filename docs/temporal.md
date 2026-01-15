# temporal.md — Temporal Knowledge Isolation (Project-Level Temporal Context Lock)
**Status:** Production hardening & implementation specification (no code)

This document defines how to implement **Temporal Knowledge Isolation** in an already-running **production** Future Predictive AI Platform. The goal is to prevent **future data leakage** during backtests/historical validation by enforcing a **project-level temporal cutoff** from the moment a project is created, and by ensuring all downstream actions inherit the same cutoff automatically.

> **Non-negotiable:** Temporal isolation is enforced via **data/tool gating + auditability**, not by claiming the foundation model “forgot” anything.

---

## How to use this document (for engineers)
- Treat this as the **single source of truth** for Temporal Isolation.
- **Do not implement partial isolation.** If a data path bypasses the DataGateway, the system fails compliance.
- Every “Backtest” run must produce a **Run Audit Package** (manifest + lineage + versions + seed) and expose a **PASS/FAIL** isolation indicator.

---

## Production-grade additions (hardening requirements)
These requirements **extend** (not replace) the specification below.

### 1) Reliability & safety requirements (production)
- **Fail closed** in strict backtest: if timestamps are missing/ambiguous, block the source or the subset (based on policy), and surface a clear UI error.
- **Idempotency** for DataGateway requests per run: repeated requests with same normalized params must produce identical manifest entries and consistent hashes.
- **Observability**
  - Emit structured logs for: cutoff blocks, filtered record counts, unsafe source usage attempts, manifest creation failures.
  - Metrics: `backtest_cutoff_blocks_total`, `unsafe_source_blocks_total`, `manifest_write_failures_total`, `audit_pass_rate`, `audit_fail_rate`.
- **Security**
  - Treat the manifest as sensitive (it may reveal endpoints/queries). Apply role-based access and redact secrets.
- **Performance**
  - Support caching *within* a run (keyed by normalized params + as_of_datetime) without violating audit.
- **Change management**
  - Temporal Context is locked by default. Any unlock/change requires admin-only action, must write an immutable audit trail, and must invalidate “comparability” flags.

### 2) Compatibility guarantees (production)
- Existing production projects must continue functioning (default to Live mode).
- New Backtest projects must enforce strict gating from Day 1.

### 3) Source governance (production)
- Maintain a **Source Capability Registry** as a governed artifact:
  - Each source has an owner, review date, and compliance classification.
  - Any change to the registry increments `policy_version`.

---

## Canonical specification (verbatim, no deletions)  
> The section below is the full instruction set you must implement. It is included **without any deletions**.  
> Where it previously said “MVP”, interpret it as “existing production system” (see “Errata & Clarifications” after the block).

```text
You are a senior full-stack engineer joining an existing MVP of a “Future Predictive AI Platform”.
Current situation: The MVP is already built and uses OpenRouter for LLM calls. The system currently calls various external APIs directly and has NO temporal knowledge isolation. The Create Project flow already has a “Recommended Core” (not smart yet) — keep it as-is for now.

Your mission: Implement PROJECT-LEVEL Temporal Knowledge Isolation (Temporal Context Lock) so that the moment a project is created, it becomes temporally isolated. Every subsequent action (runs, branches, asks, calibration, replay) must automatically inherit the project’s temporal cutoff and must not access post-cutoff data.

IMPORTANT RULES:
- Do NOT write code in your response. Produce implementation plans, specs, UI copy, data model changes, and acceptance tests only.
- The solution must be auditable: it must generate proof that no future data leaked into any backtest run.
- Assume we will continue to use OpenRouter (no “true forgetting” of model weights). Temporal isolation must be enforced by data/tool gating + audit, not by claiming the model forgot.

========================
1) OBJECTIVES
========================
Implement Temporal Knowledge Isolation such that:

A) Project-level Temporal Context Lock
- Every Project has a locked Temporal Context at creation time:
  - mode (Live or Backtest)
  - as_of_datetime + timezone
  - isolation_level
  - allowed_sources policy
  - policy_version
- This Temporal Context must be immutable by default after project creation (allow changes only via explicit admin action + full audit trail, not normal UI).

B) Data Gateway Enforcement (Critical)
- All external data access (APIs, retrieval, search, any “tools”) must go through a single DataGateway layer.
- DataGateway must enforce the cutoff so that, in backtest mode, no data with timestamp > as_of_datetime can be used.

C) Auditability (Non-negotiable)
- Every run must produce a “Run Audit Package” containing:
  - Data Manifest (sources, endpoints, time ranges, record counts, payload hashes)
  - Feature/Derivation Lineage metadata (what was derived from what; window boundaries; timestamps)
  - Versions (dataset/rules/engine/policy) + random seeds
- Provide a Run Audit Report view/page/API to show the above.

D) LLM Containment (OpenRouter)
- The LLM must not directly browse or call raw APIs.
- The LLM can only request data through DataGateway-exposed tools.
- The final numeric predictions must come from the simulation/aggregation engine, not from the LLM “guessing”.
- The LLM may:
  - compile natural language into structured event scripts
  - propose scenarios
  - explain results using only run artifacts + manifest references

========================
2) WHERE TO CHANGE THE CREATE PROJECT FLOW
========================
Current flow (MVP):
Step 1: “What do you want to predict?” (goal)
Step 2: Choose Core (Collective Dynamics / Targeted Decision / Hybrid Strategy) + shows “Recommended Core”
Step 3: Basic settings (project name, tags, etc.)

Update flow (minimal, keep existing “Recommended Core” logic unchanged):
Step 1: Prediction goal
Step 2: Temporal Context (NEW, required confirmation)
Step 3: Choose Core (existing) + show Recommended Core (keep current behavior)
Step 4: Basic settings

Rationale:
- Temporal isolation must be bound before any data fetch, simulation, or branching occurs.
- Once set, every downstream action reads Project Temporal Context automatically.

========================
3) TEMPORAL CONTEXT STEP — UI SPEC + COPY (NO CODE)
========================
Design principle: “Simple for normal users, strict for backtesting.”

Step Title:
- “Time Context (Prevents Future Data Leakage)”

Step Layout:
A) Mode Selector (radio buttons)
- Live (default)
- Backtest (Historical)

Helper text under Mode:
- Live: “Uses the latest available data at the time you run the simulation.”
- Backtest: “Locks the project to an ‘as-of’ time so the system cannot use information from the future. Recommended for validation and benchmarking.”

B) As-of Date/Time (only visible if Backtest)
Field label:
- “As-of Date & Time”
Default:
- user’s local timezone (Asia/Kuala_Lumpur as default display; allow changing timezone)
Helper text:
- “All data used in this project will be restricted to timestamps on or before this moment.”
Validation copy:
- If empty: “As-of time is required for Backtest mode.”
- If future date: “As-of time cannot be in the future.”

C) Timezone (visible for both modes, but emphasized in Backtest)
Field label:
- “Timezone”
Default:
- Asia/Kuala_Lumpur
Helper text:
- “Time cutoffs and timestamps are evaluated using this timezone.”

D) Isolation Level (advanced toggle; default Level 2 in Backtest)
Label:
- “Isolation Strictness”
Options:
- Level 1 (Basic): “Cutoff applied where supported by sources; may exclude sources without timestamps.”
- Level 2 (Strict, Recommended): “All data must pass the cutoff check; sources without timestamps are blocked in backtests.”
- Level 3 (Audit-First, Optional): “Adds blind/reveal protocol and stricter audit requirements.” (You may stub this for now but design the fields.)

E) Allowed Sources (only show in Backtest, collapsible)
Title:
- “Allowed Data Sources for This Backtest”
Behavior:
- Show the list of current external APIs/integrations used by MVP.
- For each source, display capability badge:
  - “Supports historical/as-of queries”
  - “Timestamped but no native as-of filtering”
  - “No timestamps / latest-only (unsafe for backtest)”
Default selection rules:
- Auto-select sources that support historical/as-of queries.
- Auto-disable (blocked) sources that are latest-only or missing timestamps in Level 2+.
Copy for blocked sources:
- “Blocked in Strict Backtest: this source cannot guarantee pre-cutoff data.”

F) Confirmation (required checkbox for Backtest)
Checkbox label:
- “I understand this project will be locked to the selected As-of time to prevent future leakage.”
Note:
- “Changing the As-of time later will invalidate audit comparability and is restricted.”

Step CTA:
- “Continue”

========================
4) DATA MODEL / SCHEMA CHANGES (SPEC ONLY)
========================
Add/extend Project with:
- mode: enum('live','backtest')
- as_of_datetime: timestamp (required for backtest; for live store created_at or last_run_time policy)
- timezone: string (IANA)
- isolation_level: int (1..3)
- allowed_sources: json array (source identifiers + policy)
- policy_version: string
- temporal_lock_status: enum('locked','unlocked') default 'locked'
- temporal_lock_history: (audit trail: who/when/why changed, if you allow admin unlock later)

Add/extend Run with:
- project_id
- run_id
- created_at
- random_seed
- engine_version
- ruleset_version
- dataset_version
- policy_version
- scenario_patch (diff from parent node)
- data_manifest_ref (pointer)
- lineage_ref (pointer)
- telemetry_ref (pointer)
- results_ref (pointer)
- cutoff_applied_as_of_datetime (copied from project at run-time; must match unless admin override)

Node/Edge integration requirement:
- Every Node must reference a Run (or a set of Runs if aggregated).
- Forking creates a new Node with a scenario_patch and a new Run referencing the same project temporal context.

========================
5) DATA GATEWAY (CRITICAL MODULE) — BEHAVIOR SPEC
========================
Create a single service/module called DataGateway.
All external API calls must be routed through DataGateway (no direct calls from simulation, UI, or LLM tool code).

DataGateway responsibilities:
1) Cutoff enforcement:
- If project.mode='backtest':
  - Enforce timestamp <= as_of_datetime on all returned records.
  - If an API supports time_end/as-of parameters: always include them in the request.
  - If an API returns mixed timestamps: filter strictly and log what was removed.
  - If a source provides no timestamps or is latest-only:
    - Level 1: mark “unsafe” and exclude from run by default, or allow only if explicitly whitelisted with warning
    - Level 2+: block entirely (hard fail) unless using an approved snapshot dataset

2) Source capability registry:
- Maintain a registry that declares per-source:
  - timestamp availability
  - historical query support
  - required params for cutoff
  - safe/unsafe classification per isolation level

3) Data Manifest generation per run:
For every DataGateway request, record:
- run_id
- source_name
- endpoint / query type
- request parameters (normalized)
- requested time window (start/end) + as_of_datetime
- record count returned + record count filtered out
- normalization hash of the payload (content hash)
- retrieved_at timestamp
Store as the Data Manifest for the run.

4) Strict mode behavior:
- In Level 2+, if any returned record lacks a timestamp → treat as unsafe and block or exclude that portion.
- Provide clear error messages so the UI can tell the user which source was blocked and why.

========================
6) LLM CONTAINMENT & TOOLING POLICY (OPENROUTER)
========================
We cannot “make the model forget” weights. We must enforce isolation by system design.

Rules:
- LLM must not directly browse or call raw APIs.
- Provide tool(s) that ONLY call DataGateway and only return pre-cutoff data.
- All prompts in backtest mode must include:
  - “You may only use information returned in this run context / DataGateway outputs.”
  - “If unsure, you must say you are unsure.”

Output auditing (required):
- Implement an auditor that checks LLM outputs for:
  - Specific facts/numbers/entities not present in the run’s manifest/context
  - If detected: flag the output, lower confidence, and require regeneration with stricter constraints.

Prediction responsibility:
- LLM must not produce the final numeric prediction directly.
- The simulation engine / aggregation engine produces the prediction distribution and metrics.
- LLM can only summarize/explain those engine outputs.

========================
7) BACKWARDS COMPATIBILITY
========================
Existing projects:
- Default to mode='live'
- as_of_datetime = project.created_at (or last_run_time policy)
- isolation_level = 1
- temporal_lock_status='locked'
No breaking behavior for existing runs; new Backtest projects must follow strict gating.

========================
8) IMPLEMENTATION PLAN (THE ENGINEER MUST EXECUTE THIS PLAN)
========================
Execute in this order (no detours; do not start UI polish before the DataGateway exists):

Phase 1 — Foundation Contracts (must be done first)
1) Add Project Temporal Context fields + migrations + audit trail spec
2) Add/extend Run fields to store cutoff, versions, seed, manifest references
3) Define source capability registry schema (source -> timestamp/historical support)

Phase 2 — DataGateway (must be done next)
4) Implement DataGateway routing layer and replace all direct API calls with DataGateway calls
5) Enforce cutoff rules per source (block unsafe sources in strict backtests)
6) Generate and persist per-run Data Manifest with hashes

Phase 3 — Create Project UI Integration
7) Add Temporal Context step to Create Project flow using the UI spec above
8) On project creation: lock Temporal Context, persist policy_version, and store allowed_sources selection
9) Ensure all subsequent actions read Project Temporal Context automatically (no manual cutoff passing in UI)

Phase 4 — LLM Tooling & Audit
10) Restrict LLM data access to DataGateway tools only
11) Add backtest-mode policy text to system prompts (no browsing, only context)
12) Implement output auditor: flag hallucinated or non-manifest facts

Phase 5 — Run Audit Reporting
13) Build “Run Audit Report” view/page/API that shows:
    - as_of_datetime, timezone, isolation level
    - all sources accessed + endpoints + time windows
    - payload hashes + counts filtered out
    - versions + seed
14) Add a prominent “Temporal Isolation: PASS/FAIL” indicator per run

Phase 6 — Validation Tests (must pass before merge)
15) Create acceptance tests listed below and ensure they pass.

========================
9) ACCEPTANCE TESTS / VALIDATION (REQUIRED)
========================
A) Project-level lock
- Create a backtest project with as_of_datetime = X.
- Confirm the project is locked and the cutoff is stored.
- Any subsequent run automatically uses X (no manual passing).

B) Cutoff enforcement
- In backtest mode, request data that would include timestamps > X.
- Verify DataGateway filters or blocks and logs filtered counts.
- Verify “unsafe/no timestamp” sources are blocked in Level 2+.

C) Latest-only source protection
- Attempt to use a latest-only/no-timestamp API in backtest strict mode.
- System must hard fail with a clear error: “Blocked in Strict Backtest”.

D) Run Audit Package
- For every run:
  - Data Manifest exists
  - Contains normalized request params + time window + payload hashes
  - Shows filtered-out record counts (if any)
  - Stores engine/rules/dataset/policy versions + random seed

E) Reproducibility
- Re-run same project, same config, same seed:
  - deterministic components produce identical outputs within tolerance.

F) LLM containment & audit
- Attempt to force the LLM to reference external post-cutoff facts:
  - the auditor must flag it and require regeneration or lower confidence.
- The final numeric prediction must match the engine output, not LLM guess.

========================
10) DELIVERABLES (WHAT YOU MUST PRODUCE)
========================
1) Updated Create Project flow with a Temporal Context step (per UI copy/spec above)
2) Project + Run schema updates + locking behavior
3) DataGateway replacing all direct API calls + per-run manifest + cutoff enforcement
4) LLM tooling restrictions + output auditor
5) Run Audit Report view/page/API and PASS/FAIL isolation indicator
6) Test suite proving cutoff enforcement and audit correctness

End of instructions.
```

---

## Errata & clarifications (production context)
- Wherever the block says “MVP”, interpret as **existing production system**.
- “Backwards compatibility” must preserve production stability; isolate changes behind feature flags if needed.
- “No code in response” applies to this spec; implementation must be production-grade with:
  - retries/timeouts/circuit breakers
  - request normalization for hashing
  - secret redaction in manifests
  - RBAC for audit views

---

## Engineering checklist (quick reference)
- [ ] Create Project: Temporal Context step added; lock stored; user confirmation required in Backtest
- [ ] DataGateway exists and is the only path to external data
- [ ] Source Capability Registry exists; policy_version increments on change
- [ ] Backtest strict mode blocks unsafe sources; errors are user-readable
- [ ] Per-run Data Manifest + Lineage persisted with hashes
- [ ] Run Audit Report view/API available; PASS/FAIL indicator shown
- [ ] LLM cannot call raw APIs; only DataGateway tools; auditor flags non-manifest claims
- [ ] Tests pass: cutoff enforcement, unsafe-source block, reproducibility, audit package integrity

---
End of temporal.md

# Future Predictive AI Platform — Project Development Manual (project.md)

**Document type:** End-to-end engineering build manual (no code)  
**Audience:** Engineering team + AI coding agent(s) building from 0 → production  
**Scope:** Full system blueprint: foundations → core engines → UX surfaces → reliability → operations  
**Date:** 2026-01-08 (Asia/Kuala_Lumpur)  
**Version:** v1.0 (living document; all changes must be versioned)

---

## 0) What this document is (and is not)

### What this is
A **construction-grade blueprint** for building a production-ready **Future Predictive AI Platform** that:
- Predicts outcomes by **running reversible, on-demand simulations** (not continuous always-on worlds).
- Supports both:
  - **Society Mode:** many agents interacting → emergent outcomes.
  - **Target Mode:** one/few key actors + many possible event sequences → path distributions.
- Produces **auditable, explainable, reproducible** outputs with confidence reporting.
- Visualizes simulations through:
  - A **Universe Map** (parallel-universe graph of branches + probabilities).
  - A **2D telemetry renderer** (Farm-Story-like view as replay, *read-only*, derived from logs).

### What this is not
- Not a business model or revenue plan.
- Not code or SQL.
- Not a “nice-to-have feature list” without dependencies.
- Not a promise that any domain reaches 80% accuracy without **calibration, data quality, and evaluation**. This manual builds the system required to *measure and improve* accuracy, not hand-wave it.

---

## 1) Product principles (non-negotiable)

These principles are architectural constraints. Violating them causes costly rebuilds.

### P1 — Reversible-by-design
- You never “edit the past.” You **fork** a new branch from a prior node.
- Every run is reproducible given: **versions + config + seed**.
- A Node is a **world version**, not a UI artifact.

### P2 — On-demand execution (default)
- Simulations run only on explicit triggers: `Run`, `Ask`, `Tune`, `Expand`.
- “Replay” must be **read-only** and must not trigger simulation.

### P3 — Auditable predictions
Every prediction must ship with:
- Data provenance (what was used, which version).
- Run provenance (config + engine version + seed).
- Reliability metrics (calibration score, stability, drift warning).

### P4 — Separation of concerns
- Simulation engine is **headless** (no UI assumptions).
- 2D visualization is a **telemetry renderer** (read-only).
- LLMs are **planners/compilers**, not tick-by-tick brains inside large-scale agent loops.

### P5 — Progressive complexity for users
- Most users get a **3-step flow** (Ask → Run → Result).
- Expert controls exist but are hidden behind “Advanced” and progressive disclosure.

### P6 — Production from Day 1
- Auth, rate limits, tenancy boundaries, logging, monitoring, and secure secrets handling are part of Phase 0–2, not an afterthought.

---

## 2) Glossary (shared language)

- **Persona:** canonical profile template describing human-like preferences, biases, perceptions, and action tendencies.  
- **Agent:** a runtime instance derived from a Persona (plus current state + social edges).  
- **Target:** a specific individual (or small set) in Target Mode modeled as a decision process (state machine / planning).  
- **World State:** the complete set of environment variables + agent states at a point in time.  
- **Tick:** one discrete time step in simulation (logical time; not tied to rendering FPS).  
- **Event:** an intervention described by a structured “event script” that modifies environment variables and/or agent perceptions.  
- **Scenario:** a particular configuration of events/variable deltas, often used to create branches.  
- **Node:** a parallel-universe snapshot representing (state reference + scenario patch + aggregated outcomes + probability + telemetry refs).  
- **Edge:** a transformation from one node to another (event/variable/NL-compiled intervention).  
- **Run:** one execution instance producing outcomes + telemetry under a RunConfig.  
- **Telemetry:** a compressed log of key state deltas and events enabling replay/explanation.  
- **Calibration:** evaluating and tuning model parameters against known historical outcomes without leakage.  
- **Stability:** output consistency across seeds / small perturbations.  
- **Drift:** data distribution shift relative to calibration regime.

---

## 3) System overview

### 3.1 Core user-facing workflow (happy path)
1. **Create Project:** user describes prediction goal in natural language.
2. System recommends:
   - **Prediction Core:** Collective Dynamics / Targeted Decision / Hybrid Strategic
   - **Domain Template** (optional accelerator)
3. User hits **Run Baseline** → Universe Map creates **Root Node**.
4. User uses **Ask “What if …”** → Event Compiler generates scenarios → branches appear as nodes/edges.
5. User explores Universe Map, expands clusters, compares branches.
6. User optionally opens **2D Replay** to see “what happened” in a branch.
7. Reliability panel shows calibration/stability/drift and confidence.

### 3.2 Engineering workflow (what must be true)
- Every UI action maps to:
  - Creating/reading **RunConfig**
  - Creating **Run** artifacts
  - Writing **Node** records
  - Writing **Telemetry** references
- No UI state is “truth.” Truth is in persisted Node/Run/Telemetry artifacts.

---

## 4) Architecture blueprint (services & layers)

> Think “house”: foundations → structural frame → wiring/plumbing → surfaces → inspections.

### 4.1 Layered architecture
**Layer 0 — Contracts & Governance**
- Schemas, versioning, deterministic contracts, data provenance rules.

**Layer 1 — Core Execution Engines**
- Society Mode engine (agents + scheduler + rules insertion points)
- Target Mode planner (state machine + action space + constraints + search)
- Hybrid engine (key actors + context population)

**Layer 2 — Branching & Universe Graph**
- Scenario generator, clustering, progressive expansion, conditional probability.

**Layer 3 — Reliability & Calibration**
- Historical replay, metrics, bounded auto-tune, drift detection.

**Layer 4 — Telemetry & Replay**
- Snapshot manager, delta log, deterministic replayer, query interfaces.

**Layer 5 — Visualization & API**
- Universe Map UI, editors, result views, 2D renderer, admin dashboards.

### 4.2 Recommended service split (MVP → scale)
**MVP (single backend + worker pool)**
- `api-service` (REST/GraphQL): auth, project CRUD, node graph, results.
- `sim-worker` (queue-based): runs simulations/plans, writes artifacts.
- `store` (Postgres + object storage): nodes/runs metadata + telemetry blobs.

**Scale (optional later)**
- Dedicated `simulation-service` with separate compute cluster
- Dedicated `telemetry-service` (hot querying)
- Dedicated `calibration-service` (batch jobs)

---

## 5) Tech stack (recommended, cost-effective, production-minded)

> This is guidance; you may adapt to fit your existing repo, but keep contracts identical.

### 5.1 Frontend
- **React + Next.js** (App Router), TypeScript
- Rendering:
  - Universe Map: Canvas/WebGL (for large graphs) or performant SVG for small graphs
  - 2D Replay: Canvas (tilemap style), optional WebGL later
- Performance:
  - Virtualized lists, incremental graph rendering, lazy data fetching, skeleton states
- State/data:
  - React Query / TanStack Query for caching & background refetch
  - WebSocket/SSE optional for run progress updates

### 5.2 Backend API
- **Python FastAPI** or **Node.js (NestJS)** (choose one; keep consistent)
- Auth: JWT + refresh tokens, OAuth optional
- Rate limiting: Redis-based
- Multi-tenant: tenant_id on all resources

### 5.3 Simulation & planning runtime
- Primary: **Python** (rapid iteration; rich ML ecosystem)
- Performance-critical modules later: Rust/C++ extensions (optional)
- Task queue: **Redis Queue / Celery / BullMQ** (choose to match backend)
- Determinism: strict seeded RNG + pinned dependency versions

### 5.4 Storage
- Postgres: projects, nodes, edges, runs, configs, reliability reports
- Object storage (S3-compatible): telemetry blobs, snapshots, large artifacts
- Cache: Redis (configs, hot nodes, progress states)
- Optional: vector DB for persona retrieval; graph DB not required early (Postgres adjacency is enough)

### 5.5 Observability & operations
- Structured logs (JSON), request tracing
- Metrics (Prometheus/OpenTelemetry)
- Error tracking (Sentry or equivalent)
- CI/CD: GitHub Actions
- Infrastructure: Docker + (optional) Kubernetes later

---

## 6) Data contracts (schemas you must lock early)

> These are “wiring diagrams.” Once UI depends on them, changes are expensive.

### 6.1 ProjectSpec (per project)
Minimum required fields:
- `project_id`, `tenant_id`
- `title`, `goal_nl` (natural-language goal)
- `prediction_core` (Collective/Target/Hybrid)
- `domain_template` (optional)
- `created_at`, `updated_at`
- `default_horizon` (ticks/time window)
- `default_output_metrics` (e.g., outcome distribution, trend lines)
- `privacy_level` (private/team/public)
- `policy_flags` (safety/ethics constraints)

### 6.2 Persona (canonical form)
Persona must be ingestible and convertible to both modes.
- Identity:
  - `persona_id`, `label`, `source` (uploaded/generated/deep_search)
- Demographics (structured, normalized)
- Preferences vector(s): media diet, consumption preferences, risk attitude
- Perception weights: trust in sources, attention allocation, priors
- Bias parameters: loss aversion, confirmation bias, conformity, etc.
- Action priors: baseline propensity for actions
- Uncertainty:
  - `uncertainty_score`
  - `evidence_refs` (for deep search)
- Versioning:
  - `persona_version`, `schema_version`

### 6.3 Agent (runtime instance)
Agent is derived and not necessarily persisted in full.
- `agent_id`, `persona_ref`
- `state_vector` (current)
- `memory_state` (bounded, optional)
- `social_edges` (neighbors + weights)
- `location/region` (for 2D placement & aggregation)

### 6.4 Event Script
Events must be executable without LLM involvement at runtime.
- `event_id`
- `event_type` (policy/media/shock/individual action)
- Scope:
  - affected regions, affected persona segments, start/end ticks
- Deltas:
  - environment variable deltas
  - perception deltas (e.g., media topic weight)
- Intensity profile: instantaneous/decay/lagged
- Uncertainty + assumptions
- Provenance:
  - compiled_from (NL prompt)
  - compiler_version

### 6.5 RunConfig
- Versions:
  - `engine_version`, `ruleset_version`, `dataset_version`, `schema_version`
- Randomness:
  - `seed`, `seed_strategy` (single/multi)
- Execution:
  - `horizon`, `tick_rate` (logical), `scheduler_profile`
- Logging:
  - `logging_profile` (sampling, keyframes)
- Scenario patch:
  - variable changes, event bundle, constraints (target mode)

### 6.6 Run artifact
- `run_id`, `node_id`, `project_id`
- `run_config_ref`
- Status: queued/running/succeeded/failed
- Timing: start/end, tick count
- Outputs:
  - `results_ref`
  - `telemetry_ref`
  - `snapshot_refs` (optional)

### 6.7 Node & Edge (Universe Map)
**Node:**
- ids: `node_id`, `parent_node_id`
- `scenario_patch_ref` (what changed)
- `run_refs` (1+ runs aggregated)
- `aggregated_outcome` summary + metric refs
- `probability` (conditional to parent)
- `confidence` + reliability refs
- `telemetry_ref` for replay
- `cluster_id` (optional)

**Edge:**
- `edge_id`, `from_node_id`, `to_node_id`
- `intervention_ref` (event script / variable delta / NL query)
- `explanation_ref` (why this branch exists)

### 6.8 Telemetry (replay contract)
Telemetry is “playback evidence,” not full world state.
- Keyframes: world/region snapshots at intervals
- Delta stream:
  - agent segment changes (aggregated)
  - key agent actions (sampled)
  - event triggers
  - metric time series
- Indexes for query:
  - by tick
  - by region
  - by persona segment
  - by key agent id (if tracked)

---

## 7) Reliability & calibration contracts (benchmark-level)

### 7.1 Reliability Report (per node/run)
- Calibration score(s): aligned historical replays
- Stability score: variance across seeds
- Sensitivity summary: key variables and impact direction
- Drift status: data distribution divergence warnings
- Data gaps: missing or weak evidence areas
- Confidence level: High/Medium/Low with reasons

### 7.2 Anti-leakage guardrails (mandatory)
- Historical calibration must enforce “time cutoff.”
- Deep research ingestion must tag timestamps; prevent future data mixing into past runs.

---

## 8) Security, privacy, and abuse prevention (production must-haves)

### 8.1 Multi-tenancy boundaries
- Tenant isolation at DB query layer (row-level security or strict query scoping).
- Separate object storage prefixes per tenant.

### 8.2 Auth & permissions
Roles:
- Owner / Admin / Analyst / Viewer
Permissions per project:
- run simulations, edit personas, export artifacts, share links

### 8.3 Rate limiting & job quotas
- Per-tenant concurrency limits
- Per-project run budget limits (configurable)
- Abuse protection for “Deep Search” and “Ask”

### 8.4 Data protection
- Encrypt secrets at rest
- Signed URLs for telemetry downloads (short-lived)
- PII minimization: persona data stored as needed; support anonymization pipelines

### 8.5 Safety and ethical constraints
- Policy flags on projects:
  - disallow operational harm guidance
  - require explanation layers for sensitive domains
- Audit logs for who ran what, when.

---

## 9) Performance & scalability design (avoid rebuild later)

### 9.1 Frontend performance requirements
- Universe Map must handle:
  - Thousands of nodes via clustering + progressive expansion
- Required techniques:
  - lazy loading node details
  - virtualization for lists
  - incremental graph layout (avoid full re-layout on every update)
  - optimistic UI for run submission, real-time progress events

### 9.2 Backend performance requirements
- All simulation runs are async:
  - API only enqueues and returns run_id
- Caching:
  - hot nodes and frequently used templates/personas
- Deterministic replay:
  - store enough to replay without re-running simulation

### 9.3 Engine performance requirements (MVP)
- Society Mode:
  - rule-driven core loop; avoid LLM-in-the-loop at scale
  - segmentation: compute aggregated dynamics per segment when possible
- Target Mode:
  - path search uses pruning + clustering; supports progressive expansion

---

## 10) Testing & QA strategy (must be built in)

### 10.1 Determinism tests (non-negotiable)
- Same RunConfig + seed → same aggregated outcome & telemetry signatures
- Any change in engine/ruleset version must update golden baselines intentionally

### 10.2 Simulation validity tests
- Unit tests for:
  - rule insertion points
  - event script execution
  - scheduler correctness
- Integration tests:
  - end-to-end “Ask → branches → replay”
- Load tests:
  - concurrency and queue backpressure

### 10.3 Reliability tests
- Calibration pipeline must produce reports
- Drift detection must trigger under synthetic shifts

---

## 11) Phase plan (development order with dependencies)

> Each phase has: objective, deliverables, dependencies, acceptance criteria, and “do not do yet” warnings.

---

### Phase 0 — Foundations (Contracts, Versioning, Determinism)
**Objective:** Prevent architectural rework later.

**Deliverables**
- Finalize schemas in Section 6
- Artifact versioning strategy:
  - `engine_version`, `ruleset_version`, `dataset_version`, `schema_version`
- Seed and RNG policy:
  - how seeds are generated, stored, and used
- Minimal storage layout:
  - Postgres tables for projects/nodes/edges/runs/configs
  - object storage buckets/prefixes for telemetry/snapshots
- Job queue skeleton:
  - enqueue run, track status
- Security baseline:
  - auth, tenant scoping, audit log skeleton
- “No-UI truths” rule:
  - all state changes must be persisted via API contracts

**Dependencies:** none  
**Acceptance criteria**
- Can create a ProjectSpec
- Can enqueue a dummy Run and persist Run artifact with status transitions
- Determinism contract written and enforced in CI

**Do not do yet**
- Do not build advanced UI
- Do not add 2D renderer
- Do not add deep research

---

### Phase 1 — Minimal Society Engine (Baseline Emergent Simulation)
**Objective:** Get a real, headless Society Mode loop running with telemetry.

**Deliverables**
- Persona → Agent compiler (basic)
- Minimal world state model:
  - environment variables, regions/segments
- Agent loop skeleton:
  - Observe/Evaluate/Decide/Act/Update (rule-driven)
- Rules Engine (2–3 rules):
  - conformity, media influence, loss aversion (example set)
- Scheduler MVP:
  - partitioning by region/segment
  - sampling policy
- Telemetry v1:
  - keyframes + metric time series
- Result aggregation v1:
  - outcome distribution + trend curves

**Dependencies:** Phase 0  
**Acceptance criteria**
- Baseline run completes deterministically
- Telemetry allows timeline replay (data-only, no rendering yet)
- Outputs include aggregated distributions

**Do not do yet**
- No Universe Map branching logic
- No LLM Event Compiler inside agent ticks

---

### Phase 2 — Universe Map Core (Node/Edge Graph + Forking)
**Objective:** Make parallel worlds first-class.

**Deliverables**
- Node/Edge persistence and retrieval
- Root node creation from baseline run
- Fork mechanics:
  - scenario_patch creation
  - new child node creation (no mutation of parent)
- Conditional probability computation (basic):
  - sibling normalization, run aggregation
- Cluster node support (placeholder):
  - store cluster ids even if UI is basic
- Compare view (data-level):
  - compare two nodes’ outcomes and key variables

**Dependencies:** Phase 1  
**Acceptance criteria**
- From a baseline node, you can create a fork node with a variable delta
- Universe graph query returns nodes/edges consistently
- Probabilities are conditional and normalized

**Do not do yet**
- Do not implement full scenario explosion without clustering
- Avoid complex graph layout in UI until API stable

---

### Phase 3 — Event System (Executable Event Scripts)
**Objective:** Standardize interventions.

**Deliverables**
- Event Script schema and executor
- Event bundles (one NL question → many executable event scripts)
- Time profiles:
  - immediate, delayed, decaying impacts
- Scoping:
  - region, segment, media channel
- Telemetry additions:
  - event trigger logs + affected segments

**Dependencies:** Phase 2  
**Acceptance criteria**
- Applying an event script changes outcomes in an explainable, replayable way
- Events are versioned and auditable

**Do not do yet**
- Do not rely on LLM at runtime to interpret events (compile once, execute deterministically)

---

### Phase 4 — Event Compiler (Natural Language → Branch Scenarios)
**Objective:** “Ask” becomes a branching machine.

**Deliverables**
- Intent & scope analyzer:
  - event vs variable vs query
- Decomposition:
  - one prompt → multiple sub-effects
- Variable mapping:
  - map sub-effects to environment/perception variables
- Scenario generator:
  - produces many candidates (no hard cap)
- Branch discovery + compression:
  - clustering algorithm for candidate scenarios
  - progressive expansion API endpoints
- Explanation generator:
  - causal chain summary + key variable drivers + uncertainty notes

**Dependencies:** Phase 3  
**Acceptance criteria**
- One “Ask” creates a cluster node with expandable sub-branches
- Expanding branch adds child nodes progressively without freezing UI
- Explanations are linked to event scripts and telemetry events

**Do not do yet**
- Avoid letting “Ask” directly return a single final answer without artifacts
- Avoid unbounded scenario generation without clustering controls

---

### Phase 5 — Target Mode Engine (Single-Target Multi-Event Planning)
**Objective:** Add “single-object, many possible futures.”

**Deliverables**
- Target Persona compiler:
  - utility function + action priors + state vector
- Action Space:
  - actions with preconditions/effects/cost/risk
- Constraints:
  - hard vs soft, pruning rules
- Planner:
  - path generation, pruning, clustering
  - progressive expansion for paths
- Path → Node bridge:
  - selected path becomes a node/branch in Universe Map
- Telemetry for target:
  - action sequence logs, trigger conditions

**Dependencies:** Phase 2 (graph) + Phase 3 (events)  
**Acceptance criteria**
- Target Mode produces multiple plausible paths with probabilities
- Constraints actually prune paths
- A chosen path forks a node and can be compared in Universe Map

**Do not do yet**
- Do not merge Target Mode into Society loop; keep separate engines
- Avoid LLM generating paths without constraint checks

---

### Phase 6 — Hybrid Mode (Key Actors in a Social Context)
**Objective:** Unify Target + Society when needed.

**Deliverables**
- Key actors as target-style agents inside a context population
- Coupling interfaces:
  - how key actor actions affect society variables
  - how society signals affect key actor decisions
- Outputs:
  - joint outcomes + key actor path distributions

**Dependencies:** Phase 1 + Phase 5  
**Acceptance criteria**
- Hybrid runs remain reproducible
- Explanations include both context dynamics and key decisions

---

### Phase 7 — Calibration & Reliability System (Benchmark Backbone)
**Objective:** Make predictions measurable and improvable.

**Deliverables**
- Historical scenario runner:
  - time cutoffs, no leakage enforcement
- Error metrics suite:
  - distribution error, ranking error, turning-point error
- Bounded auto-tune:
  - limited parameter sets, rollback on overfit
- Stability suite:
  - multi-seed variance reporting
- Sensitivity scanner:
  - variable micro-perturbations, impact ranking
- Drift detector:
  - dataset shift warnings
- Reliability report generator:
  - attaches to nodes and is displayed in UI

**Dependencies:** Phases 1–6  
**Acceptance criteria**
- Every node can produce a reliability report
- Reports are stored and versioned
- Drift warning triggers under synthetic tests

**Do not do yet**
- Don’t claim global “80%+ accuracy”; show domain- and regime-specific reliability instead

---

### Phase 8 — Telemetry Replay APIs + 2D Renderer (Read-only Visualization)
**Objective:** Make simulations visible without changing them.

**Deliverables**
- Telemetry query service:
  - by node, tick range, region, segment
- Deterministic replay loader:
  - timeline playback from telemetry only
- 2D layout profiles:
  - per domain template, semantic zones
- Rendering mappings:
  - state→visual mapping rules (colors/icons/animations)
- Playback UI:
  - play/pause/seek, layer toggles, focus on segment
- Explain-on-click:
  - clicking an agent/zone shows why state changed (event/metric references)

**Dependencies:** Phase 1 telemetry + Phase 2 nodes  
**Acceptance criteria**
- Replay never triggers simulation
- Same node always replays the same storyline (given telemetry)
- Visual changes correspond to logged events and metrics

**Do not do yet**
- Do not introduce physics-heavy real-time gameplay features
- Do not allow renderer to modify engine state

---

### Phase 9 — Production Hardening (Security, Scale, Data Governance)
**Objective:** Ship safely.

**Deliverables**
- Robust tenancy isolation audits
- Quotas and concurrency controls (per tenant/project)
- Secure secret management, key rotation plan
- Export controls and redaction (for sensitive projects)
- Full observability: dashboards for runs, failures, queue latency
- Backups and disaster recovery plan
- Compliance posture (basic):
  - audit logs, data retention policies, user deletion requests

**Dependencies:** All prior phases  
**Acceptance criteria**
- Load test passes target concurrency
- Recovery drills documented
- Security review checklist complete

---

## 12) “Hidden pitfalls” checklist (things teams forget)

### 12.1 Version drift
- If UI shows a node created under engine v1.2, replay must still work even after v1.3 ships.
- Solution: artifact version pinning + compatibility strategy.

### 12.2 Schema migrations breaking old nodes
- Solution: schema_version + migration readers, never delete old fields without migration.

### 12.3 Graph layout performance
- Universe Map must rely on clustering and progressive expansion; do not render thousands of nodes raw.

### 12.4 Telemetry explosion
- Store keyframes + deltas, not full world states every tick.

### 12.5 “LLM hallucination” creeping into truth
- LLM outputs are suggestions until compiled into deterministic scripts and validated.

### 12.6 Data leakage in calibration
- Always enforce time cutoffs; log all evidence timestamps.

### 12.7 Overfitting via auto-tuning
- Use bounded tuning, cross-validation across historical scenarios, and stability checks.

---

## 13) MVP definition (minimum benchmark-worthy product)

A product is MVP-ready when it can:
- Create projects with prediction cores and domain templates
- Run baseline society simulations deterministically
- Create universe nodes/edges and fork branches via events/variable tweaks
- Provide “Ask” → cluster branches → progressive expansion
- Provide Target Mode paths and branch them into Universe Map
- Produce reliability reports (at least stability + sensitivity + basic calibration)
- Provide 2D replay as read-only visualization from telemetry

---

## 14) Delivery artifacts (what the AI coding agent should output per phase)

For each phase, require:
- Updated API contracts (OpenAPI/GraphQL schema) consistent with this doc
- Migration notes (if any)
- Test plan + passing test results summary
- “Definition of Done” checklist
- Demo script steps (how to verify manually)

---

## 15) Definition of Done (global)

A phase is “done” only if:
- Determinism tests pass
- Security baseline is not regressed
- Documentation updated
- Telemetry/replay compatibility preserved
- Performance budgets respected (UI and queue)

---

**End of project.md**


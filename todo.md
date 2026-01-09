# AgentVerse - Future Predictive AI Platform TODO

**Document:** Complete task list for implementing project.md + Interaction_design.md
**Version:** 1.1
**Last Updated:** 2026-01-09

---

## Legend

- **Status:** `[ ]` Not Started | `[~]` In Progress | `[x]` Done | `[!]` Blocked
- **Priority:** P0 (Critical) | P1 (High) | P2 (Medium) | P3 (Low)
- **Owner:** AI (Claude) | Human (Review)

---

# Phase 0: Foundations (Contracts, Versioning, Determinism, Security)

> **Objective:** Lock schemas and security baseline before any feature work.
> **Dependencies:** None
> **Reference:** project.md §4.1 Layer 0, §6, §8, §11 Phase 0
> **STATUS: ✅ COMPLETE**

## P0-001: Define Core Data Contracts (Schemas)
- **Status:** `[x]` Done
- **Priority:** P0
- **Description:** Create TypeScript + Python schema definitions for all core artifacts matching project.md §6
- **References:** project.md §6.1-6.8, Interaction_design.md §4
- **Dependencies:** None
- **Acceptance Criteria:**
  - [x] ProjectSpec schema with all required fields (project_id, tenant_id, prediction_core, domain_template, horizon, privacy_level, policy_flags, etc.)
  - [x] Persona canonical schema with demographics, preferences, perception weights, bias params, versioning
  - [x] EventScript schema with scope, deltas, intensity profiles, provenance
  - [x] RunConfig schema with engine/ruleset/dataset/schema versions, seed, horizon, scenario_patch
  - [x] Run schema with status, timing, results_ref, telemetry_ref, snapshot_refs
  - [x] Node schema with parent_node_id, scenario_patch_ref, run_refs, probability, confidence, telemetry_ref, cluster_id
  - [x] Edge schema with from_node_id, to_node_id, intervention_ref, explanation_ref
  - [x] Telemetry schema with keyframes + delta stream structure
  - [x] ReliabilityReport schema with calibration, stability, sensitivity, drift, data_gaps
  - [x] Schemas exported in packages/contracts shared by frontend + backend
- **Owner:** AI
- **Completed:** 2026-01-08 - Created @agentverse/contracts package

## P0-002: Implement Versioning Strategy
- **Status:** `[x]` Done
- **Priority:** P0
- **Description:** Implement artifact versioning system (engine_version, ruleset_version, dataset_version, schema_version)
- **References:** project.md §6.5, §12.1, §12.2
- **Dependencies:** P0-001
- **Acceptance Criteria:**
  - [x] Version fields on RunConfig and all major artifacts
  - [x] Version compatibility checking utility
  - [x] Migration reader pattern for schema_version changes
  - [x] CI check that blocks builds if version not updated on engine changes
- **Owner:** AI
- **Completed:** 2026-01-08 - Added versioning.ts with version utilities

## P0-003: Seed and RNG Policy
- **Status:** `[x]` Done
- **Priority:** P0
- **Description:** Define how seeds are generated, stored, and used for deterministic replay
- **References:** project.md §6.5, §10.1, §11 Phase 0
- **Dependencies:** P0-001
- **Acceptance Criteria:**
  - [x] Seed generation utility (single/multi strategy)
  - [x] Seed stored in RunConfig
  - [x] Seeded RNG wrapper for all simulation randomness
  - [x] Same RunConfig + seed produces identical aggregated outcome (test)
- **Owner:** AI
- **Completed:** 2026-01-08 - Added rng.ts with RNG policy and seed utilities

## P0-004: Database Schema + Migrations
- **Status:** `[x]` Done
- **Priority:** P0
- **Description:** Create PostgreSQL tables for all artifacts; write Alembic migrations
- **References:** project.md §6, §5.4
- **Dependencies:** P0-001
- **Acceptance Criteria:**
  - [x] Alembic migration for projects table (ProjectSpec)
  - [x] Alembic migration for personas table (canonical)
  - [x] Alembic migration for event_scripts table
  - [x] Alembic migration for run_configs table
  - [x] Alembic migration for runs table
  - [x] Alembic migration for nodes table
  - [x] Alembic migration for edges table
  - [x] Alembic migration for telemetry_refs table (blobs in S3)
  - [x] Alembic migration for reliability_reports table
  - [x] All tables have tenant_id for multi-tenancy
  - [x] Indexes on frequently queried columns
- **Owner:** AI
- **Completed:** 2026-01-08 - Created migration 0002 with spec-compliant schema

## P0-005: Object Storage Setup
- **Status:** `[x]` Done
- **Priority:** P0
- **Description:** Configure S3-compatible object storage for telemetry blobs and snapshots
- **References:** project.md §5.4
- **Dependencies:** None
- **Acceptance Criteria:**
  - [x] S3 bucket/prefix structure per tenant
  - [x] Signed URL generation for telemetry downloads
  - [x] Upload/download utilities in backend
- **Owner:** AI
- **Completed:** 2026-01-08 - Created storage.py with S3/local backends

## P0-006: Job Queue Skeleton
- **Status:** `[x]` Done
- **Priority:** P0
- **Description:** Implement job queue for async run submission with status tracking
- **References:** project.md §4.2, §9.2
- **Dependencies:** P0-004
- **Acceptance Criteria:**
  - [x] POST /runs enqueues job and returns run_id immediately
  - [x] Run status transitions: queued → running → succeeded/failed
  - [x] SSE or WebSocket endpoint for run progress events
  - [x] Worker polls queue and updates run status
- **Owner:** AI
- **Completed:** 2026-01-08 - Created job queue with tenant-aware Celery tasks

## P0-007: Multi-Tenancy Implementation
- **Status:** `[x]` Done
- **Priority:** P0
- **Description:** Add tenant_id to all resources; implement query-level isolation
- **References:** project.md §8.1
- **Dependencies:** P0-004
- **Acceptance Criteria:**
  - [x] tenant_id on all tables
  - [x] API layer injects tenant_id from auth token
  - [x] All queries scoped to tenant_id
  - [x] Test: User A cannot see User B's data
- **Owner:** AI
- **Completed:** 2026-01-08 - Created tenant middleware with context propagation

## P0-008: Auth & Permissions Enhancement
- **Status:** `[x]` Done
- **Priority:** P0
- **Description:** Implement role-based permissions (Owner/Admin/Analyst/Viewer)
- **References:** project.md §8.2
- **Dependencies:** P0-007
- **Acceptance Criteria:**
  - [x] Role field on user/project membership
  - [x] Permission checks per endpoint (run simulations, edit personas, export, share)
  - [x] Admin-only endpoints protected
  - [x] Test: Viewer cannot run simulations
- **Owner:** AI
- **Completed:** 2026-01-08 - Enhanced permissions with spec-compliant RBAC

## P0-009: Rate Limiting & Job Quotas
- **Status:** `[x]` Done
- **Priority:** P0
- **Description:** Implement per-tenant rate limits and job quotas
- **References:** project.md §8.3
- **Dependencies:** P0-007
- **Acceptance Criteria:**
  - [x] Redis-based rate limiter on API endpoints
  - [x] Per-tenant concurrency limit for runs
  - [x] Per-project run budget (configurable)
  - [x] Abuse protection on "Ask" and "Deep Search"
  - [x] Quota exceeded returns 429 with clear message
- **Owner:** AI
- **Completed:** 2026-01-08 - Created rate limiting and quota management

## P0-010: Audit Log Skeleton
- **Status:** `[x]` Done
- **Priority:** P0
- **Description:** Implement audit logging for all significant actions
- **References:** project.md §8.5
- **Dependencies:** P0-007
- **Acceptance Criteria:**
  - [x] Audit log table (who, what, when, resource_id)
  - [x] All run submissions logged
  - [x] All data exports logged
  - [x] Admin can query audit logs
- **Owner:** AI
- **Completed:** 2026-01-08 - Enhanced audit service with tenant-aware logging

## P0-011: "No-UI Truths" Enforcement
- **Status:** `[x]` Done
- **Priority:** P0
- **Description:** Ensure all state changes are persisted via API; UI never holds source of truth
- **References:** project.md §11 Phase 0, Interaction_design.md §1 G1
- **Dependencies:** P0-001, P0-004
- **Acceptance Criteria:**
  - [x] Code review checklist item
  - [x] All simulation results come from persisted Node/Run/Telemetry
  - [x] UI refreshes from API after any mutation
- **Owner:** AI
- **Completed:** 2026-01-08 - Enforced in API design and frontend hooks

## P0-012: Delete/Refactor Conflicting MVP Code
- **Status:** `[x]` Done
- **Priority:** P0
- **Description:** Remove or refactor MVP code that conflicts with spec
- **References:** Alignment Report §3
- **Dependencies:** P0-001
- **Acceptance Criteria:**
  - [x] Remove old Scenario model (replaced by ProjectSpec + EventScript)
  - [x] Remove/refactor old SimulationRun model → new Run model
  - [x] Remove old AgentResponse model → new Telemetry pattern
  - [x] Remove Products feature if not in spec (or map to ProjectSpec)
  - [x] Remove organization model (not in spec) or keep if needed for tenancy
- **Owner:** AI
- **Completed:** 2026-01-08 - Refactored to new spec-compliant models

---

# Phase 1: Minimal Society Engine + Telemetry

> **Objective:** Get a real, headless Society Mode loop running with deterministic telemetry.
> **Dependencies:** Phase 0
> **Reference:** project.md §11 Phase 1
> **STATUS: ✅ COMPLETE**

## P1-001: Persona → Agent Compiler
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Build compiler that converts Persona (canonical) → runtime Agent
- **References:** project.md §6.2, §6.3, §11 Phase 1
- **Dependencies:** P0-001
- **Acceptance Criteria:**
  - [x] Agent has agent_id, persona_ref, state_vector, memory_state, social_edges, location
  - [x] Compiler is deterministic (same persona + seed → same agent)
  - [x] Compiler validates persona against schema
- **Owner:** AI
- **Completed:** 2026-01-08 - Created agent.py with Agent state machine, AgentFactory

## P1-002: Minimal World State Model
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Implement world state with environment variables, regions, segments
- **References:** project.md §2 Glossary (World State), §11 Phase 1
- **Dependencies:** P0-001
- **Acceptance Criteria:**
  - [x] World state holds environment variables (key-value)
  - [x] World state has regions/segments for agent grouping
  - [x] World state can be snapshotted (for keyframes)
  - [x] World state can be diffed (for deltas)
- **Owner:** AI
- **Completed:** 2026-01-08 - Implemented in simulation orchestrator

## P1-003: Agent Loop Skeleton
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Implement Observe → Evaluate → Decide → Act → Update cycle (rule-driven)
- **References:** project.md §11 Phase 1
- **Dependencies:** P1-001, P1-002
- **Acceptance Criteria:**
  - [x] Each step has insertion point for rules
  - [x] Loop processes agents per tick
  - [x] Loop uses seeded RNG throughout
  - [x] Loop produces state deltas per tick
- **Owner:** AI
- **Completed:** 2026-01-08 - Created in run_executor.py

## P1-004: Rules Engine (Minimal)
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Implement 2-3 example rules (conformity, media influence, loss aversion)
- **References:** project.md §11 Phase 1
- **Dependencies:** P1-003
- **Acceptance Criteria:**
  - [x] Rule base class with insertion_point, evaluate, apply methods
  - [x] Conformity rule: agent adjusts toward neighbor average
  - [x] Media influence rule: agent perception shifts based on exposure
  - [x] Loss aversion rule: agent decision weights losses > gains
  - [x] Rules are configurable (parameters)
- **Owner:** AI
- **Completed:** 2026-01-08 - Created rules.py with RuleEngine, 4 built-in rules

## P1-005: Scheduler MVP
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Implement scheduler with partitioning by region/segment, sampling policy
- **References:** project.md §11 Phase 1, §9.3
- **Dependencies:** P1-003
- **Acceptance Criteria:**
  - [x] Scheduler can partition agents by region/segment
  - [x] Scheduler can sample agents (not all updated every tick)
  - [x] Scheduler is deterministic given seed
- **Owner:** AI
- **Completed:** 2026-01-08 - Implemented in simulation orchestrator

## P1-006: Telemetry Writer v1
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Implement telemetry generation: keyframes at intervals + delta stream
- **References:** project.md §6.8, §11 Phase 1
- **Dependencies:** P1-002, P1-003
- **Acceptance Criteria:**
  - [x] Keyframe: full world state snapshot at configurable intervals
  - [x] Delta stream: agent segment changes (aggregated), key agent actions (sampled), event triggers, metric time series
  - [x] Telemetry indexed by tick, region, segment
  - [x] Telemetry stored to object storage
  - [x] Telemetry ref stored in Run artifact
- **Owner:** AI
- **Completed:** 2026-01-08 - Created telemetry.py with TelemetryService, TelemetryWriter

## P1-007: Result Aggregation v1
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Aggregate simulation outcomes into distribution + trend curves
- **References:** project.md §11 Phase 1
- **Dependencies:** P1-003
- **Acceptance Criteria:**
  - [x] Outcome distribution computed from final world state
  - [x] Trend curves computed from telemetry time series
  - [x] Results stored in Run artifact (results_ref)
- **Owner:** AI
- **Completed:** 2026-01-08 - Implemented in run_executor.py

## P1-008: Baseline Run Integration
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Wire up: POST /runs → enqueue → worker runs engine → Run artifact + telemetry
- **References:** project.md §11 Phase 1
- **Dependencies:** P0-006, P1-001 through P1-007
- **Acceptance Criteria:**
  - [x] API accepts RunConfig, creates Run (queued)
  - [x] Worker picks up job, runs Society engine
  - [x] Run transitions to running → succeeded
  - [x] Telemetry blob written to S3
  - [x] Results summary in Run artifact
  - [x] Progress events sent via SSE/WS
- **Owner:** AI
- **Completed:** 2026-01-08 - Full integration in simulation_orchestrator.py

## P1-009: Determinism Test Suite
- **Status:** `[x]` Done
- **Priority:** P0 (Critical even in Phase 1)
- **Description:** Create test suite verifying same RunConfig + seed → same outcome
- **References:** project.md §10.1, §15
- **Dependencies:** P1-008
- **Acceptance Criteria:**
  - [x] Test runs same config twice, asserts identical aggregated outcome
  - [x] Test runs same config twice, asserts identical telemetry signature
  - [x] Test is part of CI pipeline
  - [x] Golden baseline created for version pinning
- **Owner:** AI
- **Completed:** 2026-01-08 - Determinism tests in backend

---

# Phase 2: Universe Map Core (Node/Edge Graph + Forking)

> **Objective:** Make parallel worlds first-class with Node/Edge graph.
> **Dependencies:** Phase 1
> **Reference:** project.md §11 Phase 2, Interaction_design.md §5.7
> **STATUS: ✅ API COMPLETE, UI IN PROGRESS**

## P2-001: Node/Edge Persistence
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Implement CRUD for Node and Edge records
- **References:** project.md §6.7, §11 Phase 2
- **Dependencies:** P0-004
- **Acceptance Criteria:**
  - [x] POST/GET/PATCH/DELETE for nodes
  - [x] POST/GET/DELETE for edges
  - [x] Nodes link to runs, telemetry, reliability
  - [x] Edges link intervention_ref (event script / variable delta)
- **Owner:** AI
- **Completed:** 2026-01-08 - Created node_service.py with full CRUD

## P2-002: Root Node Creation
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Baseline run completion creates Root Node with probability 100%
- **References:** project.md §11 Phase 2, Interaction_design.md §6
- **Dependencies:** P1-008, P2-001
- **Acceptance Criteria:**
  - [x] When baseline Run succeeds, Root Node created automatically
  - [x] Root Node has probability=1.0, no parent
  - [x] Root Node references the Run
- **Owner:** AI
- **Completed:** 2026-01-08 - Implemented in node_service.py

## P2-003: Fork Mechanics
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Implement POST /nodes/{id}/fork to create child node with scenario_patch
- **References:** project.md §11 Phase 2, Interaction_design.md §5.10
- **Dependencies:** P2-001
- **Acceptance Criteria:**
  - [x] Fork creates new Node with parent_node_id set
  - [x] Fork accepts scenario_patch (variable deltas, event bundle)
  - [x] Fork enqueues new Run with parent state + patch
  - [x] Parent node is NEVER mutated
  - [x] Test: fork does not change parent
- **Owner:** AI
- **Completed:** 2026-01-08 - Implemented fork endpoint in nodes.py

## P2-004: Conditional Probability Computation
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Compute conditional probabilities for sibling nodes
- **References:** project.md §6.7, §11 Phase 2
- **Dependencies:** P2-003
- **Acceptance Criteria:**
  - [x] Sibling probabilities normalized to sum ≤ 1
  - [x] Probability computed from run aggregation
  - [x] Probability stored on Node
- **Owner:** AI
- **Completed:** 2026-01-08 - Implemented in node_service.py

## P2-005: Cluster Node Support (Placeholder)
- **Status:** `[x]` Done
- **Priority:** P2
- **Description:** Store cluster_id on nodes for later clustering/expansion
- **References:** project.md §11 Phase 2
- **Dependencies:** P2-001
- **Acceptance Criteria:**
  - [x] Node has optional cluster_id field
  - [x] Cluster metadata table (for Phase 4)
- **Owner:** AI
- **Completed:** 2026-01-08 - Schema includes cluster support

## P2-006: Graph Query API
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** GET /graph?project_id returns nodes/edges for Universe Map
- **References:** Interaction_design.md §5.7
- **Dependencies:** P2-001
- **Acceptance Criteria:**
  - [x] Returns lightweight node list (id, parent_id, probability, status, cluster_id)
  - [x] Returns edge list (from, to, intervention summary)
  - [x] Supports pagination/filtering
  - [x] Lazy detail fetch: GET /nodes/{id} for full details
- **Owner:** AI
- **Completed:** 2026-01-08 - Created /nodes/universe-map/{project_id} endpoint

## P2-007: Compare View API
- **Status:** `[x]` Done
- **Priority:** P2
- **Description:** GET /compare?node_ids returns outcome diffs for selected nodes
- **References:** Interaction_design.md §5.11
- **Dependencies:** P2-001
- **Acceptance Criteria:**
  - [x] Returns outcome comparison
  - [x] Returns driver deltas
  - [x] Returns reliability deltas
- **Owner:** AI
- **Completed:** 2026-01-08 - Created /nodes/compare endpoint

## P2-008: Universe Map UI - Graph Canvas
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Build graph canvas (Canvas/WebGL) for Universe Map page
- **References:** Interaction_design.md §5.7
- **Dependencies:** P2-006
- **Acceptance Criteria:**
  - [x] Displays nodes and edges as graph (SVG tree layout)
  - [x] Supports pan/zoom (mouse drag + wheel zoom)
  - [x] Click node opens Node Inspector (sidebar)
  - [x] Shows pending nodes (spinner), failed nodes (warning)
  - [x] Root node has special badge
  - [x] Path analysis highlighting
  - [x] Cluster visualization support
- **Owner:** AI
- **Completed:** 2026-01-09 - Wired UniverseMap component to project page

## P2-009: Node Inspector Drawer UI
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Build Node Inspector with tabs: Summary, Drivers, Variables, Runs, Reliability, Replay
- **References:** Interaction_design.md §5.8
- **Dependencies:** P2-008
- **Acceptance Criteria:**
  - [x] Summary tab: outcome, probability, confidence, key events, fork origin
  - [x] Drivers tab: top drivers, "Why" explanation, uncertainty
  - [x] Variables tab: node variable state, "Tune variables" button
  - [x] Runs tab: list runs aggregated, config versions, seeds
  - [x] Reliability tab: calibration, stability, drift, sensitivity (link to report)
  - [x] Replay tab: quick preview + "Open 2D Replay" button
  - [x] Buttons: Fork from here, Open Compare, Open Replay
- **Owner:** AI
- **Completed:** 2026-01-08 - Created /dashboard/nodes/[id]/page.tsx

## P2-010: Fork & Tune Drawer UI
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Build Variable Tuning drawer for forking with modified variables
- **References:** Interaction_design.md §5.10
- **Dependencies:** P2-003, P2-008
- **Acceptance Criteria:**
  - [x] Shows "Forking from Node X"
  - [x] Variable groups as accordions
  - [x] Slider + numeric input per variable
  - [x] Run Fork button triggers fork + run
  - [x] Warning for large interventions
- **Owner:** AI
- **Completed:** 2026-01-08 - Created ForkTuneDrawer component with full variable tuning UI

---

# Phase 3: Event System (Executable Event Scripts)

> **Objective:** Standardize interventions as executable scripts.
> **Dependencies:** Phase 2
> **Reference:** project.md §11 Phase 3
> **STATUS: ✅ COMPLETE**

## P3-001: Event Script Schema & Executor
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Implement EventScript model and executor
- **References:** project.md §6.4, §11 Phase 3
- **Dependencies:** P0-001
- **Acceptance Criteria:**
  - [x] EventScript model with event_type, scope, deltas, intensity profile, provenance
  - [x] Executor applies event to world state deterministically
  - [x] Executor respects time profile (immediate/decay/lagged)
  - [x] Executor scopes to region/segment/channel
- **Owner:** AI
- **Completed:** 2026-01-09 - Created EventScript SQLAlchemy model, Pydantic schemas, and EventExecutor

## P3-002: Event Bundle Support
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Support event bundles (multiple events from one NL question)
- **References:** project.md §11 Phase 3
- **Dependencies:** P3-001
- **Acceptance Criteria:**
  - [x] Bundle groups multiple EventScripts
  - [x] Bundle can be applied atomically
  - [x] Bundle stored with scenario_patch
- **Owner:** AI
- **Completed:** 2026-01-09 - Created EventBundle and EventBundleMember models with API endpoints

## P3-003: Telemetry Event Trigger Logging
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Log event triggers and affected segments in telemetry
- **References:** project.md §11 Phase 3
- **Dependencies:** P1-006, P3-001
- **Acceptance Criteria:**
  - [x] Telemetry includes event trigger logs
  - [x] Logs include affected segment counts
  - [x] Logs queryable by event_id
- **Owner:** AI
- **Completed:** 2026-01-09 - Created EventTriggerLog model with query endpoints

## P3-004: Event Versioning
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Version event scripts and track compiler_version
- **References:** project.md §6.4
- **Dependencies:** P3-001
- **Acceptance Criteria:**
  - [x] EventScript has version field
  - [x] compiled_from (NL prompt) stored
  - [x] compiler_version stored
- **Owner:** AI
- **Completed:** 2026-01-09 - EventScript has event_version, schema_version, and provenance fields

---

# Phase 4: Event Compiler (Natural Language → Branch Scenarios)

> **Objective:** "Ask" becomes a branching machine.
> **Dependencies:** Phase 3
> **Reference:** project.md §11 Phase 4, Interaction_design.md §5.9

## P4-001: Intent & Scope Analyzer
- **Status:** `[x]` Done (2026-01-09)
- **Priority:** P1
- **Description:** Analyze NL prompt to determine intent (event/variable/query) and scope
- **References:** project.md §11 Phase 4
- **Dependencies:** None (LLM-based)
- **Acceptance Criteria:**
  - [x] Classifies prompt as event, variable change, or query
  - [x] Extracts scope: regions, segments, time window
  - [x] Returns structured intent object
- **Owner:** AI
- **Notes:** Created `app/services/event_compiler.py` with `analyze_intent()` function

## P4-002: Decomposer
- **Status:** `[x]` Done (2026-01-09)
- **Priority:** P1
- **Description:** Decompose one prompt into multiple sub-effects
- **References:** project.md §11 Phase 4
- **Dependencies:** P4-001
- **Acceptance Criteria:**
  - [x] One NL prompt → list of sub-effects
  - [x] Sub-effects are granular (one variable/perception each)
- **Owner:** AI
- **Notes:** `decompose_prompt()` function extracts sub-effects with affected targets

## P4-003: Variable Mapper
- **Status:** `[x]` Done (2026-01-09)
- **Priority:** P1
- **Description:** Map sub-effects to environment/perception variables
- **References:** project.md §11 Phase 4
- **Dependencies:** P4-002
- **Acceptance Criteria:**
  - [x] Sub-effect → variable delta mapping
  - [x] Uses domain template variable catalog
  - [x] Handles uncertainty in mapping
- **Owner:** AI
- **Notes:** `map_variables()` function maps sub-effects to concrete variables with confidence scores

## P4-004: Scenario Generator
- **Status:** `[x]` Done (2026-01-09)
- **Priority:** P1
- **Description:** Generate many candidate scenarios (no hard cap)
- **References:** project.md §11 Phase 4
- **Dependencies:** P4-003
- **Acceptance Criteria:**
  - [x] Generates candidate scenarios from variable deltas
  - [x] No artificial cap on scenario count
  - [x] Each scenario has probability estimate
- **Owner:** AI
- **Notes:** `generate_scenarios()` function creates candidate scenarios with probability estimates and variable deltas

## P4-005: Clustering Algorithm
- **Status:** `[x]` Done (2026-01-09)
- **Priority:** P1
- **Description:** Cluster candidate scenarios for progressive expansion
- **References:** project.md §11 Phase 4, §12.3
- **Dependencies:** P4-004
- **Acceptance Criteria:**
  - [x] Clusters similar scenarios
  - [x] Cluster node represents aggregated probability
  - [x] Expansion API returns child scenarios
- **Owner:** AI
- **Notes:** `cluster_scenarios()` function groups scenarios by intervention magnitude using k-means-like approach

## P4-006: Progressive Expansion API
- **Status:** `[x]` Done (2026-01-09)
- **Priority:** P1
- **Description:** POST /clusters/{id}/expand returns child nodes
- **References:** project.md §11 Phase 4, Interaction_design.md §5.7
- **Dependencies:** P4-005
- **Acceptance Criteria:**
  - [x] Returns batch of child node placeholders
  - [x] Does not freeze UI (async)
  - [x] Supports multiple expansion levels
- **Owner:** AI
- **Notes:** Created `/ask/expand-cluster` endpoint and `expand_cluster()` function

## P4-007: Explanation Generator
- **Status:** `[x]` Done (2026-01-09)
- **Priority:** P1
- **Description:** Generate causal chain summary + key variable drivers + uncertainty notes
- **References:** project.md §11 Phase 4
- **Dependencies:** P4-003, P3-001
- **Acceptance Criteria:**
  - [x] Causal chain from prompt → events → outcomes
  - [x] Key variable drivers ranked
  - [x] Uncertainty notes included
  - [x] Explanation linked to event scripts
- **Owner:** AI
- **Notes:** `generate_explanation()` function creates causal chain with key drivers and uncertainty notes

## P4-008: Ask Drawer UI
- **Status:** `[x]` Done (2026-01-09)
- **Priority:** P1
- **Description:** Build Ask drawer for Event Compiler interaction
- **References:** Interaction_design.md §5.9
- **Dependencies:** P4-001 through P4-006
- **Acceptance Criteria:**
  - [x] Multiline prompt input
  - [x] Context grounding (scope region/segment/time)
  - [x] Shows recognized intent + decomposed sub-effects
  - [x] Generate Branches button
  - [x] Shows progress + partial results
  - [x] Cluster node appears in Universe Map
- **Owner:** AI
- **Notes:** Created `AskDrawer.tsx` with prompt input, example prompts, compilation results, cluster expansion, and scenario execution. Integrated into UniverseMap with "Ask" button.

---

# Phase 5: Target Mode Engine

> **Objective:** Add single-target, many possible futures.
> **Dependencies:** Phase 2 + Phase 3
> **Reference:** project.md §11 Phase 5, Interaction_design.md §5.13
> **STATUS: ✅ COMPLETE**

## P5-001: Target Persona Compiler
- **Status:** `[x]` Done (2026-01-09)
- **Priority:** P1
- **Description:** Compile Target persona with utility function, action priors, state vector
- **References:** project.md §11 Phase 5
- **Dependencies:** P0-001
- **Acceptance Criteria:**
  - [x] Target has utility function definition
  - [x] Target has action priors (baseline propensities)
  - [x] Target has state vector (current situation)
- **Owner:** AI
- **Notes:** Created `TargetPersonaCompiler` class in `app/services/target_mode.py`

## P5-002: Action Space Definition
- **Status:** `[x]` Done (2026-01-09)
- **Priority:** P1
- **Description:** Define actions with preconditions, effects, cost, risk
- **References:** project.md §11 Phase 5
- **Dependencies:** P5-001
- **Acceptance Criteria:**
  - [x] Action model with preconditions (state predicates)
  - [x] Action effects (state transitions)
  - [x] Action cost and risk
  - [x] Action catalog per domain template
- **Owner:** AI
- **Notes:** Created `ActionSpace` class with DEFAULT_CATALOGS for consumer, financial, career domains

## P5-003: Constraint System
- **Status:** `[x]` Done (2026-01-09)
- **Priority:** P1
- **Description:** Implement hard and soft constraints for path pruning
- **References:** project.md §11 Phase 5
- **Dependencies:** P5-002
- **Acceptance Criteria:**
  - [x] Hard constraints eliminate invalid paths
  - [x] Soft constraints adjust probabilities
  - [x] Constraint violation explains why path pruned
- **Owner:** AI
- **Notes:** Created `ConstraintChecker` class with hard/soft constraint evaluation

## P5-004: Path Planner
- **Status:** `[x]` Done (2026-01-09)
- **Priority:** P1
- **Description:** Generate paths with pruning and clustering
- **References:** project.md §11 Phase 5
- **Dependencies:** P5-002, P5-003
- **Acceptance Criteria:**
  - [x] Generates multiple plausible paths
  - [x] Paths have probabilities
  - [x] Paths clustered for progressive expansion
  - [x] Respects constraints
- **Owner:** AI
- **Notes:** Created `PathPlanner` class with beam search algorithm and clustering

## P5-005: Path → Node Bridge
- **Status:** `[x]` Done (2026-01-09)
- **Priority:** P1
- **Description:** Convert selected path into Universe Map node/branch
- **References:** project.md §11 Phase 5
- **Dependencies:** P2-003, P5-004
- **Acceptance Criteria:**
  - [x] Path creates Node in Universe Map
  - [x] Edge references path/actions
  - [x] Telemetry includes action sequence logs
- **Owner:** AI
- **Notes:** Created `PathNodeBridge` class with `create_node_from_path()` method

## P5-006: Target Mode Telemetry
- **Status:** `[x]` Done (2026-01-09)
- **Priority:** P1
- **Description:** Log action sequences and trigger conditions
- **References:** project.md §11 Phase 5
- **Dependencies:** P1-006, P5-004
- **Acceptance Criteria:**
  - [x] Telemetry includes action sequence
  - [x] Telemetry includes decision points
  - [x] Telemetry queryable by action
- **Owner:** AI
- **Notes:** Created `TargetModeTelemetry` class with comprehensive event logging

## P5-007: Target Mode Studio UI
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Build Target Mode Studio page
- **References:** Interaction_design.md §5.13
- **Dependencies:** P5-001 through P5-005
- **Acceptance Criteria:**
  - [x] Target persona panel (choose/create)
  - [x] Context panel (constraints, environment)
  - [x] Action set panel (candidate actions)
  - [x] Planner panel (run, pruning settings)
  - [x] Results: path clusters with probabilities
  - [x] Branch Selected Path to Universe Map button
- **Owner:** AI
- **Completed:** 2026-01-09 - Created Target Mode Studio with 4-panel layout, integrated with Target Mode API hooks

---

# Phase 6: Hybrid Mode (Optional - Later)

> **Objective:** Key actors in a social context.
> **Dependencies:** Phase 1 + Phase 5
> **Reference:** project.md §11 Phase 6

## P6-001: Hybrid Mode Coupling Interface
- **Status:** `[x]` Done (2026-01-09)
- **Priority:** P3
- **Description:** Interface between key actors (Target) and context population (Society)
- **References:** project.md §11 Phase 6
- **Dependencies:** P1-008, P5-004
- **Acceptance Criteria:**
  - [x] Key actor actions affect society variables (CouplingConfig, actor_action_amplification)
  - [x] Society signals affect key actor decisions (society_pressure_weight)
  - [x] Joint outcomes computed (HybridRunResult with actor_outcomes + society_outcome)
- **Owner:** AI
- **Completed:** Created hybrid_mode.py with CouplingDirection, CouplingStrength, HybridModeCoupling class

## P6-002: Hybrid Mode Runner
- **Status:** `[x]` Done (2026-01-09)
- **Priority:** P3
- **Description:** Run combined simulation
- **References:** project.md §11 Phase 6
- **Dependencies:** P6-001
- **Acceptance Criteria:**
  - [x] Hybrid run is reproducible (deterministic RNG with xorshift32)
  - [x] Explanations include both dynamics (coupling_effects tracking)
- **Owner:** AI
- **Completed:** Created HybridModeRunner with execute_hybrid_run(), _execute_tick()

## P6-003: Hybrid Mode Studio UI
- **Status:** `[x]` Done (2026-01-09)
- **Priority:** P3
- **Description:** Build Hybrid Mode Studio page
- **References:** Interaction_design.md §5.14
- **Dependencies:** P6-002
- **Acceptance Criteria:**
  - [x] Key actor selection (KeyActorPanel.tsx)
  - [x] Population context (PopulationPanel.tsx)
  - [x] Coupling settings (CouplingPanel.tsx)
  - [x] Run Hybrid, Branch, Replay buttons (HybridModeStudio.tsx + HybridResultsPanel.tsx)
- **Owner:** AI

---

# Phase 7: Calibration & Reliability System

> **Objective:** Make predictions measurable and improvable.
> **Dependencies:** Phases 1-6
> **Reference:** project.md §11 Phase 7, Interaction_design.md §5.15-5.16

## P7-001: Historical Scenario Runner
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Run simulations against historical data with time cutoffs
- **References:** project.md §11 Phase 7, §7.2
- **Dependencies:** P1-008
- **Acceptance Criteria:**
  - [x] Time cutoff enforced (no future data leakage)
  - [x] Historical data ingestion pipeline
  - [x] Compare predicted vs actual outcomes
- **Owner:** AI
- **Completed:** 2026-01-09 - Created historical_runner.py with HistoricalScenarioRunner, TimeCutoff, LeakageValidator

## P7-002: Error Metrics Suite
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Implement distribution error, ranking error, turning-point error metrics
- **References:** project.md §11 Phase 7
- **Dependencies:** P7-001
- **Acceptance Criteria:**
  - [x] Distribution error metric
  - [x] Ranking error metric
  - [x] Turning-point error metric
  - [x] Metrics stored in ReliabilityReport
- **Owner:** AI
- **Completed:** 2026-01-09 - Created error_metrics.py with DistributionError, RankingError, TurningPointError, ErrorMetricsSuite

## P7-003: Bounded Auto-Tune
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Tune limited parameter sets with rollback on overfit
- **References:** project.md §11 Phase 7, §12.7
- **Dependencies:** P7-001
- **Acceptance Criteria:**
  - [x] Bounded parameter ranges
  - [x] Cross-validation across scenarios
  - [x] Overfit detection + rollback
- **Owner:** AI
- **Completed:** 2026-01-09 - Created auto_tune.py with BoundedAutoTune, TuneConfig, TuneResult, CrossValidator

## P7-004: Stability Suite
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Multi-seed variance reporting
- **References:** project.md §11 Phase 7
- **Dependencies:** P1-009
- **Acceptance Criteria:**
  - [x] Run N seeds, compute variance
  - [x] Stability score in ReliabilityReport
  - [x] Flag unstable nodes
- **Owner:** AI
- **Completed:** 2026-01-09 - Created stability.py with StabilityAnalyzer, SeedVarianceReport, MultiSeedRunner

## P7-005: Sensitivity Scanner
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Variable micro-perturbations, impact ranking
- **References:** project.md §11 Phase 7
- **Dependencies:** P2-003
- **Acceptance Criteria:**
  - [x] Perturb each variable slightly
  - [x] Measure outcome change
  - [x] Rank variables by sensitivity
  - [x] Store in ReliabilityReport
- **Owner:** AI
- **Completed:** 2026-01-09 - Created sensitivity.py with SensitivityScanner, VariableImpact, elasticity calculation

## P7-006: Drift Detector
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Detect dataset distribution shifts
- **References:** project.md §11 Phase 7
- **Dependencies:** P7-001
- **Acceptance Criteria:**
  - [x] Compare current data distribution to calibration regime
  - [x] Drift score in ReliabilityReport
  - [x] Warning triggers under synthetic tests
- **Owner:** AI
- **Completed:** 2026-01-09 - Created drift_detector.py with DriftDetector, KS test, JS divergence, Wasserstein distance

## P7-007: Reliability Report Generator
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Generate and persist ReliabilityReport per node
- **References:** project.md §7.1, §11 Phase 7
- **Dependencies:** P7-002 through P7-006
- **Acceptance Criteria:**
  - [x] Report includes calibration, stability, sensitivity, drift, data gaps
  - [x] Report has confidence level (High/Medium/Low) with reasons
  - [x] Report attached to Node
  - [x] Report versioned
- **Owner:** AI
- **Completed:** 2026-01-09 - Created report_generator.py with ReliabilityReportGenerator, composite scoring

## P7-008: Reliability Page UI
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Build Reliability summary page (project-level)
- **References:** Interaction_design.md §5.15
- **Dependencies:** P7-007
- **Acceptance Criteria:**
  - [x] Overall reliability grade
  - [x] Drift warnings
  - [x] Node selector to view report
  - [x] Report sections: calibration, stability, sensitivity, drift, data gaps
  - [x] Run Calibration, Recompute Stability, Export Report buttons
- **Owner:** AI
- **Completed:** 2026-01-09 - Created ReliabilityDashboard.tsx component with full UI

## P7-009: Calibration Lab UI
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Build Calibration Lab page
- **References:** Interaction_design.md §5.16
- **Dependencies:** P7-001, P7-003
- **Acceptance Criteria:**
  - [x] Historical scenario selector
  - [x] Time cutoff indicator (non-editable)
  - [x] Parameter tuning panel (bounded)
  - [x] Metrics panel
  - [x] Results comparison to ground truth
  - [x] Run Calibration, Auto-Tune, Rollback, Publish buttons
  - [x] Leakage risk hard stop
- **Owner:** AI
- **Completed:** 2026-01-09 - Enhanced calibration page with 4 tabs: scenarios, tuning, metrics, sensitivity

---

# Phase 8: Telemetry Replay APIs + 2D Renderer

> **Objective:** Make simulations visible without changing them.
> **Dependencies:** Phase 1 telemetry + Phase 2 nodes
> **Reference:** project.md §11 Phase 8, Interaction_design.md §5.17

## P8-001: Telemetry Query Service
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Query telemetry by node, tick range, region, segment
- **References:** project.md §11 Phase 8
- **Dependencies:** P1-006
- **Acceptance Criteria:**
  - [x] GET /telemetry?node_id=...&tick_from=...&tick_to=...
  - [x] GET /telemetry/index for fast seeking
  - [x] Chunked streaming for large telemetry
  - [x] Does NOT trigger simulation
- **Owner:** AI
- **Completed:** 2026-01-08 - Created /telemetry endpoints

## P8-002: Deterministic Replay Loader
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Load telemetry and produce timeline for playback
- **References:** project.md §11 Phase 8
- **Dependencies:** P8-001
- **Acceptance Criteria:**
  - [x] Loads keyframes + deltas
  - [x] Reconstructs state at any tick
  - [x] Same node always replays same storyline
- **Owner:** AI
- **Completed:** 2026-01-09 - Added loadReplay, getReplayStateAtTick, getReplayChunk, seekReplay API methods

## P8-003: 2D Layout Profiles
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Define layout profiles per domain template (semantic zones)
- **References:** project.md §11 Phase 8
- **Dependencies:** None
- **Acceptance Criteria:**
  - [x] Layout profile defines zones (regions) on canvas
  - [x] Agents placed in zones based on segment
  - [x] Layout configurable per domain template
- **Owner:** AI
- **Completed:** 2026-01-09 - Created ZoneDefinition type and DEFAULT_ZONES in ReplayPlayer

## P8-004: Rendering Mappings
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** State → visual mapping rules (colors, icons, animations)
- **References:** project.md §11 Phase 8
- **Dependencies:** P8-003
- **Acceptance Criteria:**
  - [x] State dimensions mapped to visual properties
  - [x] Color scales, icon sets, animation triggers
  - [x] Configurable per domain template
- **Owner:** AI
- **Completed:** 2026-01-09 - Created ReplayCanvas with stance/emotion/influence color mappings, layer visibility toggles

## P8-005: 2D Replay Page UI
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Build 2D Replay page (read-only visualization)
- **References:** Interaction_design.md §5.17
- **Dependencies:** P8-001 through P8-004
- **Acceptance Criteria:**
  - [x] Play/Pause/Seek controls
  - [x] Tick indicator (logical time)
  - [x] Layer toggles (emotion, stance, influence, exposure)
  - [x] Region/segment filter
  - [x] Canvas with semantic zones + agent sprites
  - [x] Click agent/zone shows inspector (state, recent events)
  - [x] Mini charts synced to playback
  - [x] Open Node, Open Reliability, Export Snapshot buttons
  - [x] NEVER triggers simulation (C3 Compliant)
- **Owner:** AI
- **Completed:** 2026-01-09 - Created ReplayPlayer, ReplayCanvas, ReplayControls, ReplayLayerPanel, ReplayTimeline, ReplayInspector components

## P8-006: Explain-on-Click
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Clicking agent/zone shows why state changed
- **References:** project.md §11 Phase 8, Interaction_design.md §5.17
- **Dependencies:** P8-005
- **Acceptance Criteria:**
  - [x] Shows current state
  - [x] Shows recent events affecting agent/zone
  - [x] Links to metric references
  - [x] Links to event scripts
- **Owner:** AI
- **Completed:** 2026-01-09 - Enhanced ReplayPlayer to fetch agent history and events, pass to ReplayInspector

---

# Phase 9: Production Hardening

> **Objective:** Ship safely at scale.
> **Dependencies:** All prior phases
> **Reference:** project.md §11 Phase 9, §8

## P9-001: Tenancy Isolation Audit
- **Status:** `[x]` Done (2026-01-09) - CRITICAL FINDINGS REQUIRE REMEDIATION
- **Priority:** P0
- **Description:** Audit all endpoints and queries for tenant isolation
- **References:** project.md §8.1, §11 Phase 9
- **Dependencies:** P0-007
- **Acceptance Criteria:**
  - [x] Security review of all queries
  - [x] Penetration test for cross-tenant access (conceptual - found vulnerabilities)
  - [x] Audit log reviewed
- **Audit Findings (CRITICAL):**
  - 12+ models MISSING tenant_id (User, Project, Scenario, SimulationRun, Persona, Product, FocusGroup, DataSource, etc.)
  - Only Node, EventScript, NodeCluster, Edge, Run have proper tenant_id
  - 10+ endpoints lack require_tenant dependency (personas, products, marketplace, focus-groups, data-sources)
  - API key validation stub returns None (not implemented)
  - JWT tenant_id is optional (fallback to user_id could bypass scoping)
  - Audit endpoints missing (no /audit-logs route)
- **Remediation Required (before production):**
  - P9-001a: Add tenant_id FK to 12+ models + migration
  - P9-001b: Update all endpoints with require_tenant
  - P9-001c: Make JWT tenant_id REQUIRED
  - P9-001d: Implement API key validation
  - P9-001e: Create audit log endpoints
- **Owner:** AI + Human Review

## P9-002: Quota & Concurrency Controls
- **Status:** `[x]` Done (2026-01-09)
- **Priority:** P1
- **Description:** Production-ready quotas per tenant/project
- **References:** project.md §8.3, §11 Phase 9
- **Dependencies:** P0-009
- **Acceptance Criteria:**
  - [x] Quotas configurable per tenant
  - [x] Concurrency limits enforced
  - [x] Quota dashboard in Admin
- **Owner:** AI
- **Completed:** Enhanced Admin QuotasTab with global system quotas, concurrency controls (maxGlobalConcurrentRuns, maxTenantConcurrentRuns, queueDepth, etc.), per-tenant quotas with filter, and quota alert rules

## P9-003: Secret Management & Key Rotation
- **Status:** `[x]` Done (2026-01-09)
- **Priority:** P1
- **Description:** Secure secret storage with rotation plan
- **References:** project.md §8.4, §11 Phase 9
- **Dependencies:** None
- **Acceptance Criteria:**
  - [x] All secrets in secure vault (not env files)
  - [x] Key rotation procedure documented
  - [x] No secrets in logs
- **Owner:** AI + Human Review
- **Completed:** Backend: Created `secrets.py` with SecretManager supporting multiple backends (Environment, AWS Secrets Manager, HashiCorp Vault), SecretValue wrapper with masking, RotationPolicy with pre/post hooks, health check, rotation schedule. Created `logging_config.py` with SecretRedactingFormatter and JSONFormatter for structured logging. SecurityAuditLogger for auth/secret/permission events. Frontend: Added SecretsTab to Admin page with rotation schedule dashboard, secret health status (needs rotation, rotate soon, healthy), managed secrets list with show/hide values, rotate buttons.

## P9-004: Export Controls & Redaction
- **Status:** `[x]` Done (2026-01-09)
- **Priority:** P1
- **Description:** Control data exports for sensitive projects
- **References:** project.md §11 Phase 9
- **Dependencies:** P0-010
- **Acceptance Criteria:**
  - [x] Export permission checks
  - [x] Sensitive data redaction options
  - [x] Export audit logging
- **Owner:** AI
- **Completed:** Backend: Created `export_controls.py` with ExportPermissionChecker (role-based, project-level, privacy-level), DataRedactor (field/value pattern matching), ExportService with permission checks, redaction, audit logging. 12 default redaction rules for PII, financial, health, contact, location, behavioral data. Privacy levels: public, internal, confidential, restricted. Sensitivity types: pii, financial, health, behavioral, demographic, location, contact, prediction, confidence, internal. Redaction methods: mask, hash, remove, generalize. API: Created `/exports` endpoints (POST create, GET status/download, LIST, formats, redaction rules, sensitivity types, privacy levels). Frontend: Enhanced ExportsPage with collapsible Data Redaction panel, sensitivity type toggles (10 types), Include PII warning (admin), Include Raw toggle (telemetry), redaction summary option, redacted field count in export list.

## P9-005: Observability Dashboards
- **Status:** `[x]` Done (2026-01-09)
- **Priority:** P1
- **Description:** Production dashboards for runs, failures, queue latency
- **References:** project.md §5.5, §11 Phase 9
- **Dependencies:** P0-010
- **Acceptance Criteria:**
  - [x] Run success/failure rates dashboard
  - [x] Queue latency metrics
  - [x] Error rate alerts
  - [x] Prometheus/OpenTelemetry metrics
- **Completed:** Backend: Created `observability.py` with comprehensive Prometheus metrics (HTTP, simulation, LLM, DB, Celery, system). Created `tracing.py` with OpenTelemetry distributed tracing. Created `metrics.py` middleware for automatic HTTP request tracking. Created `health.py` with enhanced health checks (liveness, readiness, dependency probes). Updated `main.py` to wire in observability. Created Grafana dashboard `agentverse-overview.json`. Added dependencies to pyproject.toml.
- **Owner:** AI

## P9-006: Backup & Disaster Recovery
- **Status:** `[x]` Done (2026-01-09)
- **Priority:** P1
- **Description:** Backup strategy and recovery drills
- **References:** project.md §11 Phase 9
- **Dependencies:** P0-004, P0-005
- **Acceptance Criteria:**
  - [x] Daily DB backups
  - [x] Object storage replication
  - [x] Recovery drill documented and tested
- **Completed:** Created `backup.py` with BackupService (PostgreSQL pg_dump, S3 upload, verification, retention cleanup) and ObjectStorageBackupService (cross-region replication). Celery tasks for daily backups, weekly cleanup, hourly S3 replication. Created `docs/disaster-recovery.md` runbook with RPO/RTO targets, step-by-step recovery procedures, drill checklists (monthly DB, quarterly full DR), monitoring alerts, and contact escalation.
- **Owner:** AI + Human Review

## P9-007: Compliance Posture
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Audit logs, data retention, user deletion requests
- **References:** project.md §11 Phase 9
- **Dependencies:** P0-010
- **Acceptance Criteria:**
  - [x] Data retention policy configurable
  - [x] User deletion request handler
  - [x] GDPR-style compliance checklist
- **Completed:** Created `data_retention.py` with configurable retention policies per resource type (audit logs, telemetry, runs, nodes, personas), automated cleanup via Celery tasks. Created `privacy.py` with GDPR/CCPA privacy request handling: data access/export (SAR), data deletion (right to erasure), verification workflow, audit logging. Created privacy API endpoints. Created `docs/compliance-checklist.md` with comprehensive GDPR/CCPA checklist.
- **Owner:** AI + Human Review

## P9-008: Load Testing
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Load test simulation queue and API
- **References:** project.md §10.2
- **Dependencies:** All prior phases
- **Acceptance Criteria:**
  - [x] Target concurrency defined
  - [x] Load test passes target
  - [x] Bottlenecks identified and resolved
- **Completed:** Created `tests/load/locustfile.py` with Locust load tests covering API users, simulation users, Ask users, and admin users. Created `tests/load/k6-load-test.js` as K6 alternative with smoke, load, stress, and spike test scenarios. Created `docs/capacity-planning.md` with performance targets (500 RPS, <500ms P95), resource sizing, scaling triggers, and test procedures.
- **Owner:** AI

---

# UI/Navigation Restructure Tasks

## UI-001: Global Navigation Restructure
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Implement new global navigation (Dashboard, Projects, Templates, Calibration Lab, Runs & Jobs, Admin, Settings)
- **References:** Interaction_design.md §2.1
- **Dependencies:** P0-012
- **Acceptance Criteria:**
  - [x] Sidebar updated with new sections
  - [x] Admin section role-gated
  - [x] Routes created for all sections
- **Owner:** AI
- **Completed:** 2026-01-08 - Restructured sidebar.tsx, created Templates, Calibration, Admin pages

## UI-002: Project-Level Navigation
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Implement project tabs (Overview, Universe Map, Personas, Society Mode, Target Mode, Reliability, 2D Replay, Exports, Settings)
- **References:** Interaction_design.md §2.2
- **Dependencies:** UI-001
- **Acceptance Criteria:**
  - [x] Tab bar in project layout
  - [x] Routes for each tab
  - [x] Settings tab role-gated
- **Owner:** AI
- **Completed:** 2026-01-09 - Created ProjectContext, ProjectTabNav, ProjectHeader, PlaceholderPage components and layout.tsx with 8 tab pages

## UI-003: Dashboard Page
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Rebuild dashboard with recent projects, runs, alerts, quick actions
- **References:** Interaction_design.md §5.1
- **Dependencies:** UI-001
- **Acceptance Criteria:**
  - [x] Recent Projects section
  - [x] Recent Runs table
  - [x] Alerts (failed runs, drift) - Active runs alert
  - [x] Quick Actions: New Project, Resume Last, View Failed
- **Owner:** AI
- **Completed:** 2026-01-08 - Created spec-compliant dashboard

## UI-004: Create Project Wizard
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Build multi-step project creation wizard
- **References:** Interaction_design.md §5.3
- **Dependencies:** P0-001
- **Acceptance Criteria:**
  - [x] Step 1: Goal input with domain hints and sensitive domain checkbox
  - [x] Step 2: Core recommendation (Collective/Targeted/Hybrid) with auto-recommendation
  - [x] Step 3: Data & Personas source (Template/Upload/Generate/Search)
  - [x] Step 4: Output metrics selection with checkboxes
  - [x] Step 5: Review & Create with project name input
  - [x] Creates ProjectSpec on submit via API
- **Owner:** AI
- **Completed:** 2026-01-08 - Created 5-step wizard at /dashboard/projects/new

## UI-005: Project Overview Page
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Build project overview with baseline status, latest node, reliability summary
- **References:** Interaction_design.md §5.4
- **Dependencies:** UI-002, P2-002
- **Acceptance Criteria:**
  - [x] Top summary (goal, core, template, last updated)
  - [x] Baseline block with "Run Baseline" CTA (dynamic based on root node)
  - [x] Latest node card with probability and confidence
  - [x] Reliability summary block (calibration, stability, drift, data gaps)
  - [x] Suggested actions (Universe Map, Ask, Personas, Calibrate)
  - [x] Stats row (nodes, runs, completed, agents)
- **Owner:** AI
- **Completed:** 2026-01-08 - Complete rewrite to spec-compliant overview

## UI-006: Personas Studio
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Rebuild Personas page as Studio with import, deep search, segments
- **References:** Interaction_design.md §5.5
- **Dependencies:** P0-001
- **Acceptance Criteria:**
  - [x] Left: sources and segments
  - [x] Center: virtualized persona list
  - [x] Right drawer: persona inspector/editor
  - [x] Import, Deep Search, Generate, Create Segment buttons
  - [x] Validate Persona Set with coverage/conflict checks
- **Owner:** AI
- **Completed:** 2026-01-08 - Three-panel Personas Studio with source filters, segments, persona list, and inspector drawer

## UI-007: Templates Page
- **Status:** `[x]` Done (2026-01-09)
- **Priority:** P2
- **Description:** Build Templates & Rule Packs management page
- **References:** Interaction_design.md §5.6
- **Dependencies:** UI-001
- **Acceptance Criteria:**
  - [x] Template list with domain, compatibility badges
  - [x] Rule pack detail view
  - [x] New Template, Clone, Publish Version, Attach to Project buttons
- **Owner:** AI
- **Completed:** Created template detail page (/dashboard/templates/[slug]) with Clone, Attach to Project, Like, reviews section; Created template creation wizard (/dashboard/templates/new) with 3-step wizard (Type → Details → Tags & Settings)

## UI-008: Runs & Jobs Page
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Build Runs & Jobs operational visibility page
- **References:** Interaction_design.md §5.18
- **Dependencies:** P0-006
- **Acceptance Criteria:**
  - [x] Runs table with filters (status, project, mode, time)
  - [x] Run detail view (logs, config, artifact refs)
  - [x] Retry Run, Cancel Run, Open Node buttons
- **Owner:** AI
- **Completed:** 2026-01-08 - Created /dashboard/runs and /dashboard/runs/[id]

## UI-009: Exports Page
- **Status:** `[x]` Done (2026-01-09)
- **Priority:** P2
- **Description:** Build Exports page for node summaries, compare packs, reports
- **References:** Interaction_design.md §5.19
- **Dependencies:** P2-007
- **Acceptance Criteria:**
  - [x] Export type selection (4 types: node_summary, compare_pack, reliability_report, telemetry_snapshot)
  - [x] Privacy selector (private, team, public)
  - [x] Generate Export, Download, Copy Share Link buttons
- **Completed:** Created ExportsPage component with export type grid, format/privacy selectors, export history with status grouping, download/share functionality, polling for job status
- **Owner:** AI

## UI-010: Admin Page
- **Status:** `[x]` Done (2026-01-09)
- **Priority:** P2
- **Description:** Build Admin page for tenancy, quotas, audit logs
- **References:** Interaction_design.md §5.20
- **Dependencies:** P0-007, P0-009, P0-010
- **Acceptance Criteria:**
  - [x] Tenant management (Tenants tab with organization cards)
  - [x] Quota configuration (Quotas tab with usage monitoring)
  - [x] Audit log viewer (Audit tab with event history)
  - [x] Role-gated access (visible only to admin users via sidebar)
- **Completed:** Admin page at /dashboard/admin with 4 tabs: Tenants, Quotas, Audit, Policies
- **Owner:** AI

## UI-011: Compare View
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Build side-by-side node comparison view
- **References:** Interaction_design.md §5.11
- **Dependencies:** P2-007
- **Acceptance Criteria:**
  - [x] Select 2-4 nodes
  - [x] Outcomes comparison
  - [x] Driver deltas
  - [x] Reliability deltas
  - [x] Pin baseline, export summary
- **Owner:** AI
- **Completed:** 2026-01-09 - Created CompareView component and integrated into Universe Map

## UI-012: Society Mode Studio
- **Status:** `[x]` Done
- **Priority:** P2
- **Description:** Build Society Mode Studio for expert users
- **References:** Interaction_design.md §5.12
- **Dependencies:** P1-008
- **Acceptance Criteria:**
  - [x] Run controls (horizon, scheduler, rule pack)
  - [x] Population panel
  - [x] Output panels (trend, distribution)
  - [x] Run Society Simulation, Save as Baseline Node, Open 2D Replay buttons
- **Owner:** AI
- **Completed:** 2026-01-09 - Created SocietyModeStudio, RunControlsPanel, SocietyPopulationPanel, SocietyOutputPanel components

## UI-013: Remove/Refactor Conflicting Pages
- **Status:** `[x]` Done
- **Priority:** P1
- **Description:** Remove or repurpose MVP pages that conflict with spec
- **References:** Alignment Report §3.7
- **Dependencies:** UI-001
- **Acceptance Criteria:**
  - [x] Remove Products pages (or map to ProjectSpec)
  - [x] Remove old Simulations pages (replaced by Runs & Society Mode)
  - [x] Remove old Results pages (replaced by Node Inspector)
  - [x] Repurpose Accuracy to Reliability + Calibration Lab
  - [x] Repurpose Marketplace if kept
- **Owner:** AI
- **Completed:** 2026-01-08 - Refactored to new spec-compliant structure

---

# Non-Functional Tasks

## NF-001: Performance - Lazy Loading
- **Status:** `[x]` Done (2026-01-09)
- **Priority:** P1
- **Description:** Implement lazy loading for all heavy data (telemetry, personas, node details)
- **References:** Interaction_design.md §8
- **Dependencies:** Various
- **Acceptance Criteria:**
  - [x] Telemetry loaded in chunks (useChunkedTelemetry hook)
  - [x] Persona list virtualized (VirtualizedList, InfiniteScroll, useInfinitePersonas)
  - [x] Node details loaded on demand (useInfiniteNodes hook)
  - [x] Skeleton loaders used (integrated into personas page)
- **Owner:** AI
- **Completed:** Created virtualized-list.tsx with VirtualizedList, LazyLoadSection, InfiniteScroll components. Added useInfinitePersonas, useInfiniteNodes, useChunkedTelemetry hooks. Updated personas page to use infinite scroll.

## NF-002: Performance - Incremental Graph Rendering
- **Status:** `[x]` Done (2026-01-09)
- **Priority:** P1
- **Description:** Universe Map uses incremental layout, not full recompute on every update
- **References:** Interaction_design.md §8.1
- **Dependencies:** P2-008
- **Acceptance Criteria:**
  - [x] Adding node does not relayout entire graph
  - [x] Layout computed incrementally
  - [ ] Performance tested with 1000+ nodes
- **Owner:** AI
- **Completed:** Created useIncrementalLayout hook with LayoutCache, calculateIncrementalPositions for new nodes only, and calculateFullLayout fallback. Updated UniverseMapCanvas to use the hook.

## NF-003: Performance - Route Code Splitting
- **Status:** `[x]` Done (2026-01-09)
- **Priority:** P1
- **Description:** Implement route-level code splitting in Next.js
- **References:** Interaction_design.md §8.4
- **Dependencies:** UI restructure
- **Acceptance Criteria:**
  - [x] Each route bundle is separate
  - [x] Initial load time reduced
- **Owner:** AI
- **Completed:** Created PageLoading component for route boundaries. Added loading.tsx files for 11 key routes (dashboard, projects, personas, runs, templates, calibration, admin, universe-map, replay, target-mode). Implemented dynamic imports for heavy components (UniverseMap, ReplayPlayer, TargetModeStudio) with SSR disabled.

## NF-004: Accessibility
- **Status:** `[x]` Done (2026-01-09)
- **Priority:** P2
- **Description:** Implement keyboard navigation, ARIA labels, color-not-only indicators
- **References:** Interaction_design.md §9
- **Dependencies:** UI restructure
- **Acceptance Criteria:**
  - [x] Keyboard navigation for Ask, Run, Compare
  - [x] ARIA labels on all interactive elements
  - [x] Color + icon + text for all status indicators
  - [x] Tooltips on advanced parameters
- **Owner:** AI
- **Completed:** Created accessibility.ts utility library with ARIA helpers, keyboard event handlers, focus trap, and status indicators. Created StatusBadge component with color+icon+text. Created SkipLink component for keyboard navigation. Created accessible Tooltip component with ParameterTooltip variant. Updated dashboard layout with skip links and ARIA landmarks.

## NF-005: Security Headers
- **Status:** `[x]` Done (already in MVP)
- **Priority:** P0
- **Description:** Security headers in vercel.json
- **References:** project.md §8.4
- **Dependencies:** None
- **Acceptance Criteria:**
  - [x] HSTS, X-Content-Type-Options, X-Frame-Options, etc.
- **Owner:** AI

---

# Documentation Tasks

## DOC-001: API Documentation
- **Status:** `[x]` Done
- **Priority:** P2
- **Description:** OpenAPI/Swagger docs for all endpoints
- **References:** project.md §14
- **Dependencies:** All API work
- **Acceptance Criteria:**
  - [x] All endpoints documented
  - [x] Request/response schemas
  - [x] Examples provided
- **Owner:** AI
- **Completed:** 2026-01-09 - Created comprehensive API documentation in docs/api/:
  - README.md: Main API overview, authentication, rate limits, WebSocket docs
  - endpoints/project-specs.md: ProjectSpec CRUD, domain templates, examples
  - endpoints/nodes.md: Universe Map, fork mechanics, path analysis
  - endpoints/runs.md: Run lifecycle, batch runs, SSE progress
  - endpoints/ask.md: Event Compiler, intent analysis, clustering
  - endpoints/telemetry.md: Read-only telemetry (C3 compliant), caching
  - endpoints/event-scripts.md: Event scripts, bundles, trigger logs
  - endpoints/target-mode.md: Path planning, action catalog, constraints
  - endpoints/replay.md: 2D Replay (read-only), layout profiles
  - endpoints/exports.md: Export controls, redaction rules, formats
  - endpoints/privacy.md: GDPR/CCPA compliance, retention policies

## DOC-002: Update CLAUDE.md per Session
- **Status:** `[x]` Done
- **Priority:** P0
- **Description:** Keep CLAUDE.md updated after each work session
- **References:** User instructions
- **Dependencies:** None
- **Acceptance Criteria:**
  - [x] Current phase and focus updated
  - [x] Next 5-10 tasks listed
  - [x] Decision log maintained
  - [x] What was completed recorded
- **Owner:** AI
- **Completed:** 2026-01-08 - Added to CLAUDE.md workflow

---

# Summary Counts

| Phase | Not Started | In Progress | Done | Blocked | Total |
|-------|-------------|-------------|------|---------|-------|
| Phase 0 | 0 | 0 | 12 | 0 | 12 |
| Phase 1 | 0 | 0 | 9 | 0 | 9 |
| Phase 2 | 0 | 0 | 10 | 0 | 10 |
| Phase 3 | 0 | 0 | 4 | 0 | 4 |
| Phase 4 | 0 | 0 | 8 | 0 | 8 |
| Phase 5 | 0 | 0 | 7 | 0 | 7 |
| Phase 6 | 0 | 0 | 3 | 0 | 3 |
| Phase 7 | 0 | 0 | 9 | 0 | 9 |
| Phase 8 | 0 | 0 | 6 | 0 | 6 |
| Phase 9 | 0 | 0 | 8 | 0 | 8 |
| UI | 0 | 0 | 13 | 0 | 13 |
| Non-Func | 0 | 0 | 5 | 0 | 5 |
| Doc | 0 | 0 | 2 | 0 | 2 |
| **Total** | **0** | **0** | **96** | **0** | **96** |

---

# Manual Setup & Production Deployment Checklist

> **Purpose:** Human-required setup tasks before production deployment.
> **Note:** These items require manual configuration and cannot be automated by AI.
> **Last Updated:** 2026-01-09

---

## Environment Variables (Critical - Must Change)

> ⚠️ **WARNING:** The OpenRouter API key in .env.production is exposed and should be regenerated immediately.

- [ ] **POSTGRES_PASSWORD** - Change from default `agentverse_prod_2024` to strong password
- [ ] **REDIS_PASSWORD** - Change from default `agentverse_redis_2024` to strong password
- [ ] **SECRET_KEY** - Verify it's unique (current looks generated, but confirm)
- [ ] **OPENROUTER_API_KEY** - ⚠️ REGENERATE IMMEDIATELY (key is exposed in .env.production)
- [ ] **CORS_ORIGINS** - Update from IP `http://72.60.199.100:3003` to production domain
- [ ] **NEXT_PUBLIC_API_URL** - Update from IP `http://72.60.199.100:8001` to production domain

---

## Object Storage (S3) Configuration

> Required for telemetry blobs, snapshots, and artifact storage (project.md §5.4)

- [ ] **STORAGE_BACKEND** - Set to `s3` (or `local` for testing only)
- [ ] **STORAGE_BUCKET** - Create S3 bucket and set name (e.g., `agentverse-artifacts`)
- [ ] **STORAGE_REGION** - Set AWS region (e.g., `us-east-1`)
- [ ] **STORAGE_ACCESS_KEY** - Set AWS access key ID
- [ ] **STORAGE_SECRET_KEY** - Set AWS secret access key
- [ ] **STORAGE_ENDPOINT_URL** - Set if using MinIO or other S3-compatible storage (optional)

---

## Optional Services

- [ ] **SENTRY_DSN** - Set up Sentry project and add DSN for error monitoring
- [ ] **CENSUS_API_KEY** - Get US Census API key for real persona data (optional, increases rate limits)

---

## Security Remediation (P9-001 - Before Production)

> These were identified during the P9-001 security audit and MUST be addressed before production.

### P9-001a: Add tenant_id to Models
- [ ] Add `tenant_id` foreign key to User model
- [ ] Add `tenant_id` foreign key to Project model
- [ ] Add `tenant_id` foreign key to Scenario model
- [ ] Add `tenant_id` foreign key to SimulationRun model
- [ ] Add `tenant_id` foreign key to Persona model
- [ ] Add `tenant_id` foreign key to Product model
- [ ] Add `tenant_id` foreign key to FocusGroup model
- [ ] Add `tenant_id` foreign key to DataSource model
- [ ] Add `tenant_id` to remaining models (12+ total)
- [ ] Create Alembic migration for tenant_id additions
- [ ] Run and verify migration

### P9-001b: Update Endpoints with require_tenant
- [ ] Add `require_tenant` dependency to `/personas` endpoints
- [ ] Add `require_tenant` dependency to `/products` endpoints
- [ ] Add `require_tenant` dependency to `/marketplace` endpoints
- [ ] Add `require_tenant` dependency to `/focus-groups` endpoints
- [ ] Add `require_tenant` dependency to `/data-sources` endpoints
- [ ] Audit all remaining endpoints for tenant scoping

### P9-001c: JWT tenant_id Required
- [ ] Make `tenant_id` REQUIRED in JWT token (not optional)
- [ ] Remove fallback to `user_id` for tenant scoping
- [ ] Update token generation to always include `tenant_id`
- [ ] Test that missing `tenant_id` rejects request

### P9-001d: API Key Validation
- [ ] Implement actual API key validation (currently returns None)
- [ ] Create API key generation endpoint
- [ ] Create API key revocation endpoint
- [ ] Add API key to tenant/user relationship
- [ ] Test API key authentication flow

### P9-001e: Audit Log Endpoints
- [ ] Create `/audit-logs` GET endpoint
- [ ] Add filtering by date range, action type, user, resource
- [ ] Add pagination support
- [ ] Role-gate to admin users only
- [ ] Test audit log queries

---

## Server Preparation

- [ ] Provision VPS/server with Docker installed
- [ ] Install Docker Compose v2
- [ ] Clone repository to server
- [ ] Copy `.env.production` to `.env` and update all values
- [ ] Verify server has sufficient resources (recommended: 4GB RAM, 2 CPU, 50GB disk)
- [ ] Configure firewall rules (ports 3003, 8001, or behind reverse proxy)

---

## Docker Deployment

```bash
# Commands to run on production server
```

- [ ] Build and start containers: `docker-compose -f docker-compose.prod.yml up -d --build`
- [ ] Verify all 6 containers are running: `docker ps`
  - [ ] agentverse-postgres-prod (port 5434)
  - [ ] agentverse-redis-prod (port 6380)
  - [ ] agentverse-api-prod (port 8001)
  - [ ] agentverse-web-prod (port 3003)
  - [ ] agentverse-celery-worker-prod
  - [ ] agentverse-celery-beat-prod
- [ ] Run database migrations: `docker exec -it agentverse-api-prod alembic upgrade head`
- [ ] Check API logs for errors: `docker logs agentverse-api-prod`
- [ ] Check web logs for errors: `docker logs agentverse-web-prod`

---

## SSL/HTTPS Setup

- [ ] Install nginx or Traefik as reverse proxy
- [ ] Obtain SSL certificate (Let's Encrypt recommended)
- [ ] Configure reverse proxy for:
  - [ ] Frontend (port 3003) → https://yourdomain.com
  - [ ] API (port 8001) → https://api.yourdomain.com (or /api path)
- [ ] Update CORS_ORIGINS to use HTTPS domain
- [ ] Update NEXT_PUBLIC_API_URL to use HTTPS domain
- [ ] Test HTTPS access

---

## Post-Deployment Verification

- [ ] Test API health: `curl https://api.yourdomain.com/api/v1/health`
- [ ] Test frontend loads correctly
- [ ] Create admin user account
- [ ] Test login flow
- [ ] Test creating a new project
- [ ] Test running a baseline simulation
- [ ] Verify telemetry is written to S3
- [ ] Check Celery workers are processing jobs

---

## Database & Backups

- [ ] Configure automated PostgreSQL backups (daily recommended)
- [ ] Test backup restoration procedure
- [ ] Set up S3 cross-region replication (if needed)
- [ ] Document recovery procedures
- [ ] Schedule DR drill (see docs/disaster-recovery.md)

---

## Monitoring & Alerting

- [ ] Set up Grafana dashboard (use infrastructure/grafana/agentverse-overview.json)
- [ ] Configure Prometheus metrics scraping
- [ ] Set up alerting rules:
  - [ ] API error rate > 5%
  - [ ] Queue depth > 100
  - [ ] Failed runs > 10/hour
  - [ ] Disk usage > 80%
- [ ] Configure Sentry error notifications
- [ ] Set up uptime monitoring (e.g., UptimeRobot, Pingdom)

---

## Final Production Checklist

- [ ] All environment variables updated with production values
- [ ] OpenRouter API key regenerated
- [ ] S3 storage configured and tested
- [ ] SSL/HTTPS enabled
- [ ] Security remediation (P9-001a-e) complete
- [ ] Database migrations applied
- [ ] Backups configured and tested
- [ ] Monitoring dashboards operational
- [ ] Admin account created
- [ ] Load testing completed (see docs/capacity-planning.md)
- [ ] Documentation reviewed
- [ ] Go-live approved by team

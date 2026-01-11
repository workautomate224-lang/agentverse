# Future Predictive AI Platform — Ultra Detailed Implementation & Verification Checklist

Single-file, production-grade checklist to eliminate black boxes. Designed to be committed into the
repo and used as the execution + QA contract for an AI programmer. Every box must be PASS (checked)
or tracked as FAIL with an issue/PR and an Evidence Pack.

Generated: 2026-01-10 (Asia/Kuala_Lumpur)


## Operating Rules

- [ ] Execute strictly in order: STEP 0 → STEP 10. Do not start STEP N+1 until STEP N is PASS.
- [ ] Every 'real' execution must emit evidence artifacts: RunSpec + RunTrace + OutcomeReport (and PlanningSpec/PlanTrace when applicable).
- [ ] Any UI element that can be clicked must have a documented Button→Backend Chain Map and an automated/typed contract.
- [ ] If a behavior cannot be proven by artifacts, logs, or tests, treat it as NOT IMPLEMENTED.
- [ ] For every failure mode, implement a visible error surface (UI) + structured error (API) + audit log entry.

## Core Object Glossary (Must Exist or Equivalent Semantics)

- [ ] Project: project_id, owner/org_id, settings, created_at
- [ ] UniverseNode: node_id, project_id, parent_node_id, baseline flag, patch_id, created_at
- [ ] UniverseEdge: edge_id, project_id, parent_node_id, child_node_id, patch_id/event_id, created_at
- [ ] PersonaProfile: persona_id, project_id, attributes, provenance
- [ ] PersonaSegment: segment_id, project_id, definition, weight
- [ ] PersonaSnapshot: snapshot_id, project_id, immutable segments+weights, snapshot_hash, created_at
- [ ] Event: event_id, project_id, source_text, type, params, scope, injection_time, ambiguity/confidence
- [ ] NodePatch: patch_id, project_id, parent_node_id, deltas, affected_variables, patch_hash, created_at
- [ ] Run: run_id, project_id, node_id, status, worker_id, job_id, created_at, finished_at
- [ ] RunSpec: run_id, spec_hash, seed, horizon/ticks_total, environment_spec, model_bundle, data_cutoff, created_at
- [ ] RunTrace: run_id, tick/time, agent_id, state summary, action markers, event markers, timestamps
- [ ] OutcomeReport: run_id and/or node_id, distribution, confidence, drivers, evidence refs
- [ ] PlanningSpec: planning_id, project_id, start_node_id, target_snapshot_id, constraints, search_config, budget, seed
- [ ] PlanTrace: planning_id, candidates, pruning, run_ids per candidate, scoring breakdown
- [ ] CalibrationScenario: scenario_id, cutoff, ground_truth, protocol
- [ ] CalibrationReport: scenario_id, metrics (Brier/ECE), predicted vs actual, evidence refs
- [ ] StabilityReport: node/spec reference, seeds, variance metrics
- [ ] DriftReport: dimension, stats deltas, severity
- [ ] ReliabilityScore: node_id, component scores, final score
- [ ] AuditLog: immutable, actor_id, action_type, entity ids, timestamp, hash
- [ ] CostRecord: run_id/planning_id, tokens, compute_time, queue_latency, ensemble_count
- [ ] ExportBundle: bundle_id, manifest, artifact ids, checksums

## STEP 0 — Repo, Environments, Observability, Determinism

Goal: Make the system debuggable and reproducible. If STEP 0 is weak, every later step becomes a
black box.

### Repository Boot & Dev Experience

- [ ] One-command boot for full stack (e.g., docker compose up) including DB, queue, worker, API, frontend.
- [ ] One-command teardown resets dev state safely (no accidental prod deletion).
- [ ] One-command run unit tests + integration tests (backend).
- [ ] One-command run lint/typecheck/tests (frontend).
- [ ] .env.example includes every required env var with comment docs and sane defaults.
- [ ] Dev seed script creates: 1 project, baseline node, 2 persona snapshots, 1 event, 2 nodes, 2 runs, 1 replay-able run.
- [ ] API versioning policy documented (e.g., /api/v1).
- [ ] DB migration tool documented + 'migrate up/down' commands.
- [ ] Local storage for traces/exports defined (S3/minio/local) and documented.
- [ ] CI pipeline runs tests + migrations + minimal smoke simulation run.

### Logging, Metrics, and Error Surfacing

- [ ] Structured JSON logs for API and worker including request_id, project_id, run_id, planning_id.
- [ ] Correlation ID propagation API → queue job → worker → DB writes → logs.
- [ ] Centralized error format: {error_code, message, details, trace_id}.
- [ ] UI error toasts show error_code and link to debug panel.
- [ ] Health endpoints: API /health, Worker /health/worker, DB connectivity check /health/db.
- [ ] Basic metrics: run throughput, success rate, avg latency, queue depth, token burn rate.
- [ ] Admin debug page can inspect last N runs and their error summaries.
- [ ] Sentry (or equivalent) integrated with PII redaction.

### Determinism & Repro Packs

- [ ] Global random seed strategy documented; seeds flow into simulation, samplers, planner.
- [ ] Spec hashing uses canonical JSON; exclude volatile fields from hash inputs.
- [ ] Repro Pack export for any run: RunSpec + Trace snippet + Outcome + checksums.
- [ ] Replay determinism test exists (same run_id playback identical).
- [ ] Time handling: store UTC, display local; time cutoff comparisons use UTC.
- [ ] Feature flags system exists (even minimal) for toggling expensive modules in dev.

### Security & Privacy Hygiene

- [ ] Secrets scanning prevents committing API keys.
- [ ] PII redaction rules for logs and traces.
- [ ] Max upload sizes enforced for persona import and export bundles.
- [ ] Role-based access stub exists (user/org) to avoid future rewrite.
- [ ] Data retention policy config exists for trace storage (TTL).

## STEP 1 — Runs & Jobs Reality (No Fake Completion)

### UI Pages & Buttons

### Runs Panel — Button→Backend Chain Checks

- [ ] [Runs Panel] Button 'Run Simulation' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Run Simulation' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Run Simulation' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Runs Panel] Button 'Run Ensemble' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Run Ensemble' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Run Ensemble' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Runs Panel] Button 'View Run Details' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'View Run Details' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'View Run Details' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Runs Panel] Button 'Cancel Run' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Cancel Run' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Cancel Run' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Runs Panel] Button 'Retry Failed Run' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Retry Failed Run' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Retry Failed Run' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Runs Panel] Button 'Export Repro Pack' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Export Repro Pack' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Export Repro Pack' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.

### Run Details Drawer — Button→Backend Chain Checks

- [ ] [Run Details Drawer] Button 'Open RunSpec' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Open RunSpec' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Open RunSpec' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Run Details Drawer] Button 'Open RunTrace' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Open RunTrace' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Open RunTrace' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Run Details Drawer] Button 'Open OutcomeReport' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Open OutcomeReport' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Open OutcomeReport' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Run Details Drawer] Button 'Open Raw Logs' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Open Raw Logs' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Open Raw Logs' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Run Details Drawer] Button 'Download Evidence Pack' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Download Evidence Pack' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Download Evidence Pack' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.

### Backend / Worker / Data Checks

- [ ] Run state machine enforces valid transitions server-side only.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] RunSpec compilation fails fast on missing fields; never silently defaults to 0/0 ticks.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] Queue job enqueue is transactional with Run update (job_id stored).
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] Worker claims job with atomic lock (no double-claim).
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] RunTrace writer streams increments; incomplete trace marks run INCOMPLETE/FAILED.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] OutcomeReport writer is idempotent (retries do not duplicate).
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] Progress streaming via SSE/WebSocket uses backpressure; polling fallback exists.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] Dead-letter queue (DLQ) records permanent failures with remediation hints.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.

### Verification (Manual + Automated)

- [ ] Manual: worker offline shows queued state and 'no worker online' indicator.
  - [ ] Record exact reproduction steps and expected outputs.
  - [ ] Attach evidence (screenshots/JSON) into the step Evidence Pack.
- [ ] Manual: invalid spec yields clear error, no 0/0 tick UI.
  - [ ] Record exact reproduction steps and expected outputs.
  - [ ] Attach evidence (screenshots/JSON) into the step Evidence Pack.
- [ ] Manual: cancel run stops worker and writes terminal status + audit log.
  - [ ] Record exact reproduction steps and expected outputs.
  - [ ] Attach evidence (screenshots/JSON) into the step Evidence Pack.
- [ ] Auto: trace has ≥N ticks for non-trivial run; outcome has numeric distribution.
  - [ ] Record exact reproduction steps and expected outputs.
  - [ ] Attach evidence (screenshots/JSON) into the step Evidence Pack.
- [ ] Auto: illegal transitions rejected (e.g., SUCCEEDED→RUNNING).
  - [ ] Record exact reproduction steps and expected outputs.
  - [ ] Attach evidence (screenshots/JSON) into the step Evidence Pack.

## STEP 2 — Project Overview + Baseline Truthfulness

### UI Pages & Buttons

### Project Create — Button→Backend Chain Checks

- [ ] [Project Create] Button 'Create Project' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Create Project' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Create Project' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Project Create] Button 'Create and Run Baseline Now' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Create and Run Baseline Now' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Create and Run Baseline Now' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.

### Overview — Button→Backend Chain Checks

- [ ] [Overview] Button 'Refresh Snapshot' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Refresh Snapshot' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Refresh Snapshot' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Overview] Button 'View Baseline Node' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'View Baseline Node' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'View Baseline Node' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Overview] Button 'Run Baseline (if pending)' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Run Baseline (if pending)' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Run Baseline (if pending)' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Overview] Button 'Download Project Snapshot' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Download Project Snapshot' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Download Project Snapshot' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.

### Backend / Worker / Data Checks

- [ ] Project creation creates exactly one baseline root UniverseNode atomically.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] Baseline completion gating: UI badge only if baseline run SUCCEEDED + outcome exists.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] ProjectSnapshot endpoint aggregates baseline/latest nodes, counts, costs, reliability status.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] Baseline immutability enforced: baseline cannot be edited, only forked.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] Reopening project does not create new baseline nodes; DB constraint prevents duplicates.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.

### Verification (Manual + Automated)

- [ ] Manual: create project produces one baseline node.
  - [ ] Record exact reproduction steps and expected outputs.
  - [ ] Attach evidence (screenshots/JSON) into the step Evidence Pack.
- [ ] Manual: Baseline Complete appears only after successful baseline run with outcome.
  - [ ] Record exact reproduction steps and expected outputs.
  - [ ] Attach evidence (screenshots/JSON) into the step Evidence Pack.
- [ ] Auto: DB uniqueness for baseline per project enforced.
  - [ ] Record exact reproduction steps and expected outputs.
  - [ ] Attach evidence (screenshots/JSON) into the step Evidence Pack.
- [ ] Auto: ProjectSnapshot matches DB truth and returns no placeholder values.
  - [ ] Record exact reproduction steps and expected outputs.
  - [ ] Attach evidence (screenshots/JSON) into the step Evidence Pack.

## STEP 3 — Personas (Snapshots, Validation, Influence Proof)

### UI Pages & Buttons

### Personas — Button→Backend Chain Checks

- [ ] [Personas] Button 'Import Personas' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Import Personas' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Import Personas' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Personas] Button 'Generate Personas' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Generate Personas' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Generate Personas' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Personas] Button 'Deep Search Personas' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Deep Search Personas' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Deep Search Personas' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Personas] Button 'Validate Set' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Validate Set' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Validate Set' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Personas] Button 'Save as Snapshot' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Save as Snapshot' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Save as Snapshot' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Personas] Button 'Set as Default Snapshot' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Set as Default Snapshot' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Set as Default Snapshot' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.

### Persona Snapshot Viewer — Button→Backend Chain Checks

- [ ] [Persona Snapshot Viewer] Button 'View Snapshot JSON' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'View Snapshot JSON' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'View Snapshot JSON' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Persona Snapshot Viewer] Button 'Compare Snapshots' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Compare Snapshots' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Compare Snapshots' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Persona Snapshot Viewer] Button 'Lock Snapshot' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Lock Snapshot' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Lock Snapshot' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Persona Snapshot Viewer] Button 'Export Snapshot' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Export Snapshot' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Export Snapshot' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.

### Backend / Worker / Data Checks

- [ ] PersonaSnapshot is immutable; runs reference snapshot_id in RunSpec.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] Validation produces PersonaValidationReport persisted and linked to snapshot.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] OutcomeReport includes segment driver analysis (which segments contributed).
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] Modifying personas produces new snapshot_id; old snapshots remain usable for replay.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] Deep search (if used) records provenance and respects cutoff where applicable.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.

### Verification (Manual + Automated)

- [ ] Manual: two runs with different snapshots yield different outcomes.
  - [ ] Record exact reproduction steps and expected outputs.
  - [ ] Attach evidence (screenshots/JSON) into the step Evidence Pack.
- [ ] Auto: RunSpec always includes personas_snapshot_id.
  - [ ] Record exact reproduction steps and expected outputs.
  - [ ] Attach evidence (screenshots/JSON) into the step Evidence Pack.
- [ ] Auto: snapshot immutability enforced (update creates new snapshot).
  - [ ] Record exact reproduction steps and expected outputs.
  - [ ] Attach evidence (screenshots/JSON) into the step Evidence Pack.
- [ ] Manual: validation report reduces confidence when coverage gaps exist.
  - [ ] Record exact reproduction steps and expected outputs.
  - [ ] Attach evidence (screenshots/JSON) into the step Evidence Pack.

## STEP 4 — Universe Map (Nodes, Patches, Ensembles, Unlimited Branching)

### UI Pages & Buttons

### Universe Map — Button→Backend Chain Checks

- [ ] [Universe Map] Button 'Create Fork' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Create Fork' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Create Fork' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Universe Map] Button 'Compare Nodes' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Compare Nodes' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Compare Nodes' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Universe Map] Button 'Collapse Branches' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Collapse Branches' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Collapse Branches' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Universe Map] Button 'Prune Low Probability' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Prune Low Probability' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Prune Low Probability' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Universe Map] Button 'Prune Low Reliability' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Prune Low Reliability' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Prune Low Reliability' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Universe Map] Button 'Refresh Stale Nodes' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Refresh Stale Nodes' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Refresh Stale Nodes' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.

### Node Details — Button→Backend Chain Checks

- [ ] [Node Details] Button 'View Patch' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'View Patch' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'View Patch' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Node Details] Button 'Run Node Ensemble' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Run Node Ensemble' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Run Node Ensemble' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Node Details] Button 'View Aggregated Outcome' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'View Aggregated Outcome' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'View Aggregated Outcome' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Node Details] Button 'List Runs' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'List Runs' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'List Runs' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Node Details] Button 'Open Replay' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Open Replay' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Open Replay' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.

### Backend / Worker / Data Checks

- [ ] Fork creates child node + patch; parent is immutable.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] Node has one-to-many runs; aggregated outcome computed from ensemble.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] Probability aggregation stored with method metadata; never hardcoded.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] No backend hard limit on child count; UI uses pruning/collapse logic.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] Staleness marking exists for downstream nodes when upstream changes occur.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.

### Verification (Manual + Automated)

- [ ] Manual: create >10 child nodes; backend allows it.
  - [ ] Record exact reproduction steps and expected outputs.
  - [ ] Attach evidence (screenshots/JSON) into the step Evidence Pack.
- [ ] Auto: aggregated outcome equals normalized ensemble counts.
  - [ ] Record exact reproduction steps and expected outputs.
  - [ ] Attach evidence (screenshots/JSON) into the step Evidence Pack.
- [ ] Manual: compare nodes shows patch diff + outcome diff + reliability diff.
  - [ ] Record exact reproduction steps and expected outputs.
  - [ ] Attach evidence (screenshots/JSON) into the step Evidence Pack.

## STEP 5 — Natural Language Event Compiler (Candidates → Validation → Patch Binding)

### UI Pages & Buttons

### Event Lab — Button→Backend Chain Checks

- [ ] [Event Lab] Button 'Compile What-if' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Compile What-if' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Compile What-if' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Event Lab] Button 'Select Candidate' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Select Candidate' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Select Candidate' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Event Lab] Button 'Edit Parameters' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Edit Parameters' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Edit Parameters' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Event Lab] Button 'Apply to Node' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Apply to Node' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Apply to Node' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Event Lab] Button 'Save as Template' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Save as Template' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Save as Template' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Event Lab] Button 'Delete Event' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Delete Event' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Delete Event' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.

### Event Candidate Modal — Button→Backend Chain Checks

- [ ] [Event Candidate Modal] Button 'Show Missing Fields' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Show Missing Fields' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Show Missing Fields' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Event Candidate Modal] Button 'Show Affected Variables' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Show Affected Variables' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Show Affected Variables' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Event Candidate Modal] Button 'Show Scope Preview' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Show Scope Preview' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Show Scope Preview' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.

### Backend / Worker / Data Checks

- [ ] Event parsing returns multiple candidates on ambiguity.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] Validation enforces variable existence, ranges, conflicts; prompts for missing info.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] Applying candidate creates patch with patch_hash; binds to child node.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] RunTrace records injection tick and deltas; OutcomeReport references event/patch ids.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] Reproducibility: same event+parent produces same patch_hash and spec (except seed).
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.

### Verification (Manual + Automated)

- [ ] Manual: ambiguous event yields multiple candidates; user chooses one.
  - [ ] Record exact reproduction steps and expected outputs.
  - [ ] Attach evidence (screenshots/JSON) into the step Evidence Pack.
- [ ] Auto: invalid params rejected with error_code and details.
  - [ ] Record exact reproduction steps and expected outputs.
  - [ ] Attach evidence (screenshots/JSON) into the step Evidence Pack.
- [ ] Manual: event overlay appears at correct tick in replay.
  - [ ] Record exact reproduction steps and expected outputs.
  - [ ] Attach evidence (screenshots/JSON) into the step Evidence Pack.

## STEP 6 — Target Mode (Single Target, Multi-Path Planning with Evidence)

### UI Pages & Buttons

### Target Mode — Button→Backend Chain Checks

- [ ] [Target Mode] Button 'Create Planning Spec' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Create Planning Spec' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Create Planning Spec' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Target Mode] Button 'Run Planning' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Run Planning' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Run Planning' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Target Mode] Button 'View Top Plans' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'View Top Plans' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'View Top Plans' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Target Mode] Button 'Compare Plans' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Compare Plans' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Compare Plans' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Target Mode] Button 'Export Plan Evidence' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Export Plan Evidence' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Export Plan Evidence' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.

### Plan Details — Button→Backend Chain Checks

- [ ] [Plan Details] Button 'View PlanTrace' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'View PlanTrace' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'View PlanTrace' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Plan Details] Button 'Open Evidence Runs' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Open Evidence Runs' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Open Evidence Runs' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Plan Details] Button 'Open Node Chain' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Open Node Chain' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Open Node Chain' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Plan Details] Button 'Re-run Candidate' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Re-run Candidate' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Re-run Candidate' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Plan Details] Button 'Mark Plan Verified' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Mark Plan Verified' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Mark Plan Verified' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.

### Backend / Worker / Data Checks

- [ ] PlanningSpec stored with goal, constraints, search_config, budget, seed, action_library_version.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] Planner generates candidates, evaluates via simulation runs (ensemble), aggregates scores.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] PlanTrace stores candidate gen, pruning, run_ids, scoring breakdown.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] Unverified plans are clearly labeled when simulation evidence missing.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] Reproducibility enforced with seed + deterministic candidate ordering.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.

### Verification (Manual + Automated)

- [ ] Manual: Top plans link to runs, nodes, outcomes; no orphan suggestions.
  - [ ] Record exact reproduction steps and expected outputs.
  - [ ] Attach evidence (screenshots/JSON) into the step Evidence Pack.
- [ ] Auto: PlanTrace includes pruning reasons and run_ids per candidate.
  - [ ] Record exact reproduction steps and expected outputs.
  - [ ] Attach evidence (screenshots/JSON) into the step Evidence Pack.
- [ ] Manual: changing action library version changes planning outputs.
  - [ ] Record exact reproduction steps and expected outputs.
  - [ ] Attach evidence (screenshots/JSON) into the step Evidence Pack.

## STEP 7 — Calibration & Reliability (Cutoff, Stability, Drift, Confidence)

### UI Pages & Buttons

### Calibration Lab — Button→Backend Chain Checks

- [ ] [Calibration Lab] Button 'Create Calibration Scenario' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Create Calibration Scenario' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Create Calibration Scenario' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Calibration Lab] Button 'Run Calibration' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Run Calibration' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Run Calibration' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Calibration Lab] Button 'View Calibration Metrics' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'View Calibration Metrics' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'View Calibration Metrics' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Calibration Lab] Button 'Run Stability Test' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Run Stability Test' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Run Stability Test' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Calibration Lab] Button 'Run Drift Scan' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Run Drift Scan' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Run Drift Scan' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Calibration Lab] Button 'Auto-Tune Parameters' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Auto-Tune Parameters' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Auto-Tune Parameters' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Calibration Lab] Button 'Rollback Parameters' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Rollback Parameters' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Rollback Parameters' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.

### Reliability Panel — Button→Backend Chain Checks

- [ ] [Reliability Panel] Button 'View Reliability Breakdown' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'View Reliability Breakdown' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'View Reliability Breakdown' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Reliability Panel] Button 'Download Reliability Report' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Download Reliability Report' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Download Reliability Report' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.

### Backend / Worker / Data Checks

- [ ] Cutoff enforcement blocks post-cutoff data access; evidence includes timestamps.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] CalibrationReport stores Brier/ECE + predicted vs actual + evidence refs.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] StabilityReport stores variance across seeds; impacts reliability score.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] DriftReport stores persona/data/model drift; impacts reliability score.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] ReliabilityScore computed by explicit rules and displayed with component breakdown.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] Auto-tune versioned with rollback; never mutates baseline silently.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.

### Verification (Manual + Automated)

- [ ] Manual: calibration refuses post-cutoff evidence.
  - [ ] Record exact reproduction steps and expected outputs.
  - [ ] Attach evidence (screenshots/JSON) into the step Evidence Pack.
- [ ] Auto: reliability score decreases with high variance or drift.
  - [ ] Record exact reproduction steps and expected outputs.
  - [ ] Attach evidence (screenshots/JSON) into the step Evidence Pack.
- [ ] Manual: rollback restores prior parameter set and logs audit entry.
  - [ ] Record exact reproduction steps and expected outputs.
  - [ ] Attach evidence (screenshots/JSON) into the step Evidence Pack.

## STEP 8 — 2D Replay / Visualization (Trace-Driven, Deterministic)

### UI Pages & Buttons

### Replay Viewer — Button→Backend Chain Checks

- [ ] [Replay Viewer] Button 'Play' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Play' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Play' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Replay Viewer] Button 'Pause' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Pause' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Pause' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Replay Viewer] Button 'Step Forward' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Step Forward' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Step Forward' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Replay Viewer] Button 'Step Backward' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Step Backward' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Step Backward' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Replay Viewer] Button 'Jump to Tick' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Jump to Tick' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Jump to Tick' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Replay Viewer] Button 'Toggle Event Overlay' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Toggle Event Overlay' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Toggle Event Overlay' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Replay Viewer] Button 'Toggle Segment Highlights' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Toggle Segment Highlights' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Toggle Segment Highlights' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Replay Viewer] Button 'Export Replay Bundle' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Export Replay Bundle' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Export Replay Bundle' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.

### 2D Scene Controls — Button→Backend Chain Checks

- [ ] [2D Scene Controls] Button 'Zoom' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Zoom' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Zoom' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [2D Scene Controls] Button 'Pan' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Pan' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Pan' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [2D Scene Controls] Button 'Focus Agent' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Focus Agent' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Focus Agent' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [2D Scene Controls] Button 'Show Agent State Card' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Show Agent State Card' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Show Agent State Card' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [2D Scene Controls] Button 'Show Variable Panel' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Show Variable Panel' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Show Variable Panel' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.

### Backend / Worker / Data Checks

- [ ] Replay reads only from stored RunTrace; cannot run without trace.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] Trace schema includes minimal location/state fields required for deterministic replay.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] Event overlays are driven by Event/Patch + trace injection markers.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] Exports include manifest + checksums for RunSpec/Trace/Outcome + replay config.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] Replay can open from any node/run and shows linked evidence.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.

### Verification (Manual + Automated)

- [ ] Manual: replay same run twice → identical.
  - [ ] Record exact reproduction steps and expected outputs.
  - [ ] Attach evidence (screenshots/JSON) into the step Evidence Pack.
- [ ] Auto: trace schema validation prevents missing fields for visualization.
  - [ ] Record exact reproduction steps and expected outputs.
  - [ ] Attach evidence (screenshots/JSON) into the step Evidence Pack.
- [ ] Manual: overlay matches injection tick and variable deltas.
  - [ ] Record exact reproduction steps and expected outputs.
  - [ ] Attach evidence (screenshots/JSON) into the step Evidence Pack.

## STEP 9 — Knowledge Graph / Parallel Universe Ops (Dependency, Compare, Prune, Refresh)

### UI Pages & Buttons

### Universe Graph — Button→Backend Chain Checks

- [ ] [Universe Graph] Button 'Switch View: Tree/Graph' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Switch View: Tree/Graph' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Switch View: Tree/Graph' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Universe Graph] Button 'Search Node' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Search Node' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Search Node' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Universe Graph] Button 'Filter by Probability' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Filter by Probability' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Filter by Probability' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Universe Graph] Button 'Filter by Reliability' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Filter by Reliability' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Filter by Reliability' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Universe Graph] Button 'Cluster Similar Branches' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Cluster Similar Branches' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Cluster Similar Branches' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Universe Graph] Button 'Mark Stale' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Mark Stale' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Mark Stale' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Universe Graph] Button 'Refresh Branch' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Refresh Branch' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Refresh Branch' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.

### Node Compare — Button→Backend Chain Checks

- [ ] [Node Compare] Button 'Select A' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Select A' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Select A' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Node Compare] Button 'Select B' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Select B' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Select B' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Node Compare] Button 'Show Diff' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Show Diff' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Show Diff' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Node Compare] Button 'Export Diff Report' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Export Diff Report' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Export Diff Report' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.

### Backend / Worker / Data Checks

- [ ] Graph API returns nodes+edges with paging; UI does not invent edges.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] Dependency tracking marks downstream stale when upstream patch/personas/model changes.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] Node compare returns patch diff + outcome diff + driver diff + reliability diff.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] Pruning/collapse operate as UI filters without deleting data unless explicit delete action used.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] Refresh reruns only stale nodes with cost estimate and audit logs.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.

### Verification (Manual + Automated)

- [ ] Manual: edit upstream → downstream stale markers propagate.
  - [ ] Record exact reproduction steps and expected outputs.
  - [ ] Attach evidence (screenshots/JSON) into the step Evidence Pack.
- [ ] Auto: compare endpoint returns consistent diff given same node pair.
  - [ ] Record exact reproduction steps and expected outputs.
  - [ ] Attach evidence (screenshots/JSON) into the step Evidence Pack.
- [ ] Manual: pruning hides branches without data loss.
  - [ ] Record exact reproduction steps and expected outputs.
  - [ ] Attach evidence (screenshots/JSON) into the step Evidence Pack.

## STEP 10 — Governance, Cost Controls, Safety, Access Control, Auditability

### UI Pages & Buttons

### Admin / Governance — Button→Backend Chain Checks

- [ ] [Admin / Governance] Button 'View Audit Logs' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'View Audit Logs' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'View Audit Logs' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Admin / Governance] Button 'Set Quotas' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Set Quotas' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Set Quotas' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Admin / Governance] Button 'View Costs' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'View Costs' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'View Costs' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Admin / Governance] Button 'Manage Feature Flags' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Manage Feature Flags' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Manage Feature Flags' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Admin / Governance] Button 'Review Safety Blocks' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Review Safety Blocks' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Review Safety Blocks' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Admin / Governance] Button 'Manage Exports' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Manage Exports' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Manage Exports' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.

### Billing Hooks — Button→Backend Chain Checks

- [ ] [Billing Hooks] Button 'View Usage' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'View Usage' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'View Usage' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Billing Hooks] Button 'View Quota Remaining' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'View Quota Remaining' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'View Quota Remaining' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Billing Hooks] Button 'Upgrade Tier (stub)' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Upgrade Tier (stub)' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Upgrade Tier (stub)' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.
- [ ] [Billing Hooks] Button 'Download Invoice (stub)' has a single authoritative backend endpoint (no UI-only state).
  - [ ] Click 'Download Invoice (stub)' triggers request with request_id and relevant ids (project/node/run/planning).
  - [ ] Backend validates input schema and permissions; returns typed error on failure.
  - [ ] Backend writes explicit DB records for 'Download Invoice (stub)' action (or confirms no-op) and emits AuditLog entry.
  - [ ] Backend emits CostRecord updates if action triggers LLM/compute.
  - [ ] UI shows loading state + success state driven by backend response, not assumptions.
  - [ ] Failure mode: user sees actionable remediation + link to debug details.

### Backend / Worker / Data Checks

- [ ] CostRecord stored per run/planning/calibration; estimator returns pre-run cost range.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] Quotas enforced server-side with degrade/block behaviors.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] Feature flags enforced server-side (API guards) for tiered plans.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] Rate limiting for runs/plans/events to prevent abuse and cost spikes.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] Safety classifier blocks/downgrades high-risk requests; logs decisions.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] AuditLog is immutable, append-only; includes actor, action, entity ids, spec_hash, timestamp.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.
- [ ] Export bundles include integrity metadata; access checks + audit log for every download.
  - [ ] Has unit tests for core logic and schema validation.
  - [ ] Emits structured logs with request_id and entity ids.
  - [ ] Writes an AuditLog entry when it changes state/data.

### Verification (Manual + Automated)

- [ ] Manual: exceed quota → blocked/degraded + audit log.
  - [ ] Record exact reproduction steps and expected outputs.
  - [ ] Attach evidence (screenshots/JSON) into the step Evidence Pack.
- [ ] Manual: high-risk request → safety block + logged reason code.
  - [ ] Record exact reproduction steps and expected outputs.
  - [ ] Attach evidence (screenshots/JSON) into the step Evidence Pack.
- [ ] Auto: feature gate cannot be bypassed via API.
  - [ ] Record exact reproduction steps and expected outputs.
  - [ ] Attach evidence (screenshots/JSON) into the step Evidence Pack.
- [ ] Auto: export manifest checksums validate.
  - [ ] Record exact reproduction steps and expected outputs.
  - [ ] Attach evidence (screenshots/JSON) into the step Evidence Pack.

## Appendix A — Artifact Field Completeness (RunSpec / Trace / Outcome / Planning)

These checks ensure artifacts are not placeholders and are sufficient to debug and reproduce every
result.

### RunSpec

- [ ] spec_hash present and stable for identical canonical inputs.
- [ ] contains project_id, node_id, personas_snapshot_id, patch/event references.
- [ ] contains model_bundle identifiers (model name, version, prompt hash).
- [ ] contains environment schema version (state space & action space versions).
- [ ] contains ticks_total/horizon and tick duration assumptions.
- [ ] contains data_cutoff (if applicable) and retrieval policy mode.
- [ ] contains random seed and stochastic config.
- [ ] contains resource budget hints (max tokens, max tool calls).
- [ ] contains safety policy mode for the run (allowed/blocked categories).

### RunTrace

- [ ] tick index starts at 0 (or 1) consistently; no gaps unless explicitly recorded.
- [ ] each tick has timestamp; monotonic ordering guaranteed.
- [ ] agent_id present; mapping to persona/segment available.
- [ ] state summary includes at least location (x,y or zone) + key state variables.
- [ ] action marker recorded for each agent action; includes action type and params.
- [ ] event injection markers present; includes event_id/patch_id and deltas applied.
- [ ] trace is append-only; no retroactive edits.
- [ ] trace can be paged and streamed; supports large runs.
- [ ] trace integrity hash or chunk hashes stored (optional but recommended).

### OutcomeReport

- [ ] outcome distribution numeric and sums to 1.0 (or 100%).
- [ ] confidence/reliability score present with component breakdown references.
- [ ] top drivers include variable/segment/action contributions with scores.
- [ ] links to evidence artifacts (RunSpec/Trace ids, Event ids, PersonaSnapshot id).
- [ ] contains aggregation metadata if derived from ensemble runs.
- [ ] contains warnings: data gaps, drift severity, stability variance.
- [ ] contains export-ready summary section and a machine-readable JSON form.

### PlanningSpec

- [ ] planning_id, project_id, start_node_id, target_snapshot_id present.
- [ ] goal definition explicit and machine-readable (success criteria).
- [ ] constraints explicit (time/budget/forbidden actions).
- [ ] search_config includes algorithm type + parameters.
- [ ] evaluation budget includes runs per candidate, max candidates, max depth/time.
- [ ] action_library_version present; changes version changes results.
- [ ] seed present for deterministic candidate ordering.

### PlanTrace

- [ ] records candidate generation order and features used to generate candidates.
- [ ] records pruning decisions with reason codes (e.g., low score bound).
- [ ] records run_ids executed per candidate and their spec_hashes.
- [ ] records score breakdown per candidate (success prob/cost/risk).
- [ ] records stop reason (budget/time/depth) and totals (candidates evaluated).

### CalibrationReport

- [ ] scenario_id, cutoff, protocol version, predicted vs actual stored.
- [ ] metric values stored (Brier/ECE) + raw confusion data where relevant.
- [ ] evidence timestamps recorded; post-cutoff evidence blocked or flagged.
- [ ] includes run_ids/nodes used for calibration and their spec_hashes.

### AuditLog

- [ ] append-only; cannot be updated/deleted without admin break-glass and reason.
- [ ] records actor_id, org_id, action_type, entity ids, timestamp, spec_hash.
- [ ] records client_ip or session id if allowed; respects privacy requirements.
- [ ] supports filtering by project/node/run/planning and time range.

## Appendix B — Page Inventory & Required Panels (UI Completeness)

Ensure the UI stays simple for users while exposing deep evidence via optional drawers. Check each
panel exists and is wired to backend truth.

### Project List

- [ ] Project List: Panel/Control exists — Create Project CTA
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Project List: Panel/Control exists — Project search
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Project List: Panel/Control exists — Recent projects
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Project List: Panel/Control exists — Project cards show baseline status
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Project List: Panel/Control exists — Open project
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Project List: Panel/Control exists — Delete project (if supported) with confirmation and audit log
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.

### Project Overview

- [ ] Project Overview: Panel/Control exists — Baseline status widget
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Project Overview: Panel/Control exists — Latest node widget
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Project Overview: Panel/Control exists — Reliability widget
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Project Overview: Panel/Control exists — Cost-to-date widget
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Project Overview: Panel/Control exists — Quick Run CTA
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Project Overview: Panel/Control exists — Links to Personas, Universe Map, Event Lab, Target Mode, Calibration, Replay
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.

### Personas

- [ ] Personas: Panel/Control exists — Import
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Personas: Panel/Control exists — Generate
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Personas: Panel/Control exists — Deep Search
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Personas: Panel/Control exists — Segments editor
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Personas: Panel/Control exists — Weights slider
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Personas: Panel/Control exists — Validate
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Personas: Panel/Control exists — Save snapshot
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Personas: Panel/Control exists — Snapshot list
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Personas: Panel/Control exists — Snapshot compare
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Personas: Panel/Control exists — Snapshot lock indicator
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.

### Universe Map

- [ ] Universe Map: Panel/Control exists — Graph/tree view toggle
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Universe Map: Panel/Control exists — Node list
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Universe Map: Panel/Control exists — Node detail drawer
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Universe Map: Panel/Control exists — Fork button
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Universe Map: Panel/Control exists — Compare button
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Universe Map: Panel/Control exists — Prune controls
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Universe Map: Panel/Control exists — Reliability filter
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Universe Map: Panel/Control exists — Stale indicators
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Universe Map: Panel/Control exists — Refresh branch
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.

### Event Lab

- [ ] Event Lab: Panel/Control exists — Natural language input box
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Event Lab: Panel/Control exists — Candidate list
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Event Lab: Panel/Control exists — Parameter editor
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Event Lab: Panel/Control exists — Scope preview
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Event Lab: Panel/Control exists — Apply event to node
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Event Lab: Panel/Control exists — Save template
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Event Lab: Panel/Control exists — Template library
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Event Lab: Panel/Control exists — Event history
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.

### Runs

- [ ] Runs: Panel/Control exists — Run creation form
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Runs: Panel/Control exists — Ensemble toggle
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Runs: Panel/Control exists — Seed controls
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Runs: Panel/Control exists — Queue status
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Runs: Panel/Control exists — Run list
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Runs: Panel/Control exists — Run detail drawer
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Runs: Panel/Control exists — Cancel/Retry
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Runs: Panel/Control exists — Repro pack export
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.

### Target Mode

- [ ] Target Mode: Panel/Control exists — Target input
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Target Mode: Panel/Control exists — Goal builder
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Target Mode: Panel/Control exists — Constraints
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Target Mode: Panel/Control exists — Action library selector
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Target Mode: Panel/Control exists — Search config (advanced drawer)
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Target Mode: Panel/Control exists — Run planning
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Target Mode: Panel/Control exists — Top plans list
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Target Mode: Panel/Control exists — Plan detail
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Target Mode: Panel/Control exists — Evidence links
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Target Mode: Panel/Control exists — Export plan report
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.

### Calibration Lab

- [ ] Calibration Lab: Panel/Control exists — Scenario library
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Calibration Lab: Panel/Control exists — Create scenario
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Calibration Lab: Panel/Control exists — Cutoff picker
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Calibration Lab: Panel/Control exists — Run calibration
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Calibration Lab: Panel/Control exists — Metrics view
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Calibration Lab: Panel/Control exists — Stability test
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Calibration Lab: Panel/Control exists — Drift scan
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Calibration Lab: Panel/Control exists — Reliability breakdown
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Calibration Lab: Panel/Control exists — Auto-tune & rollback
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.

### Replay

- [ ] Replay: Panel/Control exists — Run selector
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Replay: Panel/Control exists — Play controls
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Replay: Panel/Control exists — Tick panel
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Replay: Panel/Control exists — Event overlay
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Replay: Panel/Control exists — Agent focus
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Replay: Panel/Control exists — Variable panel
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Replay: Panel/Control exists — Export replay bundle
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.

### Admin/Governance

- [ ] Admin/Governance: Panel/Control exists — Audit log viewer
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Admin/Governance: Panel/Control exists — Cost dashboard
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Admin/Governance: Panel/Control exists — Quota settings
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Admin/Governance: Panel/Control exists — Feature flags
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Admin/Governance: Panel/Control exists — Safety review
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.
- [ ] Admin/Governance: Panel/Control exists — Exports manager
  - [ ] Loads data from backend API and handles empty/error states.
  - [ ] Includes minimal tooltips or inline help for non-expert users.

# Future Predictive AI Platform — Verification & Evidence Checklist (Deep Implementation Proof)
**Document type:** Implementation-proof checklist (beyond UI/feature presence)  
**Audience:** Engineering team + AI coding agent executing tests with minimal interpretation  
**Goal:** Prove that results are produced via the intended **simulation + branching + calibration** mechanisms (not “looks right” shortcuts).  
**Version:** v2.0 (Deep Proof)  
**Date:** 2026-01-09 (Asia/Kuala_Lumpur)

---

## 0) What “PASS” means in this checklist
A test **passes only if**:
1. The **UI output** exists (result visible), **AND**
2. The system emits a **machine-verifiable Evidence Pack** proving the backend executed the required internal mechanisms, **AND**
3. The evidence is consistent with **reversible, on-demand** principles (forking, determinism, artifact lineage), **AND**
4. No leakage (for backtests) and no hidden “single-shot LLM answer” path.

> If a feature “works” but you cannot produce the evidence below, treat it as **FAIL**.

---

## 1) Mandatory Debug/Evidence Interfaces (must exist before running any checklist)
If any item is missing, implement it first (this is not optional for verification).

### 1.1 Evidence Pack Export (per Run and per Node)
**Required capability:** Export a JSON (or zipped bundle) for a given `run_id` or `node_id` containing:

- `artifact_lineage`
  - project_id, node_id, parent_node_id, edge_id
  - run_ids aggregated into node
  - scenario_patch_ref
- `run_config`
  - engine_version, ruleset_version, dataset_version, schema_version
  - horizon/ticks, scheduler_profile, logging_profile
  - seed_strategy + list of seeds used
- `execution_proof`
  - counters: ticks_executed, agent_steps_executed
  - rule_application_counts (by rule name + insertion point)
  - scheduler_stats (partitions, batches, sampling ratios)
  - event_execution_log (event_id, tick, scope)
  - policy_update_log (if any learning loop): updates_count, epochs, convergence metric snapshots
  - external_call_log: network calls count, LLM calls count (by component)
- `telemetry_proof`
  - telemetry_ref, keyframe_count, delta_count
  - telemetry_hash/signature (stable hash)
  - replay_index_presence (seek index)
- `results_proof`
  - aggregated metrics + hashes
  - probability normalization report (siblings sum to 1 under same parent)
- `reliability_proof` (if available)
  - calibration_cutoff, leakage_guard flags
  - stability variance across seeds
  - sensitivity scan summary
  - drift score summary
- `audit_proof`
  - actor (user/service), timestamp
  - permission context, tenant_id
  - quota consumption record

**PASS evidence:** Evidence Pack exports successfully and is internally consistent.

### 1.2 Determinism Signature API
**Required capability:** Given the same `RunConfig + seeds + dataset_version + ruleset_version + engine_version`, the system returns:
- `result_hash`
- `telemetry_hash`
- `run_config_hash`

**PASS evidence:** Hashes match across repeated runs (see §3.2).

### 1.3 Time-Cutoff / Anti-Leakage Gate (for backtests)
**Required capability:** When running backtests, system must enforce:
- dataset rows/documents have timestamps
- the engine/compiler cannot access evidence after `cutoff_time`

**PASS evidence:** Evidence Pack includes:
- cutoff_time
- filtered_data_counts (before/after)
- leakage_guard = true
- blocked_access_attempts count (should be 0 if implemented correctly; >0 indicates guard is catching attempts)

### 1.4 “No Hidden Runtime LLM in Agent Tick” Proof
**Required capability:** Every run reports LLM usage counts by component:
- persona generation (allowed)
- event compilation (allowed)
- target planning helper (allowed if validated)
- **society tick loop** (must be 0 at scale)

**PASS evidence:** For Society Mode runs, `LLM_calls_in_tick_loop == 0`.

---

## 2) Global Invariants (system-wide proofs)
Run these invariants on any environment before scenario tests.

### 2.1 Forking Not Editing (Reversibility Proof)
**Steps**
1. Pick an existing node `N0`.
2. Apply a variable change via “Fork & Tune” → creates `N1`.
3. Fetch `N0` again; verify it is unchanged.

**Evidence required**
- Node record immutability: `N0.state_ref`, `N0.results_ref`, `N0.telemetry_ref` unchanged
- `N1.parent_node_id == N0.node_id`
- `N1.scenario_patch_ref` exists and contains only deltas
- Audit log shows **create** not **update** for parent artifacts

**PASS criteria**
- Parent node immutable; child node created with patch diff.

---

### 2.2 On-Demand Execution Only
**Steps**
1. Open Replay/2D view for node `N`.
2. Observe system logs and run/job queue.

**Evidence required**
- No new run created
- No new compute job enqueued
- Evidence Pack: `replay_action` logs show telemetry read only

**PASS criteria**
- Replay never triggers simulation.

---

### 2.3 Artifact Lineage Completeness
**Steps**
1. For node `N`, export Evidence Pack.
2. Confirm all refs exist and are retrievable.

**Evidence required**
- run_ids exist and map to node
- telemetry exists and is queryable
- reliability report attached or explicitly “not computed”
- config versions pinned

**PASS criteria**
- No dangling references.

---

### 2.4 Conditional Probability Correctness
**Steps**
1. Choose a parent node with multiple children.
2. Export probability report.

**Evidence required**
- `sum(P(child_i | parent)) == 1` (within tolerance, e.g., 0.999–1.001)
- If clustering is used:
  - cluster node probability equals sum of contained leaves (or documented approximation with error bounds)

**PASS criteria**
- Probabilities are conditional and normalized.

---

## 3) Engine-Level Proofs (the “is it really that engine?” tests)

### 3.1 Society Mode: Agent Loop Execution Proof (Observe→Evaluate→Decide→Act→Update)
This section proves the system did not “shortcut” to a single LLM answer or a direct formula.

**Steps**
1. Run Society baseline with:
   - agents >= 1,000 (or the platform’s realistic test scale)
   - horizon >= 200 ticks
2. Export Evidence Pack.

**Evidence required**
- `ticks_executed == horizon`
- `agent_steps_executed == ticks_executed * active_agents` (allow sampling if declared; then evidence must show sampling ratios)
- `loop_stage_counters`:
  - observe_count, evaluate_count, decide_count, act_count, update_count
- Stage timing:
  - avg latency per stage (optional but recommended)
- Rule insertion proof:
  - each rule indicates insertion point and count (e.g., `conformity@Decide: 200k applications`)

**PASS criteria**
- All five stages executed repeatedly with non-trivial counts.
- Rule applications occur at declared insertion points.
- No runtime LLM calls inside tick loop.

**“Looks like but FAIL” indicators**
- ticks_executed small (e.g., 1–3)
- agent_steps_executed far below expected without declared sampling
- rule_application_counts missing
- results appear but loop_stage_counters absent

---

### 3.2 Deterministic Reproducibility Proof
**Steps**
1. Run the exact same config twice (same seeds, versions).
2. Compare determinism signatures.

**Evidence required**
- `run_config_hash` identical
- `result_hash` identical
- `telemetry_hash` identical (or identical within documented nondeterministic fields; if so, these fields must be excluded from hash)

**PASS criteria**
- Hashes match.

**FAIL indicators**
- result changes with same seed/config
- telemetry changes unpredictably (suggests hidden nondeterminism or time-based randomness)

---

### 3.3 Scheduler Proof (Not a naive single-thread loop)
**Steps**
1. Run Society with scheduler_profile = `fast` and again with `accurate`.
2. Export scheduler stats from Evidence Packs.

**Evidence required**
- partitions/batches counts
- sampling policy (if any) explicitly reported
- backpressure metrics (queue time, worker time)
- identical deterministic rules for same config within same profile

**PASS criteria**
- Scheduler stats exist and differ meaningfully between profiles.
- Outputs differ in expected ways (fast may be noisier; accurate more stable), but both remain reproducible.

---

### 3.4 Rule Pack Proof (Rules are applied, not just “selected in UI”)
**Steps**
1. Create two runs:
   - Run A: rule pack ON (e.g., conformity high)
   - Run B: rule pack OFF (or conformity near 0)
2. Compare outcome shifts.

**Evidence required**
- rule_application_counts show large difference between A and B
- sensitivity report indicates conformity is a driver
- telemetry shows social influence events/updates in A more than B

**PASS criteria**
- Measurable and explainable differences consistent with rules.

---

### 3.5 Event Script Execution Proof (Compiled once, executed deterministically)
**Steps**
1. Use Ask to generate an event (e.g., “tariffs increase by X%”).
2. Inspect event script and run.
3. Re-run with same event script ID.

**Evidence required**
- event script exists with:
  - scope, deltas, start/end ticks, intensity profile
  - compiler_version
- event execution log shows:
  - event_id executed at correct ticks
  - affected scope counts
- deterministic replay: identical event effects under same seeds

**PASS criteria**
- Event is executed from structured script, not re-interpreted by LLM during run.

---

### 3.6 Progressive Expansion Proof (No hard cap; controlled growth)
**Steps**
1. Ask a broad question to produce many branches.
2. Verify UI initially shows cluster(s).
3. Expand cluster multiple times.

**Evidence required**
- cluster node created with `contains_n_candidates` metadata
- expand calls produce additional child nodes incrementally
- expansion strategy evidence:
  - information_gain ranking or documented heuristic
- no “fixed limit” in backend; candidate pool exists

**PASS criteria**
- Branches grow progressively, not capped.
- System remains responsive and auditable.

---

## 4) Target Mode Proofs (single-object, multi-event decision engine)

### 4.1 Action Space is generated + validated (not a static list)
**Steps**
1. Create a Target project or enter Target Mode.
2. Provide target persona and context.
3. Ask system to propose actions; then run planner.

**Evidence required**
- action_space artifact includes:
  - actions with preconditions, effects, costs/risks, constraints tags
- validation log:
  - rejected actions with reasons (precondition fail, policy violation, duplicates)

**PASS criteria**
- Actions are structured and validated; rejected actions are logged.

---

### 4.2 Planner is an iterative search (not one-shot)
**Steps**
1. Run Target planner with:
   - horizon sufficient for multiple steps (e.g., 10–30 steps)
   - progressive expansion enabled
2. Export Evidence Pack.

**Evidence required**
- search counters:
  - explored_states, expanded_nodes, pruned_paths
- pruning reasons breakdown:
  - constraint violated, dominated path, low probability
- path clustering metadata:
  - cluster ids, representative paths, cluster probability sums
- optional: rollout counts if using rollout-based planning

**PASS criteria**
- Non-trivial search occurs; pruning/clustering evidence present.
- Multiple plausible paths exist with probabilities.

**FAIL indicators**
- only one path returned with no search stats
- no pruning reasons, no constraint checks logged

---

### 4.3 Constraint Engine Proof (constraints actually bite)
**Steps**
1. Add a hard constraint that should remove many actions/paths.
2. Re-run planner.

**Evidence required**
- increased pruned_paths count
- explicit constraint-violation logs
- different path set vs no-constraint run

**PASS criteria**
- Constraints materially change the search space and outputs.

---

### 4.4 Path→Universe Map Bridge Proof
**Steps**
1. Select one target path and “Branch to Universe Map”.
2. Verify a new node is created.

**Evidence required**
- new node created with:
  - parent_node_id
  - scenario_patch_ref derived from path actions/events
- edge references the selected path
- node telemetry contains action sequence events

**PASS criteria**
- Path becomes a first-class branch in Universe Map with lineage.

---

## 5) Hybrid Mode Proofs (key actors + social context coupling)

### 5.1 Bidirectional coupling proof (two-way influence exists)
**Steps**
1. Run Hybrid with:
   - at least 1 key actor (Target-like)
   - a population context (Society)
2. Export Evidence Pack.

**Evidence required**
- coupling logs show:
  - key actor action modifies world variables / event triggers in society
  - society metrics (public sentiment, adoption) feed back into key actor perception/state
- counters show both engines executed:
  - society agent_steps_executed
  - target planner/decision steps executed

**PASS criteria**
- Two-way influence is present and logged.

**FAIL indicators**
- hybrid output equals society-only or target-only with no coupling evidence

---

## 6) Telemetry & 2D Replay Proofs (read-only renderer, consistent with logs)

### 6.1 Replay is derived from telemetry only
**Steps**
1. Open 2D Replay for node `N`.
2. Seek randomly across time.

**Evidence required**
- telemetry query logs show chunked reads and index usage
- no new run created
- playback tick matches telemetry tick
- clicking an agent/zone shows “why” with event_id references

**PASS criteria**
- Read-only; “why” traces back to logged events/deltas.

---

### 6.2 Telemetry sufficiency & integrity
**Steps**
1. For a node with replay enabled, export telemetry proof.

**Evidence required**
- keyframes exist
- deltas exist
- telemetry_hash stable across replays
- if telemetry too thin: system explicitly flags “replay degraded”

**PASS criteria**
- Telemetry supports explainable replay; integrity checks exist.

---

## 7) Reliability/Calibration Proofs (benchmark backbone)

### 7.1 Backtest harness enforces time cutoff (anti-leakage)
**Steps**
1. Choose a historical scenario with a known outcome.
2. Set cutoff_time before the outcome.
3. Run calibration/backtest.

**Evidence required**
- cutoff_time stored in RunConfig and Evidence Pack
- dataset_version corresponds to cutoff-filtered dataset
- blocked_access_attempts = 0 (or >0 with clear guard logs, still PASS if no leakage)
- reliability report references cutoff_time explicitly

**PASS criteria**
- No future data leakage possible; evidence demonstrates enforcement.

---

### 7.2 Calibration is bounded and rollback-able (not overfit)
**Steps**
1. Run calibration on Scenario A.
2. Apply auto-tune.
3. Validate on Scenario B (holdout).
4. Rollback tuning and compare.

**Evidence required**
- tuned parameters list + bounds
- error metrics improvement on A
- no catastrophic degradation on B
- rollback restores previous parameter set and reproducibility

**PASS criteria**
- Tuning improves or preserves generalization; rollback works.

---

### 7.3 Stability & Sensitivity are real (not UI placeholders)
**Steps**
1. Run multi-seed evaluation for a node.
2. Run sensitivity scan for top variables.

**Evidence required**
- stability variance numbers + seed list
- sensitivity ranked list with deltas
- telemetry references showing variable perturbations applied in forked runs

**PASS criteria**
- Values are computed from runs; lineage exists.

---

### 7.4 Drift detection triggers appropriately
**Steps**
1. Create synthetic drift (change persona distributions or key input distributions).
2. Run drift detection.

**Evidence required**
- drift score changes
- warning badges appear
- report includes which features shifted

**PASS criteria**
- Drift mechanism is working and explainable.

---

## 8) Production-readiness Proofs (launch gating)

### 8.1 Multi-tenancy isolation
**Steps**
1. Create two tenants A and B.
2. Attempt to access A’s nodes/runs from B.

**Evidence required**
- access denied
- audit log records attempt
- no cross-tenant object storage reads possible

**PASS criteria**
- Hard isolation is enforced end-to-end.

---

### 8.2 Quotas, rate limits, and job concurrency
**Steps**
1. Submit many runs concurrently beyond quota.
2. Verify system behavior.

**Evidence required**
- requests throttled or queued with clear messaging
- no runaway worker usage
- quota consumption recorded in Evidence Pack

**PASS criteria**
- System is resilient and controlled under load.

---

### 8.3 Audit logs & traceability
**Steps**
1. Run baseline, fork, ask, expand, replay.
2. Retrieve audit log.

**Evidence required**
- all actions recorded with actor, timestamps, tenant, project, run_id/node_id
- links to artifacts

**PASS criteria**
- Full traceability exists.

---

# 9) Scenario-Driven Backtests (real cases) — execution scripts
These tests prove “prediction mechanism” is genuine and time-aware.

> **Important rule:** You must provide the dataset yourself with timestamped sources.  
> This checklist verifies **mechanism integrity**. Accuracy depends on data quality + calibration.

---

## 9.1 Society Mode Backtest — National election (example: US presidential election date)
**Purpose:** Validate large-scale emergent dynamics with strict cutoff and reproducibility.

### Setup
- Scenario: National election outcome distribution (state/region aggregations)
- cutoff_time: choose multiple cutoffs (e.g., T-30d, T-7d)
- Inputs (timestamped):
  - demographics distribution
  - economic indicators up to cutoff
  - media topic intensity up to cutoff
  - optional polling up to cutoff (clearly marked as observations)

### Execution
1. Create Project (Collective Dynamics)
2. Import persona sets; validate coverage
3. Run Baseline (multi-seed)
4. Ask: “Introduce a late economic shock” (creates branch cluster)
5. Expand top cluster progressively (≥3 expansions)
6. For each node: generate reliability report, stability, sensitivity

### Required Evidence (mechanism proof)
- Anti-leakage cutoff proof (blocked access = 0 or guarded)
- Agent loop counters show sustained execution across horizon
- Rule insertion counts reflect applied rules
- Event scripts compiled once and executed deterministically
- Branch probabilities normalized
- Stability variance computed from seeds

### PASS criteria
- All required evidence present for baseline and branches
- Replay works and is read-only
- Reliability report attached

### Accuracy evaluation (optional but recommended)
- Compute Brier score / log loss using known outcomes
- Record “calibration curve” (predicted prob vs observed freq) across historical elections if available

---

## 9.2 Society Mode Backtest — Public policy response (safe, non-violent)
**Purpose:** Validate response dynamics to policy interventions.

### Example scenario
- A tax/subsidy policy change affecting consumer spending or adoption of a public service.
- Use a historical policy change with known aggregate trend.

### Execution
- Baseline with pre-policy conditions
- Event script representing policy change
- Compare outcome curves to historical trend

### Required Evidence
- Event timing and scope logs
- Variable-to-outcome causal driver list
- Sensitivity shows policy variable as a key driver

---

## 9.3 Target Mode Backtest — Product conversion journey (safe single-target)
**Purpose:** Validate that Target Mode is true multi-step planning with constraints.

### Example scenario
- Target: a “prospect persona” deciding whether to adopt a paid plan.
- Actions: trial, discount offer, feature education, social proof, reminder, etc.
- Constraints: budget, time, risk aversion.

### Execution
1. Create Target project
2. Import/create target persona + context constraints
3. Run planner (progressive expansion)
4. Add/remove constraints and verify path changes
5. Select top path → branch into Universe Map

### Required Evidence
- search counters: explored/pruned paths
- constraint violation logs
- path clusters with conditional probabilities
- bridge node created with lineage and telemetry action log

---

## 9.4 Hybrid Mode Backtest — Key decision-maker in population
**Purpose:** Validate bidirectional coupling between key actor decisions and population reaction.

### Example scenario
- Key actor: pricing decision of a provider (single decision-maker model)
- Population: customer segments reacting over time (society)
- Coupling: price decision changes adoption; adoption changes key actor’s next choice

### Execution
1. Create Hybrid project
2. Define key actor + population
3. Run hybrid baseline
4. Modify one coupling parameter → fork → rerun
5. Inspect coupling logs and outcome differences

### Required Evidence
- coupling logs in both directions
- both engines executed (society steps + key actor decision steps)
- fork lineage preserved

---

# 10) “Looks like vs Actually implemented” Red-Flag Guide
If any of these are observed, **pause launch** and fix:

1. **No Evidence Pack** (or missing loop counters) → cannot prove mechanism
2. **Replay triggers simulation** → violates on-demand and auditability
3. **No seed/version pinning** → irreproducible; not benchmark-grade
4. **LLM inside Society tick loop** at scale → likely cost/perf explosion and nondeterminism
5. **Fork modifies parent node** → breaks reversibility
6. **Branch count hard-capped** → not parallel-universe exploration; missing clustering/expansion
7. **Calibration uses post-cutoff data** (or cannot prove cutoff) → invalid backtests
8. **Constraints don’t prune** in Target Mode → planner is decorative
9. **Hybrid has no coupling logs** → it’s just two modes stapled together
10. **Reliability values present without run lineage** → placeholders, not computed

---

# 11) Launch Gate: “Ready to Production” Checklist
A release is production-ready only if:

- ✅ Global invariants (§2) all PASS
- ✅ Engine proofs (§3–§6) PASS on at least:
  - 1 Society scenario
  - 1 Target scenario
  - 1 Hybrid scenario
- ✅ Reliability proofs (§7) PASS (cutoff, stability, sensitivity, drift)
- ✅ Production proofs (§8) PASS (tenancy, quotas, audit logs)
- ✅ Backtest scripts (§9) executed with stored evidence bundles
- ✅ A “Reproducibility Report” is attached to release:
  - exact versions, config hashes, and baseline golden runs

---

## Appendix A — Evidence Pack naming & storage convention (recommended)
- `/evidence/{project_id}/{node_id}/{run_id}/evidence_pack.json`
- `/evidence/{project_id}/{node_id}/{run_id}/telemetry_hash.txt`
- `/evidence/{project_id}/{node_id}/{run_id}/results_hash.txt`
- `/evidence/{project_id}/{node_id}/{run_id}/reliability_report.json`

---

**End of verification checklist v2.0**

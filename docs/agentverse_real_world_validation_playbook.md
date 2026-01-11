# Agentverse — Real‑World Validation Playbook (Backtest + “No Black Boxes” Proof)
_Last updated: 2026‑01‑10_

This document is a **hands‑on test execution plan** to validate that Agentverse is not just “UI + one LLM call”, but a **multi‑module, multi‑step, reversible simulation platform** with auditable backend logic.

> ✅ Goal: After running this playbook, you can confidently say **“every page / button triggers the intended backend pipeline”** and you have **proof artifacts** to show it.

---

## 0) The One Rule: Every Button Must Produce Proof

For any user-visible action (Create Project, Expand Node, Auto‑Tune, Calibration, Run, Branch Aggregation, Export…), the backend must produce a **Run Evidence Pack**.

### 0.1 Run Evidence Pack (REP) — required artifacts
A REP is a folder (or DB record bundle) created for each run:

- **manifest.json**
  - `commit_sha`, `env`, `mode`, `project_id`, `scenario_id`
  - `time_cutoff` (ISO timestamp) and enforcement strategy
  - `seed`, `replicate_count`, `agent_count`, `step_count`
  - `model_provider`, `model_name`, `temperature`, `top_p`, `max_tokens`
  - `rulepacks[]`, `variables[]`, `constraints[]`
- **data_provenance.json**
  - list of ingested datasets/sources with: `source_name`, `source_type`, `retrieved_at`, `max_doc_date`, `hash`
- **trace.ndjson** (or equivalent)
  - append‑only event stream: `RUN_STARTED`, `AGENT_STEP`, `POLICY_UPDATE`, `WORLD_TICK`, `NODE_EXPAND`, `AGGREGATE`, `CALIBRATE`, `AUTO_TUNE`, `RUN_DONE`
- **llm_ledger.ndjson**
  - every LLM call: `call_id`, `purpose`, `input_hash`, `output_hash`, `tokens_in/out`, `latency_ms`, `cache_hit`, `model`
- **universe_graph.json**
  - nodes & edges with provenance: parent link, variable delta, probability estimates, confidence intervals
- **report.md**
  - plain‑English summary + metrics (accuracy, calibration, stability, drift checks)

> Pass/Fail:
> - **FAIL** if a button produces output without producing a REP.
> - **FAIL** if Universe Map expands without `NODE_EXPAND` + supporting simulation traces.

---

## 1) Test Philosophy: “Prove It’s Not a Single Prompt”

A real simulation pipeline leaves footprints:

- **Scaling footprints**: increasing `agent_count` or `replicate_count` should increase traces, runtime, and ledger entries.
- **Reproducibility footprints**: same seed + same inputs → same outputs (within allowed stochastic tolerance).
- **Causality footprints**: changing one variable produces a measurable shift, and the shift is explained in trace + aggregation.

If none of these footprints exist, it’s likely a thin wrapper around a single LLM response.

---

## 2) Mandatory Controls You Must Have Before Backtests

### 2.1 Time‑Cutoff Enforcement (“Only knows pre‑X”)
You cannot truly erase a model’s pretraining knowledge, but you can enforce **tool+evidence discipline**:

- **No live web** during backtest.
- **Retrieval filter**: only documents with `doc_date <= time_cutoff` can be retrieved.
- **Citation gate**: any factual claim must cite retrieved sources; uncited claims are rejected/flagged.
- **Leakage canaries**: ask “post‑cutoff” questions; system must refuse or say “not in evidence pack”.

Output must include:
- `time_cutoff` in manifest
- `max_doc_date` in `data_provenance.json` (must be <= cutoff)
- `leakage_test_results` section in report

### 2.2 Reversibility Contract (core engine)
For “100% reversible, on‑demand”:
- Every run is keyed by `(project_id, scenario_id, node_id, seed, replicate_id)`
- Universe Map is **a DAG of results**, not a live evolving world.
- Deleting a node deletes its REP + derived children unless explicitly retained.

---

## 3) Platform Test Map (Pages → Proof)

This is your “page-by-page” coverage. If your UI labels differ, map them one-to-one.

### 3.1 Dashboard
Buttons/features to validate:
- **Create Project**
- **Open Project**
- **Recent Runs**
- **System Health / Workers**
Proof:
- Dashboard load must show backend health checks and last 10 REPs.

### 3.2 Project Workspace
Tabs:
1) **Data**
2) **Personas**
3) **Rules / Variables**
4) **Mode Config (Society / Target / Hybrid)**
5) **Simulation**
6) **Universe Map**
7) **Calibration**
8) **Auto‑Tune**
9) **Stability Test**
10) **Reports / Export**

Each tab action must emit trace events and record REP diffs.

---

## 4) Test Suites (Run These in Order)

### Suite 0 — Smoke & Observability (30 minutes)
Goal: verify the platform can produce REPs end‑to‑end.

**Steps**
1. Create Project → choose any small template → Save.
2. Import 3 personas manually (tiny).
3. Select 1 rulepack.
4. Run simulation with `agent_count=5`, `step_count=5`, `replicate_count=2`.
5. Confirm REP exists and contains all mandatory files.

**Pass criteria**
- REP created
- trace contains at least: `RUN_STARTED`, `WORLD_TICK`, `AGENT_STEP`, `AGGREGATE`, `RUN_DONE`
- llm_ledger exists even if using mocks (records should show `mock=true`)

---

### Suite 1 — “Not a Single Prompt” Scaling Test (1 hour)
Goal: prove backend actually runs multi‑agent/replicate logic.

**Run A**
- `agent_count=10`, `step_count=10`, `replicate_count=3`

**Run B**
- `agent_count=200`, `step_count=30`, `replicate_count=10`

**Expected footprints**
- trace event counts scale roughly with `agent_count * step_count * replicate_count`
- llm_ledger call count scales (unless you have strong caching—if cached, you must show cache stats)

**Fail signals**
- both runs produce similar ledger counts or runtime
- trace shows only “one” LLM call and no per‑agent steps

---

### Suite 2 — Universe Map Correctness (Node Expand is Real Work) (2 hours)
Goal: verify Universe Map is derived from simulation + probability aggregation.

**Setup**
- Create a scenario with 1–3 controllable variables (e.g., “message framing”, “tax change”, “price change”).

**Node Expand Test**
1. Generate root node (baseline).
2. Click **Expand Node** (or “Branch”) with:
   - `branch_policy=diverse`
   - `max_branch=unlimited` (do NOT hardcap to 3–7; allow “budget-based cap”)
   - `replicate_count>=20` (so probabilities aren’t random)
3. Inspect REP:
   - `NODE_EXPAND` event exists
   - each child node has its own REP
   - `universe_graph.json` updated with new nodes + probabilities + confidence intervals

**Causality Test**
4. Choose one child node → modify a variable → Re-run.
5. Verify:
   - only that node and its descendants change
   - parent node remains intact (reversible DAG property)

**Fail signals**
- node expansion produces text but no new simulation traces
- probabilities do not change when replicate_count increases
- no confidence intervals / no aggregation logs

---

### Suite 3 — Calibration + Auto‑Tune (3–6 hours)
Goal: verify calibration isn’t cosmetic; it updates parameters, then improves metrics.

**Calibration**
- run `calibration_job` on a labeled dataset or event set (see Suites 4/5/6)
- outputs:
  - reliability diagram data
  - ECE/MCE/Brier score
  - tuned mapping parameters saved to project profile

**Auto‑Tune**
- objective: maximize calibration + accuracy under compute budget
- must log:
  - search space (agent_count range, step_count range, prompt policy, memory settings)
  - trials, metrics, chosen configuration

**Fail signals**
- “Auto‑Tune completed” but no trial logs
- tuning does not change runtime config or results

---

## 5) Real‑World Backtests (Mode‑Specific)

You asked for **real cases** per mode. Here are 3 that are measurable and reproducible.

### Suite 4 — Society Mode Backtest: 2024 US Presidential Election
> Note on date: Election Day was **Nov 5, 2024**; most “Nov 6” references are reporting time. Your cutoff should be **2024‑11‑05T00:00:00Z** (or earlier).

Ground truth references:
- 270toWin summarizes result as Trump 312 EV vs Harris 226 EV.  
- Reuters provides official results dashboards.  
- CFR recaps Electoral College vote casting and certification timeline.  
(See citations in the chat response that accompanies this file.)

**Test Goal**
Predict:
- winner
- electoral votes range (not necessarily exact)
- top 7 swing state outcomes (or a chosen set)

**Data Pack (pre‑cutoff)**
- state demographics
- historical turnout patterns
- polling averages up to cutoff
- macro indicators (inflation, unemployment) up to cutoff
- campaign event timeline up to cutoff

**Steps (UI)**
1) Create Project → Mode: **Society**
2) Set `time_cutoff = 2024‑11‑05`
3) Data → Import “ElectionDataPack_2024_pre1105”
4) Personas → Generate voter personas (N=5k–50k) via stratified sampling:
   - state, age, education, urban/rural, party lean
5) Rules → load:
   - persuasion susceptibility
   - turnout friction
   - media exposure
6) Simulation config:
   - `agent_count = 20k` (or scaled down for MVP)
   - `step_count = 50–200` (ticks of campaign timeline)
   - `replicate_count = 30–200` for probability stability
7) Run baseline → produce root node.
8) Universe Map → Expand with event variables:
   - “late economic shock”
   - “turnout surge in subgroup”
   - “messaging shift”
9) Calibration:
   - calibrate probabilities against historical election backtests (2012, 2016, 2020) if you have them
10) Report:
   - predicted winner + probabilities
   - calibrated confidence
   - ablation: remove media influence → see shift (sanity check)

**Pass criteria**
- REP proves multi‑agent ticks and replicate aggregation
- probabilities are stable when replicate_count increases
- results respond to variable ablations

---

### Suite 5 — Target Mode Backtest: Bank Marketing (Individual Decision)
Dataset:
- UCI Bank Marketing dataset (term deposit subscription).  
(See citations in the chat response.)

**Why it fits Target Mode**
Each row is “one client persona” and label is whether they subscribed (`y=yes/no`). This is perfect to validate:
- persona ingestion
- per‑persona decision policy
- calibration (probability of “yes”)

**Steps (UI)**
1) Create Project → Mode: **Target**
2) Data → Import `bank-additional-full.csv`
3) Persona mapping:
   - each row → persona attributes (age, job, etc.)
4) Define outcome:
   - `subscribe_term_deposit` (binary)
5) Run:
   - choose 1k rows for quick run, then 10k+
   - `replicate_count=5–20` to reduce stochastic noise
6) Evaluate:
   - accuracy, AUC, logloss
   - calibration: Brier score, reliability curve
7) Auto‑Tune:
   - try different decision policy prompts / memory / reasoning budgets
8) Export:
   - confusion matrix report
   - explanation traces for 30 random personas

**Pass criteria**
- platform can hit a reasonable baseline (don’t chase SOTA yet)
- calibration improves after calibration step
- trace shows per‑persona decision steps (not just one global summary)

---

### Suite 6 — Hybrid Mode Backtest: E‑commerce A/B Testing (Crowd + Segment)
Dataset options:
- Kaggle “Ecommerce AB Testing …” style datasets with conversion labels.  
(See citations in the chat response.)

**Why it fits Hybrid Mode**
- Society: overall traffic + network effects
- Target: high‑value segment (e.g., returning users) gets different behavior model

**Steps (UI)**
1) Create Project → Mode: **Hybrid**
2) Data → import A/B dataset
3) Define population agents:
   - segments: new vs returning, device types, geo
4) Define target agents:
   - “high intent shoppers”
5) Run simulations:
   - baseline (A), treatment (B)
6) Universe Map:
   - expand variables like “page load speed”, “discount visibility”
7) Evaluate:
   - predicted lift vs actual lift
   - segment-level lift

**Pass criteria**
- hybrid engine shows separate sub-models or policies
- aggregation matches known conversion lift directionally

---

## 6) Debug Playbook (When Something Looks “Black Box”)

### Symptom A: Universe nodes expand but no compute traces
Likely cause:
- node expansion is only an LLM “idea generator”
Fix:
- require `replicate_count >= 10` to be valid
- node probability must be computed from replicate outcomes
- enforce REP completeness before UI shows the node

### Symptom B: Calibration exists but doesn’t change anything
Fix:
- calibration must write parameters back to project config
- subsequent runs must show those params in manifest
- report must show metric deltas

### Symptom C: Results don’t change when variables change
Fix:
- add “variable influence tests” (ablation)
- log which variables were actually used by policy and environment transition

---

## 7) What “Done” Looks Like (for you as Product Owner)

You can open any run and see:

- what data was allowed (and time cutoff proof)
- what agents did (step-by-step)
- how branches were generated
- why probabilities look like that (replicates + aggregation)
- how calibration/autotune altered the engine
- how to reproduce the same run tomorrow

If any of these are missing, you don’t “own” the backend yet.

---

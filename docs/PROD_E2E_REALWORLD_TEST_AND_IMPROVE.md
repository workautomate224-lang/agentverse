# PROD_E2E_REALWORLD_TEST_AND_IMPROVE.md
> **Document Type:** Production E2E test + closed-loop improvement playbook  
> **Scope:** AgentVerse “Goal → Blueprint → Inputs → Runs → Universe Map → Report”  
> **Audience:** Engineering (execution) + Product/Founder (review)  
> **Rule:** Do not skip steps. Do not “mark PASS” without artifacts (IDs, screenshots, logs).  
> **Output:** A single report file: `REPORT_PROD_E2E_<YYYY-MM-DD>.md` (see template at the end)

---

## 0) What “Production-Level” Means Here

This is **not** a demo checklist. This is a *closed-loop* testing playbook:

1. Run a real-world case end-to-end (E2E).
2. Compare outputs to a defined acceptance bar.
3. If it fails, fix **the minimum** required to pass.
4. Re-run the *same case* until it passes.
5. Only then proceed to the next case.

**Definition of Done (DoD):**
- Both Case A and Case B complete E2E without manual hacks.
- Baseline and branch runs execute reliably (no silent fail; clear error surfaced when fail). A previous practical test flagged baseline runs failing due to worker issues, which must be eliminated. fileciteturn15file7L17-L23
- Universe Map (TEG) is usable as a **probability mind-map**, not a debugging graph. (Nodes represent likely outcomes/scenarios with probabilities; click → explain; expand → generate more; run → verify.)
- TEG “Expand” works with LLM in the Universe Map (currently partial due to route-specific LLM configuration issue). fileciteturn15file0L6-L7
- Reports reflect saved personas correctly (a prior test found “personas not reflected in report”). fileciteturn15file7L60-L63
- Missing/404 guidance endpoints are either implemented or removed from UI calls (non-blocking but must not spam errors). fileciteturn15file10L38-L41

---

## 1) Non-Negotiable Architecture Constraints (Do NOT violate)

These constraints are already documented as “non-negotiable” and must remain true during fixes:  
- **Fork-not-mutate:** never modify existing nodes; create new node on any change.  
- **On-demand:** no continuous simulation; run only when triggered.  
- **LLMs as compilers:** LLMs plan/compile; avoid tick-by-tick LLM loops. fileciteturn15file13L57-L62  
- **Auditable:** artifacts versioned, persisted, and reportable. fileciteturn15file13L57-L62

---

## 2) The Core User Flow We Are Hardening

**Create Project**
→ Goal Assistant (clarifying Q&A)
→ Blueprint (PIL) generated + previewed
→ Guidance Panel recommends inputs
→ Inputs gathered (AI helps) + saved
→ Baseline Run
→ Event Lab (what-if ideas)
→ Universe Map (TEG) expansion + branch runs
→ Compare outcomes
→ Report export

**Known issue:** TEG Expand currently blocked/partial due to LLM backend config differences between Universe Map endpoint and Event Lab, even though Event Lab LLM calls work. fileciteturn15file0L6-L7

---

## 3) Test Environment Requirements

### 3.1 Required capabilities (must be true before running Case A)
- **OpenRouter key is valid** in the environment used for the test (staging or local).
- **Simulation worker is healthy** (Celery/worker can execute baseline + branch). A previous E2E run created runs but execution failed with no details; this must be fixed before we can trust anything downstream. fileciteturn15file7L17-L23
- **Universe Map loads without loops/crashes** (already fixed per report; verify it stayed fixed). fileciteturn15file0L17-L18

### 3.2 Observability requirements (must be captured in the final report)
- Project ID(s)
- Run IDs (baseline + branches)
- For any failed run: correlation ID + error payload shown to user
- Screenshots:
  - Blueprint Preview
  - Data/Personas page showing saved inputs
  - Baseline run result
  - Universe Map graph showing verified node + expanded draft nodes
  - Report page

---

## 4) Fix-First: Stop-Ship Issues to Address If Found During Case A

These are “stop-ship” because they block the entire loop:

1. **Baseline/Branch runs fail silently**  
   - Must surface actionable error and fix worker health. fileciteturn15file7L17-L23
2. **TEG Expand cannot call LLM**  
   - Must unify/repair LLM configuration for the Universe Map expand route. fileciteturn15file0L6-L7
3. **Report doesn’t reflect saved personas**  
   - Must ensure report pulls from correct persona storage/query. fileciteturn15file7L60-L63
4. **404 guidance endpoints spam errors**  
   - Implement or remove the calls; do not leave broken UX. fileciteturn15file10L38-L41

---

## 5) Universe Map (TEG) Must Become a Probability Mind‑Map

### 5.1 User-facing requirements (production UX)
Universe Map should behave like a “parallel universe tree”:

- **Verified Outcome Node (Baseline / Branch):** shows probability + confidence + short summary.
- **Expand:** generates *candidate next events* (draft scenarios) — **no hard cap like 3–7**; instead:
  - Default show top 7 for readability
  - “Show more” loads additional scenarios (pagination). (This matches earlier next-step direction.) fileciteturn15file4L27-L29
- **Run Scenario:** converts draft → verified outcome node (new node, forked).
- **Details Panel:** must show:
  - “Why this probability?” (drivers + evidence)
  - “What data/personas influenced it?” (input provenance)
  - “What changed vs parent?” (delta)
- **Graph → Table → RAW:** must remain available, but Graph is the default for normal users.

### 5.2 Engineer-facing requirements (data model / consistency)
- Every node must carry:
  - `node_type`, `status`, `probability`, `confidence`
  - `blueprint_version` linkage (already tracked)
  - `run_ids` for verified nodes
  - `scenario_spec` for draft nodes
  - `evidence_refs` if applicable

---

## 6) Real-World Case A (Persona‑leaning) — “Interest Rate Shock → Spending Behavior”

This case is close to an existing practical test and should become your baseline “smoke test” scenario.

### 6.1 Goal (use as initial prompt)
**Goal prompt (user):**  
> “How will American consumers aged 25–55 change their spending habits if the Federal Reserve raises interest rates by 0.5% in Q1 2026?”

(Equivalent scenario was used in prior E2E testing; keep it consistent so we can compare regressions.) fileciteturn15file15L20-L22

### 6.2 Project creation parameters
- Strategy: whichever the platform recommends; do not force unless the system breaks.
- Temporal cutoff:
  - For this forward-looking scenario, set cutoff to “today - 1 day” to ensure temporal filter is active but not blocking.

### 6.3 Required input outcome (what must exist after “Inputs”)
- Personas saved (≥ 100) with clear coverage: regions, income, debt profile, homeowners/renters.
- At least one “Evidence / Data” artifact:
  - Either user-provided URLs (Fed statement, CPI trend) or minimal doc uploads.
- Rules/assumptions recorded:
  - Interest rate shock magnitude, time window, channels (mortgage rates, credit cards).

### 6.4 Execution steps (E2E)
1. Create project → finish Goal Assistant Q&A → Blueprint Preview shows expected drivers and required inputs.
2. Data & Personas:
   - Generate personas via natural language.
   - Attach 2–4 evidence URLs or upload minimal docs.
3. Run baseline.
4. Event Lab: ask 1 what-if question (rate cut instead / delayed hike).
5. Universe Map:
   - Confirm baseline verified node appears.
   - Expand baseline into draft scenarios.
   - Run at least 2 draft scenarios → produce verified nodes.
   - Compare baseline vs branches.

### 6.5 Acceptance criteria (must PASS)
- Baseline run completes successfully (no silent failure). Prior test had baseline fail due to worker; this must be fixed. fileciteturn15file7L17-L23
- Universe Map expansion produces multiple draft nodes and *at least* 2 can be run to verified outcomes.
- Report:
  - Shows personas count correctly (not “no personas”). fileciteturn15file7L60-L63
  - Shows evidence sources section.
  - Shows baseline vs branch comparison.

### 6.6 Failure → immediate fix loop
If any acceptance check fails:
- Stop. Do not proceed to Case B.
- Implement the smallest fix needed.
- Re-run Case A from project creation (new project) to confirm the fix is real.

---

## 7) Real-World Case B (Data‑heavy) — “Backtest: Tesla Revenue Forecast”

This case stress-tests data ingestion, blueprint slot guidance, evidence linkage, and numeric outputs.

### 7.1 Goal (use as initial prompt)
**Goal prompt (user):**  
> “Backtest: Using only information available up to 2022-12-31, forecast Tesla’s FY2023 total revenue (USD). Output a probability distribution (P10/P50/P90), and explain key drivers.”

### 7.2 Temporal isolation (must be enforced)
- Set project cutoff date to **2022-12-31**.
- Add an explicit “Evidence-only expectation” in the system context:
  - If the platform cannot cite evidence ≤ cutoff, it must declare “insufficient evidence” rather than hallucinate.

### 7.3 Evidence pack (engineering responsibility)
Attach official sources **dated ≤ 2022-12-31**, for example:
- Tesla 2022 annual report / 10-K
- Tesla quarterly results for 2022
- Deliveries / ASP summaries for 2022
- Macro context if used (rates, commodity inputs)

**Important:** Do not attach anything that includes FY2023 revenue results.

### 7.4 Execution steps (E2E)
1. Create project with prompt + cutoff.
2. Blueprint must recommend Data slots strongly; Personas should be optional/low weight.
3. “Inputs” phase must allow:
   - Evidence attachments (URLs/doc uploads)
   - Optional structured dataset upload (CSV) if supported; otherwise document the gap and implement minimal support.
4. Run baseline → produce predicted distribution.
5. Universe Map:
   - Expand into revenue-impact scenarios (demand swing, price cuts, supply constraints, competition).
   - Run at least 2 scenarios.
6. After results are produced:
   - Attach the **ground truth** FY2023 revenue document *only after* prediction is locked.
   - Compare whether GT is inside predicted interval.

### 7.5 Acceptance criteria (must PASS)
- Universe Map shows:
  - Baseline verified node with distribution summary (P10/P50/P90)
  - Draft nodes for scenario variations
  - Verified branch nodes after running scenarios
- Evidence compliance:
  - Node details must list evidence references and show cutoff compliance status.
- Backtest quality gate:
  - GT revenue should fall within the platform’s P10–P90 range.
  - If it misses, repeat with improvements (better slot extraction, numeric summarization, or scenario plan).

### 7.6 Leakage test (must PASS)
Re-run **the same project goal** with **no evidence attached**:
- Expected behavior: the system refuses to give a confident numeric forecast (or outputs very wide uncertainty + explicit insufficiency).
- If it confidently outputs a precise number anyway, treat as a “temporal isolation bypass” and fix prompts/guards.

---

## 8) Production Fix Targets (What We Expect to Improve While Running Tests)

You should not “build random features.” Fix only what the tests expose.

### Target 1: TEG Expand uses correct LLM config
Currently: Expand in Universe Map fails due to LLM backend config route issue while Event Lab works. fileciteturn15file0L6-L7  
**Fix intent:** unify LLM provider config and error handling across:
- Universe Map expand endpoint
- Event Lab ask endpoint

### Target 2: Simulation worker reliability + error surfacing
Prior practical test shows runs created but execution failed, with no detailed backend error returned. fileciteturn15file7L17-L23  
**Fix intent:** ensure worker is healthy and on failure returns:
- a stable error code
- a human-readable explanation
- a correlation ID for logs

### Target 3: Report correctness
Report must reflect personas saved; prior test indicated mismatch. fileciteturn15file7L60-L63

### Target 4: Guidance API 404 cleanup
Prior test logged missing guidance endpoints. fileciteturn15file10L38-L41  
**Fix intent:** implement or remove calls to avoid broken UX.

### Target 5: Universe Map readability
- Default to “simple mind-map”
- Table/RAW remain but not the primary user view
- “Show more” for extra scenarios (avoid hard caps). fileciteturn15file4L27-L29

---

## 9) Report Template (ENGINEER MUST OUTPUT)

Create: `REPORT_PROD_E2E_<YYYY-MM-DD>.md`

### 9.1 Header
- Environment: (staging/local/prod)
- Commit hash
- OpenRouter model(s) used
- Worker status verification method

### 9.2 Case A Results
- Project ID
- Cutoff date
- Personas count
- Evidence count
- Baseline run ID + outcome summary
- Universe Map screenshots + “expand + run” evidence
- Report export screenshot
- PASS/FAIL + reasons

### 9.3 Case B Results
- Project ID
- Cutoff date = 2022-12-31
- Evidence list (titles, timestamps)
- Baseline distribution (P10/P50/P90)
- Scenario branches run + deltas
- GT source + whether inside P10–P90
- Leakage test outcome
- PASS/FAIL + reasons

### 9.4 Fix Log (Closed Loop)
For each failure:
- Symptom
- Root cause
- Fix applied
- Re-test evidence (IDs/screenshots)
- Result

### 9.5 Final Summary
- What’s production-ready now
- What’s still risky
- Next 3 priorities

---

## 10) Execution Rules (Strict)

- Do not remove Goal Assistant or Blueprint again (regressions already happened before). fileciteturn15file5L33-L47
- Do not “fake pass” by hardcoding results.
- Do not proceed to Case B until Case A passes fully.
- Any new UI must be minimal and must *reduce* user effort (AI-first).
- Always preserve: on-demand, reversible, auditable constraints. fileciteturn15file13L57-L62

---

*End of playbook.*

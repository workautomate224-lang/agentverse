# Slice 1B Staging Test Report

**Date**: 2026-01-17
**Environment**: Staging (https://agentverse-web-staging-production.up.railway.app)
**Tester**: Claude Code

---

## Summary

| Test | Status | Notes |
|------|--------|-------|
| Test 1: Happy path with clarification | ✅ PASSED | Blueprint ready with correct provenance |
| Test 2: Skip path without clarification | ✅ PASSED | Blueprint ready without answers |
| Test 3: Refresh/navigation persistence | ❌ FAILED | State lost after page refresh |
| Test 4: Failure visibility regression | ✅ PASSED | Jobs fail visibly with clear status |

**Overall**: 3/4 tests passed. One blocker identified for state persistence.

---

## Test Details

### Test 1: Happy Path with Clarification ✅ PASSED

**Flow Tested:**
1. Enter goal: "Policy change impact on inflation sentiment"
2. Click "Analyze Goal" → Goal Analysis job starts
3. Goal Analysis completes with 6 clarifying questions
4. Answer all required questions (Q1-Q6)
5. Click "Generate Blueprint Preview"
6. Blueprint Build job completes at 100%
7. UI shows "BLUEPRINT READY" with profile

**Verification:**
- ✅ LLM Provenance: Provider=openrouter, Model=openai/gpt-5.2
- ✅ Cache: Bypassed
- ✅ Fallback: No (fallback_used=false)
- ✅ NEXT button enabled

**Evidence:**
- `docs/evidence/slice_1b_goal_analysis_provenance.png`
- `docs/evidence/slice_1b_blueprint_ready.png`

---

### Test 2: Skip Path without Clarification ✅ PASSED

**Flow Tested:**
1. Enter goal: "Brand perception shift after PR crisis"
2. Click "Skip & Generate Blueprint"
3. Blueprint Build job starts immediately (no questions shown)
4. Blueprint Build job completes at 100%
5. UI shows "BLUEPRINT READY" with profile

**Verification:**
- ✅ LLM Provenance: Provider=openrouter, Model=openai/gpt-5.2
- ✅ No clarifying questions displayed
- ✅ Job Name: "Blueprint Generation (Skip Clarify)"
- ✅ NEXT button enabled

**Evidence:**
- `docs/evidence/slice_1b_skip_clarify_success.png`
- `docs/evidence/slice_1b_job_center_both_flows.png`

---

### Test 3: Refresh/Navigation Persistence ❌ FAILED

**Flow Tested:**
1. Enter goal: "New product launch reception prediction"
2. Click "Analyze Goal" → Goal Analysis completes
3. Answer Q1 (time horizon): "3 months"
4. Answer Q2 (primary KPI): "Unit sales / revenue"
5. Answer Q3 (reporting cadence): "First quarter (0-90 days)"
6. **Refresh page**
7. ❌ State completely lost - empty page

**Expected Behavior:**
- Goal text should persist
- Analysis results should persist
- Answered questions should persist
- No re-running of goal_analysis

**Actual Behavior:**
- Goal text box is empty (0 characters)
- No "Goal Assistant" panel visible
- No analysis results
- No clarifying questions
- Complete state loss

**Root Cause:**
The `/dashboard/projects/new` page does not persist wizard state in browser storage (localStorage/sessionStorage) or URL state. The beforeunload dialog appeared, indicating the app knows about unsaved changes but doesn't restore them.

**Evidence:**
- `docs/evidence/slice_1b_persistence_fail.png` - Empty page after refresh

**Recommendation:**
Implement state persistence using:
1. `localStorage` or `sessionStorage` for wizard state
2. Or URL query params for state recovery
3. Or backend draft persistence (pil_job with draft status)

---

### Test 4: Failure Visibility Regression ✅ PASSED

**Flow Tested:**
Verified Job Center shows failed jobs with clear failure status.

**Verification (from Background Jobs tab):**
| Job Type | Stage at Failure | Progress |
|----------|------------------|----------|
| Goal Analysis | "Analyzing goal and domain" | 20% |
| Goal Analysis | "Generating blueprint preview" | 80% |
| Blueprint Build | "Generating input slots" | 30% |
| Blueprint Build | "Saving input slots" | 60% |

**Confirmation:**
- ✅ Jobs show "FAILED" status in red
- ✅ Stage where failure occurred is visible
- ✅ Progress percentage at failure is shown
- ✅ No "fake success" - failures are genuine failures
- ✅ Slice 1A guarantees maintained (strict_llm mode)

**Evidence:**
- `docs/evidence/slice_1b_failure_visibility.png` - Job Center showing failed jobs

---

## LLM Provenance Summary

All successful PIL jobs maintain Slice 1A guarantees:

| Field | Expected | Actual |
|-------|----------|--------|
| provider | openrouter | ✅ openrouter |
| model | openai/gpt-5.2 | ✅ openai/gpt-5.2 |
| fallback_used | false | ✅ false |
| fallback_attempts | 0 | ✅ 0 |

---

## Evidence Files

| File | Description |
|------|-------------|
| `docs/evidence/slice_1b_goal_analysis_provenance.png` | Goal Analysis with LLM Provenance |
| `docs/evidence/slice_1b_blueprint_ready.png` | Blueprint Ready (clarification flow) |
| `docs/evidence/slice_1b_skip_clarify_success.png` | Skip Clarify flow success |
| `docs/evidence/slice_1b_job_center_both_flows.png` | Job Center showing both successful flows |
| `docs/evidence/slice_1b_persistence_fail.png` | State lost after refresh (failure) |
| `docs/evidence/slice_1b_failure_visibility.png` | Job Center showing failed jobs |

---

## Recommendations

### Critical (Before Production Deploy)
1. **Fix state persistence** - Wizard state must survive page refresh

### Nice to Have
1. Add "Resume" functionality for interrupted wizard sessions
2. Consider auto-save draft to backend every N seconds

---

## Deploy Decision

| Criteria | Status |
|----------|--------|
| Happy path works | ✅ |
| Skip path works | ✅ |
| LLM provenance correct | ✅ |
| Failure visibility works | ✅ |
| State persistence | ❌ BLOCKER |

**Recommendation**: Fix state persistence before production deploy, or document as known limitation if acceptable for MVP.

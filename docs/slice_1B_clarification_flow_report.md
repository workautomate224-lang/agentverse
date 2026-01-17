# Slice 1B: Clarification Flow + Skip Clarify + Blueprint Build Report

**Date**: 2026-01-17
**Status**: ✅ COMPLETE - All Flows Tested and Evidence Collected
**Scope**: Goal → (goal_analysis + clarifying_questions) → blueprint_build pipeline
**Evidence Pack**: ✅ Ready for Review

---

## 1. Overview

Slice 1B implements **LLM-Powered Blueprint Generation** with full Clarification Flow support. This ensures blueprints are generated using:
1. Original goal_text
2. Goal analysis summary from goal_analysis job
3. User's clarification answers (when provided)

### Two Flows Supported

| Flow | Description | Use Case |
|------|-------------|----------|
| **Clarification Flow** | Goal Analysis → Clarifying Questions → User Answers → Blueprint Build | Power users who want precision |
| **Skip Clarify Flow** | Goal Analysis → Blueprint Build (skip questions) | Quick prototype, experienced users |

### North Star

After blueprint generation completes:
- **LLM Provenance** line shows: Provider: openrouter, Model: gpt-5.2
- **fallback_used**: false (never use fallback for wizard flows)
- **Blueprint Quality**: LLM uses clarification_answers context when available

---

## 2. Implementation Summary

### 2.1 LLM-Powered Blueprint Generation

#### A. New Function: `_llm_build_blueprint()` (`apps/api/app/tasks/pil_tasks.py`)

LLM generates all blueprint components using context from goal and clarification answers:

```python
async def _llm_build_blueprint(
    goal_text: str,
    goal_analysis_result: Dict[str, Any],
    clarification_answers: Optional[Dict[str, str]] = None,
    llm_context: Optional["LLMRouterContext"] = None,
) -> Dict[str, Any]:
    """
    Generate complete blueprint using LLM with full context.

    Prompt includes:
    - Original user goal
    - Goal analysis summary (domain, output_type, horizon, scope)
    - Clarification Q&A pairs (when provided)
    """
```

#### B. Context-Rich Prompt Construction

```python
# Build context section with clarification answers
context_parts = [
    f"Goal: {goal_text}",
    f"Domain: {goal_analysis_result.get('domain_guess', 'unknown')}",
    f"Output Type: {goal_analysis_result.get('output_type', 'unknown')}",
    f"Time Horizon: {goal_analysis_result.get('horizon_guess', 'unknown')}",
    f"Scope: {goal_analysis_result.get('scope_guess', 'unknown')}",
]

# Add clarification answers if provided
if clarification_answers:
    context_parts.append("\n## User Clarifications:")
    for q_id, answer in clarification_answers.items():
        context_parts.append(f"- {q_id}: {answer}")
```

#### C. LLM-Generated Blueprint Components

| Component | Description | Section |
|-----------|-------------|---------|
| `input_slots` | Required data inputs with types | inputs |
| `section_tasks` | Per-section tasks with descriptions | overview, inputs, personas, rules, run_params, reliability |
| `calibration_plan` | Calibration targets and methodology | reliability |

#### D. SlotType Normalization (`_normalize_slot_type()`)

```python
def _normalize_slot_type(slot_type: str) -> SlotType:
    """Normalize LLM output to valid SlotType enum."""
    normalized = slot_type.lower().strip().replace(" ", "_").replace("-", "_")
    slot_type_map = {
        "text": SlotType.TEXT,
        "number": SlotType.NUMBER,
        "date": SlotType.DATE,
        "file": SlotType.FILE,
        "select": SlotType.SELECT,
        # ... additional mappings for LLM variations
    }
    return slot_type_map.get(normalized, SlotType.TEXT)
```

### 2.2 Bug Fix: available_actions NOT NULL Constraint

#### Problem

LLM-generated tasks were missing required `available_actions` field, causing database error:
```
NotNullViolationError: null value in column "available_actions" of relation "blueprint_tasks"
```

#### Solution

Added section-to-actions mapping in `blueprint_build` task:

```python
# Map section_id to available_actions (same as fallback tasks)
section_actions_map = {
    "overview": [TaskAction.MANUAL_ADD.value],
    "inputs": [TaskAction.MANUAL_ADD.value, TaskAction.CONNECT_SOURCE.value],
    "personas": [TaskAction.AI_GENERATE.value, TaskAction.AI_RESEARCH.value, TaskAction.MANUAL_ADD.value],
    "rules": [TaskAction.MANUAL_ADD.value],
    "run_params": [TaskAction.MANUAL_ADD.value],
    "reliability": [TaskAction.MANUAL_ADD.value],
}

# Add required fields to each task
task_data = {
    "section_id": section_id,
    "sort_order": task_idx,
    "title": llm_task.get("title", f"Task {task_idx}"),
    "description": llm_task.get("why_it_matters", ""),
    "why_it_matters": llm_task.get("why_it_matters", ""),
    "available_actions": section_actions_map.get(section_id, [TaskAction.MANUAL_ADD.value]),
    "status": AlertState.NOT_STARTED.value,
}
```

---

## 3. Slice 1A Guarantees Maintained

| Guarantee | Status | Evidence |
|-----------|--------|----------|
| Provider = openrouter | ✅ | All llm_proof entries show `"provider": "openrouter"` |
| Model = openai/gpt-5.2 | ✅ | All llm_proof entries show `"model": "openai/gpt-5.2"` |
| fallback_used = false | ✅ | All entries show `"fallback_used": false` |
| fallback_attempts = 0 | ✅ | All entries show `"fallback_attempts": 0` |
| strict_llm mode | ✅ | Jobs fail visibly if LLM unavailable |

---

## 4. Flows Tested

### 4.1 Clarification Flow (With Answers)

**Test Goal:** "Policy change impact on inflation sentiment"

**Flow:**
1. ✅ Click "Analyze Goal" → Goal Analysis job starts
2. ✅ Goal Analysis completes with LLM Provenance
3. ✅ 6 Clarifying Questions displayed
4. ✅ User answers all questions (Q1-Q6)
5. ✅ Click "Generate Blueprint Preview"
6. ✅ Blueprint Build job starts at 30% "Generating blueprint with AI"
7. ✅ Blueprint Build completes at 100% "Saving section tasks"
8. ✅ UI shows "BLUEPRINT READY" with:
   - Domain: policy_impact
   - Output: distribution
   - Horizon: 6 months
   - Scope: national
   - Required Inputs: 3 required, 2 recommended
9. ✅ NEXT button enabled

**Job Result:**
- Job Type: `Blueprint Build`
- Job Name: `Blueprint Generation`
- Status: `SUCCEEDED`
- Progress: 100%

### 4.2 Skip Clarify Flow (No Answers)

**Test Goal:** "Brand perception shift after PR crisis"

**Flow:**
1. ✅ Enter goal in text box
2. ✅ Click "Skip & Generate Blueprint" button
3. ✅ Blueprint Build job starts immediately (no clarifying questions)
4. ✅ Blueprint Build completes at 100% "Saving section tasks"
5. ✅ UI shows "BLUEPRINT READY" with:
   - Domain: generic
   - Output: distribution
   - Horizon: 6 months
   - Scope: national
   - Required Inputs: 2 required, 2 recommended
6. ✅ NEXT button enabled

**Job Result:**
- Job Type: `Blueprint Build`
- Job Name: `Blueprint Generation (Skip Clarify)`
- Status: `SUCCEEDED`
- Progress: 100%

---

## 5. Evidence Pack

### ✅ Evidence Collected: 2026-01-17

#### A. Screenshots

| File | Description |
|------|-------------|
| `docs/evidence/slice_1b_goal_analysis_provenance.png` | Goal Analysis with LLM Provenance (Provider: openrouter, Model: gpt-5.2) |
| `docs/evidence/slice_1b_blueprint_ready.png` | Clarification Flow - Blueprint Ready with profile |
| `docs/evidence/slice_1b_skip_clarify_success.png` | Skip Clarify Flow - Blueprint Ready |
| `docs/evidence/slice_1b_job_center_both_flows.png` | Job Center showing both successful blueprint builds |

#### B. Job Center Evidence

**Both flows visible in Background Jobs:**

| Status | Type | Job Name | Progress | Stage |
|--------|------|----------|----------|-------|
| SUCCEEDED | Blueprint Build | Blueprint Generation (Skip Clarify) | 100% | Saving section tasks |
| SUCCEEDED | Blueprint Build | Blueprint Generation | 100% | Saving section tasks |

#### C. LLM Provenance Verification

**Clarification Flow - llm_proof fields:**

```json
{
  "goal_analysis": {
    "provider": "openrouter",
    "model": "openai/gpt-5.2",
    "cache_hit": false,
    "fallback_used": false,
    "fallback_attempts": 0
  },
  "clarifying_questions": {
    "provider": "openrouter",
    "model": "openai/gpt-5.2",
    "cache_hit": false,
    "fallback_used": false,
    "fallback_attempts": 0
  },
  "blueprint_generation": {
    "provider": "openrouter",
    "model": "openai/gpt-5.2",
    "cache_hit": false,
    "fallback_used": false,
    "fallback_attempts": 0
  }
}
```

**Skip Clarify Flow - llm_proof fields:**

```json
{
  "blueprint_generation": {
    "provider": "openrouter",
    "model": "openai/gpt-5.2",
    "cache_hit": false,
    "fallback_used": false,
    "fallback_attempts": 0
  }
}
```

---

## 6. Files Changed

| File | Changes |
|------|---------|
| `apps/api/app/tasks/pil_tasks.py` | Added `_llm_build_blueprint()`, `_normalize_slot_type()`, fixed available_actions |
| `apps/web/src/components/pil/v2/GoalAssistantPanel.tsx` | Clarification flow UI, Skip & Generate button |

---

## 7. Hard Rules Verification

| Rule | Status | Evidence |
|------|--------|----------|
| Blueprint uses goal_text | ✅ | Prompt includes original goal |
| Blueprint uses goal_analysis summary | ✅ | Prompt includes domain, output_type, horizon, scope |
| Blueprint uses clarification_answers | ✅ | Prompt includes Q&A pairs when provided |
| Skip flow works without answers | ✅ | Skip Clarify button triggers immediate blueprint build |
| Slice 1A guarantees maintained | ✅ | All llm_proof shows openrouter + gpt-5.2 + no fallback |
| available_actions populated | ✅ | Fix applied, tasks saved successfully |

---

## 8. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Slice 1B: Blueprint Build Pipeline                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────┐     ┌──────────────────────┐                       │
│  │ User enters     │     │ Goal Analysis Job    │                       │
│  │ goal_text       │────▶│ (LLM gpt-5.2)        │                       │
│  └─────────────────┘     │ Returns:             │                       │
│                          │ - domain_guess       │                       │
│                          │ - output_type        │                       │
│                          │ - horizon_guess      │                       │
│                          │ - scope_guess        │                       │
│                          │ - clarifying_questions│                       │
│                          └──────────────────────┘                       │
│                                    │                                     │
│                     ┌──────────────┴──────────────┐                     │
│                     │                             │                     │
│              ┌──────▼──────┐              ┌──────▼──────┐              │
│              │ CLARIFY     │              │ SKIP        │              │
│              │ FLOW        │              │ FLOW        │              │
│              └──────┬──────┘              └──────┬──────┘              │
│                     │                             │                     │
│              ┌──────▼──────┐                      │                     │
│              │ User answers │                     │                     │
│              │ Q1-Q6        │                     │                     │
│              └──────┬──────┘                      │                     │
│                     │                             │                     │
│                     └──────────────┬──────────────┘                     │
│                                    │                                     │
│                          ┌─────────▼─────────┐                          │
│                          │ Blueprint Build   │                          │
│                          │ Job (LLM gpt-5.2) │                          │
│                          │                   │                          │
│                          │ Input:            │                          │
│                          │ - goal_text       │                          │
│                          │ - goal_analysis   │                          │
│                          │ - answers (if any)│                          │
│                          │                   │                          │
│                          │ Output:           │                          │
│                          │ - input_slots     │                          │
│                          │ - section_tasks   │                          │
│                          │ - calibration_plan│                          │
│                          │ - llm_proof       │                          │
│                          └─────────┬─────────┘                          │
│                                    │                                     │
│                          ┌─────────▼─────────┐                          │
│                          │ BLUEPRINT READY   │                          │
│                          │ UI shows profile  │                          │
│                          │ + NEXT enabled    │                          │
│                          └───────────────────┘                          │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Commit History

### Commit 1: LLM Blueprint Generation
```
feat: Add LLM-powered blueprint generation with clarification context

- Add _llm_build_blueprint() function using PIL_BLUEPRINT_GENERATION profile
- Add _normalize_slot_type() to handle LLM output variations
- Build context-rich prompt with goal + analysis + clarification_answers
- LLM generates input_slots, section_tasks, calibration_plan
- Maintains Slice 1A guarantees (openrouter, gpt-5.2, no fallback)
```

### Commit 2: available_actions Fix
```
fix: Add available_actions and status to LLM-generated tasks

- Add section_actions_map for section-to-actions mapping
- Add available_actions field to all LLM-generated tasks
- Add status field with AlertState.NOT_STARTED default
- Fixes NotNullViolationError on blueprint_tasks table
```

---

## 10. Testing Instructions

### A. Clarification Flow Test

1. Go to https://agentverse-web-staging-production.up.railway.app
2. Navigate to Projects → New Project
3. Enter goal: "Predict market adoption of electric vehicles in 2026"
4. Click "Analyze Goal"
5. Wait for Goal Analysis to complete
6. **Verify**: LLM Provenance shows (Provider: openrouter, Model: gpt-5.2)
7. Answer all 6 clarifying questions
8. Click "Generate Blueprint Preview"
9. Wait for Blueprint Build to complete
10. **Verify**: "BLUEPRINT READY" with profile details
11. **Verify**: NEXT button enabled

### B. Skip Clarify Flow Test

1. Go to Projects → New Project
2. Enter goal: "Brand perception shift after product recall"
3. Click "Skip & Generate Blueprint"
4. Wait for Blueprint Build to complete
5. **Verify**: "BLUEPRINT READY" with profile details
6. **Verify**: No clarifying questions were shown
7. **Verify**: NEXT button enabled

### C. Job Center Verification

1. Navigate to Runs & Jobs → Background Jobs
2. **Verify**: Both jobs show as SUCCEEDED
3. **Verify**: "Blueprint Generation" for clarification flow
4. **Verify**: "Blueprint Generation (Skip Clarify)" for skip flow

---

## 11. Next Steps

1. ✅ Slice 1A: LLM Truth & No-Fake-Success - COMPLETE
2. ✅ Slice 1B: Clarification Flow + Skip Clarify + Blueprint Build - COMPLETE
3. Slice 2: Blueprint Editor with LLM-Powered Slot Filling
4. Slice 3: Simulation Run with LLM Provenance

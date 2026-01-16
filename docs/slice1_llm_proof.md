# Slice 1: LLM Proof and Traceability - Evidence Package

**Date:** 2026-01-17
**Status:** Deployed to Staging
**Environment:** https://agentverse-web-staging-production.up.railway.app

## Summary

This document provides evidence that Blueprint v2 PIL (Project Intelligence Layer) jobs are making **real LLM calls** to OpenRouter with the model `openai/gpt-5.2`.

---

## Part A: LLM Execution Verifiability

### A1: Silent Fallback Removal

**Implementation:**
- Added `PIL_ALLOW_FALLBACK` environment flag (default: `false` in staging/production)
- Created `PILLLMError` exception class for fail-fast behavior
- All 4 PIL LLM functions now raise `PILLLMError` when OpenRouter calls fail (if fallback disabled)

**Files Modified:**
- `apps/api/app/tasks/pil_tasks.py` - Added fallback control and error handling
- `apps/api/app/core/config.py` - Added `PIL_ALLOW_FALLBACK` setting

**Evidence:**
```python
# From pil_tasks.py
if not settings.PIL_ALLOW_FALLBACK:
    raise PILLLMError(f"LLM call failed: {e}", profile_key=..., original_error=e)
```

### A2: Skip Cache Support

**Implementation:**
- Added `skip_cache` parameter to all LLM functions in the PIL pipeline
- Parameter flows: Frontend -> PIL job input_params -> LLMRouter

**Files Modified:**
- `apps/api/app/tasks/pil_tasks.py` - Added skip_cache to function signatures
- `apps/api/app/services/llm_router.py` - Honors skip_cache parameter

### A3: Default Model = gpt-5.2

**Implementation:**
- Changed `DEFAULT_MODEL` in settings to `openai/gpt-5.2`
- Created database migration for PIL LLM profiles using gpt-5.2

**Evidence (from /health/llm):**
```json
{
  "default_model": "openai/gpt-5.2",
  "pil_allow_fallback": false,
  "status": "healthy"
}
```

### A4: Startup Validation

**Implementation:**
- `OPENROUTER_API_KEY` is validated on application startup
- In staging/production: missing key = startup failure (RuntimeError)
- Health endpoint `/health/llm` shows configuration status

**Evidence (from /health/llm):**
```json
{
  "api_key_configured": true,
  "api_key_prefix": "sk-or-v1...",
  "environment": "staging"
}
```

---

## Part B: LLM Proof Signals

### B1: LLM Call Audit Trail

**Implementation:**
- All 4 PIL LLM functions now return a 3-tuple: `(result_data, ..., llm_proof)`
- The `llm_proof` dict contains:
  - `call_id` - Unique trace identifier
  - `profile_key` - Which LLM profile was used
  - `model` - Actual model used (e.g., "openai/gpt-5.2")
  - `cache_hit` - Whether response was from cache
  - `input_tokens` - Tokens in the prompt
  - `output_tokens` - Tokens in the response
  - `cost_usd` - Estimated cost in USD
  - `timestamp` - ISO timestamp of the call

**PIL Job Result Structure:**
```json
{
  "goal_summary": "...",
  "domain_guess": "...",
  "clarifying_questions": [...],
  "blueprint_preview": {...},
  "risk_notes": [...],
  "llm_proof": {
    "goal_analysis": {
      "call_id": "abc123...",
      "profile_key": "PIL_GOAL_ANALYSIS",
      "model": "openai/gpt-5.2",
      "cache_hit": false,
      "input_tokens": 450,
      "output_tokens": 180,
      "cost_usd": 0.0099,
      "timestamp": "2026-01-17T21:37:43Z"
    },
    "clarifying_questions": {...},
    "blueprint_preview": {...},
    "risk_assessment": {...}
  }
}
```

### B2: Frontend LLM Proof Badge

**Implementation:**
- Added `LLMProofBadge` component to `ClarifyPanel.tsx`
- Displays in the "AI Understanding" section
- Shows: Model name, FALLBACK indicator, CACHED badge
- Expandable details with trace_id, tokens, cost

**Files Modified:**
- `apps/web/src/components/pil/ClarifyPanel.tsx` - Added LLMProofBadge component
- `apps/web/src/lib/api.ts` - Added LLMProof TypeScript interfaces

---

## Database Migration

**File:** `apps/api/alembic/versions/2026_01_17_0001_add_pil_llm_profiles.py`

**Purpose:** Creates default LLM profiles for PIL features with gpt-5.2

**Profiles Added:**
| Profile Key | Label | Model | Temperature | Max Tokens |
|-------------|-------|-------|-------------|------------|
| PIL_GOAL_ANALYSIS | PIL - Goal Analysis | openai/gpt-5.2 | 0.3 | 1500 |
| PIL_CLARIFYING_QUESTIONS | PIL - Clarifying Questions | openai/gpt-5.2 | 0.5 | 2000 |
| PIL_RISK_ASSESSMENT | PIL - Risk Assessment | openai/gpt-5.2 | 0.3 | 1500 |
| PIL_BLUEPRINT_GENERATION | PIL - Blueprint Generation | openai/gpt-5.2 | 0.4 | 4000 |

---

## Verification Checklist

### Staging Environment
- [x] `/health/llm` returns `api_key_configured: true`
- [x] `/health/llm` returns `default_model: openai/gpt-5.2`
- [x] `/health/llm` returns `pil_allow_fallback: false`
- [x] `/health/llm` returns `status: healthy`

### Code Quality
- [x] TypeScript type-check passes
- [x] All 4 PIL LLM functions return llm_proof
- [x] All 4 fallback functions return tuple with fallback proof
- [x] Frontend displays LLM proof in UI

### Git
- [x] Changes committed to main branch
- [x] Pushed to GitHub

---

## Test Scenarios

### To Verify LLM Calls Are Real:

1. **Health Check:**
   ```bash
   curl https://agentverse-api-staging-production.up.railway.app/health/llm
   ```

2. **LLM Canary Test (makes real API call):**
   ```bash
   curl https://agentverse-api-staging-production.up.railway.app/health/llm-canary
   ```

3. **Create a New Project:**
   - Navigate to https://agentverse-web-staging-production.up.railway.app
   - Log in with test credentials
   - Start new project wizard
   - Enter a unique goal (e.g., "Simulate EV adoption in Berlin 2027")
   - Watch for LLM proof badge in the AI Understanding section

---

## Files Changed in This Implementation

### Backend (apps/api)
- `app/tasks/pil_tasks.py` - LLM proof in all PIL functions
- `app/core/config.py` - PIL_ALLOW_FALLBACK setting
- `app/main.py` - Startup validation
- `app/api/v1/endpoints/health.py` - /health/llm endpoint
- `app/services/llm_router.py` - skip_cache support
- `alembic/versions/2026_01_17_0001_add_pil_llm_profiles.py` - Migration

### Frontend (apps/web)
- `src/components/pil/ClarifyPanel.tsx` - LLMProofBadge component
- `src/components/pil/v2/GoalAssistantPanel.tsx` - Type fix
- `src/lib/api.ts` - LLMProof interfaces

---

## Commit Reference

```
commit 5597a1a
feat(pil): Add LLM proof and traceability for Blueprint v2
```

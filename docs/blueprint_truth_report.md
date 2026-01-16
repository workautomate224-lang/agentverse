# Blueprint v2 Truth/Audit Report

**Report Date:** 2026-01-17
**Environment Tested:** Local Development + Staging
**Report Author:** Claude (Implementation Audit)

---

## Executive Summary

| Status | Finding |
|--------|---------|
| **VERDICT** | Blueprint v2 is **PARTIALLY REAL** with a critical disconnect |

**The UI shows a working wizard, but the backend PIL job system is NOT connected to the wizard flow.**

The Goal step calls a frontend-only API that returns AI results directly to React state. These results are **never persisted to the database**, so when users navigate to other pages, there is **no blueprint in the DB** for the GuidancePanel to display.

---

## Section 1: Environment + Flags (PROOF)

### Current environment tested
- **Local:** `http://localhost:3002` (web), `http://localhost:8000` (api)
- **Staging:** `https://agentverse-web-staging-production.up.railway.app`

### Feature Flag Configuration

**File:** `apps/web/src/lib/feature-flags.ts`
```typescript
export const FEATURE_FLAGS = {
  BLUEPRINT_V2_WIZARD: true, // Always enabled per blueprint_v3.md - no legacy path
} as const;
```

**Evidence:** Feature flag is **HARDCODED to `true`** - no env variable toggles it.

### OpenRouter API Key

**File:** `apps/web/.env.local`
```
OPENROUTER_API_KEY=sk-or-v1-1fbcd***[MASKED]
```

**Status:** Present and valid.

### Environment Summary

| Variable | Value | Status |
|----------|-------|--------|
| `BLUEPRINT_V2_WIZARD` | `true` (hardcoded) | Active |
| `OPENROUTER_API_KEY` | `sk-or-v1-***` | Present |
| `BACKEND_API_URL` | `http://localhost:8000` | Configured |
| `NEXT_PUBLIC_WS_URL` | Not set locally | OK (optional) |

---

## Section 2: Step 1 (Goal) – Network Proof

### What SHOULD happen (per architecture)
1. User submits goal text
2. Frontend calls `POST /api/v1/pil-jobs/` with `job_type: 'goal_analysis'`
3. Backend creates PIL job, dispatches Celery task
4. Task calls OpenRouter via LLMRouter
5. Result stored in `pil_artifacts` table
6. Blueprint created/updated in `blueprints` table

### What ACTUALLY happens

**File:** `apps/web/src/components/pil/v2/GoalAssistantPanel.tsx`

```typescript
// Lines 89-105: The component calls a FRONTEND API route, not the backend PIL system
const response = await fetch('/api/goal-analysis', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ goalText }),
});
const result = await response.json();
```

**File:** `apps/web/src/app/api/goal-analysis/route.ts`

```typescript
// Lines 8-11: Frontend route calls OpenRouter DIRECTLY
const OPENROUTER_API_KEY = process.env.OPENROUTER_API_KEY;
const OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions';
const MODEL = 'openai/gpt-4o-mini';  // NOTE: NOT gpt-5.2!

// Lines 50-70: Direct fetch to OpenRouter
const response = await fetch(OPENROUTER_URL, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${OPENROUTER_API_KEY}`,
    'HTTP-Referer': process.env.NEXTAUTH_URL || 'https://agentverse.io',
    'X-Title': 'AgentVerse Goal Analysis',
  },
  body: JSON.stringify({
    model: MODEL,
    messages: [...],
    temperature: 0.7,
    max_tokens: 2000,
    response_format: { type: 'json_object' },
  }),
});
```

### Network Evidence

| Expected Call | Actual Call | Status |
|---------------|-------------|--------|
| `POST /api/v1/pil-jobs/` | NOT MADE | MISSING |
| `POST /api/goal-analysis` | MADE | Frontend-only |
| OpenRouter call | MADE (via frontend) | Works |
| Blueprint DB write | NOT MADE | MISSING |

### Model Used

| Documented | Actual | Discrepancy |
|------------|--------|-------------|
| `openai/gpt-5.2` (premium) | `openai/gpt-4o-mini` | Different model |

---

## Section 3: Backend Proof – Job + OpenRouter Call

### Backend PIL Task System EXISTS and is COMPLETE

**File:** `apps/api/app/tasks/pil_tasks.py`

```python
# Lines 220-232: Celery task definition
@celery_app.task(bind=True, base=TenantAwareTask, max_retries=3)
def goal_analysis_task(self, job_id: str, context: dict):
    """
    Analyze user goal text and produce:
    - Goal summary
    - Domain classification
    - Clarifying questions
    - Blueprint preview
    - Risk notes
    """
    return _run_async(_goal_analysis_async(self, job_id, context))

# Lines 269-274: LLM call via LLMRouter
goal_summary, domain_guess = await _llm_analyze_goal(session, goal_text, llm_context)

# Lines 386-430: Actual LLM call
async def _llm_analyze_goal(...):
    router = LLMRouter(session)
    response = await router.complete(
        profile_key=LLMProfileKey.PIL_GOAL_ANALYSIS.value,
        messages=[...],
        context=context,
    )
```

### LLMRouter Configuration

**File:** `apps/api/app/services/llm_router.py`

```python
# Lines 386-401: Default profile when no DB profile exists
def _get_default_profile(self, profile_key: str) -> LLMProfile:
    return LLMProfile(
        model="openai/gpt-4o-mini",  # Default model
        temperature=0.3,
        max_tokens=2000,
        fallback_models=["anthropic/claude-3-haiku-20240307"],
    )
```

### OpenRouterService Configuration

**File:** `apps/api/app/services/openrouter.py`

```python
AVAILABLE_MODELS = {
    "premium": ModelConfig(
        model="openai/gpt-5.2",  # GPT-5.2 IS configured as premium
        ...
    ),
    "fast": ModelConfig(
        model="openai/gpt-4o-mini",
        ...
    ),
}
```

### Backend Status Summary

| Component | Status | Evidence |
|-----------|--------|----------|
| `goal_analysis_task` | Implemented | `pil_tasks.py:220-232` |
| `_llm_analyze_goal` | Implemented | `pil_tasks.py:386-454` |
| LLMRouter | Implemented | `llm_router.py:126-313` |
| OpenRouterService | Implemented | `openrouter.py` |
| PIL Job endpoint | Implemented | `apps/api/app/api/v1/pil_jobs.py` |

**VERDICT:** Backend is **FULLY IMPLEMENTED** but **NOT CALLED** by the wizard.

---

## Section 4: Persistence Proof – Blueprint linked to Project

### Database Schema

**Tables exist:**
- `blueprints` - Stores blueprint metadata, goal_text, domain_guess
- `blueprint_slots` - Stores data requirement slots
- `blueprint_tasks` - Stores section tasks
- `pil_jobs` - Stores background job tracking
- `pil_artifacts` - Stores job outputs

### What the Wizard SHOULD Do

```
GoalAssistantPanel.tsx
  → POST /api/v1/pil-jobs/ (job_type: 'goal_analysis')
  → Backend creates PILJob row
  → Celery task creates Blueprint row
  → Blueprint.id returned to frontend
  → Frontend stores blueprint_id in state
  → Next step uses blueprint_id
```

### What the Wizard ACTUALLY Does

```
GoalAssistantPanel.tsx
  → POST /api/goal-analysis (frontend route)
  → Route calls OpenRouter directly
  → Returns JSON to React state
  → NO DATABASE WRITE
  → Blueprint exists only in React state
  → Page navigation → state lost → no blueprint
```

### Evidence: Frontend Route Has No DB Writes

**File:** `apps/web/src/app/api/goal-analysis/route.ts`

```typescript
// Entire file has NO database calls
// Lines 1-120: Only OpenRouter HTTP call + JSON response
// No imports of: prisma, db, sql, database, repository
// No mentions of: blueprint, PILJob, artifact
```

### Persistence Status

| Data | Where Expected | Where Stored | Status |
|------|----------------|--------------|--------|
| Goal analysis result | `pil_artifacts` table | React state only | NOT PERSISTED |
| Domain classification | `blueprints.domain_guess` | React state only | NOT PERSISTED |
| Clarifying questions | `pil_artifacts` table | React state only | NOT PERSISTED |
| Blueprint draft | `blueprints` table | React state only | NOT PERSISTED |

---

## Section 5: Guidance Proof – Other Pages Consume Blueprint

### GuidancePanel v2 IS REAL

**File:** `apps/web/src/components/pil/v2/GuidancePanel.tsx`

```typescript
// Lines 67-73: Reads blueprint from API
const { data: blueprint, isLoading, error } = useActiveBlueprint(projectId);

// Filter tasks by section_id
const sectionTasks: BlueprintTask[] = blueprint?.tasks?.filter(
  (task) => task.section_id === section
) || [];
```

### What Pages Use GuidancePanel

| Page | Uses GuidancePanel | Section |
|------|-------------------|---------|
| `/p/[projectId]/data-personas` | Yes | `inputs` |
| `/p/[projectId]/rules` | Yes | `rules` |
| `/p/[projectId]/run-center` | Yes | `runs` |
| `/p/[projectId]/universe-map` | Yes | `universe` |
| `/p/[projectId]/event-lab` | Yes | `events` |
| `/p/[projectId]/reliability` | Yes | `reliability` |

### What Users See

When blueprint exists in DB:
```
┌─────────────────────────────────────────┐
│ Blueprint Guidance                       │
│ Data & Personas • 2/5 tasks             │
│ ┌─────────────────────────────────────┐ │
│ │ ○ Upload required data              │ │
│ │ ✓ Create agent population           │ │
│ │ ...                                 │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

When blueprint DOES NOT exist (current state):
```
┌─────────────────────────────────────────┐
│ Blueprint Guidance                       │
│ No blueprint tasks for Data & Personas   │
└─────────────────────────────────────────┘
```

---

## Section 6: Diagnosis – Why UI "Looks Ready" But Isn't

### Root Cause

**Two parallel code paths that don't connect:**

```
┌──────────────────────────────────────────────────────────────────┐
│  PATH A: Frontend-Only (Currently Used)                          │
│                                                                  │
│  GoalAssistantPanel.tsx                                          │
│        │                                                         │
│        ▼                                                         │
│  POST /api/goal-analysis (Next.js route)                         │
│        │                                                         │
│        ▼                                                         │
│  OpenRouter API (direct call)                                    │
│        │                                                         │
│        ▼                                                         │
│  JSON returned to React state                                    │
│        │                                                         │
│        ▼                                                         │
│  ❌ LOST on navigation (no DB)                                   │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  PATH B: Backend PIL System (NOT Connected)                      │
│                                                                  │
│  POST /api/v1/pil-jobs/                                          │
│        │                                                         │
│        ▼                                                         │
│  PILJob created in DB                                            │
│        │                                                         │
│        ▼                                                         │
│  Celery task dispatched                                          │
│        │                                                         │
│        ▼                                                         │
│  LLMRouter → OpenRouterService                                   │
│        │                                                         │
│        ▼                                                         │
│  Blueprint + Artifacts saved to DB                               │
│        │                                                         │
│        ▼                                                         │
│  ✅ GuidancePanel can read blueprint                             │
└──────────────────────────────────────────────────────────────────┘
```

### Why This Happened

1. **Incremental development:** Frontend route was created for quick iteration
2. **Missing integration:** Frontend route was never replaced with backend call
3. **No end-to-end test:** Unit tests passed, but no test verified DB persistence
4. **Confirmation bias:** "Goal step works!" (it does, visually) masked the persistence gap

### Symptoms

| Symptom | Cause |
|---------|-------|
| Goal step shows AI results | Frontend route works |
| Clarifying questions appear | Frontend route works |
| Blueprint preview renders | React state works |
| Other pages show "No tasks" | No blueprint in DB |
| GuidancePanel empty | `useActiveBlueprint` returns null |

---

## Section 7: Fix Plan (Smallest Safe Change)

### Option A: Wire Frontend to Backend PIL Jobs (RECOMMENDED)

**Change 1:** Modify `GoalAssistantPanel.tsx` to use PIL job hooks

**Current (broken):**
```typescript
const response = await fetch('/api/goal-analysis', {...});
const result = await response.json();
setAnalysisResult(result);
```

**Fixed:**
```typescript
import { useCreatePILJob, usePILJob } from '@/hooks/useApi';

// Create PIL job
const { mutateAsync: createJob } = useCreatePILJob();
const job = await createJob({
  job_type: 'goal_analysis',
  job_name: 'Goal Analysis',
  input_params: { goal_text: goalText },
});

// Poll for completion
const { data: completedJob } = usePILJob(job.id);
if (completedJob?.status === 'succeeded') {
  setAnalysisResult(completedJob.result);
  setBlueprintId(completedJob.blueprint_id); // Now persisted!
}
```

**Change 2:** Remove or deprecate `/api/goal-analysis` route

**Change 3:** Test end-to-end:
1. Submit goal in wizard
2. Navigate to `/p/[projectId]/data-personas`
3. Verify GuidancePanel shows tasks

### Option B: Add DB Write to Frontend Route (Quick fix, not recommended)

Add Prisma call to `/api/goal-analysis/route.ts` to create blueprint.
**Downsides:** Duplicates backend logic, no progress tracking, no retry support.

### Estimated Effort

| Option | Files Changed | Effort | Risk |
|--------|---------------|--------|------|
| A (Backend) | 2-3 files | 2-4 hours | Low |
| B (Frontend) | 1 file | 1-2 hours | Medium |

---

## Section 8: Verification Checklist (MUST)

### Pre-Fix Verification

- [ ] Confirm `pil_jobs` table has goal_analysis task type
- [ ] Confirm Celery worker is running
- [ ] Confirm Redis is connected
- [ ] Confirm OpenRouter API key is in backend env

### Post-Fix Verification

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | Open wizard at `/new-project` | Wizard loads | |
| 2 | Enter goal text, click "Analyze" | Loading spinner appears | |
| 3 | Check Network tab | `POST /api/v1/pil-jobs/` called | |
| 4 | Check `pil_jobs` table | Row created with status='running' | |
| 5 | Wait for completion | Analysis result shown | |
| 6 | Check `pil_jobs` table | Row status='succeeded' | |
| 7 | Check `blueprints` table | Row created with goal_summary | |
| 8 | Navigate to project page | GuidancePanel shows tasks | |
| 9 | Check `blueprint_tasks` table | Tasks exist for blueprint_id | |

### Staging Deployment Verification

```bash
# After fix is deployed to staging:

# 1. Create new project via wizard
curl -X POST https://agentverse-api-staging-production.up.railway.app/api/v1/pil-jobs/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"job_type": "goal_analysis", "job_name": "Test", "input_params": {"goal_text": "Test goal"}}'

# 2. Check job status
curl https://agentverse-api-staging-production.up.railway.app/api/v1/pil-jobs/{job_id}

# 3. Verify blueprint created
curl https://agentverse-api-staging-production.up.railway.app/api/v1/blueprints/?project_id={project_id}
```

---

## Appendix A: File References

| File | Purpose | Lines of Interest |
|------|---------|-------------------|
| `apps/web/src/lib/feature-flags.ts` | Feature toggle | Line 3 |
| `apps/web/src/app/api/goal-analysis/route.ts` | Frontend-only route | Lines 50-70 |
| `apps/web/src/components/pil/v2/GoalAssistantPanel.tsx` | Wizard step 1 | Lines 89-105 |
| `apps/api/app/tasks/pil_tasks.py` | Backend PIL tasks | Lines 220-380 |
| `apps/api/app/services/llm_router.py` | LLM routing | Lines 126-313 |
| `apps/web/src/components/pil/v2/GuidancePanel.tsx` | Blueprint guidance | Lines 67-73 |

---

## Appendix B: Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        BLUEPRINT V2 ARCHITECTURE                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐     ┌──────────────┐     ┌───────────────┐                │
│  │   Wizard    │────▶│  PIL Jobs    │────▶│  Celery       │                │
│  │   (React)   │     │  API         │     │  Worker       │                │
│  └─────────────┘     └──────────────┘     └───────────────┘                │
│         │                   │                     │                         │
│         │                   │                     ▼                         │
│         │                   │            ┌───────────────┐                  │
│         │                   │            │  LLMRouter    │                  │
│         │                   │            │               │                  │
│         │                   │            │  ┌─────────┐  │                  │
│         │                   │            │  │OpenRouter│  │                  │
│         │                   │            │  │ Service │  │                  │
│         │                   │            │  └─────────┘  │                  │
│         │                   │            └───────────────┘                  │
│         │                   │                     │                         │
│         │                   ▼                     ▼                         │
│         │            ┌──────────────────────────────────┐                   │
│         │            │          PostgreSQL              │                   │
│         │            │  ┌──────────┐ ┌──────────────┐   │                   │
│         │            │  │blueprints│ │pil_jobs      │   │                   │
│         │            │  └──────────┘ └──────────────┘   │                   │
│         │            │  ┌──────────┐ ┌──────────────┐   │                   │
│         │            │  │  slots   │ │pil_artifacts │   │                   │
│         │            │  └──────────┘ └──────────────┘   │                   │
│         │            │  ┌──────────┐                    │                   │
│         │            │  │  tasks   │                    │                   │
│         │            │  └──────────┘                    │                   │
│         │            └──────────────────────────────────┘                   │
│         │                           ▲                                       │
│         │                           │                                       │
│         ▼                           │                                       │
│  ┌─────────────┐            ┌──────────────┐                               │
│  │ Guidance    │───────────▶│ useActive    │                               │
│  │ Panel       │  (reads)   │ Blueprint()  │                               │
│  └─────────────┘            └──────────────┘                               │
│                                                                             │
│  CURRENT BUG: Wizard ─────▶ /api/goal-analysis (frontend-only)             │
│               Does NOT use PIL Jobs API, so DB is empty                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

**END OF REPORT**

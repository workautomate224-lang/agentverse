# LLM Pipeline Trace Report: Goal → Blueprint Generation

**Generated**: 2026-01-17
**Scope**: Tracing whether OpenRouter is actually called during Blueprint generation
**Status**: Investigation Complete

---

## 1. Verdict (One Sentence)

**OpenRouter IS wired up to be called**, but the actual execution depends on: (1) Celery worker being online, (2) OPENROUTER_API_KEY being set in the environment, and (3) no cache hit for the request—if any of these conditions fail, the system silently falls back to keyword-based heuristics that do NOT call OpenRouter.

---

## 2. End-to-End Pipeline (Step-by-Step)

### Step 1: Frontend - User Enters Goal Text
**File**: `apps/web/src/components/pil/v2/GoalAssistantPanel.tsx`
**Lines**: 180-195

```typescript
const job = await createJobMutation.mutateAsync({
  job_type: 'goal_analysis',
  job_name: 'Goal Analysis',
  input_params: {
    goal_text: goalText,
    skip_clarification: false,
  },
});
```

**What happens**: When user clicks "Analyze Goal", the frontend calls `POST /api/v1/pil-jobs/` with job_type `goal_analysis`.

---

### Step 2: API Endpoint - Job Creation
**File**: `apps/api/app/api/v1/endpoints/pil_jobs.py`
**Lines**: 122-154

```python
@router.post("/", response_model=PILJobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(job_in: PILJobCreate, ...):
    job = PILJob(
        tenant_id=current_user.id,
        job_type=job_in.job_type,
        status=PILJobStatus.QUEUED,
        input_params=job_in.input_params,
        ...
    )
    db.add(job)
    await db.commit()

    # THIS IS THE CRITICAL LINE - dispatches to Celery
    dispatch_pil_job.delay(str(job.id))

    return job
```

**What happens**: Job is saved to database with status `QUEUED`, then `dispatch_pil_job.delay()` queues a Celery task.

---

### Step 3: Celery Dispatcher - Routes to Correct Task
**File**: `apps/api/app/tasks/pil_tasks.py`
**Lines**: 1745-1796

```python
@celery_app.task(bind=True, base=TenantAwareTask)
def dispatch_pil_job(self, job_id: str):
    return _run_async(_dispatch_pil_job_async(self, job_id))

async def _dispatch_pil_job_async(task, job_id: str):
    # Route to appropriate task based on job_type
    if job.job_type == PILJobType.GOAL_ANALYSIS:
        goal_analysis_task.delay(job_id, context)
    elif job.job_type == PILJobType.BLUEPRINT_BUILD:
        blueprint_build_task.delay(job_id, context)
```

**What happens**: Based on `job_type`, the dispatcher calls the appropriate Celery task.

---

### Step 4: Goal Analysis Task - LLM Router Invocation
**File**: `apps/api/app/tasks/pil_tasks.py`
**Lines**: 220-407

```python
@celery_app.task(bind=True, base=TenantAwareTask, max_retries=3)
def goal_analysis_task(self, job_id: str, context: dict):
    return _run_async(_goal_analysis_async(self, job_id, context))

async def _goal_analysis_async(task, job_id: str, context: dict):
    # Create LLMRouter context
    llm_context = LLMRouterContext(
        tenant_id=str(job.tenant_id),
        project_id=str(job.project_id),
        phase="compilation",  # C5 tracking
    )

    # Stage 1: Parse goal and classify domain (20%)
    goal_summary, domain_guess = await _llm_analyze_goal(session, goal_text, llm_context)

    # Stage 2: Generate clarifying questions (50%)
    clarifying_questions = await _llm_generate_clarifying_questions(...)

    # Stage 3: Generate blueprint preview (80%)
    blueprint_preview = await _llm_generate_blueprint_preview(...)
```

**What happens**: The task creates an `LLMRouterContext` and calls LLM-powered functions.

---

### Step 5: LLM-Powered Functions - Router.complete()
**File**: `apps/api/app/tasks/pil_tasks.py`
**Lines**: 414-482

```python
async def _llm_analyze_goal(session, goal_text, context):
    router = LLMRouter(session)

    try:
        response = await router.complete(
            profile_key=LLMProfileKey.PIL_GOAL_ANALYSIS.value,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            context=context,
            temperature_override=0.3,
            max_tokens_override=500,
        )
        # Parse JSON response
        result = json.loads(response.content)
        ...
    except Exception:
        # FALLBACK - NO LLM CALL
        return _fallback_goal_analysis(goal_text)
```

**Critical Finding**: If `router.complete()` raises ANY exception, the code falls back to `_fallback_goal_analysis()` which uses keyword matching, NOT LLM.

---

### Step 6: LLM Router - Cache Check & OpenRouter Call
**File**: `apps/api/app/services/llm_router.py`
**Lines**: 126-313

```python
async def complete(self, profile_key, messages, context, ...):
    # 1. Look up profile
    profile = await self._get_profile(profile_key, context.tenant_id)
    if not profile:
        profile = self._get_default_profile(profile_key)  # Uses gpt-4o-mini

    # 2. Compute cache key
    cache_key = self._compute_cache_key(...)

    # 3. Check cache FIRST (if enabled)
    if profile.cache_enabled and not skip_cache:
        cached = await self._get_cached_response(cache_key)
        if cached:
            # CACHE HIT - NO OPENROUTER CALL
            return LLMRouterResponse(content=cached.response_content, ...)

    # 4. Make actual call via OpenRouter
    response, model_used, fallback_attempts, error = await self._complete_with_fallback(...)
```

**Critical Finding**: If cache is enabled (default=True) and request matches a previous one, OpenRouter is NOT called.

---

### Step 7: OpenRouter Service - HTTP Call
**File**: `apps/api/app/services/openrouter.py`
**Lines**: 121-262

```python
class OpenRouterService:
    def __init__(self, api_key=None, base_url=None):
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        if not self.api_key:
            raise ValueError("OpenRouter API key is required")  # FAILS HERE IF NO KEY

    async def complete(self, messages, model=None, ...):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",  # https://openrouter.ai/api/v1/chat/completions
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": "https://agentverse.ai",
                    "X-Title": "AgentVerse Simulation",
                },
                json=request_payload,
            )
```

**What happens**: Makes actual HTTP POST to OpenRouter API with Bearer token authentication.

---

## 3. Root-Cause Analysis: Why OpenRouter Credits Didn't Change

### Hypothesis 1: Celery Worker Not Running (MOST LIKELY)
**Evidence**: Jobs get created with status `QUEUED` but never transition to `RUNNING` or `SUCCEEDED`.

**Check**:
```bash
# Check if Celery worker is running
docker ps | grep celery
# Or check worker logs
docker logs agentverse-worker-staging 2>&1 | tail -50
```

**Impact**: Without a running worker, `dispatch_pil_job.delay()` queues the task but it's never executed. The frontend sees the job stuck at `QUEUED` forever.

---

### Hypothesis 2: Fallback Triggered Due to LLM Error
**Evidence**: In `pil_tasks.py`, every LLM function has a try/except that falls back to heuristics:

```python
# Line 480-482
except Exception:
    return _fallback_goal_analysis(goal_text)

# Line 584-586
except Exception:
    return _fallback_clarifying_questions(domain)
```

**Check**: Look at job error messages in database:
```sql
SELECT id, job_type, status, error_message, created_at
FROM pil_jobs
ORDER BY created_at DESC
LIMIT 10;
```

---

### Hypothesis 3: Cache Hit (Previous Request Cached)
**Evidence**: LLMRouter has caching enabled by default:

```python
# llm_router.py line 399
cache_enabled=True,
```

**Check**: Look at `llm_cache` table:
```sql
SELECT cache_key, profile_key, hit_count, created_at, last_hit_at
FROM llm_cache
ORDER BY last_hit_at DESC
LIMIT 10;
```

---

### Hypothesis 4: OPENROUTER_API_KEY Not Set
**Evidence**: `openrouter.py` line 133-134:
```python
if not self.api_key:
    raise ValueError("OpenRouter API key is required")
```

This error would be caught by the try/except in `pil_tasks.py` and trigger fallback.

**Check**:
```bash
# Railway staging
railway variables | grep OPENROUTER

# Local
cat apps/api/.env | grep OPENROUTER
```

---

### Hypothesis 5: LLM Profile Missing from Database
**Evidence**: `llm_router.py` line 386-401 falls back to default profile if none found:
```python
def _get_default_profile(self, profile_key: str) -> LLMProfile:
    return LLMProfile(
        model="openai/gpt-4o-mini",  # NOT gpt-5.2
        ...
    )
```

**Check**:
```sql
SELECT profile_key, model, is_active FROM llm_profiles
WHERE profile_key LIKE 'PIL_%';
```

---

## 4. Evidence Package

### 4.1 Code Path Evidence

| Step | File | Function | Line | What It Does |
|------|------|----------|------|--------------|
| 1 | `GoalAssistantPanel.tsx` | `handleAnalyze` | 180 | Calls POST `/api/v1/pil-jobs/` |
| 2 | `pil_jobs.py` | `create_job` | 152 | Calls `dispatch_pil_job.delay()` |
| 3 | `pil_tasks.py` | `dispatch_pil_job` | 1746 | Routes to `goal_analysis_task` |
| 4 | `pil_tasks.py` | `_goal_analysis_async` | 271 | Calls `_llm_analyze_goal()` |
| 5 | `pil_tasks.py` | `_llm_analyze_goal` | 451 | Calls `router.complete()` |
| 6 | `llm_router.py` | `complete` | 221 | Calls `_complete_with_fallback()` |
| 7 | `llm_router.py` | `_complete_with_fallback` | 577 | Calls `_openrouter.complete()` |
| 8 | `openrouter.py` | `complete` | 197 | HTTP POST to OpenRouter API |

### 4.2 Fallback Functions (NO LLM CALLS)

| Function | File | Line | Description |
|----------|------|------|-------------|
| `_fallback_goal_analysis` | `pil_tasks.py` | 485-508 | Keyword-based domain classification |
| `_fallback_clarifying_questions` | `pil_tasks.py` | 589-634 | Static questions based on domain |
| `_fallback_blueprint_preview` | `pil_tasks.py` | 707-731 | Static slot/task lists |
| `_fallback_risk_assessment` | `pil_tasks.py` | 799-816 | Keyword-based risk detection |

### 4.3 Default Model Configuration

```python
# openrouter.py line 89-95
"premium": ModelConfig(
    model="openai/gpt-5.2",
    cost_per_1k_input_tokens=0.005,
    cost_per_1k_output_tokens=0.015,
)

# llm_router.py line 388-392 (default profile)
model="openai/gpt-4o-mini",  # NOT gpt-5.2!
```

**Finding**: The default profile uses `gpt-4o-mini`, not `gpt-5.2`. To use GPT-5.2, there must be an explicit LLM profile in the database with `model="openai/gpt-5.2"`.

---

## 5. Repro Checklist

### To Verify OpenRouter IS Being Called:

1. **Check Celery Worker Status**
   ```bash
   docker ps | grep worker
   # Should show agentverse-worker running
   ```

2. **Check LLM Calls Table**
   ```sql
   SELECT id, profile_key, model_used, status, cost_usd, created_at
   FROM llm_calls
   ORDER BY created_at DESC
   LIMIT 20;
   ```
   - If rows exist with `status='success'` and `cost_usd > 0`, OpenRouter was called
   - If rows have `status='cached'`, response was from cache (no OpenRouter call)
   - If NO rows exist, Celery worker isn't processing or LLM calls are failing silently

3. **Check PIL Jobs Status**
   ```sql
   SELECT id, job_type, status, error_message, created_at, completed_at
   FROM pil_jobs
   ORDER BY created_at DESC
   LIMIT 10;
   ```
   - `QUEUED` = Celery worker not picking up
   - `RUNNING` = In progress
   - `SUCCEEDED` = Completed (check `result` column for output)
   - `FAILED` = Error occurred (check `error_message`)

4. **Check Cache Hits**
   ```sql
   SELECT cache_key, profile_key, hit_count, last_hit_at
   FROM llm_cache
   WHERE profile_key LIKE 'PIL_%'
   ORDER BY last_hit_at DESC;
   ```

5. **Check OpenRouter Dashboard**
   - Visit: https://openrouter.ai/activity
   - Filter by date range of your tests
   - Should show API calls if they went through

6. **Force Fresh LLM Call (Skip Cache)**
   Modify frontend to pass `skip_cache: true`:
   ```typescript
   const job = await createJobMutation.mutateAsync({
     job_type: 'goal_analysis',
     input_params: {
       goal_text: goalText + ' [test-' + Date.now() + ']',  // Unique text
     },
   });
   ```

---

## 6. Summary Table

| Question | Answer |
|----------|--------|
| Is OpenRouter wired up? | **YES** - Code path exists from frontend to OpenRouter HTTP call |
| Is OpenRouter being called? | **DEPENDS** - On worker status, API key, cache, and no errors |
| Default model used? | `openai/gpt-4o-mini` (NOT gpt-5.2) |
| Are there fallbacks? | **YES** - 4 fallback functions use keyword heuristics, no LLM |
| Is caching enabled? | **YES** - By default, responses are cached |
| Where are calls logged? | `llm_calls` table in database |

---

## 7. Recommended Diagnostic Commands

```bash
# 1. Check if Celery worker is running (Railway)
railway logs -s agentverse-worker-staging --tail 100

# 2. Check PIL jobs in database
docker exec -it agentverse-postgres psql -U postgres -d agentverse -c \
  "SELECT id, job_type, status, error_message FROM pil_jobs ORDER BY created_at DESC LIMIT 5;"

# 3. Check LLM calls in database
docker exec -it agentverse-postgres psql -U postgres -d agentverse -c \
  "SELECT profile_key, model_used, status, cost_usd, created_at FROM llm_calls ORDER BY created_at DESC LIMIT 5;"

# 4. Check if OPENROUTER_API_KEY is set
railway variables -s agentverse-api-staging | grep -i openrouter

# 5. Check cache hits
docker exec -it agentverse-postgres psql -U postgres -d agentverse -c \
  "SELECT profile_key, hit_count, last_hit_at FROM llm_cache ORDER BY last_hit_at DESC LIMIT 5;"
```

---

**Report Complete**. The pipeline is correctly wired to call OpenRouter, but multiple conditions (worker status, API key, cache, error handling) can prevent actual calls.

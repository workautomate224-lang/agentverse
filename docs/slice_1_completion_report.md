# VERTICAL SLICE #1 - Completion Report

## Overview

**Feature:** Create Project Step 1 (Goal) - Background Job Integration
**Status:** Implementation Complete
**Date:** 2026-01-16

---

## 1. What Was Implemented

### 1.1 GoalAssistantPanel Job Integration

**File:** `apps/web/src/components/pil/v2/GoalAssistantPanel.tsx`

- Replaced direct API fetch calls with PIL background job system
- Added job ID state tracking for both goal analysis and blueprint generation
- Implemented `useCreatePILJob`, `usePILJob`, `useCancelPILJob`, `useRetryPILJob` hooks
- Added job completion effects that extract results from `job.result`
- Created `JobStatusDisplay` sub-component showing:
  - **queued** (amber) - Job waiting in queue
  - **running** (cyan with animation) - Job in progress
  - **succeeded** (green) - Job completed successfully
  - **failed** (red) - Job failed with retry option
  - **cancelled** (gray) - Job was cancelled
- Added Cancel and Retry button functionality

### 1.2 localStorage Persistence for Resume

**PersistedWizardState** interface extended with:
```typescript
interface PersistedWizardState {
  goalText: string;
  stage: Stage;
  goalAnalysisJobId: string | null;  // NEW
  blueprintJobId: string | null;      // NEW
  analysisResult: GoalAnalysisResult | null;
  answers: Record<string, string | string[]>;
  blueprintDraft: BlueprintDraft | null;
  savedAt: string;
}
```

- Job IDs are persisted to localStorage
- On page reload or navigation back, job IDs are restored
- `usePILJob` hook auto-polls active jobs for status updates
- Completed job results are automatically extracted and displayed

### 1.3 Global Active Jobs Banner

**File:** `apps/web/src/app/dashboard/layout.tsx`

The dashboard layout already includes an `ActiveJobsBanner` component (line 181) WITHOUT a projectId filter, which means it shows ALL active jobs globally - including jobs created in Step 1 before a project exists.

### 1.4 Next Button Gating

**File:** `apps/web/src/app/dashboard/projects/new/page.tsx`

Next button is already gated via `isStepValid('goal')` (line 367):
```typescript
case 'goal':
  return formData.goal.trim().length >= 10 && blueprintDraft !== null;
```

The Next button is disabled when `!isStepValid(currentStep)` (line 1245), ensuring users cannot proceed without a Blueprint.

### 1.5 Type Fixes

**File:** `apps/web/src/lib/api.ts`

- Fixed field name mismatch: `output_summary` -> `result` to match backend schema
- Updated both `PILJob` and `PILJobUpdate` interfaces

---

## 2. Backend Infrastructure (Pre-existing)

The following backend components were already in place:

### 2.1 PIL Job API Routes
**File:** `apps/api/app/api/v1/endpoints/pil_jobs.py`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/pil-jobs/` | GET | List jobs with filters |
| `/api/v1/pil-jobs/active` | GET | List active (queued/running) jobs |
| `/api/v1/pil-jobs/{job_id}` | GET | Get specific job |
| `/api/v1/pil-jobs/` | POST | Create new job |
| `/api/v1/pil-jobs/{job_id}/cancel` | POST | Cancel job |
| `/api/v1/pil-jobs/{job_id}/retry` | POST | Retry failed job |

### 2.2 Celery Tasks
**File:** `apps/api/app/tasks/pil_tasks.py`

- `dispatch_pil_job` - Main entry point routing by job_type
- `goal_analysis_task` - Handles `goal_analysis` jobs
- `blueprint_build_task` - Handles `blueprint_build` jobs
- Progress reporting via `update_job_progress()`
- Artifact creation for results

### 2.3 Job Types Supported
**File:** `apps/api/app/models/pil_job.py`

```python
class PILJobType(str, Enum):
    GOAL_ANALYSIS = "goal_analysis"
    BLUEPRINT_BUILD = "blueprint_build"
    # ... other types
```

---

## 3. User Flow

### 3.1 Happy Path
1. User enters goal text (>= 10 characters)
2. GoalAssistantPanel appears
3. User clicks "Analyze Goal"
4. Job created via `/api/v1/pil-jobs/` (POST)
5. Job appears in:
   - Inline progress in Step 1 (GoalAssistantPanel)
   - Global ActiveJobsBanner at top of dashboard
6. UI polls job status every 2 seconds via `usePILJob` hook
7. Job completes -> Clarifying questions displayed (>= 3 questions)
8. User answers questions
9. User clicks "Generate Blueprint"
10. Blueprint job created and processed
11. Blueprint Preview displayed
12. Next button enabled

### 3.2 Resume Behavior
- **Navigate away/back:** Job IDs restored from localStorage, status checked
- **Browser refresh:** Same as above - state fully recovers
- **Job still running:** UI shows current progress, continues polling
- **Job completed:** Results extracted and displayed immediately

### 3.3 Error Handling
- **Job failed:** Error message displayed with "Retry" button
- **Job cancelled:** Status shown, user can start new analysis
- **Network error:** Error toast shown, retry available

---

## 4. Evidence Checklist (To Be Provided)

### A. Screen Recording (30-90 seconds)
[ ] Video showing full happy path from goal entry to blueprint preview

### B. Chrome Console
[ ] Screenshot showing 0 errors at end of recording

### C. Chrome Network Tab
[ ] Screenshot showing:
- Job enqueue request (POST `/api/v1/pil-jobs/`)
- Job status polling (GET `/api/v1/pil-jobs/{id}`)
- Active jobs list (GET `/api/v1/pil-jobs/active`)

### D. Resume Proof
[ ] Screenshot/recording showing:
- Start analysis, navigate away before completion
- Return to page, job resumes/completes
- OR: Browser refresh during job, state recovered

---

## 5. Files Changed

| File | Changes |
|------|---------|
| `apps/web/src/components/pil/v2/GoalAssistantPanel.tsx` | Added job hooks, persistence, JobStatusDisplay |
| `apps/web/src/lib/api.ts` | Fixed `output_summary` -> `result` field name |

---

## 6. Verification Commands

```bash
# Type check (should pass with 0 errors)
cd apps/web && pnpm type-check

# Backend API running
curl http://localhost:8000/api/v1/pil-jobs/active

# Frontend running
pnpm dev
```

---

## 7. Known Limitations

1. **No Project ID:** Jobs in Step 1 don't have a project_id (project doesn't exist yet). This is by design - jobs are tenant-scoped.

2. **Celery Worker Required:** Backend Celery worker must be running for jobs to process. In development, run:
   ```bash
   cd apps/api && celery -A app.tasks worker --loglevel=info
   ```

3. **LLM Fallback:** If OpenRouter API key is not configured, goal analysis uses fallback mock generation.

---

## 8. Stop Rule Compliance

Per the task specification:
> "Once Slice #1 is green-lit, stop. Do not start Slice #2 or any other features."

**No additional features were implemented beyond Slice #1 scope.**

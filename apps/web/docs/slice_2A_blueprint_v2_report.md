# Slice 2A: Blueprint v2 Data Contract + Final Blueprint Build Pipeline

**Status:** Complete
**Date:** 2026-01-18
**Reference:** blueprint_v2.md §2.1.1

---

## Overview

This slice implements the Blueprint v2 structured data contract and the "final_blueprint_build" PIL job pipeline. The system generates a comprehensive, AI-powered blueprint from Q/A session data using OpenRouter's `openai/gpt-5.2` model.

### Key Features

- **Structured Blueprint v2 Schema**: Intent, prediction target, horizon, output format, evaluation plan, required inputs
- **PIL Job Pipeline**: Proper job state machine (queued → running → succeeded/failed)
- **No Silent Fallback**: Strict validation with job failure on invalid output
- **LLM Provenance**: Full audit trail with model verification
- **Real-time Progress UI**: Polling-based status updates with stage indicators

---

## Files Modified/Created

### Backend (apps/api/)

| File | Action | Description |
|------|--------|-------------|
| `app/models/blueprint.py` | Modified | Added `BlueprintV2` SQLAlchemy model with all schema fields |
| `app/schemas/blueprint.py` | Modified | Added Pydantic schemas: `BlueprintV2Intent`, `BlueprintV2PredictionTarget`, `BlueprintV2Horizon`, `BlueprintV2OutputFormat`, `BlueprintV2EvaluationPlan`, `BlueprintV2RequiredInput`, `BlueprintV2Provenance`, `BlueprintV2Response`, `BlueprintV2CreateRequest` |
| `app/models/pil_job.py` | Modified | Added `FINAL_BLUEPRINT_BUILD` to `PILJobType` enum |
| `app/core/llm.py` | Modified | Added `PIL_FINAL_BLUEPRINT_BUILD` to `LLMProfileKey` enum |
| `app/tasks/pil_tasks.py` | Modified | Added `final_blueprint_build_task` Celery task with OpenRouter integration |
| `app/api/v1/endpoints/blueprints.py` | Modified | Added 4 Blueprint v2 API endpoints |

### Frontend (apps/web/)

| File | Action | Description |
|------|--------|-------------|
| `src/lib/api.ts` | Modified | Added Blueprint v2 TypeScript interfaces and API methods |
| `src/hooks/useApi.ts` | Modified | Added React Query hooks with polling support |
| `src/components/pil/v2/BlueprintBuildingState.tsx` | Created | Progress UI with stage indicators |
| `src/components/pil/v2/BlueprintV2Preview.tsx` | Created | Read-only blueprint display |
| `src/components/pil/v2/index.ts` | Modified | Exported new components |
| `src/components/ui/badge.tsx` | Created | Badge component for Blueprint v2 preview |
| `src/components/ui/card.tsx` | Created | Card component for Blueprint v2 sections |
| `src/app/api/health/route.ts` | Modified | Added `dynamic = 'force-dynamic'` to fix build timeout |

---

## API Endpoints

### POST `/api/v1/blueprints/v2/build`

Triggers a Blueprint v2 build job.

**Request Body:**
```json
{
  "project_id": "uuid",
  "force_rebuild": false
}
```

**Response:**
```json
{
  "job_id": "uuid",
  "status": "queued",
  "message": "Blueprint v2 build job created"
}
```

### GET `/api/v1/blueprints/v2/{blueprint_id}`

Retrieves a Blueprint v2 by its ID.

**Response:** `BlueprintV2Response`

### GET `/api/v1/blueprints/v2/project/{project_id}`

Retrieves the latest Blueprint v2 for a project.

**Response:** `BlueprintV2Response`

### GET `/api/v1/blueprints/v2/job/{job_id}/status`

Gets the status of a Blueprint v2 build job.

**Response:**
```json
{
  "job_id": "uuid",
  "status": "running|succeeded|failed|queued",
  "progress": 50,
  "stage": "building_blueprint",
  "blueprint_id": "uuid|null",
  "error": "string|null",
  "error_code": "string|null"
}
```

---

## Blueprint v2 Schema

```typescript
interface BlueprintV2Response {
  id: string;
  project_id: string;
  version: number;

  // Core sections
  intent: BlueprintV2Intent;
  prediction_target: BlueprintV2PredictionTarget;
  horizon: BlueprintV2Horizon;
  output_format: BlueprintV2OutputFormat;
  evaluation_plan: BlueprintV2EvaluationPlan;
  required_inputs: BlueprintV2RequiredInput[];

  // Metadata
  provenance: BlueprintV2Provenance;
  created_at: string;
  updated_at: string;
}
```

### Intent
```typescript
interface BlueprintV2Intent {
  business_question: string;
  decision_context: string;
  success_criteria: string[];
}
```

### Prediction Target
```typescript
interface BlueprintV2PredictionTarget {
  primary_metric: string;
  metric_definition: string;
  target_population: string;
  segmentation?: string[];
}
```

### Horizon
```typescript
interface BlueprintV2Horizon {
  prediction_window: string;
  data_freshness_requirement: string;
  update_frequency: string;
}
```

### Output Format
```typescript
interface BlueprintV2OutputFormat {
  format_type: string;
  granularity: string;
  confidence_intervals: boolean;
  explanation_depth: string;
}
```

### Evaluation Plan
```typescript
interface BlueprintV2EvaluationPlan {
  validation_approach: string;
  backtesting_period?: string;
  accuracy_thresholds?: Record<string, number | string>;
  comparison_benchmarks?: string[];
}
```

### Required Input
```typescript
interface BlueprintV2RequiredInput {
  input_name: string;
  input_type: string;
  description: string;
  required: boolean;
  source_suggestion?: string;
}
```

### Provenance
```typescript
interface BlueprintV2Provenance {
  model: string;
  provider: string;
  generated_at: string;
  prompt_version?: string;
  token_usage?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}
```

---

## Celery Task Implementation

### Task: `final_blueprint_build_task`

**Location:** `apps/api/app/tasks/pil_tasks.py`

**Flow:**
1. Load project and Q/A session data
2. Build structured prompt with all Q/A responses
3. Call OpenRouter API (`openai/gpt-5.2`)
4. Validate JSON response structure
5. Store Blueprint v2 with provenance
6. Update job status (succeeded/failed)

**Key Features:**
- Uses `TenantAwareTask` base class
- Async execution via `_run_async()` wrapper
- Progress updates at each stage (0%, 25%, 50%, 75%, 100%)
- Strict JSON validation - rejects malformed output
- LLM provenance verification via `build_llm_proof_from_response()`

**Error Handling:**
- `PILLLMError`: LLM API failures
- `PILProvenanceError`: Model verification failures
- `ValidationError`: Invalid JSON structure
- All errors result in job status = `failed` with error details

---

## React Query Hooks

### `useTriggerBlueprintV2Build`

Mutation hook to trigger a Blueprint v2 build.

```typescript
const { mutate, isPending } = useTriggerBlueprintV2Build();

mutate({ project_id: 'uuid' }, {
  onSuccess: (data) => {
    console.log('Job started:', data.job_id);
  }
});
```

### `useBlueprintV2`

Query hook to fetch a Blueprint v2 by ID.

```typescript
const { data, isLoading } = useBlueprintV2(blueprintId);
```

### `useBlueprintV2ByProject`

Query hook to fetch the latest Blueprint v2 for a project.

```typescript
const { data, isLoading } = useBlueprintV2ByProject(projectId);
```

### `useBlueprintV2JobStatus`

Query hook with automatic polling (2 second interval).

```typescript
const { data: jobStatus } = useBlueprintV2JobStatus(jobId, {
  enabled: !!jobId,
});

// Automatically stops polling when job completes
// (status === 'succeeded' || status === 'failed')
```

---

## UI Components

### `BlueprintBuildingState`

Displays the "Generating Blueprint..." progress state.

**Props:**
```typescript
interface BlueprintBuildingStateProps {
  jobId: string;
  onComplete?: (blueprintId: string) => void;
  onError?: (error: string) => void;
  className?: string;
}
```

**Features:**
- Progress bar with percentage
- Stage indicators (4 stages):
  - Gathering Context
  - Analyzing Intent
  - Building Blueprint
  - Validating Structure
- Success/failure states with animations
- Automatic polling via `useBlueprintV2JobStatus`

**Usage:**
```tsx
<BlueprintBuildingState
  jobId={jobId}
  onComplete={(blueprintId) => {
    // Navigate to preview
  }}
  onError={(error) => {
    toast.error(error);
  }}
/>
```

### `BlueprintV2Preview`

Read-only display of a Blueprint v2.

**Props:**
```typescript
interface BlueprintV2PreviewProps {
  projectId?: string;
  blueprintId?: string;
  data?: BlueprintV2Response;
  className?: string;
}
```

**Features:**
- Fetches data automatically if not provided
- Displays all 6 sections with icons
- Shows provenance badge (model + date)
- Loading and error states
- Responsive grid layout

**Usage:**
```tsx
// Fetch by project ID
<BlueprintV2Preview projectId={projectId} />

// Fetch by blueprint ID
<BlueprintV2Preview blueprintId={blueprintId} />

// Pre-loaded data
<BlueprintV2Preview data={blueprintData} />
```

---

## Evidence of Implementation

### 1. PIL Job Type Added

```python
# apps/api/app/models/pil_job.py
class PILJobType(str, Enum):
    # ... existing types ...
    FINAL_BLUEPRINT_BUILD = "final_blueprint_build"
```

### 2. LLM Profile Key Added

```python
# apps/api/app/core/llm.py
class LLMProfileKey(str, Enum):
    # ... existing keys ...
    PIL_FINAL_BLUEPRINT_BUILD = "pil_final_blueprint_build"
```

### 3. Job Dispatch Routing

```python
# apps/api/app/tasks/pil_tasks.py
elif job.job_type == PILJobType.FINAL_BLUEPRINT_BUILD:
    await final_blueprint_build_task.apply_async(
        args=[str(job.id)],
        queue="pil_jobs"
    )
```

### 4. API Endpoints Registered

All endpoints registered under `/api/v1/blueprints/v2/` prefix with proper authentication and authorization.

### 5. Frontend Types Match Backend

TypeScript interfaces in `api.ts` exactly match Pydantic schemas in `blueprint.py`.

### 6. Polling Mechanism

```typescript
// apps/web/src/hooks/useApi.ts
refetchInterval: (query) => {
  const data = query.state.data;
  if (data?.status === 'succeeded' || data?.status === 'failed') {
    return false; // Stop polling
  }
  return 2000; // Poll every 2 seconds
}
```

---

## Testing Checklist

- [ ] Trigger Blueprint v2 build via API
- [ ] Verify job appears in `pil_jobs` table with status `queued`
- [ ] Verify Celery worker picks up job and transitions to `running`
- [ ] Verify progress updates (0% → 25% → 50% → 75% → 100%)
- [ ] Verify Blueprint v2 record created on success
- [ ] Verify provenance includes model and token usage
- [ ] Verify job status endpoint returns correct data
- [ ] Verify frontend polling stops on completion
- [ ] Verify `BlueprintBuildingState` shows progress
- [ ] Verify `BlueprintV2Preview` renders all sections
- [ ] Verify error handling on LLM failure
- [ ] Verify validation error on malformed JSON

---

## Configuration

### LLM Model

```python
PIL_EXPECTED_MODELS = {
    LLMProfileKey.PIL_FINAL_BLUEPRINT_BUILD: "openai/gpt-5.2"
}
```

### Cache Bypass

In staging/dev environments, cache bypass is enabled to ensure fresh LLM responses.

### Queue

All Blueprint v2 jobs are dispatched to the `pil_jobs` Celery queue.

---

## Future Enhancements

1. **Blueprint v2 Edit Mode**: Allow manual adjustments to AI-generated sections
2. **Version History**: Track and compare blueprint versions
3. **Export**: PDF/JSON export of Blueprint v2
4. **Validation Rules**: Custom business rules for blueprint validation
5. **Templates**: Pre-built blueprint templates for common use cases

---

## Related Documentation

- `docs/pil/pil_arch.md` - PIL Architecture Overview
- `docs/blueprint_v2.md` - Blueprint v2 Specification
- `docs/slice_2-0_hotfix_report.md` - Previous Slice Report

# Runs API

**Tag:** `Simulation Runs`
**Base Path:** `/api/v1/runs`

Runs are executions of the simulation engine that produce outcomes, telemetry, and nodes.

---

## Run Lifecycle

```
queued → running → succeeded/failed/cancelled
```

| Status | Description |
|--------|-------------|
| `queued` | Run is waiting in the job queue |
| `running` | Simulation is actively executing |
| `succeeded` | Run completed successfully |
| `failed` | Run encountered an error |
| `cancelled` | Run was manually cancelled |

---

## Data Model

### Run

```json
{
  "id": "uuid",
  "project_id": "uuid",
  "tenant_id": "uuid",
  "name": "Baseline Simulation",
  "mode": "society",
  "status": "succeeded",
  "config": {
    "engine_version": "1.0.0",
    "ruleset_version": "1.0.0",
    "dataset_version": "1.0.0",
    "schema_version": "1.0.0",
    "seed": 42,
    "horizon_ticks": 100,
    "scheduler": {
      "partition_by": "region",
      "sample_rate": 1.0
    },
    "scenario_patch": null
  },
  "progress": {
    "current_tick": 100,
    "total_ticks": 100,
    "agents_processed": 10000,
    "percent_complete": 100
  },
  "outputs": {
    "node_id": "uuid",
    "telemetry_ref": "s3://bucket/telemetry/uuid.parquet",
    "results_ref": "s3://bucket/results/uuid.json",
    "snapshot_refs": ["s3://bucket/snapshots/tick-50.json"]
  },
  "timing": {
    "queued_at": "2026-01-09T12:00:00Z",
    "started_at": "2026-01-09T12:00:05Z",
    "completed_at": "2026-01-09T12:02:30Z",
    "duration_seconds": 145
  },
  "error": null,
  "created_by": "user-uuid"
}
```

### RunConfig

```json
{
  "engine_version": "1.0.0",
  "ruleset_version": "1.0.0",
  "dataset_version": "1.0.0",
  "schema_version": "1.0.0",
  "seed": 42,
  "horizon_ticks": 100,
  "scheduler": {
    "partition_by": "region",
    "sample_rate": 1.0,
    "batch_size": 1000
  },
  "scenario_patch": {
    "variable_deltas": {
      "economy_confidence": 0.1
    },
    "event_bundle_id": "uuid"
  }
}
```

---

## Endpoints

### List Runs

```http
GET /api/v1/runs
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `project_id` | uuid | - | Filter by project |
| `status` | string | - | Filter by status |
| `mode` | string | - | Filter by mode (society/target/hybrid) |
| `skip` | int | 0 | Pagination offset |
| `limit` | int | 20 | Items per page (max 100) |
| `sort` | string | `-created_at` | Sort field (prefix `-` for desc) |

**Response:**

```json
{
  "items": [
    {
      "id": "uuid",
      "name": "Baseline Simulation",
      "mode": "society",
      "status": "succeeded",
      "created_at": "2026-01-09T12:00:00Z",
      "duration_seconds": 145
    }
  ],
  "total": 50,
  "page": 1,
  "size": 20,
  "pages": 3
}
```

---

### Create Run

```http
POST /api/v1/runs
Content-Type: application/json
```

**Request Body:**

```json
{
  "project_id": "uuid",
  "name": "Market Response Simulation",
  "mode": "society",
  "config": {
    "seed": 42,
    "horizon_ticks": 100,
    "scheduler": {
      "partition_by": "region",
      "sample_rate": 1.0
    }
  },
  "parent_node_id": "uuid",
  "scenario_patch": {
    "variable_deltas": {
      "economy_confidence": 0.2
    }
  }
}
```

**Response:** `201 Created`

```json
{
  "id": "new-run-uuid",
  "project_id": "uuid",
  "name": "Market Response Simulation",
  "mode": "society",
  "status": "queued",
  "config": { ... },
  "created_at": "2026-01-09T12:00:00Z"
}
```

---

### Get Run Details

```http
GET /api/v1/runs/{id}
```

**Response:**

Returns the full Run object including progress and outputs.

---

### Start Run

```http
POST /api/v1/runs/{id}/start
```

Transitions a `queued` run to `running` and dispatches to workers.

**Response:** `202 Accepted`

```json
{
  "id": "uuid",
  "status": "running",
  "message": "Run started successfully",
  "estimated_duration_seconds": 120
}
```

---

### Cancel Run

```http
POST /api/v1/runs/{id}/cancel
```

Cancels a `queued` or `running` run.

**Response:**

```json
{
  "id": "uuid",
  "status": "cancelled",
  "message": "Run cancelled",
  "partial_results": true,
  "ticks_completed": 45
}
```

---

### Get Run Progress (SSE)

```http
GET /api/v1/runs/{id}/progress
Accept: text/event-stream
```

Server-Sent Events stream for real-time progress updates.

**Events:**

```
event: progress
data: {"tick": 25, "total_ticks": 100, "percent": 25, "agents_processed": 2500}

event: progress
data: {"tick": 50, "total_ticks": 100, "percent": 50, "agents_processed": 5000}

event: completed
data: {"status": "succeeded", "node_id": "uuid", "duration_seconds": 145}
```

---

### Get Run Results

```http
GET /api/v1/runs/{id}/results
```

**Response:**

```json
{
  "run_id": "uuid",
  "status": "succeeded",
  "node_id": "uuid",
  "outcome_summary": {
    "adoption_rate": 0.72,
    "sentiment_shift": 0.15,
    "confidence_level": "high"
  },
  "distribution": {
    "supporters": 0.45,
    "neutral": 0.35,
    "skeptics": 0.20
  },
  "trends": {
    "adoption_rate": [
      {"tick": 0, "value": 0.50},
      {"tick": 25, "value": 0.58},
      {"tick": 50, "value": 0.65},
      {"tick": 75, "value": 0.70},
      {"tick": 100, "value": 0.72}
    ]
  },
  "key_events": [
    {
      "tick": 15,
      "type": "media_exposure",
      "description": "Major news coverage",
      "impact": 0.08
    }
  ],
  "telemetry_ref": "s3://bucket/telemetry/uuid.parquet"
}
```

---

### Create Batch Runs

```http
POST /api/v1/runs/batch
Content-Type: application/json
```

Create multiple runs at once (e.g., for multi-seed stability testing).

**Request Body:**

```json
{
  "project_id": "uuid",
  "base_config": {
    "mode": "society",
    "horizon_ticks": 100
  },
  "variations": [
    {"name": "Seed 1", "seed": 1},
    {"name": "Seed 2", "seed": 2},
    {"name": "Seed 3", "seed": 3},
    {"name": "Seed 4", "seed": 4},
    {"name": "Seed 5", "seed": 5}
  ],
  "auto_start": true
}
```

**Response:** `201 Created`

```json
{
  "batch_id": "batch-uuid",
  "runs": [
    {"id": "run-1", "name": "Seed 1", "status": "queued"},
    {"id": "run-2", "name": "Seed 2", "status": "queued"},
    {"id": "run-3", "name": "Seed 3", "status": "queued"},
    {"id": "run-4", "name": "Seed 4", "status": "queued"},
    {"id": "run-5", "name": "Seed 5", "status": "queued"}
  ],
  "total": 5
}
```

---

## Concurrency Limits

| Limit | Value | Scope |
|-------|-------|-------|
| Max concurrent runs | 10 | Per tenant |
| Max queued runs | 50 | Per tenant |
| Max run duration | 30 minutes | Per run |

When limits are exceeded, the API returns `429 Too Many Requests`.

---

## Error Responses

### 400 Bad Request - Invalid Config

```json
{
  "detail": "horizon_ticks must be between 1 and 1000",
  "status_code": 400,
  "error_code": "VALIDATION_ERROR"
}
```

### 409 Conflict - Already Running

```json
{
  "detail": "Run is already running",
  "status_code": 409,
  "error_code": "ALREADY_RUNNING"
}
```

### 429 Too Many Requests

```json
{
  "detail": "Concurrent run limit exceeded (10/10). Try again later.",
  "status_code": 429,
  "error_code": "QUOTA_EXCEEDED",
  "retry_after": 30
}
```

---

## Examples

### Run with Progress Tracking

```python
import httpx
import sseclient

client = httpx.Client(
    base_url="https://api.agentverse.ai/api/v1",
    headers={"Authorization": f"Bearer {token}"}
)

# Create and start run
run = client.post("/runs", json={
    "project_id": "project-uuid",
    "name": "Test Simulation",
    "mode": "society",
    "config": {"seed": 42, "horizon_ticks": 100}
}).json()

client.post(f"/runs/{run['id']}/start")

# Stream progress
with httpx.stream(
    "GET",
    f"/runs/{run['id']}/progress",
    headers={"Accept": "text/event-stream", "Authorization": f"Bearer {token}"}
) as response:
    sse_client = sseclient.SSEClient(response.iter_bytes())
    for event in sse_client.events():
        print(f"{event.event}: {event.data}")
        if event.event == "completed":
            break
```

### Batch Multi-Seed Runs

```bash
curl -X POST "https://api.agentverse.ai/api/v1/runs/batch" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "uuid",
    "base_config": {"mode": "society", "horizon_ticks": 100},
    "variations": [
      {"name": "Seed 1", "seed": 1},
      {"name": "Seed 2", "seed": 2},
      {"name": "Seed 3", "seed": 3}
    ],
    "auto_start": true
  }'
```

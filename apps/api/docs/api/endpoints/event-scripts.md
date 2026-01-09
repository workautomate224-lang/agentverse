# Event Scripts API

**Tag:** `Event Scripts`
**Base Path:** `/api/v1/event-scripts`

Event Scripts are pre-compiled interventions that modify simulation state. They implement constraint **C5: LLMs as Compilers** - events are compiled once and executed deterministically.

---

## Core Concepts

### Compilation Flow (C5)

```
Natural Language → LLM Compilation → Event Script → Deterministic Execution
```

1. **Compile**: LLM translates prompt to structured event script (once)
2. **Store**: Event script persisted with versioning
3. **Execute**: Script runs deterministically (no LLM at runtime)
4. **Replay**: Same script always produces same effect

### Intensity Profiles

Events can have different temporal patterns:

| Profile | Description |
|---------|-------------|
| `instantaneous` | Immediate full effect, no decay |
| `linear_decay` | Linear decrease over time |
| `exponential_decay` | Exponential decrease over time |
| `lagged` | Delayed start before full effect |
| `pulse` | Repeated effect at intervals |
| `step` | Discrete jumps at specified ticks |
| `custom` | User-defined curve |

---

## Data Model

### EventScript

```json
{
  "id": "uuid",
  "project_id": "uuid",
  "tenant_id": "uuid",
  "name": "Major Media Campaign",
  "description": "Launches positive media coverage across urban regions",
  "target_type": "perception",
  "target_scope": {
    "regions": ["urban", "suburban"],
    "segments": ["early_adopters", "mainstream"]
  },
  "effects": [
    {
      "variable": "media_sentiment",
      "operation": "add",
      "base_value": 0.15,
      "intensity_profile": {
        "type": "exponential_decay",
        "decay_rate": 0.05,
        "duration_ticks": 20
      }
    }
  ],
  "preconditions": [
    {
      "variable": "economy_confidence",
      "operator": "gte",
      "value": 0.5
    }
  ],
  "event_version": "1.0.0",
  "schema_version": "1.0.0",
  "provenance": {
    "compiler_version": "1.0.0",
    "compiled_at": "2026-01-09T12:00:00Z",
    "compiled_from": "natural_language",
    "original_prompt": "Launch a positive media campaign in urban areas"
  },
  "is_active": true,
  "created_at": "2026-01-09T12:00:00Z",
  "created_by": "user-uuid"
}
```

### EventBundle

```json
{
  "id": "uuid",
  "project_id": "uuid",
  "name": "Economic Recovery Package",
  "description": "Combined economic and media intervention",
  "event_ids": ["event-1", "event-2", "event-3"],
  "joint_probability": 0.75,
  "execution_order": "parallel",
  "created_at": "2026-01-09T12:00:00Z"
}
```

### Effect

```json
{
  "variable": "media_sentiment",
  "operation": "add",
  "base_value": 0.15,
  "intensity_profile": {
    "type": "exponential_decay",
    "decay_rate": 0.05,
    "duration_ticks": 20
  },
  "variance": 0.02,
  "conditions": [
    {
      "variable": "awareness",
      "operator": "gte",
      "value": 0.5
    }
  ]
}
```

### IntensityProfile

```json
{
  "type": "exponential_decay",
  "decay_rate": 0.05,
  "duration_ticks": 20,
  "initial_delay": 0,
  "min_intensity": 0.0,
  "max_intensity": 1.0
}
```

---

## Endpoints

### List Event Scripts

```http
GET /api/v1/event-scripts
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `project_id` | uuid | - | Filter by project |
| `target_type` | string | - | Filter by target (environment, perception, network) |
| `is_active` | bool | - | Filter by active status |
| `search` | string | - | Search by name |
| `skip` | int | 0 | Pagination offset |
| `limit` | int | 20 | Items per page |

**Response:**

```json
{
  "items": [
    {
      "id": "uuid",
      "name": "Major Media Campaign",
      "target_type": "perception",
      "is_active": true,
      "event_version": "1.0.0",
      "created_at": "2026-01-09T12:00:00Z"
    }
  ],
  "total": 25,
  "page": 1,
  "size": 20
}
```

---

### Create Event Script

```http
POST /api/v1/event-scripts
Content-Type: application/json
```

**Request Body:**

```json
{
  "project_id": "uuid",
  "name": "Economic Boost",
  "description": "Improves economy confidence",
  "target_type": "environment",
  "target_scope": {
    "regions": ["urban", "suburban", "rural"]
  },
  "effects": [
    {
      "variable": "economy_confidence",
      "operation": "add",
      "base_value": 0.2,
      "intensity_profile": {
        "type": "linear_decay",
        "duration_ticks": 30
      }
    }
  ],
  "preconditions": []
}
```

**Response:** `201 Created`

```json
{
  "id": "new-event-uuid",
  "project_id": "uuid",
  "name": "Economic Boost",
  "target_type": "environment",
  "effects": [...],
  "event_version": "1.0.0",
  "schema_version": "1.0.0",
  "is_active": true,
  "created_at": "2026-01-09T12:00:00Z"
}
```

---

### Get Event Script

```http
GET /api/v1/event-scripts/{id}
```

**Response:**

Returns the full EventScript object with all effects, preconditions, and provenance.

---

### Update Event Script

```http
PUT /api/v1/event-scripts/{id}
Content-Type: application/json
```

**Request Body:**

```json
{
  "name": "Updated Event Name",
  "description": "Updated description",
  "effects": [
    {
      "variable": "economy_confidence",
      "operation": "add",
      "base_value": 0.25
    }
  ]
}
```

**Response:** `200 OK`

Returns the updated EventScript with bumped `event_version`.

---

### Delete Event Script

```http
DELETE /api/v1/event-scripts/{id}
```

**Response:** `204 No Content`

---

### Execute Event Script

```http
POST /api/v1/event-scripts/{id}/execute
Content-Type: application/json
```

Execute an event script on a specific node.

**Request Body:**

```json
{
  "node_id": "uuid",
  "tick": 25,
  "intensity_override": 0.8,
  "scope_override": {
    "regions": ["urban"]
  }
}
```

**Response:** `202 Accepted`

```json
{
  "execution_id": "uuid",
  "event_id": "uuid",
  "node_id": "uuid",
  "tick": 25,
  "affected_agents": 2500,
  "status": "applied",
  "effects_applied": [
    {
      "variable": "economy_confidence",
      "delta": 0.16,
      "agents_affected": 2500
    }
  ]
}
```

---

### Validate Event Script

```http
POST /api/v1/event-scripts/validate
Content-Type: application/json
```

Validate an event script without creating it.

**Request Body:**

```json
{
  "project_id": "uuid",
  "effects": [
    {
      "variable": "unknown_variable",
      "operation": "add",
      "base_value": 0.2
    }
  ]
}
```

**Response:**

```json
{
  "valid": false,
  "errors": [
    {
      "path": "effects[0].variable",
      "message": "Variable 'unknown_variable' not found in project schema",
      "suggestion": "Did you mean 'economy_confidence'?"
    }
  ],
  "warnings": [
    {
      "path": "effects[0].base_value",
      "message": "Value 0.2 is in the 95th percentile - this is a strong effect"
    }
  ]
}
```

---

## Event Bundles

### List Event Bundles

```http
GET /api/v1/event-scripts/bundles
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `project_id` | uuid | - | Filter by project |
| `skip` | int | 0 | Pagination offset |
| `limit` | int | 20 | Items per page |

**Response:**

```json
{
  "items": [
    {
      "id": "uuid",
      "name": "Economic Recovery Package",
      "event_count": 3,
      "joint_probability": 0.75,
      "created_at": "2026-01-09T12:00:00Z"
    }
  ],
  "total": 5
}
```

---

### Create Event Bundle

```http
POST /api/v1/event-scripts/bundles
Content-Type: application/json
```

**Request Body:**

```json
{
  "project_id": "uuid",
  "name": "Economic Recovery Package",
  "description": "Combined interventions for economic recovery",
  "event_ids": ["event-1", "event-2", "event-3"],
  "joint_probability": 0.75,
  "execution_order": "sequential"
}
```

**Response:** `201 Created`

```json
{
  "id": "bundle-uuid",
  "name": "Economic Recovery Package",
  "event_ids": ["event-1", "event-2", "event-3"],
  "joint_probability": 0.75,
  "execution_order": "sequential",
  "created_at": "2026-01-09T12:00:00Z"
}
```

---

### Execute Event Bundle

```http
POST /api/v1/event-scripts/bundles/{id}/execute
Content-Type: application/json
```

**Request Body:**

```json
{
  "node_id": "uuid",
  "tick": 25
}
```

**Response:** `202 Accepted`

```json
{
  "bundle_id": "uuid",
  "node_id": "uuid",
  "tick": 25,
  "events_executed": [
    {
      "event_id": "event-1",
      "status": "applied",
      "affected_agents": 2500
    },
    {
      "event_id": "event-2",
      "status": "applied",
      "affected_agents": 3000
    }
  ],
  "total_affected_agents": 3500
}
```

---

## Trigger Logs

### Get Trigger Logs

```http
GET /api/v1/event-scripts/{id}/triggers
```

List all times this event script was triggered.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `node_id` | uuid | - | Filter by node |
| `run_id` | uuid | - | Filter by run |
| `skip` | int | 0 | Pagination offset |
| `limit` | int | 50 | Items per page |

**Response:**

```json
{
  "event_id": "uuid",
  "triggers": [
    {
      "id": "trigger-uuid",
      "node_id": "uuid",
      "run_id": "uuid",
      "tick": 25,
      "intensity": 0.8,
      "affected_agents": 2500,
      "triggered_at": "2026-01-09T12:01:00Z"
    }
  ],
  "total": 15
}
```

---

### Get Event Statistics

```http
GET /api/v1/event-scripts/{id}/stats
```

**Response:**

```json
{
  "event_id": "uuid",
  "total_triggers": 45,
  "total_affected_agents": 112500,
  "average_intensity": 0.75,
  "average_affected_agents": 2500,
  "triggers_by_node": {
    "node-1": 15,
    "node-2": 20,
    "node-3": 10
  },
  "first_triggered": "2026-01-01T10:00:00Z",
  "last_triggered": "2026-01-09T12:00:00Z"
}
```

---

## Error Responses

### 400 Bad Request - Invalid Effect

```json
{
  "detail": "Invalid effect configuration",
  "status_code": 400,
  "error_code": "INVALID_EFFECT",
  "errors": [
    {
      "path": "effects[0].operation",
      "message": "Operation 'divide' is not supported. Use: set, add, multiply, min, max"
    }
  ]
}
```

### 404 Not Found

```json
{
  "detail": "Event script not found",
  "status_code": 404,
  "error_code": "NOT_FOUND"
}
```

### 422 Unprocessable Entity - Unknown Variable

```json
{
  "detail": "Variable not found in project schema",
  "status_code": 422,
  "error_code": "UNKNOWN_VARIABLE",
  "variable": "nonexistent_variable",
  "available_variables": ["economy_confidence", "media_sentiment", "social_trust"]
}
```

### 409 Conflict - Version Conflict

```json
{
  "detail": "Event script has been modified by another user",
  "status_code": 409,
  "error_code": "VERSION_CONFLICT",
  "current_version": "1.2.0",
  "your_version": "1.1.0"
}
```

---

## Examples

### Create and Execute Event

```python
import httpx

client = httpx.Client(
    base_url="https://api.agentverse.ai/api/v1",
    headers={"Authorization": f"Bearer {token}"}
)

# Create event script
event = client.post("/event-scripts", json={
    "project_id": "project-uuid",
    "name": "Flash Sale Announcement",
    "target_type": "perception",
    "effects": [
        {
            "variable": "price_sensitivity",
            "operation": "add",
            "base_value": -0.15,
            "intensity_profile": {
                "type": "pulse",
                "interval_ticks": 5,
                "duration_ticks": 20
            }
        }
    ]
}).json()

print(f"Created event: {event['id']}")

# Execute on a node
result = client.post(f"/event-scripts/{event['id']}/execute", json={
    "node_id": "target-node-uuid",
    "tick": 10
}).json()

print(f"Affected {result['affected_agents']} agents")
```

### Create Event Bundle

```python
# Create individual events
economic_event = client.post("/event-scripts", json={
    "project_id": "project-uuid",
    "name": "Economic Stimulus",
    "target_type": "environment",
    "effects": [{"variable": "economy_confidence", "operation": "add", "base_value": 0.1}]
}).json()

media_event = client.post("/event-scripts", json={
    "project_id": "project-uuid",
    "name": "Media Campaign",
    "target_type": "perception",
    "effects": [{"variable": "media_sentiment", "operation": "add", "base_value": 0.15}]
}).json()

# Bundle them
bundle = client.post("/event-scripts/bundles", json={
    "project_id": "project-uuid",
    "name": "Recovery Package",
    "event_ids": [economic_event['id'], media_event['id']],
    "joint_probability": 0.8,
    "execution_order": "parallel"
}).json()

print(f"Bundle created: {bundle['id']}")
```

### Query Trigger History

```bash
# Get trigger logs for an event
curl -X GET "https://api.agentverse.ai/api/v1/event-scripts/{event_id}/triggers" \
  -H "Authorization: Bearer $TOKEN"

# Get event statistics
curl -X GET "https://api.agentverse.ai/api/v1/event-scripts/{event_id}/stats" \
  -H "Authorization: Bearer $TOKEN"
```

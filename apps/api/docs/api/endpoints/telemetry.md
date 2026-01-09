# Telemetry API (Read-Only)

**Tag:** `Telemetry`
**Base Path:** `/api/v1/telemetry`

Telemetry provides read-only access to simulation time-series data. This API implements constraint **C3: Replay is Read-Only** - telemetry queries never trigger simulations.

---

## Core Concepts

### Read-Only Guarantee (C3)

All telemetry endpoints are **strictly read-only**:
- No mutations to simulation state
- No triggering of new runs
- Safe to query at any time
- Results are cached for performance

### Data Structure

Telemetry is stored as time-series data:
- **Keyframes**: Full state snapshots at specific ticks
- **Deltas**: Incremental changes between keyframes
- **Events**: Triggered events during simulation
- **Aggregates**: Pre-computed metrics and distributions

---

## Data Model

### TelemetryIndex

```json
{
  "node_id": "uuid",
  "run_id": "uuid",
  "total_ticks": 100,
  "keyframe_interval": 10,
  "keyframe_ticks": [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
  "agent_count": 10000,
  "event_count": 45,
  "file_size_bytes": 15728640,
  "storage_ref": "s3://bucket/telemetry/uuid.parquet",
  "created_at": "2026-01-09T12:00:00Z"
}
```

### Keyframe

```json
{
  "tick": 50,
  "timestamp": "2026-01-09T12:01:15Z",
  "world_state": {
    "economy_confidence": 0.75,
    "media_sentiment": 0.60,
    "social_trust": 0.70
  },
  "distributions": {
    "adoption_rate": 0.65,
    "by_segment": {
      "early_adopters": 0.85,
      "mainstream": 0.55,
      "skeptics": 0.25
    },
    "by_region": {
      "urban": 0.72,
      "suburban": 0.58,
      "rural": 0.45
    }
  },
  "agent_summary": {
    "total": 10000,
    "active": 9850,
    "decided": 6500,
    "undecided": 3350
  }
}
```

### AgentHistory

```json
{
  "agent_id": "agent-uuid",
  "persona_id": "persona-uuid",
  "segment": "early_adopter",
  "region": "urban",
  "trajectory": [
    {
      "tick": 0,
      "state": {"adoption_intent": 0.5, "awareness": 0.3},
      "action": null
    },
    {
      "tick": 25,
      "state": {"adoption_intent": 0.7, "awareness": 0.8},
      "action": "researched_product"
    },
    {
      "tick": 50,
      "state": {"adoption_intent": 0.9, "awareness": 1.0},
      "action": "adopted"
    }
  ],
  "final_decision": "adopted",
  "decision_tick": 50
}
```

### Event

```json
{
  "id": "event-uuid",
  "tick": 15,
  "type": "media_exposure",
  "source": "event_script",
  "description": "Major news coverage launched",
  "affected_agents": 2500,
  "variable_changes": {
    "media_sentiment": 0.15
  },
  "impact_score": 0.08
}
```

---

## Endpoints

### Get Telemetry Index

```http
GET /api/v1/telemetry/{node_id}
```

Get metadata about available telemetry for a node.

**Response:**

```json
{
  "node_id": "uuid",
  "run_id": "uuid",
  "total_ticks": 100,
  "keyframe_interval": 10,
  "keyframe_ticks": [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
  "agent_count": 10000,
  "event_count": 45,
  "metrics_available": [
    "adoption_rate",
    "sentiment_shift",
    "awareness_level"
  ],
  "segments": ["early_adopters", "mainstream", "skeptics"],
  "regions": ["urban", "suburban", "rural"],
  "created_at": "2026-01-09T12:00:00Z"
}
```

---

### Get Tick Slice

```http
GET /api/v1/telemetry/{node_id}/slice
```

Get telemetry data for a range of ticks.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `start_tick` | int | 0 | Start of range (inclusive) |
| `end_tick` | int | - | End of range (inclusive) |
| `resolution` | int | 1 | Sample every N ticks |
| `metrics` | string | - | Comma-separated metric names |
| `segments` | string | - | Filter by segments |
| `regions` | string | - | Filter by regions |

**Example:**

```http
GET /api/v1/telemetry/{node_id}/slice?start_tick=0&end_tick=100&resolution=5&metrics=adoption_rate,sentiment_shift
```

**Response:**

```json
{
  "node_id": "uuid",
  "start_tick": 0,
  "end_tick": 100,
  "resolution": 5,
  "data": [
    {
      "tick": 0,
      "adoption_rate": 0.50,
      "sentiment_shift": 0.0
    },
    {
      "tick": 5,
      "adoption_rate": 0.52,
      "sentiment_shift": 0.02
    },
    {
      "tick": 10,
      "adoption_rate": 0.55,
      "sentiment_shift": 0.05
    }
  ],
  "total_points": 21
}
```

---

### Get Keyframe

```http
GET /api/v1/telemetry/{node_id}/keyframe/{tick}
```

Get full state snapshot at a specific tick.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `node_id` | uuid | Node identifier |
| `tick` | int | Tick number (must be a keyframe tick) |

**Response:**

```json
{
  "tick": 50,
  "is_keyframe": true,
  "world_state": {
    "economy_confidence": 0.75,
    "media_sentiment": 0.60,
    "social_trust": 0.70
  },
  "distributions": {
    "adoption_rate": 0.65,
    "by_segment": {
      "early_adopters": 0.85,
      "mainstream": 0.55,
      "skeptics": 0.25
    }
  },
  "agent_summary": {
    "total": 10000,
    "active": 9850,
    "decided": 6500
  },
  "top_events": [
    {
      "tick": 15,
      "type": "media_exposure",
      "impact": 0.08
    }
  ]
}
```

---

### Get Agent History

```http
GET /api/v1/telemetry/{node_id}/agent/{agent_id}
```

Get the full trajectory of a specific agent.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `include_reasoning` | bool | false | Include decision reasoning |
| `tick_range` | string | - | Filter to tick range (e.g., "0-50") |

**Response:**

```json
{
  "agent_id": "agent-uuid",
  "persona_id": "persona-uuid",
  "persona_name": "Urban Professional #1234",
  "segment": "early_adopter",
  "region": "urban",
  "initial_state": {
    "adoption_intent": 0.5,
    "awareness": 0.3,
    "trust": 0.6
  },
  "trajectory": [
    {
      "tick": 0,
      "state": {"adoption_intent": 0.5, "awareness": 0.3},
      "action": null,
      "reasoning": null
    },
    {
      "tick": 25,
      "state": {"adoption_intent": 0.7, "awareness": 0.8},
      "action": "researched_product",
      "reasoning": "Saw positive media coverage"
    },
    {
      "tick": 50,
      "state": {"adoption_intent": 0.9, "awareness": 1.0},
      "action": "adopted",
      "reasoning": "Peer recommendation pushed over threshold"
    }
  ],
  "final_decision": "adopted",
  "decision_tick": 50,
  "key_influences": [
    {"type": "media", "impact": 0.2},
    {"type": "peer", "impact": 0.3}
  ]
}
```

---

### Get Events

```http
GET /api/v1/telemetry/{node_id}/events
```

List all events that occurred during simulation.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `type` | string | - | Filter by event type |
| `tick_range` | string | - | Filter to tick range |
| `min_impact` | float | - | Minimum impact score |
| `skip` | int | 0 | Pagination offset |
| `limit` | int | 50 | Items per page |

**Response:**

```json
{
  "node_id": "uuid",
  "events": [
    {
      "id": "event-uuid",
      "tick": 15,
      "type": "media_exposure",
      "source": "event_script",
      "description": "Major news coverage",
      "affected_agents": 2500,
      "impact_score": 0.08
    },
    {
      "id": "event-uuid-2",
      "tick": 30,
      "type": "price_change",
      "source": "variable_delta",
      "description": "10% price reduction",
      "affected_agents": 10000,
      "impact_score": 0.12
    }
  ],
  "total": 45
}
```

---

### Stream Telemetry (SSE)

```http
GET /api/v1/telemetry/{node_id}/stream
Accept: text/event-stream
```

Stream telemetry chunks for progressive loading.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `chunk_size` | int | 10 | Ticks per chunk |
| `metrics` | string | - | Metrics to include |

**Events:**

```
event: chunk
data: {"start_tick": 0, "end_tick": 10, "data": [...]}

event: chunk
data: {"start_tick": 10, "end_tick": 20, "data": [...]}

event: complete
data: {"total_chunks": 10, "total_ticks": 100}
```

---

### Get Aggregate Metrics

```http
GET /api/v1/telemetry/{node_id}/aggregates
```

Get pre-computed aggregate metrics.

**Response:**

```json
{
  "node_id": "uuid",
  "aggregates": {
    "final_adoption_rate": 0.72,
    "peak_adoption_rate": 0.73,
    "peak_tick": 95,
    "average_decision_tick": 45,
    "median_decision_tick": 42,
    "conversion_by_segment": {
      "early_adopters": 0.92,
      "mainstream": 0.68,
      "skeptics": 0.35
    },
    "top_influencing_factors": [
      {"factor": "media_sentiment", "weight": 0.35},
      {"factor": "peer_influence", "weight": 0.28},
      {"factor": "price_sensitivity", "weight": 0.22}
    ]
  },
  "computed_at": "2026-01-09T12:02:30Z"
}
```

---

## Caching

Telemetry responses are cached aggressively:

| Endpoint | Cache TTL | Notes |
|----------|-----------|-------|
| Index | 1 hour | Invalidated on new run |
| Slice | 24 hours | Immutable after run completes |
| Keyframe | 24 hours | Immutable after run completes |
| Agent | 24 hours | Immutable after run completes |
| Events | 24 hours | Immutable after run completes |
| Aggregates | 24 hours | Immutable after run completes |

Cache headers are included in responses:

```http
Cache-Control: public, max-age=86400
ETag: "abc123"
```

---

## Error Responses

### 404 Not Found - Node Has No Telemetry

```json
{
  "detail": "No telemetry found for node. Run may still be in progress.",
  "status_code": 404,
  "error_code": "TELEMETRY_NOT_FOUND",
  "run_status": "running"
}
```

### 400 Bad Request - Invalid Tick

```json
{
  "detail": "Tick 150 is out of range. Max tick is 100.",
  "status_code": 400,
  "error_code": "INVALID_TICK"
}
```

### 400 Bad Request - Not a Keyframe

```json
{
  "detail": "Tick 15 is not a keyframe. Available keyframes: [0, 10, 20, ...]",
  "status_code": 400,
  "error_code": "NOT_A_KEYFRAME",
  "nearest_keyframes": [10, 20]
}
```

---

## Examples

### Fetch Adoption Curve

```python
import httpx

client = httpx.Client(
    base_url="https://api.agentverse.ai/api/v1",
    headers={"Authorization": f"Bearer {token}"}
)

# Get adoption rate over time
telemetry = client.get(
    f"/telemetry/{node_id}/slice",
    params={
        "start_tick": 0,
        "end_tick": 100,
        "resolution": 5,
        "metrics": "adoption_rate"
    }
).json()

# Plot the curve
for point in telemetry['data']:
    print(f"Tick {point['tick']}: {point['adoption_rate']:.1%}")
```

### Analyze Segment Differences

```python
# Get keyframe at end of simulation
final_state = client.get(f"/telemetry/{node_id}/keyframe/100").json()

# Compare segments
for segment, rate in final_state['distributions']['by_segment'].items():
    print(f"{segment}: {rate:.1%} adoption")
```

### Track Individual Agent

```python
# Get agent trajectory with reasoning
agent = client.get(
    f"/telemetry/{node_id}/agent/{agent_id}",
    params={"include_reasoning": True}
).json()

print(f"Agent: {agent['persona_name']}")
print(f"Final decision: {agent['final_decision']} at tick {agent['decision_tick']}")

for step in agent['trajectory']:
    if step['action']:
        print(f"  Tick {step['tick']}: {step['action']} - {step['reasoning']}")
```

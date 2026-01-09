# Nodes API (Universe Map)

**Tag:** `Universe Map`
**Base Path:** `/api/v1/nodes`

Nodes represent points in the Universe Map - each node is a possible future state with its own probability, outcomes, and telemetry.

---

## Core Concepts

### Fork-Not-Mutate (C1)

The Universe Map is an **append-only tree**. When you want to explore a different scenario:

1. Fork an existing node with modified variables
2. A new child node is created
3. The parent node is **never** modified
4. History is always preserved

### Node Types

| Type | Description |
|------|-------------|
| **Root** | The baseline node (probability = 1.0, no parent) |
| **Branch** | A forked node with modified variables |
| **Cluster** | An aggregated node representing similar scenarios |

---

## Data Model

### Node

```json
{
  "id": "uuid",
  "project_id": "uuid",
  "parent_node_id": "uuid | null",
  "cluster_id": "uuid | null",
  "name": "Optimistic Economy Scenario",
  "probability": 0.35,
  "confidence_level": "high",
  "status": "completed",
  "outcome_summary": {
    "adoption_rate": 0.72,
    "sentiment_shift": 0.15,
    "key_drivers": ["media_sentiment", "peer_influence"]
  },
  "scenario_patch_ref": "s3://bucket/patches/uuid.json",
  "run_refs": ["run-uuid-1", "run-uuid-2"],
  "telemetry_ref": "s3://bucket/telemetry/uuid.parquet",
  "reliability_ref": "uuid",
  "created_at": "2026-01-09T12:00:00Z"
}
```

### Edge

```json
{
  "id": "uuid",
  "from_node_id": "uuid",
  "to_node_id": "uuid",
  "intervention_ref": "event-script-uuid",
  "explanation_ref": "s3://bucket/explanations/uuid.json",
  "variable_deltas": {
    "economy_confidence": 0.2,
    "media_sentiment": -0.1
  }
}
```

---

## Endpoints

### Get Universe Map

```http
GET /api/v1/nodes/universe-map/{project_id}
```

Returns the complete node/edge graph for visualization.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `include_clusters` | bool | true | Include cluster nodes |
| `max_depth` | int | - | Limit tree depth |
| `status` | string | - | Filter by status |

**Response:**

```json
{
  "project_id": "uuid",
  "nodes": [
    {
      "id": "root-uuid",
      "parent_node_id": null,
      "name": "Baseline",
      "probability": 1.0,
      "confidence_level": "high",
      "status": "completed",
      "is_root": true,
      "cluster_id": null
    },
    {
      "id": "child-uuid",
      "parent_node_id": "root-uuid",
      "name": "Optimistic Scenario",
      "probability": 0.35,
      "confidence_level": "medium",
      "status": "completed",
      "is_root": false,
      "cluster_id": null
    }
  ],
  "edges": [
    {
      "id": "edge-uuid",
      "from_node_id": "root-uuid",
      "to_node_id": "child-uuid",
      "intervention_summary": "+20% economy confidence"
    }
  ],
  "total_nodes": 45,
  "max_depth": 6
}
```

---

### Get Node Details

```http
GET /api/v1/nodes/{id}
```

**Response:**

```json
{
  "id": "uuid",
  "project_id": "uuid",
  "parent_node_id": "parent-uuid",
  "name": "Optimistic Economy",
  "probability": 0.35,
  "confidence_level": "high",
  "status": "completed",
  "outcome_summary": {
    "adoption_rate": 0.72,
    "sentiment_shift": 0.15,
    "key_drivers": ["media_sentiment", "peer_influence"],
    "distribution": {
      "supporters": 0.45,
      "neutral": 0.35,
      "skeptics": 0.20
    }
  },
  "variable_state": {
    "economy_confidence": 0.8,
    "media_sentiment": 0.6,
    "social_trust": 0.7,
    "price_sensitivity": 0.4
  },
  "runs": [
    {
      "id": "run-uuid",
      "status": "succeeded",
      "completed_at": "2026-01-09T10:30:00Z",
      "seed": 42
    }
  ],
  "reliability": {
    "calibration_score": 0.85,
    "stability_score": 0.90,
    "drift_score": 0.05,
    "confidence_level": "high"
  },
  "created_at": "2026-01-09T12:00:00Z",
  "created_by": "user-uuid"
}
```

---

### Fork Node

```http
POST /api/v1/nodes/fork
Content-Type: application/json
```

Create a new node by forking an existing one with modified variables.

**Request Body:**

```json
{
  "parent_node_id": "uuid",
  "name": "Pessimistic Economy Scenario",
  "variable_deltas": {
    "economy_confidence": -0.3,
    "media_sentiment": -0.2,
    "social_trust": -0.1
  },
  "event_bundle_id": "uuid",
  "auto_run": true,
  "run_config": {
    "ticks": 100,
    "seed": 42
  }
}
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `parent_node_id` | uuid | yes | Node to fork from |
| `name` | string | no | Name for the new node |
| `variable_deltas` | object | no | Variable changes to apply |
| `event_bundle_id` | uuid | no | Pre-compiled event bundle |
| `auto_run` | bool | no | Start simulation immediately |
| `run_config` | object | no | Configuration for auto-run |

**Response:** `201 Created`

```json
{
  "node": {
    "id": "new-node-uuid",
    "parent_node_id": "parent-uuid",
    "name": "Pessimistic Economy Scenario",
    "status": "pending",
    "probability": null
  },
  "run": {
    "id": "run-uuid",
    "status": "queued"
  },
  "edge": {
    "id": "edge-uuid",
    "from_node_id": "parent-uuid",
    "to_node_id": "new-node-uuid"
  }
}
```

---

### List Child Nodes

```http
GET /api/v1/nodes/{id}/children
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `include_clusters` | bool | true | Include clustered children |
| `status` | string | - | Filter by status |

**Response:**

```json
{
  "parent_id": "uuid",
  "children": [
    {
      "id": "child-1",
      "name": "Optimistic",
      "probability": 0.35,
      "status": "completed"
    },
    {
      "id": "child-2",
      "name": "Pessimistic",
      "probability": 0.25,
      "status": "completed"
    }
  ],
  "total": 2
}
```

---

### Compare Nodes

```http
GET /api/v1/nodes/compare
```

Compare 2-4 nodes side-by-side.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `node_ids` | string | yes | Comma-separated node IDs |

**Example:**

```http
GET /api/v1/nodes/compare?node_ids=uuid1,uuid2,uuid3
```

**Response:**

```json
{
  "nodes": [
    {
      "id": "uuid1",
      "name": "Baseline",
      "probability": 1.0
    },
    {
      "id": "uuid2",
      "name": "Optimistic",
      "probability": 0.35
    }
  ],
  "outcome_comparison": {
    "adoption_rate": {
      "uuid1": 0.55,
      "uuid2": 0.72,
      "delta": 0.17,
      "percent_change": 30.9
    },
    "sentiment_shift": {
      "uuid1": 0.0,
      "uuid2": 0.15,
      "delta": 0.15,
      "percent_change": null
    }
  },
  "driver_comparison": {
    "media_sentiment": {
      "uuid1": 0.5,
      "uuid2": 0.7,
      "impact_score": 0.85
    }
  },
  "reliability_comparison": {
    "uuid1": {"confidence_level": "high", "score": 0.90},
    "uuid2": {"confidence_level": "medium", "score": 0.75}
  }
}
```

---

### Path Analysis

```http
GET /api/v1/nodes/{id}/path-analysis
```

Analyze the path from root to this node.

**Response:**

```json
{
  "node_id": "uuid",
  "path": [
    {
      "node_id": "root-uuid",
      "name": "Baseline",
      "depth": 0
    },
    {
      "node_id": "mid-uuid",
      "name": "Economy Boost",
      "depth": 1,
      "intervention": "+10% economy"
    },
    {
      "node_id": "uuid",
      "name": "Media Campaign",
      "depth": 2,
      "intervention": "+15% media sentiment"
    }
  ],
  "total_probability": 0.28,
  "key_interventions": [
    {
      "description": "Economy confidence boost",
      "impact": 0.15
    },
    {
      "description": "Media campaign launch",
      "impact": 0.12
    }
  ],
  "cumulative_deltas": {
    "economy_confidence": 0.25,
    "media_sentiment": 0.15
  }
}
```

---

## Error Responses

### 400 Bad Request - Invalid Fork

```json
{
  "detail": "Cannot fork a pending node. Wait for completion.",
  "status_code": 400,
  "error_code": "INVALID_FORK"
}
```

### 404 Not Found

```json
{
  "detail": "Node not found",
  "status_code": 404
}
```

### 409 Conflict - Circular Reference

```json
{
  "detail": "Fork would create circular reference",
  "status_code": 409,
  "error_code": "CIRCULAR_REFERENCE"
}
```

---

## Examples

### Fork with Auto-Run

```python
import httpx

client = httpx.Client(
    base_url="https://api.agentverse.ai/api/v1",
    headers={"Authorization": f"Bearer {token}"}
)

# Fork the root node with optimistic economy
result = client.post("/nodes/fork", json={
    "parent_node_id": "root-node-uuid",
    "name": "Optimistic Economy Q2",
    "variable_deltas": {
        "economy_confidence": 0.2,
        "media_sentiment": 0.1
    },
    "auto_run": True,
    "run_config": {
        "ticks": 100,
        "seed": 12345
    }
}).json()

print(f"New node: {result['node']['id']}")
print(f"Run started: {result['run']['id']}")
```

### Compare Multiple Scenarios

```bash
# Compare 3 scenarios
curl -X GET "https://api.agentverse.ai/api/v1/nodes/compare?node_ids=uuid1,uuid2,uuid3" \
  -H "Authorization: Bearer $TOKEN"
```

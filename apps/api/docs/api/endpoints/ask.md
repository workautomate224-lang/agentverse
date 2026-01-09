# Ask API (Event Compiler)

**Tag:** `Ask - Event Compiler`
**Base Path:** `/api/v1/ask`

The Ask API converts natural language prompts into executable simulation events. This implements the "LLMs as Compilers" (C5) constraint - the LLM compiles once, and execution is deterministic.

---

## Core Concepts

### Compilation Flow

```
Natural Language → Intent Analysis → Decomposition → Variable Mapping → Scenarios → Clusters
```

1. **Intent Analysis**: Classify prompt type (event, variable change, query)
2. **Decomposition**: Break into atomic sub-effects
3. **Variable Mapping**: Map to environment/perception variables
4. **Scenario Generation**: Create candidate futures (no hard cap)
5. **Clustering**: Group similar scenarios for progressive expansion

### Intent Types

| Type | Description | Example |
|------|-------------|---------|
| `event` | External event affecting agents | "A major news story breaks" |
| `variable_change` | Direct variable modification | "Economy improves by 20%" |
| `comparison` | Compare multiple scenarios | "What if A vs B" |
| `query` | Information request | "What drives adoption?" |
| `explanation` | Causal explanation | "Why did trust drop?" |

---

## Endpoints

### Compile Prompt

```http
POST /api/v1/ask/compile
Content-Type: application/json
```

Compile a natural language prompt into simulation events.

**Request Body:**

```json
{
  "project_id": "uuid",
  "prompt": "What if the economy improves by 20% and there's positive media coverage?",
  "scope": {
    "regions": ["urban", "suburban"],
    "segments": ["early_adopters"],
    "time_window": {
      "start_tick": 0,
      "end_tick": 50
    }
  },
  "max_scenarios": 20,
  "use_clustering": true,
  "cluster_threshold": 0.7
}
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `project_id` | uuid | yes | Target project |
| `prompt` | string | yes | Natural language prompt |
| `scope` | object | no | Limit scope (regions, segments, time) |
| `max_scenarios` | int | no | Soft limit on scenarios (default: 50) |
| `use_clustering` | bool | no | Enable scenario clustering (default: true) |
| `cluster_threshold` | float | no | Similarity threshold for clustering |

**Response:**

```json
{
  "compilation_id": "uuid",
  "intent": {
    "type": "event",
    "confidence": 0.92,
    "summary": "Economic improvement with positive media"
  },
  "scope": {
    "regions": ["urban", "suburban"],
    "segments": ["early_adopters"],
    "time_window": {"start_tick": 0, "end_tick": 50}
  },
  "sub_effects": [
    {
      "id": "effect-1",
      "description": "Economy confidence boost",
      "target_type": "environment",
      "confidence": 0.95
    },
    {
      "id": "effect-2",
      "description": "Positive media sentiment",
      "target_type": "perception",
      "confidence": 0.88
    }
  ],
  "variable_mappings": [
    {
      "effect_id": "effect-1",
      "variable": "economy_confidence",
      "delta": 0.2,
      "confidence": 0.95
    },
    {
      "effect_id": "effect-2",
      "variable": "media_sentiment",
      "delta": 0.15,
      "confidence": 0.88
    }
  ],
  "scenarios": [
    {
      "id": "scenario-1",
      "name": "Strong Combined Effect",
      "probability": 0.35,
      "variable_deltas": {
        "economy_confidence": 0.25,
        "media_sentiment": 0.20
      }
    }
  ],
  "clusters": [
    {
      "id": "cluster-1",
      "name": "High Impact",
      "scenario_count": 8,
      "probability_range": [0.25, 0.40],
      "representative_scenario": "scenario-1",
      "expandable": true
    },
    {
      "id": "cluster-2",
      "name": "Moderate Impact",
      "scenario_count": 12,
      "probability_range": [0.10, 0.25],
      "representative_scenario": "scenario-5",
      "expandable": true
    }
  ],
  "explanation": {
    "causal_chain": "Economic improvement → increased consumer confidence → higher purchase intent. Media coverage amplifies effect through social proof.",
    "key_drivers": [
      {"variable": "economy_confidence", "impact_score": 0.85},
      {"variable": "media_sentiment", "impact_score": 0.65}
    ],
    "uncertainty_notes": [
      "Media sentiment effect may vary by demographic"
    ]
  }
}
```

---

### Expand Cluster

```http
POST /api/v1/ask/expand-cluster
Content-Type: application/json
```

Reveal individual scenarios within a cluster for progressive exploration.

**Request Body:**

```json
{
  "compilation_id": "uuid",
  "cluster_id": "cluster-1",
  "max_scenarios": 10
}
```

**Response:**

```json
{
  "cluster_id": "cluster-1",
  "scenarios": [
    {
      "id": "scenario-1",
      "name": "Strong Economy + Strong Media",
      "probability": 0.35,
      "variable_deltas": {
        "economy_confidence": 0.25,
        "media_sentiment": 0.20
      }
    },
    {
      "id": "scenario-2",
      "name": "Strong Economy + Moderate Media",
      "probability": 0.30,
      "variable_deltas": {
        "economy_confidence": 0.25,
        "media_sentiment": 0.12
      }
    }
  ],
  "remaining_count": 6,
  "has_more": true
}
```

---

### Execute Scenario

```http
POST /api/v1/ask/execute-scenario
Content-Type: application/json
```

Execute a compiled scenario and create a node in the Universe Map.

**Request Body:**

```json
{
  "compilation_id": "uuid",
  "scenario_id": "scenario-1",
  "parent_node_id": "uuid",
  "run_config": {
    "ticks": 100,
    "seed": 42
  }
}
```

**Response:** `202 Accepted`

```json
{
  "node_id": "new-node-uuid",
  "run_id": "run-uuid",
  "status": "queued",
  "scenario": {
    "id": "scenario-1",
    "name": "Strong Combined Effect"
  }
}
```

---

### Get Compilation History

```http
GET /api/v1/ask/history/{project_id}
```

List previous compilations for a project.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skip` | int | 0 | Pagination offset |
| `limit` | int | 20 | Items per page |

**Response:**

```json
{
  "items": [
    {
      "id": "uuid",
      "prompt": "What if the economy improves?",
      "intent_type": "event",
      "scenario_count": 15,
      "created_at": "2026-01-09T12:00:00Z",
      "executed_count": 3
    }
  ],
  "total": 25
}
```

---

## Rate Limits

The Ask API has stricter rate limits due to LLM usage:

| Limit | Value |
|-------|-------|
| Compile requests | 20/minute |
| Expand requests | 50/minute |
| Execute requests | 10/minute |

---

## Error Responses

### 400 Bad Request - Ambiguous Prompt

```json
{
  "detail": "Prompt is ambiguous. Please be more specific.",
  "status_code": 400,
  "error_code": "AMBIGUOUS_PROMPT",
  "suggestions": [
    "Specify a percentage for 'economy improves'",
    "Clarify which region should be affected"
  ]
}
```

### 422 Unprocessable Entity - Unknown Variables

```json
{
  "detail": "Could not map to known variables",
  "status_code": 422,
  "error_code": "UNKNOWN_VARIABLES",
  "unmapped_effects": [
    {
      "description": "quantum entanglement boost",
      "reason": "Not a recognized variable in consumer_goods domain"
    }
  ]
}
```

---

## Examples

### Basic Compilation

```python
import httpx

client = httpx.Client(
    base_url="https://api.agentverse.ai/api/v1",
    headers={"Authorization": f"Bearer {token}"}
)

# Compile a prompt
result = client.post("/ask/compile", json={
    "project_id": "project-uuid",
    "prompt": "What happens if a competitor launches a cheaper product?",
    "use_clustering": True
}).json()

print(f"Intent: {result['intent']['summary']}")
print(f"Clusters: {len(result['clusters'])}")

# Explore the top cluster
if result['clusters']:
    expanded = client.post("/ask/expand-cluster", json={
        "compilation_id": result['compilation_id'],
        "cluster_id": result['clusters'][0]['id']
    }).json()

    for scenario in expanded['scenarios']:
        print(f"- {scenario['name']}: {scenario['probability']:.0%}")
```

### Execute and Track

```python
# Execute a scenario
execution = client.post("/ask/execute-scenario", json={
    "compilation_id": result['compilation_id'],
    "scenario_id": expanded['scenarios'][0]['id'],
    "parent_node_id": "root-node-uuid",
    "run_config": {"ticks": 100, "seed": 42}
}).json()

print(f"Run started: {execution['run_id']}")
print(f"New node: {execution['node_id']}")
```

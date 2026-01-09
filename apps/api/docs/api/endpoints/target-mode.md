# Target Mode API

**Tag:** `Target Mode`
**Base Path:** `/api/v1/target`

Target Mode enables individual-focused path planning - simulating how to influence a specific persona toward a goal state. While Society Mode simulates populations, Target Mode plans optimal intervention sequences for individuals.

---

## Core Concepts

### Target vs Society Mode

| Aspect | Society Mode | Target Mode |
|--------|--------------|-------------|
| Focus | Population-level outcomes | Individual journey |
| Output | Distribution shifts | Action sequences |
| Question | "What happens if...?" | "How do I get X to Y?" |
| Use Case | Policy impact analysis | Sales/marketing sequences |

### Path Planning

Target Mode generates **paths** - sequences of actions that move a target persona from initial state to goal state:

```
Initial State → Action 1 → Intermediate State → Action 2 → ... → Goal State
```

Each path has:
- **Probability**: Likelihood of success
- **Cost**: Resource expenditure (time, money)
- **Constraint compliance**: Whether all constraints are met

### Actions and Constraints

- **Actions**: Interventions the operator can take (emails, calls, ads)
- **Constraints**: Limits on actions (budget, timing, channel limits)
- **Utility Profile**: What the target persona values

---

## Data Model

### TargetPersona

```json
{
  "id": "uuid",
  "project_id": "uuid",
  "persona_id": "uuid",
  "name": "Tech-Savvy Professional",
  "initial_state": {
    "awareness": 0.3,
    "interest": 0.4,
    "consideration": 0.1,
    "intent": 0.05
  },
  "goal_state": {
    "intent": 0.9
  },
  "utility_profile": {
    "price_sensitivity": 0.6,
    "quality_focus": 0.8,
    "brand_loyalty": 0.4,
    "social_influence": 0.7
  },
  "constraints": [
    {
      "type": "budget",
      "max_value": 500
    },
    {
      "type": "time",
      "max_ticks": 30
    }
  ]
}
```

### Action

```json
{
  "id": "uuid",
  "domain": "consumer_goods",
  "name": "Send Product Demo Email",
  "category": "email",
  "effects": {
    "awareness": 0.1,
    "interest": 0.05
  },
  "cost": 5,
  "duration_ticks": 1,
  "cooldown_ticks": 3,
  "prerequisites": {
    "awareness": 0.2
  },
  "success_rate": 0.7
}
```

### Path

```json
{
  "id": "uuid",
  "session_id": "uuid",
  "sequence": [
    {
      "tick": 0,
      "action_id": "action-1",
      "action_name": "Social Media Ad",
      "expected_state": {"awareness": 0.5}
    },
    {
      "tick": 5,
      "action_id": "action-2",
      "action_name": "Product Demo Email",
      "expected_state": {"awareness": 0.6, "interest": 0.5}
    }
  ],
  "total_cost": 150,
  "total_ticks": 25,
  "final_probability": 0.72,
  "constraint_violations": []
}
```

### PathCluster

```json
{
  "id": "uuid",
  "name": "Email-Heavy Paths",
  "path_count": 15,
  "avg_probability": 0.68,
  "avg_cost": 120,
  "representative_path_id": "path-uuid",
  "common_actions": ["email_demo", "email_followup", "phone_call"],
  "expandable": true
}
```

---

## Endpoints

### Compile Target Persona

```http
POST /api/v1/target/compile-persona
Content-Type: application/json
```

Compile a persona for target mode planning.

**Request Body:**

```json
{
  "project_id": "uuid",
  "persona_id": "uuid",
  "goal_state": {
    "intent": 0.9,
    "consideration": 0.8
  },
  "constraints": [
    {
      "type": "budget",
      "max_value": 500
    },
    {
      "type": "action_limit",
      "action_category": "phone",
      "max_count": 3
    }
  ]
}
```

**Response:** `201 Created`

```json
{
  "target_id": "uuid",
  "persona_id": "uuid",
  "initial_state": {
    "awareness": 0.3,
    "interest": 0.4,
    "consideration": 0.1,
    "intent": 0.05
  },
  "goal_state": {
    "intent": 0.9,
    "consideration": 0.8
  },
  "utility_profile": {
    "price_sensitivity": 0.6,
    "quality_focus": 0.8
  },
  "gap_analysis": {
    "intent": {"current": 0.05, "target": 0.9, "gap": 0.85},
    "consideration": {"current": 0.1, "target": 0.8, "gap": 0.7}
  },
  "estimated_actions_needed": 8,
  "estimated_cost_range": [100, 400]
}
```

---

### Get Action Catalog

```http
GET /api/v1/target/actions/{domain}
```

Get available actions for a domain.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `domain` | string | Domain template (e.g., consumer_goods) |

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `category` | string | - | Filter by category |
| `min_effect` | float | - | Minimum effect magnitude |
| `max_cost` | float | - | Maximum cost |

**Response:**

```json
{
  "domain": "consumer_goods",
  "actions": [
    {
      "id": "email_intro",
      "name": "Introduction Email",
      "category": "email",
      "effects": {"awareness": 0.1},
      "cost": 5,
      "duration_ticks": 1
    },
    {
      "id": "phone_demo",
      "name": "Phone Demo Call",
      "category": "phone",
      "effects": {"interest": 0.2, "consideration": 0.1},
      "cost": 50,
      "duration_ticks": 2
    }
  ],
  "categories": ["email", "phone", "social", "content", "event"],
  "total": 25
}
```

---

### Generate Paths (Plan)

```http
POST /api/v1/target/plan
Content-Type: application/json
```

Generate action paths to reach goal state.

**Request Body:**

```json
{
  "target_id": "uuid",
  "planner_config": {
    "max_paths": 50,
    "max_depth": 15,
    "min_probability": 0.3,
    "optimization": "probability",
    "use_clustering": true,
    "cluster_threshold": 0.6
  },
  "action_filters": {
    "categories": ["email", "phone", "content"],
    "excluded_actions": ["cold_call"]
  }
}
```

**Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_paths` | int | 50 | Soft limit on paths generated |
| `max_depth` | int | 20 | Maximum actions per path |
| `min_probability` | float | 0.2 | Minimum success probability |
| `optimization` | string | "probability" | Optimize for: probability, cost, time |
| `use_clustering` | bool | true | Group similar paths |

**Response:**

```json
{
  "session_id": "uuid",
  "target_id": "uuid",
  "planning_time_ms": 1250,
  "paths_generated": 45,
  "clusters": [
    {
      "id": "cluster-1",
      "name": "Email-Focused Strategy",
      "path_count": 18,
      "avg_probability": 0.72,
      "avg_cost": 85,
      "avg_ticks": 20,
      "representative_path": {
        "id": "path-uuid",
        "sequence": [
          {"tick": 0, "action": "email_intro"},
          {"tick": 3, "action": "content_blog"},
          {"tick": 7, "action": "email_demo"}
        ]
      }
    },
    {
      "id": "cluster-2",
      "name": "Phone-Heavy Strategy",
      "path_count": 12,
      "avg_probability": 0.68,
      "avg_cost": 180,
      "avg_ticks": 15
    }
  ],
  "best_path": {
    "id": "best-path-uuid",
    "probability": 0.78,
    "cost": 120,
    "total_ticks": 18
  }
}
```

---

### Expand Path Cluster

```http
POST /api/v1/target/expand-cluster
Content-Type: application/json
```

**Request Body:**

```json
{
  "session_id": "uuid",
  "cluster_id": "cluster-1",
  "max_paths": 10
}
```

**Response:**

```json
{
  "cluster_id": "cluster-1",
  "paths": [
    {
      "id": "path-1",
      "probability": 0.75,
      "cost": 90,
      "total_ticks": 22,
      "sequence": [
        {"tick": 0, "action_id": "email_intro", "action_name": "Introduction Email"},
        {"tick": 3, "action_id": "content_case", "action_name": "Case Study Share"},
        {"tick": 8, "action_id": "email_demo", "action_name": "Demo Request Email"}
      ]
    }
  ],
  "remaining_count": 8,
  "has_more": true
}
```

---

### Get Path Details

```http
GET /api/v1/target/paths/{session_id}/{path_id}
```

**Response:**

```json
{
  "id": "path-uuid",
  "session_id": "uuid",
  "target_id": "uuid",
  "probability": 0.75,
  "cost": 120,
  "total_ticks": 22,
  "sequence": [
    {
      "step": 1,
      "tick": 0,
      "action": {
        "id": "email_intro",
        "name": "Introduction Email",
        "category": "email",
        "cost": 5
      },
      "state_before": {"awareness": 0.3, "interest": 0.4},
      "state_after": {"awareness": 0.4, "interest": 0.42},
      "probability": 0.95
    },
    {
      "step": 2,
      "tick": 5,
      "action": {
        "id": "phone_demo",
        "name": "Phone Demo",
        "category": "phone",
        "cost": 50
      },
      "state_before": {"awareness": 0.4, "interest": 0.42},
      "state_after": {"awareness": 0.5, "interest": 0.6, "consideration": 0.3},
      "probability": 0.70
    }
  ],
  "final_state": {
    "awareness": 0.9,
    "interest": 0.85,
    "consideration": 0.8,
    "intent": 0.75
  },
  "constraint_violations": [],
  "created_at": "2026-01-09T12:00:00Z"
}
```

---

### Branch Path to Universe Map

```http
POST /api/v1/target/branch
Content-Type: application/json
```

Create a Universe Map node from a target path to explore population-level effects.

**Request Body:**

```json
{
  "session_id": "uuid",
  "path_id": "path-uuid",
  "parent_node_id": "uuid",
  "segment_to_apply": "early_adopters",
  "name": "Email Strategy Rollout"
}
```

**Response:** `201 Created`

```json
{
  "node": {
    "id": "new-node-uuid",
    "parent_node_id": "parent-uuid",
    "name": "Email Strategy Rollout",
    "status": "pending"
  },
  "event_bundle": {
    "id": "bundle-uuid",
    "event_count": 5,
    "name": "Path-derived: Email Strategy"
  },
  "run": {
    "id": "run-uuid",
    "status": "queued"
  }
}
```

---

### List Planning Sessions

```http
GET /api/v1/target/sessions
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
      "id": "session-uuid",
      "target_id": "uuid",
      "persona_name": "Tech Professional",
      "paths_generated": 45,
      "best_probability": 0.78,
      "created_at": "2026-01-09T12:00:00Z"
    }
  ],
  "total": 10
}
```

---

## Error Responses

### 400 Bad Request - Invalid Goal State

```json
{
  "detail": "Goal state contains invalid variables",
  "status_code": 400,
  "error_code": "INVALID_GOAL_STATE",
  "invalid_variables": ["nonexistent_metric"],
  "available_variables": ["awareness", "interest", "consideration", "intent"]
}
```

### 400 Bad Request - Constraint Violation

```json
{
  "detail": "Constraints cannot be satisfied",
  "status_code": 400,
  "error_code": "UNSATISFIABLE_CONSTRAINTS",
  "analysis": {
    "min_cost_to_goal": 250,
    "budget_constraint": 100,
    "message": "Budget constraint too restrictive for goal state"
  }
}
```

### 404 Not Found

```json
{
  "detail": "Planning session not found",
  "status_code": 404,
  "error_code": "SESSION_NOT_FOUND"
}
```

### 422 Unprocessable Entity - No Valid Paths

```json
{
  "detail": "No valid paths found to goal state",
  "status_code": 422,
  "error_code": "NO_VALID_PATHS",
  "suggestions": [
    "Relax budget constraint (current: $100, suggested: $200)",
    "Increase time horizon (current: 30 ticks, suggested: 50)",
    "Lower goal state threshold (current: 0.9, suggested: 0.7)"
  ]
}
```

---

## Examples

### Full Target Mode Workflow

```python
import httpx

client = httpx.Client(
    base_url="https://api.agentverse.ai/api/v1",
    headers={"Authorization": f"Bearer {token}"}
)

# 1. Compile target persona
target = client.post("/target/compile-persona", json={
    "project_id": "project-uuid",
    "persona_id": "persona-uuid",
    "goal_state": {"intent": 0.8},
    "constraints": [
        {"type": "budget", "max_value": 300},
        {"type": "time", "max_ticks": 30}
    ]
}).json()

print(f"Gap to goal: {target['gap_analysis']['intent']['gap']}")

# 2. Get available actions
actions = client.get(
    "/target/actions/consumer_goods",
    params={"max_cost": 100}
).json()

print(f"Available actions: {len(actions['actions'])}")

# 3. Generate paths
plan = client.post("/target/plan", json={
    "target_id": target['target_id'],
    "planner_config": {
        "max_paths": 50,
        "optimization": "probability",
        "use_clustering": True
    }
}).json()

print(f"Generated {plan['paths_generated']} paths")
print(f"Best path probability: {plan['best_path']['probability']:.0%}")

# 4. Explore a cluster
cluster = plan['clusters'][0]
expanded = client.post("/target/expand-cluster", json={
    "session_id": plan['session_id'],
    "cluster_id": cluster['id']
}).json()

# 5. Branch to Universe Map
branch = client.post("/target/branch", json={
    "session_id": plan['session_id'],
    "path_id": plan['best_path']['id'],
    "parent_node_id": "root-node-uuid",
    "segment_to_apply": "early_adopters"
}).json()

print(f"Created node: {branch['node']['id']}")
```

### Compare Path Strategies

```python
# Generate paths with different optimizations
prob_plan = client.post("/target/plan", json={
    "target_id": target_id,
    "planner_config": {"optimization": "probability"}
}).json()

cost_plan = client.post("/target/plan", json={
    "target_id": target_id,
    "planner_config": {"optimization": "cost"}
}).json()

time_plan = client.post("/target/plan", json={
    "target_id": target_id,
    "planner_config": {"optimization": "time"}
}).json()

print("Strategy Comparison:")
print(f"Probability-optimized: {prob_plan['best_path']['probability']:.0%} @ ${prob_plan['best_path']['cost']}")
print(f"Cost-optimized: {cost_plan['best_path']['probability']:.0%} @ ${cost_plan['best_path']['cost']}")
print(f"Time-optimized: {time_plan['best_path']['probability']:.0%} in {time_plan['best_path']['total_ticks']} ticks")
```

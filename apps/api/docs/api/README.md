# AgentVerse API Documentation

**Version:** 1.0.0
**Base URL:** `https://api.agentverse.ai/api/v1`
**Last Updated:** 2026-01-09

---

## Overview

AgentVerse is an AI-powered simulation platform for predicting human decisions at scale. The API provides endpoints for managing simulation projects, running predictions, and analyzing results through the Universe Map.

### Key Concepts

| Concept | Description |
|---------|-------------|
| **ProjectSpec** | A simulation project configuration with domain, personas, and settings |
| **Persona** | Canonical profile of a simulated human agent |
| **Node** | A point in the Universe Map representing a possible future state |
| **Run** | An execution of the simulation engine producing outcomes |
| **Telemetry** | Time-series data from simulation runs (read-only) |
| **EventScript** | Pre-compiled intervention that modifies simulation state |

### Core Constraints

1. **Fork-not-Mutate (C1)**: Any change creates a new Node; history is never modified
2. **On-Demand Execution (C2)**: Simulations run only when requested
3. **Replay is Read-Only (C3)**: Telemetry queries never trigger simulations
4. **Auditable Artifacts (C4)**: All outputs are versioned and traceable
5. **LLMs as Compilers (C5)**: AI compiles events once; execution is deterministic
6. **Multi-Tenancy (C6)**: All resources are isolated by tenant

---

## Authentication

All API endpoints (except health checks) require authentication via JWT bearer token.

### Obtaining a Token

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "your-password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": "user-uuid",
    "email": "user@example.com",
    "full_name": "John Doe"
  }
}
```

### Using the Token

Include the token in the `Authorization` header:

```http
GET /api/v1/project-specs
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

---

## Rate Limits

| Endpoint Type | Limit | Window |
|---------------|-------|--------|
| Standard API | 100 requests | per minute |
| Simulation Runs | 10 concurrent | per tenant |
| Ask (Event Compiler) | 20 requests | per minute |
| Deep Search | 5 requests | per minute |
| Exports | 10 requests | per minute |

When rate limited, the API returns `429 Too Many Requests` with a `Retry-After` header.

---

## API Endpoints

### Project Specs

Manage simulation projects.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/project-specs` | List all projects |
| `POST` | `/project-specs` | Create a new project |
| `GET` | `/project-specs/{id}` | Get project details |
| `PUT` | `/project-specs/{id}` | Update a project |
| `DELETE` | `/project-specs/{id}` | Delete a project |
| `GET` | `/project-specs/{id}/stats` | Get project statistics |
| `POST` | `/project-specs/{id}/duplicate` | Duplicate a project |
| `POST` | `/project-specs/{id}/runs` | Create a run for project |

### Nodes (Universe Map)

Navigate and fork the multiverse tree.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/nodes/universe-map/{project_id}` | Get full graph for project |
| `GET` | `/nodes/{id}` | Get node details |
| `POST` | `/nodes/fork` | Fork a node with changes |
| `GET` | `/nodes/{id}/children` | List child nodes |
| `GET` | `/nodes/{id}/edges` | List edges from node |
| `GET` | `/nodes/compare` | Compare 2-4 nodes |
| `GET` | `/nodes/{id}/path-analysis` | Analyze path from root |

### Runs

Execute simulations and track progress.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/runs` | List runs (filter by project, status) |
| `POST` | `/runs` | Create a new run |
| `GET` | `/runs/{id}` | Get run details |
| `POST` | `/runs/{id}/start` | Start a pending run |
| `POST` | `/runs/{id}/cancel` | Cancel a running run |
| `GET` | `/runs/{id}/progress` | SSE stream of progress |
| `GET` | `/runs/{id}/results` | Get run results |
| `POST` | `/runs/batch` | Create multiple runs |

### Telemetry (Read-Only)

Query simulation time-series data. **Never triggers simulations (C3)**.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/telemetry/{node_id}` | Get telemetry index |
| `GET` | `/telemetry/{node_id}/slice` | Get tick range slice |
| `GET` | `/telemetry/{node_id}/keyframe/{tick}` | Get keyframe at tick |
| `GET` | `/telemetry/{node_id}/agent/{agent_id}` | Get agent history |
| `GET` | `/telemetry/{node_id}/events` | Get event triggers |
| `GET` | `/telemetry/{node_id}/stream` | SSE stream chunks |

### Ask (Event Compiler)

Natural language to simulation events.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/ask/compile` | Compile NL prompt to events |
| `POST` | `/ask/expand-cluster` | Expand a scenario cluster |
| `POST` | `/ask/execute-scenario` | Execute a compiled scenario |
| `GET` | `/ask/history/{project_id}` | Get compilation history |

### Target Mode

Individual-focused path planning.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/target/compile-persona` | Compile target persona |
| `GET` | `/target/actions/{domain}` | Get action catalog |
| `POST` | `/target/plan` | Generate action paths |
| `POST` | `/target/branch` | Branch path to Universe Map |
| `GET` | `/target/paths/{session_id}` | Get planned paths |

### Event Scripts

Manage compiled event interventions.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/event-scripts` | List event scripts |
| `POST` | `/event-scripts` | Create event script |
| `GET` | `/event-scripts/{id}` | Get event script |
| `PUT` | `/event-scripts/{id}` | Update event script |
| `DELETE` | `/event-scripts/{id}` | Delete event script |
| `POST` | `/event-scripts/{id}/execute` | Execute event script |
| `GET` | `/event-scripts/bundles` | List event bundles |
| `POST` | `/event-scripts/bundles` | Create event bundle |

### 2D Replay (Read-Only)

Playback simulation visualizations. **Never triggers simulations (C3)**.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/replay/load` | Load replay data |
| `GET` | `/replay/{session_id}/state` | Get state at tick |
| `GET` | `/replay/{session_id}/chunk` | Get chunk of ticks |
| `POST` | `/replay/{session_id}/seek` | Seek to tick |

### Exports

Export data with privacy controls.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/exports` | Create export job |
| `GET` | `/exports/{id}` | Get export status |
| `GET` | `/exports/{id}/download` | Download export file |
| `GET` | `/exports` | List exports |
| `GET` | `/exports/formats` | Get available formats |
| `GET` | `/exports/redaction-rules` | Get redaction rules |

### Privacy & Compliance

GDPR/CCPA compliance endpoints.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/privacy/requests` | Create privacy request |
| `GET` | `/privacy/requests` | List my requests |
| `POST` | `/privacy/delete-my-data` | Request data deletion |
| `POST` | `/privacy/export-my-data` | Request data export |
| `GET` | `/privacy/retention/policies` | Get retention policies |
| `GET` | `/privacy/compliance/rights` | Get available rights |

### Health & Metrics

System health and observability.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Basic health check |
| `GET` | `/health/ready` | Readiness probe |
| `GET` | `/health/live` | Liveness probe |
| `GET` | `/metrics` | Prometheus metrics |

---

## Common Response Formats

### Success Response

```json
{
  "id": "uuid",
  "created_at": "2026-01-09T12:00:00Z",
  "updated_at": "2026-01-09T12:00:00Z",
  ...
}
```

### Paginated Response

```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "size": 20,
  "pages": 5
}
```

### Error Response

```json
{
  "detail": "Error message",
  "status_code": 400,
  "error_code": "VALIDATION_ERROR"
}
```

---

## WebSocket Connections

Real-time updates via WebSocket.

### General Connection

```
ws://api.agentverse.ai/ws
```

### Run-Specific Connection

```
ws://api.agentverse.ai/ws/{run_id}
```

### Message Types

```json
// Run progress
{
  "type": "run_progress",
  "run_id": "uuid",
  "tick": 45,
  "total_ticks": 100,
  "agents_processed": 5000
}

// Run completed
{
  "type": "run_completed",
  "run_id": "uuid",
  "status": "succeeded",
  "node_id": "uuid"
}

// Run failed
{
  "type": "run_failed",
  "run_id": "uuid",
  "error": "Error message"
}
```

---

## SDKs and Examples

### Python

```python
import httpx

client = httpx.Client(
    base_url="https://api.agentverse.ai/api/v1",
    headers={"Authorization": f"Bearer {token}"}
)

# List projects
projects = client.get("/project-specs").json()

# Create a run
run = client.post("/runs", json={
    "project_id": "project-uuid",
    "name": "My Simulation",
    "mode": "society",
    "config": {
        "ticks": 100,
        "seed": 42
    }
}).json()

# Start the run
client.post(f"/runs/{run['id']}/start")
```

### JavaScript/TypeScript

```typescript
const response = await fetch('https://api.agentverse.ai/api/v1/project-specs', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});
const projects = await response.json();

// Fork a node
const fork = await fetch('https://api.agentverse.ai/api/v1/nodes/fork', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    parent_node_id: 'node-uuid',
    variable_deltas: {
      economy_confidence: 0.1,
      media_sentiment: -0.2
    },
    name: 'Optimistic Scenario'
  })
});
```

---

## Changelog

### v1.0.0 (2026-01-09)

- Initial release
- Core simulation engine (Society, Target, Hybrid modes)
- Universe Map with fork mechanics
- Event Compiler (Ask feature)
- 2D Replay visualization
- GDPR/CCPA compliance endpoints
- Load testing validated at 500 RPS

---

## Support

- **Documentation:** https://docs.agentverse.ai
- **API Status:** https://status.agentverse.ai
- **Support Email:** support@agentverse.ai

# Project Specs API

**Tag:** `Project Specs`
**Base Path:** `/api/v1/project-specs`

Project Specs define simulation projects with their configuration, domain template, and settings.

---

## Data Model

### ProjectSpec

```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "name": "Consumer Sentiment Study",
  "description": "Analyzing brand perception shifts",
  "domain": "consumer_goods",
  "prediction_core": "society",
  "default_horizon_days": 30,
  "privacy_level": "internal",
  "policy_flags": {
    "allow_exports": true,
    "allow_sharing": true,
    "require_approval": false
  },
  "created_at": "2026-01-09T12:00:00Z",
  "updated_at": "2026-01-09T12:00:00Z",
  "schema_version": "1.0.0"
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | uuid | auto | Unique identifier |
| `tenant_id` | uuid | auto | Tenant isolation key |
| `name` | string | yes | Project name (max 200 chars) |
| `description` | string | no | Project description |
| `domain` | string | yes | Domain template (see below) |
| `prediction_core` | enum | yes | `society`, `target`, or `hybrid` |
| `default_horizon_days` | int | no | Default simulation horizon (default: 30) |
| `privacy_level` | enum | no | `public`, `internal`, `confidential`, `restricted` |
| `policy_flags` | object | no | Feature flags for the project |
| `schema_version` | string | auto | Schema version for migrations |

### Domain Templates

| Domain | Description |
|--------|-------------|
| `consumer_goods` | FMCG, retail, brand perception |
| `financial_services` | Banking, insurance, investment |
| `healthcare` | Patient behavior, treatment adherence |
| `technology` | Software adoption, product launches |
| `automotive` | Vehicle purchase decisions |
| `media_entertainment` | Content consumption, subscription |
| `custom` | User-defined domain |

---

## Endpoints

### List Projects

```http
GET /api/v1/project-specs
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skip` | int | 0 | Pagination offset |
| `limit` | int | 20 | Items per page (max 100) |
| `search` | string | - | Search by name |
| `domain` | string | - | Filter by domain |
| `prediction_core` | string | - | Filter by core type |

**Response:**

```json
{
  "items": [
    {
      "id": "uuid",
      "name": "Consumer Sentiment Study",
      "domain": "consumer_goods",
      "prediction_core": "society",
      "created_at": "2026-01-09T12:00:00Z"
    }
  ],
  "total": 15,
  "page": 1,
  "size": 20,
  "pages": 1
}
```

---

### Create Project

```http
POST /api/v1/project-specs
Content-Type: application/json
```

**Request Body:**

```json
{
  "name": "Brand Launch Simulation",
  "description": "Predicting market response to new product",
  "domain": "consumer_goods",
  "prediction_core": "society",
  "default_horizon_days": 60,
  "privacy_level": "internal",
  "policy_flags": {
    "allow_exports": true,
    "allow_sharing": true,
    "require_approval": false
  }
}
```

**Response:** `201 Created`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "tenant_id": "tenant-uuid",
  "name": "Brand Launch Simulation",
  "description": "Predicting market response to new product",
  "domain": "consumer_goods",
  "prediction_core": "society",
  "default_horizon_days": 60,
  "privacy_level": "internal",
  "policy_flags": {
    "allow_exports": true,
    "allow_sharing": true,
    "require_approval": false
  },
  "created_at": "2026-01-09T12:00:00Z",
  "updated_at": "2026-01-09T12:00:00Z",
  "schema_version": "1.0.0"
}
```

---

### Get Project

```http
GET /api/v1/project-specs/{id}
```

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | uuid | Project ID |

**Response:** `200 OK`

Returns the full ProjectSpec object.

---

### Update Project

```http
PUT /api/v1/project-specs/{id}
Content-Type: application/json
```

**Request Body:**

```json
{
  "name": "Updated Project Name",
  "description": "Updated description",
  "default_horizon_days": 90
}
```

**Response:** `200 OK`

Returns the updated ProjectSpec object.

---

### Delete Project

```http
DELETE /api/v1/project-specs/{id}
```

**Response:** `204 No Content`

---

### Get Project Statistics

```http
GET /api/v1/project-specs/{id}/stats
```

**Response:**

```json
{
  "project_id": "uuid",
  "node_count": 45,
  "run_count": 120,
  "completed_runs": 115,
  "failed_runs": 5,
  "persona_count": 10000,
  "last_run_at": "2026-01-09T10:30:00Z",
  "root_node_id": "root-node-uuid",
  "reliability_score": 0.85
}
```

---

### Duplicate Project

```http
POST /api/v1/project-specs/{id}/duplicate
Content-Type: application/json
```

**Request Body:**

```json
{
  "name": "Copy of Original Project",
  "include_personas": true,
  "include_event_scripts": true,
  "include_nodes": false
}
```

**Response:** `201 Created`

Returns the new ProjectSpec object.

---

### Create Run for Project

```http
POST /api/v1/project-specs/{id}/runs
Content-Type: application/json
```

Convenience endpoint to create a run directly from a project.

**Request Body:**

```json
{
  "name": "Baseline Simulation",
  "mode": "society",
  "config": {
    "ticks": 100,
    "seed": 42,
    "scheduler": {
      "partition_by": "region",
      "sample_rate": 1.0
    }
  },
  "parent_node_id": null
}
```

**Response:** `201 Created`

Returns the Run object. See [Runs API](./runs.md) for details.

---

## Error Responses

### 400 Bad Request

```json
{
  "detail": "Invalid domain: 'unknown'. Must be one of: consumer_goods, financial_services, healthcare, technology, automotive, media_entertainment, custom",
  "status_code": 400,
  "error_code": "VALIDATION_ERROR"
}
```

### 404 Not Found

```json
{
  "detail": "Project not found",
  "status_code": 404,
  "error_code": "NOT_FOUND"
}
```

### 403 Forbidden

```json
{
  "detail": "You don't have permission to access this project",
  "status_code": 403,
  "error_code": "PERMISSION_DENIED"
}
```

---

## Examples

### Python

```python
import httpx

client = httpx.Client(
    base_url="https://api.agentverse.ai/api/v1",
    headers={"Authorization": f"Bearer {token}"}
)

# Create a project
project = client.post("/project-specs", json={
    "name": "Q1 2026 Brand Analysis",
    "domain": "consumer_goods",
    "prediction_core": "society",
    "default_horizon_days": 90
}).json()

print(f"Created project: {project['id']}")

# Get statistics
stats = client.get(f"/project-specs/{project['id']}/stats").json()
print(f"Nodes: {stats['node_count']}, Runs: {stats['run_count']}")
```

### cURL

```bash
# List projects
curl -X GET "https://api.agentverse.ai/api/v1/project-specs" \
  -H "Authorization: Bearer $TOKEN"

# Create project
curl -X POST "https://api.agentverse.ai/api/v1/project-specs" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "New Project",
    "domain": "consumer_goods",
    "prediction_core": "society"
  }'
```

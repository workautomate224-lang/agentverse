# Privacy & Compliance API

**Tag:** `Privacy`
**Base Path:** `/api/v1/privacy`

The Privacy API provides GDPR/CCPA compliance endpoints for data subject requests, retention policies, and user rights management.

---

## Core Concepts

### Supported Regulations

| Regulation | Region | Key Rights |
|------------|--------|------------|
| GDPR | EU/EEA | Access, Rectification, Erasure, Portability, Object |
| CCPA | California | Know, Delete, Opt-Out, Non-Discrimination |
| LGPD | Brazil | Access, Correction, Deletion, Portability |

### Request Types

| Type | Description | SLA |
|------|-------------|-----|
| `access` | Export user's data | 30 days |
| `erasure` | Delete user's data | 30 days |
| `rectification` | Correct inaccurate data | 14 days |
| `portability` | Machine-readable export | 30 days |
| `objection` | Object to processing | 7 days |
| `restriction` | Restrict processing | 7 days |

### Request Lifecycle

```
submitted → pending_verification → in_progress → completed/rejected
```

---

## Data Model

### PrivacyRequest

```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "user_id": "uuid",
  "request_type": "erasure",
  "status": "in_progress",
  "regulation": "gdpr",
  "subject_email": "user@example.com",
  "scope": {
    "include_simulations": true,
    "include_personas": true,
    "include_exports": true,
    "include_audit_logs": false
  },
  "verification": {
    "method": "email",
    "verified_at": "2026-01-09T12:00:00Z",
    "verified_by": "automated"
  },
  "processing": {
    "started_at": "2026-01-09T12:05:00Z",
    "items_processed": 150,
    "items_total": 200
  },
  "deadline": "2026-02-08T12:00:00Z",
  "created_at": "2026-01-09T12:00:00Z",
  "completed_at": null
}
```

### RetentionPolicy

```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "name": "Standard Retention",
  "is_default": true,
  "rules": [
    {
      "data_type": "simulation_runs",
      "retention_days": 365,
      "action": "delete"
    },
    {
      "data_type": "telemetry",
      "retention_days": 180,
      "action": "anonymize"
    },
    {
      "data_type": "audit_logs",
      "retention_days": 730,
      "action": "archive"
    },
    {
      "data_type": "exports",
      "retention_days": 30,
      "action": "delete"
    }
  ],
  "created_at": "2026-01-01T00:00:00Z"
}
```

### ComplianceRight

```json
{
  "id": "access",
  "name": "Right of Access",
  "description": "Obtain confirmation and copy of personal data",
  "regulations": ["gdpr", "ccpa", "lgpd"],
  "sla_days": 30,
  "requires_verification": true,
  "available": true
}
```

---

## Endpoints

### Create Privacy Request

```http
POST /api/v1/privacy/requests
Content-Type: application/json
```

**Request Body:**

```json
{
  "request_type": "access",
  "regulation": "gdpr",
  "subject_email": "user@example.com",
  "scope": {
    "include_simulations": true,
    "include_personas": true,
    "include_exports": true
  },
  "reason": "Subject access request under GDPR Article 15"
}
```

**Response:** `201 Created`

```json
{
  "id": "request-uuid",
  "request_type": "access",
  "status": "pending_verification",
  "subject_email": "user@example.com",
  "verification_required": true,
  "verification_method": "email",
  "deadline": "2026-02-08T12:00:00Z",
  "created_at": "2026-01-09T12:00:00Z"
}
```

---

### List Privacy Requests

```http
GET /api/v1/privacy/requests
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `status` | string | - | Filter by status |
| `request_type` | string | - | Filter by type |
| `skip` | int | 0 | Pagination offset |
| `limit` | int | 20 | Items per page |

**Response:**

```json
{
  "items": [
    {
      "id": "uuid",
      "request_type": "access",
      "status": "completed",
      "subject_email": "user@example.com",
      "created_at": "2026-01-05T12:00:00Z",
      "completed_at": "2026-01-08T12:00:00Z"
    }
  ],
  "total": 5
}
```

---

### Get Privacy Request

```http
GET /api/v1/privacy/requests/{id}
```

**Response:**

Returns the full PrivacyRequest object with processing details.

---

### Cancel Privacy Request

```http
POST /api/v1/privacy/requests/{id}/cancel
```

Cancel a pending request (before processing starts).

**Response:**

```json
{
  "id": "request-uuid",
  "status": "cancelled",
  "message": "Request cancelled successfully"
}
```

---

## User Self-Service

### Request Data Deletion

```http
POST /api/v1/privacy/delete-my-data
Content-Type: application/json
```

User requests deletion of their own data.

**Request Body:**

```json
{
  "confirm": true,
  "reason": "Closing account",
  "scope": {
    "include_simulations": true,
    "include_personas": true,
    "include_exports": true,
    "include_account": false
  }
}
```

**Response:**

```json
{
  "request_id": "uuid",
  "status": "pending_verification",
  "verification_email_sent": true,
  "estimated_completion": "2026-02-08T12:00:00Z",
  "data_to_delete": {
    "simulations": 15,
    "personas": 1200,
    "exports": 8,
    "total_storage_mb": 256
  }
}
```

---

### Request Data Export

```http
POST /api/v1/privacy/export-my-data
Content-Type: application/json
```

User requests export of their personal data.

**Request Body:**

```json
{
  "format": "json",
  "scope": {
    "include_profile": true,
    "include_simulations": true,
    "include_personas": true,
    "include_activity_log": true
  }
}
```

**Response:**

```json
{
  "request_id": "uuid",
  "status": "pending",
  "estimated_completion": "2026-01-12T12:00:00Z",
  "export_format": "json",
  "estimated_size_mb": 45
}
```

---

### Get My Data Summary

```http
GET /api/v1/privacy/my-data
```

Get summary of what data is stored for the current user.

**Response:**

```json
{
  "user_id": "uuid",
  "data_summary": {
    "profile": {
      "exists": true,
      "last_updated": "2026-01-09T10:00:00Z"
    },
    "projects": {
      "count": 5,
      "oldest": "2025-06-01T00:00:00Z",
      "newest": "2026-01-08T00:00:00Z"
    },
    "simulations": {
      "count": 45,
      "total_runs": 120
    },
    "personas_created": 5000,
    "exports": {
      "count": 12,
      "total_size_mb": 156
    },
    "activity_logs": {
      "count": 1500,
      "oldest": "2025-06-01T00:00:00Z"
    }
  },
  "retention_policy": {
    "name": "Standard Retention",
    "simulation_retention_days": 365,
    "export_retention_days": 30
  }
}
```

---

## Retention Policies

### Get Retention Policies

```http
GET /api/v1/privacy/retention/policies
```

**Response:**

```json
{
  "policies": [
    {
      "id": "uuid",
      "name": "Standard Retention",
      "is_default": true,
      "rules": [
        {
          "data_type": "simulation_runs",
          "retention_days": 365,
          "action": "delete"
        },
        {
          "data_type": "telemetry",
          "retention_days": 180,
          "action": "anonymize"
        }
      ]
    }
  ],
  "active_policy": "uuid"
}
```

---

### Get Retention Policy Details

```http
GET /api/v1/privacy/retention/policies/{id}
```

**Response:**

Returns the full RetentionPolicy object.

---

### Get Data Expiration Schedule

```http
GET /api/v1/privacy/retention/schedule
```

See what data is scheduled for deletion/anonymization.

**Response:**

```json
{
  "upcoming_actions": [
    {
      "date": "2026-01-15",
      "data_type": "exports",
      "action": "delete",
      "items_count": 3,
      "size_mb": 45
    },
    {
      "date": "2026-02-01",
      "data_type": "telemetry",
      "action": "anonymize",
      "items_count": 15,
      "size_mb": 500
    }
  ],
  "total_scheduled_for_deletion_mb": 245
}
```

---

## Compliance Rights

### Get Available Rights

```http
GET /api/v1/privacy/compliance/rights
```

Get available privacy rights based on user's region.

**Response:**

```json
{
  "detected_region": "EU",
  "applicable_regulation": "gdpr",
  "rights": [
    {
      "id": "access",
      "name": "Right of Access",
      "description": "Obtain confirmation and copy of personal data",
      "sla_days": 30,
      "available": true
    },
    {
      "id": "erasure",
      "name": "Right to Erasure",
      "description": "Request deletion of personal data",
      "sla_days": 30,
      "available": true
    },
    {
      "id": "rectification",
      "name": "Right to Rectification",
      "description": "Correct inaccurate personal data",
      "sla_days": 14,
      "available": true
    },
    {
      "id": "portability",
      "name": "Right to Data Portability",
      "description": "Receive data in machine-readable format",
      "sla_days": 30,
      "available": true
    },
    {
      "id": "objection",
      "name": "Right to Object",
      "description": "Object to processing of personal data",
      "sla_days": 7,
      "available": true
    }
  ]
}
```

---

### Get Consent Status

```http
GET /api/v1/privacy/consent
```

**Response:**

```json
{
  "user_id": "uuid",
  "consents": [
    {
      "purpose": "simulation_processing",
      "granted": true,
      "granted_at": "2025-06-01T00:00:00Z",
      "expires_at": null
    },
    {
      "purpose": "marketing_communications",
      "granted": false,
      "withdrawn_at": "2025-09-15T00:00:00Z"
    },
    {
      "purpose": "analytics",
      "granted": true,
      "granted_at": "2025-06-01T00:00:00Z"
    }
  ],
  "last_reviewed": "2025-12-01T00:00:00Z"
}
```

---

### Update Consent

```http
PUT /api/v1/privacy/consent
Content-Type: application/json
```

**Request Body:**

```json
{
  "consents": [
    {
      "purpose": "marketing_communications",
      "granted": false
    }
  ]
}
```

**Response:**

```json
{
  "updated": ["marketing_communications"],
  "effective_immediately": true
}
```

---

## Error Responses

### 400 Bad Request - Invalid Request Type

```json
{
  "detail": "Invalid request type",
  "status_code": 400,
  "error_code": "INVALID_REQUEST_TYPE",
  "available_types": ["access", "erasure", "rectification", "portability", "objection", "restriction"]
}
```

### 403 Forbidden - Verification Required

```json
{
  "detail": "Email verification required before processing",
  "status_code": 403,
  "error_code": "VERIFICATION_REQUIRED",
  "verification_email_sent": true
}
```

### 409 Conflict - Duplicate Request

```json
{
  "detail": "A similar request is already in progress",
  "status_code": 409,
  "error_code": "DUPLICATE_REQUEST",
  "existing_request_id": "uuid",
  "existing_request_status": "in_progress"
}
```

### 429 Too Many Requests

```json
{
  "detail": "Privacy request rate limit exceeded",
  "status_code": 429,
  "error_code": "RATE_LIMITED",
  "retry_after_hours": 24,
  "message": "Maximum 3 privacy requests per 24 hours"
}
```

---

## Examples

### Submit GDPR Access Request

```python
import httpx

client = httpx.Client(
    base_url="https://api.agentverse.ai/api/v1",
    headers={"Authorization": f"Bearer {token}"}
)

# Request data access
request = client.post("/privacy/requests", json={
    "request_type": "access",
    "regulation": "gdpr",
    "subject_email": "user@example.com",
    "scope": {
        "include_simulations": True,
        "include_personas": True,
        "include_exports": True
    }
}).json()

print(f"Request created: {request['id']}")
print(f"Deadline: {request['deadline']}")
print(f"Verification required: {request['verification_required']}")
```

### Self-Service Data Export

```python
# Request my own data
export = client.post("/privacy/export-my-data", json={
    "format": "json",
    "scope": {
        "include_profile": True,
        "include_simulations": True,
        "include_personas": True,
        "include_activity_log": True
    }
}).json()

print(f"Export request: {export['request_id']}")
print(f"Estimated completion: {export['estimated_completion']}")
```

### Check Data Summary

```python
# See what data is stored
summary = client.get("/privacy/my-data").json()

print(f"Projects: {summary['data_summary']['projects']['count']}")
print(f"Simulations: {summary['data_summary']['simulations']['count']}")
print(f"Personas: {summary['data_summary']['personas_created']}")
print(f"Retention: {summary['retention_policy']['simulation_retention_days']} days")
```

### Manage Consents

```python
# Check current consents
consents = client.get("/privacy/consent").json()

for consent in consents['consents']:
    status = "Granted" if consent['granted'] else "Withdrawn"
    print(f"{consent['purpose']}: {status}")

# Withdraw marketing consent
client.put("/privacy/consent", json={
    "consents": [
        {"purpose": "marketing_communications", "granted": False}
    ]
})
```

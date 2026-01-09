# Exports API

**Tag:** `Exports`
**Base Path:** `/api/v1/exports`

The Exports API enables controlled data export with privacy controls, redaction rules, and format options. All exports respect tenant boundaries and data governance policies.

---

## Core Concepts

### Export Pipeline

```
Request → Validation → Privacy Check → Generation → Storage → Download
```

1. **Request**: User specifies data scope and format
2. **Validation**: Check permissions and quotas
3. **Privacy Check**: Apply redaction rules
4. **Generation**: Generate export file (async)
5. **Storage**: Store temporarily in S3
6. **Download**: Signed URL for download

### Privacy Levels

| Level | Description | Redaction |
|-------|-------------|-----------|
| `full` | All data included | None |
| `anonymized` | PII removed | Names, IDs hashed |
| `aggregated` | No individual data | Only aggregates |
| `summary` | Minimal output | High-level metrics only |

### Supported Formats

| Format | Extension | Use Case |
|--------|-----------|----------|
| `json` | .json | API integration |
| `csv` | .csv | Spreadsheet analysis |
| `parquet` | .parquet | Big data tools |
| `excel` | .xlsx | Business reporting |
| `pdf` | .pdf | Presentation |

---

## Data Model

### ExportJob

```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "project_id": "uuid",
  "name": "Q1 Simulation Results",
  "status": "completed",
  "export_type": "node_comparison",
  "config": {
    "node_ids": ["uuid-1", "uuid-2"],
    "format": "excel",
    "privacy_level": "anonymized",
    "include_telemetry": true,
    "include_personas": false,
    "date_range": {
      "start": "2026-01-01T00:00:00Z",
      "end": "2026-01-09T23:59:59Z"
    }
  },
  "output": {
    "file_ref": "s3://bucket/exports/uuid.xlsx",
    "file_size_bytes": 1048576,
    "row_count": 5000,
    "expires_at": "2026-01-16T12:00:00Z"
  },
  "redaction_applied": {
    "fields_redacted": ["persona_name", "agent_id"],
    "rows_filtered": 0
  },
  "timing": {
    "requested_at": "2026-01-09T12:00:00Z",
    "started_at": "2026-01-09T12:00:05Z",
    "completed_at": "2026-01-09T12:01:30Z",
    "duration_seconds": 85
  },
  "created_by": "user-uuid"
}
```

### ExportConfig

```json
{
  "format": "csv",
  "privacy_level": "anonymized",
  "include_telemetry": true,
  "include_personas": true,
  "include_events": true,
  "include_reliability": true,
  "telemetry_resolution": 5,
  "date_range": {
    "start": "2026-01-01T00:00:00Z",
    "end": "2026-01-09T23:59:59Z"
  },
  "filters": {
    "segments": ["early_adopters"],
    "regions": ["urban"],
    "min_confidence": 0.7
  }
}
```

### RedactionRule

```json
{
  "id": "uuid",
  "name": "PII Redaction",
  "description": "Remove personally identifiable information",
  "fields": [
    {
      "path": "persona.name",
      "action": "hash",
      "algorithm": "sha256"
    },
    {
      "path": "agent.id",
      "action": "replace",
      "value": "REDACTED"
    },
    {
      "path": "persona.demographics.age",
      "action": "bucket",
      "buckets": [[18, 25], [26, 35], [36, 50], [51, 100]]
    }
  ],
  "is_active": true
}
```

---

## Endpoints

### Create Export Job

```http
POST /api/v1/exports
Content-Type: application/json
```

Create a new export job (async).

**Request Body:**

```json
{
  "project_id": "uuid",
  "name": "Weekly Report Export",
  "export_type": "project_summary",
  "config": {
    "format": "excel",
    "privacy_level": "anonymized",
    "include_telemetry": true,
    "include_personas": true,
    "include_events": true,
    "telemetry_resolution": 10
  }
}
```

**Export Types:**

| Type | Description |
|------|-------------|
| `project_summary` | Full project overview |
| `node_comparison` | Compare specific nodes |
| `telemetry_dump` | Raw telemetry data |
| `persona_catalog` | Persona definitions |
| `reliability_report` | Reliability metrics |
| `audit_log` | Activity history |

**Response:** `202 Accepted`

```json
{
  "id": "export-uuid",
  "status": "pending",
  "export_type": "project_summary",
  "estimated_duration_seconds": 60,
  "position_in_queue": 3,
  "created_at": "2026-01-09T12:00:00Z"
}
```

---

### Get Export Status

```http
GET /api/v1/exports/{id}
```

**Response:**

```json
{
  "id": "export-uuid",
  "status": "completed",
  "export_type": "project_summary",
  "config": {...},
  "output": {
    "file_ref": "s3://bucket/exports/uuid.xlsx",
    "file_size_bytes": 1048576,
    "row_count": 5000,
    "expires_at": "2026-01-16T12:00:00Z"
  },
  "redaction_applied": {
    "fields_redacted": ["persona_name"],
    "rows_filtered": 0
  },
  "timing": {
    "requested_at": "2026-01-09T12:00:00Z",
    "completed_at": "2026-01-09T12:01:30Z",
    "duration_seconds": 90
  }
}
```

---

### Download Export

```http
GET /api/v1/exports/{id}/download
```

Get a signed download URL.

**Response:**

```json
{
  "download_url": "https://s3.amazonaws.com/bucket/exports/uuid.xlsx?X-Amz-Signature=...",
  "expires_at": "2026-01-09T13:00:00Z",
  "file_name": "Weekly_Report_Export.xlsx",
  "file_size_bytes": 1048576,
  "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
}
```

---

### List Exports

```http
GET /api/v1/exports
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `project_id` | uuid | - | Filter by project |
| `status` | string | - | Filter by status |
| `export_type` | string | - | Filter by type |
| `skip` | int | 0 | Pagination offset |
| `limit` | int | 20 | Items per page |

**Response:**

```json
{
  "items": [
    {
      "id": "uuid",
      "name": "Weekly Report",
      "status": "completed",
      "export_type": "project_summary",
      "format": "excel",
      "file_size_bytes": 1048576,
      "created_at": "2026-01-09T12:00:00Z",
      "expires_at": "2026-01-16T12:00:00Z"
    }
  ],
  "total": 15
}
```

---

### Cancel Export

```http
POST /api/v1/exports/{id}/cancel
```

Cancel a pending or running export.

**Response:**

```json
{
  "id": "export-uuid",
  "status": "cancelled",
  "message": "Export cancelled successfully"
}
```

---

### Delete Export

```http
DELETE /api/v1/exports/{id}
```

Delete an export and its files.

**Response:** `204 No Content`

---

## Format Options

### Get Available Formats

```http
GET /api/v1/exports/formats
```

**Response:**

```json
{
  "formats": [
    {
      "id": "json",
      "name": "JSON",
      "extension": ".json",
      "content_type": "application/json",
      "max_size_mb": 100
    },
    {
      "id": "csv",
      "name": "CSV",
      "extension": ".csv",
      "content_type": "text/csv",
      "max_size_mb": 500
    },
    {
      "id": "parquet",
      "name": "Apache Parquet",
      "extension": ".parquet",
      "content_type": "application/octet-stream",
      "max_size_mb": 1000
    },
    {
      "id": "excel",
      "name": "Microsoft Excel",
      "extension": ".xlsx",
      "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "max_size_mb": 50
    },
    {
      "id": "pdf",
      "name": "PDF Report",
      "extension": ".pdf",
      "content_type": "application/pdf",
      "max_size_mb": 25
    }
  ]
}
```

---

## Redaction Rules

### Get Redaction Rules

```http
GET /api/v1/exports/redaction-rules
```

**Response:**

```json
{
  "rules": [
    {
      "id": "pii-standard",
      "name": "Standard PII Redaction",
      "description": "Hash personal identifiers, bucket demographics",
      "is_default": true,
      "fields_affected": 12
    },
    {
      "id": "full-anonymization",
      "name": "Full Anonymization",
      "description": "Remove all identifying information",
      "is_default": false,
      "fields_affected": 25
    }
  ],
  "default_rule": "pii-standard"
}
```

### Get Redaction Rule Details

```http
GET /api/v1/exports/redaction-rules/{id}
```

**Response:**

```json
{
  "id": "pii-standard",
  "name": "Standard PII Redaction",
  "description": "Hash personal identifiers, bucket demographics",
  "fields": [
    {
      "path": "persona.name",
      "action": "hash",
      "algorithm": "sha256",
      "preserve_prefix": 3
    },
    {
      "path": "persona.email",
      "action": "redact",
      "replacement": "[EMAIL REDACTED]"
    },
    {
      "path": "persona.demographics.age",
      "action": "bucket",
      "buckets": [[18, 25], [26, 35], [36, 50], [51, 100]]
    },
    {
      "path": "persona.demographics.income",
      "action": "bucket",
      "buckets": [[0, 50000], [50001, 100000], [100001, 200000], [200001, null]]
    }
  ],
  "is_active": true,
  "created_at": "2026-01-01T00:00:00Z"
}
```

---

## Rate Limits

| Operation | Limit | Window |
|-----------|-------|--------|
| Create export | 10 | per minute |
| Concurrent exports | 3 | per tenant |
| Download | 50 | per minute |
| Max export size | 1 GB | per export |

---

## Error Responses

### 400 Bad Request - Invalid Format

```json
{
  "detail": "Invalid export format",
  "status_code": 400,
  "error_code": "INVALID_FORMAT",
  "requested_format": "docx",
  "available_formats": ["json", "csv", "parquet", "excel", "pdf"]
}
```

### 403 Forbidden - Privacy Level

```json
{
  "detail": "Privacy level 'full' requires admin role",
  "status_code": 403,
  "error_code": "PRIVACY_LEVEL_DENIED",
  "your_role": "viewer",
  "required_role": "admin"
}
```

### 413 Payload Too Large

```json
{
  "detail": "Export would exceed size limit",
  "status_code": 413,
  "error_code": "EXPORT_TOO_LARGE",
  "estimated_size_mb": 1500,
  "max_size_mb": 1000,
  "suggestion": "Apply filters or reduce telemetry resolution"
}
```

### 429 Too Many Requests

```json
{
  "detail": "Export rate limit exceeded",
  "status_code": 429,
  "error_code": "RATE_LIMITED",
  "retry_after_seconds": 30
}
```

---

## Examples

### Create and Download Export

```python
import httpx
import time

client = httpx.Client(
    base_url="https://api.agentverse.ai/api/v1",
    headers={"Authorization": f"Bearer {token}"}
)

# Create export
export = client.post("/exports", json={
    "project_id": "project-uuid",
    "name": "Monthly Analysis",
    "export_type": "project_summary",
    "config": {
        "format": "excel",
        "privacy_level": "anonymized",
        "include_telemetry": True,
        "telemetry_resolution": 10
    }
}).json()

export_id = export['id']
print(f"Export created: {export_id}")

# Poll for completion
while True:
    status = client.get(f"/exports/{export_id}").json()
    print(f"Status: {status['status']}")

    if status['status'] == 'completed':
        break
    elif status['status'] == 'failed':
        raise Exception(f"Export failed: {status.get('error')}")

    time.sleep(5)

# Download
download = client.get(f"/exports/{export_id}/download").json()
print(f"Download URL: {download['download_url']}")

# Actually download the file
response = httpx.get(download['download_url'])
with open(download['file_name'], 'wb') as f:
    f.write(response.content)

print(f"Downloaded: {download['file_name']}")
```

### Node Comparison Export

```python
# Compare specific nodes
export = client.post("/exports", json={
    "project_id": "project-uuid",
    "name": "Scenario Comparison",
    "export_type": "node_comparison",
    "config": {
        "node_ids": ["node-1", "node-2", "node-3"],
        "format": "pdf",
        "privacy_level": "summary",
        "include_reliability": True
    }
}).json()
```

### Bulk Telemetry Export

```python
# Export raw telemetry for external analysis
export = client.post("/exports", json={
    "project_id": "project-uuid",
    "name": "Telemetry Dump",
    "export_type": "telemetry_dump",
    "config": {
        "format": "parquet",
        "privacy_level": "full",
        "telemetry_resolution": 1,
        "filters": {
            "segments": ["early_adopters"],
            "min_confidence": 0.8
        }
    }
}).json()
```

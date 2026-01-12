# AgentVerse Backend Execution Flow - QA Documentation

## Test Date: January 12, 2026
## Test Type: End-to-End Backend Verification
## Test Subject: 2024 US Presidential Election Backtest

---

## 1. Infrastructure & Deployment

### 1.1 Railway Services Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Railway Platform                             │
├─────────────────────┬─────────────────────┬────────────────────┤
│   API Service       │   Worker Service    │   Redis Service    │
│   (FastAPI)         │   (Celery)          │   (Queue Broker)   │
│                     │                     │                    │
│   railway.toml      │   railway-worker    │   Managed by       │
│   Port: 8000        │   .toml             │   Railway          │
│   /health endpoint  │   No HTTP port      │                    │
└─────────────────────┴─────────────────────┴────────────────────┘
```

### 1.2 Worker Configuration (Verified)

**File: `/apps/api/railway-worker.toml`**
```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile"

[deploy]
numReplicas = 1
# NO healthcheckPath - Celery workers don't serve HTTP
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10
startCommand = "./start-worker.sh"
```

**Key Finding**: Worker services must NOT have `healthcheckPath` configured as Celery workers don't expose HTTP endpoints. Railway's process monitoring handles worker health.

---

## 2. Run Execution Flow

### 2.1 Run Lifecycle States

```
CREATED → QUEUED → RUNNING → SUCCEEDED
                          ↘ FAILED
```

### 2.2 Baseline Run Execution (Evidence)

**Run ID**: `be0208ce-98d9-4200-98b9-1717109a7787`
**Project**: 2024 US Presidential Election (`e57cae97-e1df-42e2-9b07-2c6999c1fda7`)

**API Request**:
```http
POST /api/v1/runs/{run_id}/start
Authorization: Bearer <jwt_token>
```

**Execution Timeline**:
| Timestamp | Status | Details |
|-----------|--------|---------|
| Start | CREATED | Run initialized |
| +0.1s | QUEUED | Task dispatched to Celery via Redis |
| +0.5s | RUNNING | Worker picked up task |
| +2.89s | SUCCEEDED | Simulation complete |

**Final Telemetry**:
```json
{
  "run_id": "be0208ce-98d9-4200-98b9-1717109a7787",
  "status": "SUCCEEDED",
  "total_ticks": 1000,
  "agents_count": 10,
  "execution_time_seconds": 2.89
}
```

### 2.3 Task Processing Code Path

```
1. POST /runs/{id}/start
   └── RunService.start_run()
       └── celery_app.send_task('run_simulation')
           └── Redis Queue (LPUSH)

2. Celery Worker
   └── tasks/simulation_tasks.py
       └── run_simulation(run_id)
           └── SimulationEngine.execute()
               └── AgentManager.tick() × 1000
               └── TelemetryService.record()
```

---

## 3. Fork Mechanism (C1: Fork-not-mutate)

### 3.1 Architectural Principle

**Constraint C1**: Nodes are immutable. Any modification creates a new branched node rather than mutating the original.

```
        [Baseline Node]
        depth=0, is_baseline=true
              │
              ▼
    [Trump +5% Victory Node]
    depth=1, is_baseline=false
    parent_id → Baseline
```

### 3.2 Fork Execution (Evidence)

**BUG-012 Fix Required**: The fork endpoint had a tuple unpacking error.

**Root Cause** (`/apps/api/app/services/node_service.py:405`):
```python
return child_node, edge, node_patch  # Returns 3 values
```

**Broken Code** (`/apps/api/app/api/v1/endpoints/nodes.py:432`):
```python
node, edge = await orchestrator.fork_node(...)  # Expected 2
```

**Fixed Code**:
```python
node, edge, node_patch = await orchestrator.fork_node(...)  # Now handles 3
```

**Fork API Call**:
```http
POST /api/v1/projects/{project_id}/nodes/{node_id}/fork
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "name": "Trump +5% Victory",
  "description": "What-if scenario: Trump performs 5% better in swing states"
}
```

**Response**:
```json
{
  "id": "1396551a-7ce7-4162-81c4-b2e0262536d1",
  "name": "Trump +5% Victory",
  "depth": 1,
  "is_baseline": false,
  "parent_id": "ba52e0eb-fd16-44c5-9428-e53e61a8a8bc"
}
```

### 3.3 Universe Map Structure (Verified)

**API Call**:
```http
GET /api/v1/projects/{project_id}/nodes
```

**Result** - Proper Tree Structure:
```
Nodes Retrieved: 2

Node 1 (Baseline):
  - id: ba52e0eb-fd16-44c5-9428-e53e61a8a8bc
  - name: "Baseline"
  - depth: 0
  - is_baseline: true
  - parent_id: null

Node 2 (Fork):
  - id: 1396551a-7ce7-4162-81c4-b2e0262536d1
  - name: "Trump +5% Victory"
  - depth: 1
  - is_baseline: false
  - parent_id: ba52e0eb-fd16-44c5-9428-e53e61a8a8bc (→ Baseline)
```

---

## 4. What-If Scenario Execution

### 4.1 What-If Run on Forked Node (Evidence)

**Run ID**: `ae53f257-1964-44dd-bac3-ce0ea8d99eef`
**Node**: Trump +5% Victory (`1396551a-7ce7-4162-81c4-b2e0262536d1`)

**Run Creation**:
```http
POST /api/v1/projects/{project_id}/nodes/{node_id}/runs
Content-Type: application/json

{
  "name": "What-if: Trump +5%",
  "description": "Simulation with Trump performing 5% better"
}
```

**Execution Result**:
```json
{
  "id": "ae53f257-1964-44dd-bac3-ce0ea8d99eef",
  "status": "SUCCEEDED",
  "node_id": "1396551a-7ce7-4162-81c4-b2e0262536d1",
  "started_at": "2026-01-12T...",
  "completed_at": "2026-01-12T...",
  "execution_time": 2.89
}
```

---

## 5. AI Persona Generation

### 5.1 Demographics Data Source

- **Source**: US Census Bureau American Community Survey (ACS) 5-Year Estimates
- **Confidence Level**: 95%
- **Geographic Granularity**: State-level (PUMA regions)

### 5.2 Region Code Discovery

**API Endpoint**:
```http
GET /api/v1/personas/regions
```

**Valid Region Codes**:
```json
{
  "us": {
    "name": "United States",
    "countries": ["AL", "AK", "AZ", ..., "PA", ..., "WY"]
  },
  "europe": { ... },
  "southeast_asia": { ... },
  "china": { ... }
}
```

**Note**: "country" field for US region uses state abbreviations (e.g., "PA" for Pennsylvania).

### 5.3 Persona Generation Request (Evidence)

**API Call**:
```http
POST /api/v1/personas/generate
Content-Type: application/json

{
  "count": 5,
  "region": "us",
  "country": "PA",
  "topic": "2024 US Presidential Election",
  "settings": {
    "include_psychographics": true,
    "include_behavioral": true
  }
}
```

### 5.4 Generated Personas (Sample)

**Total Generated**: 5 Pennsylvania voters

| # | Age | Ethnicity | Gender | Generation | Area | Voting Pattern | Priority Issue |
|---|-----|-----------|--------|------------|------|----------------|----------------|
| 1 | 71 | Hispanic | Male | Baby Boomer | Rural | Undecided | Economy |
| 2 | 26 | White | Male | Gen Z | Urban | Strong Partisan | Healthcare |
| 3 | 76 | White | Male | Baby Boomer | Urban | Lean Partisan | Healthcare |
| 4 | 33 | White | Male | Millennial | Rural | Undecided | Healthcare |
| 5 | 26 | Hispanic | Female | Gen Z | Urban | Independent | Environment |

**Persona Structure** (Example - Persona #1):
```json
{
  "id": "persona_pa_001",
  "demographics": {
    "age": 71,
    "gender": "male",
    "ethnicity": "hispanic",
    "education": "bachelor",
    "income_bracket": "middle",
    "location": {
      "region": "us",
      "state": "PA",
      "area_type": "rural"
    }
  },
  "psychographics": {
    "big_five": {
      "openness": 0.45,
      "conscientiousness": 0.72,
      "extraversion": 0.38,
      "agreeableness": 0.61,
      "neuroticism": 0.29
    },
    "mbti_tendency": "ISTJ",
    "values": ["family", "tradition", "security"]
  },
  "behavioral": {
    "media_consumption": ["local_news", "facebook"],
    "information_seeking": "passive",
    "social_influence_susceptibility": 0.4
  },
  "election_specific": {
    "voting_pattern": "undecided",
    "party_affiliation": "independent",
    "priority_issues": ["economy", "immigration"],
    "candidate_familiarity": {
      "trump": 0.9,
      "biden": 0.85
    }
  },
  "llm_prompt": "You are a 71-year-old Hispanic male living in rural Pennsylvania..."
}
```

---

## 6. Telemetry & Metrics Storage

### 6.1 Telemetry Data Points

Each simulation run stores:
- Tick-by-tick agent states
- Decision events
- Interaction logs
- Aggregate metrics

### 6.2 Metrics API

```http
GET /api/v1/projects/{project_id}/nodes/{node_id}/runs/{run_id}/metrics
```

**Sample Response**:
```json
{
  "run_id": "be0208ce-98d9-4200-98b9-1717109a7787",
  "summary": {
    "total_ticks": 1000,
    "total_agents": 10,
    "total_interactions": 4523,
    "avg_decision_time_ms": 2.3
  },
  "tick_data": [
    {"tick": 0, "active_agents": 10, "events": 12},
    {"tick": 1, "active_agents": 10, "events": 8},
    ...
  ]
}
```

---

## 7. Bug Fixes Applied During Testing

### BUG-012: Fork Endpoint Tuple Unpacking Error

**Symptom**:
```json
{"detail": "too many values to unpack (expected 2)"}
```

**Files Modified**:
1. `/apps/api/app/api/v1/endpoints/nodes.py` - Line 432-433
2. `/apps/api/app/services/simulation_orchestrator.py` - Line 32, 479

**Commit**: `921adc4` - "Fix BUG-012: Fork endpoint tuple unpacking error"

**Status**: ✅ FIXED AND DEPLOYED

---

## 8. Test Summary

| Test Case | Status | Evidence |
|-----------|--------|----------|
| Worker Deployment | ✅ PASS | Railway logs show worker processing tasks |
| Baseline Run Execution | ✅ PASS | Run `be0208ce...` completed in 2.89s |
| Fork Creation | ✅ PASS | Node `1396551a...` created with correct parent |
| What-If Run | ✅ PASS | Run `ae53f257...` executed on forked node |
| Universe Map Structure | ✅ PASS | Proper tree hierarchy verified |
| AI Persona Generation | ✅ PASS | 5 PA voter personas generated |
| Telemetry Storage | ✅ PASS | Metrics retrieved for completed runs |

---

## 9. Known Issues

### 9.1 Frontend Node Detail Page

**Issue**: Client-side exception when viewing node details
**Workaround**: Use API directly with Bearer token authentication
**Status**: Not fixed (frontend issue, not backend)

---

## 10. Appendix: API Authentication

### NextAuth Session Token Retrieval

For direct API calls outside the browser session:

```javascript
// In browser console while logged in:
const session = await fetch('/api/auth/session').then(r => r.json());
const token = session.accessToken;

// Use in API calls:
fetch('/api/v1/...', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});
```

---

**Document Author**: Claude Code (QA Testing)
**Last Updated**: January 12, 2026

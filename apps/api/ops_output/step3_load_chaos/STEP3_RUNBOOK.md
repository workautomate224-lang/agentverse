# Step 3: Load & Chaos Test Runbook

**Environment:** Railway STAGING
**Version:** 1.0.0
**Created:** 2026-01-10

---

## Overview

This runbook documents how to execute the Step 3 Load & Chaos validation tests for the AgentVerse staging environment.

### Test Categories

| Category | Tests | Purpose |
|----------|-------|---------|
| Load Tests | L1, L2, L3 | Validate concurrency, mixed workloads, streaming stress |
| Chaos Tests | C1, C2, C3 | Validate resilience to service restarts and failures |
| Verification | REP, Bucket | Validate data integrity and isolation |

---

## Prerequisites

### Environment Variables

```bash
# Required for chaos tests (service restarts)
export RAILWAY_TOKEN="<your-railway-token>"

# Optional: Override staging URLs
export STAGING_API_URL="https://agentverse-api-staging-production.up.railway.app"
export STAGING_WEB_URL="https://agentverse-web-staging-production.up.railway.app"
```

### Railway Token (for Chaos Tests)

To get your Railway token:
```bash
# From Railway CLI config
cat ~/.railway/config.json | jq -r '.user.token'

# Or from Railway Dashboard:
# Settings > Tokens > Create Token
```

**Note:** Without a Railway token, chaos tests will run in "simulated" mode (no actual service restarts).

### Python Dependencies

```bash
pip install aiohttp
```

---

## Running the Tests

### Full Test Suite (Recommended)

```bash
cd apps/api/ops_output/step3_load_chaos

# Run all tests
python load_chaos_runner.py --all

# With Railway token for actual chaos testing
RAILWAY_TOKEN="<token>" python load_chaos_runner.py --all
```

### Individual Test Categories

```bash
# Load tests only
python load_chaos_runner.py --load-only

# Chaos tests only
python load_chaos_runner.py --chaos-only

# Verification only
python load_chaos_runner.py --verify-only
```

---

## Test Descriptions

### Load Test L1: Universe Node Expansion Concurrency

- **Objective:** Validate system handles concurrent node expansion operations
- **Method:** 20 concurrent requests × 3 rounds = 60 total operations
- **Metrics:** P50/P95 latency, success/failure counts
- **Pass Criteria:** 0 failures, P95 < 5000ms

### Load Test L2: Calibration + Auto-Tune Mixed Workload

- **Objective:** Validate mixed workload of calibration and auto-tune jobs
- **Method:** 10 calibration + 10 auto-tune jobs concurrently
- **Metrics:** Queue backlog peak, latency percentiles
- **Pass Criteria:** 0 failures, queue backlog < 100

### Load Test L3: Replay Streaming + Export Stress

- **Objective:** Validate streaming and export operations under load
- **Method:** 10 streaming + 10 export jobs concurrently
- **Metrics:** Bucket operation failures, latency
- **Pass Criteria:** 0 bucket failures, no timeouts

### Chaos Test C1: Worker Restart Mid-Run

- **Objective:** Validate runs survive worker restarts
- **Method:** Start runs, restart worker, verify completion
- **Metrics:** Stuck runs, duplicate results
- **Pass Criteria:** 0 stuck runs, 0 duplicates

### Chaos Test C2: API Restart Mid-Stream

- **Objective:** Validate streaming survives API restarts
- **Method:** Open streams, restart API, verify reconnection
- **Metrics:** Stream failures, REP integrity
- **Pass Criteria:** Graceful failure or reconnection

### Chaos Test C3: Transient DB Failure Simulation

- **Objective:** Validate system handles DB connectivity issues
- **Method:** Test under load with DB health probes
- **Metrics:** Data corruption, stuck runs
- **Pass Criteria:** 0 data corruption, 0 stuck runs

---

## Output Files

After running, the following files are generated:

| File | Description |
|------|-------------|
| `step3_results.json` | Complete test results in JSON format |
| `step3_results.md` | Human-readable markdown report |

### JSON Schema

```json
{
  "environment": {
    "api_url": "https://...",
    "web_url": "https://...",
    "minio_url": "https://...",
    "bucket": "agentverse-staging-artifacts"
  },
  "test_started_at": "ISO8601",
  "test_completed_at": "ISO8601",
  "total_duration_seconds": 123.45,
  "load_tests": {
    "L1": { "test_id": "...", "status": "PASS", ... },
    "L2": { ... },
    "L3": { ... }
  },
  "chaos_tests": {
    "C1": { ... },
    "C2": { ... },
    "C3": { ... }
  },
  "rep_integrity_results": [...],
  "bucket_isolation_verified": true,
  "overall_status": "PASS",
  "rep_corruption_count": 0,
  "stuck_runs_count": 0,
  "graph_integrity_errors": 0
}
```

---

## Interpreting Results

### GO/NO-GO Criteria

**GO (PASS):**
- REP corruption = 0
- Stuck runs = 0
- Universe graph integrity errors = 0
- All artifacts in staging bucket

**NO-GO (FAIL):**
- Any of the above criteria not met
- Fix plan will be included in results

### Common Issues

| Issue | Possible Cause | Resolution |
|-------|---------------|------------|
| High P95 latency | Cold start, Railway scaling | Wait for warm-up, retry |
| Bucket failures | MinIO connectivity | Check storage-test endpoint |
| Service restart failed | Invalid Railway token | Regenerate token |
| Stuck runs | Worker crash | Check worker logs |

---

## Railway Service IDs

For manual operations or debugging:

| Service | ID |
|---------|-----|
| API | `8b516747-7745-431b-9a91-a2eb1cc9eab3` |
| Worker | `b6edcdd4-a1c0-4d7f-9eda-30aeb12dcf3a` |
| Web | `093ac3ad-9bb5-43c0-8028-288b4d8faf5b` |
| MinIO | `b2254168-907d-4d99-9341-5d4cff255d43` |

### Manual Service Restart

```bash
# Get Railway token
TOKEN=$(cat ~/.railway/config.json | jq -r '.user.token')

# Restart a service
curl -X POST "https://backboard.railway.app/graphql/v2" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation { serviceInstanceRedeploy(serviceId: \"SERVICE_ID\", environmentId: \"668ced2e-6da8-4b5d-a915-818580666b01\") }"
  }'
```

---

## Logs and Debugging

### View Service Logs

```bash
# Using Railway CLI
RAILWAY_TOKEN="<token>" railway logs --service agentverse-api-staging

# Or via GraphQL API
curl -X POST "https://backboard.railway.app/graphql/v2" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query { deploymentLogs(deploymentId: \"DEPLOYMENT_ID\", limit: 100) { logs { timestamp message } } }"
  }'
```

### Check Health Endpoints

```bash
# Basic health
curl https://agentverse-api-staging-production.up.railway.app/health | jq

# Full readiness (with dependencies)
curl https://agentverse-api-staging-production.up.railway.app/health/ready | jq

# Storage test
curl https://agentverse-api-staging-production.up.railway.app/health/storage-test | jq
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-10 | Initial release |

---

*This runbook is part of AgentVerse Step 3: Load & Chaos Validation*

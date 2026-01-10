# Staging Smoke Test Results

**Environment:** staging
**Test Date:** 2026-01-10
**Tester:** Automated/Manual

---

## Executive Summary

| Test Category | Status | Details |
|---------------|--------|---------|
| API Health Check | PENDING | Awaiting deployment |
| Worker Verification | PENDING | Awaiting deployment |
| Database Connectivity | PENDING | Awaiting deployment |
| Redis Connectivity | PENDING | Awaiting deployment |
| Storage Bucket Access | PENDING | Awaiting deployment |
| Web Application | PENDING | Awaiting deployment |

**Overall Status:** PENDING - Awaiting Railway deployment

---

## 1. API Health Check

### Test Command

```bash
curl -s https://agentverse-api-staging.up.railway.app/health | jq
```

### Expected Response

```json
{
  "status": "healthy",
  "environment": "staging",
  "version": "1.0.0",
  "timestamp": "2026-01-10T...",
  "checks": {
    "database": "connected",
    "redis": "connected",
    "storage": "accessible"
  }
}
```

### Actual Response

```
PENDING - Run after deployment
```

### Status: PENDING

---

## 2. Worker Verification

### Test: Check Worker Logs

```bash
# In Railway Dashboard: Services → agentverse-worker-staging → Logs
# Or via Railway CLI:
railway logs -s agentverse-worker-staging
```

### Expected Log Pattern

```
[2026-01-10 ...] celery@... ready.
[2026-01-10 ...] Connected to redis://...
[2026-01-10 ...] mingle: all alone
[2026-01-10 ...] celery@... ready.
```

### Actual Logs

```
PENDING - Run after deployment
```

### Status: PENDING

---

## 3. Database Connectivity

### Test: Run Migration Check

```bash
# SSH into API container or run via Railway
cd apps/api
alembic current
```

### Expected Output

```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
<revision_id> (head)
```

### Actual Output

```
PENDING - Run after deployment
```

### Test: Simple Query

```bash
curl -s https://agentverse-api-staging.up.railway.app/api/v1/health/db
```

### Status: PENDING

---

## 4. Redis Connectivity

### Test: Cache Ping

```bash
curl -s https://agentverse-api-staging.up.railway.app/api/v1/health/redis
```

### Expected Response

```json
{
  "redis": "connected",
  "ping": "PONG"
}
```

### Actual Response

```
PENDING - Run after deployment
```

### Test: Celery Queue Check

```bash
# Check if Celery can communicate with Redis
railway run celery -A app.worker inspect ping
```

### Status: PENDING

---

## 5. Storage Bucket Access

### Test: Write Test File

```bash
curl -X POST https://agentverse-api-staging.up.railway.app/api/v1/health/storage-write \
  -H "Content-Type: application/json" \
  -d '{"test_key": "smoke-test-2026-01-10"}'
```

### Expected Response

```json
{
  "status": "success",
  "bucket": "agentverse-staging-reps",
  "key": "smoke-test-2026-01-10",
  "written": true
}
```

### Actual Response

```
PENDING - Run after deployment
```

### Test: Read Test File

```bash
curl -s https://agentverse-api-staging.up.railway.app/api/v1/health/storage-read?key=smoke-test-2026-01-10
```

### Status: PENDING

---

## 6. Web Application

### Test: Homepage Load

```bash
curl -s -o /dev/null -w "%{http_code}" https://agentverse-web-staging.up.railway.app/
```

### Expected: `200`

### Actual Response

```
PENDING - Run after deployment
```

### Test: API Connection from Web

```bash
# Open browser to staging web URL
# Check browser console for API connection errors
# Verify NEXT_PUBLIC_API_URL points to staging API
```

### Status: PENDING

---

## 7. End-to-End Flow Test

### Test: Create and Retrieve Simulation

```bash
# 1. Create a test simulation
curl -X POST https://agentverse-api-staging.up.railway.app/api/v1/simulations \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Smoke Test Simulation",
    "mode": "society",
    "agent_count": 2,
    "step_count": 2,
    "replicate_count": 1
  }'

# 2. Check simulation status
curl https://agentverse-api-staging.up.railway.app/api/v1/simulations/{id}

# 3. Verify REP was created in staging bucket
```

### Status: PENDING

---

## Smoke Test Execution Checklist

Run these tests after Railway deployment completes:

- [ ] API health endpoint returns 200 with `environment: staging`
- [ ] Worker logs show "celery@... ready"
- [ ] Database migrations are current (`alembic current` shows head)
- [ ] Redis ping returns PONG
- [ ] Storage bucket write succeeds
- [ ] Storage bucket read succeeds
- [ ] Web homepage loads (HTTP 200)
- [ ] Web connects to staging API (no CORS errors)
- [ ] End-to-end simulation flow works

---

## Re-Test Instructions

To re-run smoke tests after issues are resolved:

```bash
# Run all smoke tests
./scripts/staging_smoke_tests.sh

# Or manually run each curl command above
```

---

## Failure Response

If any smoke test fails:

1. **Check Railway logs** for the failing service
2. **Verify environment variables** are correctly set
3. **Check service dependencies** (Postgres, Redis) are healthy
4. **Review recent commits** for breaking changes
5. **Rollback if necessary** to last known good state

---

## Sign-Off

```
Smoke Tests Completed By: ___________________
Date: ___________________
All Tests Passed: [ ] Yes  [ ] No

If No, list failing tests:
1. ___________________
2. ___________________
3. ___________________

Action Items:
1. ___________________
2. ___________________
```

---

## Post-Deployment Evidence

After deployment, update this section with actual results:

### Screenshots/Evidence to Attach

1. Railway Dashboard showing all services "Deployed"
2. API health check response JSON
3. Worker log output showing ready state
4. Storage bucket listing showing staging bucket
5. Web application loaded in browser with staging banner

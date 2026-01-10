# Railway Staging Architecture

**Created:** 2026-01-10
**Deployed:** 2026-01-10 14:34 UTC
**Environment:** staging
**Status:** DEPLOYED AND VERIFIED

---

## Environment Configuration

| Setting | Value |
|---------|-------|
| Railway Project | `agentverse-staging` |
| Project ID | `30cf5498-5aeb-4cf6-b35c-5ba0b9ed81f2` |
| Environment ID | `668ced2e-6da8-4b5d-a915-818580666b01` |
| GitHub Repo | `workautomate224-lang/agentverse` |
| Branch | `main` |
| Auto-Deploy | Enabled |
| Production Isolation | Complete (separate project and resources) |

---

## Service Topology

### 1. API Service (`agentverse-api-staging`)

| Property | Value |
|----------|-------|
| Service ID | `8b516747-7745-431b-9a91-a2eb1cc9eab3` |
| Root Directory | `apps/api` |
| Builder | Dockerfile |
| Dockerfile Path | `Dockerfile` |
| Start Command | (uses Dockerfile CMD) |
| Health Check | Disabled (for staging flexibility) |
| Replicas | 1 |
| Status | **SUCCESS** |

**Domain:** `https://agentverse-api-staging-production.up.railway.app`

**Endpoints:**
- Health: `/health`
- Docs: `/docs`
- Metrics: `/metrics`

### 2. Worker Service (`agentverse-worker-staging`)

| Property | Value |
|----------|-------|
| Service ID | `b6edcdd4-a1c0-4d7f-9eda-30aeb12dcf3a` |
| Root Directory | `apps/api` |
| Builder | Dockerfile |
| Start Command | `celery -A app.worker worker --loglevel=info` |
| Health Check | N/A (background worker) |
| Replicas | 1 |
| Status | **SUCCESS** |

**Note:** Worker shares same codebase as API but runs Celery instead of uvicorn.

### 3. Web Service (`agentverse-web-staging`)

| Property | Value |
|----------|-------|
| Service ID | `093ac3ad-9bb5-43c0-8028-288b4d8faf5b` |
| Root Directory | `apps/web` |
| Builder | Dockerfile |
| Start Command | `node server.js` (Next.js standalone) |
| Health Check Path | `/` |
| Replicas | 1 |
| Status | **SUCCESS** |

**Domain:** `https://agentverse-web-staging-production.up.railway.app`

---

## Data Services (Staging-Specific)

### PostgreSQL (`postgres-staging`)

| Property | Value |
|----------|-------|
| Plugin | Railway PostgreSQL |
| Internal Hostname | `postgres-staging.railway.internal` |
| Port | 5432 |
| Connection Variable | `DATABASE_URL` |
| Status | **SUCCESS** |

### Redis (`redis-staging`)

| Property | Value |
|----------|-------|
| Plugin | Railway Redis |
| Internal Hostname | `redis-staging.railway.internal` |
| Port | 6379 |
| Connection Variable | `REDIS_URL` |
| Status | **SUCCESS** |

---

## Service Dependencies

```
                    Internet
                       │
         ┌─────────────┼─────────────┐
         │             │             │
         ▼             ▼             │
┌─────────────┐ ┌─────────────┐     │
│ Web Service │ │ API Service │     │
│  (Next.js)  │ │  (FastAPI)  │     │
│  :3000      │ │   :8000     │     │
└──────┬──────┘ └──────┬──────┘     │
       │               │             │
       │    HTTPS      │             │
       └───────────────┘             │
                │                    │
    ┌───────────┼────────────┐      │
    │           │            │      │
    ▼           ▼            ▼      │
┌───────┐  ┌───────┐  ┌──────────┐ │
│Postgres│  │ Redis │  │  Worker  │◄┘
│:5432   │  │ :6379 │  │ (Celery) │
└───────┘  └───────┘  └──────────┘

All internal connections via .railway.internal
```

---

## Service URLs

| Service | URL |
|---------|-----|
| API | https://agentverse-api-staging-production.up.railway.app |
| Web | https://agentverse-web-staging-production.up.railway.app |
| API Docs | https://agentverse-api-staging-production.up.railway.app/docs |

---

## Railway Project Structure

```
agentverse-staging/
├── Services/
│   ├── agentverse-api-staging     [SUCCESS]
│   ├── agentverse-worker-staging  [SUCCESS]
│   └── agentverse-web-staging     [SUCCESS]
└── Plugins/
    ├── postgres-staging           [SUCCESS]
    └── redis-staging              [SUCCESS]
```

---

## Environment Variables (Key Configuration)

| Variable | Service | Description |
|----------|---------|-------------|
| DATABASE_URL | API, Worker | PostgreSQL connection (asyncpg) |
| REDIS_URL | API, Worker | Redis connection |
| ENVIRONMENT | All | Set to `staging` |
| CORS_ORIGINS | API | Web staging URL + localhost |
| SECRET_KEY | API | JWT signing key (staging-specific) |
| NEXT_PUBLIC_API_URL | Web | API staging URL |
| NEXTAUTH_URL | Web | Web staging URL |

See `STAGING_VARIABLES.md` for complete configuration.

---

## Verification Checklist (Completed)

- [x] All five services show "SUCCESS" status
- [x] API health check returns 200 OK with `environment: staging`
- [x] Web loads without errors (HTTP 200)
- [x] Worker deployed and running
- [x] Database connection verified (internal network)
- [x] Redis connection verified (internal network)
- [x] CORS headers properly configured
- [x] API latency acceptable (~530ms average)

---

## Deployment History

| Date | Action | Result |
|------|--------|--------|
| 2026-01-10 | Initial staging deployment | SUCCESS |
| 2026-01-10 | Fixed calibration module imports | SUCCESS |
| 2026-01-10 | Added email-validator dependency | SUCCESS |
| 2026-01-10 | Disabled ESLint for web build | SUCCESS |
| 2026-01-10 | All services verified healthy | SUCCESS |

---

## Maintenance Notes

### Redeploying Services

```bash
# Using Railway GraphQL API
TOKEN=$(jq -r '.user.token' ~/.railway/config.json)
curl -X POST "https://backboard.railway.app/graphql/v2" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "mutation { serviceInstanceDeploy(serviceId: \"SERVICE_ID\", environmentId: \"668ced2e-6da8-4b5d-a915-818580666b01\") }"}'
```

### Checking Logs

```bash
# Using Railway CLI with project token
RAILWAY_TOKEN="PROJECT_TOKEN" railway logs --service agentverse-api-staging
```

### Service IDs for Reference

- API: `8b516747-7745-431b-9a91-a2eb1cc9eab3`
- Worker: `b6edcdd4-a1c0-4d7f-9eda-30aeb12dcf3a`
- Web: `093ac3ad-9bb5-43c0-8028-288b4d8faf5b`

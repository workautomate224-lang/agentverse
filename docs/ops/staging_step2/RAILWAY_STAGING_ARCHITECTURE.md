# Railway Staging Architecture

**Created:** 2026-01-10
**Environment:** staging
**Purpose:** Production-like isolated environment for pre-deployment validation

---

## Environment Configuration

| Setting | Value |
|---------|-------|
| Environment Name | `staging` |
| Branch Mapping | `staging` branch |
| Auto-Deploy | Enabled on push to `staging` |
| Production Isolation | Complete (separate resources) |

---

## Service Topology

### 1. API Service (`agentverse-api-staging`)

| Property | Value |
|----------|-------|
| Root Directory | `apps/api` |
| Builder | Dockerfile |
| Dockerfile Path | `Dockerfile` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/health` |
| Health Check Timeout | 30s |
| Replicas | 1 |
| Watch Paths | `apps/api/**` |

**Domain:** `agentverse-api-staging.up.railway.app` (auto-assigned)

### 2. Worker Service (`agentverse-worker-staging`)

| Property | Value |
|----------|-------|
| Root Directory | `apps/api` |
| Builder | Dockerfile |
| Dockerfile Path | `Dockerfile` |
| Start Command | `celery -A app.worker worker --loglevel=info` |
| Health Check | N/A (background worker) |
| Replicas | 1 |
| Watch Paths | `apps/api/**` |

**Note:** Worker shares same codebase as API but runs Celery instead of uvicorn.

### 3. Web Service (`agentverse-web-staging`)

| Property | Value |
|----------|-------|
| Root Directory | `apps/web` |
| Builder | Nixpacks (auto-detected) |
| Start Command | `pnpm start` |
| Health Check Path | `/` |
| Replicas | 1 |
| Watch Paths | `apps/web/**`, `packages/**` |

**Domain:** `agentverse-staging.up.railway.app` (auto-assigned)

---

## Data Services (Staging-Specific)

### PostgreSQL (`postgres-staging`)

| Property | Value |
|----------|-------|
| Plugin | Railway PostgreSQL |
| Version | 15 |
| Connection Variable | `DATABASE_URL` |
| Purpose | Staging database (isolated from production) |

### Redis (`redis-staging`)

| Property | Value |
|----------|-------|
| Plugin | Railway Redis |
| Version | 7 |
| Connection Variable | `REDIS_URL` |
| Purpose | Celery broker + cache (staging only) |

### Storage Bucket (`storage-staging`)

| Property | Value |
|----------|-------|
| Provider | Supabase Storage or S3-compatible |
| Bucket Name | `agentverse-staging-reps` |
| Variables | `STORAGE_BUCKET_NAME`, `STORAGE_ENDPOINT`, `STORAGE_ACCESS_KEY`, `STORAGE_SECRET_KEY` |
| Purpose | REP artifact storage (staging only) |

---

## Service Dependencies

```
┌─────────────────┐
│   Web (Next.js) │
└────────┬────────┘
         │ NEXT_PUBLIC_API_URL
         ▼
┌─────────────────┐     ┌─────────────────┐
│   API (FastAPI) │────►│  Worker (Celery)│
└────────┬────────┘     └────────┬────────┘
         │                       │
    ┌────┴────┐             ┌────┴────┐
    ▼         ▼             ▼         ▼
┌───────┐ ┌───────┐    ┌───────┐ ┌─────────┐
│Postgres│ │ Redis │    │ Redis │ │ Storage │
└───────┘ └───────┘    └───────┘ └─────────┘
```

---

## Branch Mapping

| Branch | Environment | Auto-Deploy |
|--------|-------------|-------------|
| `main` | production | Yes |
| `staging` | staging | Yes |
| `develop` | (none) | No |

---

## Deployment Flow

1. Push to `staging` branch triggers Railway staging environment
2. All three services rebuild with staging-specific variables
3. Health checks verify API and Web are responding
4. Worker begins processing queue immediately

---

## Railway Project Structure

```
agentverse-staging/
├── Services/
│   ├── agentverse-api-staging
│   ├── agentverse-worker-staging
│   └── agentverse-web-staging
└── Plugins/
    ├── postgres-staging
    └── redis-staging
```

---

## Manual Setup Steps in Railway Dashboard

1. **Create Project:** New Project → Empty Project → Name: `agentverse-staging`
2. **Add PostgreSQL:** Add Plugin → PostgreSQL
3. **Add Redis:** Add Plugin → Redis
4. **Add API Service:**
   - New Service → GitHub Repo
   - Root Directory: `apps/api`
   - Branch: `staging`
   - Set Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. **Add Worker Service:**
   - New Service → GitHub Repo
   - Root Directory: `apps/api`
   - Branch: `staging`
   - Set Start Command: `celery -A app.worker worker --loglevel=info`
6. **Add Web Service:**
   - New Service → GitHub Repo
   - Root Directory: `apps/web`
   - Branch: `staging`
7. **Configure Environment Variables:** See `STAGING_VARIABLES.md`
8. **Deploy:** Trigger initial deployment

---

## Verification Checklist

- [ ] All three services show "Deployed" status
- [ ] API health check returns 200 OK
- [ ] Web loads without errors
- [ ] Worker logs show "celery@... ready"
- [ ] Database connection verified
- [ ] Redis connection verified
- [ ] Storage bucket accessible

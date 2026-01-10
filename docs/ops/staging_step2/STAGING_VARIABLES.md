# Staging Environment Variables

**Environment:** staging
**Last Updated:** 2026-01-10

---

## Variable Reference

| Variable | Scope | Source | Notes |
|----------|-------|--------|-------|
| `ENVIRONMENT` | All Services | Manual | **Must be `staging`** |
| `STAGING_BANNER` | Web | Manual | Set to `true` to show staging indicator |
| `DATABASE_URL` | API, Worker | Railway Plugin | Auto-injected by PostgreSQL plugin |
| `REDIS_URL` | API, Worker | Railway Plugin | Auto-injected by Redis plugin |
| `SECRET_KEY` | API, Worker | Manual | Unique staging secret (not production) |
| `OPENROUTER_API_KEY` | API, Worker | Manual | LLM API key (can use same as prod or separate) |
| `NEXT_PUBLIC_API_URL` | Web | Manual | Points to staging API URL |
| `STORAGE_BUCKET_NAME` | API, Worker | Manual | `agentverse-staging-reps` |
| `STORAGE_ENDPOINT` | API, Worker | Manual | Storage provider endpoint |
| `STORAGE_ACCESS_KEY` | API, Worker | Manual | Storage credentials |
| `STORAGE_SECRET_KEY` | API, Worker | Manual | Storage credentials |
| `PORT` | All Services | Railway Auto | Auto-injected by Railway |
| `RAILWAY_ENVIRONMENT` | All Services | Railway Auto | Auto-set to `staging` |

---

## Service-Specific Variables

### API Service (`agentverse-api-staging`)

```
ENVIRONMENT=staging
DATABASE_URL=${{postgres-staging.DATABASE_URL}}
REDIS_URL=${{redis-staging.REDIS_URL}}
SECRET_KEY=<staging-specific-secret>
OPENROUTER_API_KEY=<api-key>
STORAGE_BUCKET_NAME=agentverse-staging-reps
STORAGE_ENDPOINT=<storage-endpoint>
STORAGE_ACCESS_KEY=<access-key>
STORAGE_SECRET_KEY=<secret-key>
```

### Worker Service (`agentverse-worker-staging`)

```
ENVIRONMENT=staging
DATABASE_URL=${{postgres-staging.DATABASE_URL}}
REDIS_URL=${{redis-staging.REDIS_URL}}
SECRET_KEY=<staging-specific-secret>
OPENROUTER_API_KEY=<api-key>
STORAGE_BUCKET_NAME=agentverse-staging-reps
STORAGE_ENDPOINT=<storage-endpoint>
STORAGE_ACCESS_KEY=<access-key>
STORAGE_SECRET_KEY=<secret-key>
```

### Web Service (`agentverse-web-staging`)

```
ENVIRONMENT=staging
STAGING_BANNER=true
NEXT_PUBLIC_API_URL=https://agentverse-api-staging.up.railway.app
```

---

## Variable Injection Syntax

Railway supports variable references between services:

| Syntax | Example | Description |
|--------|---------|-------------|
| `${{service.VAR}}` | `${{postgres-staging.DATABASE_URL}}` | Reference another service's variable |
| `${{VAR}}` | `${{PORT}}` | Reference Railway-injected variable |

---

## Secrets Management

**CRITICAL:** Never commit secrets to this file or repository.

| Secret | Storage Location | Rotation Policy |
|--------|------------------|-----------------|
| `SECRET_KEY` | Railway Dashboard | Rotate quarterly |
| `OPENROUTER_API_KEY` | Railway Dashboard | As needed |
| `STORAGE_ACCESS_KEY` | Railway Dashboard | Rotate quarterly |
| `STORAGE_SECRET_KEY` | Railway Dashboard | Rotate quarterly |

---

## Production vs Staging Isolation

| Variable | Production Value | Staging Value | Isolated? |
|----------|------------------|---------------|-----------|
| `ENVIRONMENT` | `production` | `staging` | YES |
| `DATABASE_URL` | `postgres-prod.*` | `postgres-staging.*` | YES |
| `REDIS_URL` | `redis-prod.*` | `redis-staging.*` | YES |
| `STORAGE_BUCKET_NAME` | `agentverse-reps` | `agentverse-staging-reps` | YES |
| `SECRET_KEY` | `<prod-secret>` | `<staging-secret>` | YES |

---

## Configuration Validation

Before deploying, verify:

1. **ENVIRONMENT is set to `staging`** - Critical for code paths
2. **DATABASE_URL points to staging Postgres** - Check hostname
3. **REDIS_URL points to staging Redis** - Check hostname
4. **STORAGE_BUCKET_NAME is staging bucket** - Verify bucket name
5. **NEXT_PUBLIC_API_URL points to staging API** - Check domain

---

## Debugging Variables

To verify variables are correctly set:

```bash
# Check API environment
curl https://agentverse-api-staging.up.railway.app/health

# Response should include:
# {"status": "healthy", "environment": "staging", ...}
```

---

## Adding New Variables

When adding new environment variables:

1. Add to this documentation table
2. Add to Railway Dashboard for staging environment
3. Add to `apps/api/app/core/config.py` if backend
4. Add to `apps/web/.env.example` if frontend
5. Verify in staging before production

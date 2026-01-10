# Staging Resource Isolation Proof

**Environment:** staging
**Verification Date:** 2026-01-10
**Purpose:** Prove staging does not touch production data or resources

---

## Isolation Verification Matrix

| Resource | Production | Staging | Isolation Method | Verified |
|----------|------------|---------|------------------|----------|
| PostgreSQL | `postgres-prod` | `postgres-staging` | Separate Railway plugin instance | PENDING |
| Redis | `redis-prod` | `redis-staging` | Separate Railway plugin instance | PENDING |
| Storage Bucket | `agentverse-reps` | `agentverse-staging-reps` | Separate bucket name | PENDING |
| API Domain | `api.agentverse.io` | `*-staging.up.railway.app` | Different hostname | PENDING |
| Web Domain | `agentverse.io` | `*-staging.up.railway.app` | Different hostname | PENDING |

---

## 1. Database Isolation Proof

### Expected Configuration

```
Production DATABASE_URL: postgres://user:pass@prod-host:5432/railway
Staging DATABASE_URL:    postgres://user:pass@staging-host:5432/railway
```

### Verification Steps

1. **Check Hostname Difference:**
   ```bash
   # In Railway Dashboard, verify DATABASE_URL hostnames are different
   # Production: containers-us-west-xxx.railway.app
   # Staging:    containers-us-west-yyy.railway.app (DIFFERENT)
   ```

2. **Table Count Verification:**
   ```sql
   -- Run in staging database
   SELECT COUNT(*) FROM information_schema.tables
   WHERE table_schema = 'public';
   -- Should be 0 or show only staging test data
   ```

3. **Data Sample Check:**
   ```sql
   -- Verify no production user data exists in staging
   SELECT COUNT(*) FROM users WHERE email LIKE '%@production.com';
   -- Should return 0
   ```

### Evidence

```
[ ] Screenshot of Railway showing two separate PostgreSQL plugins
[ ] DATABASE_URL hostnames confirmed different
[ ] No production data found in staging database
```

---

## 2. Redis Isolation Proof

### Expected Configuration

```
Production REDIS_URL: redis://default:pass@prod-redis:6379
Staging REDIS_URL:    redis://default:pass@staging-redis:6379
```

### Verification Steps

1. **Check Hostname Difference:**
   ```bash
   # Verify REDIS_URL hostnames are different in Railway Dashboard
   ```

2. **Key Namespace Check:**
   ```bash
   # Connect to staging Redis
   redis-cli -u $REDIS_URL
   > KEYS *
   # Should show only staging keys (or empty)
   ```

3. **Queue Isolation:**
   ```bash
   # Verify Celery queues are separate
   > KEYS celery*
   # Should show staging-specific queue names
   ```

### Evidence

```
[ ] Screenshot of Railway showing two separate Redis plugins
[ ] REDIS_URL hostnames confirmed different
[ ] No production queue data in staging Redis
```

---

## 3. Storage Bucket Isolation Proof

### Expected Configuration

```
Production Bucket: agentverse-reps
Staging Bucket:    agentverse-staging-reps
```

### Verification Steps

1. **Bucket Name Verification:**
   ```bash
   # Check STORAGE_BUCKET_NAME environment variable
   echo $STORAGE_BUCKET_NAME
   # Should output: agentverse-staging-reps
   ```

2. **Bucket Contents Check:**
   ```bash
   # List bucket contents (using s3cmd or similar)
   s3cmd ls s3://agentverse-staging-reps/
   # Should show only staging REPs or empty
   ```

3. **Write/Read Test:**
   ```bash
   # Upload test file to staging bucket
   echo "staging-test" > /tmp/staging-test.txt
   s3cmd put /tmp/staging-test.txt s3://agentverse-staging-reps/test/

   # Verify it's NOT in production bucket
   s3cmd ls s3://agentverse-reps/test/staging-test.txt
   # Should return empty/not found
   ```

### Evidence

```
[ ] STORAGE_BUCKET_NAME confirmed as staging bucket
[ ] Test file written to staging bucket only
[ ] Production bucket does not contain staging test file
```

---

## 4. Network Isolation Proof

### Domain Verification

| Service | Production Domain | Staging Domain |
|---------|-------------------|----------------|
| API | `api.agentverse.io` | `agentverse-api-staging.up.railway.app` |
| Web | `agentverse.io` | `agentverse-web-staging.up.railway.app` |

### API Endpoint Check

```bash
# Staging API should return environment=staging
curl https://agentverse-api-staging.up.railway.app/health
# Expected: {"status": "healthy", "environment": "staging", ...}

# Production API should return environment=production
curl https://api.agentverse.io/health
# Expected: {"status": "healthy", "environment": "production", ...}
```

### Evidence

```
[ ] Staging API returns environment=staging
[ ] Different domains confirmed
[ ] No cross-environment API calls possible
```

---

## 5. Environment Variable Isolation

### ENVIRONMENT Variable Check

```bash
# Staging services must have ENVIRONMENT=staging
# This affects code paths, logging, and feature flags
```

### Critical Variables Comparison

| Variable | Must Be Different | Staging Value |
|----------|-------------------|---------------|
| `ENVIRONMENT` | YES | `staging` |
| `DATABASE_URL` | YES (hostname) | `*-staging*` |
| `REDIS_URL` | YES (hostname) | `*-staging*` |
| `STORAGE_BUCKET_NAME` | YES | `*-staging*` |
| `SECRET_KEY` | YES | Different from prod |

### Evidence

```
[ ] ENVIRONMENT=staging confirmed
[ ] All hostnames contain staging identifier
[ ] SECRET_KEY is different from production
```

---

## Isolation Certification

### Pre-Deployment Checklist

- [ ] PostgreSQL is separate instance (different hostname)
- [ ] Redis is separate instance (different hostname)
- [ ] Storage bucket is different (staging-specific name)
- [ ] API domain is staging-specific
- [ ] Web domain is staging-specific
- [ ] ENVIRONMENT variable set to `staging`
- [ ] SECRET_KEY is different from production
- [ ] No production data accessible from staging

### Sign-Off

```
Verified By: ___________________
Date: 2026-01-10
Status: PENDING VERIFICATION
```

---

## Incident Response

If production data is ever found in staging:

1. **STOP** all staging deployments immediately
2. **AUDIT** environment variables for misconfiguration
3. **PURGE** any production data from staging resources
4. **ROTATE** all secrets that may have been exposed
5. **DOCUMENT** the incident and root cause

---

## Automated Isolation Checks

Consider implementing these automated checks:

```python
# In app/main.py startup
async def verify_staging_isolation():
    if settings.ENVIRONMENT == "staging":
        # Verify DATABASE_URL contains staging identifier
        assert "staging" in settings.DATABASE_URL.lower() or \
               settings.DATABASE_URL != KNOWN_PROD_URL

        # Verify STORAGE_BUCKET_NAME is staging bucket
        assert "staging" in settings.STORAGE_BUCKET_NAME.lower()

        logger.info("Staging isolation verified")
```

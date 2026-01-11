# AgentVerse Production Deployment Guide

**Date:** 2026-01-09
**Status:** Ready for deployment with decisions required

---

## Part 1: Decisions Required

### Decision 1: Tenant Isolation (GAP-P0-002 to GAP-P0-004)

**Question:** Do you want strict multi-tenant isolation before production?

**Options:**

| Option | Description | Risk Level | Effort |
|--------|-------------|------------|--------|
| **A) Deploy Now** | Skip tenant isolation for MVP. Single-tenant or trusted users only. | Medium | None |
| **B) Full Isolation** | Implement all tenant_id FKs and require_tenant checks. | Low | 2-3 days |

**My Recommendation:** **Option A** for initial launch if you have a small trusted user base. Implement Option B before public launch or enterprise customers.

**If you choose Option B**, run these commands:
```bash
# I can implement these for you - just say "implement tenant isolation"
```

---

### Decision 2: API Key Authentication (GAP-P0-005)

**Question:** Do you need programmatic API access (for integrations, scripts)?

**Options:**

| Option | Description |
|--------|-------------|
| **A) JWT Only** | Users authenticate via login, get JWT tokens. No API keys. |
| **B) API Keys** | Add API key generation for programmatic access. |

**My Recommendation:** **Option A** for MVP. API keys are usually needed later for enterprise integrations.

---

### Decision 3: Object Storage

**Question:** Where should telemetry/artifacts be stored?

**Options:**

| Option | Provider | Cost | Setup |
|--------|----------|------|-------|
| **A) Local** | Server filesystem | Free | Set `STORAGE_BACKEND=local` |
| **B) AWS S3** | Amazon S3 | ~$0.023/GB | Need AWS credentials |
| **C) MinIO** | Self-hosted S3 | Free | Need MinIO server |
| **D) DigitalOcean Spaces** | DO Spaces | $5/250GB | Need DO credentials |

**My Recommendation:** **Option A (Local)** for MVP, migrate to S3/Spaces when data grows.

---

## Part 2: API Keys & Services Setup

### Required APIs

#### 1. OpenRouter (REQUIRED - for AI features)

**What it does:** Provides access to GPT-4, Claude, and other AI models through a unified API.

**How to get:**
1. Go to https://openrouter.ai
2. Sign up for an account
3. Go to https://openrouter.ai/keys
4. Click "Create Key"
5. Copy the key (starts with `sk-or-`)

**Cost:** Pay-as-you-go. ~$0.15 per 1M tokens for GPT-4o-mini (default model)

**Set in:** `apps/api/.env`
```env
OPENROUTER_API_KEY=sk-or-your-key-here
```

---

#### 2. PostgreSQL Database (REQUIRED)

**Options:**

| Provider | Free Tier | Production Cost |
|----------|-----------|-----------------|
| **Supabase** | 500MB free | $25/mo for 8GB |
| **Neon** | 512MB free | $19/mo for 10GB |
| **Railway** | $5 credit | ~$5-20/mo |
| **DigitalOcean** | None | $15/mo |
| **AWS RDS** | 750hrs free | ~$15/mo |

**Recommended:** Supabase or Neon for easy setup.

**Supabase Setup:**
1. Go to https://supabase.com
2. Create new project
3. Go to Settings > Database
4. Copy the connection string (use "URI" format)
5. Replace `[YOUR-PASSWORD]` with your database password

**Set in:** `apps/api/.env`
```env
DATABASE_URL=postgresql+asyncpg://postgres:[PASSWORD]@[HOST]:5432/postgres
```

---

#### 3. Redis (REQUIRED for background jobs)

**Options:**

| Provider | Free Tier | Production |
|----------|-----------|------------|
| **Upstash** | 10K commands/day free | $0.2/100K commands |
| **Redis Cloud** | 30MB free | $7/mo for 250MB |
| **Railway** | $5 credit | ~$5/mo |

**Recommended:** Upstash for serverless Redis.

**Upstash Setup:**
1. Go to https://upstash.com
2. Create new Redis database
3. Copy the Redis URL

**Set in:** `apps/api/.env`
```env
REDIS_URL=rediss://default:[PASSWORD]@[HOST]:6379
```

---

#### 4. NextAuth Secret (REQUIRED for frontend auth)

**Generate a secure secret:**
```bash
openssl rand -base64 32
```

**Set in Vercel Dashboard** (NOT in code):
- `NEXTAUTH_SECRET` = the generated string
- `NEXTAUTH_URL` = your production URL (e.g., https://agentverse.vercel.app)

---

### Optional APIs

#### 5. Sentry (Error Tracking)

**Setup:**
1. Go to https://sentry.io
2. Create project (select FastAPI for backend, Next.js for frontend)
3. Copy the DSN

**Set in:** `apps/api/.env` and Vercel Dashboard
```env
SENTRY_DSN=https://[key]@sentry.io/[project-id]
```

---

#### 6. Census API (Enhanced Persona Data)

**What it does:** Real demographic data for realistic persona generation.

**Setup:**
1. Go to https://api.census.gov/data/key_signup.html
2. Request a free API key
3. Key arrives via email

**Set in:** `apps/api/.env`
```env
CENSUS_API_KEY=your-census-key
USE_REAL_CENSUS_DATA=true
```

---

## Part 3: Complete Environment Setup

### Backend (apps/api/.env)

Create this file with your values:

```env
# Application
PROJECT_NAME=AgentVerse API
VERSION=1.0.0
ENVIRONMENT=production
DEBUG=false

# Security (CHANGE THIS!)
SECRET_KEY=<run: openssl rand -hex 32>

# Database (from Supabase/Neon)
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname

# Redis (from Upstash)
REDIS_URL=rediss://default:pass@host:6379

# OpenRouter (REQUIRED)
OPENROUTER_API_KEY=sk-or-your-key-here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
DEFAULT_MODEL=openai/gpt-4o-mini

# CORS - Add your production frontend URL
CORS_ORIGINS=["https://your-frontend.vercel.app","http://localhost:3002"]

# Storage (local for MVP)
STORAGE_BACKEND=local
STORAGE_LOCAL_PATH=/tmp/agentverse-storage

# Optional
SENTRY_DSN=
CENSUS_API_KEY=
```

### Frontend (Vercel Dashboard)

Set these in Vercel Project Settings > Environment Variables:

| Variable | Value | Environment |
|----------|-------|-------------|
| `NEXTAUTH_SECRET` | `<openssl rand -base64 32>` | Production |
| `NEXTAUTH_URL` | `https://your-app.vercel.app` | Production |
| `BACKEND_API_URL` | `https://your-api-url.com` | Production |
| `NEXT_PUBLIC_WS_URL` | `wss://your-api-url.com` | Production |

---

## Part 4: Deployment Steps

### Step 1: Deploy Backend API

**Option A: Railway (Recommended for MVP)**
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize project
cd apps/api
railway init

# Add environment variables
railway variables set OPENROUTER_API_KEY=sk-or-xxx
railway variables set DATABASE_URL=postgresql+asyncpg://...
railway variables set REDIS_URL=rediss://...
railway variables set SECRET_KEY=$(openssl rand -hex 32)

# Deploy
railway up
```

**Option B: Docker**
```bash
cd apps/api
docker build -t agentverse-api .
docker run -p 8000:8000 --env-file .env agentverse-api
```

### Step 2: Run Database Migrations

```bash
cd apps/api
alembic upgrade head
```

### Step 3: Deploy Frontend to Vercel

1. Push code to GitHub
2. Import project in Vercel
3. Set environment variables (see table above)
4. Deploy

### Step 4: Test

1. Visit your frontend URL
2. Login with test credentials:
   - Email: `claude-test@agentverse.io`
   - Password: `TestAgent2024!`
3. Create a project
4. Run a baseline simulation

---

## Quick Reference: All API Keys Needed

| API | Required | Cost | Where to Get |
|-----|----------|------|--------------|
| OpenRouter | YES | Pay-per-use | https://openrouter.ai/keys |
| PostgreSQL | YES | Free tier available | Supabase/Neon/Railway |
| Redis | YES | Free tier available | Upstash/Redis Cloud |
| NextAuth Secret | YES | Free (generate locally) | `openssl rand -base64 32` |
| Sentry | No | Free tier | https://sentry.io |
| Census API | No | Free | https://api.census.gov |
| AWS S3 | No | Pay-per-use | AWS Console |

---

## Summary of My Recommendations

1. **Deploy Now** with single-tenant mode (Option A for Decision 1)
2. **Use JWT only** for auth (Option A for Decision 2)
3. **Use local storage** for MVP (Option A for Decision 3)
4. **Get OpenRouter key** - this is the only paid API you need immediately
5. **Use Supabase** for PostgreSQL (free tier)
6. **Use Upstash** for Redis (free tier)

Total cost for MVP: **~$0-5/month** (mostly OpenRouter usage)

---

*Generated by Claude Code*

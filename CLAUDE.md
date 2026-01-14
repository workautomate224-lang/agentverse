# AgentVerse

Future Predictive AI Platform with reversible, on-demand simulations producing auditable predictions.

## Tech Stack

**Frontend:** Next.js 14, TypeScript, React Query, Tailwind CSS, Radix UI
**Backend:** FastAPI, Python 3.12+, SQLAlchemy, Pydantic, Celery
**Database:** PostgreSQL (Supabase), Redis (Upstash)
**LLM:** OpenRouter API (routed through LLMRouter service)

> **Full Tech Stack Reference:** See `docs/techstack.md` for comprehensive technology details, versions, and configurations.

## Project Structure

```
agentverse/
├── apps/
│   ├── web/                   # Next.js frontend
│   │   └── src/
│   │       ├── app/           # App router pages
│   │       ├── components/    # React components
│   │       ├── hooks/         # React Query hooks (useApi.ts)
│   │       └── lib/           # API client, utilities
│   └── api/                   # FastAPI backend
│       └── app/
│           ├── api/v1/        # REST endpoints
│           ├── engine/        # Simulation engine (rules, agents, events)
│           ├── services/      # Business logic
│           ├── models/        # SQLAlchemy models
│           ├── schemas/       # Pydantic schemas
│           └── tasks/         # Celery tasks
├── packages/
│   ├── contracts/             # Shared TypeScript types
│   └── ui/                    # Shared UI components
└── docs/
    ├── project.md             # Technical specification
    └── Interaction_design.md  # UI/UX specification
```

## Common Commands

```bash
# Frontend (from apps/web)
pnpm dev                    # Start dev server on :3000
pnpm build                  # Production build
pnpm type-check             # TypeScript validation

# Backend (from apps/api)
uvicorn app.main:app --reload    # Start API on :8000
alembic upgrade head             # Run migrations
celery -A app.tasks worker       # Start Celery worker

# Monorepo root
pnpm install                # Install all dependencies
```

## Development Workflow

- Push to `https://github.com/workautomate224-lang/agentverse.git`
- Run `pnpm type-check` before commits
- Use LLMRouter for all LLM calls (enforced by `scripts/check_llm_usage.py`)
- Reference specs in `docs/` for implementation details

## Architecture Constraints

These constraints are non-negotiable:

1. **Fork-not-mutate (C1):** Never modify existing Nodes. Create new Node on any change.
2. **On-demand (C2):** No continuous simulation. Execute only when triggered.
3. **Replay read-only (C3):** 2D replay queries telemetry only. Never triggers simulation.
4. **Auditable (C4):** All artifacts versioned and persisted.
5. **LLMs as compilers (C5):** LLMs plan/compile once. No LLM in tick-by-tick loops.
6. **Multi-tenant (C6):** All data scoped by tenant_id.

## Code Style

- Use ES modules (import/export) in TypeScript
- Use async/await, not callbacks
- Pydantic for all API schemas
- SQLAlchemy 2.0 async patterns
- Keep cyberpunk UI theme (cyan accents, dark backgrounds)

## Key Files

| Purpose | Location |
|---------|----------|
| API client | `apps/web/src/lib/api.ts` |
| React hooks | `apps/web/src/hooks/useApi.ts` |
| LLM gateway | `apps/api/app/services/llm_router.py` |
| Simulation engine | `apps/api/app/engine/` |
| DB migrations | `apps/api/alembic/versions/` |

## Deployment Stack

**All services are deployed on Railway:**

| Service | Railway Service | URL |
|---------|----------------|-----|
| Frontend | `agentverse-web-staging` | https://agentverse-web-staging-production.up.railway.app |
| Backend API | `agentverse-api-staging` | https://agentverse-api-staging-production.up.railway.app |
| Worker | `agentverse-worker-staging` | Internal |
| Database | `postgres-staging` | Internal |
| Cache | `redis-staging` | Internal |
| Storage | `minio-staging` | Internal |

## OpenRouter API Configuration (CRITICAL - DO NOT FORGET!)

**OpenRouter API Key** is required for ALL AI-powered features.

### Key Locations
| Environment | Location | Status |
|-------------|----------|--------|
| Local Dev | `apps/web/.env.local` → `OPENROUTER_API_KEY` | ✅ Configured |
| Railway Staging | Environment variable `OPENROUTER_API_KEY` | ✅ Configured |
| Production | Railway env vars | ✅ Configured |

### Features Using OpenRouter
- Event Lab scenario generation (`/p/:id/event-lab`)
- Future AI-powered analysis features

### API Details
- Provider: OpenRouter (https://openrouter.ai)
- Default Model: `openai/gpt-4o-mini` (fast, cheap)
- Endpoint: `https://openrouter.ai/api/v1/chat/completions`

### Implementation
All OpenRouter calls go through Next.js API routes (e.g., `/api/ask/generate`).
See `apps/web/CLAUDE.md` for detailed usage patterns.

---

## Documentation Maintenance (Claude Auto-Update)

**IMPORTANT:** When making changes that affect the tech stack or project structure, Claude must automatically update the relevant documentation:

1. **Tech Stack Changes** (new libraries, version upgrades, removed dependencies):
   - Update `docs/techstack.md` with the changes
   - Update the "Tech Stack" section in this file if it's a major component

2. **Project Structure Changes** (new directories, reorganized folders, new apps/packages):
   - Update the "Project Structure" section in this file
   - Update `docs/techstack.md` Architecture section if applicable

3. **New Key Files** (important new services, configs, or entry points):
   - Add to the "Key Files" table in this file

4. **Deployment Changes** (new services, URL changes, infrastructure updates):
   - Update the "Deployment Stack" section in this file

This ensures documentation stays in sync with the codebase automatically.

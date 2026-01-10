# AgentVerse

Future Predictive AI Platform with reversible, on-demand simulations producing auditable predictions.

## Tech Stack

**Frontend:** Next.js 14, TypeScript, React Query, Tailwind CSS, Radix UI
**Backend:** FastAPI, Python 3.11+, SQLAlchemy, Pydantic, Celery
**Database:** PostgreSQL (Supabase), Redis (Upstash)
**LLM:** OpenRouter API (routed through LLMRouter service)

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

- Push to `https://github.com/sweiloon/agentverse.git`
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

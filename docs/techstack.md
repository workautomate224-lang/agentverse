# AgentVerse Technology Stack

> Last Updated: 2026-01-14

## Overview

AgentVerse is an AI Agent Simulation Platform built as a monorepo using Turborepo. The platform enables predictive simulations with AI-powered consumer personas.

---

## Architecture

```
agentverse/
├── apps/
│   ├── web/          # Next.js 14 Frontend
│   └── api/          # FastAPI Backend
├── packages/
│   ├── contracts/    # Shared TypeScript contracts
│   ├── types/        # Shared type definitions
│   ├── ui/           # Shared UI components
│   └── utils/        # Shared utilities
└── docs/             # Documentation
```

---

## Frontend Stack (`apps/web/`)

### Core Framework
| Technology | Version | Purpose |
|------------|---------|---------|
| Next.js | 14.0.4 | React framework (App Router) |
| React | 18.2.0 | UI library |
| TypeScript | 5.3.2 | Type-safe JavaScript |

### State Management & Data Fetching
| Technology | Version | Purpose |
|------------|---------|---------|
| TanStack React Query | 5.8.4 | Server state management |
| Zustand | 4.4.7 | Client state management |
| NextAuth.js | 4.24.5 | Authentication |

### UI & Styling
| Technology | Version | Purpose |
|------------|---------|---------|
| Tailwind CSS | 3.3.6 | Utility-first CSS |
| Radix UI | Various | Accessible UI primitives |
| Class Variance Authority | 0.7.0 | Component variants |
| Framer Motion | 10.16.5 | Animations |
| Lucide React | 0.294.0 | Icon library |

### Data Visualization
| Technology | Version | Purpose |
|------------|---------|---------|
| Recharts | 2.10.3 | Chart library |
| PixiJS | 8.14.3 | 2D WebGL graphics |
| XYFlow | 12.10.0 | Node/edge graphs |

### Forms & Validation
| Technology | Version | Purpose |
|------------|---------|---------|
| React Hook Form | 7.48.2 | Form handling |
| Zod | 3.22.4 | Schema validation |

### Utilities
| Technology | Version | Purpose |
|------------|---------|---------|
| date-fns | 4.1.0 | Date manipulation |
| clsx | 2.0.0 | Class name utility |
| html2canvas | 1.4.1 | Screenshot generation |

---

## Backend Stack (`apps/api/`)

### Core Framework
| Technology | Version | Purpose |
|------------|---------|---------|
| FastAPI | 0.109.0 | Async Python web framework |
| Python | 3.12+ | Programming language |
| Uvicorn | 0.27.0 | ASGI server |
| Pydantic | 2.x | Data validation |

### Database & ORM
| Technology | Version | Purpose |
|------------|---------|---------|
| PostgreSQL | 15+ | Primary database |
| SQLAlchemy | 2.0.25 | Async ORM |
| asyncpg | 0.29.0 | Async PostgreSQL driver |
| Alembic | 1.13.1 | Database migrations |

### Caching & Task Queue
| Technology | Version | Purpose |
|------------|---------|---------|
| Redis | 5.0.1 | Caching & message broker |
| Celery | 5.3.6 | Distributed task queue |

### AI Integration
| Technology | Version | Purpose |
|------------|---------|---------|
| OpenAI SDK | 1.10.0 | LLM client |
| OpenRouter | - | Multi-model routing |

### Data Science
| Technology | Version | Purpose |
|------------|---------|---------|
| NumPy | 1.26.3 | Numerical computing |
| SciPy | 1.12.0 | Scientific computing |
| Pandas | 2.2.0 | Data manipulation |

### Authentication & Security
| Technology | Version | Purpose |
|------------|---------|---------|
| python-jose | 3.3.0 | JWT handling |
| passlib | 1.7.4 | Password hashing |
| bcrypt | - | Secure hashing |

### Observability
| Technology | Version | Purpose |
|------------|---------|---------|
| Sentry SDK | 1.39.0 | Error tracking |
| Prometheus Client | 0.19.0 | Metrics |
| OpenTelemetry | 1.22.0+ | Distributed tracing |

### Storage
| Technology | Version | Purpose |
|------------|---------|---------|
| boto3 | 1.34.0 | S3-compatible storage |
| aiofiles | 23.2.1 | Async file I/O |

### Development Tools
| Technology | Version | Purpose |
|------------|---------|---------|
| Ruff | 0.1.14 | Fast Python linter |
| MyPy | 1.8.0 | Static type checker |
| pytest | 7.4.4 | Testing framework |
| factory-boy | 3.3.0 | Test fixtures |
| locust | 2.20.0 | Load testing |

---

## Infrastructure

### Monorepo & Build
| Technology | Version | Purpose |
|------------|---------|---------|
| Turborepo | 2.0.0 | Monorepo build system |
| npm | 10.2.0 | Package manager |

### Containerization
| Technology | Purpose |
|------------|---------|
| Docker | Container runtime |
| Docker Compose | Local development orchestration |

### Deployment
| Service | Platform | Purpose |
|---------|----------|---------|
| Frontend | Railway | Next.js hosting |
| Backend API | Railway | FastAPI hosting |
| Worker | Railway | Celery workers |
| Database | Railway (PostgreSQL) | Primary database |
| Cache | Railway (Redis) | Caching layer |

### CI/CD
| Technology | Purpose |
|------------|---------|
| GitHub Actions | Automated testing & deployment |

---

## External Services

### AI Provider
- **OpenRouter** - Multi-model LLM routing
  - Default Model: `openai/gpt-4o-mini`
  - Endpoint: `https://openrouter.ai/api/v1`

### Database Hosting
- **Supabase** (PostgreSQL) - Production database
- **Upstash** (Redis) - Serverless Redis

---

## Key Design Patterns

### Frontend
- **Server Components** for static content
- **Client Components** (`'use client'`) for interactivity
- **React Query** for server state
- **Zustand** for client state
- **CVA** for component variants

### Backend
- **Repository Pattern** for data access
- **Service Layer** for business logic
- **Pydantic Schemas** for validation
- **SQLAlchemy 2.0** async patterns
- **Dependency Injection** via FastAPI

---

## Environment Variables

### Frontend (`apps/web/.env.local`)
```
NEXTAUTH_URL=http://localhost:3002
NEXTAUTH_SECRET=<secret>
BACKEND_API_URL=http://localhost:8000
NEXT_PUBLIC_API_URL=
OPENROUTER_API_KEY=<key>
```

### Backend (`apps/api/.env`)
```
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://localhost:6379/0
OPENROUTER_API_KEY=<key>
SECRET_KEY=<secret>
ENVIRONMENT=development
```

---

## Performance Specifications

### Simulation Limits
| Tier | Max Agents |
|------|------------|
| Free | 1,000 |
| Pro | 10,000 |
| Enterprise | 100,000 |

### Rate Limits
- 60 requests/minute
- 1,000 requests/hour

### Timeouts
- Simulation timeout: 300 seconds
- Default batch size: 50 agents

---

## Security Features

- JWT-based authentication (HS256)
- CORS configuration
- Rate limiting
- Security headers (HSTS, X-Frame-Options, etc.)
- Secret rotation support
- Multi-tenant data isolation

---

## File References

| Purpose | Location |
|---------|----------|
| API Client | `apps/web/src/lib/api.ts` |
| React Query Hooks | `apps/web/src/hooks/useApi.ts` |
| LLM Gateway | `apps/api/app/services/llm_router.py` |
| Simulation Engine | `apps/api/app/engine/` |
| DB Migrations | `apps/api/alembic/versions/` |
| Auth Config | `apps/web/src/lib/auth.ts` |
| Backend Config | `apps/api/app/core/config.py` |

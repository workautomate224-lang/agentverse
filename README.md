# AgentVerse

**AI Agent Simulation Platform** - Simulate human decisions at scale.

AgentVerse is an enterprise-grade platform for running AI-powered human behavior simulations. Generate synthetic personas, run scenarios, and get predictive insights in minutes instead of months.

## Features

- **Multi-Agent Simulation** - Run simulations with 100 to 100,000+ AI agents
- **Synthetic Persona Generation** - Demographically-accurate personas based on real population data
- **Multiple Domains** - Marketing, Political, Financial, and Custom scenarios
- **Real-time Streaming** - Watch simulation results as they happen
- **Virtual Focus Groups** - Interview AI agents for qualitative insights
- **Model Flexibility** - Switch between GPT-4, Claude, Llama, and more via OpenRouter
- **Results Analytics** - Interactive dashboards with demographic breakdowns
- **API Access** - Programmatic access for integration

## Tech Stack

### Frontend
- **Next.js 14** with App Router
- **TypeScript** for type safety
- **Tailwind CSS** + shadcn/ui for UI components
- **Zustand** + TanStack Query for state management
- **Recharts** for data visualization

### Backend
- **FastAPI** (Python 3.12) with async support
- **SQLAlchemy 2.0** with async PostgreSQL
- **Celery** for background task processing
- **Redis** for caching and queues

### Infrastructure
- **PostgreSQL 16** for data persistence
- **Redis 7** for caching and pub/sub
- **Docker Compose** for local development
- **Railway** for production deployment
- **GitHub Actions** for CI/CD

### Deployment (Railway)
All services are deployed on Railway:
| Service | Railway Service | URL |
|---------|----------------|-----|
| Frontend | `agentverse-web-staging` | https://agentverse-web-staging-production.up.railway.app |
| Backend API | `agentverse-api-staging` | https://agentverse-api-staging-production.up.railway.app |
| Worker | `agentverse-worker-staging` | Internal |
| Database | `postgres-staging` | Internal |
| Cache | `redis-staging` | Internal |
| Storage | `minio-staging` | Internal |

## Quick Start

### Prerequisites

- Node.js 20+
- Python 3.12+
- Docker and Docker Compose
- OpenRouter API key (get one at https://openrouter.ai)

### Setup

1. **Clone the repository**
   ```bash
   cd agentverse
   ```

2. **Set up environment variables**
   ```bash
   cp apps/api/.env.example apps/api/.env
   # Edit .env and add your OPENROUTER_API_KEY
   ```

3. **Start with Docker Compose**
   ```bash
   docker-compose up -d
   ```

4. **Or run locally**

   Backend:
   ```bash
   cd apps/api
   pip install -e .
   uvicorn app.main:app --reload
   ```

   Frontend:
   ```bash
   cd apps/web
   npm install
   npm run dev
   ```

5. **Access the application**
   - Frontend: http://localhost:3000
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Project Structure

```
agentverse/
├── apps/
│   ├── web/                 # Next.js frontend
│   │   ├── src/
│   │   │   ├── app/         # App Router pages
│   │   │   ├── components/  # React components
│   │   │   ├── lib/         # Utilities
│   │   │   └── hooks/       # Custom hooks
│   │   └── package.json
│   │
│   └── api/                 # FastAPI backend
│       ├── app/
│       │   ├── api/         # API endpoints
│       │   ├── core/        # Config, security
│       │   ├── db/          # Database session
│       │   ├── models/      # SQLAlchemy models
│       │   ├── schemas/     # Pydantic schemas
│       │   └── services/    # Business logic
│       ├── alembic/         # Database migrations
│       └── pyproject.toml
│
├── packages/
│   ├── types/               # Shared TypeScript types
│   ├── utils/               # Shared utilities
│   └── ui/                  # Shared UI components
│
├── infrastructure/
│   └── docker/              # Docker configurations
│
├── .github/
│   └── workflows/           # CI/CD pipelines
│
├── docker-compose.yml       # Local development setup
├── turbo.json               # Turborepo configuration
└── package.json             # Root package.json
```

## API Reference

### Authentication
- `POST /api/v1/auth/register` - Create account
- `POST /api/v1/auth/login` - Login and get tokens
- `POST /api/v1/auth/refresh` - Refresh access token
- `GET /api/v1/auth/me` - Get current user

### Projects
- `GET /api/v1/projects` - List projects
- `POST /api/v1/projects` - Create project
- `GET /api/v1/projects/{id}` - Get project
- `PUT /api/v1/projects/{id}` - Update project
- `DELETE /api/v1/projects/{id}` - Delete project

### Scenarios
- `GET /api/v1/scenarios` - List scenarios
- `POST /api/v1/scenarios` - Create scenario
- `GET /api/v1/scenarios/{id}` - Get scenario
- `PUT /api/v1/scenarios/{id}` - Update scenario
- `POST /api/v1/scenarios/{id}/validate` - Validate scenario

### Simulations
- `POST /api/v1/simulations` - Start simulation
- `GET /api/v1/simulations/{id}` - Get simulation status
- `GET /api/v1/simulations/{id}/stream` - Stream results (SSE)
- `GET /api/v1/simulations/{id}/agents` - Get agent responses
- `GET /api/v1/simulations/{id}/results` - Get aggregated results
- `POST /api/v1/simulations/{id}/interview` - Virtual focus group

## Development

### Running Tests

```bash
# Frontend tests
cd apps/web && npm test

# Backend tests
cd apps/api && pytest
```

### Database Migrations

```bash
cd apps/api

# Create a new migration
alembic revision --autogenerate -m "Description"

# Run migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Adding New Models

1. Add the model in `apps/api/app/models/`
2. Export in `apps/api/app/models/__init__.py`
3. Create Pydantic schemas in `apps/api/app/schemas/`
4. Generate migration with Alembic
5. Create API endpoints in `apps/api/app/api/v1/endpoints/`

## Roadmap

### Phase 1 (MVP) - Complete
- [x] Monorepo setup with Turborepo
- [x] FastAPI backend with auth
- [x] Next.js frontend structure
- [x] Database models and migrations
- [x] OpenRouter integration
- [x] Basic simulation engine

### Phase 2 (Production)
- [ ] Real-time streaming UI
- [ ] Interactive results dashboard
- [ ] Billing integration (Stripe)
- [ ] Team collaboration features
- [ ] API documentation portal

### Phase 3 (Differentiation)
- [ ] Virtual focus groups
- [ ] What-if analysis
- [ ] Scenario marketplace
- [ ] Multi-language support
- [ ] Enterprise features

## License

Proprietary - All rights reserved.

## Contact

For questions or support, contact the AgentVerse team.

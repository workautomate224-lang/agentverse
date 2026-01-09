# AgentVerse - Claude Session Memory

**GitHub Repository:** https://github.com/sweiloon/agentverse
**IMPORTANT:** Always push to `https://github.com/sweiloon/agentverse.git` - NOT ai-voice-chat-pwa!

**Last Updated:** 2026-01-09
**Current Phase:** ALL PHASES COMPLETE ✅ (96/96 tasks = 100%)
**Current Focus:** Project complete! Remediation items (P9-001a-e) require human review before production.

---

## 1) Mission & Constraints

**Mission:** Build Future Predictive AI Platform with reversible, on-demand simulations producing auditable predictions.

**Hard Constraints (C0-C6):**
- C0: Preserve UI visual style (cyberpunk theme) - may rewire flows but keep aesthetics
- C1: Reversible-by-design - FORK to new node, never mutate history
- C2: On-demand execution - no continuous always-on world
- C3: Replay (2D) is READ-ONLY - must NEVER trigger simulations
- C4: Predictions are auditable artifacts - Node/Run/Telemetry/Reliability persisted and versioned
- C5: LLMs are compilers/planners - NOT tick-by-tick brains in agent loops
- C6: Multi-tenancy, auth, rate limits, job quotas are mandatory early

---

## 2) Current Phase + Focus

**Phase:** ALL COMPLETE ✅
**Status:** 96/96 tasks done (100%)
**Objective:** All spec requirements implemented per project.md and Interaction_design.md

**All Phases Completed:**
- Phase 0: Foundations (12 tasks) ✅
- Phase 1: Society Engine (9 tasks) ✅
- Phase 2: Universe Map (10 tasks) ✅
- Phase 3: Event System (4 tasks) ✅
- Phase 4: Ask/Event Compiler (8 tasks) ✅
- Phase 5: Target Mode (7 tasks) ✅
- Phase 6: Hybrid Mode (3 tasks) ✅
- Phase 7: Calibration & Reliability (9 tasks) ✅
- Phase 8: 2D Replay (6 tasks) ✅
- Phase 9: Production Hardening (8 tasks) ✅
- UI Tasks (13 tasks) ✅
- Non-Functional (5 tasks) ✅
- Documentation (2 tasks) ✅

---

## 3) Remaining Work (Pre-Production)

**GAP-P0-001: LLM Router - ✅ IMPLEMENTED**
| Item | Status | Notes |
|------|--------|-------|
| LLMRouter service | ✅ Done | `app/services/llm_router.py` |
| Database tables | ✅ Done | Migration 0003 (llm_profiles, llm_calls, llm_cache) |
| Admin API | ✅ Done | `/admin/llm/profiles`, `/admin/llm/costs` |
| CI check | ✅ Done | `scripts/check_llm_usage.py` |
| Refactor event_compiler.py | ✅ Done | Uses LLMRouter |
| Refactor ai_research.py | ✅ Done | Uses LLMRouter |
| Refactor focus_group.py | ✅ Done | Uses LLMRouter |
| Refactor persona_expansion.py | ✅ Done | Uses LLMRouter |
| Legacy services | ⏳ Pending | `product_execution.py`, `simulation.py` use batch_complete (marked for removal) |
| Admin Models UI | ✅ Done | Models tab in `/dashboard/admin` with profile list, cost dashboard, test functionality |

**GAP-P0-006: Audit Log Query Endpoints - ✅ IMPLEMENTED**
| Item | Status | Notes |
|------|--------|-------|
| Audit schemas | ✅ Done | `app/schemas/audit.py` |
| Admin API endpoints | ✅ Done | `app/api/v1/endpoints/audit_admin.py` |
| Frontend API methods | ✅ Done | Added to `apps/web/src/lib/api.ts` |
| React Query hooks | ✅ Done | Added to `apps/web/src/hooks/useApi.ts` |

**P9-001 Remediation (requires human review):**
| ID | Task | Description | Status |
|----|------|-------------|--------|
| P9-001a | Add tenant_id FK | Add tenant_id to 12+ models + migration | Pending |
| P9-001b | Update endpoints | Update all endpoints with require_tenant | Pending |
| P9-001c | JWT tenant_id | Make JWT tenant_id REQUIRED | Pending |
| P9-001d | API key validation | Implement API key validation | Pending |
| P9-001e | Audit log endpoints | Create audit log query endpoints | ✅ Done (GAP-P0-006) |

These remediation items were identified during P9-001 security audit and should be addressed before production deployment.

---

## 3.5) Deployment Status (PAUSED)

**Last Updated:** 2026-01-09
**Status:** Paused - Railway trial expired, waiting for upgrade

### Infrastructure Ready ✅
| Service | Provider | Status | Details |
|---------|----------|--------|---------|
| Database | Supabase PostgreSQL | ✅ Ready | `aws-1-ap-south-1.pooler.supabase.com:5432` |
| Redis | Upstash | ✅ Ready | `welcomed-boar-9893.upstash.io:6379` (TLS) |
| GitHub Repo | GitHub | ✅ Ready | `sweiloon/agentverse` (public) |
| Frontend | Vercel | ✅ Deployed | `web-lilac-eight-56.vercel.app` |
| Backend API | Railway | ⏸️ Paused | Trial expired - needs upgrade ($5/month) |

### Railway Project Details
- **Project Name:** unique-mercy
- **Project URL:** https://railway.com/project/814d1dba-157a-4609-a1ec-ef55f10719e3
- **Issue:** Trial expired - requires Hobby plan upgrade ($5/month)

### Environment Variables (Already Configured in Railway)
```bash
DATABASE_URL=postgresql+asyncpg://postgres.rrmanrmilwjnahplpukg:[PASSWORD]@aws-1-ap-south-1.pooler.supabase.com:5432/postgres
REDIS_URL=rediss://default:[PASSWORD]@welcomed-boar-9893.upstash.io:6379
SECRET_KEY=[GENERATED]
OPENROUTER_API_KEY=[YOUR_KEY]
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
DEFAULT_MODEL=openai/gpt-4o-mini
CORS_ORIGINS=["http://localhost:3000","http://localhost:3002","https://web-lilac-eight-56.vercel.app"]
ENVIRONMENT=production
DEBUG=false
```

### Steps to Continue Deployment (When Ready)
1. **Upgrade Railway** to Hobby plan ($5/month)
   - Go to: https://railway.com/workspace/upgrade
   - Select Hobby plan

2. **Delete misconfigured service** (`@agentverse/web`)
   - The auto-detected service has wrong configuration
   - Go to service settings → Delete service

3. **Create new service from GitHub**
   - Click "Create" → "GitHub Repo"
   - Select `sweiloon/agentverse`
   - **IMPORTANT Settings:**
     - Root Directory: `apps/api`
     - Builder: Dockerfile
     - Railway Config File: `railway.json` (relative path, NOT `/apps/api/railway.json`)
     - Leave Build/Start commands empty (Dockerfile handles this)

4. **Copy environment variables** from old service to new service

5. **Generate domain** once deployed
   - Settings → Networking → Generate Domain

6. **Update frontend** with API URL
   - Add new Railway domain to `CORS_ORIGINS`
   - Update `NEXT_PUBLIC_API_URL` in Vercel

### Alternative: Render.com
If Railway doesn't work, Render has:
- Free tier available ($0/month, 512MB RAM)
- `render.yaml` already configured in `apps/api/`
- Email verified for `magicpattern@gmail.com`

---

## 4) Critical Invariants

1. **Fork-not-mutate:** Any change to outcomes creates a new Node; parent Node is NEVER modified
2. **Replay-read-only:** 2D replay uses telemetry query ONLY; never triggers simulation
3. **Artifact versioning:** All artifacts have version fields (engine, ruleset, dataset, schema)
4. **Determinism:** Same RunConfig + seed = same aggregated outcome (tested in CI)
5. **UI-is-not-truth:** All truth in persisted artifacts; UI reads from API
6. **No hard caps on futures:** Use clustering + progressive expansion

---

## 5) Repo Map

```
agentverse/
├── apps/
│   ├── web/                   # Next.js 14 Frontend (Vercel)
│   │   └── src/
│   │       ├── app/           # Pages (restructure needed)
│   │       ├── components/    # React components
│   │       ├── hooks/         # React hooks
│   │       └── lib/           # Utilities, API client
│   └── api/                   # FastAPI Backend
│       └── app/
│           ├── models/        # SQLAlchemy models (refactor needed)
│           ├── schemas/       # Pydantic schemas (refactor needed)
│           ├── api/v1/        # API endpoints
│           ├── core/          # Config, security
│           └── tasks/         # Celery tasks
│       └── alembic/
│           └── versions/
│               ├── 0001_...   # Original migration
│               └── 0002_...   # NEW: Spec-compliant schema
├── packages/
│   ├── types/                 # Shared TS types (refactor needed)
│   ├── ui/                    # Shared UI components
│   └── contracts/             # NEW: Shared TypeScript contracts
│       └── src/
│           ├── common.ts      # Shared types
│           ├── project.ts     # ProjectSpec (§6.1)
│           ├── persona.ts     # Persona (§6.2)
│           ├── agent.ts       # Agent (§6.3)
│           ├── event-script.ts # EventScript (§6.4)
│           ├── run.ts         # RunConfig/Run (§6.5-6.6)
│           ├── node.ts        # Node/Edge (§6.7)
│           ├── telemetry.ts   # Telemetry (§6.8)
│           ├── reliability.ts # ReliabilityReport (§7.1)
│           ├── versioning.ts  # Version utilities
│           ├── rng.ts         # RNG policy
│           └── index.ts       # Exports
├── docs/
│   ├── project.md             # Spec: Project Development Manual
│   └── Interaction_design.md  # Spec: Interaction Design
├── todo.md                    # Complete task list
└── CLAUDE.md                  # This file
```

---

## 6) Decision Log (Last 5)

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-09 | Created LLMRouter centralized gateway | Admin-controlled model selection, cost tracking, caching (GAPS.md GAP-P0-001) |
| 2026-01-09 | Created CI check for LLM usage | Prevent direct OpenRouter calls outside LLMRouter |
| 2026-01-08 | Created @agentverse/contracts package | TypeScript contracts for frontend/backend sharing |
| 2026-01-08 | Created spec-compliant migration 0002 | New schema matches project.md §6 exactly |
| 2026-01-08 | Added versioning.ts with semver utilities | Reproducibility requires strict versioning (§6.5) |

---

## 7) Decisions Made (Features to Remove/Keep)

| Feature | Decision | Reason |
|---------|----------|--------|
| Products | REMOVE | Not in spec |
| Focus Groups | REMOVE | Not in spec |
| Marketplace | REPURPOSE → Templates | Spec §5.6 mentions templates |
| Old Simulations/Scenarios | REMOVE | Replaced by Node/Run system |
| World | REWORK | Becomes telemetry replay only |

---

## 8) Development Workflow Rules

**IMPORTANT: Always follow these rules during development:**

1. **Update todo.md after completing tasks:**
   - Mark tasks as `[x]` Done immediately when completed
   - Add completion date and brief note
   - Update the Summary Counts table

2. **Check specs after each phase:**
   - Review project.md to ensure alignment with spec
   - Review Interaction_design.md to ensure UI matches design
   - Verify todo.md tasks align with spec requirements

3. **Update CLAUDE.md at end of each session:**
   - Update current phase and focus
   - Update next 5-10 tasks list
   - Record what was completed in session log
   - Add any decisions made to decision log

4. **Before starting new phase:**
   - Verify all tasks in current phase are complete
   - Run type-check to ensure no TypeScript errors
   - Cross-reference with project.md phase definitions

---

## 9) Session Log

### 2026-01-09 (Current Session - Deployment Attempt)
- **Deployment Infrastructure Setup:**
  - Supabase PostgreSQL ✅ - Database ready with migrations run
  - Upstash Redis ✅ - Connected and tested
  - GitHub repo ✅ - `sweiloon/agentverse` pushed
  - Vercel frontend ✅ - `web-lilac-eight-56.vercel.app` deployed
- **Railway Deployment Attempt:**
  - Created project "unique-mercy"
  - Service auto-detected as `@agentverse/web` (wrong - frontend instead of API)
  - Multiple build failures: "Dockerfile does not exist" due to path configuration issues
  - Root cause: Railway Config File set to `/apps/api/railway.json` caused path doubling with Root Directory `/apps/api`
  - Attempted UI fixes but combobox didn't allow direct text editing
  - **Trial expired** - Railway requires Hobby plan upgrade ($5/month) to continue
- **Decision:** Paused deployment until Railway upgrade
- **Documentation:** Added Section 3.5 to CLAUDE.md with full deployment instructions for later

### 2026-01-09 (Earlier - LLM Router Implementation)
- **GAP-P0-001: LLM Router Implementation ✅**
  - **SPEC_COVERAGE.md:** Created comprehensive spec coverage audit
  - **GAPS.md:** Created prioritized gaps report with P0/P1/P2 priorities
  - **LLM Router Core:**
    - Created `app/services/llm_router.py` - Central LLM gateway (~500 lines)
    - Created `app/models/llm.py` - SQLAlchemy models (LLMProfile, LLMCall, LLMCache)
    - Created `app/schemas/llm.py` - Pydantic schemas for API
    - Created migration `2026_01_09_0001_add_llm_router_tables.py`
    - Seeded 10 default profiles (EVENT_COMPILER_*, PERSONA_*, DEEP_SEARCH, etc.)
  - **Admin API:**
    - Created `app/api/v1/endpoints/llm_admin.py`
    - Endpoints: GET/POST/PATCH/DELETE profiles, GET calls, GET costs
    - Updated `app/api/v1/router.py` to include llm_admin routes
  - **CI Enforcement:**
    - Created `scripts/check_llm_usage.py` - Blocks direct OpenRouter usage
    - Checks for imports, instantiation, direct method calls
  - **Service Refactoring:**
    - Refactored `event_compiler.py` to use LLMRouter
    - Refactored `ai_research.py` to use LLMRouter (3 LLM calls)
    - Refactored `focus_group.py` to use LLMRouter (1 LLM call, streaming kept)
    - Refactored `persona_expansion.py` to use LLMRouter
  - **Legacy Services (Not Refactored):**
    - `product_execution.py` - Uses batch_complete (feature marked for removal)
    - `simulation.py` - Uses batch_complete (feature marked for removal)
  - CI check passes ✅

### 2026-01-09 (Earlier - Phase 8)
- **Phase 8 COMPLETE ✅:**
  - **P8-001:** Telemetry Query Service - Already done (Phase 1 telemetry)
  - **P8-002:** Deterministic Replay Loader
    - Added `loadReplay`, `getReplayStateAtTick`, `getReplayChunk`, `seekReplay` methods to ApiClient
    - Added React Query hooks: `useLoadReplay`, `useReplayState`, `useReplayChunk`, `useSeekReplay`
    - Created replay types: `LoadReplayRequest`, `ReplayTimeline`, `ReplayWorldState`, `ReplayChunk`
  - **P8-003:** 2D Layout Profiles
    - Created `ZoneDefinition` type for semantic zones
    - DEFAULT_ZONES in ReplayPlayer: Supporters, Neutral, Skeptics, Observers
    - Agent placement based on segment
  - **P8-004:** Rendering Mappings
    - Created `ReplayCanvas.tsx` (~400 lines) with stance/emotion/influence color mappings
    - Layer visibility toggles for each dimension
    - Agent sprites with color-coded rings based on state
  - **P8-005:** 2D Replay Page UI (C3 Compliant - READ-ONLY)
    - Created `ReplayPlayer.tsx` (~500 lines) - main container with playback controls
    - Created `ReplayControls.tsx` - play/pause/seek/speed controls
    - Created `ReplayLayerPanel.tsx` - layer toggles, segment/region filters
    - Created `ReplayTimeline.tsx` - bottom timeline with metrics
    - Created `ReplayInspector.tsx` - agent detail panel
    - Updated `/dashboard/projects/[id]/replay/page.tsx` to use ReplayPlayer
    - Fetches telemetry_ref from SpecRun.outputs to load replay data
  - **P8-006:** Explain-on-Click
    - Enhanced ReplayPlayer with `useReplayAgentHistory` and `useReplayEventsAtTick` hooks
    - Added `storageRef` prop to ReplayPlayer for fetching agent-specific data
    - Transform API data to `AgentHistoryPoint[]` and `AgentEvent[]` for ReplayInspector
    - Shows agent state, stance/emotion trends, recent events when clicking agent
  - Type check passed ✅
  - Updated todo.md: 76 done, 20 pending (79% completion)

### 2026-01-09 (Earlier - Phase 5)
- **Phase 5 COMPLETE ✅:**
  - **P5-001:** Target Persona Compiler (backend)
  - **P5-002:** Action Space Definition (backend)
  - **P5-003:** Constraint System (backend)
  - **P5-004:** Path Planner (backend)
  - **P5-005:** Path → Node Bridge (backend)
  - **P5-006:** Target Mode Telemetry (backend)
  - **P5-007:** Target Mode Studio UI
    - Created `components/target-mode/TargetModeStudio.tsx` - main 4-panel studio layout
    - Created `components/target-mode/TargetPersonaPanel.tsx` - persona selection, utility profile display
    - Created `components/target-mode/ContextPanel.tsx` - constraints, starting node, initial state
    - Created `components/target-mode/ActionSetPanel.tsx` - action cards with category filters
    - Created `components/target-mode/PlannerPanel.tsx` - planner config sliders, run button
    - Created `components/target-mode/ResultsPanel.tsx` - path clusters, expand, branch to node
    - Created `components/target-mode/index.ts` - exports
    - Updated `/dashboard/projects/[id]/target-mode/page.tsx` to use TargetModeStudio
    - Added ~350 lines of Target Mode types and API methods to `lib/api.ts`
    - Added ~170 lines of Target Mode React Query hooks to `hooks/useApi.ts`
  - Type check passed ✅
  - Updated todo.md: 62 done, 33 pending (65% completion)

### 2026-01-09 (Earlier - Phase 4)
- **Phase 4 COMPLETE ✅:**
  - **P4-001:** Intent & Scope Analyzer
    - Created `app/services/event_compiler.py` with `EventCompiler` class
    - `analyze_intent()` classifies prompts as event/variable/query/comparison/explanation
    - Extracts scope: regions, segments, time window
    - C5 compliant: LLMs compile once, execute deterministically
  - **P4-002:** Decomposer
    - `decompose_prompt()` breaks one prompt into multiple sub-effects
    - Each sub-effect is granular (one variable/perception each)
    - Extracts affected target types (environment, perception, network)
  - **P4-003:** Variable Mapper
    - `map_variables()` maps sub-effects to concrete variable deltas
    - Supports domain template variable catalogs
    - Includes confidence scores for uncertain mappings
  - **P4-004:** Scenario Generator
    - `generate_scenarios()` creates candidate scenarios from variable deltas
    - No artificial cap on scenario count (G5 compliance)
    - Each scenario has probability estimate and variable deltas
  - **P4-005:** Clustering Algorithm
    - `cluster_scenarios()` groups scenarios by intervention magnitude
    - K-means-like approach for clustering
    - Cluster nodes represent aggregated probability
  - **P4-006:** Progressive Expansion API
    - Created `/ask/expand-cluster` endpoint
    - `expand_cluster()` reveals child scenarios within cluster
    - Supports multiple expansion levels
  - **P4-007:** Explanation Generator
    - `generate_explanation()` creates causal chain summaries
    - Key variable drivers ranked by influence
    - Uncertainty notes for low-confidence mappings
  - **P4-008:** Ask Drawer UI
    - Created `components/nodes/AskDrawer.tsx` (~500 lines)
    - Prompt input with example prompts
    - Advanced settings (max scenarios, clustering toggle)
    - Compilation results: intent summary, sub-effects, variable mappings
    - Cluster accordion with expand/collapse
    - Scenario selection and execution
    - Integrated into UniverseMap with "Ask" button
  - **API Types & Hooks:**
    - Added Ask types to `lib/api.ts`: AskIntentType, AskPromptScope, AskCompilationResult, etc.
    - Added API methods: compileAskPrompt, expandAskCluster, executeAskScenario, etc.
    - Created React Query hooks in `hooks/useApi.ts`
  - Type check passed ✅
  - Updated todo.md: 55 done, 40 pending (57% completion)

### 2026-01-09 (Earlier - Phase 3)
- **Phase 3 COMPLETE ✅:**
  - **P3-001:** Event Script Schema & Executor
    - Created `app/schemas/event_script.py` with comprehensive Pydantic schemas
    - Created `app/engine/event_executor.py` with deterministic event execution
    - IntensityProfile supports: instantaneous, linear_decay, exponential_decay, lagged, pulse, step, custom
    - DeltaOperation supports: set, add, multiply, min, max
    - C5 compliant: events pre-compiled, executed without LLM at runtime
  - **P3-002:** Event Bundle Support
    - EventBundle model for grouping related events
    - EventBundleMember junction table for membership
    - Bundle execution API with joint probability
    - Atomic application of multiple events
  - **P3-003:** Telemetry Event Trigger Logging
    - EventTriggerLog model for tracking event triggers
    - Captures: trigger source, affected agent count, tick, intensity
    - Query endpoints for trigger history
  - **P3-004:** Event Versioning
    - event_version, schema_version fields on EventScript
    - ProvenanceSchema with compiler_version, compiled_at, compiled_from
    - Version bumping on updates
  - **API Endpoints:** Created `app/api/v1/endpoints/event_scripts.py`:
    - CRUD for event scripts with validation
    - Event bundle management
    - Event execution with trigger logging
    - Trigger log queries
    - Statistics endpoint
  - Type check passed ✅
  - Updated todo.md: 47 done, 48 pending (49% completion)

### 2026-01-09 (Earlier - Phase 2)
- **Phase 2 COMPLETE ✅:**
  - **P2-008:** Universe Map Graph Canvas - Wired page to use existing components
    - Updated `/app/dashboard/projects/[id]/universe-map/page.tsx` to use `UniverseMap` component
    - Uses `useProject()` context for projectId
    - Full SVG tree layout with pan/zoom, node selection, fork actions, path analysis
    - Controls bar with zoom, clusters, filters, refresh
    - Sidebar with node details, fork button, run navigation
    - Type check passed ✅
- **UI-011: Compare View COMPLETE ✅:**
  - Created `CompareView` component at `components/nodes/CompareView.tsx`:
    - Side-by-side comparison of 2-4 nodes
    - Collapsible sections: Outcomes, Key Differences, Reliability
    - TrendIndicator showing percentage changes vs baseline
    - Pin baseline functionality
    - Export compare summary to JSON
    - Loading/error states with retry
  - Integrated into `UniverseMap` component:
    - Compare mode toggle button in header
    - Compare mode indicator bar with selection count
    - Multi-select support via shift+click
    - Purple highlighting for compare-selected nodes in canvas
    - CompareView tray appears at bottom when in compare mode
  - Updated `UniverseMapCanvas` with `compareNodeIds` prop for visual highlighting
  - Type check passed ✅
- **Alignment Verification:**
  - Verified todo.md aligns with project.md and Interaction_design.md
  - 44.8% completion rate (43 done, 52 pending)
  - All constraints (C0-C6) being respected
  - Phase 0-2 complete, UI-011 complete, ready for Phase 3

### 2026-01-08 (Previous Session)
- **Phase 0 COMPLETE ✅:**
  - **P0-001:** Created @agentverse/contracts package with all data contracts
  - **P0-002:** Added versioning.ts with version utilities
  - **P0-003:** Added rng.ts with RNG policy and seed utilities
  - **P0-004:** Created migration 0002 with spec-compliant schema
  - **P0-005:** Created storage.py with S3/local backends
  - **P0-006:** Created job queue with tenant-aware Celery tasks
  - **P0-007:** Created tenant middleware with context propagation
  - **P0-008:** Enhanced permissions with spec-compliant RBAC
  - **P0-009:** Created rate limiting and quota management
  - **P0-010:** Enhanced audit service with tenant-aware logging
- **Phase 1 COMPLETE ✅:**
  - **P1-001:** Created rules.py with RuleEngine, 4 built-in rules (Conformity, MediaInfluence, LossAversion, SocialNetwork)
  - **P1-002:** Created agent.py with Agent state machine, AgentFactory, AgentPool, AgentMemory
  - **P1-003:** Created node_service.py with NodeService, Node/Edge/Cluster models, path analysis, Universe Map state
  - **P1-004:** Full run_executor.py with simulation loop, node outcome updates, deterministic RNG
  - **P1-005:** Created telemetry.py with TelemetryService, TelemetryWriter, keyframe/delta storage, query APIs
  - **P1-006:** Created simulation_orchestrator.py integrating all Phase 1 components

### Phase 1 Component Summary
| Component | File | Description |
|-----------|------|-------------|
| Rule Engine | `app/engine/rules.py` | Society Mode rule evaluation, 4 built-in rules |
| Agent State Machine | `app/engine/agent.py` | Agent lifecycle, factory, pool, memory |
| Node Service | `app/services/node_service.py` | Universe Map, fork-not-mutate, path analysis |
| Run Executor | `app/tasks/run_executor.py` | Celery task, simulation execution, outcome aggregation |
| Telemetry Service | `app/services/telemetry.py` | Keyframes, deltas, queries, replay (C3 compliant) |
| Orchestrator | `app/services/simulation_orchestrator.py` | Phase 1 integration, run lifecycle, batch ops |
| Persona Expansion | `app/services/persona_expansion.py` | LLM-powered persona expansion (C5 compliant) |

### Phase 2 - API Layer COMPLETED ✅
- **P2-001:** Created `/runs` endpoints - create, start, cancel, progress, results
- **P2-002:** Created `/nodes` endpoints - list, fork, children, edges, compare, path-analysis
- **P2-003:** Created `/project-specs` endpoints - CRUD, stats, duplicate, create-run
- **P2-004:** Created `/telemetry` endpoints - index, slice, keyframe, agent history, events, stream
- **P2-005:** Universe Map API integrated into `/nodes/universe-map/{project_id}`

### Phase 2 API Endpoints Summary
| Endpoint | File | Description |
|----------|------|-------------|
| `/runs` | `app/api/v1/endpoints/runs.py` | Run lifecycle, batch ops, progress streaming |
| `/nodes` | `app/api/v1/endpoints/nodes.py` | Universe Map, fork, compare, path analysis |
| `/telemetry` | `app/api/v1/endpoints/telemetry.py` | Read-only telemetry queries (C3 compliant) |
| `/project-specs` | `app/api/v1/endpoints/project_specs.py` | Spec-compliant project management |

### Phase 2 - Frontend Components COMPLETED ✅
- **P2-010:** Created ForkTuneDrawer component with:
  - Variable groups (economy, media, social, trust) as accordions
  - Slider + numeric input for each variable
  - Intervention magnitude calculation with warnings
  - Auto-start run option after fork
  - Integration with Node detail page

### Phase 2 Frontend Summary
| Component | File | Description |
|-----------|------|-------------|
| ForkTuneDrawer | `components/nodes/ForkTuneDrawer.tsx` | Variable tuning drawer for forking nodes |
| Slider | `components/ui/slider.tsx` | Radix UI slider component |
| Node Detail | `app/dashboard/nodes/[id]/page.tsx` | Node viewer with Fork & Tune integration |
| CompareView | `components/nodes/CompareView.tsx` | Side-by-side node comparison (2-4 nodes) |

### UI-004: Create Project Wizard COMPLETED ✅
- **UI-004:** Created 5-step project creation wizard at `/dashboard/projects/new/page.tsx`:
  - Step 1: Goal input with domain hints, sensitive domain checkbox
  - Step 2: Core recommendation (Collective/Targeted/Hybrid) with auto-recommendation based on keywords
  - Step 3: Data & Personas source selection (Template/Upload/Generate/Search)
  - Step 4: Output metrics selection with checkboxes (Reliability Report required)
  - Step 5: Review & Create summary with project name input
  - Integrated with `useCreateProjectSpec()` mutation hook
  - Type check passed ✅

### UI-005: Project Overview Page COMPLETED ✅
- **UI-005:** Rewrote project overview page at `/dashboard/projects/[id]/page.tsx`:
  - Top summary (domain, prediction core, default horizon, last updated)
  - Baseline block with dynamic "Run Baseline" CTA (shows when no root node)
  - Latest node card with probability and confidence level
  - Reliability summary block (calibration, stability, drift, data gaps)
  - Stats row (nodes, runs, completed, agents)
  - Suggested actions grid (Universe Map, Ask, Personas, Calibrate)
  - Uses NodeSummary type correctly from API hooks
  - Type check passed ✅

### UI-006: Personas Studio COMPLETED ✅
- **UI-006:** Rebuilt Personas page as three-panel Studio at `/dashboard/personas/page.tsx`:
  - **Left panel:** Sources (grouped by type) + Segments with counts and filters
  - **Center panel:** Source cards grid or persona list with table view
  - **Right drawer:** Persona Inspector with demographics, psychographics, behavioral data
  - Quick stats (total personas, source counts)
  - Source type filters (Uploaded, Generated, Deep Search)
  - Segment filters with region-based grouping
  - Action buttons: Import Personas, Generate, Deep Search
  - Validate Set button (placeholder)
  - Breadcrumb navigation between sources and persona lists
  - Persona rows with confidence score, region, source badge
  - Empty state with quick-start actions
  - Type check passed ✅

### UI-001: Global Navigation Restructure COMPLETED ✅
- **UI-001:** Restructured global navigation per Interaction_design.md §2.1:
  - Updated sidebar.tsx with new navigation items:
    - Dashboard, Projects, Templates, Calibration Lab, Runs & Jobs, Admin, Settings
  - Admin nav item is role-gated (only visible to admin users)
  - Created Templates page at `/dashboard/templates/page.tsx`:
    - Adapted from marketplace, serves as domain templates library
    - Template type filters (Domain, Rules, Personas)
    - Grid/list view toggle, search, sorting
  - Created Calibration Lab page at `/dashboard/calibration/page.tsx`:
    - Historical scenario selector
    - Parameter tuning panel (bounded)
    - Leakage prevention warning
    - Validation results display
  - Created Admin page at `/dashboard/admin/page.tsx`:
    - Tenants tab with organization management
    - Quotas tab with resource usage monitoring
    - Audit logs tab with event history
    - Policies tab with flag toggles
  - Type check passed ✅

### UI-002: Project-Level Navigation COMPLETED ✅
- **UI-002:** Implemented project-level navigation per Interaction_design.md §2.2:
  - Created `/components/project/ProjectContext.tsx`:
    - React Context for sharing project data across nested routes
    - Uses useProjectSpec, useProjectSpecStats, useNodes hooks
    - Provides project, stats, nodes, rootNode, loading/error states
  - Created `/components/project/ProjectTabNav.tsx`:
    - 9 horizontal tabs: Overview, Universe Map, Personas, Society Mode, Target Mode, Reliability, 2D Replay, Exports, Settings
    - Active state detection using usePathname()
    - Settings tab role-gated for admin users
    - Overflow scroll for mobile responsiveness
    - Cyberpunk styling with cyan accent
  - Created `/components/project/ProjectHeader.tsx`:
    - Project name with back navigation to Projects list
    - Domain badge
    - Quick stats (node count, run count, last run date)
  - Created `/components/project/PlaceholderPage.tsx`:
    - Reusable "Coming Soon" placeholder for pending implementations
  - Created `/app/dashboard/projects/[id]/layout.tsx`:
    - Wraps all project sub-pages with ProjectProvider
    - Renders ProjectHeader and ProjectTabNav
  - Created 8 tab page files (all using PlaceholderPage initially):
    - `/universe-map/page.tsx` - Universe Map visualization
    - `/personas/page.tsx` - Project-scoped personas
    - `/society-mode/page.tsx` - Collective rule configuration
    - `/target-mode/page.tsx` - Individual simulation setup
    - `/reliability/page.tsx` - Reliability reports
    - `/replay/page.tsx` - 2D Replay viewer (C3: read-only)
    - `/exports/page.tsx` - Export configurations
    - `/settings/page.tsx` - Project settings (admin-gated)
  - Type check passed ✅

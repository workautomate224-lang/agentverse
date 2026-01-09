# AgentVerse Spec Coverage Matrix

**Generated:** 2026-01-09
**Purpose:** Map project.md + Interaction_design.md spec items to implementation locations
**Status Legend:**
- ✅ Complete - Fully implemented and spec-compliant
- 🟡 Partial - Implemented but missing features or has issues
- ❌ Missing - Not implemented
- ⚠️ Risky/Incorrect - Implementation deviates from spec or has security issues

---

## Table of Contents

1. [project.md Coverage](#1-projectmd-coverage)
   - [Section 1: Product Principles](#11-section-1-product-principles-p1-p6)
   - [Section 6: Data Contracts](#12-section-6-data-contracts-schemas)
   - [Section 7: Reliability & Calibration](#13-section-7-reliability--calibration-contracts)
   - [Section 8: Security, Privacy, Abuse Prevention](#14-section-8-security-privacy-abuse-prevention)
   - [Section 9: Performance & Scalability](#15-section-9-performance--scalability)
   - [Section 10: Testing & QA](#16-section-10-testing--qa)
   - [Section 11: Phase Plan](#17-section-11-phase-plan)
2. [Interaction_design.md Coverage](#2-interaction_designmd-coverage)
   - [Section 1: Global UX Principles](#21-section-1-global-ux-principles-g1-g7)
   - [Section 5: Page Specifications](#22-section-5-page-specifications)
3. [LLM Integration Coverage](#3-llm-integration-coverage)
4. [Critical Issues Summary](#4-critical-issues-summary)

---

## 1. project.md Coverage

### 1.1 Section 1: Product Principles (P1-P6)

| Spec Item | Implementation Location | Status | Notes |
|-----------|------------------------|--------|-------|
| **P1 - Reversible-by-design** | `apps/api/app/services/node_service.py` | ✅ Complete | Fork creates new Node, parent never mutated |
| | `components/nodes/ForkTuneDrawer.tsx` | ✅ Complete | UI communicates "Forking from Node X" |
| **P2 - On-demand execution** | `apps/api/app/tasks/run_executor.py` | ✅ Complete | Runs only on explicit triggers |
| | `components/replay/ReplayPlayer.tsx` | ✅ Complete | Replay marked as read-only, no run triggers |
| **P3 - Auditable predictions** | `apps/api/app/services/audit.py` | ✅ Complete | Audit logging for all actions |
| | `apps/api/app/services/reliability/` | ✅ Complete | Full reliability suite |
| **P4 - Separation of concerns** | `apps/api/app/engine/` | ✅ Complete | Headless engine, separate telemetry renderer |
| | `apps/api/app/services/event_compiler.py` | ✅ Complete | LLMs compile once (C5), not per-tick |
| **P5 - Progressive complexity** | All UI components | ✅ Complete | Advanced controls hidden behind accordions |
| **P6 - Production from Day 1** | `apps/api/app/middleware/tenant.py` | 🟡 Partial | Infrastructure exists but NOT enforced everywhere |
| | `apps/api/app/core/rate_limiter.py` | ✅ Complete | Rate limiting implemented |
| | `apps/api/app/services/audit.py` | 🟡 Partial | No query endpoints |

### 1.2 Section 6: Data Contracts (Schemas)

| Spec Item | Implementation Location | Status | Notes |
|-----------|------------------------|--------|-------|
| **§6.1 ProjectSpec** | `apps/api/app/schemas/spec_project.py` | ✅ Complete | All required fields present |
| | `apps/api/app/api/v1/endpoints/project_specs.py` | ✅ Complete | CRUD with tenant scoping |
| **§6.2 Persona** | `apps/api/app/schemas/persona.py` | ✅ Complete | Canonical form with versioning |
| | `apps/api/app/models/persona.py` | ⚠️ Risky | Missing tenant_id FK |
| **§6.3 Agent** | `apps/api/app/engine/agent.py` | ✅ Complete | Runtime instance with state vector |
| | `apps/api/app/models/agent.py` | ⚠️ Risky | Missing tenant_id FK |
| **§6.4 EventScript** | `apps/api/app/schemas/event_script.py` | ✅ Complete | Full schema with intensity profiles |
| | `apps/api/app/engine/event_executor.py` | ✅ Complete | 7 intensity profiles, deterministic |
| | `apps/api/app/models/event_script.py` | ✅ Complete | Has tenant_id FK |
| **§6.5 RunConfig** | `apps/api/app/schemas/spec_run.py` | ✅ Complete | Versions, seed, horizon, scenario patch |
| **§6.6 Run Artifact** | `apps/api/app/schemas/spec_run.py` | ✅ Complete | Status transitions, timing, outputs |
| | `apps/api/app/api/v1/endpoints/runs.py` | ✅ Complete | Full lifecycle with tenant scoping |
| **§6.7 Node/Edge** | `apps/api/app/models/node.py` | ✅ Complete | Has tenant_id FK, proper relationships |
| | `apps/api/app/services/node_service.py` | ✅ Complete | Fork mechanics, path analysis |
| | `apps/api/app/api/v1/endpoints/nodes.py` | ✅ Complete | Universe Map API with tenant scoping |
| **§6.8 Telemetry** | `apps/api/app/schemas/telemetry.py` | ✅ Complete | Keyframes, deltas, indexes |
| | `apps/api/app/services/telemetry.py` | ✅ Complete | Read-only queries (C3 compliant) |

### 1.3 Section 7: Reliability & Calibration Contracts

| Spec Item | Implementation Location | Status | Notes |
|-----------|------------------------|--------|-------|
| **§7.1 Reliability Report** | `apps/api/app/services/reliability/report_generator.py` | ✅ Complete | All sections present |
| **§7.2 Anti-leakage guardrails** | `apps/api/app/services/reliability/historical_runner.py` | ✅ Complete | LeakageValidator with time cutoffs |

### 1.4 Section 8: Security, Privacy, Abuse Prevention

| Spec Item | Implementation Location | Status | Notes |
|-----------|------------------------|--------|-------|
| **§8.1 Multi-tenancy** | `apps/api/app/middleware/tenant.py` | 🟡 Partial | Infrastructure OK, NOT enforced on all endpoints |
| | Database models | ⚠️ Risky | **13 models missing tenant_id** |
| | API endpoints | ⚠️ Risky | **17 endpoint files missing require_tenant** |
| **§8.2 Auth & permissions** | `apps/api/app/core/security.py` | ✅ Complete | Roles: Owner/Admin/Analyst/Viewer |
| | `apps/api/app/core/permissions.py` | ✅ Complete | Permission checks per endpoint |
| **§8.3 Rate limiting & quotas** | `apps/api/app/core/rate_limiter.py` | ✅ Complete | Redis-based, per-tenant |
| | `apps/api/app/core/quotas.py` | ✅ Complete | Job quotas implemented |
| **§8.4 Data protection** | `apps/api/app/services/secrets.py` | ✅ Complete | SecretManager with rotation |
| | `apps/api/app/services/storage.py` | ✅ Complete | Signed URLs for telemetry |
| **§8.5 Safety/ethical** | `apps/api/app/services/audit.py` | 🟡 Partial | Audit logs exist, NO query endpoint |

### 1.5 Section 9: Performance & Scalability

| Spec Item | Implementation Location | Status | Notes |
|-----------|------------------------|--------|-------|
| **§9.1 Frontend performance** | `components/ui/virtualized-list.tsx` | ✅ Complete | VirtualizedList, InfiniteScroll |
| | `hooks/useIncrementalLayout.ts` | ✅ Complete | Incremental graph layout |
| **§9.2 Backend performance** | `apps/api/app/tasks/` | ✅ Complete | Async runs via Celery |
| | Redis caching | ✅ Complete | Hot nodes cached |
| **§9.3 Engine performance** | `apps/api/app/engine/rules.py` | ✅ Complete | Rule-driven, no LLM-in-loop |

### 1.6 Section 10: Testing & QA

| Spec Item | Implementation Location | Status | Notes |
|-----------|------------------------|--------|-------|
| **§10.1 Determinism tests** | `apps/api/tests/determinism/` | ✅ Complete | Same seed = same outcome |
| **§10.2 Simulation validity** | Unit tests | 🟡 Partial | Tests exist, coverage unknown |
| **§10.3 Reliability tests** | Calibration tests | ✅ Complete | Drift detection tests |

### 1.7 Section 11: Phase Plan

| Phase | Components | Implementation Status | Notes |
|-------|-----------|----------------------|-------|
| **Phase 0** | Contracts, versioning, determinism | ✅ Complete | All 12 tasks done |
| **Phase 1** | Society Engine, telemetry | ✅ Complete | All 9 tasks done |
| **Phase 2** | Node/Edge graph, forking | ✅ Complete | All 10 tasks done |
| **Phase 3** | Event System | ✅ Complete | All 4 tasks done |
| **Phase 4** | Event Compiler | ✅ Complete | All 8 tasks done |
| **Phase 5** | Target Mode | ✅ Complete | All 7 tasks done |
| **Phase 6** | Hybrid Mode | ✅ Complete | All 3 tasks done |
| **Phase 7** | Calibration & Reliability | ✅ Complete | All 9 tasks done |
| **Phase 8** | Telemetry Replay | ✅ Complete | All 6 tasks done |
| **Phase 9** | Production Hardening | ⚠️ Risky | P9-001 remediation REQUIRED |

---

## 2. Interaction_design.md Coverage

### 2.1 Section 1: Global UX Principles (G1-G7)

| Principle | Implementation | Status | Notes |
|-----------|---------------|--------|-------|
| **G1 - Truth is persisted artifacts** | All UI reads from API | ✅ Complete | No local state as truth |
| **G2 - Reversible = forks** | ForkTuneDrawer.tsx | ✅ Complete | "Forking from Node X" shown |
| **G3 - Progressive disclosure** | Accordion components | ✅ Complete | Advanced controls hidden |
| **G4 - Fast feedback** | Optimistic UI | ✅ Complete | Immediate run_id return |
| **G5 - No hard caps, use clustering** | AskDrawer.tsx | ✅ Complete | Progressive expansion |
| **G6 - Visualization read-only** | ReplayPlayer.tsx | ✅ Complete | C3 compliant |
| **G7 - Safety, auditability** | Audit service | 🟡 Partial | Missing query endpoints |

### 2.2 Section 5: Page Specifications

| Spec Section | Title | Implementation | Status |
|--------------|-------|----------------|--------|
| **§5.1** | Dashboard | `app/dashboard/page.tsx` | ✅ Complete |
| **§5.2** | Projects List | `app/dashboard/projects/page.tsx` | ✅ Complete |
| **§5.3** | Create Project Wizard | `app/dashboard/projects/new/page.tsx` | ✅ Complete |
| **§5.4** | Project Overview | `app/dashboard/projects/[id]/page.tsx` | ✅ Complete |
| **§5.5** | Personas Studio | `app/dashboard/personas/page.tsx` | ✅ Complete |
| **§5.6** | Templates & Rule Packs | `app/dashboard/templates/page.tsx` | ✅ Complete |
| **§5.7** | Universe Map (Core) | `components/universe-map/UniverseMap.tsx` | ✅ Complete |
| **§5.8** | Node Inspector | Drawer in UniverseMap | ✅ Complete |
| **§5.9** | Ask Drawer | `components/nodes/AskDrawer.tsx` | ✅ Complete |
| **§5.10** | Fork & Tune Drawer | `components/nodes/ForkTuneDrawer.tsx` | ✅ Complete |
| **§5.11** | Compare View | `components/nodes/CompareView.tsx` | ✅ Complete |
| **§5.12** | Society Mode Studio | `components/society-mode/SocietyModeStudio.tsx` | ✅ Complete |
| **§5.13** | Target Mode Studio | `components/target-mode/TargetModeStudio.tsx` | ✅ Complete |
| **§5.14** | Hybrid Mode Studio | `components/hybrid-mode/HybridModeStudio.tsx` | ✅ Complete |
| **§5.15** | Reliability Dashboard | `components/reliability/ReliabilityDashboard.tsx` | ✅ Complete |
| **§5.16** | Calibration Lab | `app/dashboard/calibration/page.tsx` | ✅ Complete |
| **§5.17** | 2D Replay | `components/replay/ReplayPlayer.tsx` | ✅ Complete |
| **§5.18** | Runs & Jobs | `app/dashboard/runs/page.tsx` | ✅ Complete |
| **§5.19** | Exports | `components/exports/ExportsPage.tsx` | ✅ Complete |
| **§5.20** | Admin & Settings | `app/dashboard/admin/page.tsx` | ✅ Complete |

---

## 3. LLM Integration Coverage

| LLM Purpose | Spec Reference | Current Implementation | Status | Notes |
|-------------|----------------|----------------------|--------|-------|
| **Event Compiler - Intent** | §11 Phase 4 | `event_compiler.py` → `openrouter.py` | 🟡 Partial | Direct call, no router |
| **Event Compiler - Decompose** | §11 Phase 4 | `event_compiler.py` → `openrouter.py` | 🟡 Partial | Direct call, no router |
| **Event Compiler - Variable Map** | §11 Phase 4 | `event_compiler.py` → `openrouter.py` | 🟡 Partial | Direct call, no router |
| **Scenario Generation** | §11 Phase 4 | `event_compiler.py` → `openrouter.py` | 🟡 Partial | Direct call, no router |
| **Explanation Generator** | §11 Phase 4 | `event_compiler.py` → `openrouter.py` | 🟡 Partial | Direct call, no router |
| **Persona Enrichment** | §6.2 | `persona_expansion.py` → `openrouter.py` | 🟡 Partial | Direct call, no router |
| **AI Research** | Deep Search | `ai_research.py` → `openrouter.py` | 🟡 Partial | Direct call, no router |
| **Admin LLM Controls** | Task Requirement | ❌ Missing | ❌ Missing | **No admin model selection** |
| **Usage Tracking** | Task Requirement | ❌ Missing | ❌ Missing | **No per-tenant cost tracking** |
| **LLM Cache/Replay** | Task Requirement | ❌ Missing | ❌ Missing | **No deterministic cache** |

### Current LLM Architecture

```
Current (Dispersed):
┌─────────────────┐     ┌─────────────────┐
│ event_compiler  │────▶│ openrouter.py   │────▶ OpenRouter API
├─────────────────┤     └─────────────────┘
│ persona_expand  │────▶│ openrouter.py   │────▶ OpenRouter API
├─────────────────┤     └─────────────────┘
│ ai_research     │────▶│ openrouter.py   │────▶ OpenRouter API
├─────────────────┤     └─────────────────┘
│ focus_group     │────▶│ openrouter.py   │────▶ OpenRouter API
└─────────────────┘     └─────────────────┘

Required (Centralized):
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ event_compiler  │────▶│                 │     │ Admin Profile   │
├─────────────────┤     │   LLMRouter     │◀────┤ Selection       │
│ persona_expand  │────▶│   (Gateway)     │     │ Per-Feature     │
├─────────────────┤     │                 │     │ Per-Tenant      │
│ ai_research     │────▶│ • Profile load  │     └─────────────────┘
├─────────────────┤     │ • Policy check  │
│ focus_group     │────▶│ • Call + log    │────▶ OpenRouter API
└─────────────────┘     │ • Cost track    │
                        │ • Cache check   │
                        └─────────────────┘
                                │
                        ┌───────▼───────┐
                        │   LLMCall     │
                        │   Database    │
                        │ (Audit Trail) │
                        └───────────────┘
```

---

## 4. Critical Issues Summary

### P0 - Production Blockers

| Issue | Location | Impact | Spec Reference |
|-------|----------|--------|----------------|
| **13 models missing tenant_id** | `apps/api/app/models/` | Cross-tenant data leakage | §8.1 |
| **17 endpoint files without require_tenant** | `apps/api/app/api/v1/endpoints/` | Authorization bypass | §8.1 |
| **JWT tenant_id optional** | `apps/api/app/middleware/tenant.py` | Silent auth failures | §8.1 |
| **API key validation stub** | `apps/api/app/core/security.py` | Returns None | §8.4 |
| **No audit log endpoints** | Missing | Non-compliance risk | §8.5 |
| **No centralized LLM router** | Missing | No admin control, no cost tracking | Task requirement |

### Models Missing tenant_id

1. User
2. Project (legacy)
3. Scenario
4. SimulationRun
5. Persona
6. PersonaTemplate
7. PersonaRecord
8. Product
9. FocusGroup
10. DataSource
11. Prediction
12. Organization
13. Marketplace items

### Endpoints Missing require_tenant

1. `projects.py` (7 endpoints)
2. `personas.py` (8 endpoints)
3. `users.py` (3 endpoints)
4. `ask.py` (all endpoints)
5. `ai_generation.py` (all endpoints)
6. `data_sources.py` (all endpoints)
7. `focus_groups.py` (all endpoints)
8. `marketplace.py` (all endpoints)
9. `organizations.py` (all endpoints)
10. `predictions.py` (all endpoints)
11. `privacy.py` (all endpoints)
12. `products.py` (all endpoints)
13. `scenarios.py` (all endpoints)
14. `simulations.py` (all endpoints)
15. `replay.py` (all endpoints)
16. `validation.py` (all endpoints)
17. `world.py` (all endpoints)

---

## Coverage Statistics

| Category | Total Items | Complete | Partial | Missing/Risky |
|----------|-------------|----------|---------|---------------|
| **project.md Principles (P1-P6)** | 6 | 5 | 1 | 0 |
| **Data Contracts (§6)** | 8 | 6 | 0 | 2 |
| **Reliability (§7)** | 2 | 2 | 0 | 0 |
| **Security (§8)** | 5 | 2 | 2 | 1 |
| **Performance (§9)** | 3 | 3 | 0 | 0 |
| **Testing (§10)** | 3 | 2 | 1 | 0 |
| **Phase Plan (§11)** | 9 | 8 | 0 | 1 |
| **UX Principles (G1-G7)** | 7 | 6 | 1 | 0 |
| **Page Specs (§5.1-5.20)** | 20 | 20 | 0 | 0 |
| **LLM Integration** | 10 | 0 | 7 | 3 |
| **TOTAL** | 73 | 54 (74%) | 12 (16%) | 7 (10%) |

---

## Next Steps (Prioritized)

1. **P0 - Create LLMRouter centralized gateway** (Part 2)
2. **P0 - Add tenant_id to 13 models + migration** (P9-001a)
3. **P0 - Add require_tenant to 17 endpoint files** (P9-001b)
4. **P0 - Make JWT tenant_id REQUIRED** (P9-001c)
5. **P0 - Implement API key validation** (P9-001d)
6. **P0 - Create audit log query endpoints** (P9-001e)

---

**End of SPEC_COVERAGE.md**

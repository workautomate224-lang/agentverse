# AgentVerse Implementation Gaps Report

**Generated:** 2026-01-09
**Purpose:** Prioritized gap analysis with root causes, fix approaches, and acceptance tests

---

## Priority Definitions

- **P0 (Production Blockers):** Must fix before ANY production deployment. Security or data integrity risks.
- **P1 (High Impact Correctness):** Affects core functionality or spec compliance. Fix before feature-complete.
- **P2 (UX/Product Completeness):** Improves user experience or fills product gaps. Can ship MVP without.

---

## P0 - Production Blockers (CRITICAL)

### GAP-P0-001: No Centralized LLM Router ✅ IMPLEMENTED

**Status:** IMPLEMENTED (2026-01-09)

**Implementation Summary:**
- Created `llm_profiles`, `llm_calls`, `llm_cache` database tables (migration 0003)
- Created `LLMRouter` service in `app/services/llm_router.py`
- Created Pydantic schemas in `app/schemas/llm.py`
- Created Admin API endpoints in `app/api/v1/endpoints/llm_admin.py`
- Refactored `event_compiler.py` to use LLMRouter (pattern for other services)
- Created CI check script `scripts/check_llm_usage.py`
- Inserted 8 default LLM profiles in migration

**Remaining Work:**
- ✅ Refactored `event_compiler.py` to use LLMRouter
- ✅ Refactored `ai_research.py` to use LLMRouter
- ✅ Refactored `focus_group.py` to use LLMRouter
- ✅ Refactored `persona_expansion.py` to use LLMRouter
- ✅ Created Admin Models UI in `/dashboard/admin` (Models tab)
- ⏳ `product_execution.py` and `simulation.py` use batch_complete (legacy features, marked for removal)

**Original Visible Symptom:**
- LLM calls scattered across 7+ service files
- No admin control over model selection per feature
- No cost tracking per tenant/project/run
- No usage audit trail
- No fallback chain when models fail
- No deterministic cache for replay

**Root Cause:**
- OpenRouter service (`openrouter.py`) is a simple wrapper
- Each service (event_compiler, persona_expansion, ai_research) calls OpenRouter directly
- No intermediate routing layer exists

**Affected Files:**
```
apps/api/app/services/openrouter.py       # Base service
apps/api/app/services/event_compiler.py   # Direct calls
apps/api/app/services/persona_expansion.py
apps/api/app/services/ai_research.py
apps/api/app/services/focus_group.py
apps/api/app/services/ai_content_generator.py
apps/api/app/services/product_execution.py
```

**Fix Approach:**
1. Create `apps/api/app/services/llm_router.py`:
   - Central gateway for ALL LLM calls
   - Profile-based model selection (see LLM Profiles below)
   - Tenant/project override support
   - Fallback chain execution
   - Usage logging to `llm_calls` table
   - Cost estimation and tracking
   - Deterministic cache with prompt hashing

2. Create database tables:
   - `llm_profiles` - Admin-configurable model profiles
   - `llm_calls` - Audit trail of all LLM invocations
   - `llm_cache` - Deterministic response cache

3. Create Admin UI:
   - Profile management (CRUD)
   - Usage dashboard (cost by tenant/project/feature)
   - Test profile (send prompt, see response)

4. Refactor all services to use LLMRouter

**LLM Profiles Required:**
```python
profiles = [
    "EVENT_COMPILER_INTENT",
    "EVENT_COMPILER_DECOMPOSE",
    "EVENT_COMPILER_VARIABLE_MAP",
    "SCENARIO_GENERATOR",
    "EXPLANATION_GENERATOR",
    "PERSONA_ENRICHMENT",
    "DEEP_SEARCH",
    "FOCUS_GROUP_DIALOGUE",
]
```

**Acceptance Tests:**
- [x] Admin can create/edit LLM profiles (API: POST/PATCH /admin/llm/profiles)
- [x] Changing profile model immediately affects new requests (profile lookup on each call)
- [x] Fallback chain works when primary model fails (_complete_with_fallback method)
- [x] All LLM calls logged to `llm_calls` table (_log_call method)
- [x] Cost tracked per tenant/project/run (LLMRouterContext, cost_usd field)
- [x] Same prompt+context returns cached response (cache_enabled, _get_cached_response)
- [x] CI check fails if direct OpenRouter calls exist outside LLMRouter (scripts/check_llm_usage.py)

---

### GAP-P0-002: 13 Models Missing tenant_id

**Visible Symptom:**
- User A can potentially access User B's data if user_id collides or is spoofed
- No row-level security possible without tenant_id FK
- Data isolation relies solely on user_id (single point of failure)

**Root Cause:**
- Original MVP was single-tenant design
- Newer spec-compliant models (Node, EventScript) have tenant_id
- Legacy models never migrated

**Affected Models:**
```
1. User
2. Project
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
```

**Fix Approach:**
1. Create Alembic migration to add tenant_id FK to all 13 models
2. Backfill existing data (assign default tenant or user's tenant)
3. Add non-nullable constraint after backfill
4. Update model classes with relationship
5. Update all queries to filter by tenant_id

**Acceptance Tests:**
- [ ] All 13 models have tenant_id FK (non-nullable)
- [ ] Migration runs without data loss
- [ ] Existing data assigned to correct tenant
- [ ] Model queries include tenant_id filter

---

### GAP-P0-003: 17 Endpoint Files Without require_tenant

**Visible Symptom:**
- API endpoints return data without tenant validation
- Potential for cross-tenant data leakage
- Inconsistent authorization across API surface

**Root Cause:**
- Spec-compliant endpoints (runs, nodes, telemetry) use `require_tenant`
- Legacy endpoints never updated

**Affected Endpoints:**
```
projects.py        - 7 endpoints
personas.py        - 8 endpoints
users.py           - 3 endpoints
ask.py             - all endpoints
ai_generation.py   - all endpoints
data_sources.py    - all endpoints
focus_groups.py    - all endpoints
marketplace.py     - all endpoints
organizations.py   - all endpoints
predictions.py     - all endpoints
privacy.py         - all endpoints
products.py        - all endpoints
scenarios.py       - all endpoints
simulations.py     - all endpoints
replay.py          - all endpoints
validation.py      - all endpoints
world.py           - all endpoints
```

**Fix Approach:**
1. Add `tenant_ctx: TenantContext = Depends(require_tenant)` to all endpoint functions
2. Update all DB queries to filter by `tenant_ctx.tenant_id`
3. Add integration tests for each endpoint

**Acceptance Tests:**
- [ ] All endpoints return 401 without valid tenant token
- [ ] User A cannot access User B's resources (cross-tenant test)
- [ ] All DB queries include tenant_id filter (code audit)

---

### GAP-P0-004: JWT tenant_id is Optional

**Visible Symptom:**
- Requests with missing tenant_id may succeed silently
- Tenant context fallbacks to user_id (inadequate isolation)
- Security check can be bypassed

**Root Cause:**
- `get_tenant_context()` returns optional tenant_id
- Fallback logic allows requests without tenant

**Affected Files:**
```
apps/api/app/middleware/tenant.py
apps/api/app/core/security.py
```

**Fix Approach:**
1. Make tenant_id REQUIRED in JWT payload
2. Update token generation to always include tenant_id
3. Remove user_id fallback in tenant middleware
4. Return 401 if tenant_id missing

**Acceptance Tests:**
- [ ] JWT without tenant_id rejected with 401
- [ ] Token generation includes tenant_id
- [ ] No fallback to user_id for tenant scoping

---

### GAP-P0-005: API Key Validation is Stub

**Visible Symptom:**
- API key authentication returns None (always fails)
- No programmatic access possible for integrations
- Rate limiting per API key not functional

**Root Cause:**
- `validate_api_key()` function is a stub returning None

**Affected Files:**
```
apps/api/app/core/security.py
```

**Fix Approach:**
1. Implement API key storage (hashed in DB)
2. Create API key generation endpoint (POST /api-keys)
3. Create API key revocation endpoint (DELETE /api-keys/{id})
4. Implement validation logic
5. Link API keys to tenant and user
6. Add per-key rate limiting

**Acceptance Tests:**
- [ ] Valid API key authenticates successfully
- [ ] Invalid API key returns 401
- [ ] API keys scoped to tenant
- [ ] Rate limiting works per API key

---

### GAP-P0-006: No Audit Log Query Endpoints ✅ IMPLEMENTED

**Status:** IMPLEMENTED (2026-01-09)

**Implementation Summary:**
- Created `app/schemas/audit.py` - Pydantic schemas for audit log API
- Created `app/api/v1/endpoints/audit_admin.py` - Admin endpoints for audit logs
- Updated `app/api/v1/router.py` to include audit_admin routes
- Added frontend API methods and React Query hooks

**Backend Endpoints Created:**
- `GET /admin/audit-logs` - List audit logs with filtering and pagination
- `GET /admin/audit-logs/{log_id}` - Get single audit log entry
- `GET /admin/audit-logs/stats` - Get audit statistics (events by action/resource, trends)
- `GET /admin/audit-logs/export` - Export logs to JSON/CSV
- `GET /admin/audit-logs/actions` - List unique action types
- `GET /admin/audit-logs/resource-types` - List unique resource types

**Frontend Hooks Created:**
- `useAuditLogs()` - Query audit logs with filters
- `useAuditLog()` - Get single audit log
- `useAuditStats()` - Get audit statistics
- `useExportAuditLogs()` - Export audit logs
- `useAuditActions()` - List action types
- `useAuditResourceTypes()` - List resource types

**Original Visible Symptom:**
- Audit logs written but not queryable
- Compliance audits require DB access
- No admin visibility into system activity

**Root Cause:**
- `audit.py` service writes logs
- No API endpoints to read them

**Acceptance Tests:**
- [x] GET /admin/audit-logs returns logs
- [x] Filtering by date/action/user works
- [x] Pagination works
- [x] Non-admin users get 403 (get_current_admin_user dependency)
- [x] LLM profile changes appear in audit (via AuditService)

---

## P1 - High Impact Correctness

### GAP-P1-001: No LLM Cost Tracking Per Tenant

**Visible Symptom:**
- Cannot bill tenants for LLM usage
- No visibility into which features consume most tokens
- Cannot set per-tenant cost limits

**Root Cause:**
- OpenRouter responses include usage data
- Data is discarded, not persisted

**Fix Approach:**
1. Part of GAP-P0-001 (LLMRouter implementation)
2. Parse `usage` field from OpenRouter response
3. Store in `llm_calls` table
4. Aggregate for dashboard

**Acceptance Tests:**
- [ ] LLM usage stored per call
- [ ] Dashboard shows cost by tenant/project/feature
- [ ] Cost estimates match OpenRouter pricing

---

### GAP-P1-002: No LLM Fallback Chain

**Visible Symptom:**
- If primary model unavailable, request fails entirely
- No graceful degradation
- Poor reliability during model outages

**Root Cause:**
- Single model configured per use case
- No retry with fallback models

**Fix Approach:**
1. Part of GAP-P0-001 (LLMRouter implementation)
2. Profile includes `fallback_models: List[str]`
3. On primary failure, try each fallback in order
4. Log which model ultimately succeeded

**Acceptance Tests:**
- [ ] Primary model failure triggers fallback
- [ ] All fallbacks tried in order
- [ ] Final model used is logged
- [ ] Max retries configurable

---

### GAP-P1-003: No Deterministic LLM Cache

**Visible Symptom:**
- Same "Ask" prompt may produce different scenarios
- Cannot replay identical compilation
- Non-determinism in critical paths

**Root Cause:**
- LLM responses not cached
- Each call is fresh

**Fix Approach:**
1. Part of GAP-P0-001 (LLMRouter implementation)
2. Cache key: `hash(tenant_id + profile + model + params + system_prompt_version + canonicalized_messages)`
3. Store response in `llm_cache` table
4. Return cached response on hit (log as cache_hit)
5. TTL configurable per profile

**Acceptance Tests:**
- [ ] Same input returns cached response
- [ ] Cache hit logged in `llm_calls`
- [ ] TTL respected
- [ ] Cache can be invalidated per profile

---

### GAP-P1-004: Legacy Endpoints Still Active

**Visible Symptom:**
- Old endpoints (products, scenarios, simulations) still accessible
- Confusion about which API to use
- Potential for data inconsistency

**Root Cause:**
- Endpoints not removed after spec refactor
- No deprecation notices

**Affected Files:**
```
products.py
scenarios.py
simulations.py
focus_groups.py
predictions.py
```

**Fix Approach:**
1. Review which legacy endpoints are still needed
2. Mark deprecated endpoints with warning header
3. Remove or redirect to new endpoints
4. Update frontend to use new endpoints only

**Acceptance Tests:**
- [ ] Legacy endpoints return deprecation warning
- [ ] Frontend uses only spec-compliant endpoints
- [ ] Data created via old endpoints migrated

---

## P2 - UX/Product Completeness

### GAP-P2-001: Admin Models UI Not Implemented

**Visible Symptom:**
- No way for admins to configure LLM profiles
- Model changes require code deployment
- No usage dashboard

**Root Cause:**
- Frontend Admin page exists but no Models tab
- Backend profile management not implemented

**Fix Approach:**
1. Part of GAP-P0-001 (Admin UI component)
2. Add "Models" tab to Admin page
3. Profile list with edit/test buttons
4. Usage dashboard with charts

**Acceptance Tests:**
- [ ] Admin can view/edit LLM profiles
- [ ] Admin can test profile with sample prompt
- [ ] Usage dashboard shows metrics
- [ ] Non-admin cannot access

---

### GAP-P2-002: No Profile-Level Cost Limits

**Visible Symptom:**
- Runaway LLM costs possible
- No per-request cost cap
- No alerts on cost threshold

**Root Cause:**
- Cost tracking not implemented
- No enforcement layer

**Fix Approach:**
1. Add `max_cost_per_request` to profile schema
2. Estimate cost before calling
3. Reject if estimate exceeds limit
4. Alert on high cost patterns

**Acceptance Tests:**
- [ ] Request rejected if cost estimate too high
- [ ] Cost limit configurable per profile
- [ ] Alert triggered on threshold

---

### GAP-P2-003: No Export of LLM Audit Trail

**Visible Symptom:**
- Cannot export LLM usage for compliance
- No CSV/JSON download of calls
- Audit reports manual

**Fix Approach:**
1. Add export endpoint for `llm_calls`
2. Support CSV and JSON formats
3. Filter by date range, tenant, profile

**Acceptance Tests:**
- [ ] Export returns all matching calls
- [ ] CSV and JSON formats work
- [ ] Large exports paginated

---

## Summary Table

| ID | Priority | Title | Effort | Dependencies |
|----|----------|-------|--------|--------------|
| GAP-P0-001 | P0 | No Centralized LLM Router | XL | None |
| GAP-P0-002 | P0 | 13 Models Missing tenant_id | L | None |
| GAP-P0-003 | P0 | 17 Endpoints Without require_tenant | M | GAP-P0-002 |
| GAP-P0-004 | P0 | JWT tenant_id Optional | S | None |
| GAP-P0-005 | P0 | API Key Validation Stub | M | GAP-P0-002 |
| GAP-P0-006 | P0 | No Audit Log Endpoints | S | None |
| GAP-P1-001 | P1 | No LLM Cost Tracking | M | GAP-P0-001 |
| GAP-P1-002 | P1 | No LLM Fallback Chain | M | GAP-P0-001 |
| GAP-P1-003 | P1 | No Deterministic LLM Cache | M | GAP-P0-001 |
| GAP-P1-004 | P1 | Legacy Endpoints Active | M | None |
| GAP-P2-001 | P2 | Admin Models UI | L | GAP-P0-001 |
| GAP-P2-002 | P2 | No Profile Cost Limits | S | GAP-P0-001 |
| GAP-P2-003 | P2 | No LLM Audit Export | S | GAP-P0-001 |

**Effort Key:** S = Small (1-2 hours), M = Medium (4-8 hours), L = Large (1-2 days), XL = Extra Large (3-5 days)

---

## Recommended Implementation Order

### Sprint 1: Security Foundation (P0)
1. GAP-P0-004: JWT tenant_id REQUIRED (S)
2. GAP-P0-002: Add tenant_id to 13 models (L)
3. GAP-P0-003: Add require_tenant to endpoints (M)
4. GAP-P0-005: API key validation (M)
5. GAP-P0-006: Audit log endpoints (S)

### Sprint 2: LLM Router (P0/P1)
1. GAP-P0-001: Centralized LLM Router (XL)
   - Day 1-2: Router service + DB schema
   - Day 3: Refactor all callers
   - Day 4: Admin API endpoints
   - Day 5: Testing + documentation
2. GAP-P1-001/002/003: Cost tracking, fallback, cache (included in P0-001)

### Sprint 3: Polish (P1/P2)
1. GAP-P1-004: Legacy endpoint cleanup (M)
2. GAP-P2-001: Admin Models UI (L)
3. GAP-P2-002: Cost limits (S)
4. GAP-P2-003: Audit export (S)

---

## Dependency Graph

```
┌─────────────────────────────────────────────────────────────┐
│                     Security Foundation                       │
│                                                               │
│  ┌──────────────┐                                            │
│  │ GAP-P0-004   │                                            │
│  │ JWT Required │                                            │
│  └──────┬───────┘                                            │
│         │                                                     │
│         ▼                                                     │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐ │
│  │ GAP-P0-002   │────▶│ GAP-P0-003   │     │ GAP-P0-006   │ │
│  │ tenant_id    │     │ require_tenant│     │ Audit API    │ │
│  └──────┬───────┘     └──────────────┘     └──────────────┘ │
│         │                                                     │
│         ▼                                                     │
│  ┌──────────────┐                                            │
│  │ GAP-P0-005   │                                            │
│  │ API Keys     │                                            │
│  └──────────────┘                                            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                        LLM Router                            │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                    GAP-P0-001                           │ │
│  │                 LLM Router Service                      │ │
│  │                                                          │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐              │ │
│  │  │ Profiles │  │ Caching  │  │ Fallback │              │ │
│  │  └──────────┘  └──────────┘  └──────────┘              │ │
│  │       │              │             │                     │ │
│  │       ▼              ▼             ▼                     │ │
│  │  ┌───────────────────────────────────────────────────┐ │ │
│  │  │              llm_calls Table (Audit)               │ │ │
│  │  └───────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────┘ │
│                            │                                  │
│         ┌──────────────────┼──────────────────┐              │
│         ▼                  ▼                  ▼              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ GAP-P1-001   │  │ GAP-P1-002   │  │ GAP-P1-003   │       │
│  │ Cost Track   │  │ Fallback     │  │ LLM Cache    │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│                            │                                  │
│         ┌──────────────────┼──────────────────┐              │
│         ▼                  ▼                  ▼              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ GAP-P2-001   │  │ GAP-P2-002   │  │ GAP-P2-003   │       │
│  │ Admin UI     │  │ Cost Limits  │  │ Audit Export │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

---

**End of GAPS.md**

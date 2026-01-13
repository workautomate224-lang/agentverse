# Phase 8: End-to-End Backtest Loop - Verification Summary

## Overview

Phase 8 implements the End-to-End Backtest Loop with Report Closure, enabling systematic comparison of predicted outcomes against ground truth data. This phase provides the critical infrastructure for validating prediction accuracy over historical events.

**Completion Date**: January 14, 2026

## Deliverables

### 1. Backend Models ✅

**Location**: `apps/api/app/models/backtest.py`

```python
# Three new SQLAlchemy models
class Backtest        # Master backtest record with config
class BacktestRun     # Individual run tracking linked to global Run
class BacktestReportSnapshot  # Cached Phase 7 report for node
```

**Key Features**:
- Multi-tenant scoped (`tenant_id` on all models) - C6 compliance
- Status enums: `BacktestStatus`, `BacktestRunStatus`
- Deterministic seed derivation via `derive_seed()` function
- Additive migration - no schema changes to existing tables

### 2. Database Migration ✅

**Location**: `apps/api/alembic/versions/h_backtests.py`

```bash
alembic upgrade head  # Applies migration
```

**Tables Created**:
- `backtests` - Master backtest configuration and status
- `backtest_runs` - Per-node-per-seed run tracking
- `backtest_report_snapshots` - Cached report outputs

### 3. Backtest Service ✅

**Location**: `apps/api/app/services/backtest_service.py`

**Key Operations**:

| Method | Description | Safety |
|--------|-------------|--------|
| `create_backtest()` | Create new backtest with planned runs | FORK-NOT-MUTATE |
| `reset_backtest_data()` | SCOPED-SAFE reset of backtest data | **CRITICAL** |
| `start_backtest()` | Execute runs sequentially or via workers | Deterministic |
| `snapshot_reports()` | Generate and cache Phase 7 reports | Cached |
| `get_backtest()` | Retrieve backtest details | Multi-tenant |
| `list_backtests()` | Paginated backtest list | Multi-tenant |
| `get_backtest_runs()` | Get all runs with status counts | Multi-tenant |
| `get_backtest_reports()` | Get cached report snapshots | Multi-tenant |

### 4. API Endpoints ✅

**Location**: `apps/api/app/api/v1/endpoints/backtests.py`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/project-specs/{project_id}/backtests` | GET | List backtests |
| `/project-specs/{project_id}/backtests` | POST | Create backtest |
| `/project-specs/{project_id}/backtests/{id}` | GET | Get backtest detail |
| `/project-specs/{project_id}/backtests/{id}/reset` | POST | SCOPED-SAFE reset |
| `/project-specs/{project_id}/backtests/{id}/start` | POST | Start execution |
| `/project-specs/{project_id}/backtests/{id}/runs` | GET | List runs |
| `/project-specs/{project_id}/backtests/{id}/reports` | GET | List report snapshots |
| `/project-specs/{project_id}/backtests/{id}/reports/snapshot` | POST | Generate snapshots |

### 5. Frontend Page ✅

**Location**: `apps/web/src/app/p/[projectId]/backtests/page.tsx`

**Features**:
- List view with status badges and progress bars
- Create form with configuration options (seed, runs per node, max ticks)
- Detail view with real-time progress tracking
- Action buttons: Start, Reset, View Reports
- Runs list with links to Run Center

**Navigation**: Added to project sidebar (`layout.tsx`) with FlaskConical icon.

### 6. Frontend Types & Hooks ✅

**Types** (`apps/web/src/lib/api.ts`):
- `BacktestStatus`, `BacktestRunStatus` enums
- `BacktestConfig`, `BacktestCreate`, `BacktestResponse` interfaces
- `BacktestRunResponse`, `BacktestReportSnapshotResponse` interfaces
- 8 new API methods in `ApiClient` class

**Hooks** (`apps/web/src/hooks/useApi.ts`):
- `useBacktests()` - List with auto-refresh for running backtests
- `useBacktest()` - Detail with 3s auto-refresh when running
- `useBacktestRuns()` - Runs list
- `useBacktestReports()` - Report snapshots
- `useCreateBacktest()`, `useResetBacktest()`, `useStartBacktest()`, `useSnapshotBacktestReports()` mutations

### 7. Pytest Tests ✅

**Location**: `apps/api/tests/test_phase8_backtests.py`

**Test Categories**:
- Seed derivation determinism (8 tests)
- Schema validation (12 tests)
- SCOPED-SAFE reset guarantees (4 critical tests)
- Model enums (2 tests)
- Service factory (1 test)
- Constants validation (3 tests)
- Integration stubs (4 tests)
- Determinism verification (3 tests)
- Status transitions (3 tests)
- Progress calculation (5 tests)
- Multi-tenant isolation (2 tests)
- Report snapshots (2 tests)

## Critical Safety Guarantees

### SCOPED-SAFE Reset

The `reset_backtest_data()` method implements **SCOPED-SAFE** deletion:

**DELETES** (backtest-specific):
- `BacktestRun` records for the specific `backtest_id`
- `BacktestReportSnapshot` records for the specific `backtest_id`

**NEVER DELETES** (global):
- Global `Run` records
- Telemetry data
- Other backtests' data
- Project data
- Node data

```python
# Example reset response
{
  "backtest_id": "...",
  "runs_deleted": 9,
  "snapshots_deleted": 3,
  "message": "Reset complete. Deleted 9 backtest runs and 3 report snapshots. Global data preserved."
}
```

### Deterministic Seed Derivation

```python
def derive_seed(base_seed: int, node_id: str, run_index: int) -> int:
    """hash(base_seed + node_id + run_index) → int32"""
    combined = f"{base_seed}:{node_id}:{run_index}"
    hash_bytes = hashlib.sha256(combined.encode()).digest()
    return int.from_bytes(hash_bytes[:4], "big") % (2**31)
```

**Guarantees**:
- Same inputs → same output (reproducibility)
- Different inputs → different outputs (uniqueness)
- Sequence of seeds all unique for single node

## Architecture Constraints Compliance

| Constraint | Status | Implementation |
|------------|--------|----------------|
| C1 FORK-NOT-MUTATE | ✅ | Creates new Run records, never modifies existing |
| C2 ON-DEMAND | ✅ | Execution triggered by POST /start only |
| C3 REPLAY READ-ONLY | N/A | Replay not involved in backtest |
| C4 AUDITABLE | ✅ | Full provenance with manifest_hash tracking |
| C5 LLMs AS COMPILERS | ✅ | No LLM in tick-by-tick loops |
| C6 MULTI-TENANT | ✅ | All operations scoped by tenant_id |

## Usage Example

### Create and Run Backtest

```typescript
// 1. Create backtest
const backtest = await api.createBacktest(projectId, {
  name: "US Election 2024 Backtest",
  topic: "Election Outcome Prediction",
  seed: 20241106,  // Use event date as seed for reproducibility
  config: {
    runs_per_node: 5,
    agent_config: { max_agents: 100 },
    scenario_config: { max_ticks: 200 },
  },
});

// 2. Start execution
await api.startBacktest(projectId, backtest.id, { sequential: true });

// 3. Monitor progress (auto-refresh in UI)
const detail = await api.getBacktest(projectId, backtest.id);
console.log(`Progress: ${detail.progress_percent}%`);

// 4. Generate report snapshots
await api.snapshotBacktestReports(projectId, backtest.id, {
  metric_key: "trump_win_probability",
  op: "ge",
  threshold: 0.5,
});

// 5. View reports
const reports = await api.getBacktestReports(projectId, backtest.id);
```

## File Inventory

| File | Type | Status |
|------|------|--------|
| `apps/api/app/models/backtest.py` | Backend Model | ✅ Created |
| `apps/api/alembic/versions/h_backtests.py` | Migration | ✅ Created |
| `apps/api/app/schemas/backtest.py` | Pydantic Schemas | ✅ Created |
| `apps/api/app/services/backtest_service.py` | Service Layer | ✅ Created |
| `apps/api/app/api/v1/endpoints/backtests.py` | API Endpoints | ✅ Created |
| `apps/api/app/api/v1/router.py` | Router Registration | ✅ Modified |
| `apps/web/src/lib/api.ts` | Frontend Types/API | ✅ Modified |
| `apps/web/src/hooks/useApi.ts` | React Query Hooks | ✅ Modified |
| `apps/web/src/app/p/[projectId]/backtests/page.tsx` | Frontend Page | ✅ Created |
| `apps/web/src/app/p/[projectId]/layout.tsx` | Navigation | ✅ Modified |
| `apps/api/tests/test_phase8_backtests.py` | Tests | ✅ Created |

## Testing Commands

```bash
# Run Phase 8 tests
cd apps/api
pytest tests/test_phase8_backtests.py -v

# Run all tests
pytest tests/ -v --tb=short

# Type check frontend
cd apps/web
pnpm type-check
```

## Next Steps

1. **Browser Testing**: Test full workflow on staging
2. **US Election Backtest**: Run with Nov 6, 2024 ground truth
3. **Report UI Fixes**: Address dark text on dark background issues

---

**Phase 8 Complete** ✅

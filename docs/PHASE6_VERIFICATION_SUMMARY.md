# PHASE 6 — Reliability Integration

## Verification Summary

**Status:** ✅ COMPLETE
**Date:** 2026-01-14

---

## Overview

Phase 6 integrates Sensitivity, Stability, and Drift analysis into the Reliability module. It computes aggregate reliability metrics across multiple runs for a node, enabling statistical analysis of simulation outcomes.

---

## Deliverables Completed

### A. Backend: Reliability Endpoints ✅

**File:** `apps/api/app/api/v1/endpoints/reliability.py`

Two new Phase 6 endpoints:

#### GET /api/v1/reliability/nodes/{node_id}/reliability/summary
Returns compact reliability metrics:
- `sensitivity`: P(metric op threshold) curve
- `stability`: Bootstrap mean, std, 95% CI
- `drift`: KS statistic, PSI, drift_status
- `calibration`: Brier score, ECE from latest CalibrationJob
- `audit`: Computation metadata for reproducibility

#### GET /api/v1/reliability/nodes/{node_id}/reliability/detail
Returns extended data for custom visualization:
- All summary fields plus:
- `raw_values`: Array of raw metric values
- `percentiles`: p5, p25, p50, p75, p95, mean, std, min, max
- `bootstrap_samples`: All 200 bootstrap estimates

### B. Computation Implementations ✅

**File:** `apps/api/app/api/v1/endpoints/reliability.py`

#### Sensitivity Analysis
- Computes empirical P(metric op threshold) across auto-generated threshold grid
- Supports operators: gte, lte, gt, lt, eq
- Returns threshold_grid[] and probabilities[] arrays

#### Stability Analysis (Bootstrap)
- Uses deterministic seed: `sha256(tenant_id:node_id:metric_key:threshold:manifest_hash)`
- 200 bootstrap samples with replacement
- Returns: bootstrap_mean, bootstrap_std, ci_95_lower, ci_95_upper

#### Drift Detection
- Kolmogorov-Smirnov two-sample test
- Population Stability Index (PSI) calculation
- Status thresholds:
  - `stable`: PSI ≤ 0.10 AND KS p-value ≥ 0.05
  - `warning`: PSI > 0.10 OR KS p-value < 0.05
  - `drifting`: PSI > 0.25 OR KS p-value < 0.01

### C. TypeScript Contracts ✅

**File:** `packages/contracts/src/reliability.ts`

Added Phase 6 types (lines 362-541):
- `Phase6SensitivityResult`
- `Phase6StabilityResult`
- `Phase6DriftResult`
- `Phase6CalibrationSummary`
- `Phase6AuditMetadata`
- `Phase6ReliabilitySummaryResponse`
- `Phase6ReliabilityDetailResponse`
- `Phase6ReliabilityQueryParams`

### D. Frontend API Integration ✅

**File:** `apps/web/src/lib/api.ts`

Added Phase 6 API types and client methods:
- `Phase6SensitivityResult`
- `Phase6StabilityResult`
- `Phase6DriftResult`
- `Phase6CalibrationSummary`
- `Phase6AuditMetadata`
- `Phase6ReliabilitySummaryResponse`
- `Phase6ReliabilityDetailResponse`
- `Phase6ReliabilityQueryParams`

Client methods:
- `getPhase6ReliabilitySummary(nodeId, params)`
- `getPhase6ReliabilityDetail(nodeId, params)`

### E. React Query Hooks ✅

**File:** `apps/web/src/hooks/useApi.ts`

Added hooks:
- `usePhase6ReliabilitySummary(nodeId, params)` - Summary data fetching
- `usePhase6ReliabilityDetail(nodeId, params)` - Detail data fetching

### F. Frontend UI Components ✅

**File:** `apps/web/src/app/p/[projectId]/reliability/page.tsx`

Added Phase 6 visualization components:
- `Phase6SensitivityChart` - LineChart showing P(metric >= threshold) curve
- `Phase6DriftStatus` - Displays KS statistic, PSI, drift status badge
- `Phase6StabilityDisplay` - Shows bootstrap mean, std, 95% CI
- Metric key selector dropdown
- Insufficient data state with CTA to Run Center

---

## Constraint Compliance

### C1 — Fork-not-mutate ✅
Phase 6 endpoints are read-only. No mutations to nodes or runs.

### C2 — On-demand ✅
Reliability metrics computed only when requested via API.

### C3 — Replay read-only ✅
All computations are read-only aggregations over existing data.

### C4 — Auditable ✅
Every response includes `audit` metadata:
- `computed_at`: Timestamp
- `run_ids_used`: List of runs included
- `filters_applied`: All query parameters
- `deterministic_seed`: Hash for reproducibility

### C5 — LLMs as compilers ✅
No LLM involvement in reliability computations.

### C6 — Multi-tenant ✅
All queries scoped by `tenant_id` from TenantContext.

---

## API Response Shapes

### GET /api/v1/reliability/nodes/{node_id}/reliability/summary

**Query Parameters:**
| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| metric_key | Yes | - | Metric to analyze (e.g., "revenue") |
| op | No | "gte" | Comparison: gte, lte, gt, lt, eq |
| threshold | No | - | Specific threshold point |
| manifest_hash | No | - | Filter by manifest version |
| window_days | No | 30 | Time window (1-365) |
| min_runs | No | 30 | Minimum runs required |

**Response:**
```json
{
  "status": "ok",
  "n_runs_total": 150,
  "n_runs_used": 142,
  "sensitivity": {
    "threshold_grid": [0.0, 0.05, 0.10, ...],
    "probabilities": [1.0, 0.95, 0.87, ...],
    "op": "gte",
    "metric_key": "revenue"
  },
  "stability": {
    "bootstrap_mean": 0.423,
    "bootstrap_std": 0.028,
    "ci_95_lower": 0.372,
    "ci_95_upper": 0.481,
    "n_bootstrap": 200,
    "seed_hash": "a1b2c3d4e5f6g7h8"
  },
  "drift": {
    "ks_statistic": 0.089,
    "ks_pvalue": 0.234,
    "psi": 0.042,
    "drift_status": "stable",
    "baseline_n": 71,
    "recent_n": 71
  },
  "calibration": {
    "brier_score": 0.12,
    "ece": 0.08,
    "method": "platt_scaling",
    "calibration_job_id": "uuid"
  },
  "audit": {
    "computed_at": "2026-01-14T12:00:00Z",
    "run_ids_used": ["uuid1", "uuid2", ...],
    "filters_applied": {...},
    "deterministic_seed": "a1b2c3d4e5f6g7h8"
  }
}
```

### Insufficient Data Response

When `n_runs_used < min_runs`:
```json
{
  "status": "insufficient_data",
  "n_runs_total": 10,
  "n_runs_used": 8,
  "sensitivity": null,
  "stability": null,
  "drift": null,
  "calibration": null,
  "audit": {...}
}
```

---

## Drift Status Thresholds

| Status | PSI | KS p-value |
|--------|-----|------------|
| stable | ≤ 0.10 | ≥ 0.05 |
| warning | > 0.10 | < 0.05 |
| drifting | > 0.25 | < 0.01 |

---

## Deterministic Seed Computation

```python
seed_input = f"{tenant_id}:{node_id}:{metric_key}:{threshold}:{manifest_hash}"
seed_hash = hashlib.sha256(seed_input.encode()).hexdigest()[:16]
```

This ensures reproducible bootstrap results for the same query parameters.

---

## Files Modified/Created

| File | Status | Description |
|------|--------|-------------|
| `apps/api/app/api/v1/endpoints/reliability.py` | Created | Phase 6 endpoints |
| `apps/api/app/api/v1/router.py` | Modified | Added reliability router |
| `packages/contracts/src/reliability.ts` | Modified | Added Phase 6 types |
| `apps/web/src/lib/api.ts` | Modified | Added API types and client methods |
| `apps/web/src/hooks/useApi.ts` | Modified | Added React Query hooks |
| `apps/web/src/app/p/[projectId]/reliability/page.tsx` | Modified | Added Phase 6 UI components |
| `docs/PHASE6_VERIFICATION_SUMMARY.md` | Created | This document |

---

## Frontend Components

### Phase6SensitivityChart
- Recharts LineChart
- X-axis: Threshold values
- Y-axis: P(metric >= threshold)
- Cyan colored line with dot markers

### Phase6DriftStatus
- KS Statistic display
- PSI display
- Drift status badge (green/yellow/red)

### Phase6StabilityDisplay
- Bootstrap mean ± std
- 95% Confidence interval range
- Sample count indicator

---

## Usage

### Querying Reliability Summary
```typescript
const { data, isLoading } = usePhase6ReliabilitySummary(nodeId, {
  metric_key: 'revenue',
  op: 'gte',
  min_runs: 30,
  window_days: 30,
});
```

### Handling Insufficient Data
```tsx
if (data?.status === 'insufficient_data') {
  return <InsufficientDataCTA runCount={data.n_runs_used} minRuns={30} />;
}
```

---

## Dependencies

- **NumPy**: Array operations, bootstrap sampling
- **SciPy**: KS test (`scipy.stats.ks_2samp`)
- **Recharts**: Frontend visualization
- **React Query**: Data fetching and caching

---

## Test Coverage

Phase 6 computations can be tested via:
```bash
cd apps/api
pytest tests/test_reliability.py -v -k phase6
```

---

## Migration Notes

No database migrations required for Phase 6. All data is computed on-the-fly from existing `RunOutcome` records.

---

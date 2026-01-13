# PHASE 7: Aggregated Reports - Verification Summary

## Overview

Phase 7 implements the **Aggregated Reports** feature (Prediction + Reliability Output Page) as specified in `project.md §11`. This feature provides a single, unified report endpoint that aggregates prediction distributions, reliability metrics, calibration data, and provenance information.

## Implementation Summary

### Backend Components

| Component | Location | Description |
|-----------|----------|-------------|
| Report Schemas | `apps/api/app/schemas/report.py` | Pydantic v2 schemas for request/response |
| Report Service | `apps/api/app/services/report_service.py` | Business logic, bootstrap resampling, drift detection |
| Report Endpoint | `apps/api/app/api/v1/endpoints/reports.py` | FastAPI router at `/api/v1/reports` |
| Tests | `apps/api/tests/test_phase7_reports.py` | pytest coverage for report endpoint |

### Frontend Components

| Component | Location | Description |
|-----------|----------|-------------|
| API Types | `apps/web/src/lib/api.ts` | TypeScript types matching backend schemas |
| API Methods | `apps/web/src/lib/api.ts` | `getNodeReport()`, `exportNodeReport()` methods |
| React Query Hooks | `apps/web/src/hooks/useApi.ts` | `useNodeReport()`, `useExportNodeReport()` hooks |
| Reports Page | `apps/web/src/app/p/[projectId]/reports/page.tsx` | Prediction Report UI with charts |

## API Specification

### GET /api/v1/reports/nodes/{node_id}

Generates an aggregated report for a specific node with prediction, reliability, calibration, and provenance data.

#### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `metric_key` | string | Yes | - | Metric to analyze (e.g., "revenue", "satisfaction") |
| `op` | enum | Yes | - | Comparison operator: `ge`, `gt`, `le`, `lt`, `eq` |
| `threshold` | float | Yes | - | Target threshold value |
| `manifest_hash` | string | No | null | Filter by specific manifest hash |
| `min_runs` | int | No | 3 | Minimum runs required for analysis |
| `window_days` | int | No | 30 | Time window for run selection |
| `n_sensitivity_grid` | int | No | 10 | Number of threshold grid points |
| `n_bootstrap` | int | No | 1000 | Bootstrap samples for stability CI |
| `n_bins` | int | No | 20 | Histogram bins for distribution |
| `seed` | int | No | 42 | Random seed for reproducibility |

#### Response Schema

```json
{
  "node_id": "uuid-string",
  "metric_key": "revenue",
  "target": {
    "op": "ge",
    "threshold": 100.0
  },
  "provenance": {
    "manifest_hash": "sha256-hash-or-null",
    "filters": {
      "manifest_hash": null,
      "window_days": 30,
      "min_runs": 3
    },
    "n_runs": 15,
    "updated_at": "2026-01-14T12:00:00Z"
  },
  "prediction": {
    "distribution": {
      "bins": [80.0, 85.0, 90.0, ...],
      "counts": [2, 5, 8, ...],
      "min": 75.5,
      "max": 145.2
    },
    "target_probability": 0.72
  },
  "calibration": {
    "available": true,
    "latest_job_id": "uuid-or-null",
    "brier": 0.15,
    "ece": 0.08,
    "curve": {
      "p_pred": [0.1, 0.2, 0.3, ...],
      "p_true": [0.12, 0.18, 0.32, ...],
      "counts": [10, 15, 20, ...]
    }
  },
  "reliability": {
    "sensitivity": {
      "thresholds": [90.0, 95.0, 100.0, 105.0, 110.0],
      "probabilities": [0.85, 0.78, 0.72, 0.65, 0.58]
    },
    "stability": {
      "mean": 0.72,
      "ci_low": 0.68,
      "ci_high": 0.76,
      "bootstrap_samples": 1000
    },
    "drift": {
      "status": "stable",
      "ks": 0.05,
      "psi": 0.02
    }
  },
  "insufficient_data": false,
  "errors": []
}
```

## curl Examples

### Basic Report Request

```bash
curl -X GET "http://localhost:8000/api/v1/reports/nodes/{node_id}?metric_key=revenue&op=ge&threshold=100" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

### Report with Custom Window and Min Runs

```bash
curl -X GET "http://localhost:8000/api/v1/reports/nodes/{node_id}?metric_key=satisfaction&op=gt&threshold=0.8&window_days=60&min_runs=5" \
  -H "Authorization: Bearer $TOKEN"
```

### Report with Bootstrap Configuration

```bash
curl -X GET "http://localhost:8000/api/v1/reports/nodes/{node_id}?metric_key=revenue&op=ge&threshold=100&n_bootstrap=2000&n_bins=30&seed=123" \
  -H "Authorization: Bearer $TOKEN"
```

### Filter by Manifest Hash

```bash
curl -X GET "http://localhost:8000/api/v1/reports/nodes/{node_id}?metric_key=revenue&op=ge&threshold=100&manifest_hash=abc123" \
  -H "Authorization: Bearer $TOKEN"
```

## Verification Tests

### Run Backend Tests

```bash
cd apps/api
pytest tests/test_phase7_reports.py -v
```

### Test Cases Covered

1. **Successful report generation** - Full report with all sections
2. **Insufficient data handling** - Returns 200 with `insufficient_data: true` (never 500)
3. **Missing metric handling** - Returns report with errors list
4. **Parameter validation** - Invalid operators, thresholds
5. **Deterministic output** - Same seed produces identical results

## Key Design Decisions

### 1. Fork-Not-Mutate (C1)
Report generation is stateless and read-only. No nodes or data are modified.

### 2. Deterministic Bootstrap (C4/C5)
All bootstrap resampling uses seeded numpy RNG for reproducibility:
```python
rng = np.random.default_rng(seed)
samples = rng.choice(values, size=(n_bootstrap, len(values)), replace=True)
```

### 3. Insufficient Data Returns 200 (Never 500)
When `n_runs < min_runs`, the endpoint returns HTTP 200 with:
```json
{
  "insufficient_data": true,
  "errors": ["Insufficient runs: 2 < 3 required"]
}
```

### 4. Deep-Linking Support
Report URLs are fully shareable with all parameters in query string:
```
/p/{projectId}/reports?type=prediction&node={nodeId}&metric=revenue&op=ge&threshold=100
```

## Drift Detection

The report service computes two drift metrics:

1. **KS Statistic** - Kolmogorov-Smirnov test comparing recent vs. older runs
2. **PSI (Population Stability Index)** - Measures distribution shift

Drift status thresholds:
- `stable`: KS < 0.1 and PSI < 0.1
- `warning`: KS < 0.2 or PSI < 0.2
- `drifting`: KS >= 0.2 or PSI >= 0.2

## Frontend Features

### Prediction Report Page

1. **Target Probability Hero** - Large display of P(metric op threshold)
2. **Distribution Histogram** - Interactive histogram with target highlighting
3. **Sensitivity Curve** - Shows how probability changes with threshold
4. **Stability Panel** - Bootstrap confidence interval visualization
5. **Drift Status** - Color-coded drift indicator with KS/PSI values
6. **Calibration Section** - Brier score, ECE, and calibration curve
7. **Provenance Panel** - Run count, window, manifest hash

### Deep-Link Parameters

All report state is reflected in URL:
- `type=prediction` - Report type
- `node={nodeId}` - Selected node
- `metric={metricKey}` - Metric to analyze
- `op={operator}` - Comparison operator
- `threshold={value}` - Target threshold
- `window={days}` - Time window
- `min_runs={count}` - Minimum runs

## File Manifest

```
apps/api/
├── app/
│   ├── api/v1/endpoints/reports.py    # FastAPI endpoint
│   ├── schemas/report.py              # Pydantic schemas
│   └── services/report_service.py     # Business logic
└── tests/
    └── test_phase7_reports.py         # pytest tests

apps/web/
└── src/
    ├── app/p/[projectId]/reports/page.tsx  # Enhanced with Prediction Report
    ├── hooks/useApi.ts                     # useNodeReport hook
    └── lib/api.ts                          # Report types & API methods

docs/
└── PHASE7_VERIFICATION_SUMMARY.md     # This file
```

## Compliance Checklist

- [x] **C1 Fork-Not-Mutate**: Report is read-only, no data modification
- [x] **C2 On-Demand**: Report generated only when requested
- [x] **C3 Replay Read-Only**: Report queries telemetry, never triggers simulation
- [x] **C4 Auditable**: Provenance section includes manifest hash, run counts, timestamps
- [x] **C5 LLMs as Compilers**: No LLM calls in report generation
- [x] **C6 Multi-Tenant**: All queries scoped by project/node ownership

## Next Steps

1. **Integration Testing**: Test with real simulation data
2. **Performance**: Add caching for expensive bootstrap calculations
3. **Export Formats**: Add PDF export alongside JSON
4. **Alerts**: Configure drift detection alerts

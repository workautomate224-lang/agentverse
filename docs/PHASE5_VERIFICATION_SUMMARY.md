# PHASE 5 — Telemetry Standardization + Spatial Replay Enablement

## Verification Summary

**Status:** ✅ COMPLETE
**Date:** 2026-01-13
**Constraint:** NO DATA WIPE — All migrations are additive only

---

## Overview

Phase 5 establishes Telemetry as a stable, versioned contract and enables spatial replay for runs containing position-like data. This implementation maintains full backward compatibility with existing telemetry data.

---

## Deliverables Completed

### A. Telemetry Contract ✅

**File:** `packages/contracts/src/telemetry.ts`

Added Phase 5 types and interfaces:
- `TelemetryCapabilities` - Capability flags for UI enablement
- `NormalizedPosition` - Canonical position format
- `TelemetryIndexResponse` - Index API response shape
- `TelemetrySliceResponse` - Slice API response shape
- `TelemetrySummaryResponse` - Summary API response shape
- `KeyframeResponse`, `DeltaResponse`, `EventResponseItem` - Supporting types
- Spatial field alias constants: `SPATIAL_X_ALIASES`, `SPATIAL_Y_ALIASES`, `SPATIAL_Z_ALIASES`
- Utility functions: `extractSpatialPosition()`, `extractNormalizedPositions()`

### B. Standardized Endpoints ✅

**File:** `apps/api/app/api/v1/endpoints/telemetry.py`

Updated Pydantic response schemas:
- `CapabilitiesResponse` - has_spatial, has_events, has_metrics
- `NormalizedPositionResponse` - Canonical position schema
- `TelemetryIndexResponse` - Added capabilities, telemetry_schema_version, total_agents, total_events, metric_keys
- `TelemetrySliceResponse` - Added normalized_positions, capabilities, telemetry_schema_version
- `TelemetrySummaryResponse` - Added capabilities, telemetry_schema_version

All endpoints now return the standardized response shape.

### C. Spatial Normalization ✅

**File:** `apps/api/app/services/telemetry.py`

Implemented spatial extraction supporting multiple field naming conventions:
- `x/y` (primary)
- `position_x/position_y`
- `pos_x/pos_y`
- `coord_x/coord_y`
- `loc_x/loc_y`
- `grid_cell`, `location_id` (fallbacks)

Functions added:
- `extract_spatial_value()` - Extract single coordinate from state
- `normalize_agent_position()` - Create NormalizedPosition from agent state
- `extract_normalized_positions()` - Batch extraction for all agents
- `detect_capabilities()` - Detect has_spatial, has_events, has_metrics
- `_has_spatial_fields()` - Check if state contains spatial data

### D. Storage & Metadata ✅

**File:** `apps/api/app/models/telemetry_index.py`

Created TelemetryIndex SQLAlchemy model with:
- `schema_version` - Telemetry schema version (default "v1")
- `capabilities` - JSONB field for capability flags
- `total_ticks` - Total tick count
- `keyframe_ticks` - Array of keyframe tick numbers
- `agent_ids` - Array of agent IDs
- `total_agents` - Agent count
- `total_events` - Event count
- `metric_keys` - Available metric names
- `storage_ref` - Reference to blob storage
- `telemetry_hash` - Integrity hash

**File:** `apps/api/alembic/versions/2026_01_13_0006_phase5_telemetry_index.py`

Database migration (ADDITIVE ONLY):
- Creates `telemetry_index` table
- Adds indexes for tenant_id, run_id, and composite
- No drops, truncates, or destructive operations

### E. Producer Side ✅

**File:** `apps/api/app/services/telemetry.py`

Updated telemetry production to include:
- `TelemetryVersion` enum with `V1_0_0`, `V1_1_0`, `CURRENT`
- Capabilities detection during telemetry creation
- Spatial position extraction in slice queries
- Schema version tagging

### F. Tests + Documentation ✅

**File:** `apps/api/tests/test_phase5_telemetry_standardization.py`

Comprehensive test coverage:
- `TestSpatialFieldAliases` - Alias constant validation
- `TestExtractSpatialValue` - Coordinate extraction
- `TestNormalizeAgentPosition` - Position normalization
- `TestExtractNormalizedPositions` - Batch extraction
- `TestHasSpatialFields` - Field detection
- `TestTelemetryCapabilities` - Capability class
- `TestDetectCapabilities` - Capability detection
- `TestTelemetryIndexModel` - Database model
- `TestTelemetryVersion` - Version enum
- `TestBackwardCompatibility` - Legacy data handling
- `TestEdgeCases` - Error handling

---

## Constraint Compliance

### C1 — Fork-not-mutate ✅
TelemetryIndex records are immutable once created. New telemetry creates new records.

### C2 — On-demand ✅
Telemetry is only processed when simulation runs complete.

### C3 — Replay read-only ✅
All telemetry queries are read-only. Spatial extraction never triggers simulation.

### C4 — Auditable ✅
Schema versioning and telemetry hashing enable full audit trails.

### C5 — LLMs as compilers ✅
No LLM involvement in telemetry processing.

### C6 — Multi-tenant ✅
All TelemetryIndex records scoped by tenant_id.

---

## API Response Shapes

### GET /api/v1/telemetry/{run_id}/index

```json
{
  "run_id": "uuid",
  "total_ticks": 100,
  "keyframe_ticks": [0, 10, 20, ...],
  "event_types": ["purchase", "visit"],
  "agent_ids": ["agent_1", "agent_2"],
  "storage_ref": {},
  "capabilities": {
    "has_spatial": true,
    "has_events": true,
    "has_metrics": true
  },
  "telemetry_schema_version": "1.1.0",
  "total_agents": 50,
  "total_events": 150,
  "metric_keys": ["revenue", "visits"]
}
```

### GET /api/v1/telemetry/{run_id}/slice

```json
{
  "run_id": "uuid",
  "start_tick": 0,
  "end_tick": 10,
  "keyframes": [...],
  "deltas": [...],
  "events": [...],
  "total_events": 10,
  "normalized_positions": [
    {
      "agent_id": "agent_1",
      "x": 10.5,
      "y": 20.3,
      "z": null,
      "rotation": 45.0,
      "scale": 1.0,
      "grid_cell": "A1",
      "location_id": null
    }
  ],
  "capabilities": {
    "has_spatial": true,
    "has_events": true,
    "has_metrics": true
  },
  "telemetry_schema_version": "1.1.0"
}
```

### GET /api/v1/telemetry/{run_id}/summary

```json
{
  "run_id": "uuid",
  "total_ticks": 100,
  "total_events": 150,
  "total_agents": 50,
  "event_type_counts": {"purchase": 100, "visit": 50},
  "key_metrics": {},
  "duration_seconds": 3600,
  "capabilities": {
    "has_spatial": true,
    "has_events": true,
    "has_metrics": true
  },
  "telemetry_schema_version": "1.1.0"
}
```

---

## Spatial Field Detection

The system supports multiple field naming conventions for position data:

| Alias Type | Fields Checked |
|------------|----------------|
| X coordinate | `x`, `position_x`, `pos_x`, `coord_x`, `loc_x` |
| Y coordinate | `y`, `position_y`, `pos_y`, `coord_y`, `loc_y` |
| Z coordinate | `z`, `position_z`, `pos_z`, `coord_z`, `loc_z` |
| Fallbacks | `grid_cell`, `location_id` |

Both top-level fields and nested `variables` dict are checked.

---

## Backward Compatibility

- Existing telemetry data without schema_version defaults to "v1"
- Missing capabilities are all set to `false`
- Legacy agent state formats (flat structure) fully supported
- No existing data modified or deleted
- Migration is additive only

---

## Files Modified/Created

| File | Status | Description |
|------|--------|-------------|
| `packages/contracts/src/telemetry.ts` | Modified | Added Phase 5 types |
| `apps/api/app/services/telemetry.py` | Modified | Spatial normalization + capabilities |
| `apps/api/app/api/v1/endpoints/telemetry.py` | Modified | Updated response schemas |
| `apps/api/app/models/telemetry_index.py` | Created | TelemetryIndex model |
| `apps/api/app/models/__init__.py` | Modified | Export TelemetryIndex |
| `apps/api/alembic/versions/2026_01_13_0006_phase5_telemetry_index.py` | Created | Migration |
| `apps/api/tests/test_phase5_telemetry_standardization.py` | Created | Test suite |
| `docs/PHASE5_VERIFICATION_SUMMARY.md` | Created | This document |

---

## Running Tests

```bash
cd apps/api
pytest tests/test_phase5_telemetry_standardization.py -v
```

---

## Migration Instructions

```bash
cd apps/api
alembic upgrade head
```

The migration is safe to run on existing data — it only creates a new table and does not modify existing tables.

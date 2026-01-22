# TEG (Thought Expansion Graph) Universe Map Replacement - Implementation Report

**Implementation Date:** 2026-01-22
**Reference:** `docs/TEG_UNIVERSE_MAP_EXECUTION.md`

---

## Task Checklist

| Task | Description | Status |
|------|-------------|--------|
| Task 1 | Product gating update - enable Universe Map in MVP mode as TEG | DONE |
| Task 2 | Backend TEG data model + read endpoints | DONE |
| Task 3 | Frontend Graph/Table/RAW + Node Details | DONE |
| Task 4 | Expand feature - create draft scenarios via LLM | DONE |
| Task 5 | Run scenario - draft → verified outcome | DONE |
| Task 6 | Compare UX panel | DONE |
| Task 7 | Evidence attach (optional) | DONE |

---

## API Changes

### New Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/projects/{project_id}/teg` | Get full TEG graph for project |
| GET | `/api/v1/teg/nodes/{node_id}` | Get node details for right panel |
| POST | `/api/v1/projects/{project_id}/teg/sync` | Sync TEG from existing runs |
| POST | `/api/v1/teg/nodes/{node_id}/expand` | Generate draft scenarios via LLM |
| POST | `/api/v1/teg/nodes/{node_id}/run` | Execute draft scenario as simulation |
| POST | `/api/v1/teg/nodes/{node_id}/attach-evidence` | Attach evidence URLs with compliance check |

### Response Schemas

All schemas defined in `apps/api/app/schemas/teg.py`:

- `TEGGraphResponse` - Full graph with nodes and edges
- `TEGNodeResponse` - Single node data
- `TEGNodeDetail` - Extended node with computed fields
- `TEGEdgeResponse` - Edge relationship data
- `ExpandScenarioRequest/Response` - Scenario expansion
- `RunScenarioRequest/Response` - Scenario execution
- `AttachEvidenceRequest/Response` - Evidence attachment

---

## Database Migrations

### Migration File
`apps/api/alembic/versions/2026_01_22_0001_add_teg_tables.py`

**Revision ID:** `teg_universe_map_001`
**Revises:** `fix_run_outcomes_fk_001`

### New Tables

| Table | Description |
|-------|-------------|
| `teg_graphs` | Root container for each project's TEG |
| `teg_nodes` | Individual scenario nodes |
| `teg_edges` | Relationships between nodes |

### Enum Types

```sql
-- Node types
CREATE TYPE teg_node_type AS ENUM (
    'OUTCOME_VERIFIED',
    'SCENARIO_DRAFT',
    'EVIDENCE'
);

-- Node statuses
CREATE TYPE teg_node_status AS ENUM (
    'DRAFT',
    'QUEUED',
    'RUNNING',
    'DONE',
    'FAILED'
);

-- Edge relations
CREATE TYPE teg_edge_relation AS ENUM (
    'EXPANDS_TO',
    'RUNS_TO',
    'FORKS_FROM',
    'SUPPORTS',
    'CONFLICTS'
);
```

### Key Indexes
- `ix_teg_nodes_tenant_project` - Multi-tenant queries
- `ix_teg_nodes_type_status` - Status-based filtering
- `ix_teg_edges_graph_id` - Graph traversal

---

## Frontend Components

### New Components (`apps/web/src/components/teg/`)

| Component | Purpose |
|-----------|---------|
| `ThoughtExpansionGraph.tsx` | Main TEG container |
| `TEGCanvas.tsx` | Graph view with ReactFlow |
| `TEGTable.tsx` | Table view with sorting/filtering |
| `TEGRaw.tsx` | Raw JSON view for debugging |
| `TEGNodeDetails.tsx` | Right panel with node details + compare |
| `TEGViewToggle.tsx` | View mode selector |
| `types.ts` | TypeScript type definitions |

### API Integration (`apps/web/src/lib/api.ts`)

New methods:
- `getTEGGraph(projectId)` - Fetch full graph
- `getTEGNodeDetail(nodeId)` - Fetch node details
- `syncTEGFromRuns(projectId)` - Sync from existing runs
- `expandTEGNode(nodeId, request)` - Generate scenarios
- `runTEGScenario(nodeId, request)` - Execute scenario
- `attachTEGEvidence(nodeId, request)` - Attach evidence

### React Query Hooks (`apps/web/src/hooks/useApi.ts`)

New hooks:
- `useTEGGraph(projectId)` - Query for graph data
- `useTEGNodeDetail(nodeId)` - Query for node details
- `useSyncTEGFromRuns()` - Mutation for sync
- `useExpandTEGNode()` - Mutation for expansion
- `useRunTEGScenario()` - Mutation for running
- `useAttachTEGEvidence()` - Mutation for evidence

---

## Temporal Isolation Verification

### Where Enforced

1. **LLM Calls (Expand endpoint)**
   - Project cutoff date passed to LLM context
   - LLMRouter enforces temporal isolation via `LLMRouterContext`
   - All LLM calls logged with project_id for audit

2. **Evidence Attachment**
   - Temporal compliance check for each URL
   - Status: PASS (pre-cutoff), WARN (uncertain), FAIL (post-cutoff)
   - Compliance status displayed in UI

3. **Run Execution**
   - SimulationOrchestrator inherits project temporal context
   - Persona snapshots versioned at cutoff time

### Audit Trail Fields

Verified nodes include:
- `run_id` - Link to simulation run
- `persona_set_version` - Persona snapshot version
- `cutoff_snapshot` - Temporal cutoff reference
- `run_manifest_link` - Full manifest hash

---

## Compare UX Panel (Task 6)

### Features Implemented

The compare panel shows when selecting a verified outcome that is not the baseline:

1. **Baseline vs Branch Header**
   - Side-by-side comparison with probabilities
   - Clear delta indicator (+/-%)
   - Visual arrow showing direction

2. **Key Driver Changes**
   - Top 4 drivers with direction indicators
   - Positive/negative impact visualization
   - Trend icons (TrendingUp/TrendingDown)

3. **Persona Segment Shifts**
   - Segment names with shift percentages
   - Visual bar chart for magnitude
   - Color-coded (green positive, red negative)

4. **Impact Summary**
   - Contextual message based on delta magnitude
   - Color-coded border (green/red/neutral)
   - Scale icon for visual emphasis

### QA Result
- Selecting a verified branch clearly shows "Baseline X → Branch Y (ΔZ)" ✓
- User does not need to leave Universe Map to understand impact ✓

---

## QA Results - Acceptance Test

### Test Flow

| Step | Action | Expected | Result |
|------|--------|----------|--------|
| 1 | Create project | Project created with goal + cutoff | PASS |
| 2 | Generate personas | Personas created | PASS |
| 3 | Run baseline | Baseline run completes | PASS |
| 4 | Open Universe Map | TEG loads with baseline node | PASS |
| 5 | Click baseline → Expand | Draft scenarios generated | PASS |
| 6 | Select draft → Run | Status transitions, verified outcome appears | PASS |
| 7 | Compare baseline vs verified | Delta shown clearly | PASS |
| 8 | Attach evidence | Compliance badges displayed | PASS |

### View Toggles
- Graph view: Nodes render with proper styles ✓
- Table view: Sorting by impact/confidence works ✓
- RAW view: Full JSON payload displayed ✓

### Node Details Panel
- Draft scenarios: Show estimated delta, confidence, rationale ✓
- Verified outcomes: Show actual probability, drivers, segments ✓
- Failed nodes: Show error details with correlation ID ✓

---

## Known Issues

1. **Graph Layout Performance**
   - Large graphs (50+ nodes) may experience layout lag
   - Mitigation: ReactFlow with dagre layout is efficient but may need pagination

2. **LLM Expansion Latency**
   - Scenario generation takes 3-8 seconds depending on model
   - Mitigation: Loading spinner and toast notifications implemented

3. **Evidence Compliance Heuristics**
   - Current implementation uses URL-based heuristics
   - Future: Integrate with archive.org API for actual temporal verification

---

## Next Steps (Post-TEG)

1. **"Show more" pagination** - For scenario candidates exceeding display limit
2. **SUPPORTS/CONFLICTS edges** - Relationship edges for evidence-claim linking
3. **Stronger evidence-to-claim linking** - AI-powered evidence relevance scoring
4. **Advanced toggle for full Universe Map** - Engineering DAG view (not default)
5. **2D world viewer** - Future visualization mode

---

## Files Modified

### Backend
- `apps/api/app/models/teg.py` - SQLAlchemy models
- `apps/api/app/schemas/teg.py` - Pydantic schemas
- `apps/api/app/api/v1/endpoints/teg.py` - FastAPI endpoints
- `apps/api/alembic/versions/2026_01_22_0001_add_teg_tables.py` - Migration

### Frontend
- `apps/web/src/components/teg/*.tsx` - TEG components
- `apps/web/src/lib/api.ts` - API client methods
- `apps/web/src/hooks/useApi.ts` - React Query hooks
- `apps/web/src/app/p/[projectId]/universe-map/page.tsx` - Page component

### Configuration
- `apps/web/src/lib/config.ts` - Universe Map enabled in MVP_DEMO2

---

## Conclusion

The TEG (Thought Expansion Graph) implementation successfully replaces the old Universe Map with a more intuitive "parallel universe / probability mind-map" interface. Users can now:

1. View verified outcomes from baseline and branch runs
2. Expand outcomes into draft scenario candidates using AI
3. Execute draft scenarios with one click
4. Compare outcomes with clear delta visualization
5. Attach and track evidence with temporal compliance

All tasks from the execution plan have been completed with QA verification.

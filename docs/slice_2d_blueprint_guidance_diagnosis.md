# Slice 2D Blueprint Guidance Diagnosis

**Date:** 2026-01-18
**Status:** DIAGNOSIS COMPLETE

---

## 1. Where is the Final Blueprint Stored?

### Table/Model

**Table Name:** `blueprints` (also referenced as `blueprint_v2` in some legacy raw SQL)

**Model File:** `apps/api/app/models/blueprint.py` (lines 122-279)

### Key Fields

| Field | Type | Purpose |
|-------|------|---------|
| `id` | UUID | Primary key |
| `project_id` | UUID (FK to `project_specs.id`) | Links blueprint to project |
| `tenant_id` | UUID (FK to `tenants.id`) | Multi-tenancy |
| `version` | Integer | Increments on each blueprint change |
| `is_active` | Boolean | **Only one active per project** |
| `is_draft` | Boolean | Draft blueprints can be edited |
| `goal_text` | Text | Full user goal statement |
| `goal_summary` | String | Short summary |
| `domain_guess` | String | AI-detected domain (election, factory, etc.) |
| `recommended_core` | String | Core strategy (collective, target, hybrid) |
| `target_outputs` | JSONB | Expected simulation outputs |
| `horizon` | JSONB | Time horizon configuration |
| `scope` | JSONB | Scope constraints |
| `success_metrics` | JSONB | Success criteria |
| `clarification_answers` | JSONB | User Q&A from wizard |

### Relationship to Project

**Direct Foreign Key:** `blueprints.project_id` → `project_specs.id`

**One-to-Many:** A project can have multiple blueprint versions. Only one should have `is_active=true`.

**No Join Table:** The relationship is direct via the foreign key.

---

## 2. Does a Published Project Always Have `blueprint_version_id`?

### Current Behavior: **NO - There is NO direct reference on the project record**

The `project_specs` table does NOT have a `blueprint_id` or `blueprint_version_id` column. The relationship is **reverse**: blueprints point to projects, not the other way around.

### When Publishing a Project

**File:** `apps/api/app/api/v1/endpoints/project_specs.py` (lines 1121-1284)

The publish endpoint does the following:

1. **Updates project status** to `ACTIVE` and sets `published_at` timestamp
2. **Queries for active blueprint** using raw SQL:
   ```sql
   SELECT id, version FROM blueprint_v2
   WHERE project_id = :project_id AND is_active = true
   ORDER BY version DESC LIMIT 1
   ```
3. **If blueprint found:** Creates a `PROJECT_GENESIS` job with `blueprint_id` in params
4. **If blueprint NOT found:** Silently skips genesis (no error thrown)

### Why Blueprint Can Be Missing

1. **Wizard incomplete:** User could publish before blueprint build finishes
2. **Blueprint build failed:** The Celery job could have failed
3. **Race condition:** Publish clicked before `is_active=true` committed
4. **Legacy projects:** Old projects created before blueprint system

### Problem

The publish flow doesn't **require** a blueprint to exist. It just logs a warning and continues:
```python
except Exception as e:
    logging.getLogger(__name__).warning(f"Failed to trigger PROJECT_GENESIS on publish: {e}")
```

This means published projects can exist without any active blueprint, causing "No blueprint found" in the UI.

---

## 3. Where Does Guidance Content Come From Today?

### Summary

| Source | Status | Details |
|--------|--------|---------|
| LLM via OpenRouter | ✅ YES | Primary generation path |
| Reading Blueprint | ✅ YES | Blueprint context extracted and sent to LLM |
| Static/Hardcoded Text | ⚠️ PARTIAL | Fallback if LLM fails or guidance missing |

### LLM Generation Path

**File:** `apps/api/app/tasks/pil_tasks.py` (lines 2841-3235)

**Task:** `project_genesis_task` (Celery task)

**Flow:**
1. Fetch active blueprint for project
2. Extract blueprint context (goal_text, domain_guess, recommended_core, horizon, etc.)
3. For each of 13 sections, call LLM with section-specific prompt
4. Parse JSON response and store in `project_guidance` table

### LLM Prompt Structure (lines 3123-3177)

The prompt **DOES consume blueprint data**:

```python
return f"""You are an AI assistant helping configure a predictive simulation project.

PROJECT CONTEXT:
- Goal: {blueprint_context['goal_summary']}
- Domain: {blueprint_context['domain']}
- Core Strategy: {blueprint_context['recommended_core']}
- Is Backtest Mode: {blueprint_context['is_backtest']}
- Time Horizon: {json.dumps(blueprint_context['horizon'])}
- Scope: {json.dumps(blueprint_context['scope'])}

SECTION TO CONFIGURE: {section.value}
...
Make the guidance specific to the project goal: "{blueprint_context['goal_text'][:200]}"
"""
```

### Blueprint Context Extracted (lines 3024-3039)

```python
def _extract_blueprint_context(blueprint: Blueprint) -> Dict[str, Any]:
    return {
        "goal_text": blueprint.goal_text,
        "goal_summary": blueprint.goal_summary or blueprint.goal_text[:200],
        "domain": blueprint.domain_guess,
        "recommended_core": blueprint.recommended_core,
        "target_outputs": blueprint.target_outputs or [],
        "horizon": blueprint.horizon or {},
        "scope": blueprint.scope or {},
        "success_metrics": blueprint.success_metrics or {},
        "primary_drivers": blueprint.primary_drivers or [],
        "clarification_answers": blueprint.clarification_answers or {},
        "calibration_plan": blueprint.calibration_plan or {},
        "is_backtest": blueprint.clarification_answers.get("temporal_mode") == "backtest",
    }
```

### Static/Fallback Guidance

**File:** `apps/api/app/models/project_guidance.py` (lines 256-322)

**When Used:**
1. LLM returns unparseable JSON → falls back to `_get_default_guidance()`
2. No guidance exists for a section → frontend shows static `SECTION_CONFIG` tips
3. Guidance fetch returns 404 → frontend displays hardcoded default tips

**Static Config Example:**
```python
GUIDANCE_SECTION_CONFIG = {
    GuidanceSection.DATA: {
        "title": "Data Sources",
        "page_route": "/data",
        "default_description": "Upload or connect your data sources.",
    },
    # ... 13 sections with generic descriptions
}
```

### Fallback in Frontend

**File:** `apps/web/src/components/pil/GuidancePanel.tsx` (lines 425-466)

When `projectGuidance` is missing, the component falls back to static "QUICK TIPS":
```typescript
const STATIC_TIPS: Record<string, string[]> = {
  overview: [
    'Review your blueprint summary to ensure alignment with goals',
    'Check the alignment score for configuration quality',
    'Monitor overall project readiness via the checklist',
  ],
  // ... generic tips for each section
}
```

---

## 4. API and Query Used Per Workspace Section

### Canonical API Pattern

All sections use the **same pattern** through the `GuidancePanel` component:

| Operation | Endpoint | Purpose |
|-----------|----------|---------|
| Get Active Blueprint | `GET /api/v1/blueprints/project/{projectId}/active` | Fetch current blueprint |
| Get Section Guidance | `GET /api/v1/blueprints/projects/{projectId}/guidance/{section}` | Fetch AI guidance |
| Trigger Genesis | `POST /api/v1/blueprints/projects/{projectId}/genesis` | Start guidance generation |
| Regenerate | `POST /api/v1/blueprints/projects/{projectId}/guidance/regenerate` | Mark stale and regenerate |
| Poll Status | `GET /api/v1/blueprints/projects/{projectId}/genesis/status` | Track job progress |

### Section to GuidanceSection Mapping

**File:** `apps/web/src/components/pil/GuidancePanel.tsx` (lines 195-209)

| Workspace Page | Route | GuidanceSection |
|----------------|-------|-----------------|
| Overview | `/p/:id/overview` | `data` |
| Data & Personas | `/p/:id/data-personas` | `personas` |
| Rules & Assumptions | `/p/:id/rules` | `rules` |
| Run Center | `/p/:id/run-center` | `run` |
| Universe Map | `/p/:id/universe-map` | `universe_map` |
| Event Lab | `/p/:id/event-lab` | `event_lab` |
| Society Simulation | `/p/:id/society` | `personas` |
| Target Planner | `/p/:id/target` | `predict` |
| Reliability | `/p/:id/reliability` | `reliability` |
| Telemetry & Replay | `/p/:id/replay` | `run` |
| 2D World Viewer | `/p/:id/world-viewer` | `universe_map` |
| Reports | `/p/:id/reports` | `reports` |
| Settings | `/p/:id/settings` | `data` |

### React Hooks Used

**File:** `apps/web/src/hooks/useApi.ts`

| Hook | Line | Purpose |
|------|------|---------|
| `useActiveBlueprint()` | 3773-3782 | Fetch active blueprint |
| `useSectionGuidance()` | 4104-4125 | Fetch section guidance |
| `useProjectGuidance()` | 4086-4098 | Fetch all sections |
| `useTriggerProjectGenesis()` | 4131-4144 | Trigger genesis job |
| `useGenesisJobStatus()` | 4168-4193 | Poll every 2 seconds |

---

## Summary of Current Issues

| Issue | Description | Impact |
|-------|-------------|--------|
| **No blueprint requirement on publish** | Publish succeeds even without active blueprint | "No blueprint found" appears for published projects |
| **Guidance fallback is generic** | When guidance missing, static tips shown | Election and Factory projects look identical |
| **No `source_refs` in guidance** | LLM output doesn't reference blueprint nodes | Can't prove guidance is derived from blueprint |
| **No project fingerprint** | No visible "Derived from Blueprint" provenance | Users can't verify guidance is project-specific |
| **Inconsistent API path styles** | Uses both `/blueprints/project/` and `/blueprints/projects/` | Minor but creates confusion |

---

## Next Steps (Task 1-3)

1. **Task 1:** Require blueprint before publish; show error if missing
2. **Task 2:** Enhance LLM prompt to output `source_refs` and `project_fingerprint`
3. **Task 3:** Capture screenshots proving different guidance for election vs factory

# Slice 2C: Project Genesis - AI-Generated Project Guidance

**Status:** Complete
**Date:** 2026-01-18

## Overview

Slice 2C implements "Project Genesis" - a system for generating AI-powered, project-specific guidance during workspace initialization. This replaces static/generic guidance with customized recommendations based on each project's Blueprint v2 configuration.

## Problem Statement

Prior to Slice 2C, all workspace sections displayed the same static guidance regardless of project type or configuration. A project focused on opinion dynamics received the same tips as a supply chain simulation, leading to:
- Generic advice not applicable to the specific domain
- Missing context about what data sources are relevant
- One-size-fits-all checklists

## Solution Architecture

### Components

```
┌─────────────────────────────────────────────────────────────────┐
│                      Frontend (Next.js)                         │
├─────────────────────────────────────────────────────────────────┤
│  GuidancePanel.tsx          │ ProjectGuidancePanel.tsx          │
│  - Fetches project guidance │ - Standalone guidance display     │
│  - Falls back to static     │ - Full section control            │
│  - Shows regenerate button  │                                   │
├─────────────────────────────────────────────────────────────────┤
│  useApi.ts Hooks                                                │
│  - useSectionGuidance(projectId, section)                       │
│  - useGenesisJobStatus(projectId)                               │
│  - useRegenerateProjectGuidance()                               │
│  - useTriggerProjectGenesis(projectId)                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                          │
├─────────────────────────────────────────────────────────────────┤
│  API Endpoints (blueprints.py)                                  │
│  - GET /blueprints/projects/{id}/guidance/{section}             │
│  - POST /blueprints/projects/{id}/guidance/regenerate           │
│  - GET /blueprints/projects/{id}/genesis/status                 │
│  - POST /blueprints/projects/{id}/genesis/trigger               │
├─────────────────────────────────────────────────────────────────┤
│  Services                                                       │
│  - guidance_service.py: mark_guidance_stale, regenerate         │
│  - pil_tasks.py: project_genesis_task (Celery)                  │
├─────────────────────────────────────────────────────────────────┤
│  Models                                                         │
│  - ProjectGuidance: Stores AI-generated guidance per section    │
│  - PILJob: Tracks genesis job status                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Database (PostgreSQL)                       │
├─────────────────────────────────────────────────────────────────┤
│  project_guidance table                                         │
│  - id, tenant_id, project_id, blueprint_id                      │
│  - section, status, blueprint_version, guidance_version         │
│  - what_to_input, recommended_sources, checklist                │
│  - suggested_actions, tips, provenance (job_id, llm_call_id)    │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Project Creation/Finalization**
   - User completes Blueprint v2 configuration
   - System triggers PROJECT_GENESIS PIL job
   - Job generates guidance for all workspace sections

2. **Guidance Display**
   - Workspace section loads GuidancePanel
   - Panel fetches project-specific guidance via API
   - If available, displays AI-generated content
   - Falls back to static guidance if not available

3. **Lifecycle Management**
   - Blueprint publish marks existing guidance as STALE
   - User sees warning and "Regenerate" button
   - Regeneration triggers new PROJECT_GENESIS job
   - New guidance replaces stale version

## Database Schema

### project_guidance Table

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| tenant_id | UUID | Tenant reference |
| project_id | UUID | Project reference |
| blueprint_id | UUID | Blueprint used for generation |
| blueprint_version | INT | Version of blueprint used |
| guidance_version | INT | Guidance revision number |
| section | VARCHAR(50) | Section identifier (enum) |
| status | VARCHAR(50) | pending/generating/ready/stale/failed |
| section_title | VARCHAR(255) | Display title |
| section_description | TEXT | Description |
| what_to_input | JSONB | Required/optional inputs |
| recommended_sources | JSONB | Data source recommendations |
| checklist | JSONB | Actionable items |
| suggested_actions | JSONB | AI-assisted actions |
| tips | JSONB | Quick tips |
| job_id | UUID | PIL job reference |
| llm_call_id | VARCHAR(100) | LLM provenance |
| is_active | BOOLEAN | Active version flag |
| created_at | TIMESTAMP | Creation time |
| updated_at | TIMESTAMP | Last update time |

### GuidanceSection Enum

```python
class GuidanceSection(str, Enum):
    DATA = "data"
    PERSONAS = "personas"
    RULES = "rules"
    RUN_PARAMS = "run_params"
    EVENT_LAB = "event_lab"
    SCENARIO_LAB = "scenario_lab"
    CALIBRATE = "calibrate"
    BACKTEST = "backtest"
    RELIABILITY = "reliability"
    RUN = "run"
    PREDICT = "predict"
    UNIVERSE_MAP = "universe_map"
    REPORTS = "reports"
```

### GuidanceStatus Enum

```python
class GuidanceStatus(str, Enum):
    PENDING = "pending"        # Job queued
    GENERATING = "generating"  # Job running
    READY = "ready"           # Guidance available
    STALE = "stale"           # Blueprint changed
    FAILED = "failed"         # Generation failed
```

## API Endpoints

### Get Section Guidance

```
GET /api/v1/blueprints/projects/{project_id}/guidance/{section}
```

Response:
```json
{
  "id": "uuid",
  "project_id": "uuid",
  "blueprint_id": "uuid",
  "blueprint_version": 1,
  "guidance_version": 1,
  "section": "personas",
  "status": "ready",
  "section_title": "Consumer Personas",
  "section_description": "Define the consumer segments...",
  "what_to_input": {
    "description": "Upload demographic data...",
    "required_items": ["age distribution", "income brackets"],
    "optional_items": ["psychographic profiles"]
  },
  "recommended_sources": [
    {
      "name": "Census Bureau",
      "type": "API",
      "description": "US demographic data",
      "priority": "recommended"
    }
  ],
  "checklist": [
    {
      "id": "personas-1",
      "label": "Define 3-5 core segments",
      "required": true,
      "completed": false
    }
  ],
  "suggested_actions": [
    {
      "action_type": "generate",
      "label": "Generate segments from data",
      "endpoint": "/api/personas/generate"
    }
  ],
  "tips": ["Start with broad segments, refine later"]
}
```

### Regenerate Guidance

```
POST /api/v1/blueprints/projects/{project_id}/guidance/regenerate
```

Response:
```json
{
  "job_id": "uuid",
  "status": "pending",
  "message": "Guidance regeneration started"
}
```

### Get Genesis Status

```
GET /api/v1/blueprints/projects/{project_id}/genesis/status
```

Response:
```json
{
  "has_job": true,
  "job_id": "uuid",
  "status": "completed",
  "progress": 100,
  "sections_completed": 13,
  "sections_total": 13
}
```

## Frontend Integration

### GuidancePanel Component

The enhanced `GuidancePanel.tsx` component:

1. **Fetches project-specific guidance** using `useSectionGuidance` hook
2. **Falls back to static guidance** when project guidance unavailable
3. **Shows visual indicators**:
   - "AI" badge for project-specific guidance
   - "GENERATING" badge with spinner when job running
   - "STALE" badge when regeneration needed
4. **Displays project-specific content**:
   - What to Input (required/optional items)
   - Recommended Sources with priority badges
   - Interactive Checklist with completion state
   - Suggested Actions as buttons
5. **Regeneration UI**:
   - Warning box when guidance is stale
   - "Regenerate Guidance" button
   - Loading state during regeneration

### Section Mapping

```typescript
const SECTION_TO_GUIDANCE: Record<string, GuidanceSection> = {
  'overview': 'data',
  'data-personas': 'personas',
  'rules': 'rules',
  'run-center': 'run',
  'universe-map': 'universe_map',
  'event-lab': 'event_lab',
  // ...
};
```

## Lifecycle Rules

### Stale Detection

Guidance becomes stale when:
1. Blueprint is published (new version activated)
2. User explicitly triggers regeneration

### Regeneration Flow

```
[Blueprint Published]
        │
        ▼
[mark_guidance_stale()]
        │
        ▼
[User sees STALE badge]
        │
        ▼
[User clicks Regenerate]
        │
        ▼
[regenerateProjectGuidance API]
        │
        ▼
[PROJECT_GENESIS job queued]
        │
        ▼
[Celery worker generates guidance]
        │
        ▼
[New guidance saved with version+1]
        │
        ▼
[UI updates to show READY status]
```

### Audit Trail

All guidance includes provenance:
- `job_id`: References the PIL job that generated it
- `llm_call_id`: References the specific LLM call
- `blueprint_version`: Blueprint version used
- `guidance_version`: Guidance revision number
- `created_at`/`updated_at`: Timestamps

## Files Changed

### Backend

| File | Changes |
|------|---------|
| `app/models/project_guidance.py` | New model for storing guidance |
| `app/services/guidance_service.py` | New service for lifecycle management |
| `app/tasks/pil_tasks.py` | PROJECT_GENESIS task implementation |
| `app/api/v1/endpoints/blueprints.py` | Guidance API endpoints |
| `alembic/versions/2026_01_18_0001_add_project_guidance_table.py` | Migration |

### Frontend

| File | Changes |
|------|---------|
| `src/components/pil/GuidancePanel.tsx` | Enhanced with project guidance |
| `src/components/pil/v2/ProjectGuidancePanel.tsx` | Standalone panel |
| `src/components/pil/v2/index.ts` | Export new component |
| `src/lib/api.ts` | API client methods, types |
| `src/hooks/useApi.ts` | React Query hooks |

## Testing

### Manual Testing Checklist

- [ ] Create Project A (Opinion Dynamics type)
  - [ ] Verify genesis job triggered on finalization
  - [ ] Check guidance appears with "AI" badge
  - [ ] Verify content is specific to opinion dynamics

- [ ] Create Project B (Supply Chain type)
  - [ ] Verify different guidance generated
  - [ ] Compare recommended sources differ from Project A

- [ ] Lifecycle Testing
  - [ ] Publish new blueprint version
  - [ ] Verify guidance shows "STALE" badge
  - [ ] Click "Regenerate Guidance"
  - [ ] Verify new guidance with version+1

### Acceptance Criteria

1. **Two different projects with different Blueprint configurations must show meaningfully different guidance**
2. Guidance must include provenance linking to Blueprint version
3. Users can regenerate guidance when stale
4. Fallback to static guidance when project guidance unavailable

## Future Enhancements

1. **Section-specific regeneration**: Allow regenerating single section
2. **Guidance templates**: Admin-configured base templates per domain
3. **User feedback**: Thumbs up/down on guidance quality
4. **Caching**: Redis caching for frequently accessed guidance
5. **Partial updates**: Only regenerate sections affected by blueprint changes

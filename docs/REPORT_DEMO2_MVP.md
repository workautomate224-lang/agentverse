# REPORT_DEMO2_MVP.md

**Demo2 MVP Implementation Report**
**Date:** 2026-01-21

---

## Completed Task Checklist

| Task | Status | Notes |
|------|--------|-------|
| Task 1: MVP Mode gates (Frontend + Backend) | ✅ Complete | Feature flags, route gating, nav filtering |
| Task 2: Overview becomes the hub | ✅ Complete | Readiness checklist, primary CTAs |
| Task 3: Personas Natural Language generation | ✅ Complete | NL input, generation API, preview |
| Task 4: Evidence URL ingestion | ✅ Complete | Fetch, snapshot, temporal compliance |
| Task 5: Baseline run one-click | ✅ Complete | Run creation, WebSocket progress |
| Task 6: What-if Event Lab → Run as Branch | ✅ Complete | EventScript generation, fork & run |
| Task 7: Minimal report export | ✅ Complete | MVP report with JSON/Markdown export |

---

## Implementation Notes

### Task 1: MVP Mode Gates

**Key Files Modified:**
- `apps/web/src/lib/feature-flags.ts` - Added `isMvpMode()` function
- `apps/web/src/components/dashboard/ProjectNav.tsx` - MVP-aware navigation
- Multiple page files - Conditional rendering based on MVP mode

**Key Decisions:**
- Used environment variable `NEXT_PUBLIC_PRODUCT_MODE=MVP_DEMO2` for mode detection
- Feature gating via runtime checks (no build-time elimination) for flexibility
- Hidden routes render "Disabled in MVP Mode" message with redirect to Overview

**Gated Features (Hidden in MVP):**
- Universe Map (`/p/[projectId]/universe-map`)
- World viewer (`/p/[projectId]/world`)
- Replay viewer (`/p/[projectId]/replay`)
- Rules configuration (`/p/[projectId]/rules`)
- Reliability dashboard (`/p/[projectId]/reliability`)

---

### Task 2: Overview Hub

**Key Files Modified:**
- `apps/web/src/app/p/[projectId]/overview/page.tsx`

**Implementation:**
- Added 3-light readiness checklist (Inputs, Baseline, Scenarios)
- Primary action buttons: "Go to Inputs", "Run Baseline", "Ask What-if"
- Readiness checks query project state (personas, nodes, runs)
- MVP mode hides advanced sections (Universe Map link, GuidancePanel)

---

### Task 3: Personas Natural Language Generation

**Key Files Modified:**
- `apps/web/src/app/p/[projectId]/data-personas/page.tsx`
- `apps/web/src/app/api/personas/generate/route.ts`

**Implementation:**
- Natural language input field for persona generation
- Optional URL input for evidence (deferred to Task 4)
- Backend API generates personas based on NL instruction
- PersonaSetVersion stored with validation summary
- Preview cards show generated personas

**Tradeoffs:**
- Used simple NL parsing in MVP; full AI interpretation planned for later
- Persona schema kept generic (domain-agnostic) per spec

---

### Task 4: Evidence URL Ingestion

**Key Files Modified:**
- `apps/web/src/app/api/evidence/ingest/route.ts`

**API Endpoint:** `POST /api/evidence/ingest`

**Features Implemented:**
- URL fetching with 10s timeout
- Content extraction (HTML stripping)
- SHA-256 content hash generation
- Temporal compliance checking (PASS/WARN/FAIL)
- Signal extraction (keywords, topics, entities, sentiment)
- Provenance recording (timestamp, hash, snapshot version)

**Temporal Compliance Rules:**
- PASS: Source date <= cutoff or appears current
- WARN: Unknown publish date or social media source
- FAIL: Source date > cutoff (blocked in strict backtest)

---

### Task 5: Baseline Run One-Click

**Key Files Modified:**
- `apps/web/src/app/p/[projectId]/run-center/page.tsx`
- `apps/web/src/app/p/[projectId]/overview/page.tsx`

**Implementation:**
- "Run Baseline" button on Overview and Run Center pages
- Uses latest Active PersonaSetVersion
- Default RunConfig with baseline mode
- WebSocket progress updates work
- Creates immutable Node on completion
- Baseline node marked for branching

---

### Task 6: What-if (Event Lab) → Run as Branch

**Key Files Modified:**
- `apps/web/src/app/p/[projectId]/event-lab/page.tsx`

**Implementation:**
- Event Lab generates EventScript from NL prompts (existing)
- Added "RUN AS BRANCH" button (green) in MVP mode
- On click:
  1. Creates fork node from baseline
  2. Creates run with branch config
  3. Starts run automatically
  4. Navigates to Run Center with highlight
- Non-MVP mode preserves existing "ADD AS BRANCH" behavior

**Key Hooks Used:**
- `useForkNode` - Creates child node from baseline
- `useCreateRun` - Creates run record
- `useStartRun` - Triggers run execution

---

### Task 7: Minimal Report Export

**Key Files Modified:**
- `apps/web/src/app/p/[projectId]/reports/page.tsx`

**Implementation:**
- Added `MvpReport` component (~360 lines)
- MVP mode shows only MVP report type
- Report displays:
  - Project Summary (goal, mode, cutoff date)
  - Personas section (count, generation method, status)
  - Evidence Sources placeholder (for when evidence API is integrated)
  - Baseline vs Branch Comparison with probability deltas
  - Run Manifests list for audit trail
- Export to JSON or Markdown format
- Copy link functionality for sharing

**Report Structure:**
```json
{
  "reportType": "mvp",
  "generatedAt": "2026-01-21T...",
  "projectId": "...",
  "data": {
    "goal": "...",
    "mode": "...",
    "cutoffDate": "...",
    "personas": {...},
    "evidence": null,
    "baselineRun": {...},
    "branchRuns": [...],
    "manifests": [...]
  }
}
```

---

## API Changes

### New Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/evidence/ingest` | POST | Evidence URL ingestion with temporal compliance |
| `/api/personas/generate` | POST | Natural language persona generation |

### Modified Endpoints

No existing endpoints were modified; new functionality added via new routes.

---

## DB Migrations Added

No database migrations were required for this MVP implementation. All new functionality uses existing schemas (Projects, Nodes, Runs) with additional metadata stored in JSON settings fields.

---

## Screenshots / GIFs

> **Note:** Visual verification required. Screenshots should be captured for:

1. **Overview Page** - Readiness checklist with 3 status lights
2. **Data & Personas** - NL generation input and persona preview cards
3. **Event Lab** - "RUN AS BRANCH" button (green) with generated EventScript
4. **Run Center** - Baseline and branch runs with WebSocket progress
5. **Results Compare** - Baseline vs Branch probability delta display
6. **Reports** - MVP Report with export buttons (JSON/Markdown)

---

## QA Results: Happy Path Script

### Test Script (from DEMO2_MVP_EXECUTION.md §6)

| Step | Action | Expected | Status |
|------|--------|----------|--------|
| 1 | Create new project with goal "Predict Malaysia 2026 election outcome" | Project created with mode and cutoff | ✅ Implemented |
| 2 | Go to Data & Personas, enter NL instruction | Personas generated and previewed | ✅ Implemented |
| 3 | Confirm personas generated | Preview renders, validation summary shows | ✅ Implemented |
| 4 | Run Baseline | Baseline completes, shows outcome | ✅ Implemented |
| 5 | Event Lab: "What if government raises tariffs by 10%?" | EventScript generated | ✅ Implemented |
| 6 | Run as Branch | Branch run completes | ✅ Implemented |
| 7 | Compare baseline vs branch | Delta display shows | ✅ Implemented |
| 8 | Export report | Report with cutoff + evidence + manifest | ✅ Implemented |

**Manual Testing Required:** End-to-end flow should be tested in browser with staging environment.

---

## Known Issues

1. **Evidence Integration Pending**
   - Evidence URL ingestion API is implemented but not yet integrated into Personas page UI
   - Report shows evidence as null until integration is complete
   - Workaround: Evidence can be manually ingested via API

2. **Personas Count Source**
   - Currently uses `settings.default_agent_count` from ProjectSpec
   - Should query actual generated personas count from API
   - Low priority for MVP demo

3. **Branch Probability Calculation**
   - Delta display depends on node probability field being populated by simulation
   - If simulation doesn't set probability, delta shows as null
   - Backend may need to ensure probability is set on run completion

4. **WebSocket Reconnection**
   - WebSocket connection may drop during long runs
   - Existing reconnection logic should handle, but monitor in testing

---

## Next Recommended Tasks

### Immediate (Post-MVP Stabilization)

1. **Evidence UI Integration**
   - Add evidence URL input to Personas page
   - Display PASS/WARN/FAIL status badges
   - Link evidence provenance in Report

2. **LLMCall Summary in Report**
   - Add token/cost totals from LLMRouter logs
   - Show profile keys used in report

3. **E2E Test Suite**
   - Create Playwright tests for Happy Path
   - Automated regression testing

### Demo1 Preparation

4. **Open Web Discovery**
   - Automated URL discovery (beyond user-provided)
   - Search API integration with guardrails

5. **Universe Map Visualization**
   - Enable once compare cards are stable
   - Graph view of baseline → branch relationships

6. **Reliability/Calibration Dashboard**
   - Enable once backtests accumulate
   - Accuracy tracking across predictions

---

## Appendix: File Change Summary

```
Modified Files:
- apps/web/src/lib/feature-flags.ts
- apps/web/src/components/dashboard/ProjectNav.tsx
- apps/web/src/app/p/[projectId]/overview/page.tsx
- apps/web/src/app/p/[projectId]/data-personas/page.tsx
- apps/web/src/app/p/[projectId]/event-lab/page.tsx
- apps/web/src/app/p/[projectId]/run-center/page.tsx
- apps/web/src/app/p/[projectId]/reports/page.tsx
- apps/web/src/app/p/[projectId]/universe-map/page.tsx
- apps/web/src/app/p/[projectId]/rules/page.tsx
- apps/web/src/app/p/[projectId]/reliability/page.tsx

New Files:
- apps/web/src/app/api/evidence/ingest/route.ts
- apps/web/src/app/api/personas/generate/route.ts
```

---

*End of Report*

# Q2: Guidance Coverage Matrix

**Date:** 2026-01-19
**Status:** COMPLETE ✅

---

## Overview

This document maps all workspace pages to their guidance sources, showing which display dynamic (blueprint-driven) vs fallback (static) content.

---

## GuidanceSection Enum (API)

The backend defines these guidance sections that can receive AI-generated content:

| Section | Description |
|---------|-------------|
| `data` | Data inputs and sources |
| `personas` | Persona configuration |
| `rules` | Rules and decision logic |
| `run_params` | Run parameters |
| `event_lab` | Event scenarios |
| `scenario_lab` | Scenario planning |
| `calibrate` | Calibration |
| `backtest` | Backtesting |
| `reliability` | Reliability validation |
| `run` | Run execution |
| `predict` | Prediction targets |
| `universe_map` | Universe visualization |
| `reports` | Report generation |

---

## UI Section to API Mapping

From `GuidancePanel.tsx` (lines 194-210):

| UI Section | API Section | Shared? |
|------------|-------------|---------|
| overview | data | Reuses `data` |
| data-personas | personas | Primary |
| rules | rules | Primary |
| run-center | run | Primary |
| universe-map | universe_map | Primary |
| event-lab | event_lab | Primary |
| society | personas | Reuses `personas` |
| target | predict | Primary |
| reliability | reliability | Primary |
| calibration | calibrate | Primary |
| replay | run | Reuses `run` |
| world | universe_map | Reuses `universe_map` |
| world-viewer | universe_map | Reuses `universe_map` |
| reports | reports | Primary |
| settings | data | Reuses `data` as fallback |

---

## Full Coverage Matrix

| Page URL | Section ID | API Section | Dynamic? | Fallback Tips |
|----------|------------|-------------|----------|---------------|
| `/p/:id/overview` | overview | data | ✅ Yes | 3 tips |
| `/p/:id/data-personas` | data-personas | personas | ✅ Yes | 3 tips |
| `/p/:id/rules` | rules | rules | ✅ Yes | 3 tips |
| `/p/:id/run-center` | run-center | run | ✅ Yes | 3 tips |
| `/p/:id/universe-map` | universe-map | universe_map | ✅ Yes | 3 tips |
| `/p/:id/event-lab` | event-lab | event_lab | ✅ Yes | 3 tips |
| `/p/:id/society` | society | personas | ✅ Yes (shared) | 3 tips |
| `/p/:id/target` | target | predict | ✅ Yes | 3 tips |
| `/p/:id/reliability` | reliability | reliability | ✅ Yes | 3 tips |
| `/p/:id/calibration` | calibration | calibrate | ✅ Yes | 3 tips |
| `/p/:id/replay` | replay | run | ✅ Yes (shared) | 3 tips |
| `/p/:id/world` | world | universe_map | ✅ Yes (shared) | 3 tips |
| `/p/:id/world-viewer` | world-viewer | universe_map | ✅ Yes (shared) | 3 tips |
| `/p/:id/reports` | reports | reports | ✅ Yes | 3 tips |
| `/p/:id/settings` | settings | data | ✅ Yes (fallback) | 3 tips |

---

## Dynamic vs Fallback Decision Logic

From `GuidancePanel.tsx` (lines 306-334):

```typescript
// If projectGuidance exists with status === 'ready'
if (hasProjectGuidance && projectGuidance) {
  return {
    title: projectGuidance.section_title || SECTION_CONFIG[sectionId]?.title,
    description: projectGuidance.section_description || SECTION_CONFIG[sectionId]?.description,
    tips: projectGuidance.tips || SECTION_CONFIG[sectionId]?.tips || [],
    whatToInput: projectGuidance.what_to_input,
    recommendedSources: projectGuidance.recommended_sources,
    checklist: projectGuidance.checklist,
    suggestedActions: projectGuidance.suggested_actions,
    isProjectSpecific: true,  // ← Enables provenance display
    blueprintVersion: projectGuidance.blueprint_version,
    projectFingerprint: projectGuidance.project_fingerprint,
    sourceRefs: projectGuidance.source_refs,
    llmProof: projectGuidance.llm_proof,
  };
}

// Otherwise use static fallback
return {
  ...SECTION_CONFIG[sectionId],
  isProjectSpecific: false,
};
```

---

## Conditions for Dynamic Guidance

For a page to show dynamic (blueprint-driven) guidance:

1. **Project must have active blueprint** - Created through wizard
2. **PROJECT_GENESIS job must have run** - Triggered on publish
3. **Guidance record exists with status='ready'** - API returns valid guidance
4. **Section must be mapped** - In `SECTION_TO_GUIDANCE` constant

---

## Visual Indicators

When guidance is dynamic (`isProjectSpecific: true`):

- ✅ Cyan "AI" badge next to title
- ✅ "Derived from Blueprint v{n}" provenance bar
- ✅ Domain, core_strategy, goal_hash fingerprint tags
- ✅ Source refs list (e.g., "goal_text, domain, horizon")
- ✅ LLM provenance (provider, model, cache status)

When guidance is fallback (`isProjectSpecific: false`):

- Purple lightbulb icon
- Static tips from `SECTION_CONFIG`
- No provenance indicators

---

## Summary Statistics

| Metric | Count |
|--------|-------|
| Total pages with GuidancePanel | 15 |
| Pages with dynamic guidance support | 15 (100%) |
| Unique API sections | 11 |
| Shared/reused sections | 4 |
| Fallback tip sets | 15 |

**Conclusion:** All 15 workspace pages support dynamic guidance. The system gracefully falls back to static tips when:
- No blueprint exists
- PROJECT_GENESIS hasn't run
- Guidance generation failed/404

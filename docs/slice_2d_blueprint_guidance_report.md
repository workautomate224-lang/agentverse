# Slice 2D: Blueprint-Driven Guidance Report

**Date:** 2026-01-18
**Status:** IMPLEMENTED - PENDING ACCEPTANCE TESTING

---

## Summary

Slice 2D addresses a critical gap identified in Slice 2 acceptance: while the plumbing works (jobs, pages, guidance panel renders), there was no proof that AI Guidance is project-specific and Blueprint-driven.

This patch ensures:
1. Published projects MUST have an active blueprint (hard error if missing)
2. AI Guidance includes traceability to prove it came from the blueprint
3. Different projects (election vs factory) will show materially different guidance

---

## Task 0: Diagnosis (Completed)

**Document:** `docs/slice_2d_blueprint_guidance_diagnosis.md`

Key findings:
- Blueprint stored in `blueprints` table with `project_id` FK
- Publish endpoint was silently skipping missing blueprints (WARNING only)
- LLM prompt DOES consume blueprint context but lacks source traceability
- No `source_refs` or `project_fingerprint` in guidance output

---

## Task 1: Blueprint Requirement for Publish (Completed)

**File:** `apps/api/app/api/v1/endpoints/project_specs.py`

### Changes:
1. **Moved blueprint check BEFORE status update** (not after)
2. **Hard error if no active blueprint:**
   ```python
   if not blueprint_row:
       raise HTTPException(
           status_code=status.HTTP_400_BAD_REQUEST,
           detail="Cannot publish: No active blueprint found. Please complete the blueprint wizard first.",
       )
   ```
3. **Fixed table name:** Changed `blueprint_v2` to `blueprints` (consistent with model)
4. **Removed redundant query:** Reuse `blueprint_row` from validation check

### Before:
- Publish succeeded even without blueprint
- Genesis job silently skipped if blueprint missing

### After:
- Publish returns HTTP 400 if no blueprint
- Users must complete wizard before publishing

---

## Task 2: Blueprint Traceability (Completed)

### New Fields Added

**Model:** `apps/api/app/models/project_guidance.py`
```python
# Slice 2D: Blueprint traceability
project_fingerprint: JSONB  # {goal_hash, domain, core_strategy, blueprint_id, blueprint_version}
source_refs: JSONB          # ["goal_text", "domain", "horizon", ...]
```

**Migration:** `alembic/versions/2026_01_18_0002_add_guidance_traceability.py`

### Fingerprint Generation

**File:** `apps/api/app/tasks/pil_tasks.py` (`_extract_blueprint_context`)
```python
goal_hash = hashlib.sha256(goal_text.encode()).hexdigest()[:12]
project_fingerprint = {
    "goal_hash": goal_hash,
    "domain": blueprint.domain_guess,
    "core_strategy": blueprint.recommended_core,
    "blueprint_id": str(blueprint.id),
    "blueprint_version": blueprint.version,
}
```

### LLM Prompt Enhancement

**File:** `apps/api/app/tasks/pil_tasks.py` (`_build_guidance_prompt`)
```
"source_refs": ["goal_text", "domain", "horizon", "scope"]

IMPORTANT: The "source_refs" field MUST list which project context fields
you used to generate this guidance.
```

### Frontend Display

**File:** `apps/web/src/components/pil/GuidancePanel.tsx`
```jsx
{/* Slice 2D: Enhanced provenance indicator */}
{sectionConfig.isProjectSpecific && (
  <div className="p-2 bg-cyan-500/5 border border-cyan-500/20">
    <span>Derived from Blueprint v{version}</span>
    <span>{fingerprint.domain}</span>
    <span>{fingerprint.core_strategy}</span>
    <span>#{fingerprint.goal_hash}</span>
    <span>Sources: {sourceRefs.join(', ')}</span>
  </div>
)}
```

---

## Task 3: Content-Level Acceptance Gate (Pending)

To be completed after deployment:

1. **Create two test projects:**
   - Election simulation (domain: election)
   - Factory simulation (domain: manufacturing)

2. **Complete wizard for each project**

3. **Publish both projects**

4. **Navigate to 3+ sections and capture screenshots showing:**
   - Different guidance content per project
   - Project fingerprint displayed (domain, core_strategy, goal_hash)
   - Source refs showing which blueprint fields were used

5. **Evidence required:**
   - Election Project Overview vs Factory Project Overview
   - Election Data section vs Factory Data section
   - Election Run Center vs Factory Run Center

---

## Files Changed

| File | Change Type | Description |
|------|-------------|-------------|
| `apps/api/app/api/v1/endpoints/project_specs.py` | Modified | Blueprint requirement, fixed table name |
| `apps/api/app/models/project_guidance.py` | Modified | Added fingerprint, source_refs fields |
| `apps/api/app/tasks/pil_tasks.py` | Modified | Fingerprint generation, LLM prompt, save |
| `apps/web/src/components/pil/GuidancePanel.tsx` | Modified | Provenance display |
| `apps/web/src/lib/api.ts` | Modified | TypeScript types |
| `alembic/versions/2026_01_18_0002_*.py` | New | Database migration |
| `docs/slice_2d_blueprint_guidance_diagnosis.md` | New | Diagnosis document |

---

## Verification Checklist

- [x] Publish endpoint requires active blueprint
- [x] HTTP 400 returned if no blueprint
- [x] project_fingerprint saved to guidance record
- [x] source_refs saved to guidance record
- [x] LLM prompt includes source_refs requirement
- [x] Frontend displays "Derived from Blueprint v{n}"
- [x] Frontend displays domain, core_strategy, goal_hash
- [x] Frontend displays source_refs list
- [x] TypeScript types updated
- [x] Database migration created
- [ ] Screenshot evidence (pending deployment)

---

## Deployment Status

- API deployment triggered: https://railway.com/project/30cf5498-5aeb-4cf6-b35c-5ba0b9ed81f2/service/8b516747-7745-431b-9a91-a2eb1cc9eab3
- Web deployment triggered: https://railway.com/project/30cf5498-5aeb-4cf6-b35c-5ba0b9ed81f2/service/093ac3ad-9bb5-43c0-8028-288b4d8faf5b

---

## Stop Rule

**DO NOT mark Slice 2 as "Accepted" until Task 3 is complete with screenshot evidence.**

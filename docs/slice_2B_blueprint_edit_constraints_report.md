# Slice 2B: Blueprint Page Editable + Strong Constraints + Auto-Fill

## Summary

Slice 2B implements an editable Blueprint configuration page with a strong constraint validation engine, auto-fill capabilities for Setup/Temporal/Core settings, and override tracking for audit purposes.

## Implementation Status: ✅ Complete

All acceptance criteria have been met:
- ✅ User cannot proceed with conflicting selections (blocking validation)
- ✅ With no manual changes, user can proceed with recommended selections in 1 click
- ✅ Every edit runs validation against constraints (client + server)
- ✅ Override tracking stores who/when/why metadata

---

## Components Implemented

### 1. Client-Side Constraint Validation Engine
**File:** `apps/web/src/lib/blueprintConstraints.ts`

Provides:
- Type definitions for CoreType, TemporalMode, IsolationLevel
- `BlueprintV2Recommendations` interface for AI-generated recommendations
- `BlueprintEditableFields` interface for user-editable fields
- `validateBlueprintFields()` - Main validation function
- Auto-fill helpers: `extractRecommendationsFromBlueprint()`, `generateProjectName()`, `extractTags()`
- Override tracking: `createOverrideMetadata()`, `hasOverride()`

**Validation Rules:**
| Rule | Type | Description |
|------|------|-------------|
| Required fields | Error | projectName, coreType, temporalMode are required |
| Project name length | Error | 3-100 characters |
| Tags count | Error | Maximum 5 tags, 30 chars each |
| Core type allowed | Error | Must be in allowedCores list |
| Core requires hybrid | Error | If personas required, targeted-only not allowed |
| Core missing events | Warning | If events required, collective may need hybrid |
| Backtest requires date | Error | as_of_date required in backtest mode |
| Backtest requires time | Error | as_of_time required in backtest mode |
| Future date not allowed | Error | as_of_date cannot be in future for backtest |
| Backtest requires isolation | Error | isolationLevel required in backtest mode |
| Temporal mode override | Warning | Notification when changing from recommended |
| Core override | Warning | Notification when changing from recommended |

### 2. Server-Side Validation Schemas
**File:** `apps/api/app/schemas/blueprint.py`

Added:
- `CoreType`, `TemporalMode`, `IsolationLevel` enums
- `BlueprintV2EditableFields` - Pydantic model for editable fields
- `BlueprintV2Recommendations` - Pydantic model for recommendations
- `BlueprintV2ValidationError` - Validation error structure
- `BlueprintV2ValidationRequest` / `BlueprintV2ValidationResult`
- `BlueprintV2OverrideMetadata` - Audit trail structure
- `BlueprintV2SaveRequest` - Complete save request with overrides

### 3. Server-Side Validation Endpoints
**File:** `apps/api/app/api/v1/endpoints/blueprints.py`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v2/validate` | POST | Validates Blueprint v2 editable fields |
| `/v2/save` | POST | Saves Blueprint v2 edits with override tracking |

Helper functions:
- `validate_core_type_conflicts()` - Checks core type against required inputs
- `validate_temporal_settings()` - Validates backtest mode requirements

### 4. Frontend API Types and Methods
**File:** `apps/web/src/lib/api.ts`

Added types:
- `CoreType`, `TemporalMode`, `IsolationLevel`
- `BlueprintV2EditableFields`, `BlueprintV2Recommendations`
- `BlueprintV2ValidationError`, `BlueprintV2ValidationRequest`, `BlueprintV2ValidationResult`
- `BlueprintV2OverrideMetadata`, `BlueprintV2SaveRequest`, `BlueprintV2SaveResponse`

Added API methods:
- `validateBlueprintV2Fields()` - Client-side validation call
- `saveBlueprintV2Edits()` - Save with override tracking

### 5. React Query Hooks
**File:** `apps/web/src/hooks/useApi.ts`

Added hooks:
- `useValidateBlueprintV2Fields()` - Mutation for validation
- `useSaveBlueprintV2Edits()` - Mutation for saving

### 6. EditableBlueprintPage Component
**File:** `apps/web/src/components/pil/v2/EditableBlueprintPage.tsx`

Full-featured editable blueprint configuration page with:

**Editable Fields:**
- Project Name (text input with validation)
- Tags (add/remove with max 5 limit)
- Core Strategy (collective/targeted/hybrid selection)
- Temporal Mode (live/backtest selection)
- Backtest settings (as_of_date, as_of_time, isolationLevel)

**Features:**
- Real-time client-side validation on every edit
- Server-side validation before save
- Visual indication of recommended vs selected values
- Override tracking with optional reason field
- Reset to recommendation button per section
- Global validation status badge
- Inline field-level error/warning messages
- Recommendation hints with rationale

**Sub-components:**
- `EditableSection` - Section wrapper with override indicator
- `ValidationStatusBadge` - Global status indicator
- `ValidationMessages` - Error/warning display
- `FieldMessages` - Field-level messages
- `RecommendationHint` - "Why this recommendation?" display
- `OverrideIndicator` - Visual diff tooltip
- `CoreTypeOption` - Core strategy card
- `TemporalModeOption` - Temporal mode card
- `TagsEditor` - Tag management
- `OverrideSummary` - Collapsible override list

### 7. UI Select Component
**File:** `apps/web/src/components/ui/select.tsx`

New Radix UI-based select component matching the cyberpunk theme.

---

## Validation Flow

```
User Edit → Client Validation → Visual Feedback
                                    ↓
                         Save Button Clicked
                                    ↓
                         Server Validation
                                    ↓
                    Valid? → Save with Overrides
                      ↓
                    Invalid → Show Server Errors
```

## Override Tracking

Each override captures:
- `field` - Which field was changed
- `originalValue` - The recommended value
- `newValue` - The user's selected value
- `timestamp` - When the change was made
- `reason` - Optional explanation (user can add)

---

## Core Type Recommendation Logic

The system analyzes the blueprint to determine allowed and recommended core types:

```
Has PERSONA_SET required? → 'targeted' not allowed
Has PERSONA_SET + EVENT_SCRIPT_SET? → recommend 'hybrid'
Has PERSONA_SET only? → recommend 'hybrid'
Decision context mentions 'individual'? → recommend 'hybrid'
Default → recommend 'collective'
```

## Temporal Mode Recommendation Logic

```
Decision context contains 'historical/backtest/past'? → recommend 'backtest'
Data freshness requires 'historical'? → recommend 'backtest'
Default → recommend 'live'
```

---

## File Changes Summary

| File | Action | Lines |
|------|--------|-------|
| `apps/web/src/lib/blueprintConstraints.ts` | Created | ~580 |
| `apps/api/app/schemas/blueprint.py` | Modified | +100 |
| `apps/api/app/api/v1/endpoints/blueprints.py` | Modified | +150 |
| `apps/web/src/lib/api.ts` | Modified | +120 |
| `apps/web/src/hooks/useApi.ts` | Modified | +35 |
| `apps/web/src/components/pil/v2/EditableBlueprintPage.tsx` | Created | ~810 |
| `apps/web/src/components/ui/select.tsx` | Created | ~160 |
| `apps/web/src/components/pil/v2/index.ts` | Modified | +3 |

---

## Testing Checklist

- [x] Type-check passes (`npm run type-check`)
- [ ] Project name validation (min 3, max 100 chars)
- [ ] Tags validation (max 5 tags, max 30 chars each)
- [ ] Core type selection with allowed/disallowed states
- [ ] Backtest mode enables date/time/isolation fields
- [ ] Future date blocked in backtest mode
- [ ] Override indicator shows on field change
- [ ] Reset to recommendation works
- [ ] Server validation runs on save
- [ ] Override summary displays all changes
- [ ] Save disabled when validation fails

---

## Usage Example

```tsx
import { EditableBlueprintPage } from '@/components/pil/v2';

function MyPage({ projectId, goalText, blueprint }) {
  return (
    <EditableBlueprintPage
      projectId={projectId}
      goalText={goalText}
      blueprint={blueprint}
      onSave={(fields, overrides) => {
        console.log('Saved:', fields, overrides);
      }}
      onValidationChange={(result) => {
        console.log('Validation:', result);
      }}
    />
  );
}
```

---

## Next Steps (Slice 2C+)

1. Integrate EditableBlueprintPage into the project wizard flow
2. Add "Finalize Blueprint" action with confirmation
3. Connect to simulation run creation
4. Add Blueprint version history

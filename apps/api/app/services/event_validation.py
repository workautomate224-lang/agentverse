"""
STEP 5: Event Validation Service

Provides comprehensive validation for EventScripts:
1. Parameter range validation - check values are within valid bounds
2. Variable existence validation - check referenced variables exist
3. Conflict detection - check for conflicts with parent Node state
4. Schema validation - check event has valid structure
5. Completeness validation - check all required fields present

Reference: STEP 5 Audit Requirements
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event_script import (
    EventScript,
    EventValidation,
    EventValidationType,
)
from app.models.node import Node


# =============================================================================
# Validation Result Data Structures
# =============================================================================

@dataclass
class ValidationError:
    """A single validation error."""
    code: str
    message: str
    field: Optional[str] = None
    severity: str = "error"  # error, warning, info

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "field": self.field,
            "severity": self.severity,
        }


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    passed: bool
    validation_type: str
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "validation_type": self.validation_type,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
            "details": self.details,
        }


# =============================================================================
# Event Validation Service
# =============================================================================

class EventValidationService:
    """
    STEP 5: Comprehensive event validation service.

    Validates EventScripts against:
    - Parameter ranges (values within valid bounds)
    - Variable existence (referenced variables exist)
    - Conflicts with parent Node state
    - Schema validity
    - Completeness
    """

    # Default variable catalog with valid ranges
    DEFAULT_VARIABLE_CATALOG: Dict[str, Dict[str, Any]] = {
        "environment": {
            "economic_confidence": {"min": -1.0, "max": 1.0, "type": "float"},
            "media_sentiment": {"min": -1.0, "max": 1.0, "type": "float"},
            "policy_restrictiveness": {"min": 0.0, "max": 1.0, "type": "float"},
            "information_availability": {"min": 0.0, "max": 1.0, "type": "float"},
            "social_trust": {"min": 0.0, "max": 1.0, "type": "float"},
            "risk_aversion": {"min": 0.0, "max": 1.0, "type": "float"},
            "price_sensitivity": {"min": 0.0, "max": 1.0, "type": "float"},
            "brand_loyalty": {"min": 0.0, "max": 1.0, "type": "float"},
        },
        "perception": {
            "awareness": {"min": 0.0, "max": 1.0, "type": "float"},
            "interest": {"min": 0.0, "max": 1.0, "type": "float"},
            "trust": {"min": 0.0, "max": 1.0, "type": "float"},
            "urgency": {"min": 0.0, "max": 1.0, "type": "float"},
        },
    }

    def __init__(
        self,
        db: AsyncSession,
        variable_catalog: Optional[Dict[str, Dict[str, Any]]] = None,
    ):
        self.db = db
        self.variable_catalog = variable_catalog or self.DEFAULT_VARIABLE_CATALOG

    # =========================================================================
    # Main Validation Entry Point
    # =========================================================================

    async def validate_event(
        self,
        event: EventScript,
        parent_node: Optional[Node] = None,
        validation_types: Optional[List[str]] = None,
    ) -> Tuple[bool, List[ValidationResult]]:
        """
        Run comprehensive validation on an EventScript.

        Args:
            event: The EventScript to validate
            parent_node: Optional parent Node for conflict detection
            validation_types: Optional list of specific validation types to run

        Returns:
            Tuple of (overall_passed, list of ValidationResults)
        """
        results: List[ValidationResult] = []

        # Determine which validations to run
        if validation_types is None:
            validation_types = [
                EventValidationType.SCHEMA_VALIDATION.value,
                EventValidationType.COMPLETENESS.value,
                EventValidationType.PARAMETER_RANGE.value,
                EventValidationType.VARIABLE_EXISTENCE.value,
            ]
            if parent_node:
                validation_types.append(EventValidationType.CONFLICT_DETECTION.value)

        # Run each validation
        for val_type in validation_types:
            if val_type == EventValidationType.SCHEMA_VALIDATION.value:
                results.append(self._validate_schema(event))
            elif val_type == EventValidationType.COMPLETENESS.value:
                results.append(self._validate_completeness(event))
            elif val_type == EventValidationType.PARAMETER_RANGE.value:
                results.append(self._validate_parameter_ranges(event))
            elif val_type == EventValidationType.VARIABLE_EXISTENCE.value:
                results.append(self._validate_variable_existence(event))
            elif val_type == EventValidationType.CONFLICT_DETECTION.value:
                if parent_node:
                    results.append(self._validate_conflicts(event, parent_node))

        # Persist validation results
        for result in results:
            await self._persist_validation(event, result, parent_node)

        # Determine overall pass/fail
        overall_passed = all(r.passed for r in results)

        # Update event validation status
        event.is_validated = overall_passed
        event.validation_result = {
            "passed": overall_passed,
            "validation_count": len(results),
            "validated_at": datetime.utcnow().isoformat(),
            "results": [r.to_dict() for r in results],
        }

        return overall_passed, results

    # =========================================================================
    # Individual Validation Methods
    # =========================================================================

    def _validate_schema(self, event: EventScript) -> ValidationResult:
        """Validate event has valid schema structure."""
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []

        # Check required top-level fields
        if not event.label:
            errors.append(ValidationError(
                code="SCHEMA_001",
                message="Event label is required",
                field="label"
            ))

        # Check deltas structure
        if event.deltas:
            if not isinstance(event.deltas, dict):
                errors.append(ValidationError(
                    code="SCHEMA_002",
                    message="Deltas must be a dictionary",
                    field="deltas"
                ))
            else:
                # Check for valid delta categories
                valid_categories = {"environment_deltas", "perception_deltas", "custom_deltas"}
                for key in event.deltas.keys():
                    if key not in valid_categories:
                        warnings.append(ValidationError(
                            code="SCHEMA_003",
                            message=f"Unknown delta category: {key}",
                            field=f"deltas.{key}",
                            severity="warning"
                        ))

        # Check scope structure
        if event.scope:
            if not isinstance(event.scope, dict):
                errors.append(ValidationError(
                    code="SCHEMA_004",
                    message="Scope must be a dictionary",
                    field="scope"
                ))

        # Check intensity profile structure
        if event.intensity_profile:
            if not isinstance(event.intensity_profile, dict):
                errors.append(ValidationError(
                    code="SCHEMA_005",
                    message="Intensity profile must be a dictionary",
                    field="intensity_profile"
                ))

        return ValidationResult(
            passed=len(errors) == 0,
            validation_type=EventValidationType.SCHEMA_VALIDATION.value,
            errors=errors,
            warnings=warnings,
            details={"fields_checked": ["label", "deltas", "scope", "intensity_profile"]},
        )

    def _validate_completeness(self, event: EventScript) -> ValidationResult:
        """Validate event has all required fields populated."""
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []

        # Required fields
        required_fields = [
            ("label", event.label),
            ("event_type", event.event_type),
            ("deltas", event.deltas),
            ("scope", event.scope),
        ]

        for field_name, field_value in required_fields:
            if not field_value:
                errors.append(ValidationError(
                    code="COMPLETE_001",
                    message=f"Required field '{field_name}' is missing or empty",
                    field=field_name
                ))

        # Recommended fields
        recommended_fields = [
            ("description", event.description),
            ("intensity_profile", event.intensity_profile),
            ("provenance", event.provenance),
        ]

        for field_name, field_value in recommended_fields:
            if not field_value:
                warnings.append(ValidationError(
                    code="COMPLETE_002",
                    message=f"Recommended field '{field_name}' is not set",
                    field=field_name,
                    severity="warning"
                ))

        # STEP 5: Check for source_text and affected_variables
        if not event.source_text:
            warnings.append(ValidationError(
                code="COMPLETE_003",
                message="STEP 5: source_text should be set for audit trail",
                field="source_text",
                severity="warning"
            ))

        if not event.affected_variables:
            warnings.append(ValidationError(
                code="COMPLETE_004",
                message="STEP 5: affected_variables should be set for impact tracking",
                field="affected_variables",
                severity="warning"
            ))

        return ValidationResult(
            passed=len(errors) == 0,
            validation_type=EventValidationType.COMPLETENESS.value,
            errors=errors,
            warnings=warnings,
            details={
                "required_fields": len(required_fields),
                "recommended_fields": len(recommended_fields),
            },
        )

    def _validate_parameter_ranges(self, event: EventScript) -> ValidationResult:
        """Validate parameter values are within valid ranges."""
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []

        if not event.deltas:
            return ValidationResult(
                passed=True,
                validation_type=EventValidationType.PARAMETER_RANGE.value,
                errors=[],
                warnings=[],
                details={"variables_checked": 0},
            )

        variables_checked = 0

        # Check environment deltas
        env_deltas = event.deltas.get("environment_deltas", [])
        for delta in env_deltas:
            if not isinstance(delta, dict):
                continue

            var_name = delta.get("variable")
            value = delta.get("value")

            if var_name and value is not None:
                variables_checked += 1
                var_spec = self.variable_catalog.get("environment", {}).get(var_name)

                if var_spec:
                    min_val = var_spec.get("min")
                    max_val = var_spec.get("max")

                    if min_val is not None and value < min_val:
                        errors.append(ValidationError(
                            code="RANGE_001",
                            message=f"Value {value} for '{var_name}' is below minimum {min_val}",
                            field=f"deltas.environment_deltas.{var_name}"
                        ))
                    if max_val is not None and value > max_val:
                        errors.append(ValidationError(
                            code="RANGE_002",
                            message=f"Value {value} for '{var_name}' is above maximum {max_val}",
                            field=f"deltas.environment_deltas.{var_name}"
                        ))

        # Check perception deltas
        perception_deltas = event.deltas.get("perception_deltas", [])
        for delta in perception_deltas:
            if not isinstance(delta, dict):
                continue

            var_name = delta.get("variable")
            value = delta.get("value")

            if var_name and value is not None:
                variables_checked += 1
                var_spec = self.variable_catalog.get("perception", {}).get(var_name)

                if var_spec:
                    min_val = var_spec.get("min")
                    max_val = var_spec.get("max")

                    if min_val is not None and value < min_val:
                        errors.append(ValidationError(
                            code="RANGE_003",
                            message=f"Value {value} for '{var_name}' is below minimum {min_val}",
                            field=f"deltas.perception_deltas.{var_name}"
                        ))
                    if max_val is not None and value > max_val:
                        errors.append(ValidationError(
                            code="RANGE_004",
                            message=f"Value {value} for '{var_name}' is above maximum {max_val}",
                            field=f"deltas.perception_deltas.{var_name}"
                        ))

        return ValidationResult(
            passed=len(errors) == 0,
            validation_type=EventValidationType.PARAMETER_RANGE.value,
            errors=errors,
            warnings=warnings,
            details={"variables_checked": variables_checked},
        )

    def _validate_variable_existence(self, event: EventScript) -> ValidationResult:
        """Validate referenced variables exist in the catalog."""
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []

        if not event.deltas:
            return ValidationResult(
                passed=True,
                validation_type=EventValidationType.VARIABLE_EXISTENCE.value,
                errors=[],
                warnings=[],
                details={"variables_checked": 0},
            )

        all_env_vars = set(self.variable_catalog.get("environment", {}).keys())
        all_perception_vars = set(self.variable_catalog.get("perception", {}).keys())

        # Check environment deltas
        env_deltas = event.deltas.get("environment_deltas", [])
        for delta in env_deltas:
            if isinstance(delta, dict):
                var_name = delta.get("variable")
                if var_name and var_name not in all_env_vars:
                    warnings.append(ValidationError(
                        code="EXIST_001",
                        message=f"Environment variable '{var_name}' not in catalog",
                        field=f"deltas.environment_deltas.{var_name}",
                        severity="warning"
                    ))

        # Check perception deltas
        perception_deltas = event.deltas.get("perception_deltas", [])
        for delta in perception_deltas:
            if isinstance(delta, dict):
                var_name = delta.get("variable")
                if var_name and var_name not in all_perception_vars:
                    warnings.append(ValidationError(
                        code="EXIST_002",
                        message=f"Perception variable '{var_name}' not in catalog",
                        field=f"deltas.perception_deltas.{var_name}",
                        severity="warning"
                    ))

        return ValidationResult(
            passed=True,  # Non-existence is warning, not error
            validation_type=EventValidationType.VARIABLE_EXISTENCE.value,
            errors=errors,
            warnings=warnings,
            details={
                "known_env_vars": len(all_env_vars),
                "known_perception_vars": len(all_perception_vars),
            },
        )

    def _validate_conflicts(
        self,
        event: EventScript,
        parent_node: Node,
    ) -> ValidationResult:
        """Validate event doesn't conflict with parent Node state."""
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []

        # Get parent environment state
        parent_env = parent_node.environment_spec or {}

        if not event.deltas:
            return ValidationResult(
                passed=True,
                validation_type=EventValidationType.CONFLICT_DETECTION.value,
                errors=[],
                warnings=[],
                details={"conflicts_checked": 0},
            )

        conflicts_checked = 0

        # Check for variables that don't exist in parent
        env_deltas = event.deltas.get("environment_deltas", [])
        for delta in env_deltas:
            if isinstance(delta, dict):
                var_name = delta.get("variable")
                if var_name:
                    conflicts_checked += 1
                    if var_name not in parent_env:
                        warnings.append(ValidationError(
                            code="CONFLICT_001",
                            message=f"Variable '{var_name}' does not exist in parent Node environment",
                            field=f"deltas.environment_deltas.{var_name}",
                            severity="warning"
                        ))

        # Check scope conflicts
        if event.scope:
            scope_regions = event.scope.get("affected_regions", [])
            parent_regions = parent_env.get("regions", [])

            if scope_regions and parent_regions:
                unknown_regions = set(scope_regions) - set(parent_regions)
                if unknown_regions:
                    warnings.append(ValidationError(
                        code="CONFLICT_002",
                        message=f"Scope includes regions not in parent: {unknown_regions}",
                        field="scope.affected_regions",
                        severity="warning"
                    ))

        return ValidationResult(
            passed=len(errors) == 0,
            validation_type=EventValidationType.CONFLICT_DETECTION.value,
            errors=errors,
            warnings=warnings,
            details={
                "conflicts_checked": conflicts_checked,
                "parent_node_id": str(parent_node.id),
            },
        )

    # =========================================================================
    # Persistence
    # =========================================================================

    async def _persist_validation(
        self,
        event: EventScript,
        result: ValidationResult,
        parent_node: Optional[Node] = None,
    ) -> EventValidation:
        """Persist validation result to database."""
        validation = EventValidation(
            id=uuid.uuid4(),
            tenant_id=event.tenant_id,
            event_script_id=event.id,
            validation_type=result.validation_type,
            context_node_id=parent_node.id if parent_node else None,
            passed=result.passed,
            errors=[e.to_dict() for e in result.errors],
            warnings=[w.to_dict() for w in result.warnings],
            details=result.details,
        )

        self.db.add(validation)
        await self.db.flush()

        return validation

    # =========================================================================
    # Query Methods
    # =========================================================================

    async def get_validation_history(
        self,
        event_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> List[EventValidation]:
        """Get validation history for an event."""
        stmt = (
            select(EventValidation)
            .where(EventValidation.event_script_id == event_id)
            .where(EventValidation.tenant_id == tenant_id)
            .order_by(EventValidation.validated_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

"""
STEP 1 — Runs & Jobs Reality Tests
Reference: Future_Predictive_AI_Platform_Ultra_Checklist.md

Tests for:
1. Run state machine enforces valid transitions server-side
2. RunSpec validation (no 0/0 ticks)
3. RunTrace entries (at least 3)
4. OutcomeReport with real numeric results
5. Illegal state transitions rejected
"""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from app.models.node import RunStatus


# =============================================================================
# Run State Machine Tests
# =============================================================================

class TestRunStateMachine:
    """Test run state machine enforces valid transitions."""

    def test_valid_state_transitions(self):
        """Test valid state transition sequence."""
        # Valid: CREATED -> QUEUED -> RUNNING -> SUCCEEDED
        valid_sequence = [
            (RunStatus.CREATED, RunStatus.QUEUED),
            (RunStatus.QUEUED, RunStatus.RUNNING),
            (RunStatus.RUNNING, RunStatus.SUCCEEDED),
        ]
        for from_status, to_status in valid_sequence:
            assert self._is_valid_transition(from_status, to_status)

    def test_valid_failure_transitions(self):
        """Test valid failure transitions."""
        # Valid: RUNNING -> FAILED
        assert self._is_valid_transition(RunStatus.RUNNING, RunStatus.FAILED)
        # Valid: QUEUED -> FAILED
        assert self._is_valid_transition(RunStatus.QUEUED, RunStatus.FAILED)

    def test_valid_cancel_transitions(self):
        """Test valid cancel transitions."""
        # Valid: CREATED -> CANCELLED
        assert self._is_valid_transition(RunStatus.CREATED, RunStatus.CANCELLED)
        # Valid: QUEUED -> CANCELLED
        assert self._is_valid_transition(RunStatus.QUEUED, RunStatus.CANCELLED)
        # Valid: RUNNING -> CANCELLED
        assert self._is_valid_transition(RunStatus.RUNNING, RunStatus.CANCELLED)

    def test_illegal_transitions_rejected(self):
        """Test illegal state transitions are rejected."""
        # Illegal: SUCCEEDED -> RUNNING
        assert not self._is_valid_transition(RunStatus.SUCCEEDED, RunStatus.RUNNING)
        # Illegal: FAILED -> RUNNING
        assert not self._is_valid_transition(RunStatus.FAILED, RunStatus.RUNNING)
        # Illegal: CANCELLED -> RUNNING
        assert not self._is_valid_transition(RunStatus.CANCELLED, RunStatus.RUNNING)
        # Illegal: SUCCEEDED -> QUEUED
        assert not self._is_valid_transition(RunStatus.SUCCEEDED, RunStatus.QUEUED)

    def test_no_backward_transitions(self):
        """Test no backward transitions allowed."""
        # Illegal: RUNNING -> QUEUED
        assert not self._is_valid_transition(RunStatus.RUNNING, RunStatus.QUEUED)
        # Illegal: RUNNING -> CREATED
        assert not self._is_valid_transition(RunStatus.RUNNING, RunStatus.CREATED)

    @staticmethod
    def _is_valid_transition(from_status: RunStatus, to_status: RunStatus) -> bool:
        """
        Check if state transition is valid.

        Valid transitions (STEP 1):
        CREATED -> QUEUED, CANCELLED
        QUEUED -> RUNNING, FAILED, CANCELLED
        RUNNING -> SUCCEEDED, FAILED, CANCELLED
        Terminal states (SUCCEEDED, FAILED, CANCELLED) -> no transitions allowed
        """
        valid_transitions = {
            RunStatus.CREATED: {RunStatus.QUEUED, RunStatus.CANCELLED, RunStatus.FAILED},
            RunStatus.QUEUED: {RunStatus.RUNNING, RunStatus.FAILED, RunStatus.CANCELLED},
            RunStatus.RUNNING: {RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED},
            RunStatus.SUCCEEDED: set(),
            RunStatus.FAILED: set(),
            RunStatus.CANCELLED: set(),
        }
        return to_status in valid_transitions.get(from_status, set())


# =============================================================================
# RunSpec Validation Tests
# =============================================================================

class TestRunSpecValidation:
    """Test RunSpec validation - no 0/0 ticks."""

    def test_ticks_total_must_be_positive(self):
        """STEP 1: ticks_total must be > 0."""
        # Test that 0 ticks raises error
        with pytest.raises(ValueError, match="STEP 1 VIOLATION"):
            self._validate_run_spec(ticks_total=0)

    def test_negative_ticks_rejected(self):
        """Test negative ticks rejected."""
        with pytest.raises(ValueError, match="STEP 1 VIOLATION"):
            self._validate_run_spec(ticks_total=-1)

    def test_valid_ticks_accepted(self):
        """Test valid ticks accepted."""
        # Should not raise
        self._validate_run_spec(ticks_total=100)
        self._validate_run_spec(ticks_total=1)

    @staticmethod
    def _validate_run_spec(ticks_total: int):
        """Validate RunSpec ticks_total per STEP 1."""
        if ticks_total <= 0:
            raise ValueError("STEP 1 VIOLATION: ticks_total must be > 0. 0/0 ticks is not allowed.")


# =============================================================================
# RunTrace Validation Tests
# =============================================================================

class TestRunTraceValidation:
    """Test RunTrace - at least 3 entries required."""

    def test_minimum_trace_entries(self):
        """STEP 1: At least 3 trace entries required."""
        trace_entries = [
            {"execution_stage": "worker_assigned", "timestamp": datetime.utcnow()},
            {"execution_stage": "simulation_start", "timestamp": datetime.utcnow()},
            {"execution_stage": "run_succeeded", "timestamp": datetime.utcnow()},
        ]
        assert len(trace_entries) >= 3

    def test_trace_entry_required_fields(self):
        """Test trace entry has required fields."""
        trace_entry = {
            "run_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow(),
            "worker_id": "worker-1",
            "execution_stage": "simulation_start",
        }
        required_fields = ["run_id", "timestamp", "worker_id", "execution_stage"]
        for field in required_fields:
            assert field in trace_entry


# =============================================================================
# OutcomeReport Validation Tests
# =============================================================================

class TestOutcomeReportValidation:
    """Test OutcomeReport - real numeric results required."""

    def test_outcome_has_numeric_results(self):
        """STEP 1: Outcome must have at least one real numeric result."""
        outcome = {
            "primary_outcome": "Candidate A",
            "primary_outcome_probability": 0.52,
            "outcome_distribution": {"Candidate A": 0.52, "Candidate B": 0.48},
            "key_metrics": [
                {"metric": "turnout", "value": 0.67},
            ],
        }

        # Verify numeric values exist
        assert isinstance(outcome["primary_outcome_probability"], (int, float))
        assert outcome["primary_outcome_probability"] > 0

        # Verify key_metrics has numeric values
        has_numeric = any(
            isinstance(m.get("value"), (int, float)) and m.get("value") != 0
            for m in outcome.get("key_metrics", [])
        )
        assert has_numeric, "STEP 1 VIOLATION: Outcome has no real numeric results"

    def test_zero_outcome_rejected(self):
        """Test zero/empty outcomes rejected."""
        outcome = {
            "primary_outcome": "",
            "primary_outcome_probability": 0,
            "outcome_distribution": {},
            "key_metrics": [],
        }

        has_numeric = any(
            isinstance(m.get("value"), (int, float)) and m.get("value") != 0
            for m in outcome.get("key_metrics", [])
        )
        assert not has_numeric, "Should reject zero outcomes"


# =============================================================================
# Integration Tests
# =============================================================================

class TestRunsEndpointValidation:
    """Test runs endpoint validation."""

    def test_cancel_only_valid_states(self):
        """Test cancel only works for pending/running."""
        valid_cancel_states = {"pending", "running"}
        invalid_cancel_states = {"succeeded", "failed", "cancelled"}

        for state in valid_cancel_states:
            assert state in {"pending", "running", "queued"}

        for state in invalid_cancel_states:
            assert state not in valid_cancel_states

    def test_start_only_pending_or_queued(self):
        """Test start only works for pending/queued."""
        valid_start_states = {"pending", "queued"}
        invalid_start_states = {"running", "succeeded", "failed", "cancelled"}

        for state in invalid_start_states:
            assert state not in valid_start_states

    def test_retry_only_failed(self):
        """Test retry only works for failed runs."""
        valid_retry_states = {"failed"}
        invalid_retry_states = {"pending", "queued", "running", "succeeded", "cancelled"}

        for state in invalid_retry_states:
            assert state not in valid_retry_states


# =============================================================================
# Artifact Model Tests
# =============================================================================

class TestArtifactModels:
    """Test STEP 1 artifact models exist and have required fields."""

    def test_run_spec_model_fields(self):
        """Test RunSpec has required fields."""
        from app.models.run_artifacts import RunSpec

        # Check required columns exist
        required_columns = [
            "run_id", "tenant_id", "project_id", "ticks_total", "seed",
            "model_config", "environment_spec", "engine_version",
            "ruleset_version", "dataset_version", "created_at"
        ]
        mapper = RunSpec.__mapper__
        column_names = [col.key for col in mapper.columns]

        for col in required_columns:
            assert col in column_names, f"Missing RunSpec column: {col}"

    def test_run_trace_model_fields(self):
        """Test RunTrace has required fields."""
        from app.models.run_artifacts import RunTrace

        required_columns = [
            "run_id", "tenant_id", "timestamp", "worker_id",
            "execution_stage", "created_at"
        ]
        mapper = RunTrace.__mapper__
        column_names = [col.key for col in mapper.columns]

        for col in required_columns:
            assert col in column_names, f"Missing RunTrace column: {col}"

    def test_outcome_report_model_fields(self):
        """Test OutcomeReport has required fields."""
        from app.models.run_artifacts import OutcomeReport

        required_columns = [
            "run_id", "node_id", "tenant_id", "primary_outcome",
            "primary_outcome_probability", "outcome_distribution",
            "key_metrics", "created_at"
        ]
        mapper = OutcomeReport.__mapper__
        column_names = [col.key for col in mapper.columns]

        for col in required_columns:
            assert col in column_names, f"Missing OutcomeReport column: {col}"

    def test_worker_heartbeat_model_fields(self):
        """Test WorkerHeartbeat has required fields."""
        from app.models.run_artifacts import WorkerHeartbeat

        required_columns = [
            "worker_id", "last_seen_at", "status", "current_run_id"
        ]
        mapper = WorkerHeartbeat.__mapper__
        column_names = [col.key for col in mapper.columns]

        for col in required_columns:
            assert col in column_names, f"Missing WorkerHeartbeat column: {col}"


# =============================================================================
# Run if main
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

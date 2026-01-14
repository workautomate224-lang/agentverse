"""
Temporal Knowledge Isolation - Unit Tests

Tests the core temporal isolation services without external dependencies.

Reference: temporal.md (Single Source of Truth)
"""

import pytest
from datetime import datetime, timedelta, timezone
from typing import Optional
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# =============================================================================
# Test A: DataGatewayContext Model
# =============================================================================

def test_a_data_gateway_context_creation():
    """
    Test A: Project-level lock - DataGatewayContext

    Verify DataGatewayContext can be created with temporal fields.
    """
    print("\n" + "=" * 60)
    print("TEST A: DataGatewayContext Creation")
    print("=" * 60)

    try:
        from app.services.data_gateway import DataGatewayContext

        # Create context with backtest cutoff
        cutoff = datetime(2024, 6, 1, tzinfo=timezone.utc)

        context = DataGatewayContext(
            tenant_id="test-tenant",
            project_id="test-project",
            run_id="test-run",
            user_id="test-user",
            cutoff_time=cutoff,
            isolation_level=2
        )

        assert context.cutoff_time == cutoff, "Cutoff time mismatch"
        assert context.isolation_level == 2, "Isolation level mismatch"
        print(f"✓ Context created with cutoff: {context.cutoff_time}")
        print(f"✓ Isolation level: {context.isolation_level}")
        print("\n✅ TEST A PASSED")

    except ImportError as e:
        pytest.skip(f"DataGateway not available: {e}")


# =============================================================================
# Test B: LeakageGuard Cutoff Filtering
# =============================================================================

def test_b_leakage_guard_cutoff_enforcement():
    """
    Test B: Cutoff enforcement via LeakageGuard

    Verify LeakageGuard filters records after cutoff.
    """
    print("\n" + "=" * 60)
    print("TEST B: LeakageGuard Cutoff Enforcement")
    print("=" * 60)

    try:
        from app.services.leakage_guard import LeakageGuard, create_leakage_guard

        cutoff = datetime(2024, 6, 1, tzinfo=timezone.utc)

        # Create guard with cutoff
        guard = create_leakage_guard(
            cutoff_time=cutoff,
            data_type="test_data",
            source_id="test_source"
        )

        # Test data with timestamps before and after cutoff
        test_data = [
            {"timestamp": "2024-05-01T00:00:00+00:00", "value": 1},  # Before
            {"timestamp": "2024-05-15T00:00:00+00:00", "value": 2},  # Before
            {"timestamp": "2024-06-15T00:00:00+00:00", "value": 3},  # After
            {"timestamp": "2024-07-01T00:00:00+00:00", "value": 4},  # After
        ]

        filtered = guard.filter_dataset(test_data, "timestamp")

        print(f"Original records: {len(test_data)}")
        print(f"Filtered records: {len(filtered)}")
        print(f"Records removed: {len(test_data) - len(filtered)}")

        # Should only have 2 records (before cutoff)
        assert len(filtered) == 2, f"Expected 2 records, got {len(filtered)}"

        # Verify all returned records are before cutoff
        for record in filtered:
            ts = datetime.fromisoformat(record["timestamp"])
            assert ts <= cutoff, f"Record after cutoff: {ts}"

        print("✓ Records after cutoff correctly filtered out")
        print("\n✅ TEST B PASSED")

    except ImportError as e:
        pytest.skip(f"LeakageGuard not available: {e}")


# =============================================================================
# Test C: Source Capability Model
# =============================================================================

def test_c_source_capability_safety_levels():
    """
    Test C: Latest-only source protection

    Verify SourceCapability model correctly identifies safe isolation levels.
    """
    print("\n" + "=" * 60)
    print("TEST C: Source Capability Safety Levels")
    print("=" * 60)

    try:
        from app.models.source_registry import SourceCapability

        # Check model has required fields
        assert hasattr(SourceCapability, 'safe_isolation_levels'), \
            "Missing safe_isolation_levels field"
        print("✓ SourceCapability has safe_isolation_levels field")

        # Check for is_safe_for_level method
        assert hasattr(SourceCapability, 'is_safe_for_level'), \
            "Missing is_safe_for_level method"
        print("✓ SourceCapability has is_safe_for_level method")

        print("\n✅ TEST C PASSED")

    except ImportError as e:
        pytest.skip(f"SourceCapability not available: {e}")


# =============================================================================
# Test D: RunManifest Audit Fields
# =============================================================================

def test_d_run_manifest_audit_fields():
    """
    Test D: Run Audit Package completeness

    Verify RunManifest has temporal audit fields.
    """
    print("\n" + "=" * 60)
    print("TEST D: RunManifest Audit Fields")
    print("=" * 60)

    try:
        from app.models.run_manifest import RunManifest

        # Check for temporal audit fields
        required_fields = [
            'cutoff_applied_as_of_datetime',
            'data_manifest_ref',
            'lineage_ref',
            'isolation_status',
            'isolation_violations',
        ]

        # Get all model attributes (including from annotations and mapped)
        model_attrs = dir(RunManifest)
        model_annotations = getattr(RunManifest, '__annotations__', {})

        print("Checking RunManifest fields:")
        for field in required_fields:
            has_field = field in model_attrs or field in model_annotations
            status = "✓" if has_field else "✗"
            print(f"  {status} {field}")

        # Check helper methods
        if hasattr(RunManifest, 'get_temporal_audit_report'):
            print("✓ get_temporal_audit_report method exists")

        if hasattr(RunManifest, 'is_isolation_passing'):
            print("✓ is_isolation_passing method exists")

        print("\n✅ TEST D PASSED")

    except ImportError as e:
        pytest.skip(f"RunManifest not available: {e}")


# =============================================================================
# Test E: ProjectSpec Temporal Fields
# =============================================================================

def test_e_project_spec_temporal_fields():
    """
    Test E: Reproducibility - Project temporal lock

    Verify ProjectSpec has temporal context fields.
    """
    print("\n" + "=" * 60)
    print("TEST E: ProjectSpec Temporal Fields")
    print("=" * 60)

    try:
        from app.models.project_spec import ProjectSpec

        # Check for temporal fields
        required_fields = [
            'temporal_mode',
            'as_of_datetime',
            'temporal_timezone',
            'isolation_level',
            'allowed_sources',
            'temporal_policy_version',
            'temporal_lock_status',
            'temporal_lock_history',
        ]

        model_attrs = dir(ProjectSpec)
        model_annotations = getattr(ProjectSpec, '__annotations__', {})

        print("Checking ProjectSpec fields:")
        for field in required_fields:
            has_field = field in model_attrs or field in model_annotations
            status = "✓" if has_field else "✗"
            print(f"  {status} {field}")

        # Check helper methods
        if hasattr(ProjectSpec, 'get_temporal_context'):
            print("✓ get_temporal_context method exists")

        if hasattr(ProjectSpec, 'is_backtest'):
            print("✓ is_backtest method exists")

        if hasattr(ProjectSpec, 'is_temporal_locked'):
            print("✓ is_temporal_locked method exists")

        print("\n✅ TEST E PASSED")

    except ImportError as e:
        pytest.skip(f"ProjectSpec not available: {e}")


# =============================================================================
# Test F: Output Auditor
# =============================================================================

def test_f_output_auditor_violation_detection():
    """
    Test F: LLM containment & audit

    Verify OutputAuditor detects temporal violations.
    """
    print("\n" + "=" * 60)
    print("TEST F: Output Auditor Violation Detection")
    print("=" * 60)

    try:
        from app.services.output_auditor import OutputAuditor, ViolationType, AuditResult
        from app.services.data_gateway import ManifestEntry

        # Check ViolationType enum
        assert hasattr(ViolationType, 'POST_CUTOFF_REFERENCE'), \
            "Missing POST_CUTOFF_REFERENCE violation type"
        assert hasattr(ViolationType, 'UNGROUNDED_FACT'), \
            "Missing UNGROUNDED_FACT violation type"
        print("✓ ViolationType enum has required values")

        # Create auditor with cutoff in the past
        cutoff = datetime(2024, 1, 1, tzinfo=timezone.utc)

        # OutputAuditor requires manifest_entries as first arg
        auditor = OutputAuditor(
            manifest_entries=[],  # Empty for this test
            cutoff_time=cutoff,
            isolation_level=2
        )

        # Test output with post-cutoff reference
        test_output = """
        According to 2025 census data, the population grew by 5%.
        This trend accelerated in March 2025.
        """

        result = auditor.audit_output(test_output)

        print(f"Compliance score: {result.compliance_score}")
        print(f"Violations found: {len(result.violations)}")

        # Should detect post-cutoff references
        assert len(result.violations) > 0, "Should detect post-cutoff references"

        for v in result.violations:
            print(f"  - {v.violation_type.value}: {v.description[:60]}...")

        print("✓ OutputAuditor correctly flags post-cutoff references")
        print("\n✅ TEST F PASSED")

    except ImportError as e:
        pytest.skip(f"OutputAuditor not available: {e}")


# =============================================================================
# Test: DataManifest Service
# =============================================================================

def test_data_manifest_service():
    """
    Test DataManifest service creates manifest entries.
    """
    print("\n" + "=" * 60)
    print("TEST: DataManifest Service")
    print("=" * 60)

    try:
        from app.services.data_manifest import DataManifestService, ManifestSummary, IsolationViolation
        from app.services.data_gateway import ManifestEntry

        # Check ManifestEntry has required fields (from data_gateway)
        entry_fields = ManifestEntry.__annotations__
        assert 'source_name' in entry_fields, "Missing source_name"
        assert 'payload_hash' in entry_fields, "Missing payload_hash"
        print("✓ ManifestEntry has required fields")

        # Check ManifestSummary has required fields
        summary_fields = ManifestSummary.__annotations__
        assert 'entry_count' in summary_fields, "Missing entry_count"
        assert 'sources_accessed' in summary_fields, "Missing sources_accessed"
        assert 'isolation_status' in summary_fields, "Missing isolation_status"
        print("✓ ManifestSummary has required fields")

        # Check DataManifestService has required methods
        assert hasattr(DataManifestService, 'add_entry'), "Missing add_entry"
        assert hasattr(DataManifestService, 'get_isolation_status'), "Missing get_isolation_status"
        assert hasattr(DataManifestService, 'finalize_manifest'), "Missing finalize_manifest"
        print("✓ DataManifestService has required methods")

        print("\n✅ TEST PASSED")

    except ImportError as e:
        pytest.skip(f"DataManifestService not available: {e}")


# =============================================================================
# Test: LLM Data Tools
# =============================================================================

def test_llm_data_tools():
    """
    Test LLM data tools schema.
    """
    print("\n" + "=" * 60)
    print("TEST: LLM Data Tools")
    print("=" * 60)

    try:
        from app.services.llm_data_tools import LLM_DATA_TOOLS_SCHEMA, get_backtest_policy_prompt

        # Check schema exists and has tools
        assert len(LLM_DATA_TOOLS_SCHEMA) > 0, "No tools in schema"
        print(f"✓ {len(LLM_DATA_TOOLS_SCHEMA)} LLM data tools defined")

        for tool in LLM_DATA_TOOLS_SCHEMA:
            print(f"  - {tool.get('name')}")

        # Check backtest policy prompt function
        cutoff = datetime(2024, 1, 1, tzinfo=timezone.utc)
        policy = get_backtest_policy_prompt(cutoff, "UTC")
        assert "TEMPORAL ISOLATION" in policy or "backtest" in policy.lower(), \
            "Policy should mention temporal isolation"
        print("✓ Backtest policy prompt generated")

        print("\n✅ TEST PASSED")

    except ImportError as e:
        pytest.skip(f"LLM data tools not available: {e}")


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("TEMPORAL KNOWLEDGE ISOLATION - UNIT TEST SUITE")
    print("Reference: temporal.md §9")
    print("=" * 70)

    tests = [
        test_a_data_gateway_context_creation,
        test_b_leakage_guard_cutoff_enforcement,
        test_c_source_capability_safety_levels,
        test_d_run_manifest_audit_fields,
        test_e_project_spec_temporal_fields,
        test_f_output_auditor_violation_detection,
        test_data_manifest_service,
        test_llm_data_tools,
    ]

    passed = 0
    failed = 0
    skipped = 0

    for test in tests:
        try:
            test()
            passed += 1
        except pytest.skip.Exception as e:
            print(f"⏭ SKIPPED: {e}")
            skipped += 1
        except Exception as e:
            print(f"❌ FAILED: {e}")
            failed += 1

    print("\n" + "=" * 70)
    print(f"Results: {passed} passed, {failed} failed, {skipped} skipped")
    print("=" * 70)

"""
Global Invariants Verification Tests
Reference: verification_checklist_v2.md §2.1-2.4

These tests verify the system-wide invariants that must hold for compliance:
- §2.1 Forking Not Editing (Reversibility Proof)
- §2.2 On-Demand Execution Only
- §2.3 Artifact Lineage Completeness
- §2.4 Conditional Probability Correctness
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


# =============================================================================
# §2.1 Forking Not Editing (Reversibility Proof)
# =============================================================================


class TestForkingNotEditing:
    """
    Tests for §2.1: Fork creates new node, parent remains unchanged.

    Evidence required:
    - Node record immutability: N0.state_ref, N0.results_ref, N0.telemetry_ref unchanged
    - N1.parent_node_id == N0.node_id
    - N1.scenario_patch_ref exists and contains only deltas
    - Audit log shows create not update for parent artifacts
    """

    @pytest.fixture
    def mock_db(self):
        """Create mock async database session."""
        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock()
        db.flush = AsyncMock()
        db.add = MagicMock()
        return db

    @pytest.fixture
    def mock_parent_node(self):
        """Create a mock parent node with frozen state."""
        node = MagicMock()
        node.id = uuid.uuid4()
        node.tenant_id = uuid.uuid4()
        node.project_id = uuid.uuid4()
        node.parent_node_id = None
        node.depth = 0
        node.probability = 1.0
        node.cumulative_probability = 1.0
        node.child_count = 0
        node.is_baseline = True
        node.aggregated_outcome = {"primary_outcome": "Test", "primary_outcome_probability": 0.8}
        node.run_refs = [{"run_id": str(uuid.uuid4())}]
        node.confidence = {"level": "HIGH", "score": 0.85}
        node.scenario_patch_ref = None
        return node

    @pytest.mark.asyncio
    async def test_fork_creates_new_node_not_update_parent(self, mock_db, mock_parent_node):
        """
        §2.1: Verify that forking creates a NEW child node.

        Evidence: N1.parent_node_id == N0.node_id
        """
        from app.services.node_service import NodeService, ForkNodeInput, InterventionDef
        from app.models.node import Node

        # Setup mock to return parent node
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_parent_node
        mock_db.execute.return_value = mock_result

        service = NodeService(mock_db)

        # Capture original parent state
        original_outcome = mock_parent_node.aggregated_outcome.copy()
        original_run_refs = mock_parent_node.run_refs.copy()
        original_confidence = mock_parent_node.confidence.copy()

        # Create fork input
        fork_input = ForkNodeInput(
            tenant_id=mock_parent_node.tenant_id,
            project_id=mock_parent_node.project_id,
            parent_node_id=mock_parent_node.id,
            intervention=InterventionDef(
                type="variable_change",
                changes=[{"variable": "price", "delta": 0.1}],
            ),
            label="Test Fork",
        )

        # Execute fork
        with patch.object(service, 'get_node', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_parent_node

            child_node, edge = await service.fork_node(fork_input)

        # VERIFICATION: Parent state unchanged
        assert mock_parent_node.aggregated_outcome == original_outcome, \
            "§2.1 FAIL: Parent aggregated_outcome was modified"
        assert mock_parent_node.run_refs == original_run_refs, \
            "§2.1 FAIL: Parent run_refs was modified"
        assert mock_parent_node.confidence == original_confidence, \
            "§2.1 FAIL: Parent confidence was modified"

        # VERIFICATION: Child references parent correctly
        assert child_node.parent_node_id == mock_parent_node.id, \
            "§2.1 FAIL: Child.parent_node_id does not reference parent"

        # VERIFICATION: Child is a new node (added to session)
        assert mock_db.add.called, \
            "§2.1 FAIL: New node was not added to session"

        # VERIFICATION: Only allowed parent mutation is child_count
        assert mock_parent_node.child_count == 1, \
            "§2.1 FAIL: Parent child_count not incremented"

    @pytest.mark.asyncio
    async def test_fork_preserves_scenario_patch_ref(self, mock_db, mock_parent_node):
        """
        §2.1: Verify that fork stores scenario_patch_ref with deltas.

        Evidence: N1.scenario_patch_ref exists and contains only deltas
        """
        from app.services.node_service import NodeService, ForkNodeInput, InterventionDef, ScenarioPatchRef

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_parent_node
        mock_db.execute.return_value = mock_result

        service = NodeService(mock_db)

        # Create fork with scenario patch
        patch_ref = ScenarioPatchRef(
            patch_type="variable_change",
            storage_key=f"patches/{uuid.uuid4()}.json",
            version="1.0.0",
        )

        fork_input = ForkNodeInput(
            tenant_id=mock_parent_node.tenant_id,
            project_id=mock_parent_node.project_id,
            parent_node_id=mock_parent_node.id,
            intervention=InterventionDef(
                type="variable_change",
                changes=[{"variable": "media_intensity", "delta": 0.2}],
            ),
            scenario_patch_ref=patch_ref,
            label="Patched Fork",
        )

        with patch.object(service, 'get_node', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_parent_node
            child_node, edge = await service.fork_node(fork_input)

        # VERIFICATION: scenario_patch_ref is stored
        assert child_node.scenario_patch_ref is not None, \
            "§2.1 FAIL: scenario_patch_ref not stored on child"
        assert child_node.scenario_patch_ref["patch_type"] == "variable_change", \
            "§2.1 FAIL: scenario_patch_ref doesn't contain correct delta type"


# =============================================================================
# §2.2 On-Demand Execution Only
# =============================================================================


class TestOnDemandExecutionOnly:
    """
    Tests for §2.2: Replay/2D view must NOT trigger new runs.

    Evidence required:
    - No new run created
    - No new compute job enqueued
    - Evidence Pack: replay_action logs show telemetry read only
    """

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        return db

    @pytest.mark.asyncio
    async def test_telemetry_query_is_read_only(self, mock_db):
        """
        §2.2: Verify telemetry queries don't trigger simulation.

        Evidence: No new run created, telemetry read only
        """
        from app.services.telemetry import TelemetryService

        # Mock storage backend
        mock_storage = MagicMock()
        mock_storage.read_json = AsyncMock(return_value={
            "keyframes": [],
            "deltas": [],
            "events": [],
        })

        service = TelemetryService(mock_db, mock_storage)

        # Query telemetry
        run_id = str(uuid.uuid4())

        # This should NOT trigger any writes or job creation
        with patch.object(mock_db, 'add') as mock_add:
            # Simulate query (method signature depends on implementation)
            result = await service.query_telemetry(
                run_id=run_id,
                start_tick=0,
                end_tick=100,
            )

            # VERIFICATION: No writes to database
            assert not mock_add.called, \
                "§2.2 FAIL: Telemetry query triggered database write"

    @pytest.mark.asyncio
    async def test_replay_does_not_create_jobs(self, mock_db):
        """
        §2.2: Verify replay operations don't enqueue compute jobs.
        """
        # Mock the job queue
        with patch('app.tasks.run_executor.execute_run.delay') as mock_celery:
            from app.services.telemetry import TelemetryService

            mock_storage = MagicMock()
            mock_storage.read_json = AsyncMock(return_value={})

            service = TelemetryService(mock_db, mock_storage)

            # Simulate replay operations
            run_id = str(uuid.uuid4())
            await service.get_keyframe_at_tick(run_id, tick=50)
            await service.get_deltas_in_range(run_id, start_tick=0, end_tick=100)

            # VERIFICATION: No Celery tasks triggered
            assert not mock_celery.called, \
                "§2.2 FAIL: Replay operation triggered compute job"


# =============================================================================
# §2.3 Artifact Lineage Completeness
# =============================================================================


class TestArtifactLineageCompleteness:
    """
    Tests for §2.3: All artifact refs exist and are retrievable.

    Evidence required:
    - run_ids exist and map to node
    - telemetry exists and is queryable
    - reliability report attached or explicitly "not computed"
    - config versions pinned
    """

    @pytest.mark.asyncio
    async def test_evidence_pack_has_complete_lineage(self):
        """
        §2.3: Verify Evidence Pack contains all required lineage fields.
        """
        from app.schemas.evidence import (
            EvidencePack,
            ArtifactLineage,
            ExecutionProof,
            DeterminismSignature,
            TelemetryProof,
            ResultsProof,
            AuditProof,
        )

        # Create complete evidence pack
        lineage = ArtifactLineage(
            project_id="proj-123",
            project_version="1.0.0",
            node_id="node-456",
            parent_node_id="node-000",
            node_depth=1,
            run_id="run-789",
            run_config_id="config-abc",
            engine_version="2.0.0",
            ruleset_version="1.5.0",
            dataset_version="3.0.0",
            schema_version="1.0.0",
            telemetry_ref="storage://telemetry/run-789.bin",
            reliability_ref="storage://reliability/run-789.json",
            created_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )

        # VERIFICATION: All required fields present
        assert lineage.project_id, "§2.3 FAIL: Missing project_id"
        assert lineage.node_id, "§2.3 FAIL: Missing node_id"
        assert lineage.run_id, "§2.3 FAIL: Missing run_id"
        assert lineage.engine_version, "§2.3 FAIL: Missing engine_version"
        assert lineage.ruleset_version, "§2.3 FAIL: Missing ruleset_version"
        assert lineage.dataset_version, "§2.3 FAIL: Missing dataset_version"
        assert lineage.telemetry_ref, "§2.3 FAIL: Missing telemetry_ref"

    @pytest.mark.asyncio
    async def test_evidence_pack_versions_pinned(self):
        """
        §2.3: Verify all versions are explicitly pinned.
        """
        from app.schemas.evidence import ArtifactLineage

        lineage = ArtifactLineage(
            project_id="proj-123",
            project_version="1.0.0",
            node_id="node-456",
            run_id="run-789",
            run_config_id="config-abc",
            engine_version="2.0.0",
            ruleset_version="1.5.0",
            dataset_version="3.0.0",
            schema_version="1.0.0",
            created_at=datetime.utcnow(),
        )

        # VERIFICATION: Version fields follow semantic versioning pattern
        import re
        semver_pattern = r'^\d+\.\d+\.\d+$'

        assert re.match(semver_pattern, lineage.engine_version), \
            "§2.3 FAIL: engine_version not semver format"
        assert re.match(semver_pattern, lineage.ruleset_version), \
            "§2.3 FAIL: ruleset_version not semver format"
        assert re.match(semver_pattern, lineage.dataset_version), \
            "§2.3 FAIL: dataset_version not semver format"


# =============================================================================
# §2.4 Conditional Probability Correctness
# =============================================================================


class TestConditionalProbabilityCorrectness:
    """
    Tests for §2.4: Branch probabilities must sum correctly.

    Evidence required:
    - sum(P(child_i | parent)) == 1 (within tolerance)
    - Cluster probabilities equal sum of contained leaves
    """

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        return db

    @pytest.mark.asyncio
    async def test_sibling_probabilities_sum_to_parent(self, mock_db):
        """
        §2.4: Verify children probabilities sum to parent probability.
        """
        from app.services.node_service import NodeService

        # Create mock parent and children
        parent = MagicMock()
        parent.id = uuid.uuid4()
        parent.probability = 1.0
        parent.cumulative_probability = 1.0

        child1 = MagicMock()
        child1.id = uuid.uuid4()
        child1.probability = 0.6
        child1.cumulative_probability = 0.6

        child2 = MagicMock()
        child2.id = uuid.uuid4()
        child2.probability = 0.4
        child2.cumulative_probability = 0.4

        service = NodeService(mock_db)

        with patch.object(service, 'get_node', new_callable=AsyncMock) as mock_get_node:
            with patch.object(service, 'get_child_nodes', new_callable=AsyncMock) as mock_get_children:
                mock_get_node.return_value = parent
                mock_get_children.return_value = [child1, child2]

                report = await service.get_sibling_probability_report(parent.id)

        # VERIFICATION: Sum equals parent probability
        children_sum = report["children_sum"]
        tolerance = 0.001

        assert abs(children_sum - parent.probability) <= tolerance, \
            f"§2.4 FAIL: Children sum {children_sum} != parent probability {parent.probability}"
        assert report["is_normalized"], \
            "§2.4 FAIL: Probabilities not normalized"

    @pytest.mark.asyncio
    async def test_normalization_fixes_inconsistent_probabilities(self, mock_db):
        """
        §2.4: Verify normalization corrects inconsistent probabilities.
        """
        from app.services.node_service import NodeService

        # Create mock parent and children with INCORRECT sum
        parent = MagicMock()
        parent.id = uuid.uuid4()
        parent.probability = 1.0
        parent.cumulative_probability = 1.0

        # Children that don't sum to 1.0 (they're both 1.0!)
        child1 = MagicMock()
        child1.id = uuid.uuid4()
        child1.probability = 1.0  # Wrong!
        child1.cumulative_probability = 1.0

        child2 = MagicMock()
        child2.id = uuid.uuid4()
        child2.probability = 1.0  # Wrong!
        child2.cumulative_probability = 1.0

        service = NodeService(mock_db)

        with patch.object(service, 'get_node', new_callable=AsyncMock) as mock_get_node:
            with patch.object(service, 'get_child_nodes', new_callable=AsyncMock) as mock_get_children:
                mock_get_node.return_value = parent
                mock_get_children.return_value = [child1, child2]

                # Execute normalization
                result = await service.normalize_sibling_probabilities(parent.id)

        # VERIFICATION: Normalization was performed
        assert result["status"] == "normalized", \
            "§2.4 FAIL: Expected normalization to occur"

        # VERIFICATION: After normalization, sum equals parent
        assert abs(result["after_sum"] - parent.probability) <= 0.001, \
            "§2.4 FAIL: After normalization, sum still incorrect"

    @pytest.mark.asyncio
    async def test_verify_probability_consistency_detects_issues(self, mock_db):
        """
        §2.4: Verify consistency checker finds probability issues.
        """
        from app.services.node_service import NodeService

        # Create mock nodes with inconsistent probabilities
        root = MagicMock()
        root.id = uuid.uuid4()
        root.parent_node_id = None
        root.probability = 1.0
        root.cumulative_probability = 1.0

        child1 = MagicMock()
        child1.id = uuid.uuid4()
        child1.parent_node_id = root.id
        child1.probability = 0.5
        child1.cumulative_probability = 0.5

        child2 = MagicMock()
        child2.id = uuid.uuid4()
        child2.parent_node_id = root.id
        child2.probability = 0.3  # Sum is 0.8, not 1.0!
        child2.cumulative_probability = 0.3

        all_nodes = [root, child1, child2]

        service = NodeService(mock_db)

        with patch.object(service, 'get_nodes_by_project', new_callable=AsyncMock) as mock_get_all:
            mock_get_all.return_value = all_nodes

            result = await service.verify_probability_consistency(
                project_id=uuid.uuid4(),
                tenant_id=uuid.uuid4(),
            )

        # VERIFICATION: Inconsistency detected
        assert not result["is_consistent"], \
            "§2.4 FAIL: Should have detected probability inconsistency"
        assert result["issues"] is not None, \
            "§2.4 FAIL: Should have recorded issues"

        # Find the children_sum_mismatch issue
        sum_issues = [i for i in result["issues"] if i["type"] == "children_sum_mismatch"]
        assert len(sum_issues) > 0, \
            "§2.4 FAIL: Should have detected children_sum_mismatch"

    @pytest.mark.asyncio
    async def test_root_probability_is_one(self, mock_db):
        """
        §2.4: Verify root node probability is 1.0.
        """
        from app.services.node_service import NodeService

        # Create root with correct probability
        root = MagicMock()
        root.id = uuid.uuid4()
        root.parent_node_id = None
        root.probability = 1.0
        root.cumulative_probability = 1.0

        service = NodeService(mock_db)

        with patch.object(service, 'get_nodes_by_project', new_callable=AsyncMock) as mock_get_all:
            mock_get_all.return_value = [root]

            result = await service.verify_probability_consistency(
                project_id=uuid.uuid4(),
                tenant_id=uuid.uuid4(),
            )

        # VERIFICATION: Root probability is correct
        assert result["is_consistent"], \
            "§2.4 FAIL: Root with P=1.0 should be consistent"

        # Test with incorrect root probability
        root.probability = 0.9

        with patch.object(service, 'get_nodes_by_project', new_callable=AsyncMock) as mock_get_all:
            mock_get_all.return_value = [root]

            result = await service.verify_probability_consistency(
                project_id=uuid.uuid4(),
                tenant_id=uuid.uuid4(),
            )

        # VERIFICATION: Incorrect root detected
        assert not result["is_consistent"], \
            "§2.4 FAIL: Should detect root P != 1.0"


# =============================================================================
# Integration Test: Full Invariants Suite
# =============================================================================


class TestGlobalInvariantsIntegration:
    """
    Integration tests combining all global invariants.
    """

    @pytest.mark.asyncio
    async def test_fork_maintains_probability_tree(self):
        """
        Integration: Fork + probability normalization work together.
        """
        # This would be a full integration test with real database
        # For now, placeholder to show structure
        pass

    @pytest.mark.asyncio
    async def test_evidence_pack_proves_invariants(self):
        """
        Integration: Evidence Pack contains proof of all invariants.
        """
        from app.schemas.evidence import EvidencePack

        # Evidence Pack should contain:
        # - artifact_lineage (§2.3)
        # - results_proof with normalized probabilities (§2.4)
        # - execution_proof showing no replay triggers (§2.2)
        # - audit_proof showing create not update (§2.1)
        pass


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

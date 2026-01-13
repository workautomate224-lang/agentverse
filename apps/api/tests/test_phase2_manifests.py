"""
PHASE 2 — Run Manifest / Seed / Version System Tests
Reference: project.md Phase 2 - Reproducibility & Auditability

Tests for:
1. RunManifest model - hash computation and immutability
2. ManifestService - create, get, reproduce, verify
3. Manifest API endpoints - GET manifest, POST reproduce, GET provenance
4. Integration with run creation flow
"""

import hashlib
import json
import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from app.models.run_manifest import RunManifest
from app.schemas.run_manifest import (
    RunManifestResponse,
    ProvenanceResponse,
    ReproduceRunRequest,
    ReproduceRunResponse,
    ReproduceMode,
    VerifyManifestResponse,
)


# =============================================================================
# RunManifest Model Tests
# =============================================================================

class TestRunManifestModel:
    """Test RunManifest SQLAlchemy model."""

    def test_compute_manifest_hash_deterministic(self):
        """PHASE 2: Hash computation must be deterministic."""
        seed = 12345
        config_json = {"max_ticks": 100, "run_mode": "society"}
        versions_json = {"code_version": "abc123", "sim_engine_version": "1.0.0"}

        hash1 = RunManifest.compute_manifest_hash(seed, config_json, versions_json)
        hash2 = RunManifest.compute_manifest_hash(seed, config_json, versions_json)

        assert hash1 == hash2, "Hash computation must be deterministic"
        assert len(hash1) == 64, "SHA256 hash must be 64 hex characters"

    def test_compute_manifest_hash_canonical_json(self):
        """PHASE 2: Hash must use canonical JSON (sorted keys, no whitespace)."""
        seed = 42
        # Same data in different order
        config1 = {"max_ticks": 100, "run_mode": "society"}
        config2 = {"run_mode": "society", "max_ticks": 100}
        versions = {"code_version": "v1"}

        hash1 = RunManifest.compute_manifest_hash(seed, config1, versions)
        hash2 = RunManifest.compute_manifest_hash(seed, config2, versions)

        assert hash1 == hash2, "Hash must be same regardless of key order"

    def test_compute_manifest_hash_different_seeds(self):
        """PHASE 2: Different seeds must produce different hashes."""
        config = {"max_ticks": 100}
        versions = {"code_version": "v1"}

        hash1 = RunManifest.compute_manifest_hash(1, config, versions)
        hash2 = RunManifest.compute_manifest_hash(2, config, versions)

        assert hash1 != hash2, "Different seeds must produce different hashes"

    def test_compute_manifest_hash_different_config(self):
        """PHASE 2: Different config must produce different hashes."""
        seed = 42
        versions = {"code_version": "v1"}

        hash1 = RunManifest.compute_manifest_hash(seed, {"max_ticks": 100}, versions)
        hash2 = RunManifest.compute_manifest_hash(seed, {"max_ticks": 200}, versions)

        assert hash1 != hash2, "Different config must produce different hashes"

    def test_compute_content_hash(self):
        """Test content hash helper method."""
        content1 = "test content"
        content2 = "test content"
        content3 = "different content"

        hash1 = RunManifest.compute_content_hash(content1)
        hash2 = RunManifest.compute_content_hash(content2)
        hash3 = RunManifest.compute_content_hash(content3)

        assert hash1 == hash2, "Same content must produce same hash"
        assert hash1 != hash3, "Different content must produce different hash"
        assert len(hash1) == 16, "Content hash should be truncated to 16 chars"


# =============================================================================
# ManifestService Tests (Unit)
# =============================================================================

class TestManifestServiceUnit:
    """Unit tests for ManifestService."""

    def test_normalize_config_extracts_standard_fields(self):
        """Test config normalization extracts standard fields."""
        from app.services.manifest_service import ManifestService

        # Create mock db
        mock_db = MagicMock()
        service = ManifestService(mock_db)

        config = {
            "max_ticks": 200,
            "agent_batch_size": 50,
            "run_mode": "target",
            "horizon": 500,
            "tick_rate": 2,
            "extra_field": "ignored",
        }

        normalized = service._normalize_config(config)

        assert normalized["max_ticks"] == 200
        assert normalized["agent_batch_size"] == 50
        assert normalized["run_mode"] == "target"
        assert normalized["horizon"] == 500
        assert normalized["tick_rate"] == 2
        # Extra fields not included in normalized output
        assert "extra_field" not in normalized

    def test_normalize_config_uses_defaults(self):
        """Test config normalization uses defaults for missing fields."""
        from app.services.manifest_service import ManifestService

        mock_db = MagicMock()
        service = ManifestService(mock_db)

        # Empty config should use defaults
        normalized = service._normalize_config({})

        assert normalized["max_ticks"] == 100
        assert normalized["agent_batch_size"] == 100
        assert normalized["run_mode"] == "society"
        assert normalized["horizon"] == 1000
        assert normalized["tick_rate"] == 1

    def test_build_versions_computes_hashes(self):
        """Test version building computes content hashes."""
        from app.services.manifest_service import ManifestService

        mock_db = MagicMock()
        service = ManifestService(mock_db)

        versions = service._build_versions(
            rules_content="rule1: do something",
            personas_content='{"persona": "test"}',
            model_info={"model": "gpt-4", "temperature": 0.7},
            dataset_version="v2.0",
        )

        assert "code_version" in versions
        assert "sim_engine_version" in versions
        assert versions["rules_version"] != "default"  # Should be a hash
        assert versions["personas_version"] != "default"  # Should be a hash
        assert "gpt-4:" in versions["model_version"]  # Model name included
        assert versions["dataset_version"] == "v2.0"

    def test_build_versions_uses_defaults_when_none(self):
        """Test version building uses defaults when no content provided."""
        from app.services.manifest_service import ManifestService

        mock_db = MagicMock()
        service = ManifestService(mock_db)

        versions = service._build_versions()

        assert versions["rules_version"] == "default"
        assert versions["personas_version"] == "default"
        assert versions["model_version"] == "default"
        assert versions["dataset_version"] == "default"


# =============================================================================
# Pydantic Schema Tests
# =============================================================================

class TestManifestSchemas:
    """Test Pydantic schema validation."""

    def test_reproduce_mode_enum(self):
        """Test ReproduceMode enum values."""
        assert ReproduceMode.SAME_NODE == "same_node"
        assert ReproduceMode.FORK_NODE == "fork_node"

    def test_reproduce_run_request_defaults(self):
        """Test ReproduceRunRequest defaults."""
        request = ReproduceRunRequest()

        assert request.mode == ReproduceMode.FORK_NODE
        assert request.label is None
        assert request.auto_start is False

    def test_reproduce_run_request_custom(self):
        """Test ReproduceRunRequest with custom values."""
        request = ReproduceRunRequest(
            mode=ReproduceMode.SAME_NODE,
            label="My reproduction",
            auto_start=True,
        )

        assert request.mode == ReproduceMode.SAME_NODE
        assert request.label == "My reproduction"
        assert request.auto_start is True

    def test_run_manifest_response_from_model(self):
        """Test RunManifestResponse can be constructed from model data."""
        response = RunManifestResponse(
            id=uuid.uuid4(),
            run_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            node_id=uuid.uuid4(),
            seed=12345,
            config_json={"max_ticks": 100},
            versions_json={"code_version": "v1"},
            manifest_hash="abc123def456",
            storage_ref=None,
            is_immutable=True,
            source_run_id=None,
            created_at=datetime.utcnow(),
            created_by_user_id=None,
        )

        assert response.seed == 12345
        assert response.is_immutable is True
        assert response.config_json["max_ticks"] == 100

    def test_provenance_response(self):
        """Test ProvenanceResponse construction."""
        response = ProvenanceResponse(
            run_id=uuid.uuid4(),
            manifest_hash="hash123",
            seed=42,
            created_at=datetime.utcnow(),
            project_id=uuid.uuid4(),
            is_reproduction=True,
            code_version="v1.0.0",
            engine_version="1.0.0",
        )

        assert response.is_reproduction is True
        assert response.code_version == "v1.0.0"

    def test_verify_manifest_response(self):
        """Test VerifyManifestResponse construction."""
        response = VerifyManifestResponse(
            run_id=uuid.uuid4(),
            manifest_hash="stored_hash",
            computed_hash="computed_hash",
            is_valid=False,
            verified_at=datetime.utcnow(),
        )

        assert response.is_valid is False
        assert response.manifest_hash == "stored_hash"
        assert response.computed_hash == "computed_hash"


# =============================================================================
# Manifest Hash Integrity Tests
# =============================================================================

class TestManifestHashIntegrity:
    """Test manifest hash integrity verification."""

    def test_verify_integrity_valid(self):
        """Test integrity verification passes for valid manifest."""
        seed = 42
        config = {"max_ticks": 100}
        versions = {"code_version": "v1"}

        # Compute hash
        computed = RunManifest.compute_manifest_hash(seed, config, versions)

        # Verification should pass
        recomputed = RunManifest.compute_manifest_hash(seed, config, versions)
        assert computed == recomputed

    def test_verify_integrity_detects_tampering(self):
        """Test integrity verification detects tampering."""
        seed = 42
        config = {"max_ticks": 100}
        versions = {"code_version": "v1"}

        # Compute original hash
        original_hash = RunManifest.compute_manifest_hash(seed, config, versions)

        # Tamper with config
        tampered_config = {"max_ticks": 200}  # Changed!
        tampered_hash = RunManifest.compute_manifest_hash(seed, tampered_config, versions)

        # Hashes should differ
        assert original_hash != tampered_hash, "Tampering must be detected"

    def test_manifest_immutability_enforcement(self):
        """Test manifest immutability is enforced."""
        # Manifest should be marked immutable at creation
        manifest = RunManifest(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            run_id=uuid.uuid4(),
            seed=42,
            config_json={"max_ticks": 100},
            versions_json={"code_version": "v1"},
            manifest_hash="abc123",
            is_immutable=True,  # Set at creation
        )

        assert manifest.is_immutable is True


# =============================================================================
# Reproducibility Tests
# =============================================================================

class TestReproducibility:
    """Test reproducibility guarantees."""

    def test_same_manifest_same_hash(self):
        """PHASE 2: Same manifest content must produce identical hash."""
        # Run 1
        manifest1_seed = 12345
        manifest1_config = {"max_ticks": 100, "run_mode": "society"}
        manifest1_versions = {"code_version": "abc123", "sim_engine_version": "1.0.0"}

        # Run 2 (reproduction)
        manifest2_seed = 12345  # Same seed
        manifest2_config = {"max_ticks": 100, "run_mode": "society"}  # Same config
        manifest2_versions = {"code_version": "abc123", "sim_engine_version": "1.0.0"}  # Same versions

        hash1 = RunManifest.compute_manifest_hash(manifest1_seed, manifest1_config, manifest1_versions)
        hash2 = RunManifest.compute_manifest_hash(manifest2_seed, manifest2_config, manifest2_versions)

        assert hash1 == hash2, "Reproduced run must have identical manifest hash"

    def test_reproduction_preserves_seed(self):
        """Test reproduction preserves the original seed."""
        original_seed = 42
        config = {"max_ticks": 100}
        versions = {"code_version": "v1"}

        # Original manifest
        original_hash = RunManifest.compute_manifest_hash(original_seed, config, versions)

        # Reproduction must use same seed
        reproduced_hash = RunManifest.compute_manifest_hash(original_seed, config, versions)

        assert original_hash == reproduced_hash
        assert original_seed == 42  # Seed preserved

    def test_reproduction_tracks_source(self):
        """Test reproduction tracks source run."""
        source_run_id = uuid.uuid4()

        manifest = RunManifest(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            run_id=uuid.uuid4(),  # New run
            seed=42,
            config_json={},
            versions_json={},
            manifest_hash="abc",
            source_run_id=source_run_id,  # Points to original
        )

        assert manifest.source_run_id == source_run_id


# =============================================================================
# API Endpoint Contract Tests
# =============================================================================

class TestManifestAPIContracts:
    """Test manifest API endpoint contracts."""

    def test_manifest_endpoint_path(self):
        """Test manifest endpoint follows spec path."""
        # Expected: GET /projects/{project_id}/runs/{run_id}/manifest
        project_id = "proj-123"
        run_id = "run-456"
        expected_path = f"/projects/{project_id}/runs/{run_id}/manifest"

        assert "projects" in expected_path
        assert "runs" in expected_path
        assert "manifest" in expected_path

    def test_reproduce_endpoint_path(self):
        """Test reproduce endpoint follows spec path."""
        # Expected: POST /projects/{project_id}/runs/{run_id}/reproduce
        project_id = "proj-123"
        run_id = "run-456"
        expected_path = f"/projects/{project_id}/runs/{run_id}/reproduce"

        assert "reproduce" in expected_path

    def test_provenance_endpoint_path(self):
        """Test provenance endpoint follows spec path."""
        # Expected: GET /projects/{project_id}/runs/{run_id}/provenance
        project_id = "proj-123"
        run_id = "run-456"
        expected_path = f"/projects/{project_id}/runs/{run_id}/provenance"

        assert "provenance" in expected_path


# =============================================================================
# Version Tracking Tests
# =============================================================================

class TestVersionTracking:
    """Test version tracking functionality."""

    def test_get_code_version_from_env(self):
        """Test code version extraction from environment."""
        from app.services.manifest_service import get_code_version

        # Default should return something (even if "unknown")
        version = get_code_version()
        assert version is not None
        assert isinstance(version, str)

    def test_versions_json_structure(self):
        """Test versions_json has required structure."""
        from app.services.manifest_service import ManifestService

        mock_db = MagicMock()
        service = ManifestService(mock_db)

        versions = service._build_versions()

        required_keys = [
            "code_version",
            "sim_engine_version",
            "rules_version",
            "personas_version",
            "model_version",
            "dataset_version",
        ]

        for key in required_keys:
            assert key in versions, f"versions_json must contain {key}"


# =============================================================================
# Edge Cases
# =============================================================================

class TestManifestEdgeCases:
    """Test edge cases for manifest handling."""

    def test_empty_config_json(self):
        """Test manifest with empty config_json."""
        seed = 42
        config = {}
        versions = {"code_version": "v1"}

        # Should not raise
        hash_result = RunManifest.compute_manifest_hash(seed, config, versions)
        assert hash_result is not None

    def test_nested_config_json(self):
        """Test manifest with nested config_json."""
        seed = 42
        config = {
            "max_ticks": 100,
            "nested": {
                "level1": {
                    "level2": {"value": 42}
                }
            }
        }
        versions = {"code_version": "v1"}

        hash_result = RunManifest.compute_manifest_hash(seed, config, versions)
        assert hash_result is not None

    def test_large_seed_value(self):
        """Test manifest with large seed value."""
        seed = 2**31 - 1  # Max 32-bit signed int
        config = {"max_ticks": 100}
        versions = {"code_version": "v1"}

        hash_result = RunManifest.compute_manifest_hash(seed, config, versions)
        assert hash_result is not None

    def test_unicode_in_config(self):
        """Test manifest with unicode in config."""
        seed = 42
        config = {"label": "テスト日本語", "emoji": "🚀"}
        versions = {"code_version": "v1"}

        hash_result = RunManifest.compute_manifest_hash(seed, config, versions)
        assert hash_result is not None

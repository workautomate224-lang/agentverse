"""
Manifest Service - PHASE 2: Reproducibility & Auditability

Provides business logic for run manifest operations:
- Creating manifests at run creation time
- Retrieving manifests
- Reproducing runs with identical manifests
- Verifying manifest integrity

Reference: project.md Phase 2 - Run Manifest / Seed / Version System
"""

import hashlib
import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.run_manifest import RunManifest
from app.models.node import Run, Node, RunStatus
from app.models.project_spec import ProjectSpec
from app.schemas.run_manifest import (
    CreateManifestInput,
    ReproduceMode,
    VersionsInfo,
)


def get_code_version() -> str:
    """
    Get the current code version from environment.

    Checks in order:
    1. GIT_SHA environment variable
    2. RAILWAY_GIT_COMMIT_SHA (Railway deployment)
    3. VERCEL_GIT_COMMIT_SHA (Vercel deployment)
    4. Falls back to "unknown"
    """
    for env_var in ["GIT_SHA", "RAILWAY_GIT_COMMIT_SHA", "VERCEL_GIT_COMMIT_SHA"]:
        value = os.environ.get(env_var)
        if value:
            return value[:12]  # First 12 chars of SHA
    return "unknown"


def compute_content_hash(content: Any) -> str:
    """
    Compute SHA256 hash of content.

    If content is a dict/list, serializes to canonical JSON first.
    """
    if isinstance(content, (dict, list)):
        content = json.dumps(content, sort_keys=True, separators=(',', ':'))
    elif not isinstance(content, str):
        content = str(content)
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]


class ManifestService:
    """
    Service for managing run manifests.

    Handles:
    - Manifest creation at run time
    - Manifest retrieval
    - Run reproduction
    - Integrity verification
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_manifest(
        self,
        tenant_id: uuid.UUID,
        project_id: uuid.UUID,
        run_id: uuid.UUID,
        node_id: Optional[uuid.UUID],
        seed: int,
        config: Dict[str, Any],
        rules_content: Optional[str] = None,
        personas_content: Optional[str] = None,
        model_info: Optional[Dict[str, Any]] = None,
        dataset_version: Optional[str] = None,
        created_by_user_id: Optional[uuid.UUID] = None,
        source_run_id: Optional[uuid.UUID] = None,
    ) -> RunManifest:
        """
        Create an immutable manifest for a run.

        This should be called at run creation time BEFORE execution starts.

        Args:
            tenant_id: Tenant ID
            project_id: Project ID
            run_id: Run ID (must already exist)
            node_id: Node ID (optional)
            seed: Global deterministic seed
            config: Run configuration dict
            rules_content: Rules text/JSON for hashing
            personas_content: Personas text/JSON for hashing
            model_info: LLM model info (name, params)
            dataset_version: Dataset version string
            created_by_user_id: User who created the run
            source_run_id: Original run ID if this is a reproduction

        Returns:
            Created RunManifest
        """
        # Build normalized config snapshot
        config_json = self._normalize_config(config)

        # Build versions snapshot
        versions_json = self._build_versions(
            rules_content=rules_content,
            personas_content=personas_content,
            model_info=model_info,
            dataset_version=dataset_version,
        )

        # Compute manifest hash
        manifest_hash = RunManifest.compute_manifest_hash(
            seed=seed,
            config_json=config_json,
            versions_json=versions_json,
        )

        # Create manifest record
        manifest = RunManifest(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            project_id=project_id,
            run_id=run_id,
            node_id=node_id,
            seed=seed,
            config_json=config_json,
            versions_json=versions_json,
            manifest_hash=manifest_hash,
            is_immutable=True,  # Immutable from creation
            created_by_user_id=created_by_user_id,
            source_run_id=source_run_id,
            created_at=datetime.utcnow(),
        )

        self.db.add(manifest)
        await self.db.flush()

        return manifest

    def _normalize_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize configuration for consistent hashing.

        Extracts standard fields and preserves extras.
        """
        normalized = {
            "max_ticks": config.get("max_ticks", 100),
            "agent_batch_size": config.get("agent_batch_size", 100),
            "run_mode": config.get("run_mode", "society"),
            "horizon": config.get("horizon", 1000),
            "tick_rate": config.get("tick_rate", 1),
        }

        # Include optional fields if present
        if "environment_params" in config:
            normalized["environment_params"] = config["environment_params"]
        if "scheduler_config" in config:
            normalized["scheduler_config"] = config["scheduler_config"]
        if "scenario_patch" in config:
            normalized["scenario_patch"] = config["scenario_patch"]
        if "society_mode" in config:
            normalized["society_mode"] = config["society_mode"]

        return normalized

    def _build_versions(
        self,
        rules_content: Optional[str] = None,
        personas_content: Optional[str] = None,
        model_info: Optional[Dict[str, Any]] = None,
        dataset_version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build versions snapshot for manifest.

        Computes hashes for rules and personas content.
        """
        versions = {
            "code_version": get_code_version(),
            "sim_engine_version": os.environ.get("SIM_ENGINE_VERSION", "1.0.0"),
        }

        # Hash rules content if provided
        if rules_content:
            versions["rules_version"] = compute_content_hash(rules_content)
        else:
            versions["rules_version"] = "default"

        # Hash personas content if provided
        if personas_content:
            versions["personas_version"] = compute_content_hash(personas_content)
        else:
            versions["personas_version"] = "default"

        # Model info
        if model_info:
            model_str = json.dumps(model_info, sort_keys=True)
            versions["model_version"] = f"{model_info.get('model', 'unknown')}:{compute_content_hash(model_str)}"
        else:
            versions["model_version"] = "default"

        # Dataset version
        versions["dataset_version"] = dataset_version or "default"

        return versions

    async def get_manifest(
        self,
        run_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Optional[RunManifest]:
        """
        Get manifest for a run.

        Args:
            run_id: Run ID
            tenant_id: Tenant ID for access control

        Returns:
            RunManifest or None if not found
        """
        query = select(RunManifest).where(
            RunManifest.run_id == run_id,
            RunManifest.tenant_id == tenant_id,
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_manifest_by_hash(
        self,
        manifest_hash: str,
        tenant_id: uuid.UUID,
    ) -> Optional[RunManifest]:
        """
        Find a manifest by its hash.

        Useful for checking if an identical configuration has been run before.

        Args:
            manifest_hash: SHA256 hash of manifest
            tenant_id: Tenant ID for access control

        Returns:
            First matching RunManifest or None
        """
        query = select(RunManifest).where(
            RunManifest.manifest_hash == manifest_hash,
            RunManifest.tenant_id == tenant_id,
        ).order_by(RunManifest.created_at.desc())
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def reproduce_run(
        self,
        source_run_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user_id: Optional[uuid.UUID],
        mode: ReproduceMode = ReproduceMode.FORK_NODE,
        label: Optional[str] = None,
    ) -> Tuple[Run, Node, RunManifest]:
        """
        Create a new run with identical manifest to source run.

        Args:
            source_run_id: Original run to reproduce
            tenant_id: Tenant ID
            user_id: User creating the reproduction
            mode: same_node or fork_node
            label: Optional label for new run

        Returns:
            Tuple of (new Run, Node, new RunManifest)

        Raises:
            ValueError: If source run or manifest not found
        """
        # Get source manifest
        source_manifest = await self.get_manifest(source_run_id, tenant_id)
        if not source_manifest:
            raise ValueError(f"Manifest not found for run {source_run_id}")

        # Get source run for node reference
        source_run_query = select(Run).where(
            Run.id == source_run_id,
            Run.tenant_id == tenant_id,
        )
        result = await self.db.execute(source_run_query)
        source_run = result.scalar_one_or_none()
        if not source_run:
            raise ValueError(f"Run {source_run_id} not found")

        # Determine node for new run
        if mode == ReproduceMode.SAME_NODE:
            # Attach to same node
            node_id = source_run.node_id
            node_query = select(Node).where(Node.id == node_id)
            node_result = await self.db.execute(node_query)
            node = node_result.scalar_one_or_none()
            if not node:
                raise ValueError(f"Node {node_id} not found")
        else:
            # Fork to new node
            from app.services.node_service import (
                NodeService,
                ForkNodeInput,
                EdgeIntervention,
                InterventionType,
            )

            node_service = NodeService(self.db)

            # Create fork with reproduction metadata
            fork_input = ForkNodeInput(
                parent_node_id=source_run.node_id,
                project_id=source_run.project_id,
                tenant_id=tenant_id,
                intervention=EdgeIntervention(
                    intervention_type=InterventionType.MANUAL_FORK,
                    variable_deltas={"_reproduction_of": str(source_run_id)},
                ),
                label=label or f"Reproduction of run {str(source_run_id)[:8]}",
            )
            node, edge, _ = await node_service.fork_node(fork_input)

        # Create new run with same config
        from sqlalchemy import text

        new_run_id = uuid.uuid4()
        run_config_id = uuid.uuid4()

        # Create run config (copy from source)
        await self.db.execute(
            text("""
                INSERT INTO run_configs (
                    id, project_id, tenant_id, versions, seed_config,
                    horizon, tick_rate, scheduler_profile, logging_profile,
                    scenario_patch, max_execution_time_ms, max_agents,
                    created_at, updated_at
                )
                SELECT
                    :new_id, project_id, tenant_id, versions, seed_config,
                    horizon, tick_rate, scheduler_profile, logging_profile,
                    scenario_patch, max_execution_time_ms, max_agents,
                    :created_at, :updated_at
                FROM run_configs
                WHERE id = :source_config_id
            """),
            {
                "new_id": run_config_id,
                "source_config_id": source_run.run_config_ref,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        )

        # Create new run
        new_run = Run(
            id=new_run_id,
            project_id=source_run.project_id,
            tenant_id=tenant_id,
            node_id=node.id,
            run_config_ref=run_config_id,
            status=RunStatus.CREATED.value,
            actual_seed=source_manifest.seed,  # Use exact same seed
            label=label or f"Reproduction of {source_run.label or str(source_run_id)[:8]}",
            triggered_by="user",
            triggered_by_user_id=user_id,
            timing={"created_at": datetime.utcnow().isoformat()},
        )
        self.db.add(new_run)
        await self.db.flush()

        # Create new manifest with same content but pointing to new run
        new_manifest = RunManifest(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            project_id=source_run.project_id,
            run_id=new_run_id,
            node_id=node.id,
            seed=source_manifest.seed,
            config_json=source_manifest.config_json,
            versions_json=source_manifest.versions_json,
            manifest_hash=source_manifest.manifest_hash,  # Should be identical
            is_immutable=True,
            created_by_user_id=user_id,
            source_run_id=source_run_id,  # Track provenance
            created_at=datetime.utcnow(),
        )
        self.db.add(new_manifest)
        await self.db.flush()

        return new_run, node, new_manifest

    async def verify_manifest_integrity(
        self,
        run_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Tuple[bool, str, str]:
        """
        Verify manifest integrity by recomputing hash.

        Args:
            run_id: Run ID
            tenant_id: Tenant ID

        Returns:
            Tuple of (is_valid, stored_hash, computed_hash)

        Raises:
            ValueError: If manifest not found
        """
        manifest = await self.get_manifest(run_id, tenant_id)
        if not manifest:
            raise ValueError(f"Manifest not found for run {run_id}")

        computed_hash = RunManifest.compute_manifest_hash(
            manifest.seed,
            manifest.config_json,
            manifest.versions_json,
        )

        return (
            computed_hash == manifest.manifest_hash,
            manifest.manifest_hash,
            computed_hash,
        )


def get_manifest_service(db: AsyncSession) -> ManifestService:
    """Factory function for ManifestService."""
    return ManifestService(db)

"""
Run Manifest Model - PHASE 2: Reproducibility & Auditability

Provides an immutable snapshot of all configuration, versions, and seeds
used for a simulation run, enabling exact reproducibility and audit trails.

Reference: project.md Phase 2 - Run Manifest / Seed / Version System
"""

import hashlib
import json
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.node import Node, Run
    from app.models.project_spec import ProjectSpec


class RunManifest(Base):
    """
    Immutable manifest capturing exact state for run reproducibility.

    PHASE 2 Requirements:
    - One-to-one relationship with Run
    - Created at run creation time
    - Immutable after run starts
    - Contains all information needed to reproduce the exact same run

    Fields:
    - seed: Global deterministic seed for RNG
    - config_json: Normalized config snapshot (max_ticks, agents, environment, etc.)
    - versions_json: All version info (code, engine, rules, personas, model)
    - manifest_hash: SHA256 of canonical manifest for integrity verification
    - storage_ref: Optional S3 pointer for large payloads
    """
    __tablename__ = "run_manifests"

    # Identity
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project_specs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One-to-one with Run
        index=True
    )
    node_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Global deterministic seed
    seed: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="Global deterministic seed for all RNG in this run"
    )

    # Configuration snapshot (normalized)
    config_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        comment="Normalized config snapshot: max_ticks, agents, environment params, etc."
    )

    # Versions snapshot
    versions_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        comment="Version info: code_version, sim_engine_version, rules_version, personas_version, model_version, dataset_version"
    )

    # Integrity hash
    manifest_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="SHA256 hash of canonical manifest payload for integrity verification"
    )

    # Optional S3 storage for large payloads
    storage_ref: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="S3 pointer if manifest is stored externally: {bucket, key, etag}"
    )

    # Immutability flag
    is_immutable: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        server_default="true",
        comment="True once run starts - prevents modifications"
    )

    # Provenance metadata
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    source_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="If this is a reproduction, the original run_id"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )

    # Relationships
    run: Mapped["Run"] = relationship(
        "Run",
        foreign_keys=[run_id],
        backref="manifest"
    )
    project: Mapped["ProjectSpec"] = relationship(
        "ProjectSpec",
        foreign_keys=[project_id]
    )
    node: Mapped[Optional["Node"]] = relationship(
        "Node",
        foreign_keys=[node_id]
    )

    def __repr__(self) -> str:
        return f"<RunManifest run_id={self.run_id} seed={self.seed} hash={self.manifest_hash[:8]}...>"

    @staticmethod
    def compute_manifest_hash(
        seed: int,
        config_json: Dict[str, Any],
        versions_json: Dict[str, Any]
    ) -> str:
        """
        Compute SHA256 hash of canonical manifest payload.

        Uses canonical JSON serialization:
        - Sorted keys
        - No whitespace
        - Stable ordering

        Returns:
            64-character hex string (SHA256)
        """
        payload = {
            "seed": seed,
            "config": config_json,
            "versions": versions_json
        }
        # Canonical JSON: sorted keys, no whitespace, separators without spaces
        canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()

    @staticmethod
    def compute_content_hash(content: str) -> str:
        """
        Compute SHA256 hash of arbitrary content (for rules, personas, etc.).

        Args:
            content: String content to hash

        Returns:
            64-character hex string (SHA256)
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Return dictionary representation for API response."""
        return {
            "id": str(self.id),
            "run_id": str(self.run_id),
            "project_id": str(self.project_id),
            "node_id": str(self.node_id) if self.node_id else None,
            "seed": self.seed,
            "config_json": self.config_json,
            "versions_json": self.versions_json,
            "manifest_hash": self.manifest_hash,
            "storage_ref": self.storage_ref,
            "is_immutable": self.is_immutable,
            "source_run_id": str(self.source_run_id) if self.source_run_id else None,
            "created_by_user_id": str(self.created_by_user_id) if self.created_by_user_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def get_provenance_summary(self) -> Dict[str, Any]:
        """
        Get a short audit summary for provenance endpoint.

        Returns:
            Provenance summary dict
        """
        return {
            "run_id": str(self.run_id),
            "manifest_hash": self.manifest_hash,
            "seed": self.seed,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by_user_id": str(self.created_by_user_id) if self.created_by_user_id else None,
            "source_run_id": str(self.source_run_id) if self.source_run_id else None,
            "node_id": str(self.node_id) if self.node_id else None,
            "project_id": str(self.project_id),
            "is_reproduction": self.source_run_id is not None,
            "code_version": self.versions_json.get("code_version", "unknown"),
            "engine_version": self.versions_json.get("sim_engine_version", "unknown"),
        }

    def verify_integrity(self) -> bool:
        """
        Verify manifest integrity by recomputing hash.

        Returns:
            True if computed hash matches stored hash
        """
        computed = self.compute_manifest_hash(
            self.seed,
            self.config_json,
            self.versions_json
        )
        return computed == self.manifest_hash

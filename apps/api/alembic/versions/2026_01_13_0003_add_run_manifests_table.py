"""Add run_manifests table for PHASE 2 Reproducibility

Revision ID: add_run_manifests_001
Revises: add_target_plans_001
Create Date: 2026-01-13

This migration creates the run_manifests table for PHASE 2:
Run Manifest / Seed / Version System for reproducibility and auditability.

The run_manifests table stores:
- Seed: Global deterministic seed for all RNG
- Config snapshot: Normalized configuration used for the run
- Versions: All version info (code, engine, rules, personas, model)
- Manifest hash: SHA256 for integrity verification
- Storage ref: Optional S3 pointer for large payloads
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "add_run_manifests_001"
down_revision = "add_target_plans_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create run_manifests table."""
    op.create_table(
        "run_manifests",
        # Identity
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("project_specs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("runs.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,  # One-to-one with Run
            index=True,
        ),
        sa.Column(
            "node_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("nodes.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        # Global deterministic seed
        sa.Column(
            "seed",
            sa.BigInteger,
            nullable=False,
            comment="Global deterministic seed for all RNG in this run",
        ),
        # Configuration snapshot (normalized)
        sa.Column(
            "config_json",
            postgresql.JSONB,
            nullable=False,
            comment="Normalized config snapshot: max_ticks, agents, environment params, etc.",
        ),
        # Versions snapshot
        sa.Column(
            "versions_json",
            postgresql.JSONB,
            nullable=False,
            comment="Version info: code_version, sim_engine_version, rules_version, personas_version, model_version, dataset_version",
        ),
        # Integrity hash
        sa.Column(
            "manifest_hash",
            sa.String(64),
            nullable=False,
            index=True,
            comment="SHA256 hash of canonical manifest payload for integrity verification",
        ),
        # Optional S3 storage for large payloads
        sa.Column(
            "storage_ref",
            postgresql.JSONB,
            nullable=True,
            comment="S3 pointer if manifest is stored externally: {bucket, key, etag}",
        ),
        # Immutability flag
        sa.Column(
            "is_immutable",
            sa.Boolean,
            nullable=False,
            server_default="true",
            comment="True once run starts - prevents modifications",
        ),
        # Provenance metadata
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "source_run_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="If this is a reproduction, the original run_id",
        ),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Create indexes for common queries
    op.create_index(
        "ix_run_manifests_project_created",
        "run_manifests",
        ["project_id", "created_at"],
    )
    op.create_index(
        "ix_run_manifests_manifest_hash",
        "run_manifests",
        ["tenant_id", "manifest_hash"],
    )
    op.create_index(
        "ix_run_manifests_source_run",
        "run_manifests",
        ["source_run_id"],
        postgresql_where=sa.text("source_run_id IS NOT NULL"),
    )


def downgrade() -> None:
    """Drop run_manifests table."""
    op.drop_index("ix_run_manifests_source_run", table_name="run_manifests")
    op.drop_index("ix_run_manifests_manifest_hash", table_name="run_manifests")
    op.drop_index("ix_run_manifests_project_created", table_name="run_manifests")
    op.drop_table("run_manifests")

#!/usr/bin/env python3
"""
Dev Seed Script - STEP 0 Requirement
Reference: Future_Predictive_AI_Platform_Ultra_Checklist.md

Creates a complete development dataset:
- 1 Project
- 1 Baseline Node
- 2 Persona Snapshots
- 1 Event
- 2 Nodes (including baseline)
- 2 Runs
- 1 Replay-able Run (with full RunSpec, RunTrace, OutcomeReport)

Usage:
    python scripts/seed_dev.py

Environment:
    Requires DATABASE_URL to be set.
"""

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Import models after path setup
from app.models import (
    Tenant,
    User,
    Project,
    PersonaTemplate,
    PersonaRecord,
)
from app.models.node import Node, Edge, Run, RunStatus
from app.models.run_config import RunConfig
from app.models.run_artifacts import RunSpec, RunTrace, OutcomeReport
from app.models.event_script import EventScript, EventType
from app.db.session import Base


# =============================================================================
# Configuration
# =============================================================================

SEED_CONFIG = {
    "tenant_name": "Dev Seed Tenant",
    "tenant_email": "seed@agentverse.dev",
    "project_name": "Dev Seed Project",
    "project_domain": "election",
    "horizon": 200,
    "seed": 42,  # Deterministic seed for reproducibility
}


# =============================================================================
# Seed Functions
# =============================================================================

async def create_tenant(db: AsyncSession) -> uuid.UUID:
    """Create dev tenant."""
    tenant_id = uuid.uuid4()
    tenant = Tenant(
        id=tenant_id,
        name=SEED_CONFIG["tenant_name"],
        slug="dev-seed",
        email=SEED_CONFIG["tenant_email"],
        settings={"seed_version": "1.0"},
        is_active=True,
    )
    db.add(tenant)
    await db.flush()
    print(f"[SEED] Created Tenant: {tenant_id}")
    return tenant_id


async def create_user(db: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    """Create dev user."""
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        tenant_id=tenant_id,
        email="dev@agentverse.dev",
        full_name="Dev Seed User",
        hashed_password="$2b$12$seedhashedpasswordnotusableforlogin",  # Not a real hash
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    await db.flush()
    print(f"[SEED] Created User: {user_id}")
    return user_id


async def create_project(db: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    """Create dev project."""
    project_id = uuid.uuid4()
    project = Project(
        id=project_id,
        tenant_id=tenant_id,
        name=SEED_CONFIG["project_name"],
        description="Development seed project for testing and verification",
        settings={
            "domain": SEED_CONFIG["project_domain"],
            "default_horizon": SEED_CONFIG["horizon"],
            "seed": SEED_CONFIG["seed"],
        },
    )
    db.add(project)
    await db.flush()
    print(f"[SEED] Created Project: {project_id}")
    return project_id


async def create_persona_snapshots(db: AsyncSession, tenant_id: uuid.UUID, project_id: uuid.UUID) -> list[uuid.UUID]:
    """Create 2 persona snapshots."""
    snapshot_ids = []

    # Snapshot 1: Moderate voter profile
    template_1 = PersonaTemplate(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Moderate Voter Snapshot",
        description="Centrist voters with mixed policy preferences",
        template_type="voter",
        attributes={
            "political_leaning": "moderate",
            "age_range": "35-54",
            "education": "college",
            "income_bracket": "middle",
        },
        is_active=True,
    )
    db.add(template_1)
    snapshot_ids.append(template_1.id)

    # Snapshot 2: Progressive voter profile
    template_2 = PersonaTemplate(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Progressive Voter Snapshot",
        description="Progressive voters with strong policy preferences",
        template_type="voter",
        attributes={
            "political_leaning": "progressive",
            "age_range": "25-34",
            "education": "graduate",
            "income_bracket": "upper-middle",
        },
        is_active=True,
    )
    db.add(template_2)
    snapshot_ids.append(template_2.id)

    await db.flush()
    print(f"[SEED] Created 2 Persona Snapshots: {snapshot_ids}")
    return snapshot_ids


async def create_event(db: AsyncSession, tenant_id: uuid.UUID, project_id: uuid.UUID) -> uuid.UUID:
    """Create 1 event."""
    event_id = uuid.uuid4()
    event = EventScript(
        id=event_id,
        tenant_id=tenant_id,
        project_id=project_id,
        name="Economic Policy Announcement",
        description="Major economic policy change affecting voter sentiment",
        event_type=EventType.ENVIRONMENTAL,
        source_text="Government announces new economic stimulus package worth $500B",
        compiled_params={
            "target_attribute": "economic_confidence",
            "delta": 0.15,
            "scope": "all_agents",
            "duration_ticks": 50,
        },
        is_active=True,
    )
    db.add(event)
    await db.flush()
    print(f"[SEED] Created Event: {event_id}")
    return event_id


async def create_nodes(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID
) -> tuple[uuid.UUID, uuid.UUID]:
    """Create baseline node + 1 child node."""
    # Baseline node
    baseline_id = uuid.uuid4()
    baseline = Node(
        id=baseline_id,
        tenant_id=tenant_id,
        project_id=project_id,
        label="Baseline - 2024 Election",
        description="Initial baseline scenario",
        is_baseline=True,
        status="completed",
        position_x=0.0,
        position_y=0.0,
    )
    db.add(baseline)

    # Child node
    child_id = uuid.uuid4()
    child = Node(
        id=child_id,
        tenant_id=tenant_id,
        project_id=project_id,
        parent_node_id=baseline_id,
        label="Scenario A - With Event",
        description="Scenario with economic policy event applied",
        is_baseline=False,
        status="completed",
        position_x=200.0,
        position_y=0.0,
    )
    db.add(child)

    # Create edge
    edge = Edge(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        project_id=project_id,
        source_node_id=baseline_id,
        target_node_id=child_id,
        label="Economic Policy",
    )
    db.add(edge)

    await db.flush()
    print(f"[SEED] Created 2 Nodes: baseline={baseline_id}, child={child_id}")
    return baseline_id, child_id


async def create_run_config(db: AsyncSession, tenant_id: uuid.UUID, project_id: uuid.UUID) -> uuid.UUID:
    """Create run configuration."""
    config_id = uuid.uuid4()
    config = RunConfig(
        id=config_id,
        tenant_id=tenant_id,
        project_id=project_id,
        name="Dev Seed Config",
        versions={
            "engine_version": "1.0.0",
            "ruleset_version": "1.0.0",
            "dataset_version": "1.0.0",
        },
        seed_config={
            "master_seed": SEED_CONFIG["seed"],
            "agent_seed": SEED_CONFIG["seed"] + 1,
            "event_seed": SEED_CONFIG["seed"] + 2,
        },
        horizon=SEED_CONFIG["horizon"],
        tick_rate=1,
        scheduler_profile={"mode": "sequential"},
        max_agents=100,
        is_active=True,
    )
    db.add(config)
    await db.flush()
    print(f"[SEED] Created RunConfig: {config_id}")
    return config_id


async def create_runs(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    baseline_id: uuid.UUID,
    child_id: uuid.UUID,
    config_id: uuid.UUID,
) -> tuple[uuid.UUID, uuid.UUID]:
    """Create 2 runs - one completed, one replay-able."""
    # Run 1: Completed run on baseline
    run1_id = uuid.uuid4()
    run1 = Run(
        id=run1_id,
        tenant_id=tenant_id,
        project_id=project_id,
        node_id=baseline_id,
        run_config_ref=config_id,
        status=RunStatus.COMPLETED,
        timing={"started_at": datetime.now(timezone.utc).isoformat()},
        outputs={"primary_outcome": "Candidate A", "probability": 0.52},
        actual_seed=SEED_CONFIG["seed"],
        ticks_completed=SEED_CONFIG["horizon"],
        ticks_total=SEED_CONFIG["horizon"],
    )
    db.add(run1)

    # Run 2: Replay-able run on child (with full artifacts)
    run2_id = uuid.uuid4()
    run2 = Run(
        id=run2_id,
        tenant_id=tenant_id,
        project_id=project_id,
        node_id=child_id,
        run_config_ref=config_id,
        status=RunStatus.COMPLETED,
        timing={"started_at": datetime.now(timezone.utc).isoformat()},
        outputs={"primary_outcome": "Candidate B", "probability": 0.54},
        actual_seed=SEED_CONFIG["seed"],
        ticks_completed=SEED_CONFIG["horizon"],
        ticks_total=SEED_CONFIG["horizon"],
    )
    db.add(run2)
    await db.flush()

    print(f"[SEED] Created 2 Runs: run1={run1_id}, run2={run2_id}")
    return run1_id, run2_id


async def create_run_artifacts(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    node_id: uuid.UUID,
    config_id: uuid.UUID,
) -> None:
    """Create full artifacts for replay-able run: RunSpec, RunTrace, OutcomeReport."""

    # RunSpec
    spec = RunSpec(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        run_id=run_id,
        spec_version="1.0.0",
        spec_hash="sha256:seed_spec_hash_placeholder",
        seed=SEED_CONFIG["seed"],
        horizon=SEED_CONFIG["horizon"],
        ticks_total=SEED_CONFIG["horizon"],
        environment_spec={
            "domain": SEED_CONFIG["project_domain"],
            "region": "national",
        },
        model_bundle={
            "agent_model": "voter_v1",
            "decision_model": "utility_v1",
        },
        data_cutoff="2024-01-01T00:00:00Z",
    )
    db.add(spec)

    # RunTrace (summary - full trace would be in blob storage)
    trace = RunTrace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        run_id=run_id,
        trace_version="1.0.0",
        trace_hash="sha256:seed_trace_hash_placeholder",
        tick_count=SEED_CONFIG["horizon"],
        agent_count=100,
        keyframe_count=20,
        delta_count=1800,
        keyframes=[
            {"tick": 0, "summary": "initial_state", "agent_snapshot_count": 100},
            {"tick": 100, "summary": "midpoint", "agent_snapshot_count": 100},
            {"tick": 200, "summary": "final", "agent_snapshot_count": 100},
        ],
        storage_uri=f"local://traces/{run_id}.jsonl",
    )
    db.add(trace)

    # OutcomeReport
    outcome = OutcomeReport(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        run_id=run_id,
        node_id=node_id,
        report_version="1.0.0",
        report_hash="sha256:seed_outcome_hash_placeholder",
        primary_outcome="Candidate B",
        primary_outcome_probability=Decimal("0.54"),
        outcome_distribution={
            "Candidate A": 0.46,
            "Candidate B": 0.54,
        },
        key_metrics=[
            {"metric": "turnout", "value": 0.67},
            {"metric": "swing_voters", "value": 0.12},
        ],
        key_drivers=[
            {"driver": "economic_confidence", "impact": 0.08},
            {"driver": "incumbent_approval", "impact": -0.05},
        ],
        confidence_interval_low=Decimal("0.49"),
        confidence_interval_high=Decimal("0.59"),
        ensemble_size=1,
        stability_variance=Decimal("0.02"),
    )
    db.add(outcome)

    await db.flush()
    print(f"[SEED] Created Run Artifacts for: {run_id}")


async def run_seed():
    """Execute full seed."""
    # Get database URL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("[ERROR] DATABASE_URL environment variable not set")
        sys.exit(1)

    # Convert to async URL if needed
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    print(f"[SEED] Connecting to database...")

    engine = create_async_engine(database_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        try:
            # Check if seed data already exists
            result = await db.execute(
                text("SELECT COUNT(*) FROM tenants WHERE slug = 'dev-seed'")
            )
            count = result.scalar()
            if count and count > 0:
                print("[SEED] Dev seed data already exists. Skipping.")
                return

            print("[SEED] Starting dev seed...")

            # Create all entities
            tenant_id = await create_tenant(db)
            user_id = await create_user(db, tenant_id)
            project_id = await create_project(db, tenant_id)
            snapshot_ids = await create_persona_snapshots(db, tenant_id, project_id)
            event_id = await create_event(db, tenant_id, project_id)
            baseline_id, child_id = await create_nodes(db, tenant_id, project_id)
            config_id = await create_run_config(db, tenant_id, project_id)
            run1_id, run2_id = await create_runs(
                db, tenant_id, project_id, baseline_id, child_id, config_id
            )

            # Create full artifacts for replay-able run
            await create_run_artifacts(db, tenant_id, project_id, run2_id, child_id, config_id)

            await db.commit()

            print("\n" + "=" * 60)
            print("[SEED] Dev seed completed successfully!")
            print("=" * 60)
            print(f"  Tenant ID:     {tenant_id}")
            print(f"  User ID:       {user_id}")
            print(f"  Project ID:    {project_id}")
            print(f"  Snapshots:     {snapshot_ids}")
            print(f"  Event ID:      {event_id}")
            print(f"  Baseline Node: {baseline_id}")
            print(f"  Child Node:    {child_id}")
            print(f"  Run 1 ID:      {run1_id}")
            print(f"  Run 2 ID:      {run2_id} (replay-able with full artifacts)")
            print("=" * 60)

        except Exception as e:
            await db.rollback()
            print(f"[ERROR] Seed failed: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(run_seed())

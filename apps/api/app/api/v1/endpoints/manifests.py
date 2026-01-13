"""
Run Manifest API Endpoints - PHASE 2: Reproducibility & Auditability

Provides endpoints for:
- GET /projects/{project_id}/runs/{run_id}/manifest - Get manifest for a run
- POST /projects/{project_id}/runs/{run_id}/reproduce - Reproduce a run
- GET /projects/{project_id}/runs/{run_id}/provenance - Get audit summary

Reference: project.md Phase 2 - Run Manifest / Seed / Version System
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.middleware.tenant import (
    TenantContext,
    require_tenant,
)
from app.models.user import User
from app.schemas.run_manifest import (
    RunManifestResponse,
    ProvenanceResponse,
    ReproduceRunRequest,
    ReproduceRunResponse,
    ReproduceMode,
    VerifyManifestResponse,
)
from app.services.manifest_service import get_manifest_service


router = APIRouter()


# =============================================================================
# GET /projects/{project_id}/runs/{run_id}/manifest
# =============================================================================

@router.get(
    "/projects/{project_id}/runs/{run_id}/manifest",
    response_model=RunManifestResponse,
    summary="Get run manifest",
    description="Retrieve the immutable manifest snapshot for a simulation run.",
)
async def get_run_manifest(
    project_id: str,
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> RunManifestResponse:
    """
    Get the manifest for a run.

    The manifest contains:
    - seed: Global deterministic seed
    - config_json: Normalized configuration snapshot
    - versions_json: Version info for all components
    - manifest_hash: SHA256 for integrity verification
    - storage_ref: S3 pointer if stored externally

    Returns 404 if run or manifest not found.
    """
    manifest_service = get_manifest_service(db)

    manifest = await manifest_service.get_manifest(
        run_id=UUID(run_id),
        tenant_id=tenant_ctx.tenant_id,
    )

    if not manifest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Manifest not found for run {run_id}. "
                   "Manifests are created when runs start. "
                   "If this is an older run, it may not have a manifest.",
        )

    # Verify project matches
    if str(manifest.project_id) != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found in project {project_id}",
        )

    return RunManifestResponse(
        id=manifest.id,
        run_id=manifest.run_id,
        project_id=manifest.project_id,
        node_id=manifest.node_id,
        seed=manifest.seed,
        config_json=manifest.config_json,
        versions_json=manifest.versions_json,
        manifest_hash=manifest.manifest_hash,
        storage_ref=manifest.storage_ref,
        is_immutable=manifest.is_immutable,
        source_run_id=manifest.source_run_id,
        created_at=manifest.created_at,
        created_by_user_id=manifest.created_by_user_id,
    )


# =============================================================================
# POST /projects/{project_id}/runs/{run_id}/reproduce
# =============================================================================

@router.post(
    "/projects/{project_id}/runs/{run_id}/reproduce",
    response_model=ReproduceRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Reproduce a run",
    description="Create a new run with identical manifest (seed, config, versions).",
)
async def reproduce_run(
    project_id: str,
    run_id: str,
    request: ReproduceRunRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> ReproduceRunResponse:
    """
    Reproduce a run with identical configuration.

    Creates a NEW run with the SAME manifest (seed/config/versions) but new run_id.

    Modes:
    - same_node: Attach new run to the same node as original
    - fork_node (default): Create a new forked node for the run

    If auto_start=true, the run will be queued for execution immediately.

    Returns the new run_id and a deep-link friendly URL.
    """
    manifest_service = get_manifest_service(db)

    # Verify source manifest exists
    source_manifest = await manifest_service.get_manifest(
        run_id=UUID(run_id),
        tenant_id=tenant_ctx.tenant_id,
    )

    if not source_manifest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Manifest not found for run {run_id}. Cannot reproduce.",
        )

    if str(source_manifest.project_id) != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found in project {project_id}",
        )

    try:
        # Reproduce the run
        new_run, node, new_manifest = await manifest_service.reproduce_run(
            source_run_id=UUID(run_id),
            tenant_id=tenant_ctx.tenant_id,
            user_id=current_user.id,
            mode=request.mode,
            label=request.label,
        )

        await db.commit()

        # Auto-start if requested
        task_id = None
        if request.auto_start:
            from app.services import get_simulation_orchestrator
            orchestrator = get_simulation_orchestrator(db)
            task_id = await orchestrator.start_run(
                new_run,
                str(tenant_ctx.tenant_id),
            )
            await db.commit()

        # Build deep link
        deep_link = f"/p/{project_id}/runs/{new_run.id}"

        return ReproduceRunResponse(
            new_run_id=new_run.id,
            new_node_id=node.id if request.mode == ReproduceMode.FORK_NODE else None,
            manifest_hash=new_manifest.manifest_hash,
            seed=new_manifest.seed,
            mode=request.mode,
            source_run_id=UUID(run_id),
            task_id=task_id,
            deep_link=deep_link,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        import traceback
        import logging
        logging.error(f"Failed to reproduce run: {str(e)}\n{traceback.format_exc()}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reproduce run: {str(e)}",
        )


# =============================================================================
# GET /projects/{project_id}/runs/{run_id}/provenance
# =============================================================================

@router.get(
    "/projects/{project_id}/runs/{run_id}/provenance",
    response_model=ProvenanceResponse,
    summary="Get run provenance",
    description="Get a short audit summary for a run.",
)
async def get_run_provenance(
    project_id: str,
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> ProvenanceResponse:
    """
    Get provenance/audit summary for a run.

    Returns:
    - created_by: User who created the run
    - created_at: When the run was created
    - source_node: Node the run is attached to
    - branch_info: Fork/branch information if applicable
    - manifest_hash: For integrity verification
    - is_reproduction: Whether this was reproduced from another run
    """
    manifest_service = get_manifest_service(db)

    manifest = await manifest_service.get_manifest(
        run_id=UUID(run_id),
        tenant_id=tenant_ctx.tenant_id,
    )

    if not manifest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Manifest not found for run {run_id}",
        )

    if str(manifest.project_id) != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found in project {project_id}",
        )

    # Get branch info if this is from a forked node
    branch_info = None
    if manifest.node_id:
        from sqlalchemy import select
        from app.models.node import Node, Edge

        # Get the node
        node_query = select(Node).where(Node.id == manifest.node_id)
        node_result = await db.execute(node_query)
        node = node_result.scalar_one_or_none()

        if node and node.parent_node_id:
            # Get the edge to parent
            edge_query = select(Edge).where(
                Edge.to_node_id == node.id,
                Edge.from_node_id == node.parent_node_id,
            )
            edge_result = await db.execute(edge_query)
            edge = edge_result.scalar_one_or_none()

            branch_info = {
                "parent_node_id": str(node.parent_node_id),
                "depth": node.depth,
                "intervention_type": edge.intervention_type if edge else None,
            }

    return ProvenanceResponse(
        run_id=manifest.run_id,
        manifest_hash=manifest.manifest_hash,
        seed=manifest.seed,
        created_at=manifest.created_at,
        created_by_user_id=manifest.created_by_user_id,
        source_run_id=manifest.source_run_id,
        node_id=manifest.node_id,
        project_id=manifest.project_id,
        is_reproduction=manifest.source_run_id is not None,
        code_version=manifest.versions_json.get("code_version", "unknown"),
        engine_version=manifest.versions_json.get("sim_engine_version", "unknown"),
        branch_info=branch_info,
    )


# =============================================================================
# GET /projects/{project_id}/runs/{run_id}/manifest/verify
# =============================================================================

@router.get(
    "/projects/{project_id}/runs/{run_id}/manifest/verify",
    response_model=VerifyManifestResponse,
    summary="Verify manifest integrity",
    description="Verify manifest integrity by recomputing the hash.",
)
async def verify_manifest_integrity(
    project_id: str,
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> VerifyManifestResponse:
    """
    Verify manifest integrity by recomputing the SHA256 hash.

    Returns whether the computed hash matches the stored hash.
    This can detect if manifest data was tampered with.
    """
    manifest_service = get_manifest_service(db)

    try:
        is_valid, stored_hash, computed_hash = await manifest_service.verify_manifest_integrity(
            run_id=UUID(run_id),
            tenant_id=tenant_ctx.tenant_id,
        )

        return VerifyManifestResponse(
            run_id=UUID(run_id),
            manifest_hash=stored_hash,
            computed_hash=computed_hash,
            is_valid=is_valid,
            verified_at=datetime.utcnow(),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


# =============================================================================
# GET /projects/{project_id}/manifests (List manifests by hash)
# =============================================================================

@router.get(
    "/projects/{project_id}/manifests",
    summary="Find manifests by hash",
    description="Find runs with a specific manifest hash (same configuration).",
)
async def find_manifests_by_hash(
    project_id: str,
    manifest_hash: str = Query(..., description="SHA256 manifest hash to search for"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> dict:
    """
    Find all runs with the same manifest hash.

    This is useful for finding runs with identical configurations.
    """
    from sqlalchemy import select
    from app.models.run_manifest import RunManifest

    query = select(RunManifest).where(
        RunManifest.manifest_hash == manifest_hash,
        RunManifest.tenant_id == tenant_ctx.tenant_id,
        RunManifest.project_id == UUID(project_id),
    ).order_by(RunManifest.created_at.desc())

    result = await db.execute(query)
    manifests = result.scalars().all()

    return {
        "manifest_hash": manifest_hash,
        "count": len(manifests),
        "runs": [
            {
                "run_id": str(m.run_id),
                "node_id": str(m.node_id) if m.node_id else None,
                "seed": m.seed,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "source_run_id": str(m.source_run_id) if m.source_run_id else None,
            }
            for m in manifests
        ],
    }

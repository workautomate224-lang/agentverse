"""
Evidence Pack API Endpoints
Reference: verification_checklist_v2.md §1

Provides endpoints for:
- Exporting Evidence Packs for runs and nodes
- Comparing runs for determinism verification
- Querying evidence signatures
"""

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
from app.schemas.evidence import (
    EvidencePack,
    EvidencePackResponse,
    DeterminismComparisonResult,
    ComparisonResponse,
    DeterminismSignature,
)
from app.services.evidence_service import get_evidence_service


# ============================================================================
# Request/Response Schemas
# ============================================================================

class CompareRunsRequest(BaseModel):
    """Request to compare two runs for determinism."""
    run_id_a: str = Field(..., description="First run ID")
    run_id_b: str = Field(..., description="Second run ID")


class SignatureResponse(BaseModel):
    """Response containing determinism signatures."""
    run_id: str
    signature: DeterminismSignature


# ============================================================================
# API Router
# ============================================================================

router = APIRouter()


@router.get(
    "/run/{run_id}",
    response_model=EvidencePackResponse,
    summary="Export Evidence Pack for a run",
)
async def get_evidence_pack_for_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> EvidencePackResponse:
    """
    Generate and export an Evidence Pack for a specific run.

    The Evidence Pack contains all proofs required for verification:
    - Artifact lineage (all version references)
    - Execution proof (loop counters, rule applications)
    - Determinism signatures (hashes for reproducibility)
    - Telemetry proof (data integrity)
    - Results proof (outcome verification)
    - Reliability proof (confidence metrics)
    - Audit proof (traceability)

    Reference: verification_checklist_v2.md §1.1
    """
    service = get_evidence_service(db)

    try:
        evidence_pack = await service.generate_evidence_pack_for_run(
            run_id=run_id,
            tenant_id=tenant_ctx.tenant_id,
        )

        warnings = []

        # Check for potential issues
        if evidence_pack.execution_proof.llm_calls_in_tick_loop > 0:
            warnings.append(
                f"LLM calls detected in tick loop ({evidence_pack.execution_proof.llm_calls_in_tick_loop}). "
                "This violates constraint C5."
            )

        if evidence_pack.execution_proof.loop_stage_counters.total_cycles() == 0:
            warnings.append(
                "No complete agent loop cycles recorded. "
                "Execution counters may not be instrumented."
            )

        return EvidencePackResponse(
            success=True,
            evidence_pack=evidence_pack,
            warnings=warnings,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate evidence pack: {str(e)}",
        )


@router.get(
    "/node/{node_id}",
    response_model=EvidencePackResponse,
    summary="Export Evidence Pack for a node",
)
async def get_evidence_pack_for_node(
    node_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> EvidencePackResponse:
    """
    Generate and export an Evidence Pack for a specific node.

    Uses the most recent run associated with the node.

    Reference: verification_checklist_v2.md §1.1
    """
    service = get_evidence_service(db)

    try:
        evidence_pack = await service.generate_evidence_pack_for_node(
            node_id=node_id,
            tenant_id=tenant_ctx.tenant_id,
        )

        warnings = []

        # Check for potential issues
        if evidence_pack.execution_proof.llm_calls_in_tick_loop > 0:
            warnings.append(
                f"LLM calls detected in tick loop ({evidence_pack.execution_proof.llm_calls_in_tick_loop}). "
                "This violates constraint C5."
            )

        return EvidencePackResponse(
            success=True,
            evidence_pack=evidence_pack,
            warnings=warnings,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate evidence pack: {str(e)}",
        )


@router.post(
    "/compare",
    response_model=ComparisonResponse,
    summary="Compare two runs for determinism",
)
async def compare_runs_for_determinism(
    request: CompareRunsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> ComparisonResponse:
    """
    Compare two runs to verify deterministic reproducibility.

    For two runs to be deterministic:
    - They must have the same config hash
    - They must have the same seed
    - They must produce the same result hash

    Reference: verification_checklist_v2.md §1.2
    """
    service = get_evidence_service(db)

    try:
        comparison = await service.compare_runs_for_determinism(
            run_id_a=request.run_id_a,
            run_id_b=request.run_id_b,
            tenant_id=tenant_ctx.tenant_id,
        )

        return ComparisonResponse(
            success=True,
            comparison=comparison,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare runs: {str(e)}",
        )


@router.get(
    "/signature/{run_id}",
    response_model=SignatureResponse,
    summary="Get determinism signatures for a run",
)
async def get_run_signatures(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> SignatureResponse:
    """
    Get just the determinism signatures for a run.

    Lighter weight than full Evidence Pack export.
    Useful for quick determinism checks.

    Reference: verification_checklist_v2.md §1.2
    """
    service = get_evidence_service(db)

    try:
        evidence_pack = await service.generate_evidence_pack_for_run(
            run_id=run_id,
            tenant_id=tenant_ctx.tenant_id,
        )

        return SignatureResponse(
            run_id=run_id,
            signature=evidence_pack.determinism_signature,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute signatures: {str(e)}",
        )


@router.get(
    "/verify/{run_id}",
    summary="Quick verification check for a run",
)
async def verify_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> dict:
    """
    Perform quick verification checks on a run.

    Returns pass/fail status for key verification criteria:
    - LLM calls in tick loop (must be 0)
    - Execution counters present
    - Telemetry integrity
    - Audit trail exists

    Reference: verification_checklist_v2.md §1
    """
    service = get_evidence_service(db)

    try:
        evidence_pack = await service.generate_evidence_pack_for_run(
            run_id=run_id,
            tenant_id=tenant_ctx.tenant_id,
        )

        # Perform verification checks
        checks = []

        # Check 1: No LLM in tick loop (C5)
        llm_in_loop = evidence_pack.execution_proof.llm_calls_in_tick_loop == 0
        checks.append({
            "name": "llm_calls_in_tick_loop",
            "status": "pass" if llm_in_loop else "fail",
            "value": evidence_pack.execution_proof.llm_calls_in_tick_loop,
            "expected": 0,
            "reference": "§1.4 / C5",
        })

        # Check 2: Execution counters present
        has_counters = evidence_pack.execution_proof.loop_stage_counters.total_cycles() > 0
        checks.append({
            "name": "execution_counters_present",
            "status": "pass" if has_counters else "blocked",
            "value": evidence_pack.execution_proof.loop_stage_counters.total_cycles(),
            "expected": "> 0",
            "reference": "§3.1",
        })

        # Check 3: Telemetry exists
        has_telemetry = bool(evidence_pack.telemetry_proof.telemetry_ref)
        checks.append({
            "name": "telemetry_exists",
            "status": "pass" if has_telemetry else "fail",
            "value": "present" if has_telemetry else "missing",
            "expected": "present",
            "reference": "§6.2",
        })

        # Check 4: Audit trail exists
        has_audit = evidence_pack.audit_proof.actions_recorded > 0
        checks.append({
            "name": "audit_trail_exists",
            "status": "pass" if has_audit else "blocked",
            "value": evidence_pack.audit_proof.actions_recorded,
            "expected": "> 0",
            "reference": "§8.3",
        })

        # Check 5: Ticks executed matches configured
        ticks_match = (
            evidence_pack.execution_proof.ticks_executed ==
            evidence_pack.execution_proof.ticks_configured
        )
        checks.append({
            "name": "ticks_completed",
            "status": "pass" if ticks_match else "fail",
            "value": evidence_pack.execution_proof.ticks_executed,
            "expected": evidence_pack.execution_proof.ticks_configured,
            "reference": "§3.1",
        })

        # Calculate overall status
        statuses = [c["status"] for c in checks]
        if "fail" in statuses:
            overall = "fail"
        elif "blocked" in statuses:
            overall = "blocked"
        else:
            overall = "pass"

        return {
            "run_id": run_id,
            "overall_status": overall,
            "checks": checks,
            "pass_count": sum(1 for c in checks if c["status"] == "pass"),
            "fail_count": sum(1 for c in checks if c["status"] == "fail"),
            "blocked_count": sum(1 for c in checks if c["status"] == "blocked"),
            "evidence_pack_id": evidence_pack.evidence_pack_id,
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify run: {str(e)}",
        )

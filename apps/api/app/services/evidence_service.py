"""
Evidence Service
Reference: verification_checklist_v2.md §1

Generates Evidence Packs and computes determinism signatures.
This is the core verification infrastructure.
"""

import hashlib
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.evidence import (
    EvidencePack,
    ArtifactLineage,
    ExecutionProof,
    DeterminismSignature,
    TelemetryProof,
    ResultsProof,
    ReliabilityProof,
    AuditProof,
    AntiLeakageProof,
    LoopStageCounters,
    RuleApplicationCount,
    EnginePathType,
    DeterminismComparisonResult,
)


class EvidenceService:
    """
    Service for generating Evidence Packs and computing signatures.

    Evidence Packs are the canonical proof bundles for verification.
    They contain all information needed to verify that:
    - The simulation was executed through the correct engine path
    - Results are deterministic and reproducible
    - No future data leakage occurred (for backtests)
    - Full audit trail exists
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # Hash Computation (§1.2)
    # =========================================================================

    @staticmethod
    def compute_hash(data: Any, algorithm: str = "sha256") -> str:
        """
        Compute hash of normalized data.
        Data is JSON-serialized with sorted keys for consistency.
        """
        if isinstance(data, str):
            normalized = data
        elif isinstance(data, bytes):
            normalized = data.decode('utf-8')
        else:
            # Sort keys and use consistent separators
            normalized = json.dumps(
                data,
                sort_keys=True,
                separators=(',', ':'),
                default=str,  # Handle datetime, UUID, etc.
            )

        if algorithm == "sha256":
            return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
        elif algorithm == "sha512":
            return hashlib.sha512(normalized.encode('utf-8')).hexdigest()
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

    def compute_run_config_hash(self, run_config: Dict[str, Any]) -> str:
        """
        Compute hash of normalized RunConfig.
        Excludes volatile fields (timestamps, IDs) that don't affect execution.
        """
        # Extract only the deterministic parts of config
        normalized_config = {
            "seed_config": run_config.get("seed_config", {}),
            "horizon": run_config.get("horizon") or run_config.get("max_ticks", 100),
            "tick_rate": run_config.get("tick_rate", 1),
            "scheduler_profile": run_config.get("scheduler_profile", {}),
            "scenario_patch": run_config.get("scenario_patch"),
            "max_agents": run_config.get("max_agents", 100),
            "versions": {
                "engine_version": run_config.get("versions", {}).get("engine_version", "0.1.0"),
                "ruleset_version": run_config.get("versions", {}).get("ruleset_version", "1.0.0"),
                "dataset_version": run_config.get("versions", {}).get("dataset_version", "1.0.0"),
            },
        }
        return self.compute_hash(normalized_config)

    def compute_result_hash(self, outcomes: Dict[str, Any]) -> str:
        """
        Compute hash of aggregated outcomes.
        """
        # Extract deterministic parts
        normalized_outcomes = {
            "primary_outcome": outcomes.get("primary_outcome"),
            "primary_outcome_probability": outcomes.get("primary_outcome_probability"),
            "outcome_distribution": outcomes.get("outcome_distribution", {}),
            "key_metrics": outcomes.get("key_metrics", []),
        }
        return self.compute_hash(normalized_outcomes)

    def compute_telemetry_hash(self, telemetry_summary: Dict[str, Any]) -> str:
        """
        Compute hash of telemetry summary.
        Full telemetry blob may be too large to hash directly.
        """
        # Create a summary that captures the essential telemetry structure
        summary = {
            "keyframe_count": telemetry_summary.get("keyframe_count", 0),
            "delta_count": telemetry_summary.get("delta_count", 0),
            "total_events": telemetry_summary.get("total_events", 0),
            "tick_count": telemetry_summary.get("tick_count", 0),
            "agent_count": telemetry_summary.get("agent_count", 0),
        }
        return self.compute_hash(summary)

    # =========================================================================
    # Evidence Pack Generation (§1.1)
    # =========================================================================

    async def generate_evidence_pack_for_run(
        self,
        run_id: str,
        tenant_id: str,
    ) -> EvidencePack:
        """
        Generate complete Evidence Pack for a run.
        """
        # Load run data
        run_data = await self._load_run_data(run_id, tenant_id)
        if not run_data:
            raise ValueError(f"Run not found: {run_id}")

        # Load node data if available
        node_data = None
        if run_data.get("node_id"):
            node_data = await self._load_node_data(run_data["node_id"], tenant_id)

        # Load run config
        config_data = await self._load_run_config(run_data.get("run_config_ref"))

        # Load LLM usage by phase (§1.4)
        llm_usage = await self._load_llm_usage_by_phase(run_id)

        # Build proofs
        artifact_lineage = self._build_artifact_lineage(run_data, node_data, config_data)
        execution_proof = self._build_execution_proof(run_data, config_data, llm_usage)
        determinism_signature = self._build_determinism_signature(run_data, config_data)
        telemetry_proof = self._build_telemetry_proof(run_data)
        results_proof = self._build_results_proof(run_data)
        reliability_proof = self._build_reliability_proof(run_data)
        audit_proof = await self._build_audit_proof(run_id, tenant_id)

        # Anti-leakage proof (if applicable)
        anti_leakage_proof = self._build_anti_leakage_proof(config_data, run_data)

        return EvidencePack(
            evidence_pack_id=f"ep-{uuid.uuid4().hex[:12]}",
            evidence_pack_version="1.0.0",
            generated_at=datetime.utcnow(),
            run_id=run_id,
            node_id=run_data.get("node_id"),
            artifact_lineage=artifact_lineage,
            execution_proof=execution_proof,
            determinism_signature=determinism_signature,
            telemetry_proof=telemetry_proof,
            results_proof=results_proof,
            reliability_proof=reliability_proof,
            audit_proof=audit_proof,
            anti_leakage_proof=anti_leakage_proof,
            tenant_id=tenant_id,
            project_id=run_data.get("project_id", ""),
        )

    async def generate_evidence_pack_for_node(
        self,
        node_id: str,
        tenant_id: str,
    ) -> EvidencePack:
        """
        Generate Evidence Pack for a node (aggregates all runs).
        """
        # Load node data
        node_data = await self._load_node_data(node_id, tenant_id)
        if not node_data:
            raise ValueError(f"Node not found: {node_id}")

        # Get the most recent run for this node
        run_refs = node_data.get("run_refs", [])
        if not run_refs:
            raise ValueError(f"Node has no runs: {node_id}")

        # Use the latest run
        latest_run_ref = run_refs[-1]
        latest_run_id = latest_run_ref.get("run_id")

        if not latest_run_id:
            raise ValueError(f"Invalid run reference in node: {node_id}")

        # Generate pack from the run
        pack = await self.generate_evidence_pack_for_run(latest_run_id, tenant_id)
        pack.node_id = node_id

        return pack

    # =========================================================================
    # Determinism Comparison (§1.2)
    # =========================================================================

    async def compare_runs_for_determinism(
        self,
        run_id_a: str,
        run_id_b: str,
        tenant_id: str,
    ) -> DeterminismComparisonResult:
        """
        Compare two runs to verify deterministic reproducibility.
        Same config + seed should produce identical hashes.
        """
        # Generate evidence packs for both runs
        pack_a = await self.generate_evidence_pack_for_run(run_id_a, tenant_id)
        pack_b = await self.generate_evidence_pack_for_run(run_id_b, tenant_id)

        sig_a = pack_a.determinism_signature
        sig_b = pack_b.determinism_signature

        # Compare hashes
        config_match = sig_a.run_config_hash == sig_b.run_config_hash
        result_match = sig_a.result_hash == sig_b.result_hash
        telemetry_match = sig_a.telemetry_hash == sig_b.telemetry_hash

        # Collect differences
        differences = []
        if not config_match:
            differences.append("run_config_hash mismatch")
        if not result_match:
            differences.append("result_hash mismatch")
        if not telemetry_match:
            differences.append("telemetry_hash mismatch")

        # Seeds must match for determinism comparison to be valid
        if sig_a.seed_used != sig_b.seed_used:
            differences.append(f"seeds differ: {sig_a.seed_used} vs {sig_b.seed_used}")

        # Overall determinism: configs match, seeds match, results match
        is_deterministic = config_match and result_match and (sig_a.seed_used == sig_b.seed_used)

        return DeterminismComparisonResult(
            run_id_a=run_id_a,
            run_id_b=run_id_b,
            config_hash_match=config_match,
            result_hash_match=result_match,
            telemetry_hash_match=telemetry_match,
            is_deterministic=is_deterministic,
            differences=differences,
        )

    # =========================================================================
    # Data Loading
    # =========================================================================

    async def _load_run_data(self, run_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Load run data from database."""
        query = text("""
            SELECT
                r.id, r.tenant_id, r.project_id, r.node_id, r.run_config_ref,
                r.status, r.timing, r.outputs, r.error, r.actual_seed,
                r.label, r.triggered_by, r.created_at, r.updated_at
            FROM runs r
            WHERE r.id = :run_id AND r.tenant_id = :tenant_id
        """)
        result = await self.db.execute(query, {"run_id": run_id, "tenant_id": tenant_id})
        row = result.fetchone()

        if not row:
            return None

        return {
            "id": str(row.id),
            "tenant_id": str(row.tenant_id),
            "project_id": str(row.project_id),
            "node_id": str(row.node_id) if row.node_id else None,
            "run_config_ref": str(row.run_config_ref) if row.run_config_ref else None,
            "status": row.status,
            "timing": row.timing or {},
            "outputs": row.outputs or {},
            "error": row.error,
            "actual_seed": row.actual_seed,
            "label": row.label,
            "triggered_by": row.triggered_by,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    async def _load_node_data(self, node_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Load node data from database."""
        query = text("""
            SELECT
                n.id, n.tenant_id, n.project_id, n.parent_node_id, n.depth,
                n.scenario_patch_ref, n.run_refs, n.aggregated_outcome, n.probability,
                n.cumulative_probability, n.confidence, n.telemetry_ref,
                n.is_baseline, n.created_at, n.updated_at
            FROM nodes n
            WHERE n.id = :node_id AND n.tenant_id = :tenant_id
        """)
        result = await self.db.execute(query, {"node_id": node_id, "tenant_id": tenant_id})
        row = result.fetchone()

        if not row:
            return None

        return {
            "id": str(row.id),
            "tenant_id": str(row.tenant_id),
            "project_id": str(row.project_id),
            "parent_node_id": str(row.parent_node_id) if row.parent_node_id else None,
            "depth": row.depth,
            "scenario_patch_ref": row.scenario_patch_ref,
            "run_refs": row.run_refs or [],
            "aggregated_outcome": row.aggregated_outcome,
            "probability": row.probability,
            "cumulative_probability": row.cumulative_probability,
            "confidence": row.confidence or {},
            "telemetry_ref": row.telemetry_ref,
            "is_baseline": row.is_baseline,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    async def _load_llm_usage_by_phase(self, run_id: str) -> Dict[str, int]:
        """
        Load LLM call counts by phase for a run.
        Reference: verification_checklist_v2.md §1.4 (LLM Usage Tracking)

        Returns:
            Dict with compilation and tick_loop counts
        """
        query = text("""
            SELECT
                phase,
                COUNT(*) as call_count
            FROM llm_calls
            WHERE run_id = :run_id
            GROUP BY phase
        """)
        result = await self.db.execute(query, {"run_id": run_id})
        rows = result.fetchall()

        counts = {
            "compilation": 0,
            "tick_loop": 0,
            "interactive": 0,  # Focus group dialogues (separate from sim engine)
            "other": 0,
        }

        for row in rows:
            phase = row.phase or "other"
            if phase in counts:
                counts[phase] = row.call_count
            else:
                counts["other"] += row.call_count

        return counts

    async def _load_run_config(self, config_id: Optional[str]) -> Dict[str, Any]:
        """Load run configuration from database."""
        if not config_id:
            return {}

        query = text("""
            SELECT
                versions, seed_config, horizon, tick_rate, scheduler_profile,
                logging_profile, scenario_patch, max_execution_time_ms, max_agents,
                cutoff_time, leakage_guard
            FROM run_configs
            WHERE id = :config_id
        """)
        result = await self.db.execute(query, {"config_id": config_id})
        row = result.fetchone()

        if not row:
            return {}

        return {
            "versions": row.versions or {},
            "seed_config": row.seed_config or {},
            "horizon": row.horizon,
            "tick_rate": row.tick_rate,
            "scheduler_profile": row.scheduler_profile or {},
            "logging_profile": row.logging_profile or {},
            "scenario_patch": row.scenario_patch,
            "max_execution_time_ms": row.max_execution_time_ms,
            "max_agents": row.max_agents,
            "cutoff_time": getattr(row, 'cutoff_time', None),
            "leakage_guard": getattr(row, 'leakage_guard', False),
        }

    # =========================================================================
    # Proof Building
    # =========================================================================

    def _build_artifact_lineage(
        self,
        run_data: Dict[str, Any],
        node_data: Optional[Dict[str, Any]],
        config_data: Dict[str, Any],
    ) -> ArtifactLineage:
        """Build artifact lineage from run/node data."""
        versions = config_data.get("versions", {})

        # Get telemetry ref from outputs
        outputs = run_data.get("outputs", {})
        telemetry_ref = outputs.get("telemetry_ref")
        reliability_ref = outputs.get("reliability")

        return ArtifactLineage(
            project_id=run_data.get("project_id", ""),
            project_version="1.0.0",  # TODO: Get from project
            node_id=run_data.get("node_id"),
            parent_node_id=node_data.get("parent_node_id") if node_data else None,
            node_depth=node_data.get("depth", 0) if node_data else 0,
            run_id=run_data.get("id"),
            run_config_id=run_data.get("run_config_ref"),
            engine_version=versions.get("engine_version", "0.1.0"),
            ruleset_version=versions.get("ruleset_version", "1.0.0"),
            dataset_version=versions.get("dataset_version", "1.0.0"),
            schema_version="1.0.0",
            telemetry_ref=telemetry_ref,
            reliability_ref=reliability_ref,
            created_at=run_data.get("created_at", datetime.utcnow()),
            completed_at=run_data.get("updated_at"),
        )

    def _build_execution_proof(
        self,
        run_data: Dict[str, Any],
        config_data: Dict[str, Any],
        llm_usage: Optional[Dict[str, int]] = None,
    ) -> ExecutionProof:
        """Build execution proof from run data."""
        timing = run_data.get("timing", {})
        outputs = run_data.get("outputs", {})

        # Extract execution counters if present
        execution_counters = outputs.get("execution_counters", {})
        loop_counters = execution_counters.get("loop_stage_counters", {})
        rule_counts = execution_counters.get("rule_application_counts", [])

        # Build loop stage counters
        loop_stage_counters = LoopStageCounters(
            observe=loop_counters.get("observe", 0),
            evaluate=loop_counters.get("evaluate", 0),
            decide=loop_counters.get("decide", 0),
            act=loop_counters.get("act", 0),
            update=loop_counters.get("update", 0),
        )

        # Build rule application counts
        rule_application_counts = [
            RuleApplicationCount(
                rule_name=rc.get("rule_name", "unknown"),
                rule_version=rc.get("rule_version", "1.0.0"),
                insertion_point=rc.get("insertion_point", "update"),
                application_count=rc.get("application_count", 0),
                agents_affected=rc.get("agents_affected", 0),
            )
            for rc in rule_counts
        ]

        # Determine engine path
        # TODO: Get from actual run mode once available
        engine_path = EnginePathType.SOCIETY

        # LLM usage from actual database queries (§1.4)
        # Prefer llm_usage from DB query, fallback to execution_counters
        llm_usage = llm_usage or {}
        llm_calls_in_tick_loop = llm_usage.get("tick_loop", execution_counters.get("llm_calls_in_tick_loop", 0))
        llm_calls_in_compilation = llm_usage.get("compilation", execution_counters.get("llm_calls_in_compilation", 0))

        return ExecutionProof(
            engine_path=engine_path,
            ticks_executed=timing.get("ticks_executed", 0),
            ticks_configured=config_data.get("horizon", 100),
            agent_count=outputs.get("outcomes", {}).get("key_metrics", [{}])[1].get("value", 0)
                if len(outputs.get("outcomes", {}).get("key_metrics", [])) > 1 else 0,
            agent_steps_executed=execution_counters.get("agent_steps_executed", 0),
            loop_stage_counters=loop_stage_counters,
            rule_application_counts=rule_application_counts,
            llm_calls_in_tick_loop=llm_calls_in_tick_loop,
            llm_calls_in_compilation=llm_calls_in_compilation,
            scheduler_profile=config_data.get("scheduler_profile", {}).get("name", "default"),
            partitions_count=execution_counters.get("partitions_count", 0),
            batches_count=execution_counters.get("batches_count", 0),
            backpressure_events=execution_counters.get("backpressure_events", 0),
        )

    def _build_determinism_signature(
        self,
        run_data: Dict[str, Any],
        config_data: Dict[str, Any],
    ) -> DeterminismSignature:
        """Build determinism signatures from run data."""
        outputs = run_data.get("outputs", {})
        outcomes = outputs.get("outcomes", {})
        telemetry_ref = outputs.get("telemetry_ref", {})

        return DeterminismSignature(
            run_config_hash=self.compute_run_config_hash(config_data),
            result_hash=self.compute_result_hash(outcomes),
            telemetry_hash=self.compute_telemetry_hash(telemetry_ref),
            seed_used=run_data.get("actual_seed", 42),
            algorithm="sha256",
            computed_at=datetime.utcnow(),
        )

    def _build_telemetry_proof(self, run_data: Dict[str, Any]) -> TelemetryProof:
        """Build telemetry proof from run data."""
        outputs = run_data.get("outputs", {})
        telemetry_ref = outputs.get("telemetry_ref", {})

        return TelemetryProof(
            telemetry_ref=telemetry_ref,
            keyframe_count=telemetry_ref.get("keyframe_count", 0),
            delta_count=telemetry_ref.get("delta_count", 0),
            total_events=telemetry_ref.get("total_events", 0),
            telemetry_hash=self.compute_telemetry_hash(telemetry_ref),
            is_complete=True,
            replay_degraded=False,
        )

    def _build_results_proof(self, run_data: Dict[str, Any]) -> ResultsProof:
        """Build results proof from run data."""
        outputs = run_data.get("outputs", {})
        outcomes = outputs.get("outcomes", {})

        return ResultsProof(
            outcomes_hash=self.compute_result_hash(outcomes),
            primary_outcome=outcomes.get("primary_outcome", "unknown"),
            primary_probability=outcomes.get("primary_outcome_probability", 0.0),
            outcome_distribution=outcomes.get("outcome_distribution", {}),
            key_metrics=outcomes.get("key_metrics", []),
            variance_metrics=outcomes.get("variance_metrics"),
        )

    def _build_reliability_proof(
        self,
        run_data: Dict[str, Any],
        stability_runs: Optional[Dict[int, Dict[str, float]]] = None,
        reference_distribution: Optional[Dict[str, float]] = None,
    ) -> ReliabilityProof:
        """
        Build reliability proof from run data.

        §7.1-7.4: Complete reliability assessment including:
        - Calibration bounding status
        - Stability variance across seeds
        - Drift detection vs reference
        """
        outputs = run_data.get("outputs", {})
        reliability = outputs.get("reliability", {})

        confidence_score = reliability.get("confidence", 0.5)

        # Determine confidence level
        if confidence_score >= 0.8:
            confidence_level = "high"
        elif confidence_score >= 0.6:
            confidence_level = "medium"
        elif confidence_score >= 0.4:
            confidence_level = "low"
        else:
            confidence_level = "very_low"

        # §7.2 - Check calibration bounded status
        calibration_bounded = reliability.get("calibration_bounded", False)

        # §7.3 - Stability: compute if multiple runs provided
        seeds_tested = [run_data.get("actual_seed", 42)]
        stability_variance = reliability.get("stability")

        if stability_runs and len(stability_runs) > 1:
            seeds_tested = list(stability_runs.keys())
            # Compute variance across seeds
            values = [
                outcome.get("primary_probability", 0.0)
                for outcome in stability_runs.values()
            ]
            if len(values) > 1:
                mean = sum(values) / len(values)
                stability_variance = sum((v - mean) ** 2 for v in values) / len(values)

        # §7.4 - Drift detection
        drift_score = None
        drift_detected = False

        if reference_distribution:
            current_distribution = outputs.get("outcome_distribution", {})
            if current_distribution:
                # Compute drift score (average shift)
                total_shift = 0.0
                features_shifted = 0
                all_features = set(reference_distribution.keys()) | set(current_distribution.keys())

                for feature in all_features:
                    ref_value = reference_distribution.get(feature, 0.0)
                    curr_value = current_distribution.get(feature, 0.0)
                    if ref_value > 0:
                        shift = abs(curr_value - ref_value) / ref_value
                    else:
                        shift = abs(curr_value) if curr_value > 0 else 0.0
                    total_shift += shift
                    if shift > 0.15:  # Drift threshold
                        features_shifted += 1

                drift_score = total_shift / len(all_features) if all_features else 0.0
                drift_detected = features_shifted > 0 or drift_score > 0.15

        return ReliabilityProof(
            confidence_score=confidence_score,
            confidence_level=confidence_level,
            calibration_score=reliability.get("calibration"),
            calibration_bounded=calibration_bounded,
            stability_variance=stability_variance,
            seeds_tested=seeds_tested,
            drift_score=drift_score,
            drift_detected=drift_detected,
            data_gaps=reliability.get("data_gaps", []),
        )

    async def _build_audit_proof(self, run_id: str, tenant_id: str) -> AuditProof:
        """Build audit proof from audit logs."""
        # Query audit logs for this run
        query = text("""
            SELECT id, user_id, action
            FROM audit_logs
            WHERE resource_id = :run_id
            AND (organization_id = :tenant_id OR organization_id IS NULL)
            ORDER BY created_at
        """)
        result = await self.db.execute(query, {"run_id": run_id, "tenant_id": tenant_id})
        rows = result.fetchall()

        audit_log_refs = [str(row.id) for row in rows]
        actor_id = str(rows[0].user_id) if rows and rows[0].user_id else None

        return AuditProof(
            audit_log_refs=audit_log_refs,
            actions_recorded=len(audit_log_refs),
            actor_id=actor_id,
            actor_type="user" if actor_id else "system",
            tenant_id=tenant_id,
        )

    def _build_anti_leakage_proof(
        self,
        config_data: Dict[str, Any],
        run_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[AntiLeakageProof]:
        """Build anti-leakage proof if applicable."""
        cutoff_time = config_data.get("cutoff_time")
        leakage_guard = config_data.get("leakage_guard", False)

        if not cutoff_time and not leakage_guard:
            return None

        # Get leakage guard stats from run outputs
        blocked_attempts = 0
        dataset_filtered = cutoff_time is not None
        leakage_detected = False
        leakage_details = None

        if run_data:
            outputs = run_data.get("outputs", {})
            leakage_stats = outputs.get("leakage_guard_stats")
            if leakage_stats:
                blocked_attempts = leakage_stats.get("blocked_attempts", 0)
                if blocked_attempts > 0:
                    leakage_detected = True
                    leakage_details = (
                        f"Blocked {blocked_attempts} access attempts. "
                        f"Types: {leakage_stats.get('blocked_by_type', {})}"
                    )

        # Parse cutoff_time if string
        if isinstance(cutoff_time, str):
            try:
                from datetime import datetime
                cutoff_time = datetime.fromisoformat(cutoff_time.replace('Z', '+00:00'))
            except ValueError:
                cutoff_time = None

        return AntiLeakageProof(
            cutoff_time=cutoff_time,
            leakage_guard_enabled=leakage_guard,
            blocked_access_attempts=blocked_attempts,
            dataset_filtered=dataset_filtered,
            leakage_detected=leakage_detected,
            leakage_details=leakage_details,
        )


# =============================================================================
# Factory Function
# =============================================================================

def get_evidence_service(db: AsyncSession) -> EvidenceService:
    """Get Evidence Service instance."""
    return EvidenceService(db)

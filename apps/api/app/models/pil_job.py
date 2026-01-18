"""
PIL Job Model (blueprint.md §5, §10 Phase B)
Reference: blueprint.md §5 Async AI Loading Architecture

Project Intelligence Layer (PIL) background job system.
All AI work runs as background jobs with:
- Progress reporting
- Persistent status
- Artifact creation
- Non-blocking UI

This extends the existing Celery infrastructure with a database-backed
job tracking system for the PIL orchestration layer.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.project_spec import ProjectSpec
    from app.models.user import User


# ============================================================================
# Enums (blueprint.md §5.3)
# ============================================================================

class PILJobStatus(str, Enum):
    """Job state machine (blueprint.md §5.3)"""
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL = "partial"  # Streaming incremental results


class PILJobType(str, Enum):
    """Types of PIL background jobs"""
    # Goal Analysis (blueprint.md §4.2)
    GOAL_ANALYSIS = "goal_analysis"
    CLARIFICATION_GENERATE = "clarification_generate"
    BLUEPRINT_BUILD = "blueprint_build"

    # Blueprint v2 (Slice 2A) - Final Blueprint Build after Q&A completion
    FINAL_BLUEPRINT_BUILD = "final_blueprint_build"

    # Slot Processing (blueprint.md §6.3)
    SLOT_VALIDATION = "slot_validation"
    SLOT_SUMMARIZATION = "slot_summarization"
    SLOT_ALIGNMENT_SCORING = "slot_alignment_scoring"
    SLOT_COMPILATION = "slot_compilation"

    # Task Processing
    TASK_VALIDATION = "task_validation"
    TASK_GUIDANCE_GENERATE = "task_guidance_generate"

    # Project Genesis (Slice 2C) - Generate project-specific guidance
    PROJECT_GENESIS = "project_genesis"

    # Calibration & Quality (blueprint.md §3.1.E)
    CALIBRATION_CHECK = "calibration_check"
    BACKTEST_VALIDATION = "backtest_validation"
    RELIABILITY_ANALYSIS = "reliability_analysis"

    # AI Research (blueprint.md §9)
    AI_RESEARCH = "ai_research"
    AI_GENERATION = "ai_generation"


class PILJobPriority(str, Enum):
    """Job priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


# ============================================================================
# PILJob Model (blueprint.md §5)
# ============================================================================

class PILJob(Base):
    """
    PIL Background Job - tracks async AI work with progress.

    Reference: blueprint.md §5

    Features:
    - Non-blocking: users can navigate while jobs run
    - Progress reporting with stages and percentage
    - Artifact creation on completion
    - Retry support
    - Notification on completion
    """
    __tablename__ = "pil_jobs"

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
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project_specs.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    blueprint_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blueprints.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Job type and identification
    job_type: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    job_name: Mapped[str] = mapped_column(String(255), nullable=False)
    priority: Mapped[str] = mapped_column(
        String(20), default=PILJobPriority.NORMAL.value, nullable=False
    )

    # Celery task tracking
    celery_task_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )

    # Status (blueprint.md §5.3)
    status: Mapped[str] = mapped_column(
        String(50), default=PILJobStatus.QUEUED.value, nullable=False, index=True
    )

    # Progress (blueprint.md §5.4)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stage_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    eta_hint: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    stages_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stages_total: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Input/Output
    input_params: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )

    # Artifact references (blueprint.md §5.6)
    artifact_ids: Mapped[Optional[List[str]]] = mapped_column(
        JSONB, nullable=True
    )  # List of created artifact UUIDs
    slot_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    task_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Retry tracking
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    retry_delay_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)

    # User tracking
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow,
        nullable=False
    )

    # Notification
    notification_sent: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Relationships
    project: Mapped[Optional["ProjectSpec"]] = relationship(
        "ProjectSpec",
        foreign_keys=[project_id]
    )
    creator: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by]
    )

    def __repr__(self) -> str:
        return f"<PILJob {self.id} type={self.job_type} status={self.status}>"

    def to_dict(self) -> Dict[str, Any]:
        """Return dictionary representation."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "project_id": str(self.project_id) if self.project_id else None,
            "blueprint_id": str(self.blueprint_id) if self.blueprint_id else None,
            "job_type": self.job_type,
            "job_name": self.job_name,
            "priority": self.priority,
            "celery_task_id": self.celery_task_id,
            "status": self.status,
            "progress_percent": self.progress_percent,
            "stage_name": self.stage_name,
            "eta_hint": self.eta_hint,
            "stages_completed": self.stages_completed,
            "stages_total": self.stages_total,
            "input_params": self.input_params,
            "result": self.result,
            "error_message": self.error_message,
            "artifact_ids": self.artifact_ids,
            "slot_id": self.slot_id,
            "task_id": self.task_id,
            "retry_count": self.retry_count,
            "created_by": str(self.created_by) if self.created_by else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def update_progress(
        self,
        percent: int,
        stage: Optional[str] = None,
        eta: Optional[str] = None
    ):
        """Update job progress (blueprint.md §5.4)"""
        self.progress_percent = min(100, max(0, percent))
        if stage:
            self.stage_name = stage
        if eta:
            self.eta_hint = eta
        self.updated_at = datetime.utcnow()

    def mark_running(self, celery_task_id: Optional[str] = None):
        """Mark job as running"""
        self.status = PILJobStatus.RUNNING.value
        self.started_at = datetime.utcnow()
        if celery_task_id:
            self.celery_task_id = celery_task_id
        self.updated_at = datetime.utcnow()

    def mark_succeeded(self, result: Optional[Dict[str, Any]] = None):
        """Mark job as succeeded"""
        self.status = PILJobStatus.SUCCEEDED.value
        self.progress_percent = 100
        self.completed_at = datetime.utcnow()
        if result:
            self.result = result
        self.updated_at = datetime.utcnow()

    def mark_failed(self, error: str, details: Optional[Dict[str, Any]] = None):
        """Mark job as failed"""
        self.status = PILJobStatus.FAILED.value
        self.error_message = error
        if details:
            self.error_details = details
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def can_retry(self) -> bool:
        """Check if job can be retried"""
        return (
            self.status == PILJobStatus.FAILED.value and
            self.retry_count < self.max_retries
        )


# ============================================================================
# PILArtifact Model (blueprint.md §5.6)
# ============================================================================

class PILArtifact(Base):
    """
    PIL Artifact - stores job outputs (summaries, validations, etc.)

    Reference: blueprint.md §5.6

    Artifacts are linked to:
    - project_id
    - blueprint_version
    - slot_id / task_id (if applicable)
    """
    __tablename__ = "pil_artifacts"

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
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project_specs.id", ondelete="CASCADE"),
        nullable=True,  # Allow null for pre-project goal analysis
        index=True
    )

    # Blueprint version tracking (blueprint.md §1.1)
    blueprint_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blueprints.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    blueprint_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Artifact type
    artifact_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    artifact_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Linked entities
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pil_jobs.id", ondelete="SET NULL"),
        nullable=True
    )
    slot_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    task_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # Content
    content: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    content_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Scoring (blueprint.md §6.3)
    alignment_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    validation_passed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<PILArtifact {self.id} type={self.artifact_type}>"

    def to_dict(self) -> Dict[str, Any]:
        """Return dictionary representation."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "project_id": str(self.project_id),
            "blueprint_id": str(self.blueprint_id) if self.blueprint_id else None,
            "blueprint_version": self.blueprint_version,
            "artifact_type": self.artifact_type,
            "artifact_name": self.artifact_name,
            "job_id": str(self.job_id) if self.job_id else None,
            "slot_id": self.slot_id,
            "task_id": self.task_id,
            "content": self.content,
            "content_text": self.content_text,
            "alignment_score": self.alignment_score,
            "quality_score": self.quality_score,
            "validation_passed": self.validation_passed,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ============================================================================
# Artifact Types
# ============================================================================

class ArtifactType(str, Enum):
    """Types of PIL artifacts"""
    # Goal Analysis
    GOAL_SUMMARY = "goal_summary"
    CLARIFICATION_QUESTIONS = "clarification_questions"
    BLUEPRINT_PREVIEW = "blueprint_preview"

    # Slot Processing
    SLOT_VALIDATION_REPORT = "slot_validation_report"
    SLOT_SUMMARY = "slot_summary"
    SLOT_ALIGNMENT_REPORT = "slot_alignment_report"
    SLOT_COMPILED_OUTPUT = "slot_compiled_output"

    # Task Processing
    TASK_GUIDANCE = "task_guidance"
    TASK_VALIDATION_REPORT = "task_validation_report"

    # Project Genesis (Slice 2C)
    PROJECT_GUIDANCE_PACK = "project_guidance_pack"

    # Calibration
    CALIBRATION_REPORT = "calibration_report"
    BACKTEST_REPORT = "backtest_report"
    RELIABILITY_REPORT = "reliability_report"

    # AI Research
    RESEARCH_RESULT = "research_result"
    GENERATED_DATA = "generated_data"

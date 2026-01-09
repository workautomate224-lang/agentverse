"""
Business Logic Services
Reference: project.md §5-8
"""

from app.services.openrouter import OpenRouterService
from app.services.simulation import SimulationService
from app.services.persona import PersonaGenerator
from app.services.census import CensusDataService, get_census_service
from app.services.storage import (
    StorageService,
    StorageBackend,
    LocalStorageBackend,
    S3StorageBackend,
    StorageRef,
    StorageError,
    StorageNotFoundError,
    get_storage_service,
    create_storage_service,
)
from app.services.audit import (
    # New spec-compliant audit (project.md §8)
    TenantAuditLogger,
    TenantAuditAction,
    AuditResourceType,
    AuditActorType,
    AuditActor,
    AuditChange,
    AuditEntry,
    get_tenant_audit_logger,
    audit_create,
    audit_update,
    audit_delete,
    # Legacy (backward compatible)
    AuditService,
)
# Node/Universe Map Service (project.md §6.7)
from app.services.node_service import (
    NodeService,
    get_node_service,
    # DTOs
    ArtifactRef,
    AggregatedOutcome,
    NodeConfidence,
    EdgeIntervention,
    EdgeExplanation,
    PathAnalysis,
    UniverseMapState,
    CreateNodeInput,
    CreateEdgeInput,
    ForkNodeInput,
)
# Telemetry Service (project.md §6.8)
from app.services.telemetry import (
    TelemetryService,
    TelemetryWriter,
    TelemetryBlob,
    TelemetryKeyframe,
    TelemetryDelta,
    TelemetryIndex,
    TelemetrySlice,
    TelemetryQueryParams,
    TelemetryVersion,
    get_telemetry_service,
    create_telemetry_writer,
)
# Simulation Orchestrator (Phase 1 Integration)
from app.services.simulation_orchestrator import (
    SimulationOrchestrator,
    SimulationMode,
    RunConfigInput,
    CreateRunInput,
    SimulationResult,
    SimulationProgress,
    get_simulation_orchestrator,
)
# Persona Expansion Service (project.md §6.2, C5 compliant)
from app.services.persona_expansion import (
    PersonaExpansionService,
    ExpandedPersona,
    PerceptionWeights,
    BiasParameters,
    ActionPriors,
    PersonaSource,
    PersonaExpansionLevel,
    get_persona_expansion_service,
)
# Event Compiler (project.md §11 Phase 4, C5 compliant)
from app.services.event_compiler import (
    EventCompiler,
    CompilationResult,
    IntentType,
    PromptScope,
    ExtractedIntent,
    SubEffect,
    VariableMapping,
    CandidateScenario,
    ScenarioCluster,
    CausalExplanation,
    get_event_compiler,
    compile_prompt,
)
# Target Mode Service (project.md §11 Phase 5)
from app.services.target_mode import (
    TargetModeService,
    TargetPersonaCompiler,
    ActionSpace,
    ConstraintChecker,
    PathPlanner,
    PathNodeBridge,
    TargetModeTelemetry,
    get_target_mode_service,
)

__all__ = [
    "OpenRouterService",
    "SimulationService",
    "PersonaGenerator",
    "CensusDataService",
    "get_census_service",
    # Storage (project.md §5.4, §8.1)
    "StorageService",
    "StorageBackend",
    "LocalStorageBackend",
    "S3StorageBackend",
    "StorageRef",
    "StorageError",
    "StorageNotFoundError",
    "get_storage_service",
    "create_storage_service",
    # Audit (project.md §8)
    "TenantAuditLogger",
    "TenantAuditAction",
    "AuditResourceType",
    "AuditActorType",
    "AuditActor",
    "AuditChange",
    "AuditEntry",
    "get_tenant_audit_logger",
    "audit_create",
    "audit_update",
    "audit_delete",
    "AuditService",  # Legacy
    # Node/Universe Map (project.md §6.7)
    "NodeService",
    "get_node_service",
    "ArtifactRef",
    "AggregatedOutcome",
    "NodeConfidence",
    "EdgeIntervention",
    "EdgeExplanation",
    "PathAnalysis",
    "UniverseMapState",
    "CreateNodeInput",
    "CreateEdgeInput",
    "ForkNodeInput",
    # Telemetry (project.md §6.8)
    "TelemetryService",
    "TelemetryWriter",
    "TelemetryBlob",
    "TelemetryKeyframe",
    "TelemetryDelta",
    "TelemetryIndex",
    "TelemetrySlice",
    "TelemetryQueryParams",
    "TelemetryVersion",
    "get_telemetry_service",
    "create_telemetry_writer",
    # Simulation Orchestrator (Phase 1 Integration)
    "SimulationOrchestrator",
    "SimulationMode",
    "RunConfigInput",
    "CreateRunInput",
    "SimulationResult",
    "SimulationProgress",
    "get_simulation_orchestrator",
    # Persona Expansion (project.md §6.2)
    "PersonaExpansionService",
    "ExpandedPersona",
    "PerceptionWeights",
    "BiasParameters",
    "ActionPriors",
    "PersonaSource",
    "PersonaExpansionLevel",
    "get_persona_expansion_service",
    # Event Compiler (project.md §11 Phase 4)
    "EventCompiler",
    "CompilationResult",
    "IntentType",
    "PromptScope",
    "ExtractedIntent",
    "SubEffect",
    "VariableMapping",
    "CandidateScenario",
    "ScenarioCluster",
    "CausalExplanation",
    "get_event_compiler",
    "compile_prompt",
    # Target Mode (project.md §11 Phase 5)
    "TargetModeService",
    "TargetPersonaCompiler",
    "ActionSpace",
    "ConstraintChecker",
    "PathPlanner",
    "PathNodeBridge",
    "TargetModeTelemetry",
    "get_target_mode_service",
]

/**
 * AgentVerse Data Contracts
 *
 * Shared type definitions for the Future Predictive AI Platform.
 * These contracts are the single source of truth for data structures
 * shared between frontend and backend.
 *
 * Reference: project.md §6 (Data contracts)
 */

// ============================================================================
// Common Types (shared across all contracts)
// ============================================================================

export {
  // Versioning
  ArtifactVersion,

  // Timestamps
  Timestamps,

  // Tenant scoping
  TenantScoped,

  // User/permissions
  UserRole,
  UserPermissions,

  // Status enums
  RunStatus,
  ConfidenceLevel,
  PrivacyLevel,

  // Prediction cores
  PredictionCore,

  // References
  ArtifactRef,

  // Pagination
  PaginatedResponse,

  // API wrappers
  ApiResponse,
  ApiError,
} from './common';

// ============================================================================
// Project Types (§6.1)
// ============================================================================

export {
  // Domain templates
  DomainTemplate,

  // Policy flags
  PolicyFlags,

  // Output metrics
  OutputMetricType,
  OutputMetricsConfig,

  // Main types
  ProjectSpec,
  ProjectSummary,

  // DTOs
  CreateProjectInput,
  UpdateProjectInput,
} from './project';

// ============================================================================
// Persona Types (§6.2)
// ============================================================================

export {
  // Source
  PersonaSource,

  // Demographics
  Demographics,

  // Preferences
  PreferencesVector,

  // Perception
  PerceptionWeights,

  // Biases
  BiasParameters,

  // Action priors
  ActionPriors,

  // Evidence
  EvidenceRef,

  // Main types
  Persona,
  PersonaSegment,
  PersonaSummary,

  // DTOs
  CreatePersonaInput,
  ImportPersonasInput,
  PersonaValidationResult,
} from './persona';

// ============================================================================
// Agent Types (§6.3)
// ============================================================================

export {
  // Social
  SocialEdge,

  // Location
  AgentLocation,

  // Memory
  MemoryState,

  // State
  AgentStateVector,

  // Main types
  Agent,
  AgentSegment,
  AgentAction,
  AgentSnapshot,
  Target,

  // DTOs
  CreateAgentInput,
  AgentStateUpdate,
} from './agent';

// ============================================================================
// Event Script Types (§6.4)
// ============================================================================

export {
  // Event classification
  EventType,

  // Scope
  EventScope,

  // Intensity
  IntensityProfileType,
  IntensityProfile,

  // Deltas
  EnvironmentDelta,
  PerceptionDelta,
  EventDeltas,

  // Uncertainty
  EventUncertainty,

  // Provenance
  EventProvenance,

  // Main types
  EventScript,
  EventBundle,

  // DTOs
  CreateEventScriptInput,
  CompileEventInput,
  CompileEventOutput,
  EventValidationResult,
} from './event-script';

// ============================================================================
// Run Types (§6.5, §6.6)
// ============================================================================

export {
  // Seed strategy
  SeedStrategy,
  SeedConfig,

  // Logging
  LoggingProfile,

  // Scheduler
  SchedulerType,
  SchedulerProfile,

  // Scenario
  ScenarioPatch,

  // RunConfig
  RunConfig,

  // Run timing
  RunTiming,

  // Run outputs
  RunOutputs,

  // Run error
  RunError,

  // Main types
  Run,
  RunResults,
  RunSummary,

  // DTOs
  CreateRunConfigInput,
  SubmitRunInput,
  RunProgressUpdate,
} from './run';

// ============================================================================
// Node & Edge Types (§6.7)
// ============================================================================

export {
  // Outcomes
  AggregatedOutcome,

  // Confidence
  NodeConfidence,

  // Main types
  Node,
  Edge,
  NodeCluster,
  UniverseMapState,

  // Intervention
  EdgeIntervention,

  // Explanation
  EdgeExplanation,

  // Summaries
  NodeSummary,
  EdgeSummary,

  // Path analysis
  PathAnalysis,
  MostLikelyPaths,

  // DTOs
  CreateNodeInput,
  CreateEdgeInput,
  ExpandNodeInput,
  ClusterNodesInput,
} from './node';

// ============================================================================
// Telemetry Types (§6.8)
// ============================================================================

export {
  // Keyframes
  WorldKeyframe,
  RegionKeyframe,
  AgentKeyframe,

  // Deltas
  DeltaType,
  TelemetryDelta,
  DeltaStream,

  // Metrics
  MetricTimeSeries,

  // Events
  EventOccurrence,

  // Index
  TelemetryIndex,

  // Main types
  Telemetry,
  TelemetrySummary,

  // Query interfaces
  TelemetryQueryByTick,
  TelemetryQueryByRange,
  TelemetryQueryByRegion,
  TelemetryQueryByAgent,
  TelemetryQueryMetric,

  // Response types
  TelemetrySlice,
  TelemetryPlaybackState,
} from './telemetry';

// ============================================================================
// Reliability Types (§7.1)
// ============================================================================

export {
  // Calibration
  CalibrationScore,

  // Stability
  StabilityScore,

  // Sensitivity
  SensitivityFactor,
  SensitivitySummary,

  // Drift
  DriftSeverity,
  DriftIndicator,
  DriftStatus,

  // Data gaps
  DataGap,
  DataGapsSummary,

  // Confidence
  ConfidenceBreakdown,

  // Main types
  ReliabilityReport,
  ReliabilitySummary,
  ReliabilityComparison,

  // Anti-leakage
  TimeCutoffValidation,
  LeakageCheck,

  // DTOs
  ComputeReliabilityInput,
  UpdateCalibrationInput,
} from './reliability';

// ============================================================================
// Versioning Utilities
// ============================================================================

export {
  // Current versions
  CURRENT_ENGINE_VERSION,
  CURRENT_RULESET_VERSION,
  CURRENT_SCHEMA_VERSION,
  DEFAULT_DATASET_VERSION,

  // Version creation
  createCurrentVersion,
  mergeWithCurrentVersion,

  // Parsing
  ParsedVersion,
  parseVersion,
  formatVersion,

  // Comparison
  VersionComparison,
  compareVersions,
  areVersionsCompatible,
  isVersionCompatibleOrNewer,

  // Validation
  VersionValidationResult,
  validateVersionString,
  validateArtifactVersion,

  // Drift detection
  VersionDrift,
  detectVersionDrift,

  // Fingerprinting
  createVersionFingerprint,
  parseVersionFingerprint,

  // Migration
  MigrationPath,
  getMigrationPath,
} from './versioning';

// ============================================================================
// RNG Policy & Utilities
// ============================================================================

export {
  // Constants
  MAX_SEED,
  MIN_SEED,
  DEFAULT_SEED,
  DEFAULT_MULTI_SEED_COUNT,
  MAX_SEEDS_PER_RUN,

  // Validation
  SeedValidationResult,
  validateSeed,
  validateSeeds,

  // Generation
  generateRandomSeed,
  generateRandomSeeds,
  generateSubSeeds,

  // Derivation
  deriveSeed,
  deriveTickSeed,
  deriveAgentTickSeed,

  // RNG streams
  RNGDomain,
  RNGStreamDescriptor,
  createRNGStreamDescriptor,

  // Determinism checks
  DeterminismCheckResult,
  validateDeterminismConfig,

  // Serialization
  serializeSeedConfig,
  deserializeSeedConfig,

  // Golden seeds for testing
  GOLDEN_SEEDS,
  GoldenSeedName,
  getGoldenSeed,
} from './rng';

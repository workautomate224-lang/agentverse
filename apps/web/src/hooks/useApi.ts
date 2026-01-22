'use client';

import { useQuery, useMutation, useQueryClient, useInfiniteQuery } from '@tanstack/react-query';
import { useSession } from 'next-auth/react';
import { useEffect, useState, useCallback } from 'react';
import api, {
  Project,
  ProjectCreate,
  ProjectUpdate,
  Scenario,
  ScenarioCreate,
  ScenarioUpdate,
  SimulationRun,
  SimulationRunCreate,
  SimulationStats,
  DataSource,
  DataSourceCreate,
  DataSourceUpdate,
  DemographicDistribution,
  CensusProfile,
  RegionalProfile,
  PersonaTemplate,
  PersonaTemplateCreate,
  PersonaRecord,
  GeneratePersonasRequest,
  GeneratePersonasResponse,
  FileAnalysisResponse,
  UploadResult,
  AIResearchRequest,
  AIResearchJob,
  RegionInfo,
  Benchmark,
  BenchmarkCreate,
  ValidationRecord,
  ValidationCreate,
  AccuracyStats,
  ProductCreate,
  ProductUpdate,
  GenerateAIContentRequest,
  // Prediction types
  PredictionCreate,
  PredictionResponse,
  PredictionListResponse,
  PredictionResults,
  PredictionStatus,
  CalibrationRequest,
  CalibrationStatus,
  MarlTrainingRequest,
  PredictionAnalyticsOverview,
  AccuracyAnalytics,
  // Spec-compliant types (project.md §6)
  SpecRunStatus,
  SpecRun,
  SpecRunConfig,
  SpecRunResults,
  RunSummary,
  RunProgressUpdate,
  SubmitRunInput,
  CreateRunConfigInput,
  SpecNode,
  SpecEdge,
  NodeSummary,
  EdgeSummary,
  UniverseMapState,
  NodeCluster,
  PathAnalysis,
  ForkNodeInput,
  CompareNodesResponse,
  TelemetryIndex,
  TelemetrySlice,
  TelemetrySummary,
  WorldKeyframe,
  TelemetryDelta,
  MetricTimeSeries,
  EventOccurrence,
  ProjectSpec,
  ProjectSpecCreate,
  ProjectSpecUpdate,
  ProjectSpecStats,
  // Target Mode types (project.md §11 Phase 5)
  TargetPersona,
  TargetPersonaCreate,
  TargetPlanRequest,
  PlanResult,
  PathCluster,
  TargetPath,
  ExpandClusterRequest,
  BranchToNodeRequest,
  TargetPlanListItem,
  ActionCatalog,
  ActionCatalogListItem,
  PlanStatus,
  PathStatus,
  // 2D Replay types (project.md §11 Phase 8)
  LoadReplayRequest,
  ReplayTimeline,
  ReplayWorldState,
  ReplayChunk,
  ReplayAgentHistory,
  ReplayTickEvents,
  // Export types (Interaction_design.md §5.19)
  ExportType,
  ExportFormat,
  ExportPrivacy,
  ExportStatus,
  ExportRequest,
  ExportJob,
  ExportListItem,
  // Hybrid Mode types (project.md §11 Phase 6)
  HybridRunRequest,
  HybridRunResult,
  HybridRunListItem,
  HybridRunProgress,
  HybridCouplingEffect,
  HybridRunStatus,
  // Target Plan types (User-defined intervention plans)
  TargetPlanItem,
  TargetPlanCreate,
  TargetPlanUpdate,
  TargetPlanListResponse,
  TargetPlanSource,
  InterventionStep,
  PlanConstraints,
  AIGeneratePlanRequest,
  AIGeneratePlanResponse,
  CreateBranchFromPlanRequest,
  CreateBranchFromPlanResponse,
  // LLM Admin types (GAPS.md GAP-P0-001)
  LLMProfile,
  LLMProfileCreate,
  LLMProfileUpdate,
  LLMProfileListResponse,
  LLMCall,
  LLMCallListResponse,
  LLMCostReport,
  AvailableLLMModelsResponse,
  ProfileKeysResponse,
  LLMTestResponse,
  // Audit Log Admin types (GAPS.md GAP-P0-006)
  AuditLogEntry,
  AuditLogListResponse,
  AuditLogStatsResponse,
  AuditLogExportResponse,
  // PHASE 6: Reliability Integration types
  Phase6ReliabilitySummaryResponse,
  Phase6ReliabilityDetailResponse,
  Phase6ReliabilityQueryParams,
  // PHASE 7: Aggregated Report types
  ReportResponse,
  ReportQueryParams,
  // PHASE 8: Backtest types
  BacktestStatus,
  BacktestCreate,
  BacktestResponse,
  BacktestListResponse,
  BacktestRunsResponse,
  BacktestReportsResponse,
  BacktestResetResponse,
  BacktestStartResponse,
  // PIL Job types (blueprint.md §5)
  PILJob,
  PILJobCreate,
  PILJobUpdate,
  PILJobStatus,
  PILJobType,
  PILArtifact,
  PILArtifactCreate,
  PILArtifactType,
  PILJobStats,
  // Blueprint types (blueprint.md §3, §4)
  Blueprint,
  BlueprintCreate,
  BlueprintUpdate,
  BlueprintSlot,
  BlueprintSlotUpdate,
  BlueprintTask,
  BlueprintTaskUpdate,
  SubmitClarificationAnswers,
  ProjectChecklist,
  GuidancePanel,
  GoalAnalysisResult,
  ClarifyingQuestion,
  // Blueprint v2 types (Slice 2A)
  BlueprintV2Response,
  BlueprintV2CreateRequest,
  BlueprintV2JobStatus,
  // Blueprint v2 validation types (Slice 2B)
  BlueprintV2ValidationRequest,
  BlueprintV2ValidationResult,
  BlueprintV2SaveRequest,
  BlueprintV2SaveResponse,
  // Project Guidance types (Slice 2C)
  GuidanceSection,
  GuidanceStatus,
  ProjectGuidanceResponse,
  ProjectGuidanceListResponse,
  TriggerGenesisResponse,
  GenesisJobStatus,
  // TEG (Thought Expansion Graph) types
  TEGNodeType,
  TEGNodeStatus,
  TEGEdgeRelation,
  TEGNodeResponse,
  TEGNodeDetail,
  TEGEdgeResponse,
  TEGGraphResponse,
  SyncFromRunsResponse,
  ExpandScenarioRequest,
  ExpandScenarioResponse,
  RunScenarioRequest,
  RunScenarioResponse,
  AttachEvidenceRequest,
  AttachEvidenceResponse,
  EvidenceComplianceResult,
} from '@/lib/api';

// Extended session user type for type safety
interface ExtendedSessionUser {
  id?: string;
  name?: string | null;
  email?: string | null;
  image?: string | null;
  accessToken?: string;
  role?: string;
  tier?: string;
}

// Set up API token from session
export function useApiAuth() {
  const { data: session, status } = useSession();

  useEffect(() => {
    if (session?.user) {
      const user = session.user as ExtendedSessionUser;
      if (user.accessToken) {
        api.setAccessToken(user.accessToken);
      }
    } else {
      api.setAccessToken(null);
    }
  }, [session]);

  const isAuthenticated = !!session;
  const isLoading = status === 'loading';
  const isReady = !isLoading && isAuthenticated;

  return { isAuthenticated, isLoading, isReady };
}

// Cache time constants for better performance
const CACHE_TIMES = {
  SHORT: 2 * 60 * 1000,      // 2 minutes - for frequently changing data
  MEDIUM: 5 * 60 * 1000,     // 5 minutes - for user data
  LONG: 15 * 60 * 1000,      // 15 minutes - for semi-static data
  STATIC: 60 * 60 * 1000,    // 1 hour - for reference data
} as const;

// Project Hooks
export function useProjects(params?: {
  skip?: number;
  limit?: number;
  domain?: string;
  search?: string;
}) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['projects', params],
    queryFn: () => api.listProjects(params),
    enabled: isReady,
    staleTime: CACHE_TIMES.MEDIUM,
  });
}

export function useProject(projectId: string) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['project', projectId],
    queryFn: () => api.getProject(projectId),
    enabled: isReady && !!projectId,
    staleTime: CACHE_TIMES.MEDIUM,
  });
}

export function useProjectStats(projectId: string) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['project', projectId, 'stats'],
    queryFn: () => api.getProjectStats(projectId),
    enabled: isReady && !!projectId,
    staleTime: CACHE_TIMES.SHORT,
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (data: ProjectCreate) => api.createProject(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
}

export function useUpdateProject() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: ({ projectId, data }: { projectId: string; data: ProjectUpdate }) =>
      api.updateProject(projectId, data),
    onSuccess: (project) => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      queryClient.setQueryData(['project', project.id], project);
    },
  });
}

export function useDeleteProject() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (projectId: string) => api.deleteProject(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
}

export function useDuplicateProject() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: ({ projectId, newName }: { projectId: string; newName?: string }) =>
      api.duplicateProject(projectId, newName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
}

// Scenario Hooks
export function useScenarios(params?: {
  project_id?: string;
  skip?: number;
  limit?: number;
  status?: string;
  scenario_type?: string;
}) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['scenarios', params],
    queryFn: () => api.listScenarios(params),
    enabled: isReady && (!params?.project_id || !!params.project_id),
    staleTime: CACHE_TIMES.MEDIUM,
  });
}

export function useScenario(scenarioId: string) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['scenario', scenarioId],
    queryFn: () => api.getScenario(scenarioId),
    enabled: isReady && !!scenarioId,
    staleTime: CACHE_TIMES.MEDIUM,
  });
}

export function useScenariosByProject(projectId: string | null) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['scenarios', { project_id: projectId }],
    queryFn: () => api.listScenarios({ project_id: projectId || undefined }),
    enabled: isReady && !!projectId,
    staleTime: CACHE_TIMES.MEDIUM,
  });
}

export function useCreateScenario() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (data: ScenarioCreate) => api.createScenario(data),
    onSuccess: (scenario) => {
      queryClient.invalidateQueries({ queryKey: ['scenarios'] });
      queryClient.invalidateQueries({ queryKey: ['project', scenario.project_id, 'stats'] });
    },
  });
}

export function useUpdateScenario() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: ({ scenarioId, data }: { scenarioId: string; data: ScenarioUpdate }) =>
      api.updateScenario(scenarioId, data),
    onSuccess: (scenario) => {
      queryClient.invalidateQueries({ queryKey: ['scenarios'] });
      queryClient.setQueryData(['scenario', scenario.id], scenario);
    },
  });
}

export function useDeleteScenario() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (scenarioId: string) => api.deleteScenario(scenarioId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scenarios'] });
    },
  });
}

export function useValidateScenario() {
  useApiAuth();

  return useMutation({
    mutationFn: (scenarioId: string) => api.validateScenario(scenarioId),
  });
}

// Simulation Hooks
export function useSimulations(params?: {
  scenario_id?: string;
  status?: string;
  skip?: number;
  limit?: number;
}) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['simulations', params],
    queryFn: () => api.listSimulations(params),
    enabled: isReady,
    staleTime: CACHE_TIMES.SHORT,
  });
}

export function useSimulation(runId: string) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['simulation', runId],
    queryFn: () => api.getSimulation(runId),
    enabled: isReady && !!runId,
    refetchInterval: (query) => {
      // Poll every 2 seconds if simulation is running
      const data = query.state.data;
      if (data?.status === 'running' || data?.status === 'pending') {
        return 2000;
      }
      return false;
    },
  });
}

export function useSimulationStats() {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['simulationStats'],
    queryFn: () => api.getSimulationStats(),
    enabled: isReady,
  });
}

export function useCreateSimulation() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (data: SimulationRunCreate) => api.createSimulation(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['simulations'] });
    },
  });
}

export function useRunSimulation() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (runId: string) => api.runSimulation(runId),
    onSuccess: (simulation) => {
      queryClient.invalidateQueries({ queryKey: ['simulations'] });
      queryClient.setQueryData(['simulation', simulation.id], simulation);
    },
  });
}

export function useCancelSimulation() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (runId: string) => api.cancelSimulation(runId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['simulations'] });
    },
  });
}

export function useSimulationResults(runId: string) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['simulation', runId, 'results'],
    queryFn: () => api.getSimulationResults(runId),
    enabled: isReady && !!runId,
  });
}

export function useAgentResponses(
  runId: string,
  params?: {
    skip?: number;
    limit?: number;
    question_id?: string;
  }
) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['simulation', runId, 'agents', params],
    queryFn: () => api.getAgentResponses(runId, params),
    enabled: isReady && !!runId,
  });
}

export function useExportSimulation() {
  useApiAuth();

  return useMutation({
    mutationFn: ({ runId, format }: { runId: string; format?: 'csv' | 'json' }) =>
      api.exportSimulation(runId, format),
  });
}

// ========== Data Source Hooks ==========

export function useDataSources(params?: {
  skip?: number;
  limit?: number;
  source_type?: string;
}) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['dataSources', params],
    queryFn: () => api.listDataSources(params),
    enabled: isReady,
    staleTime: CACHE_TIMES.LONG,
  });
}

export function useDataSource(dataSourceId: string) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['dataSource', dataSourceId],
    queryFn: () => api.getDataSource(dataSourceId),
    enabled: isReady && !!dataSourceId,
    staleTime: CACHE_TIMES.LONG,
  });
}

export function useCreateDataSource() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (data: DataSourceCreate) => api.createDataSource(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataSources'] });
    },
  });
}

export function useUpdateDataSource() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: ({ dataSourceId, data }: { dataSourceId: string; data: DataSourceUpdate }) =>
      api.updateDataSource(dataSourceId, data),
    onSuccess: (dataSource) => {
      queryClient.invalidateQueries({ queryKey: ['dataSources'] });
      queryClient.setQueryData(['dataSource', dataSource.id], dataSource);
    },
  });
}

export function useDeleteDataSource() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (dataSourceId: string) => api.deleteDataSource(dataSourceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataSources'] });
    },
  });
}

// ========== Census Data Hooks ==========

export function useUSStates() {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['usStates'],
    queryFn: () => api.getUSStates(),
    enabled: isReady,
    staleTime: 1000 * 60 * 60, // Cache for 1 hour - state list rarely changes
  });
}

export function useCensusDemographics(
  category: 'age' | 'gender' | 'income' | 'education' | 'occupation',
  params?: {
    state?: string;
    county?: string;
    year?: number;
  }
) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['censusDemographics', category, params],
    queryFn: () => api.getCensusDemographics(category, params),
    enabled: isReady,
    staleTime: 1000 * 60 * 30, // Cache for 30 minutes
  });
}

export function useCensusProfile(params?: {
  state?: string;
  county?: string;
  year?: number;
}) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['censusProfile', params],
    queryFn: () => api.getCensusProfile(params),
    enabled: isReady,
    staleTime: 1000 * 60 * 30, // Cache for 30 minutes
  });
}

export function useSyncCensusData() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (data: { state?: string; county?: string; year?: number }) =>
      api.syncCensusData(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataSources'] });
      queryClient.invalidateQueries({ queryKey: ['regionalProfiles'] });
    },
  });
}

// ========== Regional Profile Hooks ==========

export function useRegionalProfiles(params?: {
  skip?: number;
  limit?: number;
  region_type?: string;
}) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['regionalProfiles', params],
    queryFn: () => api.listRegionalProfiles(params),
    enabled: isReady,
  });
}

export function useRegionalProfile(regionCode: string) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['regionalProfile', regionCode],
    queryFn: () => api.getRegionalProfile(regionCode),
    enabled: isReady && !!regionCode,
  });
}

export function useBuildRegionalProfile() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (params: {
      region_code: string;
      region_name: string;
      state?: string;
      county?: string;
    }) => api.buildRegionalProfile(params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['regionalProfiles'] });
    },
  });
}

// ========== Persona Template Hooks ==========

export function usePersonaTemplates(params?: {
  skip?: number;
  limit?: number;
  region?: string;
  source_type?: string;
}) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['personaTemplates', params],
    queryFn: () => api.listPersonaTemplates(params),
    enabled: isReady,
  });
}

export function usePersonaTemplate(templateId: string) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['personaTemplate', templateId],
    queryFn: () => api.getPersonaTemplate(templateId),
    enabled: isReady && !!templateId,
  });
}

export function useCreatePersonaTemplate() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (data: PersonaTemplateCreate) => api.createPersonaTemplate(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['personaTemplates'] });
    },
  });
}

export function useDeletePersonaTemplate() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (templateId: string) => api.deletePersonaTemplate(templateId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['personaTemplates'] });
    },
  });
}

// ========== Persona Generation Hooks ==========

export function usePersonas(templateId: string, params?: { skip?: number; limit?: number }) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['personas', templateId, params],
    queryFn: () => api.listPersonas(templateId, params),
    enabled: isReady && !!templateId,
  });
}

/**
 * Infinite query for lazy-loading personas
 * Supports infinite scroll with automatic pagination
 */
export function useInfinitePersonas(templateId: string, pageSize = 50) {
  const { isReady } = useApiAuth();

  return useInfiniteQuery({
    queryKey: ['personas', templateId, 'infinite'],
    queryFn: async ({ pageParam = 0 }) => {
      const data = await api.listPersonas(templateId, {
        skip: pageParam,
        limit: pageSize,
      });
      return {
        items: data,
        nextCursor: data.length === pageSize ? pageParam + pageSize : undefined,
      };
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage) => lastPage.nextCursor,
    enabled: isReady && !!templateId,
  });
}

export function useGeneratePersonas() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (data: GeneratePersonasRequest) => api.generatePersonas(data),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['personaTemplates'] });
      if (result.template_id) {
        queryClient.invalidateQueries({ queryKey: ['personas', result.template_id] });
      }
    },
  });
}

// ========== Persona Upload Hooks ==========

export function useAnalyzePersonaUpload() {
  useApiAuth();

  return useMutation({
    mutationFn: (file: File) => api.analyzePersonaUpload(file),
  });
}

export function useProcessPersonaUpload() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: ({
      file,
      mapping,
      templateId,
    }: {
      file: File;
      mapping: Record<string, string>;
      templateId?: string;
    }) => api.processPersonaUpload(file, mapping, templateId),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['personaTemplates'] });
      queryClient.invalidateQueries({ queryKey: ['personaUploads'] });
    },
  });
}

export function usePersonaUploads(params?: { skip?: number; limit?: number }) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['personaUploads', params],
    queryFn: () => api.listPersonaUploads(params),
    enabled: isReady,
  });
}

export function usePersonaUploadTemplateUrl() {
  return api.getPersonaUploadTemplateUrl();
}

// ========== AI Research Hooks ==========

export function useStartAIResearch() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (data: AIResearchRequest) => api.startAIResearch(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['aiResearchJobs'] });
    },
  });
}

export function useAIResearchJob(jobId: string) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['aiResearchJob', jobId],
    queryFn: () => api.getAIResearchJob(jobId),
    enabled: isReady && !!jobId,
    refetchInterval: (query) => {
      // Poll every 3 seconds if job is still running
      const data = query.state.data;
      if (data?.status === 'running' || data?.status === 'pending') {
        return 3000;
      }
      return false;
    },
  });
}

export function useAIResearchJobs(params?: { skip?: number; limit?: number }) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['aiResearchJobs', params],
    queryFn: () => api.listAIResearchJobs(params),
    enabled: isReady,
  });
}

// ========== Project Personas Hooks (DB-persisted personas) ==========

export function useProjectPersonas(projectId: string, params?: { skip?: number; limit?: number }) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['projectPersonas', projectId, params],
    queryFn: () => api.listProjectPersonas(projectId, params),
    enabled: isReady && !!projectId,
  });
}

export function useSaveProjectPersonas() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: ({
      projectId,
      personas,
    }: {
      projectId: string;
      personas: Record<string, unknown>[];
    }) => api.saveProjectPersonas(projectId, personas),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['projectPersonas', result.project_id] });
    },
  });
}

export function useDeleteProjectPersonas() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (projectId: string) => api.deleteProjectPersonas(projectId),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['projectPersonas', result.project_id] });
    },
  });
}

// ========== Region Information Hooks ==========

export function useSupportedRegions() {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['supportedRegions'],
    queryFn: () => api.listSupportedRegions(),
    enabled: isReady,
    staleTime: 1000 * 60 * 60, // Cache for 1 hour - region list rarely changes
  });
}

export function useRegionDemographics(
  regionCode: string,
  params?: {
    country?: string;
    sub_region?: string;
    year?: number;
  }
) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['regionDemographics', regionCode, params],
    queryFn: () => api.getRegionDemographics(regionCode, params),
    enabled: isReady && !!regionCode,
    staleTime: 1000 * 60 * 30, // Cache for 30 minutes
  });
}

// ========== Product Hooks ==========

export function useProducts(params?: {
  project_id?: string;
  product_type?: string;
  status?: string;
  skip?: number;
  limit?: number;
}) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['products', params],
    queryFn: () => api.listProducts(params),
    enabled: isReady,
    staleTime: CACHE_TIMES.MEDIUM,
  });
}

export function useProduct(productId: string) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['product', productId],
    queryFn: () => api.getProduct(productId),
    enabled: isReady && !!productId,
    staleTime: CACHE_TIMES.MEDIUM,
  });
}

export function useCreateProduct() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (data: ProductCreate) => api.createProduct(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
    },
  });
}

export function useUpdateProduct() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: ({ productId, data }: { productId: string; data: ProductUpdate }) =>
      api.updateProduct(productId, data),
    onSuccess: (product) => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
      queryClient.setQueryData(['product', product.id], product);
    },
  });
}

export function useDeleteProduct() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (productId: string) => api.deleteProduct(productId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
    },
  });
}

export function useProductStats() {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['productStats'],
    queryFn: () => api.getProductStats(),
    enabled: isReady,
    staleTime: CACHE_TIMES.SHORT,
  });
}

export function useProductTypes() {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['productTypes'],
    queryFn: () => api.getProductTypes(),
    enabled: isReady,
    staleTime: 1000 * 60 * 60, // Cache for 1 hour
  });
}

// Product Runs
export function useProductRuns(productId: string) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['productRuns', productId],
    queryFn: () => api.listProductRuns(productId),
    enabled: isReady && !!productId,
  });
}

export function useCreateProductRun() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: ({ productId, name }: { productId: string; name?: string }) =>
      api.createProductRun(productId, name),
    onSuccess: (run) => {
      queryClient.invalidateQueries({ queryKey: ['productRuns', run.product_id] });
      queryClient.invalidateQueries({ queryKey: ['product', run.product_id] });
    },
  });
}

export function useStartProductRun() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: ({ productId, runId }: { productId: string; runId: string }) =>
      api.startProductRun(productId, runId),
    onSuccess: (run) => {
      queryClient.invalidateQueries({ queryKey: ['productRuns', run.product_id] });
      queryClient.invalidateQueries({ queryKey: ['product', run.product_id] });
    },
  });
}

export function useCancelProductRun() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: ({ productId, runId }: { productId: string; runId: string }) =>
      api.cancelProductRun(productId, runId),
    onSuccess: (run) => {
      queryClient.invalidateQueries({ queryKey: ['productRuns', run.product_id] });
    },
  });
}

// Product Results
export function useProductResults(productId: string) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['productResults', productId],
    queryFn: () => api.listProductResults(productId),
    enabled: isReady && !!productId,
  });
}

export function useProductResult(productId: string, resultId: string) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['productResult', productId, resultId],
    queryFn: () => api.getProductResult(productId, resultId),
    enabled: isReady && !!productId && !!resultId,
  });
}

// ==================== Validation Hooks ====================

// Benchmarks
export function useBenchmarks(params?: {
  category?: string;
  region?: string;
  is_public?: boolean;
}) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['benchmarks', params],
    queryFn: () => api.listBenchmarks(params),
    enabled: isReady,
  });
}

export function useBenchmark(benchmarkId: string) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['benchmark', benchmarkId],
    queryFn: () => api.getBenchmark(benchmarkId),
    enabled: isReady && !!benchmarkId,
  });
}

export function useCreateBenchmark() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (data: BenchmarkCreate) => api.createBenchmark(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['benchmarks'] });
    },
  });
}

export function useDeleteBenchmark() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (benchmarkId: string) => api.deleteBenchmark(benchmarkId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['benchmarks'] });
    },
  });
}

export function useSeedElectionBenchmarks() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: () => api.seedElectionBenchmarks(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['benchmarks'] });
    },
  });
}

export function useBenchmarkCategories() {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['benchmarkCategories'],
    queryFn: () => api.getBenchmarkCategories(),
    enabled: isReady,
  });
}

// Validation Records
export function useValidations(params?: {
  product_id?: string;
  benchmark_id?: string;
}) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['validations', params],
    queryFn: () => api.listValidations(params),
    enabled: isReady,
  });
}

export function useValidation(validationId: string) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['validation', validationId],
    queryFn: () => api.getValidation(validationId),
    enabled: isReady && !!validationId,
  });
}

export function useValidatePrediction() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (data: ValidationCreate) => api.validatePrediction(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['validations'] });
      queryClient.invalidateQueries({ queryKey: ['accuracyStats'] });
    },
  });
}

// Accuracy Stats
export function useAccuracyStats(category?: string) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['accuracyStats', category],
    queryFn: () => api.getAccuracyStats(category),
    enabled: isReady,
  });
}

export function useGlobalAccuracyStats(category?: string) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['globalAccuracyStats', category],
    queryFn: () => api.getGlobalAccuracyStats(category),
    enabled: isReady,
  });
}

// ==================== AI Content Generation Hooks ====================

export function useAITemplates(category?: string) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['aiTemplates', category],
    queryFn: () => api.listAITemplates(category),
    enabled: isReady,
    staleTime: 1000 * 60 * 60, // Cache for 1 hour - templates rarely change
  });
}

export function useAITemplate(templateId: string) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['aiTemplate', templateId],
    queryFn: () => api.getAITemplate(templateId),
    enabled: isReady && !!templateId,
    staleTime: 1000 * 60 * 60, // Cache for 1 hour
  });
}

export function useGenerateAIContent() {
  useApiAuth();

  return useMutation({
    mutationFn: (data: GenerateAIContentRequest) => api.generateAIContent(data),
  });
}

export function useAICategories() {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['aiCategories'],
    queryFn: () => api.getAICategories(),
    enabled: isReady,
    staleTime: 1000 * 60 * 60, // Cache for 1 hour
  });
}

// ==================== Marketplace Hooks ====================

import type {
  MarketplaceCategory,
  MarketplaceTemplateListItem,
  MarketplaceTemplateDetail,
  TemplateReview,
  MarketplaceTemplateCreate,
  MarketplaceTemplateUpdate,
  UseTemplateRequest,
} from '@/lib/api';

// Categories
export function useMarketplaceCategories() {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['marketplaceCategories'],
    queryFn: () => api.listMarketplaceCategories(),
    enabled: isReady,
    staleTime: 1000 * 60 * 60, // Cache for 1 hour
  });
}

// Templates
export function useMarketplaceTemplates(params?: {
  query?: string;
  category_id?: string;
  category_slug?: string;
  scenario_type?: string;
  tags?: string;
  author_id?: string;
  is_featured?: boolean;
  is_verified?: boolean;
  is_premium?: boolean;
  min_rating?: number;
  min_usage?: number;
  sort_by?: 'popular' | 'newest' | 'rating' | 'usage' | 'name';
  page?: number;
  page_size?: number;
}) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['marketplaceTemplates', params],
    queryFn: () => api.listMarketplaceTemplates(params),
    enabled: isReady,
    staleTime: CACHE_TIMES.SHORT, // Marketplace can change frequently
  });
}

export function useFeaturedTemplates() {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['featuredTemplates'],
    queryFn: () => api.getFeaturedTemplates(),
    enabled: isReady,
    staleTime: CACHE_TIMES.MEDIUM, // Featured don't change as often
  });
}

export function useMarketplaceTemplate(slug: string) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['marketplaceTemplate', slug],
    queryFn: () => api.getMarketplaceTemplate(slug),
    enabled: isReady && !!slug,
    staleTime: CACHE_TIMES.MEDIUM,
  });
}

export function useMyTemplates(params?: { page?: number; page_size?: number }) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['myTemplates', params],
    queryFn: () => api.listMyTemplates(params),
    enabled: isReady,
    staleTime: CACHE_TIMES.MEDIUM,
  });
}

export function useCreateMarketplaceTemplate() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (data: MarketplaceTemplateCreate) => api.createMarketplaceTemplate(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['marketplaceTemplates'] });
      queryClient.invalidateQueries({ queryKey: ['myTemplates'] });
    },
  });
}

export function useUpdateMarketplaceTemplate() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: ({ templateId, data }: { templateId: string; data: MarketplaceTemplateUpdate }) =>
      api.updateMarketplaceTemplate(templateId, data),
    onSuccess: (template) => {
      queryClient.invalidateQueries({ queryKey: ['marketplaceTemplates'] });
      queryClient.invalidateQueries({ queryKey: ['myTemplates'] });
      queryClient.setQueryData(['marketplaceTemplate', template.slug], template);
    },
  });
}

export function useDeleteMarketplaceTemplate() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (templateId: string) => api.deleteMarketplaceTemplate(templateId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['marketplaceTemplates'] });
      queryClient.invalidateQueries({ queryKey: ['myTemplates'] });
    },
  });
}

export function useUseMarketplaceTemplate() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: ({ templateId, data }: { templateId: string; data: UseTemplateRequest }) =>
      api.useMarketplaceTemplate(templateId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['marketplaceTemplate'] });
      queryClient.invalidateQueries({ queryKey: ['scenarios'] });
      queryClient.invalidateQueries({ queryKey: ['products'] });
    },
  });
}

// Likes
export function useToggleTemplateLike() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (templateId: string) => api.toggleTemplateLike(templateId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['marketplaceTemplates'] });
      queryClient.invalidateQueries({ queryKey: ['marketplaceTemplate'] });
    },
  });
}

// Reviews
export function useTemplateReviews(templateId: string, params?: { page?: number; page_size?: number; limit?: number }) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['templateReviews', templateId, params],
    queryFn: () => api.listTemplateReviews(templateId, params),
    enabled: isReady && !!templateId,
    staleTime: CACHE_TIMES.SHORT,
  });
}

export function useCreateTemplateReview() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: ({
      templateId,
      data,
    }: {
      templateId: string;
      data: { rating: number; title?: string; content?: string };
    }) => api.createTemplateReview(templateId, data),
    onSuccess: (_, { templateId }) => {
      queryClient.invalidateQueries({ queryKey: ['templateReviews', templateId] });
      queryClient.invalidateQueries({ queryKey: ['marketplaceTemplate'] });
    },
  });
}

// Marketplace Stats
export function useMarketplaceStats() {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['marketplaceStats'],
    queryFn: () => api.getMarketplaceStats(),
    enabled: isReady,
    staleTime: CACHE_TIMES.MEDIUM,
  });
}

// ==================== Predictive AI Simulation Hooks ====================

// Predictions List
export function usePredictions(params?: {
  status?: PredictionStatus;
  scenario_type?: string;
  skip?: number;
  limit?: number;
}) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['predictions', params],
    queryFn: () => api.listPredictions(params),
    enabled: isReady,
    staleTime: CACHE_TIMES.SHORT,
  });
}

// Single Prediction
export function usePrediction(predictionId: string) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['prediction', predictionId],
    queryFn: () => api.getPrediction(predictionId),
    enabled: isReady && !!predictionId,
    refetchInterval: (query) => {
      // Poll every 2 seconds if prediction is running
      const data = query.state.data;
      if (data?.status === 'running' || data?.status === 'pending') {
        return 2000;
      }
      return false;
    },
  });
}

// Create Prediction
export function useCreatePrediction() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (data: PredictionCreate) => api.createPrediction(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['predictions'] });
      queryClient.invalidateQueries({ queryKey: ['predictionAnalytics'] });
    },
  });
}

// Cancel Prediction
export function useCancelPrediction() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (predictionId: string) => api.cancelPrediction(predictionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['predictions'] });
    },
  });
}

// Prediction Results
export function usePredictionResults(predictionId: string) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['prediction', predictionId, 'results'],
    queryFn: () => api.getPredictionResults(predictionId),
    enabled: isReady && !!predictionId,
  });
}

// Real-time Prediction Stream (SSE)
export interface PredictionStreamState {
  progress: number;
  status: PredictionStatus;
  currentStep: number;
  totalSteps: number;
  currentRun: number;
  totalRuns: number;
  message: string;
  isConnected: boolean;
  error: string | null;
}

export function usePredictionStream(
  predictionId: string,
  enabled: boolean = true
): PredictionStreamState & { disconnect: () => void } {
  const [state, setState] = useState<PredictionStreamState>({
    progress: 0,
    status: 'pending',
    currentStep: 0,
    totalSteps: 0,
    currentRun: 0,
    totalRuns: 0,
    message: '',
    isConnected: false,
    error: null,
  });

  const [eventSource, setEventSource] = useState<EventSource | null>(null);

  const disconnect = useCallback(() => {
    if (eventSource) {
      eventSource.close();
      setEventSource(null);
      setState((prev) => ({ ...prev, isConnected: false }));
    }
  }, [eventSource]);

  useEffect(() => {
    if (!enabled || !predictionId) {
      return;
    }

    const source = api.streamPrediction(predictionId);
    setEventSource(source);

    source.onopen = () => {
      setState((prev) => ({ ...prev, isConnected: true, error: null }));
    };

    source.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setState((prev) => ({
          ...prev,
          progress: data.progress ?? prev.progress,
          status: data.status ?? prev.status,
          currentStep: data.current_step ?? prev.currentStep,
          totalSteps: data.total_steps ?? prev.totalSteps,
          currentRun: data.current_run ?? prev.currentRun,
          totalRuns: data.total_runs ?? prev.totalRuns,
          message: data.message ?? prev.message,
        }));

        // Auto-disconnect when completed or failed
        if (data.status === 'completed' || data.status === 'failed' || data.status === 'cancelled') {
          source.close();
          setState((prev) => ({ ...prev, isConnected: false }));
        }
      } catch {
        // Ignore parse errors for keep-alive messages
      }
    };

    source.onerror = () => {
      setState((prev) => ({
        ...prev,
        isConnected: false,
        error: 'Connection lost. Retrying...',
      }));
    };

    return () => {
      source.close();
    };
  }, [predictionId, enabled]);

  return { ...state, disconnect };
}

// Calibration
export function useStartCalibration() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (data: CalibrationRequest) => api.startCalibration(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['calibrations'] });
    },
  });
}

export function useCalibrationStatus(calibrationId: string) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['calibration', calibrationId],
    queryFn: () => api.getCalibrationStatus(calibrationId),
    enabled: isReady && !!calibrationId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.status === 'running' || data?.status === 'pending') {
        return 3000;
      }
      return false;
    },
  });
}

// =============================================================================
// PHASE 6: Reliability Integration Hooks
// =============================================================================

/**
 * Hook for Phase 6 reliability summary.
 * Returns sensitivity, stability, drift, and calibration metrics.
 */
export function usePhase6ReliabilitySummary(
  nodeId: string | undefined,
  params: Phase6ReliabilityQueryParams | undefined
) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['phase6Reliability', 'summary', nodeId, params],
    queryFn: () => api.getPhase6ReliabilitySummary(nodeId!, params!),
    enabled: isReady && !!nodeId && !!params?.metric_key,
    staleTime: CACHE_TIMES.MEDIUM,
  });
}

/**
 * Hook for Phase 6 reliability detail.
 * Returns raw values, percentiles, and bootstrap samples.
 */
export function usePhase6ReliabilityDetail(
  nodeId: string | undefined,
  params: Phase6ReliabilityQueryParams | undefined
) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['phase6Reliability', 'detail', nodeId, params],
    queryFn: () => api.getPhase6ReliabilityDetail(nodeId!, params!),
    enabled: isReady && !!nodeId && !!params?.metric_key,
    staleTime: CACHE_TIMES.MEDIUM,
  });
}

// =============================================================================
// PHASE 7: Aggregated Report Hooks (Reports Page)
// =============================================================================

/**
 * Hook for Phase 7 aggregated report.
 * Merges prediction, reliability, calibration, and provenance.
 * NEVER returns HTTP 500 - returns insufficient_data=true instead.
 */
export function useNodeReport(
  nodeId: string | undefined,
  params: ReportQueryParams | undefined
) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['reports', nodeId, params],
    queryFn: () => api.getNodeReport(nodeId!, params!),
    // Enabled only when we have nodeId and all required params
    enabled: isReady && !!nodeId && !!params?.metric_key && !!params?.op && params?.threshold !== undefined,
    staleTime: CACHE_TIMES.MEDIUM,
    // Important: Keep previous data while refetching for smooth UI transitions
    placeholderData: (prev) => prev,
  });
}

/**
 * Hook for exporting Phase 7 report as JSON.
 * Same as useNodeReport but triggers download.
 */
export function useExportNodeReport() {
  useApiAuth();

  return useMutation({
    mutationFn: ({ nodeId, params }: { nodeId: string; params: ReportQueryParams }) =>
      api.exportNodeReport(nodeId, params),
    // No cache invalidation needed - export is read-only
  });
}

// MARL Training
export function useStartMarlTraining() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (data: MarlTrainingRequest) => api.startMarlTraining(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['marlTraining'] });
    },
  });
}

// Prediction Analytics
export function usePredictionAnalyticsOverview() {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['predictionAnalytics', 'overview'],
    queryFn: () => api.getPredictionAnalyticsOverview(),
    enabled: isReady,
    staleTime: CACHE_TIMES.SHORT,
  });
}

export function usePredictionAccuracyAnalytics() {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['predictionAnalytics', 'accuracy'],
    queryFn: () => api.getAccuracyAnalytics(),
    enabled: isReady,
    staleTime: CACHE_TIMES.MEDIUM,
  });
}

// =============================================================================
// Spec-Compliant Run Hooks (project.md §6.5-6.6)
// =============================================================================

export function useRuns(params?: {
  project_id?: string;
  node_id?: string;
  status?: SpecRunStatus;
  skip?: number;
  limit?: number;
}) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['runs', params],
    queryFn: () => api.listRuns(params),
    enabled: isReady,
    staleTime: CACHE_TIMES.SHORT,
  });
}

export function useRun(runId: string | undefined) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['runs', runId],
    queryFn: () => api.getRun(runId!),
    enabled: isReady && !!runId,
    staleTime: CACHE_TIMES.SHORT,
  });
}

export function useCreateRun() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (data: SubmitRunInput) => api.createRun(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['runs'] });
      queryClient.invalidateQueries({ queryKey: ['nodes'] });
    },
  });
}

export function useStartRun() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (runId: string) => api.startRun(runId),
    onSuccess: (_, runId) => {
      queryClient.invalidateQueries({ queryKey: ['runs', runId] });
      queryClient.invalidateQueries({ queryKey: ['runs'] });
    },
  });
}

export function useCancelRun() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (runId: string) => api.cancelRun(runId),
    onSuccess: (_, runId) => {
      queryClient.invalidateQueries({ queryKey: ['runs', runId] });
      queryClient.invalidateQueries({ queryKey: ['runs'] });
    },
  });
}

export function useRunProgress(runId: string | undefined) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['runs', runId, 'progress'],
    queryFn: () => api.getRunProgress(runId!),
    enabled: isReady && !!runId,
    staleTime: 1000, // Poll frequently during run
    refetchInterval: (query) => {
      const data = query.state.data as RunProgressUpdate | undefined;
      if (data && (data.status === 'succeeded' || data.status === 'failed' || data.status === 'cancelled')) {
        return false;
      }
      return 2000; // Poll every 2 seconds while running
    },
  });
}

export function useRunResults(runId: string | undefined) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['runs', runId, 'results'],
    queryFn: () => api.getRunResults(runId!),
    enabled: isReady && !!runId,
    staleTime: CACHE_TIMES.LONG,
  });
}

// =============================================================================
// Run Audit Report Hooks (temporal.md §8 Phase 5)
// =============================================================================

export function useRunAuditReport(runId: string | undefined) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['runs', runId, 'audit'],
    queryFn: () => api.getRunAuditReport(runId!),
    enabled: isReady && !!runId,
    staleTime: CACHE_TIMES.LONG,
  });
}

export function useRunAuditManifest(runId: string | undefined) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['runs', runId, 'audit', 'manifest'],
    queryFn: () => api.getRunAuditManifest(runId!),
    enabled: isReady && !!runId,
    staleTime: CACHE_TIMES.LONG,
  });
}

export function useRunIsolationStatus(runId: string | undefined) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['runs', runId, 'audit', 'isolation'],
    queryFn: () => api.getRunIsolationStatus(runId!),
    enabled: isReady && !!runId,
    staleTime: CACHE_TIMES.SHORT,
  });
}

export function useCreateBatchRuns() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (params: {
      node_id: string;
      config_id?: string;
      seed_count: number;
      label_prefix?: string;
    }) => api.createBatchRuns(params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['runs'] });
    },
  });
}

export function useRunConfigs(params?: {
  project_id?: string;
  is_template?: boolean;
  skip?: number;
  limit?: number;
}) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['runConfigs', params],
    queryFn: () => api.listRunConfigs(params),
    enabled: isReady,
    staleTime: CACHE_TIMES.MEDIUM,
  });
}

export function useCreateRunConfig() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (data: CreateRunConfigInput) => api.createRunConfig(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['runConfigs'] });
    },
  });
}

// Run Progress Streaming Hook
export function useRunProgressStream(runId: string | undefined) {
  const [progress, setProgress] = useState<RunProgressUpdate | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runId) return;

    const eventSource = api.streamRunProgress(runId);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as RunProgressUpdate;
        setProgress(data);
        if (data.status === 'succeeded' || data.status === 'failed' || data.status === 'cancelled') {
          eventSource.close();
        }
      } catch {
        setError('Failed to parse progress update');
      }
    };

    eventSource.onerror = () => {
      setError('Connection error');
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [runId]);

  return { progress, error };
}

// =============================================================================
// Node/Universe Map Hooks (project.md §6.7)
// =============================================================================

export function useNodes(params?: {
  project_id?: string;
  parent_node_id?: string;
  skip?: number;
  limit?: number;
}) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['nodes', params],
    queryFn: () => api.listNodes(params),
    enabled: isReady,
    staleTime: CACHE_TIMES.SHORT,
  });
}

/**
 * Infinite query for lazy-loading nodes
 * Supports infinite scroll with automatic pagination
 */
export function useInfiniteNodes(
  projectId: string | undefined,
  pageSize = 50
) {
  const { isReady } = useApiAuth();

  return useInfiniteQuery({
    queryKey: ['nodes', projectId, 'infinite'],
    queryFn: async ({ pageParam = 0 }) => {
      const data = await api.listNodes({
        project_id: projectId,
        skip: pageParam,
        limit: pageSize,
      });
      return {
        items: data,
        nextCursor: data.length === pageSize ? pageParam + pageSize : undefined,
      };
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage) => lastPage.nextCursor,
    enabled: isReady && !!projectId,
    staleTime: CACHE_TIMES.SHORT,
  });
}

export function useNode(nodeId: string | undefined) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['nodes', nodeId],
    queryFn: () => api.getNode(nodeId!),
    enabled: isReady && !!nodeId,
    staleTime: CACHE_TIMES.SHORT,
  });
}

export function useForkNode() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (data: ForkNodeInput) => api.forkNode(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['nodes'] });
      queryClient.invalidateQueries({ queryKey: ['universeMap'] });
    },
  });
}

export function useNodeChildren(nodeId: string | undefined) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['nodes', nodeId, 'children'],
    queryFn: () => api.getNodeChildren(nodeId!),
    enabled: isReady && !!nodeId,
    staleTime: CACHE_TIMES.SHORT,
  });
}

export function useNodeEdges(nodeId: string | undefined) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['nodes', nodeId, 'edges'],
    queryFn: () => api.getNodeEdges(nodeId!),
    enabled: isReady && !!nodeId,
    staleTime: CACHE_TIMES.SHORT,
  });
}

export function useUpdateNodeUI() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (params: {
      nodeId: string;
      data: { ui_position?: { x: number; y: number }; is_collapsed?: boolean; is_pinned?: boolean };
    }) => api.updateNodeUI(params.nodeId, params.data),
    onSuccess: (_, params) => {
      queryClient.invalidateQueries({ queryKey: ['nodes', params.nodeId] });
      queryClient.invalidateQueries({ queryKey: ['universeMap'] });
    },
  });
}

export function useUniverseMap(projectId: string | undefined) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['universeMap', projectId],
    queryFn: () => api.getUniverseMap(projectId!),
    enabled: isReady && !!projectId,
    staleTime: CACHE_TIMES.SHORT,
  });
}

export function useUniverseMapFull(projectId: string | undefined) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['universeMap', projectId, 'full'],
    queryFn: () => api.getUniverseMapFull(projectId!),
    enabled: isReady && !!projectId,
    staleTime: CACHE_TIMES.SHORT,
  });
}

export function useCompareNodes() {
  useApiAuth();

  return useMutation({
    mutationFn: (nodeIds: string[]) => api.compareNodes(nodeIds),
  });
}

export function useAnalyzeNodePath() {
  useApiAuth();

  return useMutation({
    mutationFn: (params: { start_node_id: string; end_node_id: string }) =>
      api.analyzeNodePath(params),
  });
}

export function useMostLikelyPaths(projectId: string | undefined, maxPaths?: number) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['universeMap', projectId, 'likelyPaths', maxPaths],
    queryFn: () => api.getMostLikelyPaths(projectId!, maxPaths),
    enabled: isReady && !!projectId,
    staleTime: CACHE_TIMES.MEDIUM,
  });
}

// =============================================================================
// Telemetry Hooks (project.md §6.8) - READ-ONLY (C3 Compliant)
// =============================================================================

export function useTelemetryIndex(runId: string | undefined) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['telemetry', runId, 'index'],
    queryFn: () => api.getTelemetryIndex(runId!),
    enabled: isReady && !!runId,
    staleTime: CACHE_TIMES.LONG,
  });
}

export function useTelemetrySlice(runId: string | undefined, tick: number) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['telemetry', runId, 'slice', tick],
    queryFn: () => api.getTelemetrySlice(runId!, tick),
    enabled: isReady && !!runId,
    staleTime: CACHE_TIMES.LONG,
  });
}

export function useTelemetryRange(
  runId: string | undefined,
  params: {
    start_tick: number;
    end_tick: number;
    include_keyframes?: boolean;
    include_deltas?: boolean;
    max_deltas?: number;
  }
) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['telemetry', runId, 'range', params],
    queryFn: () => api.getTelemetryRange(runId!, params),
    enabled: isReady && !!runId,
    staleTime: CACHE_TIMES.LONG,
  });
}

export function useTelemetryKeyframe(runId: string | undefined, tick: number) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['telemetry', runId, 'keyframe', tick],
    queryFn: () => api.getTelemetryKeyframe(runId!, tick),
    enabled: isReady && !!runId,
    staleTime: CACHE_TIMES.LONG,
  });
}

export function useTelemetryMetric(
  runId: string | undefined,
  metricName: string,
  params?: { start_tick?: number; end_tick?: number; downsample_factor?: number }
) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['telemetry', runId, 'metrics', metricName, params],
    queryFn: () => api.getTelemetryMetric(runId!, metricName, params),
    enabled: isReady && !!runId && !!metricName,
    staleTime: CACHE_TIMES.LONG,
  });
}

export function useTelemetryAgentHistory(
  runId: string | undefined,
  agentId: string | undefined,
  params?: { start_tick?: number; end_tick?: number }
) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['telemetry', runId, 'agents', agentId, params],
    queryFn: () => api.getTelemetryAgentHistory(runId!, agentId!, params),
    enabled: isReady && !!runId && !!agentId,
    staleTime: CACHE_TIMES.LONG,
  });
}

export function useTelemetryEvents(runId: string | undefined) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['telemetry', runId, 'events'],
    queryFn: () => api.getTelemetryEvents(runId!),
    enabled: isReady && !!runId,
    staleTime: CACHE_TIMES.LONG,
  });
}

export function useTelemetrySummary(runId: string | undefined) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['telemetry', runId, 'summary'],
    queryFn: () => api.getTelemetrySummary(runId!),
    enabled: isReady && !!runId,
    staleTime: CACHE_TIMES.LONG,
  });
}

/**
 * Chunked telemetry loading for large datasets
 * Loads telemetry data in configurable tick ranges
 */
export function useChunkedTelemetry(
  runId: string | undefined,
  totalTicks: number,
  chunkSize = 100
) {
  const { isReady } = useApiAuth();

  return useInfiniteQuery({
    queryKey: ['telemetry', runId, 'chunked', chunkSize],
    queryFn: async ({ pageParam = 0 }) => {
      const startTick = pageParam;
      const endTick = Math.min(pageParam + chunkSize, totalTicks);

      const data = await api.getTelemetryRange(runId!, {
        start_tick: startTick,
        end_tick: endTick,
        include_keyframes: true,
        include_deltas: true,
      });

      return {
        data,
        startTick,
        endTick,
        nextCursor: endTick < totalTicks ? endTick : undefined,
      };
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage) => lastPage.nextCursor,
    enabled: isReady && !!runId && totalTicks > 0,
    staleTime: CACHE_TIMES.LONG,
  });
}

export function useExportTelemetry() {
  useApiAuth();

  return useMutation({
    mutationFn: (params: {
      runId: string;
      format?: 'json' | 'csv' | 'parquet';
      include_keyframes?: boolean;
      include_deltas?: boolean;
    }) => api.exportTelemetry(params.runId, params),
  });
}

// Telemetry Streaming Hook for Replay
export function useTelemetryStream(
  runId: string | undefined,
  params?: { start_tick?: number; speed?: number }
) {
  const [slice, setSlice] = useState<TelemetrySlice | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);

  const start = useCallback(() => {
    if (!runId) return;
    setIsPlaying(true);
  }, [runId]);

  const stop = useCallback(() => {
    setIsPlaying(false);
  }, []);

  useEffect(() => {
    if (!runId || !isPlaying) return;

    const eventSource = api.streamTelemetry(runId, params);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as TelemetrySlice;
        setSlice(data);
      } catch {
        setError('Failed to parse telemetry data');
      }
    };

    eventSource.onerror = () => {
      setError('Connection error');
      eventSource.close();
      setIsPlaying(false);
    };

    return () => {
      eventSource.close();
    };
  }, [runId, isPlaying, params]);

  return { slice, error, isPlaying, start, stop };
}

// =============================================================================
// Project Spec Hooks (project.md §6.1)
// =============================================================================

export function useProjectSpecs(params?: {
  skip?: number;
  limit?: number;
  domain?: string;
  search?: string;
}) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['projectSpecs', params],
    queryFn: () => api.listProjectSpecs(params),
    enabled: isReady,
    staleTime: CACHE_TIMES.MEDIUM,
  });
}

export function useProjectSpec(projectId: string | undefined) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['projectSpecs', projectId],
    queryFn: () => api.getProjectSpec(projectId!),
    enabled: isReady && !!projectId,
    staleTime: CACHE_TIMES.MEDIUM,
  });
}

export function useCreateProjectSpec() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (data: ProjectSpecCreate) => api.createProjectSpec(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projectSpecs'] });
    },
  });
}

export function useUpdateProjectSpec() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (params: { projectId: string; data: ProjectSpecUpdate }) =>
      api.updateProjectSpec(params.projectId, params.data),
    onSuccess: (_, params) => {
      queryClient.invalidateQueries({ queryKey: ['projectSpecs', params.projectId] });
      queryClient.invalidateQueries({ queryKey: ['projectSpecs'] });
    },
  });
}

export function useDeleteProjectSpec() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (projectId: string) => api.deleteProjectSpec(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projectSpecs'] });
    },
  });
}

export function useProjectSpecStats(projectId: string | undefined) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['projectSpecs', projectId, 'stats'],
    queryFn: () => api.getProjectSpecStats(projectId!),
    enabled: isReady && !!projectId,
    staleTime: CACHE_TIMES.SHORT,
  });
}

export function useDuplicateProjectSpec() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (params: { projectId: string; newName?: string }) =>
      api.duplicateProjectSpec(params.projectId, params.newName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projectSpecs'] });
    },
  });
}

export function useCreateProjectSpecRun() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (params: {
      projectId: string;
      data: {
        node_id?: string;
        seeds?: number[];
        auto_start?: boolean;
        config_overrides?: Partial<CreateRunConfigInput>;
      };
    }) => api.createProjectSpecRun(params.projectId, params.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['runs'] });
      queryClient.invalidateQueries({ queryKey: ['projectSpecs'] });
      queryClient.invalidateQueries({ queryKey: ['nodes'] });
    },
  });
}

// =============================================================================
// Ask / Event Compiler Hooks (project.md §11 Phase 4)
// =============================================================================

export function useCompileAskPrompt() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (data: {
      project_id: string;
      prompt: string;
      max_scenarios?: number;
      clustering_enabled?: boolean;
    }) => api.compileAskPrompt(data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['askCompilations', variables.project_id] });
    },
  });
}

export function useExpandAskCluster() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (data: {
      compilation_id: string;
      cluster_id: string;
      max_children?: number;
    }) => api.expandAskCluster(data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['askCompilation', variables.compilation_id] });
    },
  });
}

export function useAskCompilations(params?: {
  project_id?: string;
  skip?: number;
  limit?: number;
}) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['askCompilations', params?.project_id, params],
    queryFn: () => api.listAskCompilations(params),
    enabled: isReady,
    staleTime: CACHE_TIMES.SHORT,
  });
}

export function useAskCompilation(compilationId: string | undefined) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['askCompilation', compilationId],
    queryFn: () => api.getAskCompilation(compilationId!),
    enabled: isReady && !!compilationId,
    staleTime: CACHE_TIMES.SHORT,
  });
}

export function useDeleteAskCompilation() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (compilationId: string) => api.deleteAskCompilation(compilationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['askCompilations'] });
    },
  });
}

export function useExecuteAskScenario() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (data: {
      compilation_id: string;
      scenario_id: string;
      node_id?: string;
      auto_fork?: boolean;
      run_config_overrides?: Partial<CreateRunConfigInput>;
    }) => api.executeAskScenario(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['nodes'] });
      queryClient.invalidateQueries({ queryKey: ['runs'] });
    },
  });
}

// ========== Target Mode Hooks (project.md §11 Phase 5) ==========

// Target Personas
export function useTargetPersonas(params?: {
  project_id?: string;
  domain?: string;
  skip?: number;
  limit?: number;
}) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['targetPersonas', params?.project_id, params],
    queryFn: () => api.listTargetPersonas(params),
    enabled: isReady,
    staleTime: CACHE_TIMES.MEDIUM,
  });
}

export function useTargetPersona(targetId: string | undefined) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['targetPersona', targetId],
    queryFn: () => api.getTargetPersona(targetId!),
    enabled: isReady && !!targetId,
    staleTime: CACHE_TIMES.MEDIUM,
  });
}

export function useCreateTargetPersona() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (data: TargetPersonaCreate) => api.createTargetPersona(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['targetPersonas'] });
    },
  });
}

export function useDeleteTargetPersona() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (targetId: string) => api.deleteTargetPersona(targetId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['targetPersonas'] });
    },
  });
}

// Path Planning
export function useTargetPlans(params?: {
  project_id?: string;
  target_id?: string;
  status?: PlanStatus;
  skip?: number;
  limit?: number;
}) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['targetPlans', params?.project_id, params?.target_id, params],
    queryFn: () => api.listTargetPlans(params),
    enabled: isReady,
    staleTime: CACHE_TIMES.SHORT,
  });
}

export function useTargetPlan(planId: string | undefined) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['targetPlan', planId],
    queryFn: () => api.getTargetPlan(planId!),
    enabled: isReady && !!planId,
    staleTime: CACHE_TIMES.SHORT,
  });
}

export function useRunTargetPlanner() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (data: TargetPlanRequest) => api.runTargetPlanner(data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['targetPlans', variables.project_id] });
    },
  });
}

export function useTargetPlanClusters(planId: string | undefined) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['targetPlanClusters', planId],
    queryFn: () => api.getTargetPlanClusters(planId!),
    enabled: isReady && !!planId,
    staleTime: CACHE_TIMES.SHORT,
  });
}

export function useExpandTargetCluster() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (data: ExpandClusterRequest) => api.expandTargetCluster(data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['targetPlan', variables.plan_id] });
      queryClient.invalidateQueries({ queryKey: ['targetPlanClusters', variables.plan_id] });
    },
  });
}

export function useTargetPlanPaths(planId: string | undefined, params?: {
  cluster_id?: string;
  status?: PathStatus;
  limit?: number;
}) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['targetPlanPaths', planId, params],
    queryFn: () => api.getTargetPlanPaths(planId!, params),
    enabled: isReady && !!planId,
    staleTime: CACHE_TIMES.SHORT,
  });
}

export function useBranchPathToNode() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (data: BranchToNodeRequest) => api.branchPathToNode(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['nodes'] });
      queryClient.invalidateQueries({ queryKey: ['runs'] });
    },
  });
}

// Action Catalogs
export function useActionCatalogs(params?: {
  domain?: string;
}) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['actionCatalogs', params?.domain],
    queryFn: () => api.listActionCatalogs(params),
    enabled: isReady,
    staleTime: CACHE_TIMES.LONG,
  });
}

export function useActionCatalog(catalogId: string | undefined) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['actionCatalog', catalogId],
    queryFn: () => api.getActionCatalog(catalogId!),
    enabled: isReady && !!catalogId,
    staleTime: CACHE_TIMES.LONG,
  });
}

// =============================================================================
// Hybrid Mode Hooks (project.md §11 Phase 6)
// =============================================================================

export function useRunHybridSimulation() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (data: HybridRunRequest) => api.runHybridSimulation(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hybridRuns'] });
      queryClient.invalidateQueries({ queryKey: ['nodes'] });
    },
  });
}

export function useHybridRun(runId: string | undefined) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['hybridRun', runId],
    queryFn: () => api.getHybridRun(runId!),
    enabled: isReady && !!runId,
    staleTime: CACHE_TIMES.SHORT,
    refetchInterval: (query) => {
      const data = query.state.data as HybridRunResult | undefined;
      // Poll while running
      if (data?.status === 'running' || data?.status === 'pending') {
        return 2000; // 2 seconds
      }
      return false;
    },
  });
}

export function useHybridRuns(params?: {
  project_id?: string;
  status?: HybridRunStatus;
  limit?: number;
  offset?: number;
}) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['hybridRuns', params?.project_id, params?.status, params?.limit, params?.offset],
    queryFn: () => api.listHybridRuns(params),
    enabled: isReady,
    staleTime: CACHE_TIMES.SHORT,
  });
}

export function useHybridRunProgress(runId: string | undefined) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['hybridRunProgress', runId],
    queryFn: () => api.getHybridRunProgress(runId!),
    enabled: isReady && !!runId,
    staleTime: 1000, // 1 second for real-time progress
    refetchInterval: 2000, // Poll every 2 seconds
  });
}

export function useCancelHybridRun() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (runId: string) => api.cancelHybridRun(runId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hybridRuns'] });
      queryClient.invalidateQueries({ queryKey: ['hybridRun'] });
    },
  });
}

export function useBranchHybridToNode() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: ({ runId, data }: { runId: string; data: { parent_node_id: string; label?: string | null } }) =>
      api.branchHybridToNode(runId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['nodes'] });
    },
  });
}

export function useHybridCouplingEffects(
  runId: string | undefined,
  params?: {
    tick_start?: number;
    tick_end?: number;
    source_type?: 'actor' | 'society';
  }
) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['hybridCouplingEffects', runId, params?.tick_start, params?.tick_end, params?.source_type],
    queryFn: () => api.getHybridCouplingEffects(runId!, params),
    enabled: isReady && !!runId,
    staleTime: CACHE_TIMES.MEDIUM,
  });
}

// =============================================================================
// 2D Replay Hooks (project.md §11 Phase 8) - READ-ONLY (C3 Compliant)
// =============================================================================

export function useLoadReplay(storageRef: LoadReplayRequest | null) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['replay', storageRef?.storage_ref.artifact_id, storageRef?.node_id],
    queryFn: () => api.loadReplay(storageRef!),
    enabled: isReady && !!storageRef,
    staleTime: CACHE_TIMES.LONG,
  });
}

export function useReplayState(
  tick: number,
  storageRef: LoadReplayRequest | null
) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['replayState', storageRef?.storage_ref.artifact_id, tick],
    queryFn: () => api.getReplayStateAtTick(tick, storageRef!),
    enabled: isReady && !!storageRef && tick >= 0,
    staleTime: CACHE_TIMES.LONG,
  });
}

export function useReplayChunk(
  storageRef: LoadReplayRequest | null,
  params?: { start_tick?: number; end_tick?: number; include_states?: boolean }
) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['replayChunk', storageRef?.storage_ref.artifact_id, params],
    queryFn: () => api.getReplayChunk(storageRef!, params),
    enabled: isReady && !!storageRef,
    staleTime: CACHE_TIMES.LONG,
  });
}

export function useReplayAgentHistory(
  agentId: string | undefined,
  storageRef: LoadReplayRequest | null,
  params?: { tick_start?: number; tick_end?: number }
) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['replayAgentHistory', agentId, storageRef?.storage_ref.artifact_id, params],
    queryFn: () => api.getReplayAgentHistory(agentId!, storageRef!, params),
    enabled: isReady && !!agentId && !!storageRef,
    staleTime: CACHE_TIMES.MEDIUM,
  });
}

export function useReplayEventsAtTick(
  tick: number,
  storageRef: LoadReplayRequest | null
) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['replayEvents', storageRef?.storage_ref.artifact_id, tick],
    queryFn: () => api.getReplayEventsAtTick(tick, storageRef!),
    enabled: isReady && !!storageRef && tick >= 0,
    staleTime: CACHE_TIMES.LONG,
  });
}

export function useSeekReplay() {
  useApiAuth();

  return useMutation({
    mutationFn: ({ tick, request }: { tick: number; request: LoadReplayRequest }) =>
      api.seekReplay(tick, request),
  });
}

// =============================================================================
// Export Hooks (Interaction_design.md §5.19)
// =============================================================================

export function useExports(params?: {
  project_id?: string;
  export_type?: ExportType;
  status?: ExportStatus;
  limit?: number;
  offset?: number;
}) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['exports', params?.project_id, params?.export_type, params?.status],
    queryFn: () => api.listExports(params),
    enabled: isReady,
    staleTime: CACHE_TIMES.SHORT,
  });
}

export function useExport(exportId: string | undefined) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['export', exportId],
    queryFn: () => api.getExport(exportId!),
    enabled: isReady && !!exportId,
    staleTime: CACHE_TIMES.SHORT,
    refetchInterval: (query) => {
      // Refetch frequently if export is still processing
      const data = query.state.data;
      if (data && (data.status === 'pending' || data.status === 'processing')) {
        return 2000; // Poll every 2 seconds
      }
      return false;
    },
  });
}

export function useCreateExport() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (data: ExportRequest) => api.createExport(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exports'] });
    },
  });
}

export function useDeleteExport() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (exportId: string) => api.deleteExport(exportId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exports'] });
    },
  });
}

export function useExportDownloadUrl() {
  useApiAuth();

  return useMutation({
    mutationFn: (exportId: string) => api.getExportDownloadUrl(exportId),
  });
}

export function useExportShareUrl() {
  useApiAuth();

  return useMutation({
    mutationFn: ({ exportId, privacy }: { exportId: string; privacy?: ExportPrivacy }) =>
      api.getExportShareUrl(exportId, privacy),
  });
}

// =============================================================================
// LLM Admin Hooks (GAPS.md GAP-P0-001)
// =============================================================================

export function useLLMProfiles(params?: {
  tenant_id?: string;
  is_active?: boolean;
  profile_key?: string;
}) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['llm-profiles', params?.tenant_id, params?.is_active, params?.profile_key],
    queryFn: () => api.listLLMProfiles(params),
    enabled: isReady,
    staleTime: CACHE_TIMES.MEDIUM,
  });
}

export function useLLMProfile(profileId: string | undefined) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['llm-profile', profileId],
    queryFn: () => api.getLLMProfile(profileId!),
    enabled: isReady && !!profileId,
    staleTime: CACHE_TIMES.MEDIUM,
  });
}

export function useCreateLLMProfile() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (data: LLMProfileCreate) => api.createLLMProfile(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['llm-profiles'] });
    },
  });
}

export function useUpdateLLMProfile() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: ({ profileId, data }: { profileId: string; data: LLMProfileUpdate }) =>
      api.updateLLMProfile(profileId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['llm-profiles'] });
      queryClient.invalidateQueries({ queryKey: ['llm-profile'] });
    },
  });
}

export function useDeleteLLMProfile() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (profileId: string) => api.deleteLLMProfile(profileId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['llm-profiles'] });
    },
  });
}

export function useLLMCalls(params?: {
  tenant_id?: string;
  profile_key?: string;
  project_id?: string;
  run_id?: string;
  status?: string;
  page?: number;
  page_size?: number;
  start_date?: string;
  end_date?: string;
}) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['llm-calls', params],
    queryFn: () => api.listLLMCalls(params),
    enabled: isReady,
    staleTime: CACHE_TIMES.SHORT,
  });
}

export function useLLMCostReport(params?: {
  tenant_id?: string;
  start_date?: string;
  end_date?: string;
}) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['llm-cost-report', params?.tenant_id, params?.start_date, params?.end_date],
    queryFn: () => api.getLLMCostReport(params),
    enabled: isReady,
    staleTime: CACHE_TIMES.SHORT,
  });
}

export function useAvailableLLMModels() {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['llm-available-models'],
    queryFn: () => api.getAvailableLLMModels(),
    enabled: isReady,
    staleTime: CACHE_TIMES.LONG,
  });
}

export function useStandardProfileKeys() {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['llm-profile-keys'],
    queryFn: () => api.getStandardProfileKeys(),
    enabled: isReady,
    staleTime: CACHE_TIMES.LONG,
  });
}

export function useTestLLMProfile() {
  useApiAuth();

  return useMutation({
    mutationFn: ({ profileId, testPrompt }: { profileId: string; testPrompt?: string }) =>
      api.testLLMProfile(profileId, testPrompt),
  });
}

// =============================================================================
// Audit Log Admin Hooks (GAPS.md GAP-P0-006)
// =============================================================================

export function useAuditLogs(params?: {
  action?: string;
  resource_type?: string;
  resource_id?: string;
  user_id?: string;
  tenant_id?: string;
  start_date?: string;
  end_date?: string;
  ip_address?: string;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: string;
}) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: [
      'audit-logs',
      params?.action,
      params?.resource_type,
      params?.user_id,
      params?.tenant_id,
      params?.start_date,
      params?.end_date,
      params?.page,
      params?.page_size,
    ],
    queryFn: () => api.listAuditLogs(params),
    enabled: isReady,
    staleTime: CACHE_TIMES.SHORT,
  });
}

export function useAuditLog(logId: string | undefined) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['audit-log', logId],
    queryFn: () => api.getAuditLog(logId!),
    enabled: isReady && !!logId,
    staleTime: CACHE_TIMES.LONG,
  });
}

export function useAuditStats(params?: {
  tenant_id?: string;
  days?: number;
}) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['audit-stats', params?.tenant_id, params?.days],
    queryFn: () => api.getAuditStats(params),
    enabled: isReady,
    staleTime: CACHE_TIMES.SHORT,
  });
}

export function useExportAuditLogs() {
  useApiAuth();

  return useMutation({
    mutationFn: (params: {
      format?: 'json' | 'csv';
      action?: string;
      resource_type?: string;
      user_id?: string;
      tenant_id?: string;
      start_date?: string;
      end_date?: string;
      limit?: number;
    }) => api.exportAuditLogs(params),
  });
}

export function useAuditActions() {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['audit-actions'],
    queryFn: () => api.listAuditActions(),
    enabled: isReady,
    staleTime: CACHE_TIMES.LONG,
  });
}

export function useAuditResourceTypes() {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['audit-resource-types'],
    queryFn: () => api.listAuditResourceTypes(),
    enabled: isReady,
    staleTime: CACHE_TIMES.LONG,
  });
}

// =============================================================================
// User Target Plan Hooks (User-defined intervention plans)
// Note: Named with "User" prefix to avoid conflicts with existing TargetPlanner hooks
// =============================================================================

export function useUserTargetPlans(projectId: string | undefined, params?: {
  node_id?: string;
  source?: TargetPlanSource;
  skip?: number;
  limit?: number;
}) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['userTargetPlans', projectId, params],
    queryFn: () => api.listUserTargetPlans(projectId!, params),
    enabled: isReady && !!projectId,
    staleTime: CACHE_TIMES.MEDIUM,
  });
}

export function useUserTargetPlan(planId: string | undefined) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['userTargetPlans', 'detail', planId],
    queryFn: () => api.getUserTargetPlan(planId!),
    enabled: isReady && !!planId,
    staleTime: CACHE_TIMES.MEDIUM,
  });
}

export function useCreateUserTargetPlan() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: ({ projectId, data }: { projectId: string; data: TargetPlanCreate }) =>
      api.createUserTargetPlan(projectId, data),
    onSuccess: (_, { projectId }) => {
      queryClient.invalidateQueries({ queryKey: ['userTargetPlans', projectId] });
    },
  });
}

export function useUpdateUserTargetPlan() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: ({ planId, data }: { planId: string; data: TargetPlanUpdate }) =>
      api.updateUserTargetPlan(planId, data),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['userTargetPlans', result.project_id] });
      queryClient.invalidateQueries({ queryKey: ['userTargetPlans', 'detail', result.id] });
    },
  });
}

export function useDeleteUserTargetPlan() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: ({ planId, projectId }: { planId: string; projectId: string }) =>
      api.deleteUserTargetPlan(planId).then(() => projectId),
    onSuccess: (projectId) => {
      queryClient.invalidateQueries({ queryKey: ['userTargetPlans', projectId] });
    },
  });
}

export function useGenerateUserTargetPlanWithAI() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: ({ projectId, data }: { projectId: string; data: AIGeneratePlanRequest }) =>
      api.generateUserTargetPlanWithAI(projectId, data),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['userTargetPlans', result.plan.project_id] });
    },
  });
}

export function useCreateBranchFromUserPlan() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: ({ planId, data }: { planId: string; data: CreateBranchFromPlanRequest }) =>
      api.createBranchFromUserPlan(planId, data),
    onSuccess: () => {
      // Invalidate nodes and universe map
      queryClient.invalidateQueries({ queryKey: ['nodes'] });
      queryClient.invalidateQueries({ queryKey: ['universe-map'] });
    },
  });
}

// =============================================================================
// PHASE 8: Backtest Hooks (End-to-End Backtest Loop)
// =============================================================================

/**
 * List backtests for a project.
 */
export function useBacktests(
  projectId: string | undefined,
  params?: {
    status?: BacktestStatus;
    page?: number;
    page_size?: number;
  }
) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['backtests', projectId, params],
    queryFn: () => api.listBacktests(projectId!, params),
    enabled: isReady && !!projectId,
    staleTime: CACHE_TIMES.SHORT,
    refetchInterval: (query) => {
      // Auto-refresh every 5s if any backtest is running
      const data = query.state.data;
      if (data?.items?.some(b => b.status === 'running')) {
        return 5000;
      }
      return false;
    },
  });
}

/**
 * Get backtest detail.
 */
export function useBacktest(
  projectId: string | undefined,
  backtestId: string | undefined
) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['backtests', projectId, backtestId],
    queryFn: () => api.getBacktest(projectId!, backtestId!),
    enabled: isReady && !!projectId && !!backtestId,
    staleTime: CACHE_TIMES.SHORT,
    refetchInterval: (query) => {
      // Auto-refresh every 3s if backtest is running
      const data = query.state.data;
      if (data?.status === 'running') {
        return 3000;
      }
      return false;
    },
  });
}

/**
 * Get backtest runs.
 */
export function useBacktestRuns(
  projectId: string | undefined,
  backtestId: string | undefined
) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['backtests', projectId, backtestId, 'runs'],
    queryFn: () => api.getBacktestRuns(projectId!, backtestId!),
    enabled: isReady && !!projectId && !!backtestId,
    staleTime: CACHE_TIMES.SHORT,
  });
}

/**
 * Get backtest report snapshots.
 */
export function useBacktestReports(
  projectId: string | undefined,
  backtestId: string | undefined
) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['backtests', projectId, backtestId, 'reports'],
    queryFn: () => api.getBacktestReports(projectId!, backtestId!),
    enabled: isReady && !!projectId && !!backtestId,
    staleTime: CACHE_TIMES.MEDIUM,
  });
}

/**
 * Create a new backtest.
 */
export function useCreateBacktest() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: ({ projectId, data }: { projectId: string; data: BacktestCreate }) =>
      api.createBacktest(projectId, data),
    onSuccess: (_, { projectId }) => {
      queryClient.invalidateQueries({ queryKey: ['backtests', projectId] });
    },
  });
}

/**
 * SCOPED-SAFE reset backtest data.
 * Only deletes BacktestRun and BacktestReportSnapshot for this backtest.
 */
export function useResetBacktest() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: ({ projectId, backtestId }: { projectId: string; backtestId: string }) =>
      api.resetBacktest(projectId, backtestId, { confirm: true }),
    onSuccess: (_, { projectId, backtestId }) => {
      queryClient.invalidateQueries({ queryKey: ['backtests', projectId, backtestId] });
      queryClient.invalidateQueries({ queryKey: ['backtests', projectId, backtestId, 'runs'] });
      queryClient.invalidateQueries({ queryKey: ['backtests', projectId, backtestId, 'reports'] });
    },
  });
}

/**
 * Start backtest execution.
 */
export function useStartBacktest() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: ({
      projectId,
      backtestId,
      sequential = true,
    }: {
      projectId: string;
      backtestId: string;
      sequential?: boolean;
    }) => api.startBacktest(projectId, backtestId, { sequential }),
    onSuccess: (_, { projectId, backtestId }) => {
      queryClient.invalidateQueries({ queryKey: ['backtests', projectId, backtestId] });
      queryClient.invalidateQueries({ queryKey: ['backtests', projectId, backtestId, 'runs'] });
      // Also invalidate runs list as new runs will be created
      queryClient.invalidateQueries({ queryKey: ['runs'] });
    },
  });
}

/**
 * Snapshot reports for a backtest.
 */
export function useSnapshotBacktestReports() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: ({
      projectId,
      backtestId,
      metric_key,
      op,
      threshold,
    }: {
      projectId: string;
      backtestId: string;
      metric_key: string;
      op: string;
      threshold: number;
    }) => api.snapshotBacktestReports(projectId, backtestId, { metric_key, op, threshold }),
    onSuccess: (_, { projectId, backtestId }) => {
      queryClient.invalidateQueries({ queryKey: ['backtests', projectId, backtestId, 'reports'] });
    },
  });
}

// =============================================================================
// PIL Job Hooks (blueprint.md §5 - Project Intelligence Layer)
// =============================================================================

/**
 * List PIL jobs with optional filters.
 */
export function usePILJobs(params?: {
  project_id?: string;
  blueprint_id?: string;
  job_type?: PILJobType;
  status?: PILJobStatus;
  skip?: number;
  limit?: number;
}) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['pil-jobs', params],
    queryFn: () => api.listPILJobs(params),
    enabled: isReady,
    staleTime: CACHE_TIMES.SHORT,
    refetchInterval: params?.status === 'running' || params?.status === 'queued' ? 3000 : false,
  });
}

/**
 * List active (queued or running) PIL jobs.
 * Auto-refreshes every 3 seconds to track progress.
 */
export function useActivePILJobs(projectId?: string) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['pil-jobs', 'active', projectId],
    queryFn: () => api.listActivePILJobs(projectId),
    enabled: isReady,
    staleTime: 1000, // 1 second - very fresh for active jobs
    refetchInterval: 3000, // Poll every 3 seconds for active jobs
  });
}

/**
 * Get a specific PIL job by ID.
 * Auto-refreshes while job is active.
 */
export function usePILJob(jobId: string) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['pil-jobs', jobId],
    queryFn: () => api.getPILJob(jobId),
    enabled: isReady && !!jobId,
    staleTime: CACHE_TIMES.SHORT,
    refetchInterval: (query) => {
      const job = query.state.data;
      // Refresh every 2 seconds while job is active
      if (job?.status === 'queued' || job?.status === 'running') {
        return 2000;
      }
      return false;
    },
  });
}

/**
 * Create a new PIL job.
 */
export function useCreatePILJob() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (data: PILJobCreate) => api.createPILJob(data),
    onSuccess: (job) => {
      queryClient.invalidateQueries({ queryKey: ['pil-jobs'] });
      if (job.project_id) {
        queryClient.invalidateQueries({ queryKey: ['pil-jobs', { project_id: job.project_id }] });
      }
    },
  });
}

/**
 * Cancel a PIL job.
 */
export function useCancelPILJob() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (jobId: string) => api.cancelPILJob(jobId),
    onSuccess: (job) => {
      queryClient.invalidateQueries({ queryKey: ['pil-jobs'] });
      queryClient.invalidateQueries({ queryKey: ['pil-jobs', job.id] });
    },
  });
}

/**
 * Retry a failed PIL job.
 */
export function useRetryPILJob() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (jobId: string) => api.retryPILJob(jobId),
    onSuccess: (job) => {
      queryClient.invalidateQueries({ queryKey: ['pil-jobs'] });
      queryClient.invalidateQueries({ queryKey: ['pil-jobs', job.id] });
    },
  });
}

/**
 * Get PIL job statistics.
 */
export function usePILJobStats(projectId?: string) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['pil-jobs', 'stats', projectId],
    queryFn: () => api.getPILJobStats(projectId),
    enabled: isReady,
    staleTime: CACHE_TIMES.MEDIUM,
  });
}

/**
 * Get artifacts for a specific PIL job.
 */
export function usePILJobArtifacts(jobId: string) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['pil-jobs', jobId, 'artifacts'],
    queryFn: () => api.getPILJobArtifacts(jobId),
    enabled: isReady && !!jobId,
    staleTime: CACHE_TIMES.MEDIUM,
  });
}

/**
 * List PIL artifacts with optional filters.
 */
export function usePILArtifacts(params?: {
  project_id?: string;
  blueprint_id?: string;
  artifact_type?: PILArtifactType;
  slot_id?: string;
  job_id?: string;
  skip?: number;
  limit?: number;
}) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['pil-artifacts', params],
    queryFn: () => api.listPILArtifacts(params),
    enabled: isReady,
    staleTime: CACHE_TIMES.MEDIUM,
  });
}

/**
 * Get a specific PIL artifact by ID.
 */
export function usePILArtifact(artifactId: string) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['pil-artifacts', artifactId],
    queryFn: () => api.getPILArtifact(artifactId),
    enabled: isReady && !!artifactId,
    staleTime: CACHE_TIMES.LONG,
  });
}

/**
 * Create a new PIL artifact.
 */
export function useCreatePILArtifact() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (data: PILArtifactCreate) => api.createPILArtifact(data),
    onSuccess: (artifact) => {
      queryClient.invalidateQueries({ queryKey: ['pil-artifacts'] });
      if (artifact.job_id) {
        queryClient.invalidateQueries({ queryKey: ['pil-jobs', artifact.job_id, 'artifacts'] });
      }
    },
  });
}

// =============================================================================
// Blueprint Hooks (blueprint.md §3, §4)
// =============================================================================

/**
 * Get active blueprint for a project.
 */
export function useActiveBlueprint(projectId: string | undefined) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['blueprints', 'active', projectId],
    queryFn: () => api.getActiveBlueprint(projectId!),
    enabled: isReady && !!projectId,
    staleTime: CACHE_TIMES.MEDIUM,
  });
}

/**
 * Get a specific blueprint by ID.
 */
export function useBlueprint(blueprintId: string | undefined) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['blueprints', blueprintId],
    queryFn: () => api.getBlueprint(blueprintId!),
    enabled: isReady && !!blueprintId,
    staleTime: CACHE_TIMES.MEDIUM,
  });
}

/**
 * Create a new blueprint.
 */
export function useCreateBlueprint() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (data: BlueprintCreate) => api.createBlueprint(data),
    onSuccess: (blueprint) => {
      queryClient.invalidateQueries({ queryKey: ['blueprints'] });
      queryClient.invalidateQueries({ queryKey: ['pil-jobs'] });
    },
  });
}

/**
 * Update a blueprint.
 */
export function useUpdateBlueprint() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: ({ blueprintId, data }: { blueprintId: string; data: BlueprintUpdate }) =>
      api.updateBlueprint(blueprintId, data),
    onSuccess: (blueprint) => {
      queryClient.invalidateQueries({ queryKey: ['blueprints'] });
    },
  });
}

/**
 * Submit clarification answers and trigger blueprint build.
 */
export function useSubmitClarificationAnswers() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: ({
      blueprintId,
      data,
    }: {
      blueprintId: string;
      data: SubmitClarificationAnswers;
    }) => api.submitClarificationAnswers(blueprintId, data),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['blueprints'] });
      queryClient.invalidateQueries({ queryKey: ['pil-jobs'] });
    },
  });
}

/**
 * Get slots for a blueprint.
 */
export function useBlueprintSlots(blueprintId: string | undefined) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['blueprints', blueprintId, 'slots'],
    queryFn: () => api.getBlueprintSlots(blueprintId!),
    enabled: isReady && !!blueprintId,
    staleTime: CACHE_TIMES.MEDIUM,
  });
}

/**
 * Update a slot.
 */
export function useUpdateBlueprintSlot() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: ({
      blueprintId,
      slotId,
      data,
    }: {
      blueprintId: string;
      slotId: string;
      data: BlueprintSlotUpdate;
    }) => api.updateBlueprintSlot(blueprintId, slotId, data),
    onSuccess: (slot) => {
      queryClient.invalidateQueries({ queryKey: ['blueprints'] });
    },
  });
}

/**
 * Get tasks for a blueprint.
 */
export function useBlueprintTasks(blueprintId: string | undefined) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['blueprints', blueprintId, 'tasks'],
    queryFn: () => api.getBlueprintTasks(blueprintId!),
    enabled: isReady && !!blueprintId,
    staleTime: CACHE_TIMES.MEDIUM,
  });
}

/**
 * Update a task.
 */
export function useUpdateBlueprintTask() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: ({
      blueprintId,
      taskId,
      data,
    }: {
      blueprintId: string;
      taskId: string;
      data: BlueprintTaskUpdate;
    }) => api.updateBlueprintTask(blueprintId, taskId, data),
    onSuccess: (task) => {
      queryClient.invalidateQueries({ queryKey: ['blueprints'] });
    },
  });
}

/**
 * Get project checklist.
 */
export function useProjectChecklist(projectId: string | undefined) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['project-checklist', projectId],
    queryFn: () => api.getProjectChecklist(projectId!),
    enabled: isReady && !!projectId,
    staleTime: CACHE_TIMES.SHORT,
  });
}

/**
 * Get guidance panel for a section.
 */
export function useGuidancePanel(projectId: string | undefined, sectionId: string | undefined) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['guidance-panel', projectId, sectionId],
    queryFn: () => api.getGuidancePanel(projectId!, sectionId!),
    enabled: isReady && !!projectId && !!sectionId,
    staleTime: CACHE_TIMES.MEDIUM,
  });
}

/**
 * Get goal analysis result from artifacts.
 */
export function useGoalAnalysisResult(projectId: string | undefined) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['goal-analysis-result', projectId],
    queryFn: () => api.getGoalAnalysisResult(projectId!),
    enabled: isReady && !!projectId,
    staleTime: CACHE_TIMES.MEDIUM,
  });
}

// =============================================================================
// BLUEPRINT V2 HOOKS (Slice 2A)
// =============================================================================

/**
 * Trigger Blueprint v2 build job.
 */
export function useTriggerBlueprintV2Build() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (data: BlueprintV2CreateRequest) => api.triggerBlueprintV2Build(data),
    onSuccess: (result, variables) => {
      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: ['blueprint-v2', variables.project_id] });
      queryClient.invalidateQueries({ queryKey: ['pil-jobs'] });
    },
  });
}

/**
 * Get Blueprint v2 by ID.
 */
export function useBlueprintV2(blueprintId: string | undefined) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['blueprint-v2', blueprintId],
    queryFn: () => api.getBlueprintV2(blueprintId!),
    enabled: isReady && !!blueprintId,
    staleTime: CACHE_TIMES.MEDIUM,
  });
}

/**
 * Get Blueprint v2 by project ID.
 */
export function useBlueprintV2ByProject(projectId: string | undefined) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['blueprint-v2', 'project', projectId],
    queryFn: () => api.getBlueprintV2ByProject(projectId!),
    enabled: isReady && !!projectId,
    staleTime: CACHE_TIMES.MEDIUM,
  });
}

/**
 * Poll Blueprint v2 build job status.
 * Polls every 2 seconds while job is active.
 */
export function useBlueprintV2JobStatus(
  jobId: string | undefined,
  options?: { enabled?: boolean; onSuccess?: (data: BlueprintV2JobStatus) => void }
) {
  const { isReady } = useApiAuth();
  const queryClient = useQueryClient();

  return useQuery({
    queryKey: ['blueprint-v2-job', jobId],
    queryFn: () => api.getBlueprintV2JobStatus(jobId!),
    enabled: isReady && !!jobId && (options?.enabled !== false),
    refetchInterval: (query) => {
      const data = query.state.data;
      // Stop polling when job is complete or failed
      if (data?.status === 'succeeded' || data?.status === 'failed' || data?.status === 'cancelled') {
        // Invalidate related queries on completion
        if (data?.status === 'succeeded') {
          queryClient.invalidateQueries({ queryKey: ['blueprint-v2'] });
        }
        return false;
      }
      return 2000; // Poll every 2 seconds
    },
    staleTime: 1000,
  });
}

/**
 * Validate Blueprint v2 editable fields.
 * Returns validation result with errors and warnings.
 */
export function useValidateBlueprintV2Fields() {
  const { isReady } = useApiAuth();

  return useMutation({
    mutationFn: (data: BlueprintV2ValidationRequest) => api.validateBlueprintV2Fields(data),
  });
}

/**
 * Save Blueprint v2 edits with override tracking.
 * Validates before saving and stores override metadata.
 */
export function useSaveBlueprintV2Edits() {
  const { isReady } = useApiAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: BlueprintV2SaveRequest) => api.saveBlueprintV2Edits(data),
    onSuccess: (response) => {
      // Invalidate blueprint queries to refresh data
      queryClient.invalidateQueries({ queryKey: ['blueprint-v2'] });
      queryClient.invalidateQueries({ queryKey: ['blueprint-v2-project'] });
    },
  });
}

// =============================================================================
// Project Guidance Hooks (Slice 2C: Project Genesis)
// =============================================================================

/**
 * Get all project guidance sections.
 * Returns AI-generated guidance for each workspace section.
 */
export function useProjectGuidance(
  projectId: string | undefined,
  options?: { includeStale?: boolean; enabled?: boolean }
) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['project-guidance', projectId, options?.includeStale],
    queryFn: () => api.getProjectGuidance(projectId!, options?.includeStale ?? false),
    enabled: isReady && !!projectId && (options?.enabled !== false),
    staleTime: CACHE_TIMES.MEDIUM,
  });
}

/**
 * Get guidance for a specific section.
 * Returns AI-generated guidance for a single workspace section.
 */
export function useSectionGuidance(
  projectId: string | undefined,
  section: GuidanceSection | undefined,
  options?: { enabled?: boolean }
) {
  const { isReady } = useApiAuth();

  return useQuery({
    queryKey: ['project-guidance', projectId, 'section', section],
    queryFn: () => api.getSectionGuidance(projectId!, section!),
    enabled: isReady && !!projectId && !!section && (options?.enabled !== false),
    staleTime: CACHE_TIMES.MEDIUM,
    // Don't retry on 404 - guidance simply doesn't exist yet (PROJECT_GENESIS hasn't run)
    retry: (failureCount, error) => {
      const apiError = error as { status?: number };
      if (apiError?.status === 404) return false; // Don't retry 404s
      return failureCount < 1; // Standard retry for other errors
    },
    // Ensure errors go to `error` property, not error boundary
    throwOnError: false,
  });
}

/**
 * Trigger PROJECT_GENESIS job to generate guidance.
 * Returns the job ID for tracking progress.
 */
export function useTriggerProjectGenesis() {
  const { isReady } = useApiAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ projectId, forceRegenerate = false }: { projectId: string; forceRegenerate?: boolean }) =>
      api.triggerProjectGenesis(projectId, forceRegenerate),
    onSuccess: (response, { projectId }) => {
      // Invalidate guidance and genesis status queries
      queryClient.invalidateQueries({ queryKey: ['project-guidance', projectId] });
      queryClient.invalidateQueries({ queryKey: ['genesis-job-status', projectId] });
    },
  });
}

/**
 * Regenerate all project guidance.
 * Marks existing guidance as stale and triggers new genesis job.
 */
export function useRegenerateProjectGuidance() {
  const { isReady } = useApiAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (projectId: string) => api.regenerateProjectGuidance(projectId),
    onSuccess: (response, projectId) => {
      // Invalidate all guidance queries for this project
      queryClient.invalidateQueries({ queryKey: ['project-guidance', projectId] });
      queryClient.invalidateQueries({ queryKey: ['genesis-job-status', projectId] });
    },
  });
}

/**
 * Poll genesis job status.
 * Polls every 2 seconds while job is active.
 */
export function useGenesisJobStatus(
  projectId: string | undefined,
  options?: { enabled?: boolean; onSuccess?: (data: GenesisJobStatus) => void }
) {
  const { isReady } = useApiAuth();
  const queryClient = useQueryClient();

  return useQuery({
    queryKey: ['genesis-job-status', projectId],
    queryFn: () => api.getGenesisJobStatus(projectId!),
    enabled: isReady && !!projectId && (options?.enabled !== false),
    refetchInterval: (query) => {
      const data = query.state.data;
      // Stop polling when job is complete or failed
      if (data?.status === 'succeeded' || data?.status === 'failed' || data?.status === 'cancelled' || !data?.has_job) {
        // Invalidate guidance queries on completion
        if (data?.status === 'succeeded') {
          queryClient.invalidateQueries({ queryKey: ['project-guidance', projectId] });
        }
        return false;
      }
      return 2000; // Poll every 2 seconds
    },
    staleTime: 1000,
  });
}

// =============================================================================
// Evidence URL Ingestion Hooks (DEMO2_MVP_EXECUTION.md Task 4)
// =============================================================================

export type EvidenceStatus = 'PASS' | 'WARN' | 'FAIL';

export interface EvidenceUrl {
  id: string;
  url: string;
  title: string;
  content_hash: string;
  content_length: number;
  fetched_at: string;
  status: EvidenceStatus;
  status_reason: string;
  extracted_signals: {
    keywords: string[];
    topics: string[];
    entities: string[];
    sentiment?: 'positive' | 'negative' | 'neutral';
    content_type: string;
  };
  provenance: {
    source_url: string;
    fetch_timestamp: string;
    content_hash: string;
    snapshot_version: string;
    temporal_check: {
      as_of_datetime?: string;
      source_date_detected?: string;
      compliance_status: EvidenceStatus;
      compliance_reason: string;
    };
  };
}

export interface EvidenceIngestResponse {
  success: boolean;
  evidence_items: EvidenceUrl[];
  summary: {
    total: number;
    passed: number;
    warned: number;
    failed: number;
  };
}

/**
 * Ingest evidence URLs for persona generation.
 * Fetches, snapshots, and validates URLs against temporal context.
 */
export function useIngestEvidenceUrls() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: async (data: {
      urls: string[];
      project_id: string;
      as_of_datetime?: string;
    }): Promise<EvidenceIngestResponse> => {
      const response = await fetch('/api/evidence/ingest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to ingest evidence');
      }
      return response.json();
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['evidence', variables.project_id] });
    },
  });
}

// ===========================================================================
// TEG (Thought Expansion Graph) Hooks
// Reference: docs/TEG_UNIVERSE_MAP_EXECUTION.md
// ===========================================================================

/**
 * Get TEG graph for a project.
 * Returns all nodes and edges for the graph view.
 * Auto-creates TEG and syncs from runs if none exists.
 */
export function useTEGGraph(projectId: string | undefined) {
  useApiAuth();

  return useQuery({
    queryKey: ['teg', 'graph', projectId],
    queryFn: () => api.getTEGGraph(projectId!),
    enabled: !!projectId,
    staleTime: 30000, // 30 seconds
  });
}

/**
 * Get detailed TEG node information.
 * Includes computed fields for the right panel.
 */
export function useTEGNodeDetail(nodeId: string | undefined) {
  useApiAuth();

  return useQuery({
    queryKey: ['teg', 'node', nodeId],
    queryFn: () => api.getTEGNodeDetail(nodeId!),
    enabled: !!nodeId,
    staleTime: 10000, // 10 seconds
  });
}

/**
 * Sync TEG from existing simulation runs.
 * Creates OUTCOME_VERIFIED nodes for completed runs.
 */
export function useSyncTEGFromRuns() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: (projectId: string) => api.syncTEGFromRuns(projectId),
    onSuccess: (_, projectId) => {
      queryClient.invalidateQueries({ queryKey: ['teg', 'graph', projectId] });
    },
  });
}

/**
 * Set a node as the active baseline for comparisons.
 */
export function useSetTEGBaseline() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: ({ projectId, nodeId }: { projectId: string; nodeId: string }) =>
      api.setTEGBaseline(projectId, nodeId),
    onSuccess: (_, { projectId }) => {
      queryClient.invalidateQueries({ queryKey: ['teg', 'graph', projectId] });
    },
  });
}

/**
 * Expand a TEG node into draft scenario variations using LLM.
 * Creates SCENARIO_DRAFT nodes with EXPANDS_TO edges.
 */
export function useExpandTEGNode() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: ({
      nodeId,
      sourceNodeId,
      whatIfPrompt,
      numScenarios,
      includeOpposite,
    }: {
      nodeId: string;
      sourceNodeId: string;
      whatIfPrompt?: string;
      numScenarios?: number;
      includeOpposite?: boolean;
    }) =>
      api.expandTEGNode(nodeId, {
        source_node_id: sourceNodeId,
        what_if_prompt: whatIfPrompt,
        num_scenarios: numScenarios,
        include_opposite: includeOpposite,
      }),
    onSuccess: (data) => {
      // Invalidate the graph to show new nodes
      // We get projectId from the source node
      queryClient.invalidateQueries({ queryKey: ['teg', 'graph'] });
      queryClient.invalidateQueries({ queryKey: ['teg', 'node'] });
    },
  });
}

/**
 * Run a draft scenario to produce a verified outcome.
 * Creates simulation run and RUNS_TO edge.
 */
export function useRunTEGScenario() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: ({
      nodeId,
      autoCompare,
    }: {
      nodeId: string;
      autoCompare?: boolean;
    }) =>
      api.runTEGScenario(nodeId, {
        node_id: nodeId,
        auto_compare: autoCompare,
      }),
    onSuccess: () => {
      // Invalidate queries to reflect the new run and nodes
      queryClient.invalidateQueries({ queryKey: ['teg', 'graph'] });
      queryClient.invalidateQueries({ queryKey: ['teg', 'node'] });
      queryClient.invalidateQueries({ queryKey: ['runs'] });
    },
  });
}

/**
 * Attach evidence URLs to a TEG node (Task 7).
 * Validates URLs and checks temporal compliance.
 */
export function useAttachTEGEvidence() {
  const queryClient = useQueryClient();
  useApiAuth();

  return useMutation({
    mutationFn: ({
      nodeId,
      urls,
    }: {
      nodeId: string;
      urls: string[];
    }) =>
      api.attachTEGEvidence(nodeId, { urls }),
    onSuccess: () => {
      // Invalidate queries to reflect the updated node
      queryClient.invalidateQueries({ queryKey: ['teg', 'graph'] });
      queryClient.invalidateQueries({ queryKey: ['teg', 'node'] });
    },
  });
}

// Re-export TEG types for convenience
export type {
  TEGNodeType,
  TEGNodeStatus,
  TEGEdgeRelation,
  TEGNodeResponse,
  TEGNodeDetail,
  TEGEdgeResponse,
  TEGGraphResponse,
  SyncFromRunsResponse,
  ExpandScenarioRequest,
  ExpandScenarioResponse,
  RunScenarioRequest,
  RunScenarioResponse,
  AttachEvidenceRequest,
  AttachEvidenceResponse,
  EvidenceComplianceResult,
};

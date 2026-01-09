/**
 * AgentVerse Shared Types
 * Type definitions shared across frontend and backend
 */

// User Types
export interface User {
  id: string;
  email: string;
  fullName?: string;
  company?: string;
  role: UserRole;
  tier: UserTier;
  isActive: boolean;
  isVerified: boolean;
  createdAt: string;
  updatedAt: string;
  lastLoginAt?: string;
}

export type UserRole = 'user' | 'admin' | 'enterprise';
export type UserTier = 'free' | 'pro' | 'team' | 'enterprise';

// Project Types
export interface Project {
  id: string;
  userId: string;
  name: string;
  description?: string;
  domain?: ProjectDomain;
  settings: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export type ProjectDomain = 'marketing' | 'political' | 'finance' | 'custom';

// Scenario Types
export interface Scenario {
  id: string;
  projectId: string;
  name: string;
  description?: string;
  scenarioType?: ScenarioType;
  context: string;
  questions: Question[];
  variables: Record<string, unknown>;
  populationSize: number;
  demographics: Demographics;
  personaTemplate?: PersonaTemplate;
  modelConfigJson: ModelConfig;
  simulationMode: SimulationMode;
  status: ScenarioStatus;
  createdAt: string;
  updatedAt: string;
}

export type ScenarioType = 'survey' | 'election' | 'product_launch' | 'policy' | 'custom';
export type ScenarioStatus = 'draft' | 'ready' | 'running' | 'completed';
export type SimulationMode = 'batch' | 'streaming' | 'real-time';

// Question Types
export interface Question {
  id: string;
  type: QuestionType;
  text: string;
  options?: string[];
  scaleMin?: number;
  scaleMax?: number;
  required: boolean;
}

export type QuestionType = 'multiple_choice' | 'yes_no' | 'scale' | 'open_ended';

// Demographics Types
export interface Demographics {
  ageRange?: [number, number];
  ageDistribution?: 'normal' | 'uniform' | 'skewed_young' | 'skewed_old';
  genders?: string[];
  genderWeights?: number[];
  incomeBrackets?: string[];
  incomeWeights?: number[];
  educationLevels?: string[];
  educationWeights?: number[];
  regions?: string[];
  regionWeights?: number[];
  customAttributes?: Record<string, unknown>;
}

// Persona Types
export interface PersonaTemplate {
  basePrompt?: string;
  includeDemographics?: boolean;
  includePsychographics?: boolean;
  customAttributes?: Record<string, unknown>;
}

export interface Persona {
  index: number;
  demographics: {
    age: number;
    gender: string;
    incomeBacket: string;
    education: string;
    locationType: string;
    occupation: string;
  };
  psychographics: {
    valuesOrientation: string;
    riskTolerance: number;
    technologyAdoption: string;
    decisionStyle: string;
    brandLoyalty: string;
  };
  behavioralContext: string;
}

// Model Configuration Types
export interface ModelConfig {
  model?: string;
  temperature?: number;
  maxTokens?: number;
  topP?: number;
}

// Simulation Run Types
export interface SimulationRun {
  id: string;
  scenarioId: string;
  userId: string;
  runConfig: Record<string, unknown>;
  modelUsed?: string;
  agentCount: number;
  status: SimulationStatus;
  progress: number;
  startedAt?: string;
  completedAt?: string;
  resultsSummary?: ResultsSummary;
  confidenceScore?: number;
  tokensUsed: number;
  costUsd: number;
  createdAt: string;
}

export type SimulationStatus = 'pending' | 'running' | 'completed' | 'failed';

// Results Types
export interface ResultsSummary {
  totalAgents: number;
  responseDistribution: Record<string, number>;
  responsePercentages: Record<string, number>;
  demographicsBreakdown: DemographicsBreakdown;
  confidenceScore: number;
  topResponse?: string;
}

export interface DemographicsBreakdown {
  age: Record<string, Record<string, number>>;
  gender: Record<string, Record<string, number>>;
  incomeBacket: Record<string, Record<string, number>>;
  education: Record<string, Record<string, number>>;
}

// Agent Response Types
export interface AgentResponse {
  id: string;
  runId: string;
  agentIndex: number;
  persona: Persona;
  questionId?: string;
  response: Record<string, unknown>;
  reasoning?: string;
  confidence?: number;
  tokensUsed?: number;
  responseTimeMs?: number;
  modelUsed?: string;
  createdAt: string;
}

// API Response Types
export interface ApiResponse<T> {
  data: T;
  message?: string;
  meta?: {
    total?: number;
    page?: number;
    limit?: number;
  };
}

export interface ApiError {
  detail: string;
  code?: string;
  field?: string;
}

// Authentication Types
export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
  fullName?: string;
  company?: string;
}

// WebSocket/SSE Event Types
export interface SimulationProgressEvent {
  type: 'progress';
  runId: string;
  status: SimulationStatus;
  progress: number;
  agentsCompleted: number;
  agentsTotal: number;
}

export interface AgentResponseEvent {
  type: 'agent_response';
  index: number;
  total: number;
  progress: number;
  persona: Persona['demographics'];
  response: Record<string, unknown>;
  reasoning?: string;
}

export interface SimulationCompleteEvent {
  type: 'complete';
  totalAgents: number;
  tokensUsed: number;
  costUsd: number;
}

export type SimulationEvent =
  | SimulationProgressEvent
  | AgentResponseEvent
  | SimulationCompleteEvent;
